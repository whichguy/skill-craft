#!/usr/bin/env python3
"""Seeded-defect step cases: score the final tree of a slice for the latent defect its case plants.

A case in step_cases.json with a ``seeded_defect`` asks for a small change whose obvious implementation carries a defect the
case's own ``checks`` do not exercise (a locale-aware comparator where the request says case-sensitive, a sort with no
comparator, a division with no guard for an empty input). Whether the Improve review catches it at pass 1 is then a fact of
the final tree, scored by a script and never by a judgement:

    python3 test/shiploop_e2e/seeded_defects.py score <slice output dir>      # the final tree of one slice
    python3 test/shiploop_e2e/seeded_defects.py verify                         # every case: the probe tells naive from fixed

``probe`` commands exit 0 when the defect is absent. ``score`` runs them in the clean export slice.py grades
(``<output>/export``) and reports ``present`` (a probe failed: the defect survived the run) or ``absent``. ``verify`` is the
harness's own proof that a probe measures the defect: on the case's ``naive`` reference tree (what a run with no review
leaves) the case's checks pass and a probe fails, and on its ``fixed`` tree both pass. The score is a record: arms.py reads it
(a lower catch rate than control rejects an arm), it is never one of slice.py's verdicts.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEP_CASES = HERE / "step_cases.json"
FIXTURES = HERE / "fixtures"
TIMEOUT_SECONDS = 120


def cases() -> dict[str, dict]:
    """The step cases that plant a defect, by name."""
    raw = json.loads(STEP_CASES.read_text())
    return {name: case for name, case in raw.items() if not name.startswith("_") and case.get("seeded_defect")}


def _run(command: str, tree: Path) -> dict:
    try:
        done = subprocess.run(command, shell=True, cwd=tree, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return {"command": command, "exit": None, "pass": False, "output": f"timed out after {TIMEOUT_SECONDS} s"}
    output = (done.stdout + done.stderr).strip()
    return {"command": command, "exit": done.returncode, "pass": done.returncode == 0, "output": output[-400:]}


def score(case: dict, tree: Path) -> dict:
    """Run a case's defect probes in ``tree``. ``present`` is True when any probe failed (the defect survived), False when
    all passed; ``checks`` are the case's own commands, run beside them so a tree that fails those is told apart."""
    seeded = case["seeded_defect"]
    probes = [_run(command, Path(tree)) for command in seeded["probe"]]
    checks = [_run(command, Path(tree)) for command in case["checks"]]
    return {"defect": seeded["id"], "present": any(not p["pass"] for p in probes), "probes": probes,
            "checks_pass": all(c["pass"] for c in checks), "checks": checks}


def score_output(out: Path) -> dict | None:
    """Score a slice output folder: the case it ran (invocation.json) on its graded export. None for a case with no planted
    defect, or a folder without the export slice.py writes."""
    out = Path(out)
    try:
        name = json.loads((out / "invocation.json").read_text())["case"]
    except (OSError, ValueError, KeyError):
        return None
    case = cases().get(name)
    export = out / "export"
    if case is None or not export.is_dir():
        return None
    return {"case": name, **score(case, export)}


def reference_tree(case: dict, kind: str, into: Path) -> Path:
    """The case's fixture with its ``naive`` or ``fixed`` reference files laid over it, copied under ``into``."""
    tree = into / kind
    shutil.copytree(FIXTURES / case["fixture"], tree)
    shutil.copytree(FIXTURES / case["seeded_defect"]["tree"] / kind, tree, dirs_exist_ok=True)
    return tree


def verify(only: str | None = None) -> list[dict]:
    """For every defect case: does the probe fail on the naive tree while that tree's own checks pass, and pass on the fixed?"""
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, case in cases().items():
            if only and name != only:
                continue
            naive = score(case, reference_tree(case, "naive", Path(tmp) / name))
            fixed = score(case, reference_tree(case, "fixed", Path(tmp) / name))
            rows.append({"case": name, "defect": case["seeded_defect"]["id"],
                         "naive_survives_its_checks": naive["checks_pass"], "naive_defect_present": naive["present"],
                         "fixed_checks_pass": fixed["checks_pass"], "fixed_defect_present": fixed["present"],
                         "ok": naive["checks_pass"] and naive["present"] and fixed["checks_pass"] and not fixed["present"]})
    return rows


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["verify"]:
        rows = verify(args[1] if len(args) > 1 else None)
        json.dump(rows, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0 if rows and all(r["ok"] for r in rows) else 1
    if args[:1] == ["score"] and len(args) == 2:
        result = score_output(Path(args[1]))
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0 if result is not None else 2
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
