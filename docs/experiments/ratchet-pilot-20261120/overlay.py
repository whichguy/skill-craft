"""Run one run's frozen acceptance suite on a product it was not written against. No model is called.

    python3 overlay.py OUT.json LABEL=SUITE_RUN@PRODUCT ...

SUITE_RUN is a finished run folder whose work/ holds acceptance tests and their manifest. PRODUCT is either
`reference` (the case's correct reference, built fresh as grade.py builds it) or `RUN:LABEL`, the commit another
run's record names LABEL (for example `/runs/p3R-ticket-due-times-a:build-1`). The product's own acceptance tests
and Ratchet files are removed, the suite is laid over the tree exactly as grade.py lays it over a variant, and every
clause command runs once through gate.py (clauses only; a failing command is run a second time by the gate).

What it measures: how many items of a suite fail on a correct product the suite's author never saw. Read beside
the same suite's count on the product it was written against, that is an upper bound on what a test session
working without the build would have to catch up on afterwards (an upper bound, because here the two also come from
different specifications and plans). It reads the run folders and writes only OUT.json and its own temporary files.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# The pilot folder whose grade.py is used: this one, or another checkout named by RATCHET_PILOT (read, never
# written, so a run of this script leaves a checkout it does not own untouched).
sys.dont_write_bytecode = True
sys.path.insert(0, os.environ.get("RATCHET_PILOT") or str(Path(__file__).resolve().parent))
import grade  # the grader's own way of building a reference, laying a suite and calling the gate


def export(run, label, dest):
    """The product tree another run recorded under `label`, without that run's own tests and Ratchet files."""
    record = json.loads((Path(run) / "run.json").read_text())
    commits = [snap["commit"] for snap in record["snapshots"] if snap["label"] == label]
    if not commits:
        raise SystemExit(f"{run}: no snapshot labelled {label}")
    archive = subprocess.run(["git", "-C", str(Path(run) / "work"), "archive", commits[0]], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", str(dest)], input=archive, check=True)
    for name in grade.APPARATUS:
        shutil.rmtree(Path(dest) / name, ignore_errors=True)
    return commits[0]


def one(label, suite_run, product, scratch):
    suite_run = Path(suite_run).resolve()
    record, case = grade.case_of(suite_run)
    folder = Path(tempfile.mkdtemp(prefix="overlay-", dir=scratch))
    temp = Path(tempfile.mkdtemp(prefix="tmp-", dir=scratch))
    try:
        if product == "reference":
            grade.build_variant(case, "reference", folder)
            source = "the case's reference"
        else:
            run, _, snap = product.rpartition(":")
            source = f"{Path(run).name} at {snap} ({export(run, snap, folder)[:12]})"
        grade.lay_suite(suite_run, folder)
        shutil.copytree(suite_run / "work" / ".git", folder / ".git", symlinks=True)  # a suite may read the base commit
        result = grade.gate_module.gate(folder, clauses_only=True, no_restore=True, config={}, extra_env={"TMPDIR": str(temp)},
                                        named=bool(record.get("named_checks")))
        rows = result["clauses"]
        failing = sorted(result["failing"])
        return {"label": label, "suite": suite_run.name, "product": source, "items": len(rows), "failing": failing,
                "unstable": sorted(i for i, r in rows.items() if r.get("unstable")),
                "did_not_end": sorted(i for i, r in rows.items() if not r["pass"] and (r["rc"] is None or r.get("first_rc") is None)),
                "seconds": round(sum(r["seconds"] for r in rows.values()), 1),
                "tails": {ident: rows[ident]["tail"][-6:] for ident in failing}}
    finally:
        shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(temp, ignore_errors=True)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        raise SystemExit(__doc__)
    out, entries = Path(argv[0]), argv[1:]
    scratch = Path(tempfile.mkdtemp(prefix="ratchet-overlay-"))
    rows = []
    try:
        for entry in entries:
            label, _, rest = entry.partition("=")
            suite_run, _, product = rest.partition("@")
            row = one(label, suite_run, product, scratch)
            rows.append(row)
            print(f"{label}: suite {row['suite']} on {row['product']}: {row['items'] - len(row['failing'])} of {row['items']} pass; "
                  f"failing {', '.join(row['failing']) or 'none'}" + (f"; did not end {row['did_not_end']}" if row["did_not_end"] else ""),
                  flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    out.write_text(json.dumps(rows, indent=1) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
