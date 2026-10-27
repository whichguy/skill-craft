"""Replay TS1 and IN1 (this branch's shiploop_primary.check_test_spec and shiploop_request.check) on every saved run:
TS1 as at the last work item's done test-spec (its accepted result resubmitted), then with a suite row for each refused
requirement whose spec entry is about the tests; IN1 on the accepted intake result."""
import copy
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import shiploop_knowledge_home as knowledge
import shiploop_planning_revision as pr
import shiploop_primary as primary
import shiploop_request as request
import shiploop_store as store

ABOUT_TESTS = re.compile(r"\b(tests?|unittest|node --test|pytest|test_\w+\.py)\b", re.IGNORECASE)
for out in sorted(Path.home().glob("e2e-runs/2026*/*")):
    for run in out.glob(".shiploop-runs/*/run"):
        try:
            state = store.read_record(run / "state.md")
        except Exception:
            continue
        name = f"{out.parent.name}/{out.name}"
        acc = state.get("accepted") or {}
        intake = next((acc.get(h["action"]) for h in state.get("history") or () if h.get("stage") == "intake" and h.get("outcome") == "done"), None)
        in1 = "no intake"
        if intake:
            try:
                request.check(state["prompt"], "intake", intake); in1 = "accepted"
            except request.RequestError as exc:
                in1 = "REFUSED: " + str(exc)[:70]
        items = state.get("work_items") or []
        if primary.primary_ids(state) is None or not items:
            print(json.dumps({"run": name, "ts1": "no primary list (predates it)", "in1": in1})); continue
        last = copy.deepcopy(state); last["work_index"] = len(items) - 1
        cur = pr.current_actions(last)
        submitted = acc.get(cur.get((str(items[-1]["id"]), "test-spec"))) or {"outcome": "done", "test_cases": []}
        submitted = dict(submitted, outcome="done")
        def ts1(result, last=last):
            try:
                primary.check_test_spec(last, "test-spec", result); return None
            except primary.PrimaryError as exc:
                return re.search(r"Missing: ([^.]*)\.", str(exc)).group(1) if "Missing:" in str(exc) else str(exc)[:90]
        first = ts1(submitted)
        row = {"run": name, "ts1": "accepted" if first is None else "refused: " + first, "in1": in1}
        if first and first.startswith("R-"):
            held = knowledge.entries(Path(str(state["repo"])), "spec.md")
            commands = primary._recorded_commands(last)
            marks = [{"requirement": r, "command": commands[0]} for r in first.split(", ")
                     if commands and r in held and ABOUT_TESTS.search(held[r].text.split("\n")[0])]
            if marks:
                second = ts1(dict(submitted, suite_requirements=marks))
                row["with suite rows for " + ", ".join(m["requirement"] for m in marks)] = "accepted" if second is None else "still refused: " + second
        print(json.dumps(row))
