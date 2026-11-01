#!/usr/bin/env python3
"""Replay A1 (rule A over the test-class paths inside a Proof's inline code) on saved step plans, read-only (README.md,
"A1's replay").

    python3 -I replay_a1.py TRACES.txt OUT.jsonl

For every accepted step plan whose item has a recorded lint item base (RUN/lint/items/<item>.md names the run's worktree),
each step's Proof is read with ``proofscore.named_paths``. The base a plan is judged against is the worktree's commit at
the moment the step plan was accepted (its `complete` row in RUN/trace.jsonl; `git log -1 --until`), read with
`git cat-file -e`. The lint record's own tree is the item's LAST capture: after a send-back it can hold an implement
draft (A-shared-expenses-s1's held its draft test/service.test.js), which would hide the flag. A path is a flag when it
is test-class, the base lacks it, no earlier step declares it, the item is not all tests, and only the inline reading finds
it (``shiploop_item_scope.command_paths``, rule A's own reading, does not). Each flagged step is paired with its own implement
outcome: implement actions follow their step plan in step order, until the next step plan of the item. A plan with no
`complete` row or no commit before it is judged against the lint tree, as before.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import proofscore  # noqa: E402
from proofscore import scope  # noqa: E402

STATE = re.compile(r"```shiploop-state\n(.*?)\n```", re.S)


def record(path: str) -> dict:
    match = STATE.search(open(path, encoding="utf-8").read())
    return json.loads(match.group(1)) if match else {}


def in_tree(toplevel: str, tree: str, path: str) -> bool | None:
    try:
        done = subprocess.run(["git", "-C", toplevel, "cat-file", "-e", f"{tree}:{path}"], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.returncode == 0


def result_of(run: str, state: dict, action: str) -> dict:
    kept = state.get("accepted", {}).get(action)
    if isinstance(kept, dict):
        return kept
    path = os.path.join(run, "results", action + ".md")
    return (record(path).get("result") or {}) if os.path.exists(path) else {}


def accepted_at(run: str) -> dict[str, str]:
    """Action -> the ISO time its result was accepted, from RUN/trace.jsonl's command rows."""
    found: dict[str, str] = {}
    try:
        lines = open(os.path.join(run, "trace.jsonl"), encoding="utf-8").read().splitlines()
    except OSError:
        return found
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        for kept in row.get("accepted") or ():
            if isinstance(kept, dict) and kept.get("action") and row.get("at"):
                found.setdefault(kept["action"], row["at"])
    return found


def commit_at(toplevel: str, when: str) -> str | None:
    try:
        done = subprocess.run(["git", "-C", toplevel, "log", "-1", "--format=%H", "--until=" + when], capture_output=True,
                              text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() or None


def flags(plan: dict, toplevel: str, tree: str) -> list[dict]:
    item_paths = [str(path) for path in plan.get("paths") or ()]
    if item_paths and all(scope.classify(path) == "test" for path in item_paths):
        return []
    found, declared = [], set()
    for index, step in enumerate(row for row in plan.get("steps") or () if isinstance(row, dict)):
        proof = str(step.get("proof") or "")
        plain = set(scope.command_paths(proof))
        for path in proofscore.named_paths(proof):
            if path in plain or scope.classify(path) != "test" or path in declared:
                continue
            present = in_tree(toplevel, tree, path)
            if present is False:
                found.append({"step": str(step.get("id")), "index": index, "path": path, "proof": proof[:300]})
        declared.update(str(path) for path in step.get("paths") or ())
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
            implements = []
            for later in history[index + 1:]:
                if later.get("workitem") != item:
                    continue
                if later.get("stage") == "step-plan":
                    break
                if later.get("stage") == "implement":
                    result = result_of(run, state, later["action"])
                    implements.append(later.get("outcome") + (": " + str(result.get("headline") or "")[:100]
                                                              if later.get("outcome") == "send-back" else ""))
            commit = commit_at(base["toplevel"], times[row["action"]]) if row["action"] in times else None
            hits = flags(plan, base["toplevel"], commit or base["tree"])
            for hit in hits:
                hit["implement"] = implements[hit["index"]] if hit["index"] < len(implements) else None
            out.append({"run": run.replace(os.path.expanduser("~") + "/", "~/"), "item": item, "action": row["action"],
                        "base": commit or base["tree"], "base_kind": "commit" if commit else "lint-tree",
                        "steps": len(plan.get("steps") or ()), "flags": hits})
    with open(sys.argv[2], "w", encoding="utf-8") as handle:
        handle.writelines(json.dumps(row, sort_keys=True) + "\n" for row in out)
    flagged = [(row, hit) for row in out for hit in row["flags"]]
    print("plans with a base", len(out), "flagged steps", len(flagged))
    for row, hit in flagged:
        print(" ", hit["step"], hit["path"], "|", (hit["implement"] or "no implement")[:100], "|", row["run"][-60:])
    return 0


if __name__ == "__main__":
    sys.exit(main())
