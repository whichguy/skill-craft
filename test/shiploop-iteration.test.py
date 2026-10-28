#!/usr/bin/env python3
"""Hermetic tests for ``shiploop_iteration``: the contract of the per-step iteration (design T §8 and §9, build order
step 1, owner 2026-10-28: "Start step 1").

Each planned step runs implement, test, document (which owns the step's Improve review), knowledge and commit before
the next step starts. These tests pin the four invariants step 1 specifies, before the navigator uses them:
- the iteration identity (item, plan revision, step, base commit), and that a base is always a commit;
- producer ownership (document owns the Improve review; commit is ShipLoop's alone);
- retry invalidation (what a send-back keeps, what it voids, and when it ends the iteration);
- the final-tree commit invariant (commit only the tree the last gate ran on, from the iteration's base, idempotently).
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
    def test_each_step_runs_implement_test_document_knowledge_commit_in_that_order(self):
        self.assertEqual(iteration.STAGES, ("implement", "test", "document", "knowledge", "commit"))
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
        self.assertEqual(iteration.MODEL_STAGES, ("implement", "test", "document", "knowledge"))
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
        self.assertEqual(iteration.invalidated(["implement", "test", "document", "knowledge"], "implement"),
                         ["implement", "test", "document", "knowledge"])

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
    CHANGED = "e" * 40

    def decide(self, current, **overrides):
        values = {"head": current.base, "head_parent": None, "head_tree": None, "current_tree": self.TREE,
                  "gated_tree": self.TREE, "pending": None}
        values.update(overrides)
        return iteration.commit_decision(current, **values)

    def test_the_gated_tree_on_the_iteration_base_is_committed(self):
        decision = self.decide(first())
        self.assertEqual((decision.action, decision.reopen), ("commit", None))

    def test_a_tree_that_changed_after_the_knowledge_gate_is_refused_and_reopens_knowledge(self):
        decision = self.decide(first(), current_tree=self.CHANGED)
        self.assertEqual((decision.action, decision.reopen), ("refuse", "knowledge"))
        self.assertIn("knowledge", decision.reason)

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


if __name__ == "__main__":
    unittest.main()
