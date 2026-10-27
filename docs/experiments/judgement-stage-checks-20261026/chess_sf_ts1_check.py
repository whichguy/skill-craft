"""The two Grok chess-sf runs under TS1, looked at closely (2026-10-26): whether each reached its last item's test-spec,
and whether 12a23d passes TS1 once its structural requirements are marked with the recorded commands that observe them.
Usage: python3 -B chess_sf_ts1_check.py <skills/shiploop/scripts>"""
import copy
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import shiploop_primary as primary
import shiploop_store as store

for name in ("20261024/chess-sf-full-12a23d", "20261024/chess-sf-full-ed3292"):
    for run in (Path.home() / "e2e-runs" / name).glob(".shiploop-runs/*/run"):
        state = store.read_record(run / "state.md")
        last = copy.deepcopy(state)
        last["work_index"] = len(state["work_items"]) - 1
        item = str(state["work_items"][-1]["id"])
        spec = primary._current_result(last, item, "test-spec")
        commands = primary._recorded_commands(last)
        print(f"{name}: last item {item} test-spec recorded: {spec is not None}; recorded commands: {len(commands)}")
        if spec is None:
            print("  the run never reached its last item's test-spec, so TS1 is not judged on it")
            continue
        deploy = next(c for c in commands if c.startswith("sf project deploy"))
        secrets = next(c for c in commands if "accesstoken" in c)
        rules = next(c for c in commands if "SLChessRulesTest" in c)
        rows = [{"requirement": "R-1", "command": deploy}, {"requirement": "R-2", "command": deploy},
                {"requirement": "R-11", "command": rules}, {"requirement": "R-14", "command": secrets}]
        for row in rows:
            print(f"  mark {row['requirement']} with: {row['command'][:90]}")
        try:
            primary.check_test_spec(last, "test-spec", dict(spec, outcome="done", suite_requirements=rows))
            print("  TS1: accepted")
        except primary.PrimaryError as exc:
            print("  TS1: refused:", str(exc)[:160])
