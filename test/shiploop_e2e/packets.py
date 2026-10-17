#!/usr/bin/env python3
"""What ShipLoop sent and what it cost: every packet and every stage of one run, from its files only.

    python3 test/shiploop_e2e/packets.py <output directory>
    python3 test/shiploop_e2e/packets.py <output directory> --compare <earlier output directory>
    python3 test/shiploop_e2e/packets.py --offline node-fix-bug     # no model: the case's inner-loop packets as rendered
    python3 test/shiploop_e2e/packets.py --offline node-fix-bug --text-dir DIR [--delegation ask-agent]
        [--run-dir-length 83|163] [--cli-path-length 96]            # the same packets as text files, at a stated path length

--offline drives the checkout's navigator through a step case with synthetic results (the seed's pattern, no project
work) and reports the packets of the item's inner loop as a cleared model would read them: the zero-cost check of a
prompt edit's effect on packet size and shape before a live slice.

--text-dir writes each packet twice (`<NN>-<stage>.printed.txt`, what the host prints, a head when the packet passes
navigator.PRINT_LIMIT; `<NN>-<stage>.whole.txt`, the packet file) and `manifest.json` (case, route, the lengths, the
sizes, the commit): the input of render_diff.py (G-RENDER of the efficiency plan).  The text is fixed so two renders of
one tree are byte-identical and two trees differ only where their packets do: ids are derived from a counter, the run
directory and the CLI package root have the stated length (`--run-dir-length N` is the exact length of the run directory;
`--cli-path-length N` is the exact length of the CLI path a packet prints, 96 for a plugin-cache install, where the bare
`shiploop` of the default walk would otherwise print), and the checkout root and the interpreter print as fixed strings
of the lengths of a normal install (INSTALL_ROOT_LENGTH, CANONICAL_PYTHON).  Sizes are measured on that text, and the
choice between the whole packet and its head is made on it (the engine made it on the real paths).

Writes packet-report.json and packet-report.md into the output directory (with --compare, packet-compare.md too) and
prints the Markdown. It reads any E2E output directory: a step slice (slice.py), whose poll archived every distinct
packet the run emitted under packet-archive/, or a full run, which keeps only the last copy of each packet
(run/packets/<action>.md is rewritten on every `next`), so its rows say "retained only".

Nothing here is the model's account. Per packet: its stage and kind (producer or Improve; the Improve stage is an action of its own,
with its own packet file, and its row names the reviewed action and stage), size, an estimated token
count (characters / 4, not a tokenizer), its largest sections, the skill references it names and whether each exists,
how many distinct emissions were observed, and how many `next` calls the host made for that action (from the event
stream). Per stage: metrics.py's seconds, turns, tool calls and context peak. Across packets: the share of each
packet's text already sent in an earlier packet. That is reported, not flagged, because restating how a stage
operates is the main tenet (context may be cleared between stages); the figure shows what it costs.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import types
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(HERE))
import fidelity  # noqa: E402
import metrics  # noqa: E402
import shiploop_loops as loops  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402

ARCHIVE = "packet-archive"
MANIFEST = "manifest.json"
REPORT_JSON, REPORT_MD, COMPARE_MD = "packet-report.json", "packet-report.md", "packet-compare.md"
IMPROVE_STAGE = navigator.IMPROVE_STAGE  # the stage name in an Improve packet's head line
ESTIMATE = "characters / 4 (an estimate, not a tokenizer count)"
# Absolute paths a packet names; only those under a skills/<leaf>/ directory are references that must exist (a path in
# the run directory is often a file the stage is about to write).
PATH = re.compile(r"(/[\w.@+~-]+(?:/[\w.@+~-]+)+\.(?:md|py|json|html|txt|sh))")
SKILL_PATH = re.compile(r"/skills/[\w-]+/")
# A packet's section starts at a line that is a `=== ... ===` marker, a Markdown heading, or a short label ending in ':'.
SECTION = re.compile(r"(?m)^(=== .{1,80} ===|#{1,4} .{1,80}|[A-Z][\w ,()'/-]{2,60}:)$")
NEXT_CALL = re.compile(r"""(?:scripts/shiploop["']?\s+next\b|\bshiploop-next\b|\bshiploop\s+next\b)""")
OVERLAP_MIN_LINE = 20  # shorter lines (a bare heading, a brace) say nothing about repetition


def improve_links(state: dict) -> dict[str, str]:
    """{Improve stage id: the reviewed action id} from state.md: the imported reviews (`improve_results[<reviewed>]
    ["improve_action"]`, set when `complete` imports the review) and the current Improve stage (`active_improve`).

    The Improve stage is an action of its own (stage `improve`) with its own packet file `<improve id>.md`, or
    `<improve id>-bind.md` before a card is bound. A saved run of the old layout has neither field: its Improve packets
    are `<reviewed action>-improve.md` and `<reviewed action>-improve-bind.md` (`packet_owner` reads both layouts).
    """
    found: dict[str, str] = {}
    results = state.get("improve_results")
    for reviewed, record in (results.items() if isinstance(results, dict) else ()):
        identity = record.get("improve_action") if isinstance(record, dict) else None
        if isinstance(identity, str):
            found[identity] = reviewed
    child = state.get("active_improve")
    if isinstance(child, dict) and isinstance(child.get("improve_action"), str):
        found[child["improve_action"]] = str(child.get("action_id"))
    return found


def packet_owner(key: str, links: dict[str, str]) -> tuple[str, str]:
    """(the reviewed or producer action a packet file belongs to, its kind `producer` or `improve`) from the file's stem.

    New layout: `<improve id>` and `<improve id>-bind` for an id in ``links``. Old layout: `<action>-improve` and
    `<action>-improve-bind`. A stem that is neither is a producer packet (an Improve packet whose stage id state.md does
    not record, such as a pure-function seed's, is told by its head line: `packet_kind`)."""
    for suffix in ("-improve-bind", "-improve"):
        if key.endswith(suffix):
            return key[:-len(suffix)], "improve"
    base = key[:-len("-bind")] if key.endswith("-bind") and key[:-len("-bind")] in links else key
    if base in links:
        return links[base], "improve"
    return key, "producer"


def find_run_dir(out: Path) -> Path | None:
    """The ShipLoop run directory under an output directory (the throwaway home and plugin build are not searched)."""
    for state_path in sorted(out.rglob("state.md")):
        parts = state_path.relative_to(out).parts
        if parts[0] in ("home", "build", "export", ARCHIVE):
            continue
        try:
            state = store.read_record(state_path)
        except store.StorageError:
            continue
        if isinstance(state, dict) and "status" in state:
            return state_path.parent
    return None


def archive_packets(run_dir: Path, out: Path) -> int:
    """Copy each packet whose content changed since its last archived copy; return how many were new.

    ShipLoop rewrites run/packets/<action>.md on every `next`, so a poll calling this keeps every distinct emission it
    saw: packet-archive/<action>/<seq>-<sha8>.md. A packet rewritten and changed back between two polls is not seen.
    """
    source = run_dir / "packets"
    if not source.is_dir():
        return 0
    added = 0
    for packet in sorted(source.glob("*.md")):
        try:
            data = packet.read_bytes()
        except OSError:
            continue
        digest = hashlib.sha256(data).hexdigest()[:8]
        folder = out / ARCHIVE / packet.stem
        kept = sorted(folder.glob("*.md")) if folder.is_dir() else []
        if kept and kept[-1].stem.endswith(digest):
            continue
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{len(kept) + 1:03d}-{digest}.md").write_bytes(data)
        added += 1
    return added


def emissions(out: Path, run_dir: Path) -> tuple[dict[str, list[str]], bool]:
    """{packet key: the texts emitted, oldest first} and whether they come from the archive (else retained only)."""
    archive = out / ARCHIVE
    if archive.is_dir() and any(archive.iterdir()):
        return ({folder.name: [p.read_text(errors="replace") for p in sorted(folder.glob("*.md"))]
                 for folder in sorted(archive.iterdir()) if folder.is_dir()}, True)
    retained = run_dir / "packets"
    return ({p.stem: [p.read_text(errors="replace")] for p in sorted(retained.glob("*.md"))} if retained.is_dir() else {},
            False)


def sections(text: str, top: int = 5) -> list[dict]:
    """The largest sections of a packet, by characters (a heuristic split at labels and markers)."""
    marks = [(m.start(), m.group(0).strip()[:70]) for m in SECTION.finditer(text)]
    if not marks or marks[0][0] > 0:
        marks.insert(0, (0, "(opening)"))
    marks.append((len(text), None))
    found = [{"section": name, "chars": end - start} for (start, name), (end, _) in zip(marks, marks[1:])]
    return sorted(found, key=lambda row: -row["chars"])[:top]


# A guide named by the GUIDES symbol (the skill's references directory, defined once in the packet's References block) is a
# skill reference too: it counts and must exist as the absolute path it stands for.
GUIDES_DEFINITION = re.compile(r"GUIDES = (.+?) \(the skill's guides\)")
GUIDE_SYMBOL = re.compile(r"\bGUIDES/([\w.@+~-]+\.(?:md|json))")


def references(text: str) -> dict:
    named = set(PATH.findall(text))
    guides = GUIDES_DEFINITION.search(text)
    if guides:
        named |= {guides.group(1) + "/" + name for name in GUIDE_SYMBOL.findall(text)}
    named = sorted(named)
    skill = [path for path in named if SKILL_PATH.search(path)]
    return {"paths_named": len(named), "skill_references": len(skill),
            "missing": [path for path in skill if not Path(path).exists()]}


def next_calls(tool_log: metrics.ToolLog) -> list[float]:
    """Times of the host's `next` calls to the ShipLoop CLI (the recovery command: it reprints the current packet)."""
    return sorted(call["t"] for call in tool_log.calls.values()
                  if call.get("t") is not None and NEXT_CALL.search(str(call.get("command") or "")))


def attribute(times: list[float], accepted: list[dict], pending: str | None) -> dict[str, int]:
    """{action id: `next` calls made while it was current}: a call belongs to the first action accepted after it."""
    counts: dict[str, int] = {}
    timed = [row for row in accepted if row.get("action") and row.get("t") is not None]
    for t in times:
        owner = next((row["action"] for row in timed if row["t"] >= t), pending)
        if owner:
            counts[owner] = counts.get(owner, 0) + 1
    return counts


def overlap_shares(texts: list[str]) -> list[float | None]:
    """For each text in order: the share of its characters on lines already sent in an earlier text."""
    seen: set[str] = set()
    shares: list[float | None] = []
    for text in texts:
        lines = [" ".join(line.split()) for line in text.splitlines()]
        lines = [line for line in lines if len(line) >= OVERLAP_MIN_LINE]
        total = sum(map(len, lines))
        shares.append(round(sum(len(line) for line in lines if line in seen) / total, 3) if total else None)
        seen.update(lines)
    return shares


def gate_facts(run_dir: Path | None) -> dict | None:
    """The test stage's base-run and mutation-check records and those that say skipped (fidelity.gates_not_exercised);
    None when the run folder cannot be read."""
    try:
        return fidelity.gates_not_exercised(run_dir)
    except fidelity.Unmeasured:
        return None


def effectiveness(state: dict, out: Path, run_dir: Path | None = None) -> dict:
    """Script facts on whether the stages did their job (the slice verdicts when slice.py wrote them)."""
    history = [row for row in state.get("history") or [] if isinstance(row, dict)]
    order = [row.get("stage") for row in history]
    spec = order.index("test-spec") if "test-spec" in order else None
    build = order.index("implement") if "implement" in order else None
    found = {"stage_outcomes": [{"stage": row.get("stage"), "outcome": row.get("outcome"), "work_item": row.get("workitem")}
                                for row in history],
             "revise_loops": sum(1 for row in history if row.get("outcome") == "revise"),
             "test_spec_before_implement": None if spec is None or build is None else spec < build,
             "gates": gate_facts(run_dir)}
    try:
        found["slice"] = json.loads((out / "slice-result.json").read_text())
    except (OSError, ValueError):
        found["slice"] = None
    return found


def build(out: Path) -> dict:
    out = out.resolve()
    run_dir = find_run_dir(out)
    if run_dir is None:
        raise SystemExit(f"no ShipLoop state.md under {out}")
    state = store.read_record(run_dir / "state.md")
    tool_log = metrics.ToolLog()
    run_metrics = metrics.collect(out, run_dir, tools=tool_log)
    accepted = metrics.stage_results(run_dir, state)
    try:
        pending_action = str(navigator.current_action(state)["id"]) if state.get("status") == "active" else None
    except Exception:  # noqa: BLE001 - a record, never a refusal
        pending_action = None
    by_action = {row["action"]: row for row in accepted if row.get("action")}
    links = improve_links(state)
    texts, archived = emissions(out, run_dir)
    calls = attribute(next_calls(tool_log), accepted, pending_action)
    order = {row["action"]: i for i, row in enumerate(accepted) if row.get("action")}

    def key_order(key: str) -> tuple:
        action, kind = packet_owner(key, links)
        return (order.get(action, len(order)), kind == "improve", key.endswith("bind"))

    keys = sorted(texts, key=key_order)
    shares = overlap_shares([texts[key][-1] for key in keys])
    rows = []
    for key, share in zip(keys, shares):
        action, kind = packet_owner(key, links)
        sent = texts[key]
        last = sent[-1]
        known = by_action.get(action) or {}
        head = metrics.PACKET_STAGE.search(last)
        stage = known.get("stage") if kind == "producer" else None
        if stage is None:
            stage = head.group("stage") if head else None
        if stage == IMPROVE_STAGE:  # the Improve stage's own packet: it reviews the stage that `known` describes
            kind = "improve"
        row = {"packet": key, "action": action, "kind": kind, "stage": stage}
        if kind == "improve":
            row["reviewed_stage"] = known.get("stage")  # None for an old-layout run that has the `-improve` suffix only
            if row["reviewed_stage"] is None and stage != IMPROVE_STAGE:
                row["reviewed_stage"] = stage
        rows.append({**row, "work_item": known.get("work_item"), "outcome": known.get("outcome"),
                     "emissions": len(sent), "chars": len(last), "est_tokens": len(last) // 4,
                     "chars_all_emissions": sum(map(len, sent)), "repeated_share": share,
                     "next_calls": None if kind == "improve" else calls.get(action, 0),
                     "sections": sections(last), **references(last)})
    usage = run_metrics.get("tool_use") or {}
    used = usage.get("packets") if isinstance(usage, dict) else None
    read = (used or {}).get("read") or {}
    # What reached the model (Claude's tool blocks only; None on other hosts): the printed heads, whole or partial packet
    # files opened with a read tool, and packet files printed through the shell.
    reached = None if not used else {
        "printed_chars": (used.get("printed") or {}).get("chars"),
        "read_tool_chars": sum(r.get("chars") or 0 for r in read.get("read_tool") or []),
        "read_tool_packets": len(read.get("read_tool") or []),
        "shell_chars": (read.get("shell") or {}).get("chars")}
    report = {
        "output": str(out), "run_dir": str(run_dir), "status": state.get("status"),
        "emissions_source": "packet-archive (every distinct emission a 2-s poll saw)" if archived
                            else "retained only (run/packets keeps the last copy of each packet)",
        "token_estimate": ESTIMATE,
        "totals": {"packets": len(rows), "emissions": sum(r["emissions"] for r in rows),
                   "chars_written": sum(r["chars_all_emissions"] for r in rows),
                   "est_tokens_written": sum(r["chars_all_emissions"] for r in rows) // 4,
                   "reached_model": reached,
                   "next_calls": sum(calls.values()), "shiploop_failures": len(run_metrics.get("shiploop_failures") or []),
                   "model_glue": len(run_metrics.get("model_glue") or []), "turns": run_metrics.get("turns"),
                   "cost_usd": run_metrics.get("cost_usd"),
                   "cost_unmeasured": None if run_metrics.get("cost_usd") is not None else
                   "no session reported a cost (a session the slice stop ends never writes its result event)"},
        "packets": rows,
        "stages": run_metrics.get("stages") or [],
        "effectiveness": effectiveness(state, out, run_dir),
    }
    return report


def _walk(case: dict, delegation: str, temp: str, run_dir: Path):
    """Yield (key, state read back from state.md) for every packet of one step case's inner loop.

    A `-improve` key is the packet of the Improve stage that follows `<stage>`; the pure functions take the reviewed
    action id (`finish_improve`), the Improve stage's own id is only what its packet names.  The caller renders each
    state before it asks for the next: the walk goes on from it.

    Synthetic results throughout (no model, no project work): the plan's only item is the case's work item and the
    step plan records the case's first check as its test command.
    """
    count = 0

    def cold(current: dict) -> dict:
        store.write_record(run_dir / "state.md", current)
        cold_state = store.read_record(run_dir / "state.md")
        # What `emit` does before it prints: the inner action's loop contract is written, so the packet's loop block
        # is the one a run prints (without the file it would end with "The loop contract is missing").
        if cold_state["status"] == "active" and not cold_state.get("active_improve"):
            try:
                for relative, text in loops.contract_writes(run_dir, cold_state).items():
                    store.atomic_write_text(run_dir / relative, text)
            except loops.LoopError:
                pass  # as emit: the invoke block says the contract is unavailable
        return cold_state

    state = navigator.new_state(temp, case["prompt"], delegation=delegation)
    for _ in range(200):
        stage = navigator.current_stage(state)
        if state["status"] != "active" or stage in stage_spec.OUTER:
            break
        action = navigator.current_action(state)
        inner = stage in stage_spec.INNER
        if inner:
            count += 1
            yield f"{count:02d}-{stage}", cold(state)
        extra: dict = {}
        if stage == "plan":
            extra["work_items"] = [case["work_item"]]
        if stage == "step-plan":
            extra["test_commands"] = [{"command": case["checks"][0], "suite": "focused"}]
        waiting = navigator.apply(state, action["id"], {"outcome": "done", "summary": "Synthetic", **extra})
        if waiting.get("active_improve") is not None:
            if inner:
                count += 1
                yield f"{count:02d}-{stage}-improve", cold(waiting)
            waiting = navigator.finish_improve(waiting, action["id"], {"summary": "Synthetic review", "lessons": "Synthetic lessons."})
        state = waiting


def offline_packets(case: dict, delegation: str = "inline", printed: bool = False, measure_for: Any = None) -> dict[str, str]:
    """{"<nn>-<stage>[-improve]": packet text} for one step case's inner loop, rendered from a cold read of state.md.

    ``printed`` gives what `emit` prints for a packet over the limit (its head) instead of the packet file's text.  The text
    carries this machine's temporary directory and this checkout's paths; offline_renders gives the fixed text.
    ``measure_for(work directory)`` returns the length function the limits are judged by (default ``len``): a test that
    compares lengths at a reference install passes ``shiploop_head_budget.reference_measure``.
    """
    found: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="shiploop-step-packets-") as temp:
        run_dir = Path(temp) / "run"
        run_dir.mkdir()
        measure = measure_for(temp) if measure_for else len
        for key, cold_state in _walk(case, delegation, temp, run_dir):
            text = navigator.render(None, run_dir, cold_state)
            if printed and measure(text) > navigator.PRINT_LIMIT and cold_state["status"] == "active":
                # What emit prints for a packet over the limit: the head, with the rest in the file.
                text = navigator.packet_head(None, run_dir, cold_state, run_dir / "packets" / "packet.md", measure=measure)
            found[key] = text
    return found


# --- fixed-text renders (--text-dir) -------------------------------------------------------------------------------

# A plugin-cache install root ("/Users/<name>/.claude/plugins/cache/whichguy/skill-craft/2.5.0", 63 characters): the CLI
# under it, "<root>/skills/shiploop/scripts/shiploop", is the 96 characters the plan's normal install prints.
INSTALL_ROOT_LENGTH = 63
TEXT_FORMAT = 1  # bump when the fixed strings below change: render_diff refuses to compare renders of two formats
CLI_TAIL = "/scripts/shiploop"
PACKAGE_TAIL = "/skills/shiploop"
CANONICAL_PYTHON = "/usr/bin/python3"
# The fixed roots (under /home so that packet_anatomy's path statistics count them as the absolute paths they stand for).
INSTALL_BASE, WORK_BASE = "/home/install", "/home/render"
HOST_CUT = 20_000  # the characters of shell output some hosts keep (navigator.PRINT_LIMIT's comment): Grok, 2026-09-27


def padded_path(base: str, length: int, fill: str = "p") -> str:
    """`base` extended with components of `fill` (at most 40 characters each) to exactly `length` characters.  No file is touched."""
    path = str(base)
    room = length - len(path)
    if room == 0:
        return path
    if room < 2:
        raise SystemExit(f"cannot make a path of {length} characters under {path!r} ({len(path)} characters): "
                         "give TMPDIR a shorter directory or ask for a longer path")
    while room:
        width = min(40, room - 1)
        if room - 1 - width == 1:  # a one-character gap cannot be filled by any component
            width -= 1
        path += "/" + fill * width
        room -= 1 + width
    return path


@contextlib.contextmanager
def _fixed_ids():
    """uuid.uuid4 gives a sequence derived from a counter while it runs: the ids a packet prints are the same in every render."""
    counter = iter(range(1, 1_000_000))
    real = uuid.uuid4
    uuid.uuid4 = lambda: uuid.UUID(bytes=hashlib.sha256(b"offline-render-%d" % next(counter)).digest()[:16], version=4)
    try:
        yield
    finally:
        uuid.uuid4 = real


class _Canon:
    """Replace what differs between machines and checkouts with fixed strings (of the lengths a normal install has)."""

    def __init__(self, work: Path, package: Path | None, root_length: int, scratch: Path):
        install = padded_path(INSTALL_BASE, root_length, "i")
        pairs = [(str(ROOT), install), (sys.executable, CANONICAL_PYTHON),
                 (str(work), padded_path(WORK_BASE, len(str(work)), "w"))]
        if package is not None:
            pairs.append((str(package), install + PACKAGE_TAIL))
        self.pairs = sorted(pairs, key=lambda pair: -len(pair[0]))
        # What must not survive: the paths of this machine (a fixed string that equals one of them, an interpreter at
        # /usr/bin/python3 say, is not a leak).  The temporary directory itself is not listed: "never /tmp" is packet text.
        fixed_strings = {fixed for _, fixed in pairs}
        self.leaks = [item for item in (str(scratch), str(work), str(ROOT), sys.executable) if item not in fixed_strings]

    def __call__(self, text: str) -> str:
        for real, fixed in self.pairs:
            text = text.replace(real, fixed)
        leaked = [item for item in self.leaks if item and item in text]
        if leaked:
            raise SystemExit(f"a packet still prints {leaked[0]!r} after the fixed text was applied: extend packets._Canon")
        return text


def offline_renders(case: dict, delegation: str = "inline", *, run_dir_length: int | None = None,
                    cli_path_length: int | None = None, walk: Any = None) -> dict[str, dict]:
    """{key: {"whole": the packet file's text, "printed": what emit prints (ending with HEAD_END), "head": printed is a
    head, "state": the state it rendered}} with fixed text.  ``walk`` replaces the default walk (``_walk``): a generator
    of ``(key, state read back from state.md)``, called as ``walk(case, delegation, work, run_dir)``.

    ``run_dir_length`` is the exact length of the run directory the packets name (default: this machine's temporary
    directory, as offline_packets); ``cli_path_length`` the exact length of the CLI path they print (default: the bare
    `shiploop`).  The ids are derived from a counter and the checkout root and the interpreter print as fixed strings, so
    two renders of one tree are the same text whatever the temporary directory and the checkout path.  Whether a packet prints whole or as a
    head is decided on that text.
    """
    package_real = Path(navigator.__file__).resolve().parents[1]
    root_length = INSTALL_ROOT_LENGTH if cli_path_length is None else cli_path_length - len(PACKAGE_TAIL + CLI_TAIL)
    with contextlib.ExitStack() as stack:
        scratch = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix="sl-")))
        stack.enter_context(_fixed_ids())
        if run_dir_length is None:
            work = Path(tempfile.mkdtemp(prefix="shiploop-step-packets-"))
            stack.callback(shutil.rmtree, work, ignore_errors=True)
        else:
            work = Path(padded_path(str(scratch), run_dir_length - len("/run"), "p"))
            work.mkdir(parents=True)
        run_dir = work / "run"
        run_dir.mkdir()
        core, package = None, None
        if cli_path_length is not None:
            package = Path(padded_path(str(scratch), cli_path_length - len(CLI_TAIL), "c"))
            package.parent.mkdir(parents=True, exist_ok=True)
            package.symlink_to(package_real, target_is_directory=True)  # the references stay the checkout's own files
            core = types.SimpleNamespace(PACKAGE_ROOT=package)
        canon = _Canon(work, package, root_length, scratch)
        found: dict[str, dict] = {}
        def at_install(text: str) -> int:
            """The length a text has at the stated install: the limits are decided on it, not on this machine's paths."""
            return len(canon(text))

        for key, cold_state in (walk or _walk)(case, delegation, str(work), run_dir):
            real = navigator.render(core, run_dir, cold_state)
            printed = navigator.printed_text(core, run_dir, cold_state, run_dir / "packets" / "packet.md", real,
                                             measure=at_install)
            found[key] = {"whole": canon(real), "printed": canon(printed), "state": cold_state,
                          "head": at_install(real) > navigator.PRINT_LIMIT and cold_state["status"] == "active"}
        run_dir_chars = len(str(run_dir))
    for row in found.values():
        row["run_dir_length"] = run_dir_chars
    return found


def _source_facts() -> dict:
    """The commit this checkout is at and whether tracked files differ from it (None when git cannot say)."""
    def git(*args: str) -> str | None:
        try:
            done = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        return done.stdout.strip() if done.returncode == 0 else None

    head = git("rev-parse", "HEAD")
    changed = git("status", "--porcelain", "--untracked-files=no")
    return {"commit": head, "dirty": None if changed is None else bool(changed)}


def write_text_dir(out: Path, name: str, delegation: str, renders: dict[str, dict], cli_path_length: int | None) -> dict:
    """Write each render as `<key>.printed.txt` and `<key>.whole.txt` and `manifest.json`; return the manifest."""
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty: render into a fresh directory (render_diff compares two of them)")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for key, row in renders.items():
        (out / f"{key}.printed.txt").write_text(row["printed"], encoding="utf-8")
        (out / f"{key}.whole.txt").write_text(row["whole"], encoding="utf-8")
        improve = key.endswith("-improve")
        rows.append({"key": key, "stage": key.split("-", 1)[1], "kind": "improve" if improve else "producer",
                     "whole": len(row["whole"]), "printed": len(row["printed"]), "head": row["head"]})
    lengths = {row["run_dir_length"] for row in renders.values()}
    manifest = {"tool": "test/shiploop_e2e/packets.py --offline", "text_format": TEXT_FORMAT, "case": name, "delegation": delegation,
                "run_dir_length": lengths.pop() if len(lengths) == 1 else None, "cli_path_length": cli_path_length,
                "install_root_length": INSTALL_ROOT_LENGTH if cli_path_length is None
                else cli_path_length - len(PACKAGE_TAIL + CLI_TAIL),
                "python": CANONICAL_PYTHON, "print_limit": navigator.PRINT_LIMIT, "host_cut": HOST_CUT,
                "source": _source_facts(), "packets": rows}
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def render_text_summary(manifest: dict) -> str:
    where = (f"run dir {manifest['run_dir_length']}, CLI "
             f"{manifest['cli_path_length'] if manifest['cli_path_length'] is not None else 'bare'}")
    lines = [f"# Offline text render: {manifest['case']} ({manifest['delegation']}; {where})", "",
             f"Printed text is a head when the packet passes {manifest['print_limit']} characters; the host cut is about "
             f"{manifest['host_cut']}.", "",
             "| packet | whole | printed | form | printed to host cut |", "|---|--:|--:|---|--:|"]
    for row in manifest["packets"]:
        lines.append(f"| {row['key']} | {row['whole']} | {row['printed']} | {'head' if row['head'] else 'whole'} "
                     f"| {manifest['host_cut'] - row['printed']} |")
    return "\n".join(lines) + "\n"


def offline_report(name: str, case: dict, delegation: str = "inline") -> dict:
    texts = offline_packets(case, delegation)
    keys = list(texts)
    # An Improve packet is the Improve stage's own: its stage is `improve`, and `reviewed_stage` is the stage it reviews.
    rows = [{"packet": key, "stage": IMPROVE_STAGE if key.endswith("-improve") else key.split("-", 1)[1],
             "reviewed_stage": key.split("-", 1)[1].removesuffix("-improve") if key.endswith("-improve") else None,
             "kind": "improve" if key.endswith("-improve") else "producer", "chars": len(texts[key]),
             "est_tokens": len(texts[key]) // 4, "repeated_share": share, "sections": sections(texts[key]),
             **references(texts[key])}
            for key, share in zip(keys, overlap_shares([texts[key] for key in keys]))]
    return {"case": name, "delegation": delegation, "offline": True, "token_estimate": ESTIMATE,
            "totals": {"packets": len(rows), "chars": sum(r["chars"] for r in rows),
                       "est_tokens": sum(r["chars"] for r in rows) // 4},
            "packets": rows}


def render_offline(report: dict) -> str:
    t = report["totals"]
    lines = [f"# Offline packets: {report['case']} ({report['delegation']})", "",
             f"No model: synthetic results on this checkout's navigator. Tokens: {report['token_estimate']}.", "",
             f"- packets {t['packets']}, characters {t['chars']} (~{t['est_tokens']} tokens)", "",
             "| packet | chars | ~tokens | repeated | skill refs | missing | largest sections |", "|---|---|---|---|---|---|---|"]
    for row in report["packets"]:
        big = "; ".join(f"{s['section']} ({s['chars']})" for s in row["sections"][:3])
        lines.append(f"| {row['packet']} | {row['chars']} | {row['est_tokens']} | {_cell(row['repeated_share'])} "
                     f"| {row['skill_references']} | {len(row['missing'])} | {big} |")
    return "\n".join(lines) + "\n"


def _cell(value) -> str:
    return "–" if value is None else f"{value:.0%}" if isinstance(value, float) and value <= 1 else str(value)


def gates_line(gates: dict | None) -> str:
    """One report line on the test stage's gates: which ones wrote a record that says skipped (they did nothing, so this run is
    no evidence about them), or that none did, or that no record exists to say."""
    if gates is None:
        return "Gates not exercised: not measured (the run folder cannot be read)."
    if gates["skipped"]:
        return ("**Gates not exercised:** " + fidelity.gates_phrase(gates["skipped"]) + f" ({len(gates['skipped'])} of "
                f"{gates['records']} base-run and mutation-check records say skipped: the gate wrote a record and did nothing).")
    if gates["records"]:
        return f"Gates not exercised: none ({gates['records']} base-run and mutation-check records, none says skipped)."
    return "Gates not exercised: not measured (no base-run or mutation-check record: the test stage was not reached)."


def render(report: dict) -> str:
    t = report["totals"]
    lines = [f"# Packet report: {report['output']}", "",
             f"Run status **{report['status']}**. Emissions: {report['emissions_source']}. Tokens: {report['token_estimate']}.",
             "", f"- packets {t['packets']}, emissions {t['emissions']}, characters written to packet files "
                 f"{t['chars_written']} (~{t['est_tokens_written']} tokens)",
             *([f"- reached the model: printed heads {_cell(r['printed_chars'])} chars, {r['read_tool_packets']} packet "
                f"file(s) read with a read tool ({r['read_tool_chars']} chars), packet text printed through the shell "
                f"{_cell(r['shell_chars'])} chars"] if (r := t.get("reached_model")) else
               ["- reached the model: not measured on this host"]),
             f"- `next` calls {t['next_calls']}, ShipLoop failures {t['shiploop_failures']}, model glue {t['model_glue']}, "
             f"turns {_cell(t['turns'])}, cost {_cell(t['cost_usd']) if t['cost_usd'] is not None else 'unreported'}", ""]
    slice_result = report["effectiveness"].get("slice")
    if slice_result:
        verdicts = ", ".join(f"{name} {'PASS' if ok else 'FAIL'}" for name, ok in slice_result.get("verdicts", {}).items())
        lines += [f"**Slice {'PASS' if slice_result.get('pass') else 'FAIL'}**: {verdicts}", ""]
    eff = report["effectiveness"]
    lines += [f"Revise loops {eff['revise_loops']}; test-spec before implement: {_cell(eff['test_spec_before_implement'])}.",
              gates_line(eff.get("gates")), "",
              "## Packets", "",
              "| # | stage | kind | outcome | chars | ~tokens | emissions | next | repeated | skill refs | missing | largest section |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, row in enumerate(report["packets"], 1):
        big = row["sections"][0] if row["sections"] else {"section": "–", "chars": 0}
        reviewed = f" ({row['reviewed_stage']})" if row.get("reviewed_stage") else ""
        lines.append(f"| {i} | {row['stage']}{reviewed} | {row['kind']} | {_cell(row['outcome'])} | {row['chars']} | {row['est_tokens']} "
                     f"| {row['emissions']} | {_cell(row['next_calls'])} | {_cell(row['repeated_share'])} "
                     f"| {row['skill_references']} | {len(row['missing'])} | {big['section']} ({big['chars']}) |")
    lines += ["", "## Stages (metrics.py)", "", "| stage | outcome | seconds | turns | tool calls | context peak |",
              "|---|---|---|---|---|---|"]
    for row in report["stages"]:
        peak = (row.get("context") or {}).get("peak")
        lines.append(f"| {row.get('stage')}{' (incomplete)' if row.get('incomplete') else ''} | {_cell(row.get('outcome'))} "
                     f"| {_cell(row.get('seconds'))} | {_cell(row.get('turns'))} | {_cell(row.get('tool_calls'))} | {_cell(peak)} |")
    missing = sorted({path for row in report["packets"] for path in row["missing"]})
    if missing:
        lines += ["", "## Missing skill references", "", *(f"- {path}" for path in missing)]
    return "\n".join(lines) + "\n"


def compare(now: dict, before: dict) -> str:
    """Per-stage and per-packet change from `before` to `now` (the same case before and after an edit, say)."""
    def by_stage(rows, field):
        found: dict[str, float] = {}
        for row in rows:
            if isinstance(row.get(field), (int, float)) and row.get("stage"):
                found[row["stage"]] = found.get(row["stage"], 0) + row[field]
        return found

    lines = [f"# Packet comparison", "", f"- now: {now['output']}", f"- before: {before['output']}", ""]
    for name in ("chars_written", "next_calls", "shiploop_failures", "model_glue", "turns", "cost_usd"):
        a, b = now["totals"].get(name), before["totals"].get(name)
        delta = round(a - b, 2) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else "–"
        lines.append(f"- {name}: {_cell(b)} → {_cell(a)} (Δ {delta})")
    seconds_now, seconds_before = by_stage(now["stages"], "seconds"), by_stage(before["stages"], "seconds")
    turns_now, turns_before = by_stage(now["stages"], "turns"), by_stage(before["stages"], "turns")
    chars_now, chars_before = by_stage(now["packets"], "chars"), by_stage(before["packets"], "chars")
    stages = list(dict.fromkeys([*(r.get("stage") for r in before["stages"]), *(r.get("stage") for r in now["stages"])]))
    lines += ["", "| stage | Δ seconds | Δ turns | Δ packet chars |", "|---|---|---|---|"]
    for stage in stages:
        if not stage:
            continue
        cells = [round(new.get(stage, 0) - old.get(stage, 0), 1) if stage in new or stage in old else "–"
                 for new, old in ((seconds_now, seconds_before), (turns_now, turns_before), (chars_now, chars_before))]
        lines.append(f"| {stage} | " + " | ".join(map(str, cells)) + " |")
    v_now = ((now["effectiveness"].get("slice") or {}).get("verdicts") or {})
    v_before = ((before["effectiveness"].get("slice") or {}).get("verdicts") or {})
    changed = [f"- {name}: {v_before.get(name)} → {v_now.get(name)}" for name in sorted({*v_now, *v_before})
               if v_now.get(name) != v_before.get(name)]
    lines += ["", "## Verdict changes", "", *(changed or ["- none"])]
    return "\n".join(lines) + "\n"


def write_report(out: Path) -> dict:
    report = build(out)
    (out / REPORT_JSON).write_text(json.dumps(report, indent=2) + "\n")
    (out / REPORT_MD).write_text(render(report))
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("output", type=Path, nargs="?", help="an E2E output directory (slice.py or run.py)")
    p.add_argument("--compare", type=Path, help="an earlier output directory to compare this one with")
    p.add_argument("--offline", metavar="CASE", help="render a step case's inner-loop packets with no model")
    p.add_argument("--delegation", choices=("inline", "ask-agent"), default="inline", help="with --offline")
    p.add_argument("--json", action="store_true", help="with --offline: print JSON instead of Markdown")
    p.add_argument("--text-dir", type=Path, metavar="DIR",
                   help="with --offline: write each packet as printed and whole text plus manifest.json into this fresh directory")
    p.add_argument("--run-dir-length", type=int, metavar="N",
                   help="with --text-dir: the exact length of the run directory the packets name (83 is a normal install, 163 the live run)")
    p.add_argument("--cli-path-length", type=int, metavar="N",
                   help="with --text-dir: the exact length of the CLI path the packets print (96 for a plugin-cache install)")
    args = p.parse_args(argv)
    if (args.run_dir_length or args.cli_path_length or args.text_dir) and not args.offline:
        p.error("--text-dir, --run-dir-length and --cli-path-length go with --offline CASE")
    if (args.run_dir_length is not None or args.cli_path_length is not None) and args.text_dir is None:
        p.error("--run-dir-length and --cli-path-length go with --text-dir")
    if args.text_dir is not None and args.json:
        p.error("--text-dir writes files and prints a table; --json is the other report")
    if args.run_dir_length is not None and args.run_dir_length < 20:
        p.error("--run-dir-length is a path of at least 20 characters")
    if args.cli_path_length is not None and args.cli_path_length < len(PACKAGE_TAIL + CLI_TAIL) + 16:
        p.error("--cli-path-length is a path of at least 49 characters")
    if args.offline:
        cases = json.loads((HERE / "step_cases.json").read_text())
        if args.offline not in cases or args.offline.startswith("_"):
            raise SystemExit(f"unknown step case {args.offline!r}")
        if args.text_dir is not None:
            renders = offline_renders(cases[args.offline], args.delegation, run_dir_length=args.run_dir_length,
                                      cli_path_length=args.cli_path_length)
            print(render_text_summary(write_text_dir(args.text_dir.expanduser().resolve(), args.offline, args.delegation,
                                                     renders, args.cli_path_length)), end="")
            return 0
        report = offline_report(args.offline, cases[args.offline], args.delegation)
        print(json.dumps(report, indent=2) if args.json else render_offline(report), end="\n" if args.json else "")
        return 0
    if args.output is None:
        p.error("an output directory, or --offline CASE")
    out = args.output.expanduser().resolve()
    report = write_report(out)
    print(render(report), end="")
    if args.compare:
        earlier = args.compare.expanduser().resolve()
        before = (json.loads((earlier / REPORT_JSON).read_text()) if (earlier / REPORT_JSON).is_file()
                  else write_report(earlier))
        text = compare(report, before)
        (out / COMPARE_MD).write_text(text)
        print("\n" + text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
