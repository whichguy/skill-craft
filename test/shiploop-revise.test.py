#!/usr/bin/env python3
"""The revise outcome: a work item whose goal proves wrong goes back to its step plan.

Synthetic protocol tests on the pure navigator API: no Improve runtime,
command or project check runs.
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as nav  # noqa: E402
import shiploop_navigator_dry_run as dry_run  # noqa: E402
import shiploop_planning_revision as planning_revision  # noqa: E402
import shiploop_stage_spec as spec  # noqa: E402

REVISE = {"outcome": "revise", "summary": "A completion criterion is unachievable as planned."}


def drive_to(stage: str, *, two: bool = False) -> dict:
    """Walk the dry-run declarations until the current stage is ``stage``."""
    state = nav.new_state("/simulation-only/repo", "Revise fixture.", delegation=nav.DEFAULT_DELEGATION)
    for step in dry_run.activity(two=two):
        if nav.current_stage(state) == stage and step["command"] == "produce":
            return state
        action = nav.current_action(state)["id"]
        if step["command"] == "produce":
            state = nav.apply(state, action, step["result"])
        else:
            state = nav.finish_improve(state, action, step["receipt"], step.get("final_result"))
    raise AssertionError("stage not reached: " + stage)


def submit(state: dict, result: dict) -> dict:
    return nav.apply(state, nav.current_action(state)["id"], result)


class ReviseTests(unittest.TestCase):
    def test_revise_returns_the_item_to_step_plan_with_a_fresh_action(self) -> None:
        state = drive_to("implement")
        old_action = nav.current_action(state)["id"]
        state = submit(state, REVISE)
        self.assertEqual(nav.current_stage(state), "step-plan")
        self.assertEqual(state["status"], "active")
        self.assertEqual(state["revisions"], {"W1": 1})
        self.assertNotEqual(nav.current_action(state)["id"], old_action)
        self.assertEqual(state["history"][-1]["outcome"], "revise")

    def test_the_budget_is_two_revises_per_item_then_the_user_decides(self) -> None:
        state = drive_to("implement")
        for used in (1, 2):
            state = submit(state, REVISE)
            self.assertEqual(state["revisions"], {"W1": used})
            # Walk step-plan (with its Improve child) back to implement.
            for step in dry_run.activity():
                if nav.current_stage(state) == "implement":
                    break
                if step["at"] != nav.current_stage(state):
                    continue
                action = nav.current_action(state)["id"]
                if step["command"] == "produce":
                    state = nav.apply(state, action, step["result"])
                else:
                    state = nav.finish_improve(state, action, step["receipt"], step.get("final_result"))
            self.assertEqual(nav.current_stage(state), "implement")
        with self.assertRaisesRegex(nav.NavigatorError, "used its 2 revisions.*blocked_by user"):
            submit(state, REVISE)
        blocked = submit(state, {"outcome": "blocked", "blocked_by": "user",
                                 "summary": "The step plan cannot meet criterion C2; the user decides."})
        self.assertEqual(blocked["status"], "blocked")

    def test_revise_is_allowed_only_where_the_stage_table_allows_it(self) -> None:
        self.assertEqual(spec.with_outcome("revise")[0], "test-spec")
        self.assertEqual(spec.with_outcome("revise")[-1], "integration-verify")
        for stage in ("intake", "plan", "select-work", "step-plan", "carry-forward"):
            with self.subTest(stage=stage):
                state = drive_to(stage)
                with self.assertRaisesRegex(nav.NavigatorError, "revise sends a work item back"):
                    submit(state, REVISE)

    def test_earlier_results_of_a_revised_item_are_no_longer_current(self) -> None:
        state = drive_to("implement")
        current = planning_revision.current_actions(state)
        self.assertIn(("W1", "test-spec"), current)
        self.assertIn(("W1", "select-work"), current)
        state = submit(state, REVISE)
        current = planning_revision.current_actions(state)
        self.assertNotIn(("W1", "step-plan"), current)
        self.assertNotIn(("W1", "test-spec"), current)
        self.assertIn(("W1", "select-work"), current)
        self.assertIn((None, "plan"), current)

    def test_packet_states_the_revise_outcome_and_budget(self) -> None:
        state = drive_to("test-refine")
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn("Allowed outcomes: done | repeat | blocked | revise (", packet)
        self.assertIn("2 of 2 left for this item", packet)
        state = submit(state, REVISE)
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn("(sent back to step-plan)", packet)

    def test_a_saved_run_from_an_older_state_version_is_refused_with_the_fresh_run_hint(self) -> None:
        state = drive_to("implement")
        old = deepcopy(state)
        old["version"] = 3
        old.pop("revisions")
        with self.assertRaisesRegex(nav.NavigatorError, "missing: revisions"):
            nav.validate(old)
        wrong_version = deepcopy(state)
        wrong_version["version"] = 3
        with self.assertRaisesRegex(nav.NavigatorError, "state version 3 is not the supported version 4"):
            nav.validate(wrong_version)

    def test_revisions_must_name_real_items_within_the_budget(self) -> None:
        state = drive_to("implement")
        for bad in ({"W9": 1}, {"W1": 0}, {"W1": 3}):
            broken = deepcopy(state)
            broken["revisions"] = bad
            with self.subTest(revisions=bad), self.assertRaisesRegex(nav.NavigatorError, "revisions must map"):
                nav.validate(broken)


if __name__ == "__main__":
    unittest.main()
