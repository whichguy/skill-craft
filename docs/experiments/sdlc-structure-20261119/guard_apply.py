#!/usr/bin/env python3
"""Merge the guard round's step cases into a throwaway checkout's step_cases.json (round 6, guard round).

The cases in guard-step-cases.json exist only for this experiment. slice.py reads test/shiploop_e2e/step_cases.json of
the checkout it runs from, and several hermetic suites walk every case in that file, so the cases are added to a
worktree made for the round (git worktree add --detach <path> HEAD) and never to the checkout itself.

Usage: python3 -I guard_apply.py WORKTREE
"""
import json
import pathlib
import sys


def main(worktree):
    here = pathlib.Path(__file__).resolve().parent
    target = pathlib.Path(worktree) / "test" / "shiploop_e2e" / "step_cases.json"
    if here.parents[2] == pathlib.Path(worktree).resolve():
        raise SystemExit("refusing to change the checkout this script lives in: pass a throwaway worktree")
    cases = json.loads(target.read_text())
    extra = {name: case for name, case in json.loads((here / "guard-step-cases.json").read_text()).items()
             if not name.startswith("_")}
    cases.update(extra)
    target.write_text(json.dumps(cases, indent=1) + "\n")
    print("added to", target, ":", ", ".join(extra))


if __name__ == "__main__":
    main(sys.argv[1])
