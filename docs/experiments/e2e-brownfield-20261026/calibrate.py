#!/usr/bin/env python3
"""Regenerate calibration.txt: the `user-listing` brownfield case (build step 6) graded on every variant of its reference.

    python3 docs/experiments/e2e-brownfield-20261026/calibrate.py > docs/experiments/e2e-brownfield-20261026/calibration.txt

Each variant of test/fixtures/quality/reference_user_listing.py is built in a scratch folder and committed as a delivery, then
graded as a run grades it: the held-out acceptance through quality.acceptance, the base's pristine tests and the delivery's own
suite through checks/base_tests.py, and, for the base, the reference and the alternative, the case's checks through
run.run_checks. Writes nothing but stdout and its scratch folder, which it removes. No model is called.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "skills/shiploop/scripts"), str(ROOT / "test/shiploop_e2e"), str(ROOT / "test/fixtures/quality")]
os.environ.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
import boundary  # noqa: E402
import quality  # noqa: E402
import reference_user_listing as reference  # noqa: E402
import run  # noqa: E402

CASE = json.loads(run.CASES.read_text())["user-listing"]
BLOCK = CASE["quality"]["acceptance"]
GRADES = {item["id"]: item["grade"] for item in BLOCK["checks"]}


def commit(folder: Path) -> Path:
    for args in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "d"]):
        subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True)
    return folder


def base_tests(delivery: Path, subcommand: str) -> str:
    done = subprocess.run([sys.executable, str(run.HERE / "checks" / "base_tests.py"), subcommand, "node-base"], cwd=delivery,
                          capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return ("pass" if done.returncode == 0 else "FAIL") + ": " + " ".join(done.stdout.split()).removeprefix("FAIL: ")[:150]


def main() -> None:
    node = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
    # What graded, by content rather than by a commit a rebase renames (SPEC: the evaluator boundary's digests).
    graded = boundary.fingerprint(run.HERE, CASE)
    held = hashlib.sha256(Path(reference.__file__).read_bytes()).hexdigest()[:12]
    print(f"# user-listing calibration (build step 6), node {node}; evaluator {graded['evaluator']}, oracle {graded['oracle']}, "
          f"case {graded['case']}, reference_user_listing.py {held}. Each variant built by reference_user_listing.build, "
          "committed, and graded as a run grades it.")
    print("# grades: " + ", ".join(f"{ident} {grade}" for ident, grade in GRADES.items()))
    groups: set = set()
    scratch = Path(tempfile.mkdtemp(prefix="brownfield-calibration-"))
    try:
        for variant in reference.VARIANTS:
            delivery = commit(reference.build(scratch / variant, variant))
            block = quality.acceptance(delivery, BLOCK, groups=groups, stop=lambda: None, logs=scratch / "logs" / variant,
                                       ports=CASE["quality"]["refuse_ports"])
            failed = [row for row in block.get("checks", []) if not row["pass"]]
            print(f"\n## {variant}")
            print(f"held-out: {len(block['checks']) - len(failed)} of {len(block['checks'])} pass" if block["observed"]
                  else f"held-out not observed: {block['reason']}")
            for row in failed:
                print(f"  failed {row['id']} ({GRADES[row['id']]}): {row['note'][:160]}")
            print(f"pristine: {base_tests(delivery, 'pristine')}")
            print(f"own suite: {base_tests(delivery, 'suite')}")
            if variant in ("base", "reference", "alternative"):
                rows = run.run_checks(delivery, CASE["checks"], timeout=120)
                print("case checks (suite, pristine, http): " + ", ".join("pass" if row["pass"] else "FAIL" for row in rows))
        print(f"\n# server groups left running: {len(groups)}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    main()
