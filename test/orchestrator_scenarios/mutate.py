#!/usr/bin/env python3
"""Gate 4 of the Plan Orchestrator test method: every contrary change is caught.

Usage: python3 test/orchestrator_scenarios/mutate.py MUTANTS.json [--only ID ...]

The mutants file names a package directory, the suite command, and mutants
({id, file, find, replace, killed_by}). The suite must pass against the unmodified
package. Each mutant is applied to a fresh copy of the package, whose path is
passed as PLAN_DISPATCHER_DIR, and the suite must then fail, printing
`FAIL [<killed_by>]` for the scenario the spec says covers it; a failure only
elsewhere is reported as a wrong-reason kill. A `find` string
that does not occur exactly once is an error, so mutants cannot silently rot
when the code changes. Exits 1 when the baseline fails, a mutant is stale, or
any mutant survives.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT_SECONDS = 900


def run_suite(command: list[str], package: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, PLAN_DISPATCHER_DIR=str(package))
    return subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True,
                          timeout=TIMEOUT_SECONDS, check=False)


def apply(package: Path, mutant: dict, scratch: Path) -> Path:
    copy = scratch / mutant["id"]
    shutil.copytree(package, copy)
    target = copy / mutant["file"]
    text = target.read_text(encoding="utf-8")
    count = text.count(mutant["find"])
    if count != 1:
        raise ValueError(f"mutant {mutant['id']}: find text occurs {count} times in {mutant['file']}")
    target.write_text(text.replace(mutant["find"], mutant["replace"]), encoding="utf-8")
    return copy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mutants")
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    spec = json.loads(Path(args.mutants).read_text(encoding="utf-8"))
    package = ROOT / spec["package"]
    command = spec["suite"]
    mutants = [m for m in spec["mutants"] if args.only is None or m["id"] in args.only]
    ids = [m["id"] for m in spec["mutants"]]
    if len(set(ids)) != len(ids):
        print("duplicate mutant ids")
        return 1

    baseline = run_suite(command, package)
    if baseline.returncode != 0:
        print("baseline suite fails against the unmodified package:\n" + baseline.stdout[-4000:] + baseline.stderr[-2000:])
        return 1
    print(f"baseline: pass ({len(mutants)} mutants)")

    with tempfile.TemporaryDirectory(prefix="orchestrator-mutants-") as temp:
        scratch = Path(temp)
        try:
            copies = [(m, apply(package, m, scratch)) for m in mutants]
        except ValueError as exc:
            print(f"stale mutant: {exc}")
            return 1

        def check(item):
            mutant, copy = item
            result = run_suite(command, copy)
            if result.returncode == 0:
                return mutant["id"], "SURVIVED"
            if f"FAIL [{mutant['killed_by']}]" not in result.stdout:
                return mutant["id"], "WRONG-REASON (expected FAIL [" + mutant["killed_by"] + "])"
            return mutant["id"], "killed"

        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            results = list(pool.map(check, copies))

    survivors = [mid for mid, verdict in results if verdict != "killed"]
    for mid, verdict in results:
        print(f"{verdict:<10} {mid}")
    print(f"{len(results) - len(survivors)}/{len(results)} killed by their named scenario")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
