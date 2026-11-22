#!/usr/bin/env python3
"""Run the rebuilt release-verify gate itself on saved deliveries (round 15), without writing into them.

``replay_on_file.py`` runs each ADDED command alone in a fresh export.  This runs ShipLoop's own ``verify`` for
``release-verify`` on each saved run's state: the consumer checks release-plan recorded, then the commands ShipLoop adds, in ONE clean
copy of the tree the run's return receipt names, with the floors, the judging and the refusal text of the gate.  So it
also shows what a consumer check leaves behind for the command added after it, and whether a recorded command meets its floor
in a copy.

Nothing is written into a saved run: the receipt is read with ``workspace.returned_result``; the copy is made the way
``export_returned_result`` makes it (a private index, ``read-tree``, ``checkout-index``) but in a temporary workspace
folder whose ``run`` and ``worktree`` entries are links to the saved ones (so a check written as ``../run/scratch/x``
resolves); the commands run through ``lint.run_argv`` (the gate's runner without its recovery record); the gate's
record is read from the writes ``verify`` returns and is not stored.  A consumer check that names the saved run's
scratch folder runs the file it names; the scratch folder's listing before and after is compared and reported.

Usage: python3 -I gate_on_file.py SHIPLOOP_SCRIPTS_DIR LIMIT_SECONDS NAME=RUN_FOLDER ...
"""
import glob
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import shiploop_lint as lint  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as tl  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402

REAL_RETURNED = workspace.returned_result


def listing(folder):
    """{relative path: (size, mtime)} of a folder's files; empty when there is none."""
    found = {}
    for path in Path(folder).rglob("*") if Path(folder).is_dir() else ():
        if path.is_file() and not path.is_symlink():
            stat = path.stat()
            found[str(path.relative_to(folder))] = (stat.st_size, int(stat.st_mtime))
    return found


def gate(name, folder, limit):
    run = Path(sorted(glob.glob(folder + "/.shiploop-runs/*/run"))[-1])
    saved = run.parent
    state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", (run / "state.md").read_text(errors="replace"),
                                 re.S).group(1))
    found = REAL_RETURNED(saved)
    if found is None:
        print(f"{name:24s} no completed return is recorded: the stage would run in the work area, with nothing added")
        return None
    before = listing(run / "scratch")
    with tempfile.TemporaryDirectory(prefix="gate-") as scratch:
        mine = Path(scratch) / "ws"
        mine.mkdir()
        os.symlink(run, mine / "run")
        os.symlink(saved / "worktree", mine / "worktree")
        copy = mine / "consumer-check"
        place = {**found, "copy": str(copy)}

        def export(_root):
            if copy.exists():
                shutil.rmtree(copy)
            index = Path(scratch) / "index"
            for args in (("read-tree", found["tree"]), ("checkout-index", "-a", "-f", "--prefix=" + str(copy) + "/")):
                done = workspace._git(saved / "worktree", *args, env={"GIT_INDEX_FILE": str(index)}, readonly=True)
                if done.returncode:
                    raise workspace.WorkspaceError(done.stderr.decode("utf-8", "replace").strip())
            copy.mkdir(exist_ok=True)
            index.unlink()
            return {**place, "path": str(copy)}

        tl.observation = lambda root, st, stage: ({"where": "returned-result", **place}
                                                  if stage == "release-verify" else None)
        workspace.export_returned_result = export
        writes, refusal = tl.verify(run, state, "", "gate-on-file", "release-verify", runner=lint.run_argv,
                                    command_timeout=limit)
    record_path = Path(tempfile.mkdtemp(prefix="gate-record-")) / "record.md"
    (relative, text), = writes.items()
    record_path.write_text(text, encoding="utf-8")
    record = store.read_record(record_path)
    shutil.rmtree(record_path.parent)
    after = listing(run / "scratch")
    changed = sorted(key for key in set(before) | set(after) if before.get(key) != after.get(key))
    verdict = "PASSES" if record["passed"] else "REFUSED (" + str(record.get("disposition")) + ")"
    print(f"{name:24s} {verdict}")
    for row in record["runs"]:
        ran = (row.get("counts") or {}).get("ran")
        command = row["command"].replace(folder, "<delivery>")
        print(f"{'':24s}   {'added' if row.get('from_step_plan') else 'check'} [{row['suite']}] {command[:120]} -> {row['status']}"
              f", ran {ran}, floor {row.get('accepted_ran')}, {row.get('seconds', 0):.0f} s")
    if refusal:
        lines = refusal.splitlines()
        for line in lines[:2] + lines[-1:]:
            print(f"{'':24s}   | {line.replace(folder, '<delivery>').replace(str(copy), '<copy>')[:1500]}")
    if changed:
        print(f"{'':24s}   the saved run's scratch folder changed: " + ", ".join(changed[:6]))
    return record


def main(limit, argv):
    total = passed = added = bound = 0
    refused = []
    for spec in argv:
        name, folder = spec.split("=")
        record = gate(name, folder, limit)
        if record is None:
            continue
        total += 1
        passed += bool(record["passed"])
        added += sum(1 for row in record["runs"] if row.get("from_step_plan"))
        bound += sum(1 for row in record["runs"] if row.get("accepted_ran") is not None)
        if not record["passed"]:
            refused.append(name)
    print(f"\n{total} deliveries through the gate: {passed} pass, {total - passed} refused"
          + (" (" + ", ".join(refused) + ")" if refused else "")
          + f"; {added} command(s) added by ShipLoop; {bound} command run(s) held to a floor")


main(float(sys.argv[2]), sys.argv[3:])
