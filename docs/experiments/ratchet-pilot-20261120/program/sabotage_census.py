#!/usr/bin/env python3
"""Part C's census: in a suite on file, does any acceptance check fail when one of the product's own existing tests
is made to fail? No model is called.

    python3 sabotage_census.py OUT.json [--workers N] RUN [RUN ...]

RUN is a ratchet.py run folder whose work folder holds an acceptance suite (work/acceptance, with
work/ratchet/acceptance.json). For each one:

  1. The file to sabotage is the one prove_fail.py takes: the first `test/*.test.js` of the starting product (the
     work repository's first commit) that is still there. A product that started with no test file is listed so.
  2. A copy of the work folder gets one failing test appended to that file (prove_fail.SABOTAGE).
  3. The manifest's commands are run on that copy, the last entry first, each the way gate.py runs a clause command
     (a command that fails is run a second time and counts as failing only if it fails again; the run's own
     named-output rule applies). The first command that fails is then run on an untouched copy: if it passes there,
     the sabotaged copy is **noticed** by that check and the search stops; if it fails there too it decides nothing
     and the search goes on.
  4. When no command is left, the sabotaged copy is **unnoticed**: no check of the suite can tell that an existing
     test fails.

This asks what `prove_fail.py --only sabotage` asks (the registered command) and stops at the first check that
notices, where that script runs every check on the build and on the copy. The last entry goes first because the
clause that says existing behaviour stays tends to stand at the end of a specification.
"""
import concurrent.futures
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import gate as gate_module
import prove_fail


def copy(work, scratch, label):
    folder = Path(tempfile.mkdtemp(prefix=f"{label}-", dir=scratch))
    shutil.rmtree(folder)
    shutil.copytree(work, folder, symlinks=True, ignore=shutil.ignore_patterns("node_modules"))
    return folder


def one(run):
    run = Path(run).resolve()
    work = run / "work"
    record = json.loads((run / "run.json").read_text())
    row = {"run": run.name, "root": run.parent.name, "case": record.get("case"), "model": record.get("model"), "effort": record.get("effort"),
           "enrich": record.get("enrich")}
    try:
        manifest = json.loads((work / "ratchet" / "acceptance.json").read_text())
        row["checks"] = len(manifest)
        target = prove_fail.sabotage_target(work)
        if not target:
            return dict(row, result="no existing test file")
        named = bool(record.get("named_checks", True))
        scratch = Path(tempfile.mkdtemp(prefix="sabotage-census-"))
        try:
            bad = copy(work, scratch, "sabotaged")
            with (bad / target).open("a") as handle:
                handle.write(prove_fail.SABOTAGE)
            temp = Path(tempfile.mkdtemp(prefix="tmp-", dir=scratch))
            clean, tried, undecided = None, 0, []
            for ident in reversed(list(manifest)):
                entry = manifest[ident]
                command = entry.get("command") if isinstance(entry, dict) else None
                if not command:
                    continue
                tried += 1
                if gate_module.twice(command, bad, {"TMPDIR": str(temp)}, ident if named else None)["pass"]:
                    continue
                clean = clean or copy(work, scratch, "clean")
                if gate_module.twice(command, clean, {"TMPDIR": str(temp)}, ident if named else None)["pass"]:
                    return dict(row, result="noticed", sabotaged_file=target, noticed_by=ident, commands_tried=tried, fail_on_both=undecided)
                undecided.append(ident)
            return dict(row, result="unnoticed", sabotaged_file=target, commands_tried=tried, fail_on_both=undecided)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        return dict(row, result="could not be measured", error=f"{type(error).__name__}: {error}"[:300])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    workers = 3
    if "--workers" in argv:
        workers = int(argv[argv.index("--workers") + 1])
        del argv[argv.index("--workers"):argv.index("--workers") + 2]
    if len(argv) < 2:
        raise SystemExit(__doc__)
    out, runs = Path(argv[0]), argv[1:]
    rows = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for row in pool.map(one, runs):
            rows.append(row)
            print(f"{row['root']}/{row['run']} | {row.get('model')} {row.get('effort')} | {row.get('checks', '?')} checks | {row['result']}"
                  + (f" by {row['noticed_by']} after {row['commands_tried']} command(s)" if row["result"] == "noticed" else "")
                  + (f" ({row['error']})" if row.get("error") else ""), flush=True)
            out.write_text(json.dumps(rows, indent=1) + "\n")
    counts = {}
    for row in rows:
        counts[row["result"]] = counts.get(row["result"], 0) + 1
    print("in all:", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
