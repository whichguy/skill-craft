#!/usr/bin/env python3
"""Replay a rule B extension to the `minimum` regression command on saved step plans, read-only (README.md, "Needs-later-step
replay").

    python3 -I replay_rule_b_minimum.py TRACES.txt OUT.jsonl

The minimum regression command runs at every step before the last. The candidate rule: a path that the command names (in its
words or its inline code), which the item base lacks and which only a later step than S1 declares, means the command cannot pass
at S1's test stage. Each plan is judged at the worktree commit it was accepted on (as replay_a1.py). Each flag is paired with
the item's first test-stage outcome after the plan.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import proofscore  # noqa: E402
from proofscore import scope  # noqa: E402
from replay_a1 import accepted_at, commit_at, in_tree, record, result_of  # noqa: E402


def flags(plan: dict, toplevel: str, tree: str) -> list[dict]:
    steps = [row for row in plan.get("steps") or () if isinstance(row, dict)]
    if len(steps) < 2:
        return []
    first = set(str(path) for path in steps[0].get("paths") or ())
    later: dict[str, str] = {}
    for step in steps[1:]:
        for path in step.get("paths") or ():
            later.setdefault(str(path), str(step.get("id")))
    found = []
    for row in plan.get("test_commands") or ():
        # The minimum regression may sit on a regression row or on a focused row marked "regression": true
        # (shiploop_test_loop: a focused command that is also the regression command).
        if not isinstance(row, dict) or not row.get("minimum") or not (row.get("suite") == "regression" or row.get("regression") is True):
            continue
        command = str(row.get("command") or "")
        for path in dict.fromkeys(list(scope.command_paths(command)) + proofscore.named_paths(command)):
            if path in first or path not in later:
                continue
            if in_tree(toplevel, tree, path) is False:
                found.append({"command": command[:200], "path": path, "declared_by": later[path]})
    return found


def main() -> int:
    out = []
    for trace in open(sys.argv[1], encoding="utf-8").read().split():
        run = os.path.dirname(trace)
        try:
            state = record(os.path.join(run, "state.md"))
        except OSError:
            continue
        history = state.get("history", [])
        times = accepted_at(run)
        for index, row in enumerate(history):
            if row.get("stage") != "step-plan" or row.get("outcome") != "done":
                continue
            item = row.get("workitem")
            base_file = os.path.join(run, "lint", "items", f"{item}.md")
            plan = state.get("accepted", {}).get(row["action"])
            if not os.path.exists(base_file) or not isinstance(plan, dict):
                continue
            base = record(base_file)
            if not base.get("tree") or not base.get("toplevel") or not os.path.isdir(base["toplevel"]):
                continue
            commit = commit_at(base["toplevel"], times[row["action"]]) if row["action"] in times else None
            hits = flags(plan, base["toplevel"], commit or base["tree"])
            outcome = None
            for later_row in history[index + 1:]:
                if later_row.get("workitem") != item:
                    continue
                if later_row.get("stage") == "step-plan":
                    break
                if later_row.get("stage") == "test":
                    result = result_of(run, state, later_row["action"])
                    outcome = later_row.get("outcome") + (": " + str(result.get("headline") or "")[:100]
                                                          if later_row.get("outcome") == "send-back" else "")
                    break
            out.append({"run": run.replace(os.path.expanduser("~") + "/", "~/"), "item": item, "action": row["action"],
                        "flags": hits, "first_test": outcome})
    with open(sys.argv[2], "w", encoding="utf-8") as handle:
        handle.writelines(json.dumps(row, sort_keys=True) + "\n" for row in out)
    flagged = [row for row in out if row["flags"]]
    print("plans with a base", len(out), "flagged", len(flagged))
    for row in flagged:
        print(" ", row["flags"][0]["path"], "by", row["flags"][0]["declared_by"], "|", (row["first_test"] or "no test stage")[:100], "|", row["run"][-60:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
