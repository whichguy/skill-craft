"""Read the follow-on list out of finished ShipLoop E2E runs (live round of the build, 2026-11-01).

Usage: python3 extract_follow_on.py OUTPUT_DIR [OUTPUT_DIR ...] [--json]

For each E2E output folder: the run's state.md (found under <output>/.shiploop-runs/*/run/), the handoff attempts in the
run's trace (every `complete` command whose cursor stayed at the handoff is a refusal), the accepted handoff result's
`follow_on` list (None when the result has no key), the derived request file, the report's Follow-on section, and the
verdicts of result.json.  Read-only; it computes nothing about whether a label is right.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def run_dirs(output: Path) -> list[Path]:
    return sorted(path.parent for path in output.glob(".shiploop-runs/*/run/state.md"))


def read_state(run: Path) -> dict:
    # state.md is a ShipLoop record: one fenced JSON block.
    text = (run / "state.md").read_text(encoding="utf-8")
    match = re.search(r"```[a-z-]*\n(.*?)\n```", text, re.DOTALL)
    return json.loads(match.group(1)) if match else {}


def handoff_attempts(run: Path) -> list[dict]:
    attempts = []
    trace = run / "trace.jsonl"
    if not trace.is_file():
        return attempts
    for line in trace.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("kind") == "command" and row.get("verb") == "complete":
            stage = row.get("stage") or [None, None]
            if stage and stage[0] == "handoff":
                attempts.append({"exit": row.get("exit"), "moved_to": stage[1]})
    return attempts


def handoff_packet(run: Path) -> dict:
    trace = run / "trace.jsonl"
    rows = []
    if trace.is_file():
        for line in trace.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("kind") == "packet" and row.get("stage") == "handoff":
                rows.append({"chars": row.get("chars"), "printed": row.get("printed"), "whole": row.get("whole")})
    return {"packets": rows}


def describe(output: Path) -> dict:
    found = {"output": str(output), "runs": []}
    result = output / "result.json"
    if result.is_file():
        data = json.loads(result.read_text(encoding="utf-8"))
        found["verdicts"] = {key: (value.get("status") if isinstance(value, dict) else value)
                             for key, value in (data.get("verdicts") or data.get("grades") or {}).items()} \
            if isinstance(data.get("verdicts") or data.get("grades"), dict) else {}
        found["case"] = data.get("case")
    for run in run_dirs(output):
        state = read_state(run)
        handoff_rows = [row for row in state.get("history", []) if row.get("stage") == "handoff" and row.get("outcome") == "done"]
        accepted = state.get("accepted", {}).get(handoff_rows[-1]["action"], {}) if handoff_rows else {}
        report = (run / "report.html").read_text(encoding="utf-8") if (run / "report.html").is_file() else ""
        found["runs"].append({
            "run": str(run), "status": state.get("status"), "stage": state.get("stage"),
            "handoff_attempts": handoff_attempts(run), **handoff_packet(run),
            "follow_on": accepted.get("follow_on", None) if accepted else None,
            "handoff_accepted": bool(handoff_rows),
            "request_file": (run / "follow-on-request.md").is_file(),
            "report_has_section": "<h2>Follow-on</h2>" in report,
            "unverified_at_handoff": accepted.get("unverified") if accepted else None,
        })
    return found


def main(argv: list[str]) -> int:
    outputs = [Path(arg) for arg in argv if not arg.startswith("--")]
    rows = [describe(path) for path in outputs]
    if "--json" in argv:
        print(json.dumps(rows, indent=2))
        return 0
    for row in rows:
        print("=" * 100)
        print(row["output"], "| case", row.get("case"), "| verdicts", row.get("verdicts"))
        for run in row["runs"]:
            print("  run", run["run"].split(".shiploop-runs/")[-1], "| status", run["status"], "| handoff attempts",
                  run["handoff_attempts"], "| handoff packets", run["packets"])
            entries = run["follow_on"]
            print("  follow_on:", "NOT RECORDED" if entries is None else f"{len(entries)} entr" + ("y" if len(entries) == 1 else "ies"),
                  "| request file", run["request_file"], "| report section", run["report_has_section"])
            for entry in entries or []:
                print("    -", entry.get("class"), "|", entry.get("source"), "|", entry.get("request_sentence") or "-", "|",
                      " ".join(str(entry.get("statement", "")).split())[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
