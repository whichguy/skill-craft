#!/usr/bin/env python3
"""How many calibrated defects does a delivery's own test suite catch? The same question grade.py strength asks of a
Ratchet acceptance suite, asked of the tests a build delivers under test/ (ShipLoop's, or a Ratchet builder's own).

    python3 baseline.py CASE LABEL TREE OUT.json      TREE: a delivered product tree, or "-" for the base's tests alone

For the case's correct reference, its second correct delivery where it has one, and every calibrated defect, it
builds the variant in a fresh folder, removes the test files the variant itself adds to the fixture (the reference
ships a test file of its own), copies in the test files of TREE that are new or changed against the case's fixture,
and runs `node --test` with the TAP reporter. So every row is the base's own tests plus TREE's. A test is failing on a variant when it fails in two runs
in a row. A defect is caught when a test fails on it that passes on the reference. A run that does not end is "not
judged". No model is called.
"""
import concurrent.futures
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import grade  # the variant builders

NOT_OK = re.compile(r"^\s*not ok \d+ - (.+?)\s*(?:#.*)?$", re.MULTILINE)
COUNT = re.compile(r"^# (tests|pass|fail) (\d+)\s*$", re.MULTILINE)
SECONDS = 300


def delivered_tests(tree, fixture):
    """Relative paths under test/ in `tree` that the fixture lacks or holds differently."""
    if tree is None:
        return []
    found = []
    for path in sorted((Path(tree) / "test").rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(tree)
        base = Path(fixture) / relative
        if not base.is_file() or base.read_bytes() != path.read_bytes():
            found.append(str(relative))
    return found


def run_suite(folder, temp):
    """One `node --test` run in `folder`: (failing test names, counts, ended)."""
    env = {key: value for key, value in os.environ.items() if key != "PORT"}
    env["TMPDIR"] = str(temp)
    proc = subprocess.Popen(["node", "--test", "--test-reporter=tap"], cwd=str(folder), env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, errors="replace", start_new_session=True)
    try:
        output, _ = proc.communicate(timeout=SECONDS)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)  # this run's own group
        except ProcessLookupError:
            pass
        proc.communicate()
        return set(), {}, False
    try:
        os.killpg(proc.pid, signal.SIGKILL)  # anything the tests left running in that group
    except (ProcessLookupError, PermissionError):
        pass
    names = {name.strip() for name in NOT_OK.findall(output) if not name.strip().endswith((".js", ".cjs", ".mjs"))}
    counts = {key: int(value) for key, value in COUNT.findall(output)}
    if proc.returncode != 0 and not names:
        names = {"(the run failed without naming a test)"}
    return names, counts, True


def one(case, name, tree, files, scratch):
    folder = Path(tempfile.mkdtemp(prefix=f"baseline-{name}-", dir=scratch))
    temp = Path(tempfile.mkdtemp(prefix=f"tmp-{name}-", dir=scratch))
    try:
        grade.build_variant(case, name, folder)
        fixture = grade.E2E / "fixtures" / case["fixture"]
        for path in sorted((folder / "test").rglob("*")):  # a variant's own added tests go: only the base's and TREE's remain
            if path.is_file() and not (fixture / path.relative_to(folder)).exists():
                path.unlink()
        for relative in files:
            target = folder / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(tree) / relative, target)
        first, counts, ended = run_suite(folder, temp)
        if not ended:
            return name, {"ended": False}
        if first:
            second, counts, ended = run_suite(folder, temp)
            if not ended:
                return name, {"ended": False}
            first &= second  # failing means failing twice
        return name, {"ended": True, "failing": sorted(first), "counts": counts}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        return name, {"ended": False, "error": f"{type(error).__name__}: {error}"[:300]}
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(temp, ignore_errors=True)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 4:
        raise SystemExit(__doc__)
    case_name, label, tree, out = argv
    case = json.loads((HERE / "cases.json").read_text())[case_name]
    tree = None if tree == "-" else Path(tree).resolve()
    files = delivered_tests(tree, grade.E2E / "fixtures" / case["fixture"])
    defects, controls = grade.variant_names(case)
    scratch = Path(tempfile.mkdtemp(prefix="ratchet-baseline-"))
    names = ["reference", *controls, *defects]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = dict(pool.map(lambda name: one(case, name, tree, files, scratch), names))
    shutil.rmtree(scratch, ignore_errors=True)
    reference = results["reference"]
    report = {"case": case_name, "label": label, "tree": str(tree) if tree else None, "test_files": files,
              "reference": reference, "controls": {name: results[name] for name in controls}}
    if not reference.get("ended"):
        report.update(caught=None, pool=len(defects))
        Path(out).write_text(json.dumps(report, indent=1) + "\n")
        print(f"{label}: the reference could not be measured; no defect is judged")
        return
    wrong = set(reference["failing"])
    rows = {}
    for name in defects:
        row = results[name]
        fresh = sorted(set(row.get("failing") or []) - wrong) if row.get("ended") else None
        rows[name] = {"caught": None if fresh is None else bool(fresh), "by": (fresh or [])[:6]}
    caught = sum(1 for row in rows.values() if row["caught"])
    report.update(defects=rows, caught=caught, pool=len(defects), tests_on_reference=reference.get("counts"),
                  failing_on_reference=sorted(wrong),
                  missed=sorted(name for name, row in rows.items() if row["caught"] is False),
                  not_judged=sorted(name for name, row in rows.items() if row["caught"] is None))
    for name in controls:
        control = results[name]
        report[f"control_{name}_fails_beyond_reference"] = (sorted(set(control["failing"]) - wrong) if control.get("ended") else None)
    Path(out).write_text(json.dumps(report, indent=1) + "\n")
    print(f"{label}: {len(files)} delivered test file(s); tests on the reference {reference.get('counts')}; failing on the reference "
          f"{len(wrong)}; caught {caught} of {len(defects)}; missed {report['missed']}; not judged {report['not_judged']}")
    for name in controls:
        print(f"  control {name}: fails beyond the reference: {report[f'control_{name}_fails_beyond_reference']}")


if __name__ == "__main__":
    main()
