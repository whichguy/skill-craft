"""The clear-the-context probe (SPEC S-6): stop the host at a stage boundary or inside a stage, continue in a fresh
session that holds only the packet, and measure the work the fresh session redid.

    slice.py --case node-fix-bug --clear-at implement            # at the boundary: the packet arrived, nothing done
    slice.py --case node-fix-bug --clear-at test:inside          # after the stage's first completed call
    slice.py --case node-fix-bug --clear-at implement --clear-at implement:inside --clear-at improve   # three clears

`--clear-at` repeats. The positions fire **in the order given**: each session ends at the first position not yet cleared,
and the fresh session that follows is measured from its own stop (`redone`), so a redo after the second clear fails that
clear only. A position that is out of the run's order, or that never comes (a stage the slice does not reach, an inside
position whose stage finished in one call), blocks the ones after it; the slice result lists what never fired
(`clear_unfired`), so a probe that stopped less often than asked is visible, not a pass. Positions:
- `<stage>`: the run's current stage is the stage (its packet has just been printed) and no Improve stage is running;
- `<stage>:inside`: the same, and after the fresh packet was shown a call that is not ShipLoop's has its result;
- `improve`: an Improve stage is running (the producer's result waits at its review, `state["active_improve"]` is
  bound); `improve:inside` waits for the Improve stage's packet and a completed call that is not ShipLoop's. An Improve
  stage is a position of its own: the stage it reviews is not at its boundary while the review runs. Which review it is
  follows from the order: the first one after the previous clear.
A repeated identical position is the caller's mistake: the second fires at once and measures nothing.

S-6 passes only with no redone work: zero completed state-changing calls repeated after the clear. A call counts
as redone when it repeats one that was **completed** (its result was in the stream) before the stop. A call cut off
without a result is unfinished and does not count. The stop point is recorded as it actually happened, because
`run.launch` polls every POLL_SECONDS while the stream is read on another thread: the host may finish another call
before the kill, and that call is then work done before the clear, not redone work.

Same work, by operation (read-only orientation never counts: `next`, `status`, reading files, `git status`/`diff`):
- write: the same path with the same content (a Write or Edit tool call, a `cat >`/`cat >>` heredoc, `sed -i`);
- callback: the same ShipLoop verb (`complete`, `improve-*`) for the same action;
- commit: a `git commit` with no write between the two;
- test run: the same test command with no write between the two (a rerun after a code change is legitimate), and only
  when a ShipLoop callback recorded the work after the earlier run and before the stop.  A result that only the cleared
  context saw is unknown to the fresh session, so rerunning that test is verification, not redone work.

Claude's stream gives calls and results; other hosts' translated streams (Grok's and Codex's tool_call lines) are not
read here, so on them a boundary position works (it is state-based) and an `:inside` position is accepted and recorded
as requested but never fires: nothing in the stream is a call this module can see. It is not refused; it is reported
unfired. Likewise their `redone` is empty: not a measurement. Run Grok and Codex slices at boundaries.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metrics  # noqa: E402  (shell variable expansion, shared with the glue detector)

HEADER = re.compile(r"ShipLoop navigator \| (?P<stage>[\w-]+) \| revision (?P<rev>\d+)")
SHIPLOOP_CALL = re.compile(r"(?:scripts/shiploop[\"']?|(?<![\w/-])shiploop(?:-next|-complete)?)\s+(?P<verb>[\w-]+)")
ACTION = re.compile(r"--action[= ](nav-[0-9a-f]{32})")
HEREDOC = re.compile(r"cat\s+>>?\s*(?P<path>[^\s<]+)\s*<<-?\s*['\"]?(?P<tag>\w+)['\"]?\n(?P<body>.*?)\n(?P=tag)\b", re.S)
TEST_RUN = re.compile(r"\b(?:npm (?:run )?test|node --test|pytest|python3? -m (?:unittest|pytest)|go test|cargo test|"
                      r"npx (?:jest|vitest)|jest|vitest)\b[^\n;&|<>]*")
COMMIT = re.compile(r"\bgit\b[^\n;&|]*\bcommit\b")
SED_INPLACE = re.compile(r"\bsed\s+-i\b")
# A script that writes files (python3 - <<'EOF' ... open(p, 'w') / write_text / json.dump) and a plain redirect to a file.
SCRIPT_WRITE = re.compile(r"(?:\bopen\([^)]*['\"][wa]\+?['\"]|\.write_text\(|\.write_bytes\(|\bjson\.dump\(|"
                          r"\bfs\.writeFileSync\(|\bfs\.appendFileSync\()")
REDIRECT = re.compile(r"(?<![0-9&>])>>?\s*(?!&|/dev/null)(?P<path>[^\s;&|<>()]+)")
READ_ONLY_VERBS = {"next", "status", "context", "lint"}


IMPROVE = "improve"  # the position of an Improve stage (the stage ShipLoop names `improve` in its header)


def parse_spec(texts: list[str] | None) -> list[dict]:
    """The `--clear-at` positions in the order given, each {"stage", "inside"}. None or an empty list is no probe."""
    specs = []
    for text in texts or []:
        stage, _, where = text.partition(":")
        if not stage or where not in ("", "inside"):
            raise SystemExit(f"--clear-at {text!r}: use <stage> or <stage>:inside ({IMPROVE!r} is an Improve stage)")
        specs.append({"stage": stage, "inside": where == "inside"})
    return specs


def label(spec: dict) -> str:
    """The text of one position, as it was given: `implement`, `implement:inside`, `improve`."""
    return spec["stage"] + (":inside" if spec["inside"] else "")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def stream(events_path: Path, keep_text: bool = False) -> tuple[list[dict], list[dict]]:
    """(calls, arrivals) from a Claude stream. A call is {line, id, tool, input, answered, result_line, chars}; an arrival is
    {line, stage, revision}: a packet header printed in a tool result. ``chars`` is the length of the result the model was
    shown (None while unanswered); ``keep_text`` also keeps that text, as ``shown``, for a caller that classifies it."""
    calls: dict[str, dict] = {}
    arrivals = []
    if not events_path.is_file():
        return [], []
    for line, raw in enumerate(events_path.read_text(errors="replace").splitlines()):
        try:
            event = json.loads(raw)
        except ValueError:
            continue
        content = (event.get("message") or {}).get("content") if isinstance(event, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                calls[block.get("id") or f"#{line}"] = {"line": line, "id": block.get("id"), "tool": block.get("name"),
                                                        "input": block.get("input") or {}, "answered": False,
                                                        "result_line": None, "chars": None}
            elif block.get("type") == "tool_result":
                call = calls.get(block.get("tool_use_id"))
                text = block.get("content")
                text = text if isinstance(text, str) else "\n".join(
                    part.get("text", "") for part in text or [] if isinstance(part, dict))
                if call is not None:
                    call.update(answered=True, result_line=line, chars=len(text), **({"shown": text} if keep_text else {}))
                arrivals += [{"line": line, "stage": m.group("stage"), "revision": int(m.group("rev"))}
                             for m in HEADER.finditer(text)]
    return sorted(calls.values(), key=lambda c: c["line"]), arrivals


def _command(call: dict) -> str:
    return str(call["input"].get("command") or "")


def is_shiploop(call: dict) -> bool:
    return bool(SHIPLOOP_CALL.search(_command(call)))


def trigger(events_path: Path, state: dict | None, spec: dict, current_stage, current_action=None,
            since: int = 0) -> dict | None:
    """The stop point when the probe should stop now, else None.

    At the boundary: the run's current stage is the target (its packet has been printed by the last `complete`).
    Inside: the same, and at least one non-ShipLoop call made after that packet arrived has its result.
    `improve` is the stage whose result waits at its review: it needs the Improve child bound, and a stage position
    needs none (the Improve stage is a position of its own, not the stage it reviews).
    `since` is the stream line the previous clear stopped at: an inside position counts only the packet and the calls
    the fresh session made after it, never the cleared session's.
    """
    if not state or state.get("status") != "active":
        return None
    reviewing = state.get("active_improve") is not None
    if spec["stage"] == IMPROVE:
        if not reviewing:
            return None
    elif reviewing or current_stage(state) != spec["stage"]:
        return None
    if spec["inside"]:
        calls, arrivals = stream(events_path)
        arrived = [a["line"] for a in arrivals if a["stage"] == spec["stage"] and a["line"] >= since]
        if not arrived:
            return None
        done = [c for c in calls if c["line"] > arrived[0] and c["answered"] and not is_shiploop(c)]
        if not done:
            return None
    return point(events_path, state, current_stage, current_action)


def point(events_path: Path, state: dict, current_stage, current_action=None) -> dict:
    """Where the stop actually is: the stream line count and the last answered call, with the ledger's position.
    While an Improve stage runs the stage is `improve` and the action is the Improve stage's own."""
    calls, _ = stream(events_path)
    lines = len(events_path.read_text(errors="replace").splitlines()) if events_path.is_file() else 0
    answered = [c["result_line"] for c in calls if c["answered"]]
    child = state.get("active_improve")
    try:
        if child is not None:
            action = str(child.get("improve_action") or "")
        else:
            action = str((current_action(state) if current_action else state.get("action") or {}).get("id") or "")
    except Exception:  # noqa: BLE001 - a record, never a refusal
        action = ""
    return {"stage": IMPROVE if child is not None else current_stage(state), "action": action,
            "revision": state.get("revision"), "events_line": lines,
            "last_answered_line": max(answered) if answered else None}


def operations(call: dict) -> list[dict]:
    """The state-changing operations one call made, each with its identity key; read-only calls make none."""
    tool, data = call.get("tool"), call.get("input") or {}
    if tool == "Write":
        return [{"kind": "write", "key": (str(data.get("file_path")), _digest(str(data.get("content"))))}]
    if tool in ("Edit", "MultiEdit"):
        return [{"kind": "write", "key": (str(data.get("file_path")), _digest(json.dumps(data, sort_keys=True)))}]
    command = _command(call)
    if not command:
        return []
    # The model names ids through shell variables (A=nav-...; --action=$A): expand them first.
    command = metrics.expand_variables(command, metrics.shell_variables(command))
    shiploop = SHIPLOOP_CALL.search(command)
    if shiploop and shiploop.group("verb") not in READ_ONLY_VERBS:
        found = ACTION.search(command)
        # An action that cannot be resolved never matches another call: unknown is not "the same".
        return [{"kind": "callback", "key": (shiploop.group("verb"), found.group(1) if found else f"?{call['line']}")}]
    ops = [{"kind": "write", "key": (m.group("path"), _digest(m.group("body")))} for m in HEREDOC.finditer(command)]
    if SED_INPLACE.search(command) or SCRIPT_WRITE.search(command):
        ops.append({"kind": "write", "key": ("script", _digest(command))})
    heredoc_targets = {m.group("path") for m in HEREDOC.finditer(command)}
    ops += [{"kind": "write", "key": (m.group("path"), _digest(command))} for m in REDIRECT.finditer(command)
            if m.group("path") not in heredoc_targets]
    if COMMIT.search(command):
        ops.append({"kind": "commit", "key": ("git commit",)})
    ops += [{"kind": "test", "key": (" ".join(m.group(0).split()),)} for m in TEST_RUN.finditer(command)]
    return ops


def orientation(events_path: Path, clear_line: int, stamps: dict | None = None) -> dict:
    """What the fresh session took in before it changed anything (efficiency plan, unit U5): the characters its read-only calls
    returned, by class (``metrics.classify_call``: a file class such as entry_card or packet_file, else the bucket), and how long
    it took to make its first state-changing call (``operations``: a write, a callback, a commit, a test run).

    The calls are the ones from ``clear_line`` on, as ``redone`` reads them. The S-6 verdict does not change: it counts only
    state-changing calls the fresh session repeated, so a clear that read 80,000 characters of cards and redid nothing passes,
    and this record is what shows the reading. ``time_to_first_state_changing_call`` is seconds from the first stamped event at
    or after the clear to that call (None where the run has no timeline, or the session never changed anything).
    """
    calls, _arrivals = stream(events_path, keep_text=True)
    if not calls:
        return {"measured": False, "reason": "no tool calls in Claude's event shape: clear.py reads Claude's stream, and another "
                "host's reading of a fresh context is metrics.reading_path's cold calls after a break",
                "orientation_bytes": None, "read_only_calls": None, "first_state_changing_call": None,
                "time_to_first_state_changing_call": None}
    stamps = metrics.timeline(events_path.parent / "timeline.jsonl") if stamps is None else stamps
    by_class: dict[str, dict] = {}
    first = None
    read_only = 0
    for call in (c for c in calls if c["line"] >= clear_line):
        if operations(call):
            first = call
            break
        read_only += 1
        info = metrics.classify_call(str(call["tool"]), call["input"], call.get("shown") or "")
        row = by_class.setdefault(info["cls"] or info["bucket"], {"calls": 0, "chars": 0})
        row["calls"] += 1
        row["chars"] += call["chars"] or 0
    began = next((stamps[n] for n in sorted(stamps) if n >= clear_line), None)
    at = stamps.get(first["line"]) if first else None
    return {"measured": True,
            "orientation_bytes": {"total": sum(r["chars"] for r in by_class.values()), "by_class": dict(sorted(by_class.items()))},
            "read_only_calls": read_only,
            "first_state_changing_call": None if first is None else {"line": first["line"], "tool": first["tool"],
                                                                      "kinds": sorted({op["kind"] for op in operations(first)})},
            "time_to_first_state_changing_call": None if began is None or at is None else round(at - began, 3)}


def redone(events_path: Path, clear_line: int, until_line: int | None = None) -> list[dict]:
    """Completed state-changing operations from before `clear_line` that a call after it repeated.

    With several clears, `until_line` (the next clear's stop line) bounds the window to the session that began at this
    clear, so a redo is counted against the clear it follows and not against the earlier ones: it still repeats
    everything that was completed before `clear_line`, the earlier sessions' work included."""
    calls, _ = stream(events_path)
    timeline = [(c["line"], c["answered"], op) for c in calls for op in operations(c)]
    writes = [line for line, _, op in timeline if op["kind"] == "write"]
    callbacks = [line for line, answered, op in timeline if op["kind"] == "callback" and answered]
    before = [(line, op) for line, answered, op in timeline if line < clear_line and answered]
    found = []
    for line, _, op in timeline:
        if line < clear_line:
            continue
        if until_line is not None and line >= until_line:
            break
        for earlier, old in reversed(before):
            if (old["kind"], old["key"]) != (op["kind"], op["key"]):
                continue
            # A write in the same call as the rerun counts (a call that edits and then tests reruns legitimately).
            if op["kind"] in ("commit", "test") and any(earlier < w <= line for w in writes):
                break  # a change came between them: a legitimate rerun
            # A result only the cleared context saw is not known to the fresh session: rerunning that test is how it
            # learns where it stands.  It is redone only when a ShipLoop callback recorded the work before the clear.
            if op["kind"] == "test" and not any(earlier < c < clear_line for c in callbacks):
                break
            found.append({"kind": op["kind"], "key": list(op["key"]), "line": line, "earlier_line": earlier})
            break
    return found
