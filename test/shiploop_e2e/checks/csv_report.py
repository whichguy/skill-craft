#!/usr/bin/env python3
"""Product checks for the `csv-report` case (style: cli-files).

Run from the case's work directory: `python3 csv_report.py <check>`. Each check
builds its inputs in a temporary directory, runs `python3 report.py ...`, and
exits 0 on pass or non-zero with a reason. Nothing is written into the work
directory. The checks only test behaviour the case prompt states.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

HEADER = "date,region,product,units,unit_price\n"
A = HEADER + "2026-01-02,north,widget,3,2.50\n2026-01-03,south,gadget,1,10.00\n"
B = HEADER + "2026-01-04,north,gadget,2,10.00\nbad,row\n2026-01-05,south,widget,-1,2.50\n2026-01-06,east,widget,4,0.25\n"


def fail(reason: str) -> None:
    print("FAIL: " + reason)
    sys.exit(1)


def report(*paths: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "report.py", *map(str, paths)], capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          timeout=60)


def write(tmp: Path, name: str, text: str) -> Path:
    path = tmp / name
    path.write_text(text)
    return path


UNIT_PROBE = (
    "import json, sys, unittest; "
    "suite = unittest.defaultTestLoader.discover('.'); "
    "result = unittest.TextTestRunner(verbosity=0).run(suite); "
    "executed = result.testsRun - len(result.skipped); "
    "print(json.dumps({'ran': result.testsRun, 'executed': executed, "
    "'skipped': len(result.skipped), 'failures': len(result.failures), "
    "'errors': len(result.errors), 'ok': result.wasSuccessful()})); "
    "sys.exit(0 if executed >= 1 and result.wasSuccessful() else 1)"
)


def unit() -> None:
    done = subprocess.run([sys.executable, "-B", "-c", UNIT_PROBE], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=300)
    summary = {}
    for line in reversed(done.stdout.splitlines()):
        try:
            summary = json.loads(line)
            break
        except ValueError:
            continue
    executed = int(summary.get("executed", 0)) if isinstance(summary, dict) else 0
    ran = int(summary.get("ran", 0)) if isinstance(summary, dict) else 0
    skipped = int(summary.get("skipped", 0)) if isinstance(summary, dict) else 0
    if done.returncode != 0 or executed < 1 or not summary.get("ok"):
        fail(f"unittest must pass with at least one executed non-skipped test "
             f"(ran={ran} executed={executed} skipped={skipped}):\n{done.stderr[-800:]}")
    print(f"unittest ran={ran} executed={executed} skipped={skipped}")


def totals() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        done = report(write(Path(tmp), "a.csv", A))
        if done.returncode != 0:
            fail(f"valid input must exit 0, got {done.returncode}: {done.stderr[-300:]}")
        data = json.loads(done.stdout)
        want = {"rows": 2, "revenue": 17.5, "by_region": {"north": 7.5, "south": 10.0},
                "by_product": {"widget": 3, "gadget": 1}}
        for key, value in want.items():
            if key == "by_region":
                got = {k: round(float(v), 2) for k, v in (data.get(key) or {}).items()}
                if got != value:
                    fail(f"{key}: want {value}, got {data.get(key)}")
            elif key == "revenue":
                if round(float(data.get(key, -1)), 2) != value:
                    fail(f"revenue: want {value}, got {data.get(key)}")
            elif data.get(key) != value:
                fail(f"{key}: want {value}, got {data.get(key)}")


def invalid() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        a, b = write(Path(tmp), "a.csv", A), write(Path(tmp), "b.csv", B)
        done = report(a, b)
        if done.returncode != 2:
            fail(f"invalid rows must exit 2, got {done.returncode}")
        for line in ("b.csv:3", "b.csv:4"):
            if line not in done.stderr:
                fail(f"stderr must report {line}: {done.stderr[-400:]}")
        data = json.loads(done.stdout)
        if data.get("rows") != 4 or round(float(data.get("revenue", -1)), 2) != 38.5:
            fail(f"valid rows still count across files: want rows 4, revenue 38.5, got {data}")
        if (data.get("by_product") or {}).get("widget") != 7:
            fail(f"by_product.widget must be 7 (3 + 4), got {data.get('by_product')}")


def missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        done = report(Path(tmp) / "absent.csv")
        if done.returncode != 1:
            fail(f"an unreadable file must exit 1, got {done.returncode}")
        if done.stdout.strip():
            fail("nothing may be printed on stdout for an unreadable file")
        if "Traceback" in done.stderr or not done.stderr.strip():
            fail("an unreadable file needs an error message on stderr and no traceback")


def empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        done = report(write(Path(tmp), "h.csv", HEADER))
        if done.returncode != 0:
            fail(f"a header-only file must exit 0, got {done.returncode}")
        data = json.loads(done.stdout)
        if data.get("rows") != 0 or float(data.get("revenue", -1)) != 0:
            fail(f"a header-only file contributes nothing, got {data}")


CHECKS = {"unit": unit, "totals": totals, "invalid": invalid, "missing": missing, "empty": empty}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in CHECKS:
        sys.exit("usage: csv_report.py " + "|".join(CHECKS))
    try:
        CHECKS[sys.argv[1]]()
    except (ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        fail(f"{type(exc).__name__}: {exc}")
    print("ok")
