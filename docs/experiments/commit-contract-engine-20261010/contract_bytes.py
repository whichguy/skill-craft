#!/usr/bin/env python3
"""Bytes the commit-policy clause adds to the frozen Improve contract, per stage and route, with the real builder.

Repeat with:  PYTHONDONTWRITEBYTECODE=1 SHIPLOOP_PROGRESS=off python3 docs/experiments/commit-contract-engine-20261010/contract_bytes.py

It borrows the test fixture of test/shiploop-actual-improve-cli.test.py (a neutral Git repository and a real bound
child) and rebuilds the contract with navigator.improve_start_contract for each Improve stage on the inline and the
delegated (ask-agent) route.  "added" is the bytes of the new commit-policy clause less the clause of 658ff4e3 it
replaced (the parent-return path is in both).  "thin" is the same contract with the model-written Environment padded
until, under the old clause, only the thinnest saved headroom was left (spike S, batch 1012: a carry-forward child of
the saved Grok run r1-battleship-grok-none, 8,135 of 9,216 bytes).  Writes contract-bytes.json beside this file.
"""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("improve_cli_test", ROOT / "test" / "shiploop-actual-improve-cli.test.py")
module = importlib.util.module_from_spec(spec)
sys.modules["improve_cli_test"] = module
spec.loader.exec_module(module)

cls = module.ImproveCommitContractTests
case = cls("test_the_commit_clause_costs_what_the_thinnest_saved_contract_can_spare_on_every_stage_and_route")
case.setUp()
try:
    case.begin("plan")
    navigator, loop_contract, store, bridge = module.navigator, module.loop_contract, module.store, module.bridge
    state = store.read_record(case.run / "state.md")
    parent_return = str(bridge.receipt_path(case.bound).with_name("parent-return.md"))
    old_clause = case.BASE_COMMIT_CLAUSE + parent_return + "."
    rows = []
    for stage in case.IMPROVE_STAGES:
        def build(route, environment="x"):
            chosen = dict(state, active_improve=dict(state["active_improve"], stage=stage), delegation=route)
            return navigator.improve_start_contract(None, case.run, chosen, "".join(
                "## " + name + "\n" + (environment if name == "Environment" else "x") + "\n\n"
                for name in navigator.OPENING_SECTIONS))
        inline = build("inline")
        authority = inline["context"]["authority"]
        clause = authority[authority.index("Commit policy:"):]
        added = loop_contract.text_bytes(clause) - loop_contract.text_bytes(old_clause)
        # the thin case: padded on the inline route until the old clause left only the thinnest saved headroom
        pad = (loop_contract.CONTRACT_BUDGET - case.THINNEST_SAVED_HEADROOM
               - (loop_contract.compact_bytes(inline) - added) + 1)
        for route in ("inline", "ask-agent"):
            minimal, thin = build(route), build(route, "a" * pad)
            now = loop_contract.compact_bytes(minimal)
            rows.append({"stage": stage, "route": route, "minimal_bytes_before": now - added, "minimal_bytes_after": now,
                         "added": added, "thin_bytes_after": loop_contract.compact_bytes(thin),
                         "thin_headroom_after": loop_contract.CONTRACT_BUDGET - loop_contract.compact_bytes(thin),
                         "allowance_printed_before": loop_contract.CONTRACT_BUDGET - (now - added),
                         "allowance_printed_after": loop_contract.CONTRACT_BUDGET - now})
    result = {"contract_budget": loop_contract.CONTRACT_BUDGET, "thinnest_saved_headroom": case.THINNEST_SAVED_HEADROOM,
              "clause_before_bytes_without_path": loop_contract.text_bytes(case.BASE_COMMIT_CLAUSE + "."),
              "clause_after_bytes_without_path": loop_contract.text_bytes(clause) - loop_contract.text_bytes(parent_return),
              "path_bytes_in_this_fixture": loop_contract.text_bytes(parent_return), "rows": rows}
    out = Path(__file__).with_name("contract-bytes.json")
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print("added per stage/route:", sorted({row["added"] for row in rows}))
    print("tightest headroom after at the thin case:", min(row["thin_headroom_after"] for row in rows))
    print("wrote", out)
finally:
    case.tearDown()
