#!/usr/bin/env python3
"""Does a delivery's own check for an answered clause tell the answered build from the plain one? No model is called.

    python3 answer_check.py ANSWERED_RUN PLAIN_RUN OUT.json

Part D3 of the program of journal section 26 (reading RD3.4). ANSWERED_RUN is a ratchet.py run made from a
specification revised with the requester's answer: its clauses that carry `Source: answer` are the answer, and its
acceptance suite has a check for each. PLAIN_RUN is a run made from the same specification without the answer,
stopped after its build.

Every acceptance check of ANSWERED_RUN is run twice: on its own build as it stands, and on a copy of PLAIN_RUN's
build with ANSWERED_RUN's acceptance tests, manifest and specification laid over it (gate.py, clauses only, nothing
restored). OUT.json holds, for each answered clause, whether its check passes on its own build and fails on the
plain one, and the whole lists of failing checks on both.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import gate as gate_module
import ratchet


def copy_tree(work, scratch, label):
    folder = Path(tempfile.mkdtemp(prefix=f"answer-{label}-", dir=scratch))
    shutil.rmtree(folder)
    shutil.copytree(work, folder, symlinks=True, ignore=shutil.ignore_patterns("node_modules"))
    return folder


def lay_over(source, folder):
    for name in gate_module.FROZEN_PATHS:
        target = folder / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
        if (source / name).is_dir():
            shutil.copytree(source / name, target)
        elif (source / name).is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / name, target)


def measure(folder, scratch, label):
    temp = Path(tempfile.mkdtemp(prefix=f"tmp-{label}-", dir=scratch))
    record = gate_module.gate(folder, clauses_only=True, no_restore=True, config={}, extra_env={"TMPDIR": str(temp)}, named=True)
    return {"failing": sorted(record["failing"]), "ids": sorted(record["clauses"]),
            "tails": {ident: record["clauses"][ident].get("tail", [])[-6:] for ident in sorted(record["failing"])}}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 3:
        raise SystemExit(__doc__)
    answered, plain, out = Path(argv[0]).resolve(), Path(argv[1]).resolve(), Path(argv[2])
    clauses = ratchet.read_spec(answered / "work")
    answer_ids = [ident for ident, row in clauses.items() if re.match(r"answer\b", row["source"])]
    snaps = json.loads((plain / "run.json").read_text())["snapshots"]
    build = next(snap["commit"] for snap in snaps if snap["label"] == "build-1")
    scratch = Path(tempfile.mkdtemp(prefix="answer-check-"))
    try:
        own = measure(copy_tree(answered / "work", scratch, "own"), scratch, "own")
        other = Path(tempfile.mkdtemp(prefix="answer-plain-", dir=scratch))
        archive = subprocess.run(["git", "-C", str(plain / "work"), "archive", build], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(other)], input=archive, check=True)
        shutil.copytree(plain / "work" / ".git", other / ".git", symlinks=True)
        lay_over(answered / "work", other)
        on_plain = measure(other, scratch, "plain")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    rows = {ident: {"statement": clauses[ident]["statement"], "has_check": ident in own["ids"],
                    "passes_on_own_build": ident in own["ids"] and ident not in own["failing"],
                    "fails_on_plain_build": ident in on_plain["failing"]} for ident in answer_ids}
    report = {"answered_run": answered.name, "plain_run": plain.name, "plain_build_commit": build, "answer_clauses": rows,
              "checks": len(own["ids"]), "failing_on_own_build": own["failing"], "failing_on_plain_build": on_plain["failing"],
              "tails_on_plain_build": {ident: on_plain["tails"].get(ident) for ident in answer_ids}}
    out.write_text(json.dumps(report, indent=1) + "\n")
    told = sum(1 for row in rows.values() if row["passes_on_own_build"] and row["fails_on_plain_build"])
    print(f"{answered.name} against {plain.name}: {len(rows)} answered clause(s) {sorted(rows)}; {told} whose check passes on its own build and "
          f"fails on the plain one; checks failing on own build {len(own['failing'])} of {len(own['ids'])}, on the plain build {len(on_plain['failing'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
