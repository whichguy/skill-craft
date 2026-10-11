#!/usr/bin/env python3
"""Export the part of every recorded run that the count floor reads: ``python3 a5_export.py <e2e-runs dir>``.

For each run directory ``<runs>/<day>/<case>/.shiploop-runs/<id>/run`` that holds test records, keep the history rows
(action, stage, workitem, outcome), the test commands of each accepted step plan, and for each ``tests/<action>-verifyN.md``
record its stage, work item, passed flag and per-command status and counts.  Nothing else: no prompts, summaries or output.
Writes ``a5-recorded-runs.json`` next to this script.  The replay (``a5_replay.py``) needs only that file.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_store as store  # noqa: E402


def export(runs: Path) -> list:
    found = []
    for run in sorted(runs.glob("*/*/.shiploop-runs/*/run")):
        records = sorted((run / "tests").glob("*-verify*.md"))
        if not records:
            continue
        state = store.read_record(run / "state.md")
        plans = {}
        for action, result in (state.get("accepted") or {}).items():
            if isinstance(result, dict) and "test_commands" in result:
                plans[action] = {"outcome": result.get("outcome"), "test_commands": result["test_commands"]}
        verify = {}
        for path in records:
            record = store.read_record(path)
            if not isinstance(record, dict):
                continue
            action, _, number = path.stem.rpartition("-verify")
            verify.setdefault(action, {})[int(number)] = {
                "stage": record.get("stage"), "work_item": record.get("work_item"), "passed": record.get("passed"),
                "runs": [{"command": r.get("command"), "suite": r.get("suite"), "status": r.get("status"),
                          "counts": ({"ran": r["counts"].get("ran")} if r.get("counts") else None)}
                         for r in record.get("runs") or ()]}
        found.append({
            "run": str(run.relative_to(runs)).replace("/.shiploop-runs/", " | ").replace("/run", ""),
            "history": [{key: row.get(key) for key in ("action", "stage", "workitem", "outcome")}
                        for row in state.get("history", ())],
            "step_plans": plans, "verify": verify})
    return found


if __name__ == "__main__":
    runs = Path(sys.argv[1]).expanduser()
    out = export(runs)
    Path(__file__).with_name("a5-recorded-runs.json").write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(len(out), "runs,", sum(len(v) for r in out for v in r["verify"].values()), "test records")
