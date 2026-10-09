#!/usr/bin/env python3
"""Compact extracts of saved E2E runs, for test/shiploop-e2e-fidelity.test.py (the fidelity block of test/shiploop_e2e/fidelity.py).

  python3 test/fixtures/fidelity/extract.py [/Users/dadleet/e2e-runs]

Reads, never writes, the run folders below (outside the repository) and writes beside this script one folder per run,
in the shape the harness reads: ``events.jsonl`` and ``timeline.jsonl`` (only the events a test needs; every other
line of the stream is left blank, so an event keeps its original number and `metrics.events` yields it at the number
the analyses cite), ``invocation*.json`` (host and regrade only), and ``.shiploop-runs/work-1/run/`` with a
trimmed ``state.md`` (the keys the reader looks at), ``timeline.json``, the verify records without their stdout,
placeholders for the lint, quality, backchain and Improve receipt files that exist (only their names are read) and,
of each Improve packet, the lines that carry one of its five questions.

What is changed: the run folder prefix becomes /runs/<run>, the work-directory stamp becomes work-1 and the user name
becomes `user`, so no personal path is kept; Claude's thinking and text blocks are dropped; a tool result is cut to its
first 120 characters, except a ShipLoop refusal, which keeps the text from its own line on; a summary is cut to 80
characters. The tests expect the figures of these cuts; the figures of the uncut runs are in
docs/shiploop-batch-1011m-g1-fidelity-journal-2026-10-09.md.

Selection of events: every edit-tool call on a path inside a run or Improve directory or a workspace file, every shell
command that writes with sed -i or perl -i, kills by pattern, runs git commit or add, or names a workspace file, and
every ShipLoop call that was refused or exited non-zero, each with its result. Product edits and the rest of the calls are blank lines.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys

RUNS = Path(sys.argv[1] if len(sys.argv) > 1 else "/Users/dadleet/e2e-runs")
HERE = Path(__file__).resolve().parent

# alias -> (folder under RUNS, whether events are kept). The v1220 pair keeps verify heads only: their point is the null counts.
FULL = {
    "r1-battleship-sonnet": "20261008/r1-battleship-sonnet",
    "r2-battleship-sonnet": "20261008/r2-battleship-sonnet",
    "r3-battleship-sonnet": "20261008/r3-battleship-sonnet",
    "r1-checkers-sonnet": "20261008/r1-checkers-sonnet",
    "r2-checkers-sonnet": "20261008/r2-checkers-sonnet",
    "r3-checkers-sonnet": "20261008/r3-checkers-sonnet",
    "r1-battleship-grok-none": "20261008/r1-battleship-grok-none",
    "r2-battleship-grok-none": "20261008/r2-battleship-grok-none",  # started by Grok, finished by Claude: two hosts
    "r3-battleship-grok-none": "20261008/r3-battleship-grok-none",
    "v1230-battleship-sonnet": "20261007/v1230-battleship-sonnet",
    "v1230-battleship-grok-none": "20261007/v1230-battleship-grok-none",
    "v1210-battleship-luna-xhigh": "20261005/v1210-battleship-luna-xhigh",  # Codex, ShipLoop 1.21.0: the old stage table and layout
}
HEADS_ONLY = {
    "v1220-battleship-sonnet": "20261006/v1220-battleship-sonnet",
    "v1220-battleship-grok-medium-none": "20261006/v1220-battleship-grok-medium-none",
}
FENCE = re.compile(r"```shiploop-state\n(?P<json>.*?)\n```", re.S)
REFUSAL = re.compile(r"^ShipLoop (?:navigator|blocked|workspace blocked): ", re.M)
EDIT_TOOL = re.compile(r"write|edit|replace|create", re.I)
KEPT_INSIDE = re.compile(r"/\.shiploop-runs/[^/]+/(?:run/|return-plan\.md|return-receipt\.md|workspace\.md)|\.shiploop-improve/|/\.shiploop/")
SHELL_CANDIDATE = re.compile(r"\bsed\s+(?:-\w+\s+)*-i\b|\bperl\s+(?:-\w+\s+)*-\w*i\b|\bpkill\b|\bkillall\b|git\b[^\n]*\b(?:commit|add)\b|"
                             r"return-plan\.md|return-receipt\.md|workspace\.md")
# The lines of an Improve packet that carry one of its five questions (and the one that names the packet).
IMPROVE_LINES = re.compile(r"^(?:Current action:|Reviewing the returned |Goal: |Done when \(|Checked by:|"
                           r"The opening file holds exactly these headings|Then run: |Recovery command:)")
CUT_RESULT, CUT_SUMMARY, CUT_LINE, CUT_BODY = 120, 80, 220, 600
# A heredoc and its terminator; the terminator may be followed by the closing quote of a Codex `zsh -lc "..."` wrapper.
HEREDOC = re.compile(r"(<<-?\s*['\"]?(\w+)['\"]?[^\n]*\n).*?(\n\s*\2(?=[\"']?\s*(?:\n|$)))", re.S)


def rewrite(text: str, folder: Path) -> str:
    text = text.replace(str(folder), f"/runs/{folder.name}")
    text = re.sub(r"\.shiploop-runs/work-\d{8}-\d{6}-[0-9a-f]{6}", ".shiploop-runs/work-1", text)
    return text.replace("dadleet", "user")


def rewrite_json(value, folder: Path):
    return json.loads(rewrite(json.dumps(value), folder))


def run_dir_of(folder: Path) -> Path:
    found = sorted(folder.glob(".shiploop-runs/*/run"))
    if not found:
        raise SystemExit(f"{folder}: no .shiploop-runs/*/run")
    return found[-1]


def state_of(run_dir: Path) -> dict:
    return json.loads(FENCE.search((run_dir / "state.md").read_text(errors="replace")).group("json"))


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, sort_keys=True) + "\n")


def clip(text, limit):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def trimmed_state(state: dict) -> dict:
    """The keys the readers look at, with every long text cut and the Improve results reduced to their names."""
    keep = {k: state[k] for k in ("status", "stage", "planning_review", "status_reason", "work_index", "navigator_protocol_version")
            if k in state}
    keep["history"] = [{"action": h.get("action"), "stage": h.get("stage"), "outcome": h.get("outcome"), "workitem": h.get("workitem"),
                        "summary": clip(h.get("summary"), CUT_SUMMARY)} for h in state.get("history") or []]
    accepted = {}
    for action, entry in (state.get("accepted") or {}).items():
        row = {"outcome": entry.get("outcome"), "summary": clip(entry.get("summary"), CUT_SUMMARY),
               "evidence_refs": entry.get("evidence_refs") or []}
        for key in ("blocked_by", "awaiting", "unverified"):
            if key in entry:
                row[key] = entry[key]
        accepted[action] = row
    keep["accepted"] = accepted
    keep["improve_results"] = {action: {} for action in (state.get("improve_results") or {})}
    keep["work_items"] = [{"id": w.get("id")} for w in state.get("work_items") or [] if isinstance(w, dict)]
    keep["inner_loops"] = {k: {"stage": (v or {}).get("stage")} for k, v in (state.get("inner_loops") or {}).items()}
    return keep


def record_text(record: dict) -> str:
    return "# ShipLoop test-loop verification\n\n```shiploop-state\n" + json.dumps(record, indent=2, sort_keys=True) + "\n```\n"


def trimmed_record(record: dict) -> dict:
    """A verify record without the product's stdout and stderr; ``observed`` keeps the two keys the fidelity block reads."""
    keep = {k: v for k, v in record.items() if k not in ("runs", "observed", "cwd")}
    keep["runs"] = [{k: v for k, v in run.items() if k not in ("stdout", "stderr")} for run in record.get("runs") or []]
    if isinstance(record.get("observed"), dict):
        keep["observed"] = {k: record["observed"][k] for k in ("kind", "where") if k in record["observed"]}
    return keep


def extract_run_dir(src_run: Path, dst_run: Path, folder: Path, heads_only: bool) -> None:
    state = state_of(src_run) if (src_run / "state.md").is_file() else None
    if state is not None and not heads_only:
        text = "# ShipLoop navigator state\n\n```shiploop-state\n" + json.dumps(rewrite_json(trimmed_state(state), folder), indent=1,
                                                                               sort_keys=True) + "\n```\n"
        (dst_run).mkdir(parents=True, exist_ok=True)
        (dst_run / "state.md").write_text(text)
        timeline = json.loads((src_run / "timeline.json").read_text())
        write_json(dst_run / "timeline.json", rewrite_json({"started": timeline.get("started"), "accepted": timeline.get("accepted")}, folder))
    for record_path in sorted(src_run.rglob("*-verify*.md")):
        record = json.loads(FENCE.search(record_path.read_text(errors="replace")).group("json"))
        target = dst_run / record_path.relative_to(src_run)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rewrite(record_text(trimmed_record(record)), folder))
    if heads_only:
        return
    for pattern, body in (("lint/nav-*.md", "# ShipLoop lint record\n"), ("quality/nav-*-terminal.json", "{}\n"),
                          ("backchain/nav-*/check-*.json", "{}\n"), ("improve/nav-*/receipt.md", "# Improve receipt\n")):
        for path in sorted(src_run.glob(pattern)):
            target = dst_run / path.relative_to(src_run)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body)
    for packet in sorted(src_run.glob("packets/nav-*-improve.md")):
        lines = [clip(line, CUT_LINE) for line in packet.read_text(errors="replace").splitlines() if IMPROVE_LINES.match(line)]
        target = dst_run / "packets" / packet.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(rewrite("\n".join(lines) + "\n", folder))


def result_text(content) -> str:
    if isinstance(content, list):
        content = "".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
    return str(content or "")


def cut_result(shown: str) -> str:
    found = REFUSAL.search(shown)
    if found:
        return shown[:12] + "\n…\n" + shown[found.start():]
    return shown[:CUT_RESULT]


def keep_body(heredoc: str) -> bool:
    """A heredoc stays whole when it is short, or when its prose reads like a git command to the frozen glue reader (Codex event 731 of
    v1210-battleship-luna-xhigh feeds a review report to the Until Loop runtime, and its sentence "; git diff --check passed. Scoped
    commit" is the false positive the unwrapped detectors do not have)."""
    return len(heredoc) <= CUT_BODY or (len(heredoc) <= 5000 and bool(re.search(r"[;&|]\s*git\b[^\n;&|]*\s(?:commit|add)\b", heredoc)))


def compact_input(arg: dict) -> dict:
    """A call's input without the bodies it carries: a command keeps its shape (a heredoc body over 600 characters is cut, unless keep_body says its prose matters), an edit keeps only the paths it names."""
    if isinstance(arg.get("command"), str):
        command = HEREDOC.sub(lambda m: m.group(0) if keep_body(m.group(0)) else m.group(1) + "[body cut]" + m.group(3), arg["command"])
        return {"command": command}
    return {k: arg[k] for k in ("target_file", "file_path", "path", "paths") if k in arg}


def candidate_call(tool: str, arg: dict) -> bool:
    command = str(arg.get("command") or "")
    if command:
        return bool(SHELL_CANDIDATE.search(command))
    paths = [str(arg.get(k)) for k in ("target_file", "file_path", "path") if isinstance(arg.get(k), str)]
    paths += [p for p in (arg.get("paths") or []) if isinstance(p, str)]
    return bool(EDIT_TOOL.search(tool)) and any(KEPT_INSIDE.search(p) for p in paths)


def compact_event(event: dict) -> dict:
    """The call event with its input compacted (compact_input); the shape (Claude's tool_use block, Grok's rawInput) is kept."""
    if event.get("type") == "assistant":
        for block in event["message"]["content"]:
            block["input"] = compact_input(block.get("input") or {})
    elif isinstance(event.get("rawInput"), dict):
        event = {**{k: event[k] for k in ("type", "toolCallId", "title", "toolName", "status") if k in event},
                 "rawInput": compact_input(event["rawInput"])}
    return event


def extract_events(src: Path, dst: Path, folder: Path) -> None:
    """events.jsonl and timeline.jsonl with the selected events at their original line numbers.

    A call is told apart by its event number and id, and a result belongs to the latest call with its id: Codex numbers its
    calls again in each session, and one Claude message can carry several tool_use blocks."""
    lines = (src / "events.jsonl").read_text(errors="replace").splitlines()
    stamps = {}
    for line in (src / "timeline.jsonl").read_text(errors="replace").splitlines():
        item = json.loads(line)
        stamps[int(item["line"])] = item["t"]
    events = {}
    for number, line in enumerate(lines):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events[number] = event
    calls, results, latest = {}, {}, {}  # (event, id) -> (tool, input); (event, id) -> (result event, text, exit); id -> (event, id)
    for number, event in events.items():
        kind = event.get("type")
        if kind == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    calls[(number, block.get("id"))] = (str(block.get("name")), block.get("input") or {})
                    latest[block.get("id")] = (number, block.get("id"))
        elif kind == "tool_call":
            calls[(number, event.get("toolCallId"))] = (str(event.get("toolName") or event.get("title")), event.get("rawInput") or {})
            latest[event.get("toolCallId")] = (number, event.get("toolCallId"))
        elif kind == "user":
            for block in (event.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result" and block.get("tool_use_id") in latest:
                    results[latest[block["tool_use_id"]]] = (number, result_text(block.get("content")), None)
        elif kind == "tool_call_update" and isinstance(event.get("rawOutput"), dict) and event.get("status") != "in_progress":
            if event.get("toolCallId") in latest:
                raw = event["rawOutput"]
                results[latest[event["toolCallId"]]] = (number, str(raw.get("output_for_prompt") or ""), raw.get("exit_code"))
    keep = set()
    for key, (tool, arg) in calls.items():
        found = results.get(key) or (None, "", None)
        shown, code = found[1], found[2]
        exit_shown = int(m.group(1)) if (m := re.match(r"Exit code (\d+)", shown)) else code
        failed_shiploop = "shiploop" in str(arg.get("command") or "") and exit_shown not in (None, 0)
        if candidate_call(tool, arg) or REFUSAL.search(shown) or failed_shiploop:
            keep.add(key)
    out = [""] * len(lines)
    kept_blocks: dict[int, list] = {}  # event -> the blocks of that event to write
    for key in sorted(keep):
        number, call_id = key
        event = events[number]
        if event.get("type") == "assistant":
            block = next(b for b in event["message"]["content"] if b.get("type") == "tool_use" and b.get("id") == call_id)
            kept_blocks.setdefault(number, []).append({**block, "input": compact_input(block.get("input") or {})})
        else:
            out[number] = json.dumps(rewrite_json(compact_event(event), folder))
        if key in results:
            rnumber, shown, code = results[key]
            revent = events[rnumber]
            if revent.get("type") == "user":
                kept_blocks.setdefault(rnumber, []).append(
                    {"type": "tool_result", "tool_use_id": call_id, "content": cut_result(shown)})
            else:
                out[rnumber] = json.dumps(rewrite_json({
                    "type": "tool_call_update", "toolCallId": call_id, "status": revent.get("status"),
                    "rawOutput": {"output_for_prompt": cut_result(shown), "exit_code": code}}, folder))
    for number, blocks in kept_blocks.items():
        event = events[number]
        if event.get("type") == "assistant":
            body = {"type": "assistant", "message": {"id": event["message"].get("id"), "content": blocks,
                                                    "usage": event["message"].get("usage")}}
        else:
            body = {"type": "user", "message": {"role": "user", "content": blocks}}
        out[number] = json.dumps(rewrite_json(body, folder))
    kept_numbers = {n for n, text in enumerate(out) if text}
    stamped = sorted(stamps)
    kept_numbers |= {stamped[0], stamped[-1]}
    dst.mkdir(parents=True, exist_ok=True)
    (dst / "events.jsonl").write_text("\n".join(out) + "\n")
    (dst / "timeline.jsonl").write_text("".join(json.dumps({"line": n, "t": stamps[n]}) + "\n" for n in sorted(kept_numbers) if n in stamps))


def copy_invocations(src: Path, dst: Path) -> None:
    for path in sorted(src.glob("invocation*.json")):
        record = json.loads(path.read_text())
        write_json(dst / path.name, {"case": record.get("case"), "host": record.get("host"),
                                     "versions": {k: v for k, v in (record.get("versions") or {}).items() if k in ("source", "regraded")}})


def extract(alias: str, relative: str, heads_only: bool) -> None:
    folder = RUNS / relative
    dst = HERE / alias
    run_dir = run_dir_of(folder)
    extract_run_dir(run_dir, dst / ".shiploop-runs" / "work-1" / "run", folder, heads_only)
    if not heads_only:
        copy_invocations(folder, dst)
        extract_events(folder, dst, folder)


def write_stage_table() -> None:
    """stage_table.json: the stage table of the engine in this checkout, reduced to what stage_catalog reads. The tests build a stub
    shiploop_stage_spec.py from it, so a later change to the engine's table cannot change what a saved run's rows are read against."""
    import importlib.util
    path = HERE.parents[2] / "skills" / "shiploop" / "scripts" / "shiploop_stage_spec.py"
    spec = importlib.util.spec_from_file_location("fidelity_extract_stage_spec", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    rows = {name: {"complete_runs": sorted(module.STAGE_SPEC[name].complete_runs or ()),
                   "improve": module.STAGE_SPEC[name].improve or "", "reads": list(module.STAGE_SPEC[name].reads)}
            for name in module.STAGES}
    write_json(HERE / "stage_table.json", {"stages": list(module.STAGES), "rows": rows,
                                           "planning_choice_stages": sorted(module.PLANNING_CHOICE_STAGES)})


def main() -> None:
    write_stage_table()
    for alias, relative in FULL.items():
        extract(alias, relative, False)
    for alias, relative in HEADS_ONLY.items():
        extract(alias, relative, True)


if __name__ == "__main__":
    main()
