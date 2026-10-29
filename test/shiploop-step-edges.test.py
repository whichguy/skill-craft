#!/usr/bin/env python3
"""The per-step iteration's edge cases, through the real `complete` (design T §9.1 build order step 4).

Each step of an inline item is built, tested, documented, reviewed and committed before the next starts (design T §8).
The walks of shiploop-navigator-contract and shiploop-test-loop cover the plain path and the commit stage's failure and
retry; this suite drives the edges the build order names beyond them:
- a send-back in the middle of an item, after an earlier step's commit;
- a step review whose result sends the item back;
- a test case whose criterion spans steps, due only once the last step that lists it is built;
- a step that only changes test files;
- the base run at a later step: RED holds for the cases new there, and an earlier step's cases are not judged, also
  where a send-back makes a committed step's case new again, or a command holds no IDs.
Tests a review adds belong to the step floors and review-test registration (build order step 3), which test them.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(ROOT / "test"))
import shiploop_iteration as iteration  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402


def _load(name: str, path: str):
    """A sibling test module, loaded for its run drivers (as shiploop-e2e-slice borrows the test-loop driver)."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "test" / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


NC = _load("step_edges_navigator_contract", "shiploop-navigator-contract.test.py")
LOOP = _load("step_edges_test_loop", "shiploop-test-loop.test.py")


class SendBackMidItemTests(unittest.TestCase):
    """A two-step item walked through the real `complete` CLI (the navigator-contract driver: a docs-only plan, whose
    test and document stages are recorded not applicable, so each step is built, reviewed and committed)."""

    setUp = NC.EightStageInnerLoopCliTests.setUp
    git = NC.EightStageInnerLoopCliTests.git
    start = NC.EightStageInnerLoopCliTests.start
    state = NC.EightStageInnerLoopCliTests.state
    cli = NC.EightStageInnerLoopCliTests.cli
    submit = NC.EightStageInnerLoopCliTests.submit
    accept = NC.EightStageInnerLoopCliTests.accept
    finish_improve = NC.EightStageInnerLoopCliTests.finish_improve
    step_plan = NC.EightStageInnerLoopCliTests.step_plan
    drive_to_step_plan = NC.EightStageInnerLoopCliTests.drive_to_step_plan
    settle = NC.EightStageInnerLoopCliTests.settle
    THREE_STEP_PATHS = NC.EightStageInnerLoopCliTests.THREE_STEP_PATHS[:2]

    def two_step_plan(self, *, notes_works: bool = False) -> dict:
        """Two steps, each writing one new file; ``notes_works`` when an earlier plan's S1 committed notes.md."""
        plan = NC.EightStageInnerLoopCliTests.three_step_plan(self)
        plan["paths"] = list(self.THREE_STEP_PATHS)
        plan["steps"] = plan["steps"][:2]
        plan["expectations"] = plan["expectations"][:2]
        if notes_works:
            plan["expectations"][0] = {"id": "E1", "state": "works", "statement": "notes.md exists", "steps": ["S1"],
                                       "paths": ["notes.md"], "check": "test -f notes.md"}
        return plan

    def head(self) -> str:
        return self.git("rev-parse", "HEAD").strip()

    def ledger(self) -> dict:
        return json.loads((self.run_dir / "iterations" / "W1.json").read_text(encoding="utf-8"))["plans"]

    def plan_action(self) -> str:
        return test_loop._step_plan(self.state(), "W1")[0]

    def to_second_step(self) -> tuple[str, str]:
        """Build and commit S1 (it writes notes.md); returns (the base S1 began from, S1's commit)."""
        self.start()
        self.drive_to_step_plan()
        self.accept(self.two_step_plan())
        self.assertEqual(self.settle(), "test-spec")
        self.accept(NC.result())
        base = self.head()
        (self.repo / "notes.md").write_text("# notes.md\n")
        self.accept(NC.result(summary="Wrote notes.md."))
        self.settle()
        s1 = self.head()
        self.assertEqual(self.git("rev-parse", s1 + "^").strip(), base)
        self.assertEqual(nav.current_stage(self.state()), "implement")
        return base, s1

    def test_a_send_back_after_a_committed_step_keeps_its_commit_and_the_new_plan_builds_on_it(self) -> None:
        # Design T §9 row 5 and shiploop_iteration.after_send_back: a send-back to planning ends the iteration, commits
        # nothing, and the next plan revision starts its first iteration from the last commit.  A redone step that has
        # nothing left to change makes no commit and starts no review.
        _base, s1 = self.to_second_step()
        first_plan = self.plan_action()
        self.accept(NC.result(outcome="send-back", summary="S2's todo format is not settled; the step plan decides it."))
        self.assertEqual(nav.current_stage(self.state()), "step-plan")
        self.assertEqual(self.head(), s1, "a send-back commits nothing")
        self.accept(self.two_step_plan(notes_works=True))
        self.assertEqual(self.settle(), "test-spec")
        self.accept(NC.result())
        second_plan = self.plan_action()
        self.assertNotEqual(second_plan, first_plan)
        # The redone S1: notes.md is already in its base, so it changes nothing.
        self.accept(NC.result(summary="notes.md is already committed by the earlier plan's S1: nothing to change."))
        state = self.state()
        self.assertIsNone(state["active_improve"], "a step that changed nothing starts no review")
        self.assertEqual(self.head(), s1, "and makes no commit")
        (self.repo / "todo.md").write_text("# todo.md\n")
        self.accept(NC.result(summary="Wrote todo.md."))
        self.settle()
        s2 = self.head()
        self.assertEqual(self.git("rev-parse", s2 + "^").strip(), s1, "the new plan's S2 builds on the old S1's commit")
        self.assertEqual(self.git("show", "--name-only", "--format=", s2).split(), ["todo.md"])
        plans = self.ledger()
        self.assertEqual(plans[first_plan]["S1"]["commit"], s1, "the earlier plan's rows stay in the ledger")
        self.assertEqual(plans[second_plan]["S1"], {"number": 1, "base": s1, "commit": None})
        self.assertEqual(plans[second_plan]["S2"], {"number": 2, "base": s1, "commit": s2})

    def test_a_step_review_that_sends_the_item_back_commits_nothing_and_its_change_stays_for_the_next_plan(self) -> None:
        # The review's final result is the reviewed stage's result (design T §8: document owns the step's review), so a
        # review that finds the plan wrong reports send-back for it.  The commit stage commits only an accepted document,
        # so the step's change stays in the checkout, and the next plan's first iteration takes it as its change.
        self.start()
        self.drive_to_step_plan()
        self.accept(self.two_step_plan())
        self.assertEqual(self.settle(), "test-spec")
        self.accept(NC.result())
        base = self.head()
        (self.repo / "notes.md").write_text("# notes.md\n")
        self.accept(NC.result(summary="Wrote notes.md."))
        state = self.state()
        child = state["active_improve"]
        self.assertEqual(child["stage"], "document")
        updated = nav.finish_improve(state, child["action_id"], NC.receipt("document"),
                                     {"outcome": "send-back",
                                      "summary": "The review found the notes need a heading the step plan never names."})
        updated, writes, payload = nav._transition(self.core, self.run_dir, state, updated)
        nav.save(self.run_dir, updated, writes)
        nav._lint_finish(self.run_dir, payload)
        self.assertEqual(nav.current_stage(self.state()), "step-plan")
        self.assertEqual(self.head(), base, "the review's send-back commits nothing")
        self.assertIn("notes.md", self.git("status", "--porcelain", "--", "notes.md"))
        first_plan = self.plan_action()
        self.assertIsNone(self.ledger()[first_plan]["S1"]["commit"])
        self.accept(self.two_step_plan())
        self.assertEqual(self.settle(), "test-spec")
        self.accept(NC.result())
        self.accept(NC.result(summary="notes.md from before the send-back already holds this step's change."))
        self.settle()
        s1 = self.head()
        self.assertEqual(self.git("rev-parse", s1 + "^").strip(), base)
        self.assertEqual(self.git("show", "--name-only", "--format=", s1).split(), ["notes.md"])

    def test_a_step_that_only_changes_test_files_is_refused_with_the_per_step_reason(self) -> None:
        # Owner sizing rule (2026-10-10): tests are not a step unless the whole item is tests.  Since design T §8 each
        # step's own test stage writes the tests for the behaviour that step builds, which the refusal now says.
        self.start()
        self.drive_to_step_plan()
        plan = self.two_step_plan()
        plan["paths"] = ["notes.md", "test/notes.test.js"]
        plan["steps"][1]["paths"] = ["test/notes.test.js"]
        plan["expectations"] = plan["expectations"][:1]
        refused = self.submit(plan)
        self.assertNotEqual(refused.returncode, 0)
        text = refused.stdout + refused.stderr
        self.assertIn("step S2 only changes test files", text)
        self.assertIn("the test stage writes the tests for the behaviour the steps build", text)
        self.assertNotIn("after the last implement step", text)


# A focused command in TAP form.  TC-1's test always exists and passes once fixed.txt does (S1's test stage writes it).
# TC-2's test exists once its test file test/spans.txt does (the base run copies the item's test files in) and passes
# only with S2's change to a.py, so on S2's base it runs and fails.
SPANS_CHECK = ('n=1; fail=0\n'
               'if test -f fixed.txt; then echo "ok 1 - TC-1"; else echo "not ok 1 - TC-1"; fail=1; fi\n'
               'if test -f test/spans.txt; then n=2; if grep -q "import sys" a.py; then echo "ok 2 - TC-2"; '
               'else echo "not ok 2 - TC-2"; fail=1; fi; fi\n'
               'echo "Ran $n tests in 0.001s"\n'
               'if test "$fail" = 1; then echo "FAILED (failures=1)"; exit 1; fi\n'
               'echo OK\n')


class CrossStepCaseTests(unittest.TestCase):
    """A case whose criterion spans steps, through the real test gate (the test-loop driver)."""

    setUp = LOOP.TestLoopTests.setUp
    start = LOOP.TestLoopTests.start
    state = LOOP.TestLoopTests.state
    action = LOOP.TestLoopTests.action
    packet = LOOP.TestLoopTests.packet
    complete = LOOP.TestLoopTests.complete
    finish_improve = LOOP.TestLoopTests.finish_improve
    settle = LOOP.TestLoopTests.settle
    drive_to = LOOP.TestLoopTests.drive_to
    terminal = LOOP.TestLoopTests.terminal
    run_loop = LOOP.TestLoopTests.run_loop
    assert_refused = LOOP.TestLoopTests.assert_refused
    START = LOOP.TestLoopTests.START

    PLAN = {"test_commands": [{"command": "sh spans.sh", "suite": "focused", "ids": ["TC-1", "TC-2"],
                               "criteria": ["C1", "C2"]},
                              {"command": "test -f retained.txt", "suite": "regression"}],
            "paths": ["a.py"],
            "criteria": [{"id": "C1", "text": "The first check passes."},
                         {"id": "C2", "text": "The spanning check passes once both steps are built."}],
            "steps": [{"id": "S1", "task": "Build the first half.", "paths": ["a.py"], "proof": "true",
                       "criteria": ["C1", "C2"]},
                      {"id": "S2", "task": "Build the second half.", "paths": ["a.py"], "proof": "true",
                       "criteria": ["C2"]}]}
    CASES = [{"id": "TC-1", "criterion": "C1", "requirement": "R-1", "oracle": "the focused command",
              "red": "fails before the change", "green": "passes after it"},
             {"id": "TC-2", "criterion": "C2", "requirement": "R-1", "oracle": "the focused command",
              "red": "fails before the change", "green": "passes after it"}]

    def focused_ids(self) -> list[str]:
        commands = test_loop.stage_commands(self.state(), "test", "W1")[0]
        return next(row["ids"] for row in commands if row["suite"] == "focused")

    def pass_test_stage(self, *files: str) -> None:
        for name in ("fixed.txt", "retained.txt", *files):
            (self.repo / name).write_text(name + "\n")
        self.run_loop([LOOP.TRIVIAL])
        self.complete(dict(LOOP.DONE, evidence_refs=[str(self.terminal())]))

    def write_a(self, source: str):
        """The ``each`` hook that has a step's implement stage write a.py."""
        return lambda state: nav.current_stage(state) == "implement" and (self.repo / "a.py").write_text(source)

    def to_first_test(self, source: str = "import os\n") -> None:
        """Start the item and reach S1's test stage; S1's implement writes ``source`` to a.py."""
        (self.repo / "spans.sh").write_text(SPANS_CHECK)
        self.start()
        self.drive_to("test-spec", step_plan=self.PLAN)
        self.complete(dict(LOOP.DONE, test_cases=self.CASES))
        self.drive_to("test", step_plan=self.PLAN, each=self.write_a(source))

    def to_second_test(self, first: str, second: str) -> None:
        """Pass S1's test stage and reach S2's; S2's implement writes ``second`` to a.py."""
        self.to_first_test(first)
        self.pass_test_stage()
        self.drive_to("test", step_plan=self.PLAN, each=self.write_a(second))

    def write_s2_inputs(self) -> None:
        for name in ("fixed.txt", "retained.txt"):
            (self.repo / name).write_text(name + "\n")
        (self.repo / "test").mkdir(exist_ok=True)
        (self.repo / "test" / "spans.txt").write_text("both halves\n")

    def test_a_case_spanning_steps_is_due_at_the_last_step_that_lists_its_criterion(self) -> None:
        # design T §9.1 2a (iteration.case_step): TC-2's criterion C2 is listed by S1 and S2, so TC-2 is due at S2.  At
        # S1 the focused command is held to TC-1 alone, so S1's test stage passes the real gate while TC-2's test does
        # not exist yet; at S2 it owes both, and the same output without TC-2 is refused.
        self.to_first_test()
        self.assertEqual(self.focused_ids(), ["TC-1"], "S1 owes only the case due at it")
        self.pass_test_stage()                                   # test/spans.txt absent: TC-2's test is not written yet
        self.drive_to("test", step_plan=self.PLAN, each=self.write_a("import os\nimport sys\n"))
        self.assertEqual(self.focused_ids(), ["TC-1", "TC-2"], "S2 owes every case due so far")
        for name in ("fixed.txt", "retained.txt"):
            (self.repo / name).write_text(name + "\n")
        self.run_loop([LOOP.TRIVIAL])
        self.assert_refused(dict(LOOP.DONE, evidence_refs=[str(self.terminal())]), "TC-2")
        (self.repo / "test").mkdir(exist_ok=True)
        (self.repo / "test" / "spans.txt").write_text("both halves\n")
        self.complete(dict(LOOP.DONE, evidence_refs=[str(self.terminal())]))
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    def test_a_new_case_that_already_passes_on_a_later_steps_base_is_refused_and_an_earlier_case_is_not(self) -> None:
        # RED still holds at S2 for the cases new there: S1's change already holds what TC-2 asserts, so TC-2 passes on
        # S2's base and is refused by name, while S1's TC-1, which passes there too, is not judged (design T §9 row 4).
        self.to_second_test("import os\nimport sys\n", "import os\nimport sys\n# S2\n")
        flat = " ".join(self.packet().split())
        self.assertIn(" ".join(test_loop.BASE_RULE.split()), flat)
        self.assertIn("An earlier step's IDs already pass there and are not judged", flat)
        self.write_s2_inputs()
        self.run_loop([LOOP.TRIVIAL])
        done = dict(LOOP.DONE, evidence_refs=[str(self.terminal())])
        action = self.action()
        self.assert_refused(done, r"(?s)ShipLoop base run: test is not done.*passed TC-2 on the item's base")
        record = store.read_record(self.run_dir / test_loop.base_path(action, 1))
        self.assertEqual(record["earlier_steps"], ["TC-1"])
        self.assertEqual(record["runs"][0]["ids_passing"], ["TC-2"], "only the new case is judged")
        self.complete(dict(done, red_na=[{"id": "TC-2", "reason": "S1's change already holds what TC-2 asserts."}]))
        self.assertNotEqual(nav.current_stage(self.settle()), "test")

    def test_red_na_and_retired_tests_follow_the_cases_new_at_the_step(self) -> None:
        self.to_second_test("import os\n", "import os\nimport sys\n")
        state = self.state()
        with self.assertRaisesRegex(test_loop.TestLoopError,
                                    r"red_na names TC-1, which is not a test ID new at this step \(new: TC-2\)"):
            test_loop.check_result_fields(state, "W1", {"red_na": [{"id": "TC-1", "reason": "x"}]})
        with self.assertRaisesRegex(test_loop.TestLoopError,
                                    "retired_tests names TC-1, which a focused command still lists"):
            test_loop.check_result_fields(state, "W1", {"retired_tests": [{"id": "TC-1", "reason": "x"}]})
        test_loop.check_result_fields(state, "W1", {"red_na": [{"id": "TC-2", "reason": "x"}]})

    def test_a_case_committed_before_a_send_back_is_new_again_in_the_redone_plan_and_red_na_names_it(self) -> None:
        # The redone plan counts steps afresh, so S1's committed TC-1 is new at its S1 and passes on that base (the
        # iteration's base is S1's commit).  The refusal names the way through, and red_na takes it (design T §9 row 5).
        self.to_first_test()
        self.pass_test_stage()
        self.drive_to("implement", step_plan=self.PLAN)
        self.complete({"outcome": "send-back", "summary": "S2 is not settled; the step plan decides it."})
        self.drive_to("test-spec", step_plan=self.PLAN)
        self.complete(dict(LOOP.DONE, test_cases=self.CASES))
        self.drive_to("test", step_plan=self.PLAN)               # the redone S1 changes nothing: a.py is in its base
        self.assertEqual(test_loop.new_ids(self.state(), "W1"), ["TC-1"])
        for name in ("fixed.txt", "retained.txt"):
            (self.repo / name).write_text(name + "\n")
        self.run_loop([LOOP.TRIVIAL])
        done = dict(LOOP.DONE, evidence_refs=[str(self.terminal())])
        self.assert_refused(done, r"(?s)passed TC-1 on the item's base.*a case a step committed before a send-back")
        self.run_loop([LOOP.TRIVIAL])
        self.complete(dict(done, evidence_refs=[str(self.terminal())],
                           red_na=[{"id": "TC-1", "reason": "The earlier plan's S1 committed it."}]))
        self.assertNotEqual(nav.current_stage(self.settle()), "test")


class EarlierCommandTests(unittest.TestCase):
    """``iteration.earlier_command`` and the base run's verdict for a command holding only earlier steps' cases."""

    STEPS = [{"id": "S1", "criteria": ["C1"]}, {"id": "S2", "criteria": ["C2"]}]
    CASES = [{"id": "TC-1", "criterion": "C1"}, {"id": "TC-2", "criterion": "C2"}]

    def earlier(self, command: dict, number: int) -> bool:
        return iteration.earlier_command(command, self.CASES, self.STEPS, number)

    def test_a_command_is_earlier_only_when_everything_it_holds_is_due_before_the_step(self) -> None:
        listed = {"suite": "focused", "command": "run", "ids": ["TC-1"]}
        self.assertTrue(self.earlier(listed, 2))
        self.assertFalse(self.earlier(listed, 1), "a case is new at its own step")
        self.assertFalse(self.earlier(dict(listed, ids=["TC-1", "TC-2"]), 2), "a new case makes it a judged command")
        self.assertFalse(self.earlier(dict(listed, ids=["TC-9"]), 2), "an ID no case names is due at the last step")
        idless = {"suite": "focused", "command": "run", "criteria": ["C1"]}
        self.assertTrue(self.earlier(idless, 2))
        self.assertFalse(self.earlier(dict(idless, criteria=["C1", "C2"]), 2))
        self.assertFalse(self.earlier(dict(idless, criteria=[]), 2), "a command naming no criterion is due at the last step")

    def test_the_base_run_counts_an_earlier_command_and_judges_any_other(self) -> None:
        row = {"suite": "focused", "command": "run", "criteria": ["C1"]}
        counted = test_loop._judge_base(row, 0, "ok\n", [], [], [], True)
        self.assertEqual(counted["status"], "counted")
        self.assertTrue(counted["earlier_step"])
        self.assertEqual(test_loop._judge_base(row, 0, "ok\n", [], [], [])["status"], "passes-on-base",
                         "without the earlier-step mark a command with no IDs that exits 0 is judged")


if __name__ == "__main__":
    unittest.main()
