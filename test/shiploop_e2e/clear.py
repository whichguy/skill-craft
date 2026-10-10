"""The clear-the-context probe (SPEC S-6): stop the host at a stage boundary or inside a stage, continue in a fresh
session that holds only the packet, and measure the work the fresh session redid.

    slice.py --case node-fix-bug --clear-at implement            # at the boundary: the packet arrived, nothing done
    slice.py --case node-fix-bug --clear-at test-green:inside    # after the stage's first completed call

S-6 passes only with no redone work: zero completed state-changing calls repeated after the clear. A call counts
as redone when it repeats one that was **completed** (its result was in the stream) before the stop. A call cut off
without a result is unfinished and does not count. The stop point is recorded as it actually happened, because
`run.launch` polls every POLL_SECONDS while the stream is read on another thread: the host may finish another call
before the kill, and that call is then work done before the clear, not redone work.

Same work, by operation (read-only orientation never counts: `next`, `status`, reading files, `git status`/`diff`):
- write: the same path with the same content (a Write or Edit tool call, a `cat >`/`cat >>` heredoc, `sed -i`);
- callback: the same ShipLoop verb (`complete`, `improve-*`) for the same action;
- commit: a `git commit` with no write between the two;
- test run: the same test command with no write between the two (a rerun after a code change is legitimate).

Claude's stream gives calls and results; other hosts' translated streams are coarser, so their `:inside` stops are
recorded but not gated (see the plan's open unknowns).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

HEADER = re.compile(r"ShipLoop navigator \| (?P<stage>[\w-]+) \| revision (?P<rev>\d+)")
SHIPLOOP_CALL = re.compile(r"(?:scripts/shiploop[\"']?|(?<![\w/-])shiploop(?:-next|-complete)?)\s+(?P<verb>[\w-]+)")
ACTION = re.compile(r"--action[= ](nav-[0-9a-f]{32})")
HEREDOC = re.compile(r"cat\s+>>?\s*(?P<path>[^\s<]+)\s*<<-?\s*['\"]?(?P<tag>\w+)['\"]?\n(?P<body>.*?)\n(?P=tag)\b", re.S)
TEST_RUN = re.compile(r"\b(?:npm (?:run )?test|node --test|pytest|python3? -m (?:unittest|pytest)|go test|cargo test|"
                      r"npx (?:jest|vitest)|jest|vitest)\b[^\n;&|]*")
COMMIT = re.compile(r"\bgit\b[^\n;&|]*\bcommit\b")
SED_INPLACE = re.compile(r"\bsed\s+-i\b")
READ_ONLY_VERBS = {"next", "status", "context", "lint"}


def parse_spec(text: str | None) -> dict | None:
    if not text:
        return None
    stage, _, where = text.partition(":")
    if where not in ("", "inside"):
        raise SystemExit(f"--clear-at {text!r}: use <stage> or <stage>:inside")
    return {"stage": stage, "inside": where == "inside"}


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def stream(events_path: Path) -> tuple[list[dict], list[dict]]:
    """(calls, arrivals) from a Claude stream. A call is {line, id, tool, input, answered, result_line}; an arrival is
    {line, stage, revision}: a packet header printed in a tool result."""
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
                                                        "result_line": None}
            elif block.get("type") == "tool_result":
                call = calls.get(block.get("tool_use_id"))
                if call is not None:
                    call.update(answered=True, result_line=line)
                text = block.get("content")
                text = text if isinstance(text, str) else "\n".join(
                    part.get("text", "") for part in text or [] if isinstance(part, dict))
                arrivals += [{"line": line, "stage": m.group("stage"), "revision": int(m.group("rev"))}
                             for m in HEADER.finditer(text)]
    return sorted(calls.values(), key=lambda c: c["line"]), arrivals


def _command(call: dict) -> str:
    return str(call["input"].get("command") or "")


def is_shiploop(call: dict) -> bool:
    return bool(SHIPLOOP_CALL.search(_command(call)))


def trigger(events_path: Path, state: dict | None, spec: dict, current_stage) -> dict | None:
    """The stop point when the probe should stop now, else None.

    At the boundary: the run's current stage is the target (its packet has been printed by the last `complete`).
    Inside: the same, and at least one non-ShipLoop call made after that packet arrived has its result.
    """
    if not state or state.get("status") != "active" or current_stage(state) != spec["stage"]:
        return None
    calls, arrivals = stream(events_path)
    if spec["inside"]:
        arrived = [a["line"] for a in arrivals if a["stage"] == spec["stage"]]
        if not arrived:
            return None
        done = [c for c in calls if c["line"] > arrived[0] and c["answered"] and not is_shiploop(c)]
        if not done:
            return None
    return point(events_path, state, current_stage)


def point(events_path: Path, state: dict, current_stage) -> dict:
    """Where the stop actually is: the stream line count and the last answered call, with the ledger's position."""
    calls, _ = stream(events_path)
    lines = len(events_path.read_text(errors="replace").splitlines()) if events_path.is_file() else 0
    answered = [c["result_line"] for c in calls if c["answered"]]
    return {"stage": current_stage(state), "action": str((state.get("action") or {}).get("id") or ""),
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
    shiploop = SHIPLOOP_CALL.search(command)
    if shiploop and shiploop.group("verb") not in READ_ONLY_VERBS:
        found = ACTION.search(command)
        return [{"kind": "callback", "key": (shiploop.group("verb"), found.group(1) if found else "")}]
    ops = [{"kind": "write", "key": (m.group("path"), _digest(m.group("body")))} for m in HEREDOC.finditer(command)]
    if SED_INPLACE.search(command):
        ops.append({"kind": "write", "key": ("sed -i", _digest(command))})
    if COMMIT.search(command):
        ops.append({"kind": "commit", "key": ("git commit",)})
    ops += [{"kind": "test", "key": (" ".join(m.group(0).split()),)} for m in TEST_RUN.finditer(command)]
    return ops


def redone(events_path: Path, clear_line: int) -> list[dict]:
    """Completed state-changing operations from before `clear_line` that a call after it repeated."""
    calls, _ = stream(events_path)
    timeline = [(c["line"], c["answered"], op) for c in calls for op in operations(c)]
    writes = [line for line, _, op in timeline if op["kind"] == "write"]
    before = [(line, op) for line, answered, op in timeline if line < clear_line and answered]
    found = []
    for line, _, op in timeline:
        if line < clear_line:
            continue
        for earlier, old in reversed(before):
            if (old["kind"], old["key"]) != (op["kind"], op["key"]):
                continue
            if op["kind"] in ("commit", "test") and any(earlier < w < line for w in writes):
                break  # a change came between them: a legitimate rerun
            found.append({"kind": op["kind"], "key": list(op["key"]), "line": line, "earlier_line": earlier})
            break
    return found
