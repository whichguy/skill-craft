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


def walk(state: dict, rows: list) -> dict:
    """Apply dry-run declarations in order, each through the real gate."""
    for step in rows:
        action = nav.current_action(state)["id"]
        if step["command"] == "produce":
            state = nav.apply(state, action, step["result"])
        else:
            state = nav.finish_improve(state, action, step["receipt"], step.get("final_result"))
    return state


def back_to_implement(state: dict, *, two: bool = False) -> dict:
    """After a revise: replay the dry-run rows from the item's step-plan up to its implement."""
    rows = dry_run.activity(two=two)
    first = next(i for i, row in enumerate(rows) if row["at"] == "step-plan")
    until = next(i for i, row in enumerate(rows) if row["at"] == "implement")
    return walk(state, rows[first:until])


def last_action(state: dict, stage: str, outcome: str, item: str = "W1") -> str:
    return [row["action"] for row in state["history"]
            if row["stage"] == stage and row["outcome"] == outcome and row["workitem"] == item][-1]


def result_path(action: str) -> str:
    return str(dry_run.RUN / "results" / (action + ".md"))


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
        for stage in ("intake", "plan", "get-next-work-item", "step-plan", "carry-forward"):
            with self.subTest(stage=stage):
                state = drive_to(stage)
                with self.assertRaisesRegex(nav.NavigatorError, "revise sends a work item back"):
                    submit(state, REVISE)

    def test_earlier_results_of_a_revised_item_are_no_longer_current(self) -> None:
        state = drive_to("implement")
        current = planning_revision.current_actions(state)
        self.assertIn(("W1", "test-spec"), current)
        self.assertIn(("W1", "get-next-work-item"), current)
        state = submit(state, REVISE)
        current = planning_revision.current_actions(state)
        self.assertNotIn(("W1", "step-plan"), current)
        self.assertNotIn(("W1", "test-spec"), current)
        self.assertIn(("W1", "get-next-work-item"), current)
        self.assertIn((None, "plan"), current)

    def test_packet_states_the_revise_outcome_and_budget(self) -> None:
        state = drive_to("test-refine")
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn("Allowed outcomes: done | repeat | blocked | revise (", packet)
        self.assertIn("2 of 2 left for this item", packet)
        state = submit(state, REVISE)
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn("(sent back to step-plan)", packet)

    def test_a_redone_step_plan_packet_names_the_previous_plan_and_the_revise_result(self) -> None:
        state = drive_to("implement")
        plan = last_action(state, "step-plan", "done")
        state = submit(state, REVISE)
        sent_back = state["history"][-1]["action"]
        self.assertEqual(nav.current_stage(state), "step-plan")
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn(result_path(plan), packet)
        self.assertIn(result_path(sent_back), packet)

    def test_the_redone_step_plan_done_when_asks_for_the_carried_over_rows_in_the_printed_head(self) -> None:
        # Wording-level check: the amend obligation needs a stated check, so it sits among the Done-when
        # conditions of the printed head, not only in the full packet.
        first = drive_to("step-plan")
        head = nav.packet_head(dry_run.CORE, dry_run.RUN, first, dry_run.RUN / "packets" / "first.md")
        self.assertNotIn("carried over", head)
        redone = submit(drive_to("implement"), REVISE)
        head = nav.packet_head(dry_run.CORE, dry_run.RUN, redone, dry_run.RUN / "packets" / "redo.md")
        done_when = head[head.index("Done when"):head.index("Checked by")]
        self.assertIn("carried over", done_when)

    def test_a_second_revise_names_the_latest_plan_and_the_latest_revise_result(self) -> None:
        state = submit(drive_to("implement"), REVISE)
        first_plan = last_action(state, "step-plan", "done")
        first_sent_back = state["history"][-1]["action"]
        state = back_to_implement(state)
        second_plan = last_action(state, "step-plan", "done")
        self.assertNotEqual(first_plan, second_plan)
        state = submit(state, REVISE)
        second_sent_back = state["history"][-1]["action"]
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn(result_path(second_plan), packet)
        self.assertIn(result_path(second_sent_back), packet)
        self.assertNotIn(result_path(first_plan), packet)
        self.assertNotIn(result_path(first_sent_back), packet)

    def test_the_amend_lines_follow_a_repeat_of_the_redone_step_plan(self) -> None:
        state = drive_to("implement")
        plan = last_action(state, "step-plan", "done")
        state = submit(state, REVISE)
        sent_back = state["history"][-1]["action"]
        # The redone plan goes round again, so the revise result leaves the last-transition block.
        state = submit(state, {"outcome": "repeat", "summary": "The redone plan is not finished."})
        state = nav.finish_improve(state, nav.current_action(state)["id"],
                                   dry_run._improve_receipt("step-plan"), None)
        self.assertEqual(nav.current_stage(state), "step-plan")
        self.assertEqual(state["history"][-1]["outcome"], "repeat")
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn(result_path(plan), packet)
        self.assertIn(result_path(sent_back), packet)

    def test_a_first_visit_the_redone_test_spec_and_the_next_item_print_no_amend_lines(self) -> None:
        # GUARD, green before and after: only the redone step plan is asked to amend.
        head_of = lambda state: nav.packet_head(dry_run.CORE, dry_run.RUN, state, dry_run.RUN / "packets" / "x.md")
        self.assertNotIn("carried over", head_of(drive_to("step-plan", two=True)))
        state = drive_to("implement", two=True)
        plan = last_action(state, "step-plan", "done")
        state = submit(state, REVISE)
        sent_back = state["history"][-1]["action"]
        rows = dry_run.activity(two=True)
        step_plan = next(i for i, row in enumerate(rows) if row["at"] == "step-plan")
        test_spec = next(i for i, row in enumerate(rows) if row["at"] == "test-spec")
        # The redone step plan is accepted, so the test spec after it builds on the new plan and no longer
        # carries the revise evidence or the amend request.
        state = walk(state, rows[step_plan:test_spec])
        self.assertEqual(nav.current_stage(state), "test-spec")
        self.assertNotIn(result_path(sent_back), nav.render(dry_run.CORE, dry_run.RUN, state))
        self.assertNotIn("carried over", head_of(state))
        # W2 reaches its own step plan once W1 finishes: nothing of W1's plans or revise result is named.
        second_item = [i for i, row in enumerate(rows) if row["at"] == "get-next-work-item"][1]
        state = walk(state, rows[test_spec:second_item + 1])
        self.assertEqual(state["work_items"][state["work_index"]]["id"], "W2")
        self.assertEqual(nav.current_stage(state), "step-plan")
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertNotIn(result_path(plan), packet)
        self.assertNotIn(result_path(sent_back), packet)
        self.assertNotIn("carried over", head_of(state))

    def test_an_amended_step_plan_is_accepted_through_the_gate(self) -> None:
        state = submit(drive_to("implement"), REVISE)
        amended = {"outcome": "done",
                   "summary": "Amended step plan: C1 and its command are carried over; step 2 is new.",
                   "test_commands": [{"command": "python3 -m unittest discover -s tests", "suite": "focused"}]}
        state = submit(state, amended)
        self.assertIsNotNone(state["active_improve"])
        state = nav.finish_improve(state, nav.current_action(state)["id"],
                                   dry_run._improve_receipt("step-plan"), None)
        self.assertEqual(nav.current_stage(state), "test-spec")
        self.assertIn("carried over", state["accepted"][last_action(state, "step-plan", "done")]["summary"])

    def test_a_state_that_records_a_revision_without_its_rows_is_refused_at_render(self) -> None:
        # Not reachable through the gate: history is append-only and a revise always adds its row.
        # The render refuses such a state instead of printing a plan it cannot name.
        def without(state: dict, keep) -> dict:
            broken = deepcopy(state)
            gone = [row["action"] for row in broken["history"] if not keep(row)]
            broken["history"] = [row for row in broken["history"] if keep(row)]
            for action in gone:
                broken["accepted"].pop(action)
            return broken

        state = submit(drive_to("implement"), REVISE)
        with self.assertRaisesRegex(nav.NavigatorError, "records a revision but no revise result"):
            nav.render(dry_run.CORE, dry_run.RUN, without(state, lambda row: row["outcome"] != "revise"))
        # With planning_review none the step plan has no Improve result tying it to the history.
        quick = nav.new_state("/simulation-only/repo", "Revise fixture.", delegation=nav.DEFAULT_DELEGATION,
                              planning_review="none")
        for step in dry_run.activity("none"):
            if nav.current_stage(quick) == "implement":
                break
            quick = walk(quick, [step])
        quick = submit(quick, REVISE)
        broken = without(quick, lambda row: not (row["stage"] == "step-plan" and row["outcome"] == "done"))
        with self.assertRaisesRegex(nav.NavigatorError, "without an earlier accepted step-plan result"):
            nav.render(dry_run.CORE, dry_run.RUN, broken)

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
