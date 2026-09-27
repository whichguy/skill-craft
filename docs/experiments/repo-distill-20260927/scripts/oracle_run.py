#!/usr/bin/env python3
"""Run a black-box oracle against a program and report per-test results.

    oracle_run.py ORACLE_DIR --app-cmd CMD [--json OUT]
    oracle_run.py ORACLE_DIR --admit --original CMD --stub CMD

--admit runs the oracle against the original (every test must pass) and a
stub (tests that still pass test nothing), and exits 0 only when admitted.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def run(oracle: Path, app_cmd: str, timeout: int = 600, tap: Path | None = None) -> dict:
    env = {**os.environ, "APP_CMD": app_cmd}
    files = sorted(str(p) for p in oracle.glob("*.test.mjs"))
    proc = subprocess.run(["node", "--test", "--test-reporter=tap", *files], env=env,
                          capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    if tap:
        tap.write_text(proc.stdout + "\n# stderr\n" + proc.stderr)
    results = {}
    stack: list[str] = []
    for line in proc.stdout.splitlines():
        m = re.match(r"^(\s*)(not ok|ok) \d+ - (.*?)(\s+#\s*(SKIP|TODO).*)?$", line)
        if not m:
            continue
        depth = len(m.group(1)) // 4
        name = m.group(3).strip()
        stack[depth:] = [name]
        results[" > ".join(stack)] = "skip" if m.group(5) else ("pass" if m.group(2) == "ok" else "fail")
    # Only leaves are behaviours; a parent's status is the union of its children.
    leaves = {k: v for k, v in results.items() if not any(o.startswith(k + " > ") for o in results)}
    counts = {s: sum(1 for v in leaves.values() if v == s) for s in ("pass", "fail", "skip")}
    return {"app_cmd": app_cmd, "returncode": proc.returncode, "counts": counts, "tests": leaves,
            "stderr_tail": proc.stderr[-2000:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("oracle", type=Path)
    ap.add_argument("--app-cmd")
    ap.add_argument("--admit", action="store_true")
    ap.add_argument("--original")
    ap.add_argument("--stub")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--tap", type=Path, help="save the full TAP output (failure messages)")
    args = ap.parse_args()
    if args.admit:
        # Twice on the original: a check that differs between runs is flaky.
        first, second = run(args.oracle, args.original), run(args.oracle, args.original)
        stub = run(args.oracle, args.stub)
        flaky = sorted(k for k in first["tests"] if first["tests"][k] != second["tests"].get(k))
        failing = sorted(k for k, v in first["tests"].items() if v != "pass" and k not in flaky)
        # Correct negative checks (unknown id -> 404) may pass on a do-nothing stub;
        # they are listed, and most checks must still fail there.
        stub_pass = sorted(k for k, v in stub["tests"].items() if v == "pass")
        total = len(first["tests"])
        report = {"admitted": total > 0 and not failing and not flaky and len(stub_pass) * 2 < total,
                  "total": total, "original": first["counts"], "stub": stub["counts"],
                  "failing_on_original": failing, "flaky": flaky, "passing_on_stub": stub_pass}
    else:
        report = run(args.oracle, args.app_cmd, tap=args.tap)
    text = json.dumps(report, indent=2)
    if args.json:
        args.json.write_text(text + "\n")
    print(json.dumps(report["counts"]) if "counts" in report else text)
    return 0 if report.get("admitted", report.get("returncode") == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
