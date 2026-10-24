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
_IMPROVE = importlib.util.spec_from_file_location("shiploop_actual_improve_cli",
                                                  ROOT / "test" / "shiploop-actual-improve-cli.test.py")
improve_cli = importlib.util.module_from_spec(_IMPROVE)
sys.modules[_IMPROVE.name] = improve_cli
_IMPROVE.loader.exec_module(improve_cli)

FOCUSED = contract.FOCUSED
# A test-strategy target that keeps state between runs (F3), named by the rows that need one.
STATEFUL = {"target": "the shared service", "keeps_state": "yes", "base_state_route": "a clean namespace per run"}
# An unverified outcome of the spec's primary requirement R-1 (F6), and the add-work its refusal names.
PRIMARY_RUN = {"spec": {"primary": ["R-1"]}}
PRIMARY_ROW = dict(contract.UNVERIFIED_ENTRY, requirement="R-1", outcome="a person sees the built file's text",
                   lower_layer_check="the reviewer read the page")
ADD_TEST = {"outcome": "add-work", "summary": "Add the unit test that shows R-1's logic works.",
            "headline": "R-1 needs a lower-layer test.",
            "work_items": [{"id": "W2", "title": "Add a unit test of R-1's logic",
                            "context": "R-1 is primary and no unit or component test of it passed."}]}


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
    ("an unverified primary outcome whose lower-layer check is a person's reading", "run 4's product-acceptance (F6)",
     "product-acceptance", PRIMARY_RUN, lambda block: {**block, "unverified": [PRIMARY_ROW]},
     "a primary requirement (spec primary), and its lower_layer_check names no test",
     lambda block: dict(ADD_TEST, evidence_refs=block["evidence_refs"])),   # the named exit: add the missing test
]

# improve-commit dodges (F5): (label, where it was seen, the files the fix touches, the message, refusal fragment, the
# message of the named exit).  Each runs at the end-of-work review, whose commit owes the Regression test line.
REGRESSION_TEST = "from src.calc import calc\n\ndef test_calc_rejects_zero():\n    assert calc(0) == 0\n"
COMMIT_DODGES = [
    ("an end-of-work code fix committed with no regression test", "run 4's Improve fixes (F5)", None,
     "fix: guard zero\n\nKey learnings: zero needs a guard.\n", "this commit has no test file",
     "fix: guard zero\n\nKey learnings: zero needs a guard.\nRegression test: none: the guard only logs\n"),
    ("a regression line naming a test the commit does not hold", "F5", REGRESSION_TEST,
     "fix: guard zero\n\nKey learnings: zero needs a guard.\nRegression test: test_somewhere_else\n",
     "no test file in this commit holds test_somewhere_else",
     "fix: guard zero\n\nKey learnings: zero needs a guard.\nRegression test: test_calc_rejects_zero\n"),
    ("a regression line of none with no reason", "F5", None,
     "fix: guard zero\n\nKey learnings: zero needs a guard.\nRegression test: none:\n",
     "Regression test: none: <why no test can show this fix>",
     "fix: guard zero\n\nKey learnings: zero needs a guard.\nRegression test: none: the guard only logs\n"),
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
                route = exit_route(good)
                contract.write_block(path, route)
                # A stage that closes the knowledge home names its files first (the contract suite's own helper).
                contract.RefusalRouteTests.accept_after_the_knowledge_files(self, command, run)
                self.assertEqual(self.recorded(run, action)["outcome"], route["outcome"])

    def test_every_row_names_where_it_was_seen_and_a_refusal_it_expects(self) -> None:
        labels = [row[0] for row in DODGES]
        self.assertEqual(len(labels), len(set(labels)))
        for label, seen, stage, _positioning, _dodge, fragment, _exit in DODGES:
            with self.subTest(label):
                self.assertIn(stage, contract.EXPECTED_STAGES)
                self.assertTrue(seen.strip() and fragment.strip())


class CommitDodgeTests(improve_cli.ImproveCliFixture):
    """The improve-commit dodges, with the actual-improve-cli suite's commit fixture (its helpers, not its tests)."""

    for _name in ("_write_producer", "_start_parent", "git", "begin", "write", "refused", "line_one", "named_exit",
                  "run_named", "head_message", "code_change"):
        locals()[_name] = getattr(improve_cli.ImproveCommitContractTests, _name)
    del _name

    def setUp(self):
        improve_cli.ImproveCliFixture.setUp(self)
        self.environment["HOME"] = str(self.base / "home")

    def check_commit_dodge(self, label, seen, test_text, message, fragment, exit_message) -> None:
        self.begin("carry-forward", producer_extra=improve_cli.END_OF_WORK)
        self.code_change(test_text)
        self.write(message)
        refusal = self.refused()
        self.assertIn(fragment, self.line_one(refusal), label + " (" + seen + ")")
        before = self.git("rev-parse", "HEAD").strip()
        self.write(exit_message)
        self.run_named(refusal)
        self.assertNotEqual(before, self.git("rev-parse", "HEAD").strip())
        self.assertIn(exit_message.rsplit("\n", 2)[-2], self.head_message())


# One test per commit dodge: each needs a fresh repository and run, which the fixture gives per test.
for _index, _row in enumerate(COMMIT_DODGES, 1):
    setattr(CommitDodgeTests, "test_commit_dodge_" + str(_index) + "_is_refused_and_its_named_exit_commits",
            lambda self, row=_row: self.check_commit_dodge(*row))
del _index, _row


if __name__ == "__main__":
    unittest.main()
