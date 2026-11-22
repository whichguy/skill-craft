#!/usr/bin/env python3
"""Replay, on saved deliveries, the commands the rebuilt release-verify rule adds (round 15).

Written for the candidate at 62676fc0e0dacb0ca8febd7f6f2424684c707b47, whose scripts it must be given: the later
build has no ``copy_floors`` (it measures the count; see ``gate_on_file.py``).

For each run folder: ``release_commands`` (the candidate's own function, with the place taken as a clean copy of the
returned result) lists the consumer checks release-plan recorded and the regression commands ShipLoop adds after
them; ``copy_floors`` gives each recorded command its floor.  Every ADDED command is then run once in an exported
copy of the delivered tree (no Git data, nothing ignored), the way release-verify would run it, and judged by the
rule: refused when it exits non-zero, does not end within the limit, runs fewer tests than its floor, or has a floor
and a count ShipLoop cannot read.

Each command starts in its own process group with no terminal and its output in a file, and the whole group is
stopped when the command ends or the limit passes, so a test that leaves a server behind cannot hold this script
or outlive it.

Usage: python3 -I replay_on_file.py SHIPLOOP_SCRIPTS_DIR LIMIT_SECONDS NAME=RUN_FOLDER ...
"""
import glob
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, sys.argv[1])
import shiploop_test_counts as counts  # noqa: E402
import shiploop_test_loop as tl  # noqa: E402

ENV = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"], "TMPDIR": os.environ.get("TMPDIR", "/tmp")}
# The place release-verify observes once a return is recorded: release_commands adds commands only there.
tl.observation = lambda root, state, stage: {"where": "returned-result"} if stage == "release-verify" else None


def run_bounded(command, cwd, limit, log):
    """(exit code or None when it did not end, seconds, output) for one command in its own process group."""
    started = time.monotonic()
    with open(log, "wb") as out:
        proc = subprocess.Popen(["/bin/sh", "-c", command], cwd=cwd, env=ENV, stdin=subprocess.DEVNULL, stdout=out,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            code = None
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)  # the group this call created, nothing else
            except ProcessLookupError:
                break
            time.sleep(2)
        proc.wait()
    return code, time.monotonic() - started, open(log, errors="replace").read()


def main(limit, argv):
    total = added_runs = added_commands = refused_commands = 0
    for spec in argv:
        name, folder = spec.split("=")
        run = sorted(glob.glob(folder + "/.shiploop-runs/*/run"))[-1]
        state = json.loads(re.search(r"```shiploop-state\n(.*?)\n```", open(run + "/state.md", errors="replace").read(),
                                     re.S).group(1))
        commands, _reason = tl.release_commands(run, state)
        floors = tl.copy_floors(run, state, commands)
        checks = [row for row in commands if not row.get("from_step_plan")]
        added = [row for row in commands if row.get("from_step_plan")]
        total += 1
        bound = sum(1 for row in checks if row["command"] in floors)
        if not added:
            print(f"{name:24s} nothing added: {len(checks)} consumer check(s), {bound} of them a recorded test command"
                  " held to its floor")
            continue
        added_runs += 1
        head = json.load(open(folder + "/result.json"))["committed"]["head"]
        with tempfile.TemporaryDirectory(prefix="replay-") as scratch:
            clone, tree = scratch + "/clone", scratch + "/tree"
            subprocess.run(["git", "clone", "-q", folder + "/delivery/work.bundle", clone], check=True)
            os.mkdir(tree)
            tar = subprocess.run(["git", "-C", clone, "archive", head], check=True, capture_output=True).stdout
            subprocess.run(["tar", "-x", "-C", tree], input=tar, check=True)
            print(f"{name:24s} consumer checks: " + "; ".join("`" + row["command"] + "`" for row in checks))
            for row in added:
                command = row["command"]
                code, seconds, output = run_bounded(command, tree, limit, scratch + "/out.txt")
                tally = counts.count(output, code) if code is not None else None
                ran = tally["ran"] if tally else None
                floor = (floors.get(command) or {}).get("floor")
                if code is None:
                    verdict = f"REFUSED (did not end in {int(limit)} s)"
                elif code != 0:
                    verdict = f"REFUSED (exit {code})"
                elif floor is not None and ran is None:
                    verdict = "REFUSED (a floor and no readable count)"
                elif floor is not None and ran < floor:
                    verdict = f"REFUSED (ran {ran}, floor {floor})"
                else:
                    verdict = "passes"
                added_commands += 1
                refused_commands += verdict != "passes"
                print(f"{'':24s} adds `{command}`: floor {floor}, ran {ran}, {seconds:.0f} s -> {verdict}")
                if verdict != "passes":
                    for line in output.strip().splitlines()[-12:]:
                        print(f"{'':24s}   | {line[:200]}")
    print(f"\n{added_runs} of {total} deliveries get an added command ({added_commands} command(s) in all); "
          f"{refused_commands} would be refused")


main(float(sys.argv[2]), sys.argv[3:])
