"""Executable ground truth for the synthetic report controls, not a ShipLoop trial."""
import json
from pathlib import Path

inputs = json.loads(Path("input.json").read_text())
observed = json.loads(Path("report.json").read_text())["totals"]
expected = dict.fromkeys(inputs["statuses"], 0)
for row in inputs["records"]:
    expected[row["status"]] += 1
counts_pass = (set(observed).issubset(expected)
               and all(observed.get(key) == value for key, value in expected.items() if value))
zeros_pass = all(key in observed and observed[key] == 0 for key, value in expected.items() if not value)
checks = [
    {"command": f"exact totals: expected open={expected['open']}, observed open={observed.get('open')}",
     "pass": counts_pass, "returncode": 0 if counts_pass else 1, "status": "exited"},
    {"command": "zero-count statuses are present", "pass": zeros_pass,
     "returncode": 0 if zeros_pass else 1, "status": "exited"},
]
print(json.dumps({"checks": checks, "tests": len(checks)}))
raise SystemExit(0 if all(row["pass"] for row in checks) else 1)
