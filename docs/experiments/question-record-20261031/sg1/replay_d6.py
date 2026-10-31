#!/usr/bin/env python3
"""Replay the SHIPPED step-plan proof-order refusal (``shiploop_item_scope.proof_order_refusal``, SDLC gates D6) on every
accepted step plan the saved runs keep, read-only.

For each done step-plan the base is the first step's base commit from the run's iteration ledger; without a ledger (a
plan sent back before one was written) the first item's base is the planning close, the last commit whose subject records
the knowledge "at prepare"; a later item without a ledger is skipped as unjudged.  ``exists(path)`` is ``git cat-file -e
<base>:<path>`` in the run's repository.  Each row also lists the item's implement outcomes after that plan, and the
send-back summary, so a refusal can be told from a false one.  Usage: replay_d6.py SHIPLOOP_SCRIPTS GLOB [GLOB ...]
"""
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import shiploop_item_scope as scope  # noqa: E402
import shiploop_store as store  # noqa: E402

RUN_GLOBS = (".shiploop-runs/*/run", "work/.shiploop")


def base_for(run: Path, repo: str, action: str, first_item: bool) -> str | None:
    for ledger in run.glob("iterations/*.json"):
        try:
            plans = json.loads(ledger.read_text()).get("plans") or {}
        except (OSError, ValueError):
            continue
        row = (plans.get(action) or {}).get("S1") or {}
        if row.get("base"):
            return row["base"]
    if first_item:
        found = subprocess.run(["git", "-C", repo, "log", "-1", "--all", "--format=%H", "--grep", "knowledge at prepare"],
                               capture_output=True, text=True).stdout.strip()
        return found or None
    return None


def main() -> None:
    seen, totals = set(), {"runs": 0, "plans": 0, "unjudged": 0, "refused": 0}
    for pattern in sys.argv[2:]:
        for out in sorted(Path(p) for p in glob.glob(os.path.expanduser(pattern))):
            for run in sorted(p for g in RUN_GLOBS for p in out.glob(g)):
                if run.resolve() in seen:
                    continue
                seen.add(run.resolve())
                try:
                    state = store.read_record(run / "state.md")
                except Exception:  # noqa: BLE001 - a run the current reader refuses is skipped
                    continue
                totals["runs"] += 1
                repo, history, accepted = state.get("repo"), state.get("history") or [], state.get("accepted") or {}
                items = [str(w.get("id")) for w in state.get("work_items") or () if isinstance(w, dict)]
                for index, row in enumerate(history):
                    plan = accepted.get(row.get("action"))
                    if row.get("stage") != "step-plan" or row.get("outcome") != "done" or not isinstance(plan, dict):
                        continue
                    totals["plans"] += 1
                    base = base_for(run, repo, row["action"], bool(items) and row.get("workitem") == items[0]) if repo else None
                    outcomes, sendbacks = [], []
                    for later in history[index + 1:]:
                        if later.get("workitem") != row.get("workitem"):
                            continue
                        if later.get("stage") == "step-plan":
                            break
                        if later.get("stage") == "implement":
                            outcomes.append(later.get("outcome"))
                            if later.get("outcome") == "send-back":
                                result = accepted.get(later.get("action")) or {}
                                sendbacks.append(str(result.get("summary") or "")[:300])
                    if not base:
                        totals["unjudged"] += 1
                        refusal = None
                    else:
                        def exists(path, base=base):
                            return subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{base}:{path}"],
                                                  capture_output=True).returncode == 0
                        refusal = scope.proof_order_refusal(plan, exists)
                        totals["refused"] += bool(refusal)
                    print(json.dumps({"run": f"{out.parent.name}/{out.name}", "item": row.get("workitem"),
                                      "base": (base or "")[:12], "refusal": refusal, "implement_outcomes": outcomes,
                                      "send_backs": sendbacks}))
    print(json.dumps({"summary": totals}))


if __name__ == "__main__":
    main()
