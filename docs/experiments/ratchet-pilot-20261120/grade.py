#!/usr/bin/env python3
"""Grade Ratchet pilot runs with instruments no session was shown. No model is called.

    python3 grade.py snapshots RUN [RUN ...]   held-out checks on the product at each recorded stage of a run
    python3 grade.py strength RUN [RUN ...]    the run's frozen acceptance suite against a correct reference, a valid
                                               alternative and each calibrated defect of the case
    python3 grade.py report RUN [RUN ...]      one table over finished runs

snapshots  exports the commit ratchet.py made after each stage (build-N, fix-N, green-N, final) and runs the case's
           held-out checks on the copy, with the graders round 4 to 6 of the structure study used
           (docs/experiments/sdlc-structure-20261119/slice_snapshots.py) and, for ticket assignment, the full case's
           18 checks (quality.acceptance). A check that did not end is run once more; the first result is kept and
           both are recorded (the ticket fixture's known port collision). Result: RUN/hidden.json.

strength   builds the case's reference delivery and each named variant in a fresh folder, lays the run's frozen
           acceptance tests and manifest over it, and runs every clause command (gate.py, clauses only).
             reference    a correct delivery: a clause failing here is a clause the suite gets wrong, or a choice the
                          specification made that the reference does not share; it is listed and never counts as a kill
             alternative  another correct delivery, where the case has one: a failure here is an over-tight test
             each defect  caught when a clause fails that passes on the reference
           Result: RUN/strength.json.
"""
import concurrent.futures
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
E2E = REPO / "test" / "shiploop_e2e"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "sdlc-structure-20261119"))
import gate as gate_module

GRADED = ("build-", "fix-", "green-", "final")
DID_NOT_END = ("timed out", "did not end")


def load(path):
    spec = importlib.util.spec_from_file_location(Path(path).stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def case_of(run):
    record = json.loads((Path(run) / "run.json").read_text())
    cases = json.loads((HERE / "cases.json").read_text())
    return record, cases[record["case"]]


# ------------------------------------------------------------------ held-out checks at each snapshot
def hidden(kind, copy, folder):
    import slice_snapshots as slices  # the structure study's graders; it loads the E2E harness's quality module
    if kind == "expenses":
        return slices.expense(copy)
    if kind == "chess":
        return slices.chess(copy)
    if kind == "due-times":
        return slices.due_times(copy)
    if kind == "ticket-assignment":
        spec = json.loads((E2E / "cases.json").read_text())["ticket-assignment"]["quality"]
        try:
            result = slices.snap.quality.acceptance(copy, spec["acceptance"], groups=set(), stop=lambda: None, logs=folder / "logs",
                                                    ports=list(spec.get("refuse_ports") or []))
        finally:
            slices.snap.listeners.reap(folder)
        rows = result.get("checks") or []
        return {"observed": bool(result.get("observed")), "reason": result.get("reason"),
                "passed": [row["id"] for row in rows if row.get("pass")],
                "failed": {row["id"]: row.get("note") for row in rows if not row.get("pass")}}
    if kind == "stand-in":  # the harness's own strong and boundary tests for the orders module, never shown to a session
        root = E2E / "fixtures" / "stand-ins" / "stand-in-rules"
        passed, failed = [], {}
        for name, source in (("strong-tests", root / "strong-tests" / "test" / "orders.test.js"),
                             ("boundary-tests", root / "boundary-tests" / "test" / "orders.boundary.test.js")):
            target = Path(copy) / "test" / f"held_out_{name.split('-')[0]}.test.js"
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(source, target)
            try:
                done = subprocess.run(["node", "--test", str(target)], cwd=copy, capture_output=True, text=True, timeout=120, check=False)
                ok, lines = done.returncode == 0, [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]
                note = next((line.strip() for line in lines if line.strip().startswith("not ok")), (lines or [""])[-1])
            except subprocess.TimeoutExpired:
                ok, note = False, "timed out after 120 s"
            if ok:
                passed.append(name)
            else:
                failed[name] = note[:240]
        return {"observed": True, "passed": passed, "failed": failed}
    raise SystemExit(f"no held-out grader named {kind!r}")


def grade_tree(kind, work, commit, scratch):
    folder = Path(tempfile.mkdtemp(prefix="ratchet-snap-", dir=scratch))
    copy = folder / "copy"
    copy.mkdir()
    try:
        archive = subprocess.run(["git", "-C", str(work), "archive", commit], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(copy)], input=archive, check=True)
        return hidden(kind, copy, folder)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return {"observed": False, "reason": f"{type(error).__name__}: {error}"[:300]}
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def snapshots(run):
    run = Path(run).resolve()
    record, case = case_of(run)
    kind = case.get("hidden")
    if not kind:
        print(f"{run.name}: the case has no held-out grader")
        return
    out = run / "hidden.json"
    report = json.loads(out.read_text()) if out.exists() else {}
    scratch = run / "grade-work"
    scratch.mkdir(exist_ok=True)
    by_tree = {row["tree"]: row for row in report.values() if isinstance(row, dict) and row.get("tree")}
    for shot in record["snapshots"]:
        label = shot["label"]
        if not label.startswith(GRADED) or label in report:
            continue
        if shot["tree"] in by_tree:
            report[label] = dict(by_tree[shot["tree"]], same_tree_as=by_tree[shot["tree"]].get("label"), label=label)
        else:
            result = grade_tree(kind, run / "work", shot["commit"], scratch)
            if any(any(mark in str(note) for mark in DID_NOT_END) for note in (result.get("failed") or {}).values()):
                result = dict(result, rerun=grade_tree(kind, run / "work", shot["commit"], scratch))
            report[label] = dict(result, tree=shot["tree"], label=label, at=shot["at"])
            by_tree[shot["tree"]] = report[label]
        out.write_text(json.dumps(report, indent=1) + "\n")
        row = report[label]
        print(f"{run.name:<34}{label:<12}passed {len(row.get('passed') or []):>2}  failed {sorted(row.get('failed') or {})}"
              + ("  (not observed: " + str(row.get("reason")) + ")" if not row.get("observed") else ""), flush=True)
    shutil.rmtree(scratch, ignore_errors=True)


# ------------------------------------------------------------------ the frozen suite against calibrated variants
def variant_names(case):
    spec = case["variants"]
    if spec["kind"] == "overlay":
        return list(spec["defects"]), []
    module = load(REPO / spec["path"])
    return list(module.DEFECTS), [name for name in ("alternative",) if name in getattr(module, "VARIANTS", ())]


def build_variant(case, name, dest):
    spec = case["variants"]
    if spec["kind"] == "overlay":
        shutil.copytree(E2E / "fixtures" / case["fixture"], dest, dirs_exist_ok=True)
        shutil.copytree(REPO / spec["root"] / name, dest, dirs_exist_ok=True)
    else:
        load(REPO / spec["path"]).build(dest, name)
    return dest


def lay_suite(run, dest):
    """Copy the run's frozen acceptance tests, manifest and specification (its work folder's HEAD) over `dest`."""
    work = Path(run) / "work"
    for name in gate_module.FROZEN_PATHS:
        listed = subprocess.run(["git", "-C", str(work), "ls-tree", "-r", "--name-only", "HEAD", "--", name],
                                capture_output=True, text=True, check=True).stdout.splitlines()
        for relative in listed:
            target = Path(dest) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.run(["git", "-C", str(work), "show", f"HEAD:{relative}"], capture_output=True, check=True).stdout)


def run_variant(run, case, name, scratch):
    folder = Path(tempfile.mkdtemp(prefix=f"ratchet-{name}-", dir=scratch))
    try:
        build_variant(case, name, folder)
        lay_suite(run, folder)
        record = gate_module.gate(folder, clauses_only=True, no_restore=True)
        return name, {"failing": sorted(record["failing"]), "unstable": sorted(i for i, r in record["clauses"].items() if r.get("unstable")),
                      "clauses": len(record["clauses"]),
                      "tails": {ident: record["clauses"][ident]["tail"][-4:] for ident in record["failing"]}}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:  # reported, never counted
        return name, {"error": f"{type(error).__name__}: {error}"[:300]}
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def strength(run, workers=4):
    run = Path(run).resolve()
    record, case = case_of(run)
    if "variants" not in case:
        print(f"{run.name}: the case has no calibrated variants")
        return
    defects, controls = variant_names(case)
    scratch = run / "strength-work"
    scratch.mkdir(exist_ok=True)
    names = ["reference", *controls, *defects]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = dict(pool.map(lambda name: run_variant(run, case, name, scratch), names))
    shutil.rmtree(scratch, ignore_errors=True)
    wrong = set(results["reference"].get("failing") or [])
    rows = {}
    for name in defects:
        row = results[name]
        fresh = sorted(set(row.get("failing") or []) - wrong)
        rows[name] = {"caught": bool(fresh) if "error" not in row else None, "by": fresh, **({"error": row["error"]} if "error" in row else {})}
    caught = sum(1 for row in rows.values() if row["caught"])
    judged = sum(1 for row in rows.values() if row["caught"] is not None)
    report = {"case": record["case"], "clauses": results["reference"].get("clauses"), "fails_on_reference": sorted(wrong),
              "reference": results["reference"], "controls": {name: results[name] for name in controls},
              "defects": rows, "caught": caught, "judged": judged, "raw": {name: results[name] for name in defects}}
    (run / "strength.json").write_text(json.dumps(report, indent=1) + "\n")
    print(f"{run.name}: {report['clauses']} clauses; fail on the correct reference: {sorted(wrong) or 'none'}")
    for name in controls:
        extra = sorted(set(results[name].get("failing") or []) - wrong)
        print(f"  control {name}: {'passes' if not extra else 'fails ' + ', '.join(extra)}")
    for name, row in rows.items():
        mark = "caught" if row["caught"] else "MISSED" if row["caught"] is False else "not judged"
        print(f"  {name:<28}{mark:<11}{', '.join(row['by'])}{row.get('error', '')}")
    print(f"  caught {caught} of {judged} calibrated defects")


# ------------------------------------------------------------------ one table
def report(runs):
    head = f"{'run':<36}{'model':<16}{'stop':<17}{'cyc':>3}{'sess':>5}{'min':>7}{'clauses':>8}{'tamper':>7}  hidden first build -> final"
    print(head)
    for run in runs:
        run = Path(run).resolve()
        if not (run / "run.json").exists():
            continue
        record = json.loads((run / "run.json").read_text())
        marks = json.loads((run / "hidden.json").read_text()) if (run / "hidden.json").exists() else {}

        def count(label, marks=marks):
            row = marks.get(label)
            return "-" if not row else str(len(row.get("passed") or [])) + ("" if row.get("observed") else "?")
        first = next((s["label"] for s in record["snapshots"] if s["label"].startswith("build-")), None)
        print(f"{run.name:<36}{str(record.get('model'))[:15]:<16}{record.get('stop')!s:<17}{len(record.get('cycles') or []):>3}"
              f"{len(record.get('sessions') or []):>5}{(record.get('seconds') or 0) / 60:>7.1f}{record.get('clauses') or 0:>8}"
              f"{len(record.get('tamper') or []):>7}  {count(first)} -> {count('final')}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] not in ("snapshots", "strength", "report"):
        raise SystemExit(__doc__)
    verb, runs = argv[0], argv[1:]
    if verb == "report":
        return report(runs)
    for run in runs:
        (snapshots if verb == "snapshots" else strength)(run)


if __name__ == "__main__":
    main()
