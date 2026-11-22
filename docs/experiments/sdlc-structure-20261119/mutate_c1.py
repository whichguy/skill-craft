#!/usr/bin/env python3
"""Mutants of the rebuilt release-verify rule: each breaks one decision; the unit class must fail on each.
Usage: python3 mutate_c1.py TREE_COPY   (a copy: the engine file is rewritten and restored for each mutant)"""
import subprocess, sys
from pathlib import Path
root = Path(sys.argv[1])
engine = root / "skills/shiploop/scripts/shiploop_test_loop.py"
original = engine.read_text(encoding="utf-8")
MUTANTS = [
    ("every item's commands, not the last item's",
     "    for row in regression_commands(state, last_item=True):\n        if row[\"command\"] not in held:",
     "    for row in regression_commands(state):\n        if row[\"command\"] not in held:"),
    ("the last item chosen before hosted commands are left out",
     "        local = ([row for row in rows if _remote_base(row, stateful) is None] for rows in per_item)\n",
     "        local = (rows for rows in per_item)\n"),
    ("a floor for any recorded command, not only the last item's",
     "        if command in selected and command in latest:",
     "        if command in latest:"),
    ("a floor from an action that did not end done",
     "        if row.get(\"outcome\") != \"done\" or row.get(\"stage\") == \"release-verify\":\n            continue\n",
     "        if row.get(\"stage\") == \"release-verify\":\n            continue\n"),
    ("an older count kept when the latest run is uncounted",
     "                    latest[str(run[\"command\"])] = (ran, relative) if isinstance(ran, int) else None",
     "                    if isinstance(ran, int):\n                        latest[str(run[\"command\"])] = (ran, relative)"),
    ("an unreadable record raises",
     "            except (OSError, store.StorageError):\n                continue\n            if not isinstance(record, Mapping) or not record.get(\"passed\"):",
     "            except (KeyboardInterrupt,):\n                continue\n            if not isinstance(record, Mapping) or not record.get(\"passed\"):"),
    ("a release-verify record sets the floor",
     "        if row.get(\"outcome\") != \"done\" or row.get(\"stage\") == \"release-verify\":\n            continue\n",
     "        if row.get(\"outcome\") != \"done\":\n            continue\n"),
    ("the refusal does not mark an added command",
     "(ADDED_MARK if run.get(\"from_step_plan\") else \"\")\n                     + \" -> \" + _explain(run, stage))",
     "(\"\")\n                     + \" -> \" + _explain(run, stage))"),
    ("an added command is sent to release-plan to be relabelled",
     "    elif stage in OUTER_SOURCES and not plans and all(run[\"status\"] == \"uncounted\" for run in failing):",
     "    elif stage in OUTER_SOURCES and all(run[\"status\"] == \"uncounted\" for run in failing):"),
    ("an unreadable count passes where a floor is bound",
     "                elif stage == \"release-verify\" and run[\"status\"] in PASSING and not run[\"counts\"]:",
     "                elif False and stage == \"release-verify\" and run[\"status\"] in PASSING and not run[\"counts\"]:"),
    ("a count below the floor passes",
     "                if run[\"status\"] == \"passed\" and run[\"counts\"] and run[\"counts\"][\"ran\"] < floor[\"floor\"]:",
     "                if False and run[\"status\"] == \"passed\" and run[\"counts\"] and run[\"counts\"][\"ran\"] < floor[\"floor\"]:"),
    ("a check with the same text is still added (the suite runs twice)",
     "        if row[\"command\"] not in held:\n            held.add(row[\"command\"])",
     "        if True:\n            held.add(row[\"command\"])"),
    ("commands are added where the checks run in place or in the work area",
     "    if not commands or not observed or observed[\"where\"] != \"returned-result\":\n        return commands, reason\n    held = {str(row.get(\"command\")) for row in commands}",
     "    if not commands:\n        return commands, reason\n    held = {str(row.get(\"command\")) for row in commands}"),
    ("the note on what is added next is always printed",
     "             if any(run.get(\"from_step_plan\") for run in failing) else \"\")",
     "             if True else \"\")"),
    ("the reply names only add-work",
     "report outcome send-back: \"\n            \"release-plan records it and the stages after it run again.",
     "report it: \"\n            \"release-plan records it and the stages after it run again."),
]
caught = 0
try:
    for name, old, new in MUTANTS:
        if original.count(old) != 1:
            print(f"NOT APPLIED ({original.count(old)} matches): {name}")
            continue
        engine.write_text(original.replace(old, new), encoding="utf-8")
        done = subprocess.run([sys.executable, "test/shiploop-test-loop.test.py", "ReturnedCopyRegressionTests"],
                              cwd=root, capture_output=True, text=True)
        failed = [line.split()[1] for line in done.stderr.splitlines() if line.startswith(("FAIL:", "ERROR:"))]
        caught += bool(failed)
        print(("caught by " + str(len(failed)) + ": " if failed else "SURVIVED: ") + name
              + ("  [" + failed[0][5:70] + "]" if failed else ""))
finally:
    engine.write_text(original, encoding="utf-8")
print(f"\n{caught} of {len(MUTANTS)} mutants caught")
