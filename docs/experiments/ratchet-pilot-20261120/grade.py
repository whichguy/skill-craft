#!/usr/bin/env python3
"""Grade Ratchet pilot runs with instruments no session was shown. No model is called.

    python3 grade.py snapshots RUN [RUN ...]   held-out checks on the product at each recorded stage of a run
    python3 grade.py strength RUN [RUN ...]    the run's frozen acceptance suite against a correct reference, a valid
                                               alternative and each calibrated defect of the case
    python3 grade.py report RUN [RUN ...]      one table over finished runs
    python3 grade.py variant CASE NAME DEST    write the case's reference delivery or one named defect into DEST
    python3 grade.py visible CASE OUT.json     which calibrated defects the case's held-out grader can see at all

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

GRADED = ("build-", "fix-", "green-", "final", "frozen suite")  # "frozen suite ...": a repair start's defective product
DID_NOT_END = ("timed out", "did not end", "(rc None)")
APPARATUS = ("acceptance", "ratchet")  # Ratchet's own files in a work tree: never part of the delivery that is graded


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
        for name in APPARATUS:  # a check that runs `node --test` or counts tests must see the delivery's tests only
            shutil.rmtree(copy / name, ignore_errors=True)
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
            unfinished = [ident for ident, note in (result.get("failed") or {}).items() if any(mark in str(note) for mark in DID_NOT_END)]
            if unfinished:  # the ticket fixture's lost verdict: run again, keep the first result, record both
                again = grade_tree(kind, run / "work", shot["commit"], scratch)
                result = dict(result, rerun=again, did_not_end=unfinished,
                              effective_passed=sorted(set(result.get("passed") or []) | (set(unfinished) & set(again.get("passed") or []))))
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


def build_variant(case, name, dest, for_session=False):
    """Write the case's reference or one named defect into `dest`. `for_session` removes the fixture's own comments
    that say what a stand-in gets wrong (`// stand-in: ...`), which a model session must not be handed."""
    spec = case["variants"]
    if spec["kind"] == "overlay":
        shutil.copytree(E2E / "fixtures" / case["fixture"], dest, dirs_exist_ok=True)
        shutil.copytree(REPO / spec["root"] / name, dest, dirs_exist_ok=True)
        if for_session:
            for path in Path(dest).rglob("*.js"):
                lines = path.read_text().splitlines(keepends=True)
                kept = [line for line in lines if "stand-in:" not in line]
                if len(kept) != len(lines):
                    path.write_text("".join(kept))
    else:
        load(REPO / spec["path"]).build(dest, name)
    return dest


def lay_suite(run, dest):
    """Lay the run's frozen acceptance tests, manifest and specification (its work folder's HEAD) over `dest`, with
    their file modes."""
    work = Path(run) / "work"
    present = [name for name in gate_module.FROZEN_PATHS
               if subprocess.run(["git", "-C", str(work), "cat-file", "-e", f"HEAD:{name}"], capture_output=True, check=False).returncode == 0]
    if present:
        archive = subprocess.run(["git", "-C", str(work), "archive", "HEAD", "--", *present], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)


def run_variant(run, case, name, scratch, named):
    folder = Path(tempfile.mkdtemp(prefix=f"ratchet-{name}-", dir=scratch))
    temp = Path(tempfile.mkdtemp(prefix=f"tmp-{name}-", dir=scratch))  # this variant's own temporary folder
    try:
        build_variant(case, name, folder)
        lay_suite(run, folder)
        # A suite may read the work repository's history (a test that compares with the base commit): give the variant
        # that history, with the variant's own files as the working tree.
        shutil.copytree(Path(run) / "work" / ".git", folder / ".git", symlinks=True)
        record = gate_module.gate(folder, clauses_only=True, no_restore=True, config={}, extra_env={"TMPDIR": str(temp)}, named=named)
        rows = record["clauses"]
        return name, {"failing": sorted(record["failing"]), "unstable": sorted(i for i, r in rows.items() if r.get("unstable")),
                      "did_not_end": sorted(i for i, r in rows.items() if not r["pass"] and (r["rc"] is None or r.get("first_rc") is None)),
                      "ids": sorted(rows), "seconds": round(sum(r["seconds"] for r in rows.values()), 1),
                      "tails": {ident: rows[ident]["tail"][-4:] for ident in record["failing"]}}
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:  # reported, never counted
        return name, {"error": f"{type(error).__name__}: {error}"[:300]}
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(temp, ignore_errors=True)


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
    named = bool(record.get("named_checks"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = dict(pool.map(lambda name: run_variant(run, case, name, scratch, named), names))
    shutil.rmtree(scratch, ignore_errors=True)
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--", str(HERE)], capture_output=True, text=True,
                                check=False).stdout.strip())
    reference = results["reference"]
    report = {"case": record["case"], "graded_with": head + (" (with uncommitted changes to the pilot folder)" if dirty else ""),
              "reference": reference, "controls": {name: results[name] for name in controls},
              "raw": {name: results[name] for name in defects}}
    if "error" in reference:  # no defect can be judged without a measured reference
        report.update(defects={}, caught=None, pool=len(defects))
        (run / "strength.json").write_text(json.dumps(report, indent=1) + "\n")
        print(f"{run.name}: the correct reference could not be measured ({reference['error']}); no defect is judged")
        return
    wrong = set(reference["failing"])
    ids = reference["ids"]
    clause_ids = [ident for ident in ids if ident.startswith("C-")]
    use_ids = [ident for ident in ids if ident.startswith("U-")]
    rows = {}
    for name in defects:
        row = results[name]
        if "error" in row:
            rows[name] = {"caught": None, "by": [], "error": row["error"]}
            continue
        fresh = sorted(set(row["failing"]) - wrong - set(row["did_not_end"]))  # a command that did not end decides nothing
        only_unfinished = sorted((set(row["failing"]) - wrong) & set(row["did_not_end"]))
        rows[name] = {"caught": True if fresh else (None if only_unfinished else False), "by": fresh,
                      **({"did_not_end": only_unfinished} if only_unfinished else {})}
    caught = sum(1 for row in rows.values() if row["caught"])
    not_judged = sorted(name for name, row in rows.items() if row["caught"] is None)
    report.update(items=len(ids), clauses=len(clause_ids), use_cases=len(use_ids),
                  fails_on_reference=sorted(wrong), clauses_failing_on_reference=sorted(wrong & set(clause_ids)),
                  use_cases_failing_on_reference=sorted(wrong & set(use_ids)),
                  defects=rows, caught=caught, pool=len(defects), not_judged=not_judged)
    (run / "strength.json").write_text(json.dumps(report, indent=1) + "\n")
    print(f"{run.name}: {len(clause_ids)} clauses and {len(use_ids)} use cases tested; on the correct reference "
          f"{len(wrong & set(clause_ids))} clauses and {len(wrong & set(use_ids))} use cases fail: {sorted(wrong) or 'none'}")
    for name in controls:
        if "error" in results[name]:
            print(f"  control {name}: not measured ({results[name]['error']})")
            continue
        extra = sorted(set(results[name]["failing"]) - wrong)
        print(f"  control {name}: {'passes' if not extra else 'fails ' + ', '.join(extra)}")
    for name, row in rows.items():
        mark = "caught" if row["caught"] else "MISSED" if row["caught"] is False else "not judged"
        print(f"  {name:<28}{mark:<11}{', '.join(row['by'])}{row.get('error', '')}")
    print(f"  caught {caught} of {len(defects)} calibrated defects" + (f"; not judged: {', '.join(not_judged)}" if not_judged else ""))


def visible(case_name, workers=3):
    """Which calibrated defects can the case's held-out grader see at all? Grades the reference and every defect and
    writes, per defect, the checks it fails that the reference passes. A defect with none cannot be used to read a
    repair: it passes the held-out checks before any loop runs."""
    case = json.loads((HERE / "cases.json").read_text())[case_name]
    defects, _ = variant_names(case)
    scratch = Path(tempfile.mkdtemp(prefix="ratchet-visible-"))

    def one(name):
        folder = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=scratch))
        copy = folder / "copy"
        copy.mkdir()
        try:
            build_variant(case, name, copy)
            result = hidden(case["hidden"], copy, folder)
            unfinished = [i for i, note in (result.get("failed") or {}).items() if any(mark in str(note) for mark in DID_NOT_END)]
            if unfinished or not result.get("observed"):
                shutil.rmtree(copy)
                copy.mkdir()
                build_variant(case, name, copy)
                result = dict(hidden(case["hidden"], copy, folder), first=result)
            return name, result
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            return name, {"observed": False, "reason": f"{type(error).__name__}: {error}"[:300]}
        finally:
            shutil.rmtree(folder, ignore_errors=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = dict(pool.map(one, ["reference", *defects]))
    shutil.rmtree(scratch, ignore_errors=True)
    reference = results["reference"]
    passes = set(reference.get("passed") or [])
    rows = {name: {"observed": bool(results[name].get("observed")),
                   "fails": sorted(set(results[name].get("failed") or {}) & passes)} for name in defects}
    return {"case": case_name, "reference_passes": sorted(passes), "reference_fails": sorted(reference.get("failed") or {}),
            "reference_observed": bool(reference.get("observed")), "defects": rows,
            "visible": sorted(name for name, row in rows.items() if row["observed"] and row["fails"]),
            "invisible": sorted(name for name, row in rows.items() if row["observed"] and not row["fails"]),
            "not_observed": sorted(name for name, row in rows.items() if not row["observed"])}


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
            return "-" if not row else str(len(row.get("effective_passed") or row.get("passed") or [])) + ("" if row.get("observed") else "?")
        first = next((s["label"] for s in record["snapshots"] if s["label"].startswith("build-")), None)
        print(f"{run.name:<36}{str(record.get('model'))[:15]:<16}{record.get('stop')!s:<17}{len(record.get('cycles') or []):>3}"
              f"{len(record.get('sessions') or []):>5}{(record.get('seconds') or 0) / 60:>7.1f}{record.get('clauses') or 0:>8}"
              f"{len(record.get('tamper') or []):>7}  {count(first)} -> {count('final')}")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) == 4 and argv[0] == "variant":  # variant CASE NAME DEST: one reference or defect delivery, for a session
        cases = json.loads((HERE / "cases.json").read_text())
        Path(argv[3]).mkdir(parents=True, exist_ok=False)
        print(build_variant(cases[argv[1]], argv[2], Path(argv[3]), for_session=True))
        return None
    if len(argv) == 3 and argv[0] == "visible":  # visible CASE OUT.json
        report = visible(argv[1])
        Path(argv[2]).write_text(json.dumps(report, indent=1) + "\n")
        print(f"{argv[1]}: the held-out checks see {len(report['visible'])} of {len(report['defects'])} defects; "
              f"cannot see: {', '.join(report['invisible']) or 'none'}; not observed: {', '.join(report['not_observed']) or 'none'}")
        return None
    if len(argv) < 2 or argv[0] not in ("snapshots", "strength", "report"):
        raise SystemExit(__doc__)
    verb, runs = argv[0], argv[1:]
    if verb == "report":
        return report(runs)
    for run in runs:
        (snapshots if verb == "snapshots" else strength)(run)


if __name__ == "__main__":
    main()
