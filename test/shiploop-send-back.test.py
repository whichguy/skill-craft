#!/usr/bin/env python3
"""The send-back outcome: a work item whose goal proves wrong goes back to its step plan.

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

SEND_BACK = {"outcome": "send-back", "summary": "A completion criterion is unachievable as planned."}


def drive_to(stage: str, *, two: bool = False) -> dict:
    """Walk the dry-run declarations until the current stage is ``stage``."""
    state = nav.new_state("/simulation-only/repo", "Send-back fixture.", delegation=nav.DEFAULT_DELEGATION)
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
    """After a send-back: replay the dry-run rows from the item's step-plan up to its implement."""
    rows = dry_run.activity(two=two)
    first = next(i for i, row in enumerate(rows) if row["at"] == "step-plan")
    until = next(i for i, row in enumerate(rows) if row["at"] == "implement")
    return walk(state, rows[first:until])


def last_action(state: dict, stage: str, outcome: str, item: str = "W1") -> str:
    return [row["action"] for row in state["history"]
            if row["stage"] == stage and row["outcome"] == outcome and row["workitem"] == item][-1]


def result_path(action: str) -> str:
    return "RUN/results/" + action + ".md"   # a prose path prints as the References block's symbol (2026-10-16)


class SendBackTests(unittest.TestCase):
    def test_send_back_returns_the_item_to_step_plan_with_a_fresh_action(self) -> None:
        state = drive_to("implement")
        old_action = nav.current_action(state)["id"]
        state = submit(state, SEND_BACK)
        self.assertEqual(nav.current_stage(state), "step-plan")
        self.assertEqual(state["status"], "active")
        self.assertEqual(state["revisions"], {"W1": 1})
        self.assertNotEqual(nav.current_action(state)["id"], old_action)
        self.assertEqual(state["history"][-1]["outcome"], "send-back")

    def test_the_budget_is_two_send_backs_per_item_then_the_user_decides(self) -> None:
        state = drive_to("implement")
        for used in (1, 2):
            state = submit(state, SEND_BACK)
            self.assertEqual(state["revisions"], {"W1": used})
            # Walk step-plan (with its Improve stage) back to implement.
            for step in dry_run.activity():
                if nav.current_stage(state) == "implement":
                    break
                if step["at"] != nav.sequence_stage(state):
                    continue
                action = nav.current_action(state)["id"]
                if step["command"] == "produce":
                    state = nav.apply(state, action, step["result"])
                else:
                    state = nav.finish_improve(state, action, step["receipt"], step.get("final_result"))
            self.assertEqual(nav.current_stage(state), "implement")
        with self.assertRaisesRegex(nav.NavigatorError, "used its 2 send-backs.*report blocked awaiting a decision"):
            submit(state, SEND_BACK)
        # The refusal names its exit, so the exit goes through the real gate: a blocked result awaiting the user's answer.
        blocked = submit(state, {"outcome": "blocked",
                                 "awaiting": {"kind": "answer", "question": "Which criterion yields: C1 or C2?",
                                              "options": ["C1", "C2"],
                                              "no_default": "The plan cannot meet both criteria and either choice "
                                                            "changes the product."},
                                 "summary": "The step plan cannot meet criterion C2; the user decides."})
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["status_reason"], "answer: The step plan cannot meet criterion C2; the user decides.")

    def test_the_retired_outcome_names_are_refused_at_inner_and_outer_stages(self) -> None:
        # revise became send-back and replan became add-work (run-insights N5); repeat is gone.  No alias is accepted,
        # and the refusal lists the stage's own outcomes.
        for stage, outcomes in (("implement", "done, blocked, send-back"), ("product-acceptance", "done, blocked, add-work")):
            state = drive_to(stage)
            for retired in ("revise", "replan", "repeat"):
                with self.subTest(stage=stage, outcome=retired), self.assertRaisesRegex(
                        nav.NavigatorError, "must be one of " + outcomes + " at " + stage
                        + ".*revise, replan and repeat are retired"):
                    submit(state, {"outcome": retired, "summary": "A retired outcome name."})
            self.assertEqual(state["status"], "active")

    def test_a_non_done_result_at_a_reviewed_planning_stage_is_accepted_with_no_improve_record(self) -> None:
        # Improve starts only on a done result (run-insights N5), at every reviewed stage, planning stages included.
        # So a blocked, send-back or add-work result at one is accepted as it stands, and the state it leaves must
        # still validate: nothing may demand an Improve record for a result that was never reviewed.
        wait = {"kind": "answer", "question": "Which design stays?", "no_default": "Either choice changes the product."}
        cases = (("step-plan", {"outcome": "blocked", "summary": "A decision is needed.", "awaiting": wait}, "blocked"),
                 ("test-spec", SEND_BACK, "active"),
                 ("system-test-author", {"outcome": "add-work", "summary": "Missing product work.",
                                         "work_items": [{"id": "W9", "title": "Corrective item."}]}, "active"))
        for stage, result, status in cases:
            state = drive_to(stage)
            with self.subTest(stage=stage, outcome=result["outcome"]):
                action = nav.current_action(state)["id"]
                after = submit(state, result)
                self.assertIsNone(after["active_improve"])
                self.assertIn(action, after["accepted"])
                self.assertNotIn(action, after["improve_results"])
                self.assertEqual(after["status"], status)
                nav.validate(after)

    def test_send_back_is_allowed_only_where_the_stage_table_allows_it(self) -> None:
        # The INNER stages from test-spec to verify send an item back to its step plan; two OUTER stages send the run back
        # to the stage that wrote their plan (run-insights N5, build plan S1.5).
        self.assertEqual(spec.with_outcome("send-back"),
                         ("test-spec", "validate-existing", "implement", "test", "document", "verify", "system-test",
                          "release-verify"))
        for stage in ("intake", "plan", "step-plan", "carry-forward", "system-test-author", "release-plan", "release"):
            with self.subTest(stage=stage):
                state = drive_to(stage)
                with self.assertRaisesRegex(nav.NavigatorError, "send-back sends a result back to the stage that wrote "
                                            "the wrong record and is allowed only at"):
                    submit(state, SEND_BACK)

    def test_earlier_results_of_a_sent_back_item_are_no_longer_current(self) -> None:
        state = drive_to("implement")
        current = planning_revision.current_actions(state)
        self.assertIn(("W1", "test-spec"), current)
        self.assertIn(("W1", "validate-existing"), current)
        state = submit(state, SEND_BACK)
        current = planning_revision.current_actions(state)
        self.assertNotIn(("W1", "step-plan"), current)
        self.assertNotIn(("W1", "test-spec"), current)
        self.assertNotIn(("W1", "validate-existing"), current)
        self.assertIn((None, "prepare"), current)
        self.assertIn((None, "plan"), current)

    def test_packet_states_the_send_back_outcome_and_budget(self) -> None:
        state = drive_to("test")
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn("Allowed outcomes: done | blocked | send-back (", packet)
        self.assertIn("2 of 2 left for this item", packet)
        state = submit(state, SEND_BACK)
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        # The one-line status (packet review U5) has no "(sent back ...)" suffix; the revisit block says it (U4).
        self.assertIn("Revisit: test sent W1 back to step-plan (1 of 2 send-backs)", packet)

    def test_a_redone_step_plan_packet_names_the_previous_plan_and_the_send_back_result(self) -> None:
        state = drive_to("implement")
        plan = last_action(state, "step-plan", "done")
        state = submit(state, SEND_BACK)
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
        redone = submit(drive_to("implement"), SEND_BACK)
        head = nav.packet_head(dry_run.CORE, dry_run.RUN, redone, dry_run.RUN / "packets" / "redo.md")
        done_when = head[head.index("Done when"):head.index("Checked by")]
        self.assertIn("carried over", done_when)

    def test_a_second_send_back_names_the_latest_plan_and_the_latest_send_back_result(self) -> None:
        state = submit(drive_to("implement"), SEND_BACK)
        first_plan = last_action(state, "step-plan", "done")
        first_sent_back = state["history"][-1]["action"]
        state = back_to_implement(state)
        second_plan = last_action(state, "step-plan", "done")
        self.assertNotEqual(first_plan, second_plan)
        state = submit(state, SEND_BACK)
        second_sent_back = state["history"][-1]["action"]
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn(result_path(second_plan), packet)
        self.assertIn(result_path(second_sent_back), packet)
        self.assertNotIn(result_path(first_plan), packet)
        self.assertNotIn(result_path(first_sent_back), packet)

    def test_the_amend_lines_survive_a_refused_repeat_of_the_redone_step_plan(self) -> None:
        # The redone plan goes round again inside its Until Loop, never through the graph: a repeat callback is refused
        # (repeat is retired), and the packet still names the plan to amend and the send-back result.
        state = drive_to("implement")
        plan = last_action(state, "step-plan", "done")
        state = submit(state, SEND_BACK)
        sent_back = state["history"][-1]["action"]
        with self.assertRaisesRegex(nav.NavigatorError, "revise, replan and repeat are retired"):
            submit(state, {"outcome": "repeat", "summary": "The redone plan is not finished."})
        self.assertEqual(nav.current_stage(state), "step-plan")
        self.assertEqual(state["history"][-1]["outcome"], "send-back")
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertIn(result_path(plan), packet)
        self.assertIn(result_path(sent_back), packet)

    def test_a_first_visit_and_the_next_item_print_no_amend_lines(self) -> None:
        # GUARD, green before and after: a first visit and another item are never asked to amend.  (Until 2026-10-17
        # this also held that the redone test spec printed nothing of the send-back; packet review X2 reversed that: see
        # test_every_revisited_stage_head_prints_the_four_revisit_lines.)
        head_of = lambda state: nav.packet_head(dry_run.CORE, dry_run.RUN, state, dry_run.RUN / "packets" / "x.md")
        self.assertNotIn("carried over", head_of(drive_to("step-plan", two=True)))
        state = drive_to("implement", two=True)
        plan = last_action(state, "step-plan", "done")
        state = submit(state, SEND_BACK)
        sent_back = state["history"][-1]["action"]
        rows = dry_run.activity(two=True)
        step_plan = next(i for i, row in enumerate(rows) if row["at"] == "step-plan")
        test_spec = next(i for i, row in enumerate(rows) if row["at"] == "test-spec")
        state = walk(state, rows[step_plan:test_spec])
        self.assertEqual(nav.current_stage(state), "test-spec")
        # W2 reaches its own step plan once W1 finishes: nothing of W1's plans or send-back result is named.
        first_carry = next(i for i, row in enumerate(rows) if row["at"] == "carry-forward")
        second_item = next(i for i, row in enumerate(rows) if i > first_carry and row["at"] == "step-plan")
        state = walk(state, rows[test_spec:second_item])
        self.assertEqual(state["work_items"][state["work_index"]]["id"], "W2")
        self.assertEqual(nav.current_stage(state), "step-plan")
        packet = nav.render(dry_run.CORE, dry_run.RUN, state)
        self.assertNotIn(result_path(plan), packet)
        self.assertNotIn(result_path(sent_back), packet)
        self.assertNotIn("carried over", head_of(state))

    def test_every_revisited_stage_head_prints_the_four_revisit_lines(self) -> None:
        """Packet review F5 (C X1, X2, C2-1, C2-8): after a send-back, the first printed head of step-plan, test-spec and
        implement says why the stage is back (the send-back result's summary and path), names its previous accepted result,
        lists the IDs the redone upstream results added, removed or changed, and asks to keep unchanged rows with their
        IDs.  Before, only step-plan's packet file said so; a redone test spec searched the run for its own earlier result.
        Each result goes through the real gate; the amended plan adds step S2."""
        head_of = lambda state: nav.packet_head(dry_run.CORE, dry_run.RUN, state, dry_run.RUN / "packets" / "x.md")
        state = drive_to("implement")
        plan, spec_before = last_action(state, "step-plan", "done"), last_action(state, "test-spec", "done")
        state = submit(state, SEND_BACK)
        sent_back = state["history"][-1]["action"]
        why = ("Revisit: implement sent W1 back to step-plan (1 of 2 send-backs)", '"' + SEND_BACK["summary"] + '"',
               "Evidence: " + result_path(sent_back) + ".")
        keep = "Keep unchanged rows with their IDs: carry over as written every row the send-back result"

        head = head_of(state)
        self.assertEqual(nav.current_stage(state), "step-plan")
        for token in (*why, "this packet asks for an amended plan, not a new one",
                      "Your previous accepted step-plan result: " + result_path(plan),
                      "Changed upstream since your previous step plan: nothing", keep,
                      "Submit the whole amended plan: it replaces the previous one."):
            self.assertIn(token, head)
        rows = dry_run.activity()
        produced = next(row["result"] for row in rows if row["at"] == "step-plan")
        amended = dict(produced, steps=[*produced["steps"], {"id": "S2", "task": "Second synthetic step.", "deps": ["S1"]}])
        state = submit(state, amended)
        state = nav.finish_improve(state, nav.current_action(state)["id"], dry_run._improve_receipt("step-plan"), None)
        new_plan = last_action(state, "step-plan", "done")

        head = head_of(state)
        self.assertEqual(nav.current_stage(state), "test-spec")
        upstream = ("Changed upstream since your previous test-spec result (step plan " + result_path(plan) + " -> "
                    + result_path(new_plan) + "): steps added S2.")
        for token in (*why, "Your previous accepted test-spec result: " + result_path(spec_before), upstream, keep):
            self.assertIn(token, head)
        self.assertNotIn("amended plan", head)
        self.assertIn("carried over from the previous test-spec result", head[head.index("Done when"):])

        test_spec = next(i for i, row in enumerate(rows) if row["at"] == "test-spec")
        until = next(i for i, row in enumerate(rows) if row["at"] == "implement")
        state = walk(state, rows[test_spec:until])
        head = head_of(state)
        self.assertEqual(nav.current_stage(state), "implement")
        for token in (*why, "Your previous accepted implement result: none (this stage had no accepted result for W1 "
                            "before the send-back).", "Changed upstream since your previous implement result (step plan "
                      + result_path(plan) + " -> " + result_path(new_plan), "steps added S2", keep):
            self.assertIn(token, head)
        self.assertNotIn("carried over from the previous implement result", head)  # there is none to carry over

        # The amended plan's second step is no revisit: its implement result after the send-back exists.
        state = walk(state, [row for row in rows[until:] if row["at"] in ("implement", nav.IMPROVE_STAGE)][:2])
        self.assertEqual(nav.current_stage(state), "implement")
        self.assertIn("Step S2 (2 of 2)", head_of(state))
        self.assertNotIn("Revisit: ", head_of(state))

    def test_an_amended_step_plan_is_accepted_through_the_gate(self) -> None:
        state = submit(drive_to("implement"), SEND_BACK)
        amended = {"outcome": "done",
                   "summary": "Amended step plan: C1 and its command are carried over; step 2 is new.",
                   "test_commands": [{"command": "python3 -m unittest discover -s tests", "suite": "focused"}]}
        state = submit(state, amended)
        self.assertIsNotNone(state["active_improve"])
        state = nav.finish_improve(state, nav.current_action(state)["id"],
                                   dry_run._improve_receipt("step-plan"), None)
        self.assertEqual(nav.current_stage(state), "test-spec")
        self.assertIn("carried over", state["accepted"][last_action(state, "step-plan", "done")]["summary"])

    def test_a_state_that_records_a_send_back_without_its_rows_is_refused_at_render(self) -> None:
        # Not reachable through the gate: history is append-only and a send-back always adds its row.
        # The render refuses such a state instead of printing a plan it cannot name.
        def without(state: dict, keep) -> dict:
            broken = deepcopy(state)
            gone = [row["action"] for row in broken["history"] if not keep(row)]
            broken["history"] = [row for row in broken["history"] if keep(row)]
            for action in gone:
                broken["accepted"].pop(action)
            return broken

        state = submit(drive_to("implement"), SEND_BACK)
        with self.assertRaisesRegex(nav.NavigatorError, "records a send-back but no send-back result"):
            nav.render(dry_run.CORE, dry_run.RUN, without(state, lambda row: row["outcome"] != "send-back"))
        # With planning_review none the step plan has no Improve result tying it to the history.
        quick = nav.new_state("/simulation-only/repo", "Send-back fixture.", delegation=nav.DEFAULT_DELEGATION,
                              planning_review="none")
        for step in dry_run.activity("none"):
            if nav.current_stage(quick) == "implement":
                break
            quick = walk(quick, [step])
        quick = submit(quick, SEND_BACK)
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
        # A run saved by the 17-stage inner loop (state version 4) is refused with its own reason.
        # A run saved before the consumer contract's hand-off fields (state version 5) is refused by the version check.
        # T17 (implement-step fix plan): a run saved before each step recorded its Proof (state version 6) has its own
        # reason too; no Proof is ever made up for it.
        # N5 (four outcomes, `awaiting`): a run saved by state version 7 is refused by the version check like any other.
        for version, reason in ((3, "state version 3 is not the supported version 8"),
                                (4, "seventeen-stage inner loop \\(state version 4\\)"),
                                (5, "state version 5 is not the supported version 8"),
                                (6, "before each implementation step recorded its Proof \\(state version 6\\)"),
                                (7, "state version 7 is not the supported version 8")):
            wrong_version = deepcopy(state)
            wrong_version["version"] = version
            with self.subTest(version=version), self.assertRaisesRegex(
                    nav.NavigatorError, reason + ".*fresh --run-dir"):
                nav.validate(wrong_version)

    def test_revisions_must_name_real_items_within_the_budget(self) -> None:
        state = drive_to("implement")
        for bad in ({"W9": 1}, {"W1": 0}, {"W1": 3}):
            broken = deepcopy(state)
            broken["revisions"] = bad
            with self.subTest(revisions=bad), self.assertRaisesRegex(nav.NavigatorError, "revisions must map"):
                nav.validate(broken)


OUTER_SEND_BACK = {"outcome": "send-back", "summary": "A case the plan records cannot observe the clause it names."}


def outer_rows(start: str, stop: str) -> list:
    """The dry-run declarations from ``start``'s producer row up to, not including, ``stop``'s."""
    rows = dry_run.activity()
    first = next(i for i, row in enumerate(rows) if row["at"] == start and row["command"] == "produce")
    last = next(i for i, row in enumerate(rows) if i > first and row["at"] == stop and row["command"] == "produce")
    return rows[first:last]


class OuterSendBackTests(unittest.TestCase):
    """system-test sends the run back to system-test-author, and release-verify to release-plan (N5, S1.5)."""

    PAIRS = (("system-test", "system-test-author"), ("release-verify", "release-plan"))

    def test_an_outer_send_back_reruns_the_stage_that_wrote_the_plan_with_a_fresh_action(self) -> None:
        for stage, target in self.PAIRS:
            with self.subTest(stage=stage):
                state = drive_to(stage)
                sent = submit(state, OUTER_SEND_BACK)
                nav.validate(sent)
                self.assertEqual((nav.current_stage(sent), sent["status"]), (target, "active"))
                self.assertEqual(sent["revisions"], {target: 1})
                self.assertIsNone(sent["active_improve"])
                self.assertNotIn(nav.current_action(sent)["id"], state["accepted"])
                # The stages after the target run again in order, back to the stage that sent it.
                again = walk(sent, outer_rows(target, stage))
                self.assertEqual(nav.current_stage(again), stage)

    def test_the_outer_budget_is_two_send_backs_per_target_then_the_user_decides(self) -> None:
        for stage, target in self.PAIRS:
            with self.subTest(stage=stage):
                state = drive_to(stage)
                for count in (1, 2):
                    state = walk(submit(state, OUTER_SEND_BACK), outer_rows(target, stage))
                    self.assertEqual(state["revisions"], {target: count})
                with self.assertRaisesRegex(nav.NavigatorError, "has used its 2 send-backs.*report blocked"):
                    submit(state, OUTER_SEND_BACK)

    def test_the_packet_states_the_target_and_the_redone_stage_names_the_send_back_result(self) -> None:
        for stage, target in self.PAIRS:
            with self.subTest(stage=stage):
                state = drive_to(stage)
                packet = nav.render(dry_run.CORE, dry_run.RUN, state)
                self.assertIn("send-back (", packet)
                self.assertIn("back to " + target, packet)
                self.assertIn("2 of 2 left", packet)
                sent = submit(state, OUTER_SEND_BACK)
                action = last_action(sent, stage, "send-back", item=None)
                packet = nav.render(dry_run.CORE, dry_run.RUN, sent)
                self.assertIn("Revisit: " + stage + " sent the run back to " + target + " (1 of 2 send-backs)", packet)
                self.assertIn("RUN/results/" + action + ".md", packet)
                previous = last_action(state, target, "done", item=None)
                self.assertIn("Your previous accepted " + target + " result: RUN/results/" + previous + ".md", packet)
                # Once the target has an accepted result after the send-back, its next packet is no revisit.
                again = walk(sent, outer_rows(target, stage))
                self.assertNotIn("Revisit:", nav.render(dry_run.CORE, dry_run.RUN, again))

    def test_the_status_names_the_target(self) -> None:
        sent = submit(drive_to("release-verify"), OUTER_SEND_BACK)
        self.assertIn("release-verify (sent back to release-plan)", nav.status_block(sent))

    def test_a_refused_run_tally_still_ends_in_add_work_at_the_outer_test_stages(self) -> None:
        import shiploop_test_loop as test_loop
        self.assertEqual({stage: test_loop._remedy(stage) for stage in ("test", "system-test", "release-verify")},
                         {"test": "send-back", "system-test": "add-work", "release-verify": "add-work"})

    def test_outer_revisions_must_name_a_send_back_target_within_the_budget(self) -> None:
        state = drive_to("release-verify")
        good = deepcopy(state)
        good["revisions"] = {"W1": 1, "system-test-author": 2, "release-plan": 1}
        nav.validate(good)
        for bad in ({"release": 1}, {"release-plan": 3}):
            broken = deepcopy(state)
            broken["revisions"] = bad
            with self.subTest(revisions=bad), self.assertRaisesRegex(nav.NavigatorError, "revisions must map"):
                nav.validate(broken)


if __name__ == "__main__":
    unittest.main()
