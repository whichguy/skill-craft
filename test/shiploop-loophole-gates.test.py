#!/usr/bin/env python3
"""Known dodges of ShipLoop's result gates, each sent through the real CLI (owner, 2026-10-24).

``DODGES`` is one table. Each row is a way a model has met a gate's letter but not its purpose, in a live run or in the
template experiments. Each row:
1. builds the dodge from the stage's own done template;
2. submits it with the printed callback, and asserts the refusal;
3. submits the refusal's named next step with the same callback, and asserts it is accepted ("test the route, not the
   wording").

Rule (the run-5 batch, 2026-10-24): a new structured result field or gate adds its known-dodge row here, in the same
commit.

Not a dodge, so not here:
- A search of a code file for its contract docstring, confirmed `searched`. Step-plan duty 3 asks for that criterion
  (Code craft 2-3), and the template experiments' E2 samples did exactly that.
- A test of new code that fails to load on the item's base (``require`` of the module the item adds). That is a real
  failure, and ShipLoop reads it as RED.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("shiploop_callback_contract",
                                               ROOT / "test" / "shiploop-callback-contract.test.py")
contract = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = contract
_SPEC.loader.exec_module(contract)

FOCUSED = contract.FOCUSED
# A test-strategy target that keeps state between runs (F3), named by the rows that need one.
STATEFUL = {"target": "the shared service", "keeps_state": "yes", "base_state_route": "a clean namespace per run"}
STATEFUL_RUN = {"test-strategy": {"targets": [STATEFUL]}}


def commands(block: dict, change) -> dict:
    """``block`` with ``change`` applied to each of its test_commands rows (a copy)."""
    return {**block, "test_commands": [change(dict(row)) for row in block["test_commands"]]}


def focused(change):
    """A test_commands change that applies ``change`` to the focused rows only."""
    return lambda row: change(row) if row.get("suite") == "focused" else row


def guarded(prefix: str):
    """A dodge that puts ``prefix`` ahead of the focused command's tests."""
    return lambda block: commands(block, focused(lambda row: dict(row, command=prefix + row["command"])))


def targets(rows: list):
    """A test-strategy block whose targets are ``rows``."""
    return lambda block: {**block, "targets": rows}


# (label, where it was seen, stage, positioning results, dodge, refusal fragment, named exit). Each callable takes the
# stage's filled done template and returns a result block.
DODGES = [
    ("an executed criterion confirmed only by a search of the code",
     "run 4's source-grep confirmations (F1)", "step-plan", None,
     lambda block: commands(block, lambda row: dict(row, command="grep -q 'def build' src/build.py")
                            if row.get("criteria") else row),
     "every command naming them only searches text",
     lambda block: block),            # the named exit: a command that runs the code names the criterion
    ("a focused command behind a test -f guard", "run 4's W3 (F2)", "step-plan", None,
     guarded("test -f built.txt && "), "checks for a file or prints a path before its tests run", lambda block: block),
    ("a focused command behind an if-[ ! -e ] guard that prints a fake load error",
     "E3's smoke sample (F2)", "step-plan", None,
     guarded("if [ ! -e built.txt ]; then echo 'Error: Cannot find module built.txt'; exit 1; fi; "),
     "checks for a file or prints a path before its tests run", lambda block: block),
    ("a focused command behind an existsSync check", "the E3 evaluator's guard list (F2)", "step-plan", None,
     guarded("node -e \"require('fs').existsSync('built.txt') || process.exit(1)\" && "),
     "checks for a file or prints a path before its tests run", lambda block: block),
    ("a focused command that prints a path before its tests", "run 4's W3 printf guard (F2)", "step-plan", None,
     guarded("printf '%s\\n' built.txt && "),
     "checks for a file or prints a path before its tests run", lambda block: block),
    ("a target that keeps state with no base-state route", "run 4's W2 remote base run (F1, F3)", "test-strategy", None,
     targets([dict(STATEFUL, base_state_route="n/a")]),
     "keeps state between runs, so base_state_route says how a test still fails",
     targets([STATEFUL])),
    ("a test command naming a target that is no targets row", "F3", "step-plan", None,
     lambda block: commands(block, focused(lambda row: dict(row, target="the shared service"))),
     "which is no test-strategy targets row",
     lambda block: block),            # the named exit: leave target out for a command that runs on the checkout
    ("a stateful target whose focused and regression commands name no target", "run 4's W2 (F3)", "step-plan",
     STATEFUL_RUN, lambda block: block,
     "so each focused or regression command names, in target, the targets row it runs on",
     lambda block: commands(block, lambda row: dict(row, target=STATEFUL["target"])
                            if row.get("suite") in ("focused", "regression") else row)),
]


class LoopholeGateTests(contract.RealCliCase):
    def test_each_known_dodge_is_refused_and_its_named_exit_is_accepted(self) -> None:
        for label, seen, stage, positioning, dodge, fragment, exit_route in DODGES:
            with self.subTest(label, seen=seen):
                run, head = self.new_run(stage, results=positioning)
                command, path, action = contract.printed_callback(head)
                good = self.fill_done(head)
                contract.write_block(path, dodge(good))
                self.assertIn(fragment, self.refused(command, run))
                contract.write_block(path, exit_route(good))
                # A stage that closes the knowledge home names its files first (the contract suite's own helper).
                contract.RefusalRouteTests.accept_after_the_knowledge_files(self, command, run)
                self.assertEqual(self.recorded(run, action)["outcome"], "done")

    def test_every_row_names_where_it_was_seen_and_a_refusal_it_expects(self) -> None:
        labels = [row[0] for row in DODGES]
        self.assertEqual(len(labels), len(set(labels)))
        for label, seen, stage, _positioning, _dodge, fragment, _exit in DODGES:
            with self.subTest(label):
                self.assertIn(stage, contract.EXPECTED_STAGES)
                self.assertTrue(seen.strip() and fragment.strip())


if __name__ == "__main__":
    unittest.main()
