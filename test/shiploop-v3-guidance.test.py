#!/usr/bin/env python3
"""Focused v3 prompt, reference-routing, and cold-context guidance checks.

These tests verify the durable material supplied to a fresh agent. They do not
claim that an LLM interpreted a locator correctly or that Improve executed.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
REFERENCES = SCRIPTS.parent / "references"
IMPROVE_CARD = ROOT / "skills" / "improve" / "SKILL.md"
TEST_HARNESS_STAGES = (
    "test-strategy", "step-plan", "test-spec", "baseline", "test-author", "test-red",
    "implement", "test-green", "test-refine", "regression", "verify",
    "integration-verify", "system-test-author", "system-test",
)
REPEATABLE_TEST_SUITE_ROUTE = (
    "Repeatable test-suite guide: "
    + str(REFERENCES / "repeatable-test-suites.md#select-or-revalidate-the-harness")
)
RELEASE_OPERATION_STAGES = (
    "release-plan",
    "release-check",
    "release",
    "release-verify",
)
RELEASE_OPERATION_LABEL = "Release operation guidance"
RELEASE_OPERATION_REFERENCE = "environment-lifecycle.md#release-operation-ownership"
RELEASE_OPERATION_PATH = REFERENCES / "environment-lifecycle.md"
RELEASE_OPERATION_ANCHOR = "release-operation-ownership"
RELEASE_OPERATION_ROUTE = (
    RELEASE_OPERATION_LABEL + ": " + str(REFERENCES / RELEASE_OPERATION_REFERENCE)
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_navigator_v3_prompts as prompts  # noqa: E402
import shiploop_store as store  # noqa: E402


def heading_anchor(text: str) -> str:
    """Match the simple anchor IDs emitted by the package Markdown headings."""
    value = text.strip().lower()
    value = re.sub(r"\s+#+$", "", value)
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"-+", "-", re.sub(r"\s+", "-", value)).strip("-")


def normalized(text: str) -> str:
    """Compare prompt clauses without making line wrapping part of the contract."""
    return " ".join(text.split())


def result(stage: str, **extra: object) -> dict[str, object]:
    """Return a deliberately synthetic producer result for prompt traversal."""
    return {
        "outcome": "done",
        "summary": f"Synthetic producer result for {stage}.",
        "evidence_refs": [f"synthetic://evidence/{stage}"],
        **extra,
    }


def receipt(stage: str) -> dict[str, object]:
    """Return a synthetic receipt accepted by the pure navigator state API."""
    return {
        "summary": f"Synthetic Improve completion for {stage}.",
        "review_refs": [f"synthetic://review/{stage}"],
        "check_refs": [f"synthetic://check/{stage}"],
        "lessons": f"Synthetic lesson for {stage}.",
    }


class V3GuidanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-v3-guidance-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.run = Path(self.temp.name) / "run"
        self.run.mkdir()

    def state(self) -> dict:
        return navigator.new_state(
            str(self.repo),
            "Build a small capability with the repository's approved convention.",
            protocol_version=3,
            improve_skill="",
        )

    def complete_stage(self, state: dict, **extra: object) -> tuple[dict, str]:
        """Advance one synthetic producer/Improve pair solely to render later packets."""
        stage = navigator.current_stage(state)
        action = dict(navigator.current_action(state))
        waiting = navigator.apply(state, action["id"], result(stage, **extra))
        return navigator.finish_improve(waiting, action["id"], receipt(stage)), action["id"]

    def complete_stage_with_final(
        self, state: dict, final_result: dict[str, object], **extra: object
    ) -> tuple[dict, str]:
        """Import an Improve-revised result through the normal v3 parent transition."""
        stage = navigator.current_stage(state)
        action = dict(navigator.current_action(state))
        waiting = navigator.apply(state, action["id"], result(stage, **extra))
        return (
            navigator.finish_improve(waiting, action["id"], receipt(stage), final_result),
            action["id"],
        )

    def save_reload(self, state: dict) -> dict:
        navigator.save(self.run, state)
        return store.read_record(self.run / "state.md")

    def cold_packet(self, state: dict) -> tuple[dict, str]:
        recovered = self.save_reload(state)
        before = (self.run / "state.md").read_bytes()
        with patch.object(Path, "read_text", side_effect=AssertionError("render read evidence")):
            packet = navigator.render(None, self.run, recovered)
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        return recovered, packet

    def test_stage_reference_catalog_is_complete_and_resolves(self) -> None:
        self.assertEqual(set(prompts.STAGE_REFERENCES), set(prompts.STAGES))
        for stage in prompts.STAGES:
            with self.subTest(stage=stage):
                entries = prompts.STAGE_REFERENCES[stage]
                self.assertIsInstance(entries, tuple)
                self.assertTrue(entries)
                for label, locator in entries:
                    self.assertIsInstance(label, str)
                    self.assertTrue(label.strip())
                    filename, separator, anchor = locator.partition("#")
                    self.assertEqual(separator, "#")
                    self.assertTrue(filename)
                    self.assertTrue(anchor)
                    path = REFERENCES / filename
                    self.assertTrue(path.is_file(), locator)
                    headings = {
                        heading_anchor(match.group(2))
                        for match in re.finditer(
                            r"(?m)^(#{1,6})\s+(.+?)\s*$",
                            path.read_text(encoding="utf-8"),
                        )
                    }
                    self.assertIn(anchor, headings, locator)

    def test_each_current_v3_packet_renders_its_selected_stage_references(self) -> None:
        state = self.state()
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            packet = navigator.render(None, self.run, state)
            for label, locator in prompts.STAGE_REFERENCES[stage]:
                with self.subTest(stage=stage, locator=locator):
                    self.assertIn(label + ": " + str(REFERENCES / locator), packet)
            extra: dict[str, object] = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state, _action_id = self.complete_stage(state, **extra)

    def test_cold_packets_route_the_repeatable_test_suite_guide_to_each_testing_stage(self) -> None:
        """Persisted v3 states retain the direct guide route at testing checkpoints."""
        state = self.state()
        observed: list[str] = []
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            if stage in TEST_HARNESS_STAGES:
                navigator.save(self.run, state)
                before = (self.run / "state.md").read_bytes()
                recovered = store.read_record(self.run / "state.md")
                packet = navigator.render(None, self.run, recovered)

                self.assertEqual((self.run / "state.md").read_bytes(), before)
                self.assertEqual(navigator.current_stage(recovered), stage)
                self.assertEqual(packet.count(REPEATABLE_TEST_SUITE_ROUTE), 1, packet)
                observed.append(stage)

            extra: dict[str, object] = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state, _action_id = self.complete_stage(state, **extra)

        self.assertEqual(tuple(observed), TEST_HARNESS_STAGES)

    def test_cold_release_operation_route_recovers_outer_parents_and_partial_blocker(self) -> None:
        """Synthetic records exercise recovery only; no Improve or release is run."""
        self.assertTrue(RELEASE_OPERATION_PATH.is_file(), RELEASE_OPERATION_PATH)
        headings = {
            heading_anchor(match.group(2))
            for match in re.finditer(
                r"(?m)^(#{1,6})\s+(.+?)\s*$",
                RELEASE_OPERATION_PATH.read_text(encoding="utf-8"),
            )
        }
        self.assertIn(RELEASE_OPERATION_ANCHOR, headings)

        state = self.state()
        observed: list[str] = []
        release_blocked_once = False
        partial_release_refs = [
            "synthetic://release/candidate-identity",
            "synthetic://release/target-evidence-pending",
        ]

        while True:
            stage = navigator.current_stage(state)
            if stage not in RELEASE_OPERATION_STAGES:
                extra: dict[str, object] = {}
                if stage == "plan":
                    extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
                state, _action_id = self.complete_stage(state, **extra)
                state = self.save_reload(state)
                continue

            action = dict(navigator.current_action(state))
            recovered, producer_packet = self.cold_packet(state)
            self.assertEqual(navigator.current_stage(recovered), stage)
            self.assertEqual(navigator.current_action(recovered)["id"], action["id"])
            self.assertEqual(producer_packet.count(RELEASE_OPERATION_ROUTE), 1, producer_packet)

            seed_refs = ["synthetic://release-operation/" + stage + "/candidate"]
            waiting = navigator.apply(
                recovered, action["id"], result(stage, evidence_refs=seed_refs)
            )
            binding_id = waiting["active_improve"]["binding_id"]
            pending, improve_packet = self.cold_packet(waiting)
            child = pending["active_improve"]
            self.assertEqual(navigator.current_action(pending)["id"], action["id"])
            self.assertEqual(child["action_id"], action["id"])
            self.assertEqual(child["stage"], stage)
            self.assertEqual(child["binding_id"], binding_id)
            self.assertEqual(child["binding_id"], pending["run_id"] + "/" + action["id"])
            self.assertEqual(child["seed_result"]["evidence_refs"], seed_refs)
            self.assertEqual(improve_packet.count(RELEASE_OPERATION_ROUTE), 1, improve_packet)

            if stage == "release" and not release_blocked_once:
                release_blocked_once = True
                blocked = navigator.finish_improve(
                    pending,
                    action["id"],
                    receipt(stage),
                    result(
                        stage,
                        outcome="blocked",
                        summary="Synthetic release evidence is partial.",
                        evidence_refs=partial_release_refs,
                    ),
                )
                blocked, blocked_packet = self.cold_packet(blocked)
                self.assertEqual(blocked["status"], "blocked")
                self.assertEqual(navigator.current_stage(blocked), stage)
                self.assertEqual(
                    blocked["accepted"][action["id"]]["evidence_refs"], partial_release_refs
                )
                self.assertEqual(
                    blocked["improve_results"][action["id"]]["seed_result"]["evidence_refs"],
                    seed_refs,
                )
                self.assertEqual(blocked_packet.count(RELEASE_OPERATION_ROUTE), 1, blocked_packet)

                resumed = navigator.control(blocked, "resume")
                state, resumed_packet = self.cold_packet(resumed)
                self.assertEqual(state["status"], "active")
                self.assertEqual(navigator.current_stage(state), stage)
                self.assertEqual(
                    state["accepted"][action["id"]]["evidence_refs"], partial_release_refs
                )
                self.assertEqual(resumed_packet.count(RELEASE_OPERATION_ROUTE), 1, resumed_packet)
                continue

            state = navigator.finish_improve(pending, action["id"], receipt(stage))
            state = self.save_reload(state)
            observed.append(stage)
            if stage == "release-verify":
                break

        self.assertEqual(tuple(observed), RELEASE_OPERATION_STAGES)

    def test_cold_step_plan_keeps_compact_context_and_evidence_locators(self) -> None:
        context = (
            "Convention source: docs/client.md#requests; decision: reuse the existing "
            "client; rationale: it owns retries; revalidate if the client version changes."
        )
        plan_evidence = "docs/client.md#requests"
        state = self.state()
        plan_action = ""
        while navigator.current_stage(state) != "step-plan":
            stage = navigator.current_stage(state)
            extra: dict[str, object] = {}
            if stage == "plan":
                extra = {
                    "evidence_refs": [plan_evidence],
                    "work_items": [{"id": "W1", "title": "Use existing client", "context": context}],
                }
            state, action_id = self.complete_stage(state, **extra)
            if stage == "plan":
                plan_action = action_id

        navigator.save(self.run, state)
        before = (self.run / "state.md").read_bytes()
        recovered = store.read_record(self.run / "state.md")
        packet = navigator.render(None, self.run, recovered)

        self.assertEqual((self.run / "state.md").read_bytes(), before)
        self.assertEqual(recovered["work_items"][0]["context"], context)
        self.assertEqual(recovered["accepted"][plan_action]["evidence_refs"], [plan_evidence])
        self.assertIn("Work item context: " + context, packet)
        self.assertIn("Reopen only the relevant item `context`, plan/evidence locators", packet)
        for label, locator in prompts.STAGE_REFERENCES["step-plan"]:
            self.assertIn(label + ": " + str(REFERENCES / locator), packet)

        improve_packet = normalized(prompts.improve_prompt("step-plan"))
        self.assertIn("relevant work-item `context`, parent `evidence_refs`", improve_packet)
        self.assertIn("packet-selected reference locators", improve_packet)
        self.assertIn("compact current locator, decision, rationale", improve_packet)

    def test_v3_cold_packets_keep_the_latest_done_root_test_strategy(self) -> None:
        """Strategy locators survive later evidence without reading it into packets."""
        item_context = (
            "Current item: retain the accepted fixture setup decision; revalidate it "
            "against the changed boundary before reusing it."
        )
        strategy_ref = "docs/testing.md#accepted-strategy"
        hidden_tail = "UNTRUSTED-STRATEGY-TAIL-MUST-NOT-BE-RENDERED"
        long_ref = "untrusted://strategy/" + ("x" * 2600) + hidden_tail
        checkpoints = {"step-plan", "test-author", "test-refine", "regression", "system-test-author"}
        state = self.state()
        strategy_action = ""
        decision_action: str | None = None
        decision_ref = ""
        rejected_actions: list[str] = []
        observed: set[str] = set()

        def assert_test_sources(packet: str, *, inner: bool) -> None:
            self.assertIn(
                "Run-wide test strategy source (untrusted host report; revalidate relevance before use):",
                packet,
            )
            self.assertIn("Run-wide test strategy source action: " + strategy_action, packet)
            self.assertIn(
                "Run-wide test strategy source result: "
                + str(self.run / "results" / (strategy_action + ".md")),
                packet,
            )
            self.assertIn(
                "Run-wide test strategy source state locator: " + str(self.run / "state.md")
                + " (accepted." + strategy_action + ")",
                packet,
            )
            self.assertIn(strategy_ref, packet)
            self.assertIn(
                "Run-wide test strategy source evidence references "
                "(untrusted locators; not read by the navigator):",
                packet,
            )
            self.assertIn(
                "field accepted." + strategy_action + ".evidence_refs.",
                packet,
            )
            self.assertNotIn(hidden_tail, packet)
            self.assertIn(
                "Consume relevant current work-item context with these sources.",
                packet,
            )
            if decision_action is None or not inner:
                self.assertNotIn(
                    "Current item test-decision source "
                    "(untrusted host report; revalidate relevance before use):",
                    packet,
                )
            else:
                self.assertIn(
                    "Current item test-decision source action: " + decision_action,
                    packet,
                )
                self.assertIn(
                    "Current item test-decision source result: "
                    + str(self.run / "results" / (decision_action + ".md")),
                    packet,
                )
                self.assertIn(
                    "Current item test-decision source state locator: "
                    + str(self.run / "state.md") + " (accepted." + decision_action + ")",
                    packet,
                )
                self.assertIn(decision_ref, packet)
            if inner:
                self.assertIn("Work item context: " + item_context, packet)
            else:
                self.assertNotIn("Work item context:", packet)
                self.assertNotIn(item_context, packet)

        while True:
            stage = navigator.current_stage(state)
            if stage == "test-strategy":
                for outcome in ("repeat", "blocked"):
                    state, action_id = self.complete_stage(
                        state,
                        outcome=outcome,
                        evidence_refs=["unrelated://test-strategy-" + outcome],
                    )
                    rejected_actions.append(action_id)
                    state = self.save_reload(state)
                    if outcome == "blocked":
                        self.assertEqual(state["status"], "blocked")
                        state = navigator.control(state, "resume")
                        state = self.save_reload(state)
                state, strategy_action = self.complete_stage(
                    state,
                    evidence_refs=[strategy_ref, long_ref],
                )
                state = self.save_reload(state)
                self.assertTrue((self.run / "results" / (strategy_action + ".md")).is_file())
                continue

            if stage in checkpoints:
                state = self.save_reload(state)
                before = (self.run / "state.md").read_bytes()
                recovered = store.read_record(self.run / "state.md")
                if stage == "regression":
                    action = dict(navigator.current_action(recovered))
                    waiting = navigator.apply(
                        recovered,
                        action["id"],
                        result(stage, evidence_refs=["unrelated://pending-improve"]),
                    )
                    navigator.save(self.run, waiting)
                    pending_before = (self.run / "state.md").read_bytes()
                    pending = store.read_record(self.run / "state.md")
                    with patch.object(Path, "read_text", side_effect=AssertionError("render read evidence")):
                        packet = navigator.render(None, self.run, pending)
                    self.assertEqual((self.run / "state.md").read_bytes(), pending_before)
                    self.assertIn("Current action: Improve the completed regression result.", packet)
                    assert_test_sources(packet, inner=True)
                    observed.add(stage)
                    observed.add("pending Improve")
                    state = navigator.finish_improve(pending, action["id"], receipt(stage))
                    state = self.save_reload(state)
                    decision_action = action["id"]
                    decision_ref = "unrelated://pending-improve"
                    continue

                with patch.object(Path, "read_text", side_effect=AssertionError("render read evidence")):
                    packet = navigator.render(None, self.run, recovered)
                self.assertEqual((self.run / "state.md").read_bytes(), before)
                assert_test_sources(packet, inner=stage != "system-test-author")
                observed.add(stage)
                if stage == "system-test-author":
                    break

            extra: dict[str, object] = {"evidence_refs": ["unrelated://" + stage]}
            if stage == "plan":
                extra["work_items"] = [
                    {"id": "W1", "title": "Synthetic item", "context": item_context}
                ]
            state, action_id = self.complete_stage(state, **extra)
            state = self.save_reload(state)
            if stage in prompts.TEST_DECISION_STAGES:
                decision_action = action_id
                decision_ref = "unrelated://" + stage

        self.assertEqual(observed, checkpoints | {"pending Improve"})
        for action_id in rejected_actions:
            self.assertNotIn("accepted." + action_id, packet)
            self.assertNotIn(str(self.run / "results" / (action_id + ".md")), packet)

    def test_current_item_test_decision_source_is_revised_and_item_scoped(self) -> None:
        """Only the current item's latest accepted decision is retained in a packet."""
        contexts = {
            "W1": "W1 context: retain its isolated fixture decision.",
            "W2": "W2 context: use its separate compatibility fixture.",
        }
        strategy_ref = "docs/testing.md#run-wide-strategy"
        changed_step_plan_ref = "docs/testing.md#revised-step-plan"
        draft_step_plan_ref = "untrusted://draft-step-plan"
        author_ref = "docs/testing.md#authored-case"
        refine_ref = "docs/testing.md#refined-case"
        regression_repeat_ref = "untrusted://regression-repeat"
        regression_ref = "docs/testing.md#regression-decision"
        w2_ref = "docs/testing.md#w2-decision"
        state = self.state()
        strategy_action = ""

        def assert_sources(packet: str, action_id: str, reference: str) -> None:
            self.assertIn("Run-wide test strategy source action: " + strategy_action, packet)
            self.assertIn(strategy_ref, packet)
            self.assertIn("Current item test-decision source action: " + action_id, packet)
            self.assertIn(
                "Current item test-decision source result: "
                + str(self.run / "results" / (action_id + ".md")),
                packet,
            )
            self.assertIn(
                "Current item test-decision source state locator: "
                + str(self.run / "state.md") + " (accepted." + action_id + ")",
                packet,
            )
            self.assertIn(reference, packet)

        while navigator.current_stage(state) != "plan":
            stage = navigator.current_stage(state)
            state, action_id = self.complete_stage(
                state,
                evidence_refs=[strategy_ref if stage == "test-strategy" else "unrelated://" + stage],
            )
            state = self.save_reload(state)
            if stage == "test-strategy":
                strategy_action = action_id
        state, _plan_action = self.complete_stage(
            state,
            work_items=[
                {"id": "W1", "title": "First item", "context": contexts["W1"]},
                {"id": "W2", "title": "Second item", "context": contexts["W2"]},
            ],
            evidence_refs=["unrelated://plan"],
        )
        state = self.save_reload(state)
        self.assertEqual(navigator.current_stage(state), "prepare")
        state, _prepare_action = self.complete_stage(state, evidence_refs=["unrelated://prepare"])
        state = self.save_reload(state)
        self.assertEqual(navigator.current_stage(state), "select-work")
        state, _select_action = self.complete_stage(state, evidence_refs=["unrelated://select-w1"])
        state = self.save_reload(state)
        self.assertEqual(navigator.current_stage(state), "step-plan")

        final_step_plan = result(
            "step-plan",
            summary="Improve revised the W1 test decision.",
            evidence_refs=[changed_step_plan_ref],
        )
        state, step_plan_action = self.complete_stage_with_final(
            state,
            final_step_plan,
            evidence_refs=[draft_step_plan_ref],
        )
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "test-spec")
        assert_sources(packet, step_plan_action, changed_step_plan_ref)
        self.assertNotIn(draft_step_plan_ref, packet)
        self.assertIn("Work item context: " + contexts["W1"], packet)

        state, test_spec_action = self.complete_stage(
            state, evidence_refs=["docs/testing.md#test-spec"]
        )
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "baseline")
        assert_sources(packet, test_spec_action, "docs/testing.md#test-spec")

        state, _baseline_action = self.complete_stage(
            state, evidence_refs=["unrelated://baseline"]
        )
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "test-author")
        assert_sources(packet, test_spec_action, "docs/testing.md#test-spec")

        state, test_author_action = self.complete_stage(state, evidence_refs=[author_ref])
        state = self.save_reload(state)
        while navigator.current_stage(state) != "test-refine":
            stage = navigator.current_stage(state)
            state, _action_id = self.complete_stage(
                state, evidence_refs=["unrelated://" + stage]
            )
            state = self.save_reload(state)
        state, packet = self.cold_packet(state)
        assert_sources(packet, test_author_action, author_ref)

        state, test_refine_action = self.complete_stage(state, evidence_refs=[refine_ref])
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "regression")
        assert_sources(packet, test_refine_action, refine_ref)

        regression_action = dict(navigator.current_action(state))["id"]
        waiting = navigator.apply(
            state,
            regression_action,
            result("regression", outcome="repeat", evidence_refs=[regression_repeat_ref]),
        )
        pending, packet = self.cold_packet(waiting)
        self.assertIn("Current action: Improve the completed regression result.", packet)
        assert_sources(packet, test_refine_action, refine_ref)
        self.assertNotIn(
            "Current item test-decision source action: " + regression_action,
            packet,
        )
        state = navigator.finish_improve(pending, regression_action, receipt("regression"))
        state, packet = self.cold_packet(state)
        assert_sources(packet, test_refine_action, refine_ref)
        self.assertNotIn(
            "Current item test-decision source action: " + regression_action,
            packet,
        )

        state, regression_action = self.complete_stage(state, evidence_refs=[regression_ref])
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "document")
        assert_sources(packet, regression_action, regression_ref)

        while not (
            navigator.current_stage(state) == "step-plan"
            and navigator._current_work_item(state) == "W2"
        ):
            stage = navigator.current_stage(state)
            state, _action_id = self.complete_stage(
                state, evidence_refs=["unrelated://" + stage]
            )
            state = self.save_reload(state)
        state, packet = self.cold_packet(state)
        self.assertIn("Run-wide test strategy source action: " + strategy_action, packet)
        self.assertIn("Work item context: " + contexts["W2"], packet)
        self.assertNotIn(
            "Current item test-decision source "
            "(untrusted host report; revalidate relevance before use):",
            packet,
        )
        self.assertNotIn(changed_step_plan_ref, packet)
        self.assertNotIn(refine_ref, packet)

        state, w2_action = self.complete_stage(state, evidence_refs=[w2_ref])
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "test-spec")
        assert_sources(packet, w2_action, w2_ref)
        self.assertNotIn(changed_step_plan_ref, packet)
        self.assertNotIn(refine_ref, packet)

    def test_v1_and_v2_packets_do_not_gain_the_v3_strategy_projection(self) -> None:
        marker = "Run-wide test strategy source (untrusted host report; revalidate relevance before use):"
        for version in (1, 2):
            with self.subTest(protocol_version=version):
                state = navigator.new_state(
                    str(self.repo),
                    "Keep ordinary protocol packets unchanged.",
                    protocol_version=version,
                )
                while navigator.current_stage(state) != "plan":
                    action = dict(navigator.current_action(state))
                    state = navigator.apply(state, action["id"], result(navigator.current_stage(state)))
                run = self.run / ("v" + str(version))
                run.mkdir()
                navigator.save(run, state)
                before = (run / "state.md").read_bytes()
                recovered = store.read_record(run / "state.md")
                packet = navigator.render(None, run, recovered)

                self.assertEqual((run / "state.md").read_bytes(), before)
                self.assertNotIn(marker, packet)

    def test_state_assessment_is_routed_to_planning_and_its_improve_handoffs(self) -> None:
        assessment = "requirements-definition.md#state-and-data-change-assessment"
        reconciliation = "requirements-definition.md#initial-plan-reconciliation"
        stages = {"spec", "test-strategy", "plan", "step-plan", "carry-forward", "release-plan"}
        for stage in prompts.STAGES:
            locators = {locator for _label, locator in prompts.STAGE_REFERENCES[stage]}
            with self.subTest(stage=stage):
                self.assertEqual(assessment in locators, stage in stages)
                self.assertEqual(reconciliation in locators, stage == "plan")
                if stage in stages:
                    self.assertIn("State and data assessment", prompts.improve_prompt(stage))
        self.assertIn("Initial-plan reconciliation", prompts.prompt("plan"))
        self.assertIn("State and data assessment", prompts.prompt("spec"))
        # This is guidance within existing stages, not another runtime owner.
        self.assertFalse(any("assessment" in stage or "reconciliation" in stage for stage in prompts.STAGES))

    def test_synthetic_planning_fixtures_have_executable_baselines(self) -> None:
        """Fixture health is not evidence that a model produced an adequate plan."""
        fixtures = ROOT / "test" / "experiments" / "shiploop_state_planning"
        commands = {
            "memory-utility": ["-m", "unittest", "test_minute_tally.py"],
            "crm-board": ["verify_board.py"],
            "import-projection": ["-m", "unittest", "test_imports.py"],
        }
        for case, args in commands.items():
            with self.subTest(case=case):
                root = fixtures / case
                self.assertTrue((root / "request.md").read_text().strip())
                self.assertTrue((root / "frozen-rubric.md").read_text().strip())
                self.assertFalse((root / "repo" / "frozen-rubric.md").exists())
                checked = subprocess.run(
                    [sys.executable, "-B", *args], cwd=root / "repo",
                    text=True, capture_output=True, timeout=10,
                )
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_cold_initial_plan_preserves_state_obligations_through_improve(self) -> None:
        state = self.state()
        while navigator.current_stage(state) != "plan":
            state, _ = self.complete_stage(state)
        action = dict(navigator.current_action(state))
        refs = ["docs/architecture.md#access", "docs/spec.md#staff-board", "test/access.py#wrong-user"]
        context = (
            "Intended consumer: staff; deploy operator is separate. "
            "Access proof and wrong-user check: docs/spec.md#staff-board; "
            "test/access.py#wrong-user. Revalidate target before verification."
        )
        state = navigator.apply(state, action["id"], result(
            "plan", evidence_refs=refs,
            work_items=[{"id": "ACCESS", "title": "Establish intended consumer access", "context": context}],
        ))
        navigator.save(self.run, state)
        recovered = store.read_record(self.run / "state.md")
        packet = navigator.render(None, self.run, recovered)
        self.assertEqual(navigator.current_stage(recovered), "plan")
        self.assertEqual(navigator.current_action(recovered)["id"], action["id"])
        self.assertEqual(recovered["active_improve"]["seed_result"]["evidence_refs"], refs)
        self.assertIn("Initial-plan reconciliation", packet)
        self.assertIn("State and data assessment", packet)
        # Synthetic review receipt exercises transport only, not semantic review.
        recovered = navigator.finish_improve(recovered, action["id"], receipt("plan"))
        while navigator.current_stage(recovered) != "step-plan":
            recovered, _ = self.complete_stage(recovered)
        navigator.save(self.run, recovered)
        cold = store.read_record(self.run / "state.md")
        self.assertEqual(cold["work_items"][0]["context"], context)
        self.assertEqual(cold["accepted"][action["id"]]["evidence_refs"], refs)
        self.assertIn("Work item context: " + context, navigator.render(None, self.run, cold))

    def test_v3_improve_and_source_return_guidance_keep_the_existing_boundary(self) -> None:
        card = IMPROVE_CARD.read_text(encoding="utf-8")
        self.assertIn("## ShipLoop v3 whole-skill subcall", card)
        self.assertIn("standalone whole-skill subcall", card)
        self.assertIn("default no-commit constraint overrides", card)
        self.assertIn("`managed-improve`", card)
        self.assertIn("Do not use `managed_controller.py`", card)

        discovery = normalized(prompts.prompt("discovery"))
        prepare = normalized(prompts.prompt("prepare"))
        self.assertIn("returning to the original source branch triggers CI, deployment", discovery)
        self.assertIn("source-return trigger", prepare)
        self.assertIn("do not return early, deploy, or bypass the final-handoff return guard", prepare)


if __name__ == "__main__":
    unittest.main(verbosity=2)
