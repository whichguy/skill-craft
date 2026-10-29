#!/usr/bin/env python3
"""Hermetic tests for ``shiploop_iteration``: the contract of the per-step iteration (design T §8 and §9, build order
step 1, owner 2026-10-28: "Start step 1").

Each planned step runs implement, test, document (which reflects on the step in the knowledge home and owns the step's
Improve review) and commit before the next step starts; 2b-3 (option C, owner 2026-10-28) folds the knowledge stage
into document. These tests pin the four invariants step 1 specifies, before the navigator uses them:
- the iteration identity (item, plan revision, step, base commit), and that a base is always a commit;
- producer ownership (document owns the Improve review; commit is ShipLoop's alone);
- retry invalidation (what a send-back keeps, what it voids, and when it ends the iteration);
- the final-tree commit invariant (commit only the tree the last gate ran on, from the iteration's base, idempotently).
Build order step 2a adds what each step owes its test stage: due cases, new (RED) cases and the active commands,
pinned on the step plan and test spec of the 2.18.0 battleship run.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_iteration as iteration

BASE = "a" * 40
NEXT = "b" * 40
OTHER = "c" * 40
PLAN = "nav-0123456789abcdef0123456789abcdef"
REPLAN = "nav-fedcba9876543210fedcba9876543210"
STEPS = [{"id": "S1"}, {"id": "S2"}, {"id": "S3"}]


def first() -> iteration.Iteration:
    started = iteration.start("W1", PLAN, STEPS, committed=[], head=BASE)
    assert started is not None
    return started


class StageOrderTests(unittest.TestCase):
    def test_each_step_runs_implement_test_document_commit_in_that_order(self):
        # Option C (owner 2026-10-28, "Go with C"): no knowledge stage; document records the step's knowledge.
        self.assertEqual(iteration.STAGES, ("implement", "test", "document", "commit"))
        walked, stage = [], "implement"
        while stage is not None:
            walked.append(stage)
            stage = iteration.next_stage(stage)
        self.assertEqual(walked, list(iteration.STAGES))

    def test_an_unknown_stage_has_no_next_stage(self):
        with self.assertRaises(ValueError):
            iteration.next_stage("verify")

    def test_document_owns_the_improve_review_and_no_other_stage_does(self):
        self.assertEqual([stage for stage in iteration.STAGES if iteration.owns_improve(stage)], ["document"])

    def test_commit_is_shiploops_alone_and_every_other_stage_is_the_models(self):
        self.assertEqual(iteration.MODEL_STAGES, ("implement", "test", "document"))
        self.assertNotIn("commit", iteration.MODEL_STAGES)


class IdentityTests(unittest.TestCase):
    def test_the_first_iteration_is_the_first_step_from_the_head_commit(self):
        started = first()
        self.assertEqual((started.item, started.plan, started.step, started.number, started.base),
                         ("W1", PLAN, "S1", 1, BASE))

    def test_the_next_iteration_starts_from_the_commit_the_last_one_made(self):
        done = first()
        following = iteration.start("W1", PLAN, STEPS, committed=["S1"], head=iteration.advance(done, NEXT))
        self.assertEqual((following.step, following.number, following.base), ("S2", 2, NEXT))

    def test_no_iteration_is_left_once_every_step_is_committed(self):
        self.assertIsNone(iteration.start("W1", PLAN, STEPS, committed=["S1", "S2", "S3"], head=NEXT))

    def test_a_base_is_always_a_full_commit_id_never_a_snapshot_of_a_dirty_checkout(self):
        for bad in ("", "abc123", "g" * 40, None):
            with self.subTest(base=bad), self.assertRaises(ValueError):
                iteration.start("W1", PLAN, STEPS, committed=[], head=bad)
        with self.assertRaises(ValueError):
            iteration.advance(first(), "abc123")

    def test_a_committed_step_the_plan_does_not_name_is_refused(self):
        with self.assertRaises(ValueError):
            iteration.start("W1", PLAN, STEPS, committed=["S9"], head=BASE)

    def test_steps_are_committed_in_plan_order(self):
        with self.assertRaises(ValueError):
            iteration.start("W1", PLAN, STEPS, committed=["S2"], head=BASE)

    def test_a_receipt_is_stale_when_its_plan_revision_step_or_base_differs(self):
        current = first()
        same = iteration.identity(current)
        self.assertFalse(iteration.stale(same, current))
        for field, value in (("plan", REPLAN), ("step", "S2"), ("base", OTHER), ("item", "W2")):
            with self.subTest(field=field):
                self.assertTrue(iteration.stale({**same, field: value}, current))
        self.assertTrue(iteration.stale(None, current))


class SendBackTests(unittest.TestCase):
    def test_a_send_back_to_test_voids_test_and_later_and_keeps_implement(self):
        self.assertEqual(iteration.invalidated(["implement", "test", "document"], "test"), ["test", "document"])

    def test_a_send_back_to_implement_voids_every_stage_done(self):
        self.assertEqual(iteration.invalidated(["implement", "test", "document"], "implement"),
                         ["implement", "test", "document"])

    def test_a_send_back_to_planning_voids_everything_and_ends_the_iteration(self):
        self.assertEqual(iteration.invalidated(["implement", "test"], "step-plan"), ["implement", "test"])
        self.assertTrue(iteration.ends_iteration("step-plan"))
        self.assertFalse(iteration.ends_iteration("test"))

    def test_commit_is_never_a_send_back_target(self):
        with self.assertRaises(ValueError):
            iteration.invalidated(["implement"], "commit")

    def test_a_send_back_inside_the_iteration_keeps_its_base(self):
        current = first()
        self.assertEqual(iteration.after_send_back(current, "test"), current)

    def test_after_a_send_back_to_planning_the_next_iteration_starts_from_the_last_commit(self):
        current = first()
        self.assertIsNone(iteration.after_send_back(current, "step-plan"))
        # Edits left in the checkout are the new iteration's change: its base is the commit, so they never vanish into it.
        replanned = iteration.start("W1", REPLAN, STEPS, committed=[], head=BASE)
        self.assertEqual((replanned.plan, replanned.base), (REPLAN, BASE))


class CommitTests(unittest.TestCase):
    TREE = "d" * 40

    def decide(self, current, **overrides):
        values = {"head": current.base, "head_parent": None, "head_tree": None, "pending": None}
        values.update(overrides)
        return iteration.commit_decision(current, **values)

    def test_a_checkout_on_the_iteration_base_is_committed(self):
        # The commit stage runs in the call whose gates accepted the step's last stage (document's complete, or its
        # review's import), so the tree it commits is the gated one: there is no later tree to compare (2b-4).
        self.assertEqual(self.decide(first()), iteration.Decision("commit"))

    def test_a_commit_that_already_happened_is_recognised_not_repeated(self):
        current = first()
        pending = iteration.pending_record(current, self.TREE)
        decision = self.decide(current, head=NEXT, head_parent=current.base, head_tree=self.TREE, pending=pending)
        self.assertEqual(decision.action, "done")

    def test_a_commit_nobody_recorded_is_refused_because_only_the_commit_stage_commits(self):
        current = first()
        decision = self.decide(current, head=NEXT, head_parent=current.base, head_tree=self.TREE, pending=None)
        self.assertEqual(decision.action, "refuse")
        self.assertIn("only the commit stage commits", decision.reason)

    def test_a_head_that_moved_past_the_base_by_another_route_is_refused(self):
        current = first()
        pending = iteration.pending_record(current, self.TREE)
        decision = self.decide(current, head=NEXT, head_parent=OTHER, head_tree=self.TREE, pending=pending)
        self.assertEqual(decision.action, "refuse")

    def test_a_pending_record_of_another_iteration_is_refused(self):
        current = first()
        other = iteration.start("W1", REPLAN, STEPS, committed=[], head=BASE)
        decision = self.decide(current, pending=iteration.pending_record(other, self.TREE))
        self.assertEqual(decision.action, "refuse")
        self.assertIn("another iteration", decision.reason)

    def test_the_pending_record_names_the_iteration_its_parent_and_its_tree(self):
        current = first()
        self.assertEqual(iteration.pending_record(current, self.TREE),
                         {"iteration": iteration.identity(current), "parent": BASE, "tree": self.TREE})


# The step plan and test spec of v2180-sonnet-battleship-36036c (2026-10-27), trimmed to the fields the projection reads.
BATTLESHIP_STEPS = [{"id": "S1", "criteria": ["C1", "C2", "C3", "C4"]},
                    {"id": "S2", "criteria": ["C5", "C6", "C7", "C8"]},
                    {"id": "S3", "criteria": ["C9", "C10"]}]
BATTLESHIP_CASES = [{"id": case, "criterion": criterion} for case, criterion in (
    ("TC-7", "C2"), ("TC-8", "C2"), ("TC-9", "C2"), ("TC-12", "C1"), ("TC-13", "C1"), ("TC-14", "C3"),
    ("TC-1", "C5"), ("TC-2", "C5"), ("TC-3", "C5"), ("TC-4", "C9"), ("TC-5", "C6"), ("TC-6", "C6"),
    ("TC-10", "C7"), ("TC-11", "C7"), ("TC-15", "C10"))]
GAME = {"command": "node --test test/game.test.js", "suite": "focused",
        "ids": ["TC-7", "TC-8", "TC-9", "TC-12", "TC-13", "TC-14"], "criteria": ["C1", "C2", "C3"]}
SERVER = {"command": "node --test test/server.test.js", "suite": "focused",
          "ids": ["TC-1", "TC-2", "TC-3", "TC-4", "TC-5", "TC-6", "TC-10", "TC-11"], "criteria": ["C5", "C6", "C7", "C9"]}
BROWSER = {"command": "BROWSER_TESTS=1 node --test test/browser.test.js", "suite": "focused", "ids": ["TC-15"],
           "criteria": ["C10"]}
DOCS = {"command": "node RUN/scratch/check-docs.js", "suite": "check", "criteria": ["C4", "C8"]}
REGRESSION = {"command": "node --test", "suite": "regression"}
BATTLESHIP_COMMANDS = [GAME, SERVER, BROWSER, DOCS, REGRESSION]


class DueCaseTests(unittest.TestCase):
    """Build order step 2a: which cases and commands each step owes, from data ShipLoop already validates (each case
    names its step-plan criterion; each step lists the criteria it satisfies), so the test spec needs no new field."""

    def test_a_case_is_due_at_the_last_step_that_lists_its_criterion(self):
        self.assertEqual(iteration.case_step("C2", BATTLESHIP_STEPS), "S1")
        self.assertEqual(iteration.case_step("C9", BATTLESHIP_STEPS), "S3")
        shared = [{"id": "S1", "criteria": ["C1"]}, {"id": "S2", "criteria": ["C1", "C2"]}]
        self.assertEqual(iteration.case_step("C1", shared), "S2")

    def test_a_case_whose_criterion_no_step_lists_is_due_at_the_last_step(self):
        self.assertEqual(iteration.case_step("C99", BATTLESHIP_STEPS), "S3")
        self.assertEqual(iteration.case_step("C1", [{"id": "S1"}, {"id": "S2"}]), "S2")

    def test_each_step_owes_every_case_due_so_far_and_only_its_own_are_new(self):
        self.assertEqual(iteration.due_cases(BATTLESHIP_CASES, BATTLESHIP_STEPS, 1),
                         ["TC-7", "TC-8", "TC-9", "TC-12", "TC-13", "TC-14"])
        self.assertEqual(iteration.new_cases(BATTLESHIP_CASES, BATTLESHIP_STEPS, 2),
                         ["TC-1", "TC-2", "TC-3", "TC-5", "TC-6", "TC-10", "TC-11"])
        self.assertEqual(iteration.new_cases(BATTLESHIP_CASES, BATTLESHIP_STEPS, 3), ["TC-4", "TC-15"])
        self.assertEqual(len(iteration.due_cases(BATTLESHIP_CASES, BATTLESHIP_STEPS, 3)), len(BATTLESHIP_CASES))

    def active(self, number):
        return {row["command"]: row.get("ids") for row in
                iteration.active_commands(BATTLESHIP_COMMANDS, BATTLESHIP_CASES, BATTLESHIP_STEPS, number)}

    def test_s1_runs_the_game_tests_only_and_the_unmarked_regression_waits_for_the_last_step(self):
        self.assertEqual(self.active(1), {GAME["command"]: GAME["ids"]})
        self.assertNotIn(REGRESSION["command"], self.active(2))
        self.assertIn(REGRESSION["command"], self.active(3))

    MINIMUM = {"command": "node --test test/smoke.test.js", "suite": "regression", "minimum": True}

    def test_a_regression_command_marked_minimum_runs_at_every_step(self):
        """Design T §9.1 2d (owner 2026-10-28: "we definitely want to make sure that we don't do exhaustive regressions
        on every iteration"): each step runs its new code's cases, the earlier steps' cases and a minimum regression;
        the exhaustive regression, every unmarked regression command, runs at the item's last step only."""
        commands = [GAME, self.MINIMUM, REGRESSION]
        for number, expected in ((1, [GAME, self.MINIMUM]), (2, [GAME, self.MINIMUM]),
                                 (3, [GAME, self.MINIMUM, REGRESSION])):
            with self.subTest(step=number):
                self.assertEqual(iteration.active_commands(commands, BATTLESHIP_CASES, BATTLESHIP_STEPS, number),
                                 expected)

    def test_a_focused_command_that_is_also_the_minimum_regression_runs_as_the_regression_until_its_ids_are_due(self):
        """A focused row folded with the minimum regression (one command string, ``regression: true``) still runs at every
        step: before any of its IDs is due it is only the regression, so it lists no ID and confirms no criterion."""
        folded = {"command": "node --test", "suite": "focused", "ids": ["TC-4"], "criteria": ["C9"],
                  "regression": True, "minimum": True}
        self.assertEqual(iteration.active_commands([folded], BATTLESHIP_CASES, BATTLESHIP_STEPS, 1),
                         [{"command": "node --test", "suite": "regression", "minimum": True}])
        self.assertEqual(iteration.active_commands([folded], BATTLESHIP_CASES, BATTLESHIP_STEPS, 3), [folded])
        unmarked = {key: value for key, value in folded.items() if key != "minimum"}
        self.assertEqual(iteration.active_commands([unmarked], BATTLESHIP_CASES, BATTLESHIP_STEPS, 2), [])

    def test_a_focused_command_runs_from_its_first_due_id_narrowed_to_the_ids_due(self):
        at_two = self.active(2)
        self.assertEqual(at_two[SERVER["command"]], ["TC-1", "TC-2", "TC-3", "TC-5", "TC-6", "TC-10", "TC-11"])
        self.assertNotIn(BROWSER["command"], at_two)
        self.assertEqual(self.active(3)[SERVER["command"]], SERVER["ids"])

    def test_a_check_runs_from_the_last_step_that_lists_its_criteria(self):
        self.assertNotIn(DOCS["command"], self.active(1))
        self.assertIn(DOCS["command"], self.active(2))
        unnamed = {"command": "make check", "suite": "check"}
        self.assertEqual([row["command"] for row in iteration.active_commands([unnamed], [], BATTLESHIP_STEPS, 2)], [])
        self.assertEqual([row["command"] for row in iteration.active_commands([unnamed], [], BATTLESHIP_STEPS, 3)],
                         ["make check"])

    def test_the_last_step_runs_every_command_as_recorded(self):
        self.assertEqual(iteration.active_commands(BATTLESHIP_COMMANDS, BATTLESHIP_CASES, BATTLESHIP_STEPS, 3),
                         BATTLESHIP_COMMANDS)

    def test_a_projected_command_is_a_copy(self):
        narrowed = iteration.active_commands(BATTLESHIP_COMMANDS, BATTLESHIP_CASES, BATTLESHIP_STEPS, 2)
        next(row for row in narrowed if row["command"] == SERVER["command"])["ids"].append("TC-99")
        self.assertNotIn("TC-99", SERVER["ids"])

    def test_a_step_number_outside_the_plan_is_refused(self):
        for number in (0, 4):
            with self.subTest(number=number), self.assertRaises(ValueError):
                iteration.due_cases(BATTLESHIP_CASES, BATTLESHIP_STEPS, number)


if __name__ == "__main__":
    unittest.main()
