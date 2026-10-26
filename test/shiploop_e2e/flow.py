#!/usr/bin/env python3
"""The sequence of one E2E run, for the flow viewer: each packet ShipLoop sent, what the model saw, and what it did.

    python3 test/shiploop_e2e/flow.py <output>                       # writes <output>/flow.json and <output>/flow.html
    python3 test/shiploop_e2e/flow.py --bundle viewer.html <output>...  # one page that browses several runs

`flow.json` (schema `FLOW_VERSION`) is built from the run's files only:
- state.md history, which gives the actions in the order the graph took them;
- ShipLoop's run trace (RUN/trace.jsonl, shiploop 1.12.0 and later): every packet as sent (packets/sent/), each print and
  reprint, each refused command with its text, each keepalive stop decision with the text it put into the turn;
- for a run before the trace, the packet archive (slice.py) or run/packets (a full run keeps only each packet's last copy);
- the host's event stream, for what the model did: its text, calls, results and turns.

`sources` in flow.json names the file each of those came from, so a run read from the trace and one read from the stream
are never mistaken for each other.

Each action has one phase. The Improve stage is an action of its own (stage `improve`, its own id and packet file), listed
after the action it reviews and linked to it (`reviewed`, `reviewed_stage`); its phase has kind `improve`. A saved run of
the older layout has the Improve child's packet beside the producer's (`<action>-improve.md`): its action keeps two
phases, the producer and the Improve child. A phase holds:
- the packet: its text, size and largest sections;
- the head the model received, as printed in a tool result;
- how the model opened the packet file, if it did;
- the model's own events.

On Claude, the events are its text, tool calls and tool results, and hook messages. An event belongs to the action
named by the last packet head the model had received, which is exact, because each `complete` call prints the next
head. Other hosts' streams give tool calls only (metrics.ToolLog), attributed by ShipLoop's acceptance times. A traced run
adds ShipLoop's own events, attributed by the trace (the action the command named, or the one current when it ran): each
refusal (kind `refusal`, with its text) and each keepalive stop decision (kind `keepalive`), placed among the host's events
by time (both clocks are epoch seconds), or at the end of their phase when the stream has no times.

Text the host put into the conversation (Claude writes an invoked skill's body as a `user` message) is an event of kind
`injected`, never the model's `say`.

`--read-first <output>` prints the owner page's "Read first" panel as JSON (``read_first``): ShipLoop commands run (literal,
variable-built, piped, cut by a pipe with the median N kept, status displays fired), per producer stage the characters written
against those seen after any pipe and whether the packet file was opened, per stage seconds, turns and context, gates run
against skipped, refusals by stage and cause (from the trace where it covers the run, else from the stream's refusal lines),
the trace's packets, reprints and keepalive continuations, whether the item was committed, skills invoked, the staleness of the
recording against the repository, and what the run cannot show. Each figure names the file it comes from. It writes nothing;
`owner_page.py` turns it into the page.

Calls are flagged by script, never by a model:
- a script the model wrote to drive ShipLoop or Improve (`defines-script`) and every run of it (`runs-script`);
- a self-reported trivial Until Loop pass (`trivial-pass`);
- a scripted review: a review file a model-written script writes, so its text is fixed before anything is checked
  (`scripted-review`).

`flow_viewer.html` is the template: `--bundle` inlines any number of flow.json files into one self-contained page, and
the page also opens flow.json files by drag and drop. The page opens one action at `#action=<nav id>` (the run's Review
page links each visit there), and its header links to that Review page when the run's folder had one (`review_page`).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills/shiploop/scripts"))
sys.path.insert(0, str(HERE))
import metrics  # noqa: E402
import packets  # noqa: E402
import run_trace  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_store as store  # noqa: E402

FLOW_VERSION = 2  # 2: the Improve stage is an action row of its own (`reviewed`, `reviewed_stage`); version 1 files still open.
# `clear` is a list, one entry per clear of the run (several clears per slice); a flow written before that holds an object or null there,
# which the viewer shows as no clear.
TEMPLATE = HERE / "flow_viewer.html"
REVIEW_PAGE = "review-export/run-review.html"  # the run's Review page (skills/shiploop-run-review export.py), from its folder
DATA_MARK = "<!--FLOW-RUNS-->"
HEAD = re.compile(r"ShipLoop navigator \| (?P<stage>[\w-]+) \| revision (?P<rev>\d+)")
ACTION = re.compile(r"--action=(nav-[0-9a-f]{32})")
ANY_ACTION = re.compile(r"(nav-[0-9a-f]{32})")
PACKET_FILE = re.compile(r"packets/(nav-[0-9a-f]{32}(?:-improve(?:-bind)?|-bind)?)\.md")
# An Improve packet's head, old layout: the producer's stage with `| Improve` or an improve-* verb in its first lines. New layout:
# stage `improve` (a worktree path that merely contains "improve-" is not a sign).
OLD_IMPROVE_HEAD = re.compile(r"\| Improve\b|Current action: Improve|improve-(?:bind|start|complete)\b")
SCRIPT_DEF = re.compile(r"cat\s+>\s*(\S+\.sh)\s+<<|(\w+)\(\)\s*\{")
TRIVIAL = re.compile(r'\\?"classification\\?"\s*:\s*\\?"trivial')
REVIEW_FILE = re.compile(r"cat\s+>\s*\S*reviews/review-\d+\.md\s+<<")
STATUS_END = "=== end ShipLoop status ==="
# The closing line of every print since R4 of the run-5 batch (2026-10-24); from 2026-10-16 to then it was HEAD_END_UNTIL_R4,
# and older heads end at the status block.
HEAD_END = "=== end ShipLoop print ==="
HEAD_END_UNTIL_R4 = "=== end ShipLoop head ==="
# Either name, as a line: the packet's second pointer line names it inside a sentence, near the top of every print, cut or not.
HEAD_END_LINE = re.compile(r"^(?:" + re.escape(HEAD_END) + "|" + re.escape(HEAD_END_UNTIL_R4) + r")$", re.M)
CALL_LIMIT, RESULT_LIMIT, TEXT_LIMIT = 6000, 6000, 4000


class Shortener:
    """Long absolute paths shortened to labels the page can show (the labels are listed in flow.json)."""

    def __init__(self, out: Path, run_dir: Path):
        worktree = run_dir.parent / "worktree"
        self.pairs = [(str(run_dir), "<run>"), (str(worktree), "<worktree>"),
                      (str(out / "build/plugins/skill-craft/skills"), "<skills>"), (str(out), "<out>")]

    def __call__(self, text: str) -> str:
        for path, label in self.pairs:
            text = text.replace(path, label)
        return text

    def legend(self) -> dict:
        return {label: path for path, label in self.pairs}


def clip(text: str, limit: int, short: Shortener) -> dict:
    return {"text": short(text[:limit]), "chars": len(text), "clipped": len(text) > limit}


def call_flags(body: str, scripts: dict[str, bool]) -> list[str]:
    """`scripts` maps each script the model defined so far to whether its body writes a review file."""
    flags = []
    defined = [Path(a or b).name for a, b in SCRIPT_DEF.findall(body)]
    for name in defined:
        scripts[name] = bool(REVIEW_FILE.search(body))
        flags.append(f"defines-script:{name}")
    ran = [name for name in sorted(scripts) if name not in defined
           and re.search(rf"(?<![\w.]){re.escape(name)}(?![\w])", body)]
    flags += [f"runs-script:{name}" for name in ran]
    # A review the script writes is the same text whatever it reviews: written before anything is checked.
    if any(scripts.get(name) for name in [*defined, *ran]):
        flags.append("scripted-review")
    if TRIVIAL.search(body):
        flags.append("trivial-pass")
    return flags


def packet_texts(out: Path, run_dir: Path) -> tuple[dict[str, str], dict[str, int], str]:
    texts, source = packets.emissions(out, run_dir)
    return {k: v[-1] for k, v in texts.items()}, {k: len(v) for k, v in texts.items()}, source


def trace_items(traced: dict, short: Shortener, started: float | None) -> list[dict]:
    """ShipLoop's own events from its run trace, as flow items: each refused command (kind `refusal`, with its text) and each
    keepalive stop decision (kind `keepalive`), on the host stream's clock when it has one (`t` None otherwise). `ts` is the
    trace's own epoch stamp."""
    def at(ts) -> float | None:
        return round(ts - started, 1) if started is not None and isinstance(ts, (int, float)) else None

    items = []
    for failure in traced["failures"]:
        items.append({"kind": "refusal", "source": "trace", "t": at(failure["ts"]), "ts": failure["ts"], "line": None,
                      "trace_line": failure["i"],
                      "action": failure["action"], "improve": False, "verb": failure["verb"], "exit": failure["exit"],
                      "check_only": failure["check_only"], "stage": failure["stage"],
                      "body": clip(failure["text"] or run_trace.NO_TEXT, TEXT_LIMIT, short)})
    for hook in traced["hooks"]:
        items.append({"kind": "keepalive", "source": "trace", "t": at(hook["ts"]), "ts": hook["ts"], "line": None,
                      "trace_line": hook["i"],
                      "action": hook["action"], "improve": False, "decision": hook["decision"], "why": hook["why"],
                      "body": clip(hook["text"] or "", TEXT_LIMIT, short)})
    return items


def by_time(items: list[dict], extra: list[dict], epoch) -> list[dict]:
    """``items`` (the host's, in stream order) with ``extra`` (trace items) placed among them: each before the first stream item
    stamped later than it, an untimed one at the end. ``epoch(item)`` is a stream item's arrival stamp (None when unknown);
    the comparison is on the unrounded stamps, since a command, its trace line and its result often fall within 0.1 s. The
    stream's own order is never changed."""
    known = [e["t"] is not None and isinstance(e.get("ts"), (int, float)) for e in extra]
    timed = sorted((e for e, ok in zip(extra, known) if ok), key=lambda e: e["ts"])
    merged, j = [], 0
    for item in items:
        stamp = epoch(item)
        while j < len(timed) and stamp is not None and timed[j]["ts"] < stamp:
            merged.append(timed[j])
            j += 1
        merged.append(item)
    return merged + timed[j:] + [e for e, ok in zip(extra, known) if not ok]


def claude_items(out: Path, short: Shortener, first_action: str | None) -> tuple[list[dict], dict, dict, float | None]:
    """Claude's stream: text, calls, results and hook messages, each attributed to the action of the last head seen."""
    stamps = {}
    for row in (out / "timeline.jsonl").read_text().splitlines() if (out / "timeline.jsonl").is_file() else []:
        try:
            r = json.loads(row)
            stamps[r["line"]] = r["t"]
        except (ValueError, KeyError):
            continue
    t0 = min(stamps.values()) if stamps else 0.0
    current = {"action": first_action, "improve": False}
    items, heads, reads, scripts = [], {}, {}, {}
    for number, raw in enumerate((out / "events.jsonl").read_text().splitlines()):
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        t = round(stamps.get(number, t0) - t0, 1)
        kind = event.get("type")
        if kind == "system" and event.get("subtype") == "informational":
            items.append({"kind": "hook", "t": t, "line": number, **current, "body": clip(event.get("content", ""), 1500, short)})
            continue
        if kind not in ("assistant", "user") or not isinstance((event.get("message") or {}).get("content"), list):
            continue
        for block in event["message"]["content"]:
            if block.get("type") == "text" and block.get("text", "").strip():
                # Text in a `user` event is the host's, not the model's: Claude puts an invoked skill's body there.
                said = "say" if kind == "assistant" else "injected"
                items.append({"kind": said, "t": t, "line": number, **current, "body": clip(block["text"], TEXT_LIMIT, short)})
            elif block.get("type") == "tool_use":
                call = block.get("input") or {}
                body = call.get("command") or call.get("file_path") or json.dumps(call)
                for key in sorted(set(PACKET_FILE.findall(body))):
                    whole = block.get("name") == "Read" and "offset" not in call and "limit" not in call
                    reads.setdefault(key, []).append("read tool, whole file" if whole else (
                        "read tool, part" if block.get("name") == "Read" else
                        "shell, " + next((w for w in ("grep", "sed", "head", "tail", "cat") if w in body), "other")))
                items.append({"kind": "call", "t": t, "line": number, **current, "tool": block.get("name"),
                              "body": clip(body, CALL_LIMIT, short), "flags": call_flags(body, scripts),
                              "reads_packets": sorted(set(PACKET_FILE.findall(body)))})
            elif block.get("type") == "tool_result":
                content = block.get("content")
                content = content if isinstance(content, str) else "\n".join(
                    part.get("text", "") for part in content or [] if isinstance(part, dict))
                items.append({"kind": "result", "t": t, "line": number, **current, "body": clip(content, RESULT_LIMIT, short)})
                for match in HEAD.finditer(content):
                    tail = content[match.start():]
                    found = ACTION.search(tail[:3000]) or ANY_ACTION.search(tail[:3000])
                    if not found:
                        continue
                    # New layout: an `improve` head names the Improve stage's own id, so it is an ordinary action key.
                    improve = match.group("stage") != navigator.IMPROVE_STAGE and bool(OLD_IMPROVE_HEAD.search(tail[:400]))
                    key = found.group(1) + ("-improve" if improve else "")
                    end = content.find(STATUS_END, match.start())
                    closing_line = HEAD_END_LINE.search(content, match.start())
                    closing = closing_line.start() if closing_line else -1
                    stop = closing_line.end() if closing > 0 else end + len(STATUS_END) if end > 0 else len(content)
                    heads.setdefault(key, short(content[match.start(): stop]))
                    current = {"action": found.group(1), "improve": improve}
    return items, heads, reads, (t0 if stamps else None)


def toollog_items(out: Path, run_dir: Path, short: Shortener, order: list[str],
                  accepted_t: dict) -> tuple[list[dict], float | None]:
    """Other hosts: calls only, each attributed to the first action accepted at or after it; and the epoch their times count
    from (None when no call has a time)."""
    log = metrics.ToolLog()
    metrics.collect(out, run_dir, tools=log)
    timed = [(accepted_t.get(a), a) for a in order if accepted_t.get(a) is not None]
    items, scripts = [], {}
    starts = [row["t"] for row in log.sequence if row.get("t") is not None]
    t0 = min(starts) if starts else 0.0
    for row in log.sequence:
        t = row.get("t")
        owner = next((a for at, a in timed if t is not None and at >= t), order[-1] if order else None)
        body = str(row.get("command") or "")
        items.append({"kind": "call", "t": round((t or t0) - t0, 1), "action": owner, "improve": False,
                      "tool": row.get("tool"), "body": clip(body, CALL_LIMIT, short), "flags": call_flags(body, scripts),
                      "reads_packets": sorted(set(PACKET_FILE.findall(body)))})
    return items, (t0 if starts else None)


def build(out: Path) -> dict:
    out = out.resolve()
    run_dir = packets.find_run_dir(out)
    if run_dir is None:
        raise SystemExit(f"no ShipLoop state.md under {out}")
    short = Shortener(out, run_dir)
    state = store.read_record(run_dir / "state.md")
    accepted = state.get("accepted") or {}
    history = [h for h in state.get("history") or [] if isinstance(h, dict) and h.get("action")]

    def seeded(action: str) -> bool:
        action = reviewed_by.get(action, action)
        record = accepted.get(action) or {}
        result = record.get("result", record) if isinstance(record, dict) else {}
        return str((result or {}).get("summary", "")).startswith("Synthetic")

    links = packets.improve_links(state)  # {Improve stage id: reviewed action}
    reviewed_by = dict(links)
    improve_of = {reviewed: stage_id for stage_id, reviewed in links.items()}
    order = []
    for h in history:
        order.append(h["action"])
        if h["action"] in improve_of:
            order.append(improve_of[h["action"]])  # the Improve stage ran after its reviewed action and before its accept
    by_action = {h["action"]: h for h in history}
    stamps = {row["action"]: row["t"] for row in metrics.stage_results(run_dir, state) if row.get("action")}
    texts, emissions, source = packet_texts(out, run_dir)
    traced = run_trace.read(run_dir)
    traced_ok = bool(traced) and "error" not in traced
    sends = traced["packets"] if traced_ok else {}
    claude = (out / "events.jsonl").is_file() and '"tool_use"' in (out / "events.jsonl").read_text()[:2_000_000]
    try:
        pending = str(navigator.current_action(state)["id"]) if state.get("status") == "active" else None
        pending_stage = navigator.current_stage(state) if pending else None
    except Exception:  # noqa: BLE001 - a record, never a refusal
        pending, pending_stage = None, None
    child = state.get("active_improve") if isinstance(state.get("active_improve"), dict) else None
    if pending is not None and child and isinstance(child.get("improve_action"), str):
        # The run stands at an Improve stage: the cursor still names the reviewed action; the stage is the Improve one.
        order.extend(a for a in (pending, child["improve_action"]) if a not in order)
        pending, pending_stage = child["improve_action"], packets.IMPROVE_STAGE
    # Events before the first head belong to the first live action: accepted already, or the one the run is at.
    first_live = next((a for a in order if not seeded(a)), pending)
    if claude:
        items, heads, reads, started = claude_items(out, short, first_live)
        clock = started
    else:
        (items, clock), heads, reads = toollog_items(out, run_dir, short, order, stamps), {}, {}
        started = metrics.span(out / "timeline.jsonl").get("started") if (out / "timeline.jsonl").is_file() else None
    if traced_ok and (traced["failures"] or traced["hooks"]):
        arrived = metrics.timeline(out / "timeline.jsonl")
        items = by_time(items, trace_items(traced, short, clock), lambda item: arrived.get(item["line"]) if claude else (
            clock + item["t"] if clock is not None and item.get("t") is not None else None))
    # The action the run stopped in is named by a head (or an event), not yet in history.
    # A head the model cut short (it piped `complete` through tail) names nothing, so the ledger's current action is added too.
    for action in [*(i["action"] for i in items), *(k.removesuffix("-improve") for k in heads), pending]:
        if action and action not in order:
            order.append(action)
    actions = []
    for index, action in enumerate(order):
        reviewed = reviewed_by.get(action)  # set only for an Improve stage's own id
        h = by_action.get(reviewed or action, {})
        stage = packets.IMPROVE_STAGE if reviewed else h.get("stage")
        if stage is None:
            found = HEAD.search(texts.get(action, "") or texts.get(action + "-improve", ""))
            # The ledger's current action has no history row and may have no packet yet: a slice stop that lands between
            # the host saving the state and its `next` writing the packet.  The ledger still names its stage.
            stage = found.group("stage") if found else pending_stage if action == pending and pending_stage else "?"
        if reviewed:
            # The Improve stage: one phase, its packet (the bind packet when no card was ever bound), linked to the reviewed action.
            candidates = [(action, "improve", False)]
        else:
            candidates = [(action, "producer", False), (action + "-improve", "improve", True)]
        phases = []
        for key, kind, legacy in candidates:
            mine = [i for i in items if i["action"] == action and i["improve"] == legacy]
            text_key = key if key in texts else f"{key}-bind" if f"{key}-bind" in texts else key
            if text_key not in texts and not mine and not (sends.get(action) and not legacy):
                continue
            text = texts.get(text_key, "")
            times = [i["t"] for i in mine if i["t"] is not None]
            sent = [] if legacy else sends.get(action, [])
            phases.append({
                "kind": kind, "key": key,
                "packet": {"text": short(text), "chars": len(text), "emissions": emissions.get(text_key, 0),
                           # Each print of this packet, from the trace (None where it recorded none, as for a run before it):
                           # a reprint repeats an earlier text.
                           "prints": len(sent) if sent else None,
                           "reprints": sum(1 for x in sent if x.get("repeat")) if sent else None,
                           "sends": [{k: x.get(k) for k in ("at", "rev", "chars", "printed", "whole", "repeat", "file")}
                                     for x in sent],
                           "sections": packets.sections(text, top=12), **packets.references(text)},
                "head": heads.get(key) or heads.get(f"{key}-bind"), "head_chars": len(heads.get(key) or heads.get(f"{key}-bind") or ""),
                "reads": [*reads.get(key, []), *reads.get(f"{key}-bind", [])],
                "events": mine, "calls": sum(1 for i in mine if i["kind"] == "call"),
                # None for a run before the trace: there a refusal is an unmarked result, so 0 would be a guess.
                "refusals": sum(1 for i in mine if i["kind"] == "refusal" and not i["check_only"]) if traced_ok else None,
                "span_seconds": round(max(times) - min(times), 1) if times else None,
                "flags": sorted({f for i in mine if i["kind"] == "call" for f in i["flags"]}),
            })
        row = {"index": index, "action": action, "stage": stage, "outcome": h.get("outcome"),
               "work_item": h.get("workitem"), "seeded": seeded(action), "accepted": (reviewed or action) in by_action,
               "phases": phases}
        if reviewed:  # the Improve stage's accept is the reviewed action's: its `complete` imports the review
            row.update({"reviewed": reviewed, "reviewed_stage": h.get("stage")})
        actions.append(row)

    def json_file(name: str) -> dict:
        try:
            return json.loads((out / name).read_text())
        except (OSError, ValueError):
            return {}

    invocation, result = json_file("invocation.json"), json_file("slice-result.json") or json_file("result.json")
    report = json_file(packets.REPORT_JSON) or packets.build(out)
    prompt = (out / "prompt.txt").read_text().strip() if (out / "prompt.txt").is_file() else state.get("prompt", "")
    sessions = result.get("sessions") or (result.get("process") or {}).get("sessions") or []
    return {
        "flow_version": FLOW_VERSION, "output": str(out), "kind": invocation.get("kind") or "run",
        "case": invocation.get("case") or result.get("case"), "host": invocation.get("host"),
        "model": invocation.get("model"), "effort": invocation.get("effort"), "delegation": state.get("delegation"),
        "versions": invocation.get("versions") or {},
        "started": datetime.fromtimestamp(started, timezone.utc).isoformat(timespec="seconds") if started else None,
        "seconds": sum(s.get("elapsed_seconds") or 0 for s in sessions) or None,
        "pass": result.get("pass"), "verdicts": result.get("verdicts") or {},
        "run_status": state.get("status"), "prompt": prompt, "events_source": "claude" if claude else "toollog",
        "packets_source": source, "sources": sources(source, claude, traced, run_dir, out),
        "trace": run_trace.summary(traced),
        "paths": short.legend(), "totals": report.get("totals") or {},
        "review_page": REVIEW_PAGE if (out / REVIEW_PAGE).is_file() else None,  # the viewer's header links to it
        "stages": report.get("stages") or [], "actions": actions,
        "case_details": {
            "expect_paths": invocation.get("expect_paths") or [],
            "checks": [{"command": c.get("command"), "pass": c.get("pass"), "output": short(str(c.get("output") or ""))[-1500:]}
                       for c in (result.get("checks") or []) if isinstance(c, dict)],
            "assembled": {k: (result.get("assembled") or {}).get(k) for k in ("changed", "missing", "uncommitted_product")}
                         if result.get("assembled") else None,
            "item_history": result.get("item_history") or [],
            "overshoot": result.get("overshoot"), "queue_growth": result.get("queue_growth"),
        },
        # One entry per clear, in the order they fired (slice.py writes a list; a slice-result from before it holds one
        # object, which this does not read: the viewer shows no clear for it rather than a wrong one).
        "clear": [{**{k: c.get(k) for k in ("n", "stage", "inside")}, "stopped": c.get("stopped"),
                   "redone": c.get("redone"), "pass": c.get("pass")}
                  for c in (result.get("clear") if isinstance(result.get("clear"), list) else []) if isinstance(c, dict)],
        "unattributed": [i for i in items if not i["action"]],
    }


def sources(packet_source: str, claude: bool, traced: dict | None, run_dir: Path, out: Path) -> dict:
    """Which file each part of flow.json came from, relative to the output directory."""
    run = str(run_dir.relative_to(out)) if run_dir.is_relative_to(out) else str(run_dir)
    trace_file = f"{run}/{run_trace.FILE}"
    ok = bool(traced) and "error" not in traced
    return {
        "actions": f"{run}/state.md (history)",
        "packets": {"trace": f"{trace_file} and {run}/packets/sent/ (each packet as sent)",
                    "trace+archive": f"{trace_file} and {run}/packets/sent/; packet-archive/ for stages the trace never printed",
                    "trace+retained": f"{trace_file} and {run}/packets/sent/; {run}/packets/ (last copy) for stages the trace never printed",
                    "archive": "packet-archive/ (each distinct text a 2-s poll saw)",
                    "retained": f"{run}/packets/ (the last copy of each packet)"}[packet_source],
        "model": "events.jsonl (text, calls, results, hook messages)" if claude else "events.jsonl (tool calls only)",
        "refusals": (f"{trace_file} (each refused command on the run, with its text); a refusal of a command that named no run "
                     "or did not parse shows only as its result in events.jsonl"
                     + ("" if traced["covers"] else f"; partial: {traced['partial']}") if ok else
                     "events.jsonl (not marked: a refusal is a result event, and one a pipe hid is missing); "
                     + run_trace.why_not(traced)),
        "keepalive": f"{trace_file} (each stop decision, with the text put into the turn)" if ok else
                     "not recorded: " + run_trace.why_not(traced),
    }


# --- the owner page's "Read first" panel (owner_page.py) -------------------------------------------------------------------

# The status display's message in a Claude stream: the PostToolUse hook's systemMessage, which the host records as an
# informational system event ("PostToolUse:Bash says: ... ShipLoop ..."). Other hosts do not record it.
STATUS_DISPLAY = re.compile(r"^PostToolUse:\S* says:.*ShipLoop", re.S)
# The packet generators: a commit under this path can change what a recorded packet would print today.
GENERATORS = "skills/shiploop/scripts"
ABSOLUTE_PATH = re.compile(r"(?<![\w.])/[^\s'\"`)]+")


def _git(repo: Path, *args: str) -> str | None:
    import subprocess  # noqa: PLC0415 - only the staleness banner runs git
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def recorded_head(out: Path) -> str | None:
    """The checkout commit the harness recorded for a run: a slice's invocation.json `local_head`, else result.json's."""
    for name in ("invocation.json", "result.json"):
        try:
            data = json.loads((out / name).read_text())
        except (OSError, ValueError):
            continue
        for holder in (data, data.get("identity") if isinstance(data, dict) else None):
            if isinstance(holder, dict) and isinstance(holder.get("local_head"), str) and holder["local_head"]:
                return holder["local_head"]
    return None


def staleness(out: Path, repo: Path, branch: str = "main") -> dict:
    """"recorded <date> on <sha>, main <sha>, N packet-generator commits since": how far the repository's packet generators
    moved after the run was recorded. Each part the files or git cannot give is None, and ``text`` says which."""
    stamps = metrics.timeline(out / "timeline.jsonl")
    started = min(stamps.values()) if stamps else None
    date = datetime.fromtimestamp(started, timezone.utc).strftime("%Y-%m-%d") if started else None
    sha = recorded_head(out)
    tip = _git(repo, "rev-parse", "--verify", "--quiet", f"{branch}^{{commit}}")
    known = bool(sha and _git(repo, "cat-file", "-e", f"{sha}^{{commit}}") is not None)
    since = _git(repo, "rev-list", "--count", f"{sha}..{tip}", "--", GENERATORS) if known and tip else None
    count = int(since) if since and since.isdigit() else None
    text = (f"recorded {date or 'on an unknown date'} on {sha[:8] if sha else 'an unrecorded commit'}, {branch} "
            f"{tip[:8] if tip else 'unknown'}, " + (f"{count} packet-generator commit{'s' if count != 1 else ''} since"
                                                    if count is not None else "packet-generator commits since: not measured ("
                                                    + ("the recorded commit is not in this repository" if sha else
                                                       "no commit was recorded") + ")"))
    return {"recorded": date, "sha": sha, "branch": branch, "tip": tip, "generator_commits": count, "text": text,
            "file": "invocation.json" if (out / "invocation.json").is_file() else "result.json"}


def _stage_metrics(out: Path) -> tuple[list[dict] | None, str]:
    """Per stage seconds, turns, tool calls and context peak: metrics.json when the harness wrote it, else metrics.collect."""
    try:
        return json.loads((out / "metrics.json").read_text()).get("stages"), "metrics.json"
    except (OSError, ValueError, AttributeError):
        pass
    try:
        return metrics.collect(out).get("stages"), "events.jsonl"
    except Exception:  # noqa: BLE001 - a record, never a refusal
        return None, "events.jsonl"


def read_first(out: Path, repo: Path | None = None) -> dict:
    """The owner page's first screen, from the run's files only (no model judges anything here). Every block names its source
    file relative to ``out``; a block the files cannot give is ``{"measured": False, "reason": ...}``."""
    out = Path(out).resolve()
    run_dir = metrics.run_dir_of(out) or packets.find_run_dir(out)
    if run_dir is None:
        raise SystemExit(f"no ShipLoop run directory under {out}")
    rel = lambda path: str(Path(path).resolve().relative_to(out)) if str(Path(path).resolve()).startswith(str(out)) else str(path)  # noqa: E731
    run = rel(run_dir)
    reading = metrics.reading_path(out, run_dir)
    claude = reading.get("host") == "claude"
    # One pass over the stream: each ShipLoop verb a command ran, the status displays, the skills called, the refusals by stage.
    invocations, displays, skills, refusals, answered = [], 0, {}, {}, set()
    # The refusals the trace cannot hold (metrics.outside_trace), each with its first text, for a run whose trace covers it.
    commands_by_call, outside = {}, {}
    stage = None
    for _number, event in metrics.event_range(out / "events.jsonl"):
        if event.get("type") == "system" and event.get("subtype") == "informational" \
                and STATUS_DISPLAY.search(str(event.get("content") or "")):
            displays += 1
        for _call, tool, arg in metrics.tool_call_events(event):
            commands_by_call[_call] = str(arg.get("command") or "")
            if arg.get("command"):
                invocations += metrics.shiploop_invocations(str(arg["command"]))
            if tool in metrics.SKILL_TOOLS:
                name = str(arg.get("skill") or "?")
                skills[name] = skills.get(name, 0) + 1
        for call, shown in metrics.tool_results(event):
            if call in answered:
                continue  # Grok repeats an update for one call
            answered.add(call)
            refused = metrics.REFUSAL_LINE.search(shown)
            if refused:
                cause = ABSOLUTE_PATH.sub("<path>", metrics.failure_line(shown[refused.start():], None))
                cause = cause.split(": ", 1)[-1].split("; ")[0][:110]
                key = f"{stage or '?'}\t{cause}"
                refusals[key] = refusals.get(key, 0) + 1
                if metrics.outside_trace(commands_by_call.get(call, ""), shown[refused.start():]):
                    row = outside.setdefault(key, {"stage": stage or "?", "cause": cause, "count": 0,
                                                   "text": shown[refused.start():][:1200], "source": "events.jsonl"})
                    row["count"] += 1
            header = metrics.PACKET_STAGE.search(shown)
            if header:
                stage = header.group("stage")
    traced = run_trace.read(run_dir)
    sends = traced["packets"] if traced and "error" not in traced else {}
    # The lines a pipe kept: `| head` and `| tail` with no count keep 10.
    cut = sorted(i["cut"]["lines"] or (10 if i["cut"]["into"] in ("head", "tail") else 0) for i in invocations if i.get("cut"))
    cut = [n for n in cut if n]
    by_verb: dict[str, dict] = {}
    for found in invocations:
        row = by_verb.setdefault(found["verb"], {"invocations": 0, "piped": 0})
        row["invocations"] += 1
        row["piped"] += bool(found["piped"])
    commands = {
        "invocations": len(invocations),
        "literal": sum(1 for i in invocations if not i["piped"] and not i["variable_any"]),
        "variable_built": sum(1 for i in invocations if i["variable_any"]),
        "variable_run_dir": sum(1 for i in invocations if i["variable_built"]),
        "piped": sum(1 for i in invocations if i["piped"]), "by_verb": by_verb,
        "cut_by_pipe": len(cut), "median_n": metrics._median(cut),
        "status_displays": displays if claude else None,
        "status_displays_reason": None if claude else "this host's stream does not record the status display",
        "file": "events.jsonl",
    }
    # Producer stages the model met, in the ledger's order of their packets.
    opens = reading.get("packet_file_opens") or {}
    prints = (reading.get("shiploop_print_cut") or {}).get("prints") or []
    visits: dict[str, list[list[dict]]] = {}
    last = None
    for row in prints:
        if row["stage"] == "improve":
            last = None
            continue
        if row["stage"] != last:
            visits.setdefault(row["stage"], []).append([])
        visits[row["stage"]][-1].append(row)
        last = row["stage"]
    producers = []
    if opens.get("measured"):
        rows = []
        for entry in opens["stages"]:
            path = run_dir / "packets" / f"{entry['action']}.md"
            text = path.read_text(errors="replace") if path.is_file() else ""
            header = metrics.PACKET_STAGE.search(text[:4000])
            rows.append((int(header.group("revision") or 0) if header else 0, entry, text, path))
        rows.sort(key=lambda r: r[0])
        seen_count: dict[str, int] = {}
        for _revision, entry, text, path in rows:
            n = seen_count.get(entry["stage"], 0)
            seen_count[entry["stage"]] = n + 1
            mine = (visits.get(entry["stage"]) or [])
            group = mine[n] if n < len(mine) else []
            # Written: the packet as last sent when the trace kept it (packets/<action>.md is rewritten in place), else that file.
            last = next((x for x in reversed(sends.get(entry["action"]) or []) if x.get("file")), None)
            producers.append({"stage": entry["stage"], "action": entry["action"],
                              "written": last["chars"] if last else len(text),
                              "seen": sum(r["chars"] for r in group), "cut_by": [r["cut_by"] for r in group if r["cut_by"]],
                              "opened": entry["mode"], "prints": len(sends.get(entry["action"]) or []) if sends else None,
                              "file": f"{run}/{last['file']}" if last else rel(path)})
    gates = reading.get("skipped_gates") or {"measured": False}
    commit_gate = next((g for g in gates.get("gates") or [] if g["gate"] == "item_commit"), None)
    result = {}
    for name in ("slice-result.json", "result.json"):
        try:
            result = json.loads((out / name).read_text())
            result_file = name
            break
        except (OSError, ValueError):
            continue
    assembled = result.get("assembled") if isinstance(result, dict) else None
    uncommitted = (assembled or {}).get("uncommitted_product") or []
    if commit_gate is None and assembled is None:
        item_commit = {"measured": False, "reason": "no item reached verify and no assembled result was recorded"}
    else:
        present = not (commit_gate and commit_gate["skipped"]) and not uncommitted
        item_commit = {"measured": True, "present": present, "uncommitted_product": uncommitted,
                       "reason": commit_gate["reason"] if commit_gate and commit_gate["skipped"] else None,
                       "file": f"{run}/lint/items" if commit_gate else result_file}
    stages, stage_file = _stage_metrics(out)
    steps = [{"stage": s.get("stage"), "seconds": s.get("seconds"), "turns": s.get("turns"), "tool_calls": s.get("tool_calls"),
              "context_peak": (s.get("context") or {}).get("peak"), "incomplete": bool(s.get("incomplete"))}
             for s in stages or [] if s.get("seconds") is not None or s.get("turns") is not None]
    improve = reading.get("improve_skill_invoked") or {}
    state = store.read_record(run_dir / "state.md") if (run_dir / "state.md").is_file() else {}
    invocation = {}
    try:
        invocation = json.loads((out / "invocation.json").read_text())
    except (OSError, ValueError):
        pass
    seeded = list(((invocation.get("seeded") or {}).get("skipped") or []) if isinstance(invocation, dict) else [])
    accepted = state.get("accepted") or {} if isinstance(state, dict) else {}
    for h in (state.get("history") or []) if isinstance(state, dict) else []:
        record = accepted.get(h.get("action")) if isinstance(h, dict) else None
        result = record.get("result", record) if isinstance(record, dict) else {}
        # The harness's seed writes a synthetic result for each stage it records without the model (as `build` reads it).
        if str((result or {}).get("summary", "")).startswith("Synthetic") and h.get("stage") not in seeded:
            seeded.append(h["stage"])
    cannot = ["whether the model read or used the text a tool result showed it: only what reached it is counted",
              "a time or turn difference between runs: one run per side (n=1); the page shows it only beside an A/A spread"]
    if not claude:
        cannot += ["the status display, the model's own text and the printed heads: this host's stream holds tool calls only"]
    if run_trace.covers(traced):
        cannot.append("a refusal of a command that named no run (a workspace verb on --workspace-root) or did not parse, when a pipe "
                      "hid it: the trace records only commands on the run, so those come from the stream's refusal lines")
    else:
        cannot.append("refusals a pipe hid from the host, every reprint and the keepalive's continuations: "
                      + run_trace.why_not(traced))
    if seeded:
        cannot.append(f"the stages the harness recorded without the model ({', '.join(seeded)}): their packets were never run")
    if not stages:
        cannot.append("per-stage seconds, turns and context: no metrics.json and the stream could not be read for them")
    return {
        "output": str(out), "run_dir": run, "host": reading.get("host"), "case": invocation.get("case"),
        "versions": invocation.get("versions") or {}, "delegation": state.get("delegation") if isinstance(state, dict) else None,
        "staleness": staleness(out, repo or HERE.parents[1]),
        "commands": commands,
        "producers": {"measured": bool(opens.get("measured")), "count_opened": opens.get("count"), "of": opens.get("of"),
                      "rows": producers, "reason": opens.get("reason"), "file": f"{run}/packets"},
        "steps": {"measured": stages is not None, "rows": steps, "file": stage_file},
        "gates": {**gates, "ran": sum(g["records"] - g["skipped"] for g in gates.get("gates") or []), "file": f"{run}/tests"},
        "refusals": trace_refusals(traced, run, sum(refusals.values()), list(outside.values())) if run_trace.covers(traced) else {
            "count": sum(refusals.values()), "source": "events.jsonl",
            "rows": [{"stage": k.split("\t")[0], "cause": k.split("\t")[1], "count": v} for k, v in refusals.items()],
            "file": "events.jsonl"},
        "trace": trace_block(traced, run),
        "item_commit": item_commit,
        "skills": {"calls": skills if claude else None, "improve_invoked": improve.get("count"), "improve_stages": improve.get("of"),
                   "file": "events.jsonl"},
        "seeded": seeded, "cannot_show": cannot,
    }


def trace_cause(text: str | None) -> str:
    """A traced refusal's cause as the panel groups it: its first line, paths replaced, up to the first `; `."""
    return ABSOLUTE_PATH.sub("<path>", run_trace.first_line(text, None)).split("; ")[0][:110]


def trace_refusals(traced: dict, run: str, stream_count: int, outside: list[dict] = ()) -> dict:
    """The panel's refusals from the run trace: every refused command (a failed --check-only is a check, counted apart), by the
    stage the run was in and the cause, with the first refusal's text of each row, then the ``outside`` rows: refusals only the
    stream shows (a routed verb, a command that named no run, a usage error; metrics.outside_trace). ``stream_count`` is what
    events.jsonl showed in all."""
    rows: dict[tuple, dict] = {}
    checks = 0
    for failure in traced["failures"]:
        if failure["check_only"]:
            checks += 1
            continue
        key = (failure["stage"] or "?", trace_cause(failure["text"]))
        row = rows.setdefault(key, {"stage": key[0], "cause": key[1], "count": 0,
                                    "text": (failure["text"] or run_trace.NO_TEXT)[:1200], "trace_line": failure["i"],
                                    "source": "trace"})
        row["count"] += 1
    found = [*rows.values(), *outside]
    return {"count": sum(r["count"] for r in found), "checks_failed": checks, "stream_count": stream_count,
            "source": "trace", "rows": found, "file": f"{run}/{run_trace.FILE}",
            "outside_file": "events.jsonl" if outside else None}


def trace_block(traced: dict | None, run: str) -> dict:
    """What the run trace counted: packets printed, reprints, keepalive continuations and stops, failed checks."""
    if not traced or "error" in traced:
        return {"measured": False, "reason": run_trace.why_not(traced)}
    counts = traced["counts"]
    return {"measured": True, "covers": traced["covers"], "partial": traced["partial"], "packets": counts.get("packets"),
            "reprints": counts.get("reprints"), "continuations": counts.get("continuations"), "stops": counts.get("stops"),
            "checks_failed": counts.get("checks_failed"), "file": f"{run}/{run_trace.FILE}"}


STANDALONE_HEAD = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
                   '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n')


def bundle(target: Path, flows: list[dict], standalone: bool = True, home: bool = False) -> Path:
    """The viewer with `flows` inlined. A standalone page (opened from disk) gets its own doctype and charset; an
    Artifact publish adds its own skeleton, so `standalone=False` leaves them out. `home` marks the page as the one run's
    own flow.html, in its folder (`data-home`): the viewer then links to the run's Review page by a relative path."""
    page = TEMPLATE.read_text()
    if DATA_MARK not in page:
        raise SystemExit(f"{TEMPLATE} has no {DATA_MARK} marker")
    data = json.dumps(flows).replace("</", "<\\/")  # nothing in the data can close the script element
    page = page.replace(DATA_MARK, f'<script id="flow-runs" type="application/json"{" data-home" if home else ""}>{data}</script>')
    target.write_text((STANDALONE_HEAD if standalone else "") + page)
    return target


def write(out: Path) -> dict:
    """flow.json and a one-run flow.html in the output directory."""
    flow = build(out)
    (out / "flow.json").write_text(json.dumps(flow) + "\n")
    bundle(out / "flow.html", [flow], home=True)
    return flow


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("outputs", type=Path, nargs="+", help="E2E output directories (or flow.json files with --bundle)")
    p.add_argument("--bundle", type=Path, metavar="HTML", help="write one viewer page holding every given run")
    p.add_argument("--artifact", action="store_true", help="with --bundle: leave out the doctype for an Artifact publish")
    p.add_argument("--read-first", action="store_true",
                   help="print the owner page's Read first panel of one output directory as JSON (writes nothing)")
    args = p.parse_args(argv)
    if args.read_first:
        if len(args.outputs) != 1 or args.bundle:
            p.error("--read-first takes one output directory and no --bundle")
        print(json.dumps(read_first(args.outputs[0].expanduser().resolve()), indent=1))
        return 0
    flows = []
    for given in args.outputs:
        given = given.expanduser().resolve()
        if given.is_file():
            flows.append(json.loads(given.read_text()))
        else:
            flows.append(write(given) if not args.bundle else (
                json.loads((given / "flow.json").read_text()) if (given / "flow.json").is_file() else write(given)))
            if not args.bundle:
                print(given / "flow.html")
    if args.bundle:
        print(bundle(args.bundle.expanduser().resolve(), flows, standalone=not args.artifact))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
