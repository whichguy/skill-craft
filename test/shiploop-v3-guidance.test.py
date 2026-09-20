#!/usr/bin/env python3
"""Focused v3 prompt, reference-routing, and cold-context guidance checks.

These tests verify the durable material supplied to a fresh agent. They do not
claim that an LLM interpreted a locator correctly or that Improve executed.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
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
TEST_FACILITY_STAGES = (
    "test-strategy", "plan", "step-plan", "test-spec", "test-author", "test-red",
    "test-refine", "regression", "carry-forward", "system-test-author", "release-plan",
)
REUSABLE_TEST_FACILITY_ROUTE = (
    "Reusable test facilities: "
    + str(REFERENCES / "repeatable-test-suites.md#reuse-and-define-test-facilities")
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

# Deliberately independent of the prompt catalog: these are the only stages
# where a local skill must be discoverable before or during a skill decision.
LOCAL_SKILL_ROUTE_STAGES = (
    "discovery", "step-plan", "skill-assess", "skill-validate",
)
LOCAL_SKILL_GUIDE_ROUTE = (
    "Repository-local skill guidance: "
    + str(REFERENCES / "testing-and-documentation.md#reusable-product-skills")
)
CODING_GUIDE_STAGES = ("step-plan", "implement", "verify")
CODING_GUIDE_ROUTE = (
    "Coding decision guide: " + str(REFERENCES / "coding-guidance.md#select-guidance")
)
CURRENT_SYSTEM_BASELINE_GUIDE = "current-system-baseline.md"
CURRENT_SYSTEM_BASELINE_GUIDANCE_LABEL = "Current-system baseline guide"
CURRENT_SYSTEM_BASELINE_ANCHORS = (
    "establish-or-refresh",
    "evidence-and-authority",
    "remote-only-systems",
    "planning-and-review-handoff",
    "retain-across-runs",
)
# Deliberately independent of the prompt catalog: only these stages receive the
# current-system baseline guide, with the named section for their decision.
CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS = {
    "discovery": "establish-or-refresh",
    "research": "evidence-and-authority",
    "spec": "planning-and-review-handoff",
    "test-strategy": "planning-and-review-handoff",
    "plan": "planning-and-review-handoff",
    "step-plan": "planning-and-review-handoff",
    "document": "retain-across-runs",
    "carry-forward": "retain-across-runs",
    "product-acceptance": "retain-across-runs",
    "handoff": "retain-across-runs",
}
CURRENT_SYSTEM_BASELINE_ROUTES = {
    stage: (
        CURRENT_SYSTEM_BASELINE_GUIDANCE_LABEL
        + ": "
        + str(REFERENCES / (CURRENT_SYSTEM_BASELINE_GUIDE + "#" + anchor))
    )
    for stage, anchor in CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS.items()
}
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_navigator_v3_prompts as prompts  # noqa: E402
import shiploop_standalone_improve as standalone_improve  # noqa: E402
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

    def test_current_system_baseline_stage_routes_are_exact_and_selective(self) -> None:
        """Keep the guide's graph projection independent of the prompt catalog."""
        observed: list[str] = []
        for stage in prompts.STAGES:
            with self.subTest(stage=stage):
                entries = [
                    (label, locator)
                    for label, locator in prompts.STAGE_REFERENCES[stage]
                    if label == CURRENT_SYSTEM_BASELINE_GUIDANCE_LABEL
                ]
                anchor = CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS.get(stage)
                if anchor is None:
                    self.assertEqual(entries, [])
                else:
                    self.assertEqual(
                        entries,
                        [(
                            CURRENT_SYSTEM_BASELINE_GUIDANCE_LABEL,
                            CURRENT_SYSTEM_BASELINE_GUIDE + "#" + anchor,
                        )],
                    )
                    observed.append(stage)
        self.assertEqual(tuple(observed), tuple(CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS))

    def test_current_system_baseline_guide_relocates_with_recovery_cue(self) -> None:
        """The portable guide retains anchors and a minimal stale/missing recovery cue.

        This checks durable guide material only, not whether a host detects or
        refreshes a live snapshot.
        """
        guide = REFERENCES / CURRENT_SYSTEM_BASELINE_GUIDE
        self.assertTrue(guide.is_file(), guide)
        if not guide.is_file():
            return
        body = guide.read_text(encoding="utf-8")
        headings = {
            heading_anchor(match.group(2))
            for match in re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", body)
        }
        for anchor in CURRENT_SYSTEM_BASELINE_ANCHORS:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, headings)

        relocated = (self.repo / "copied-package" / "references").resolve()
        shutil.copytree(REFERENCES, relocated)
        copied_guide = relocated / CURRENT_SYSTEM_BASELINE_GUIDE
        copied_body = copied_guide.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", copied_body)
        recovery = normalized(copied_body).lower()
        self.assertRegex(recovery, r"\b(?:missing|absent|stale|outdated)\b")
        self.assertRegex(recovery, r"\b(?:refresh|re-establish|rebuild|recover)\b")
        for stage, anchor in CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS.items():
            with self.subTest(stage=stage, anchor=anchor):
                filename, separator, route_anchor = (
                    CURRENT_SYSTEM_BASELINE_GUIDE + "#" + anchor
                ).partition("#")
                self.assertEqual(separator, "#")
                destination = relocated / filename
                self.assertTrue(destination.is_file(), destination)
                destination_headings = {
                    heading_anchor(match.group(2))
                    for match in re.finditer(
                        r"(?m)^(#{1,6})\s+(.+?)\s*$",
                        destination.read_text(encoding="utf-8"),
                    )
                }
                self.assertIn(route_anchor, destination_headings)

        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", copied_body):
            if link.startswith(("https://", "http://")):
                continue
            with self.subTest(link=link):
                path, _, anchor = link.partition("#")
                destination = (copied_guide.parent / path).resolve() if path else copied_guide
                self.assertTrue(destination.is_relative_to(relocated), link)
                self.assertTrue(destination.is_file(), link)
                if anchor:
                    destination_headings = {
                        heading_anchor(match.group(2))
                        for match in re.finditer(
                            r"(?m)^(#{1,6})\s+(.+?)\s*$",
                            destination.read_text(encoding="utf-8"),
                        )
                    }
                    self.assertIn(anchor, destination_headings)

    def test_current_system_baseline_routes_survive_cold_lifecycle_and_pending_improve(self) -> None:
        """Cold packets preserve only the relevant locator through one synthetic run.

        This exercises save/reload and normal producer/Improve transitions. It
        proves route plumbing and explicitly supplied handoff locators, not that
        a model validated a source, understood a baseline, or performed a real
        review.
        """
        routes = tuple(dict.fromkeys(CURRENT_SYSTEM_BASELINE_ROUTES.values()))
        notes = self.run / "notes"
        notes.mkdir()
        prior_baseline = notes / "prior-baseline.md"
        incoming_spec = notes / "incoming-spec.md"
        prior_baseline.write_text(
            "# Prior product baseline\n\n## Accepted baseline\n\nFixture baseline.\n",
            encoding="utf-8",
        )
        incoming_spec.write_text(
            "# Incoming specification\n\n## Requested delta\n\nFixture delta.\n",
            encoding="utf-8",
        )
        prior_baseline_ref = str(prior_baseline) + "#accepted-baseline"
        incoming_delta_ref = str(incoming_spec) + "#requested-delta"
        product_refs = [prior_baseline_ref, incoming_delta_ref]
        item_context = (
            "W1 host-authored current-system handoff: reopen prior baseline "
            + prior_baseline_ref
            + " and incoming delta "
            + incoming_delta_ref
            + "; retain their selected sections and revalidation condition."
        )
        observed: list[str] = []
        state = self.state()

        def assert_packet(stage: str, packet: str) -> None:
            expected = CURRENT_SYSTEM_BASELINE_ROUTES.get(stage)
            for route in routes:
                with self.subTest(stage=stage, route=route):
                    self.assertEqual(packet.count(route), int(route == expected), packet)

        while state["status"] != "done":
            stage = navigator.current_stage(state)
            recovered, producer_packet = self.cold_packet(state)
            self.assertEqual(navigator.current_stage(recovered), stage)
            assert_packet(stage, producer_packet)
            if stage == "plan":
                # The preceding host-authored test-strategy result explicitly
                # carries these locators; the navigator did not discover them.
                self.assertIn(prior_baseline_ref, producer_packet)
                self.assertIn(incoming_delta_ref, producer_packet)
            if stage == "step-plan":
                self.assertEqual(navigator._current_work_item(recovered), "W1")
                self.assertIn("Work item context: " + item_context, producer_packet)
                self.assertIn(prior_baseline_ref, producer_packet)
                self.assertIn(incoming_delta_ref, producer_packet)

            extra: dict[str, object] = {}
            if stage in {"discovery", "test-strategy", "plan", "step-plan"}:
                # These are synthetic host-authored handoffs in ordinary result
                # fields, never inferred by the navigator from the fixture files.
                extra["evidence_refs"] = product_refs
            if stage == "plan":
                extra["work_items"] = [
                    {
                        "id": "W1",
                        "title": "Retain current-system baseline",
                        "context": item_context,
                    }
                ]
            if stage in CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS:
                action = dict(navigator.current_action(recovered))
                waiting = navigator.apply(recovered, action["id"], result(stage, **extra))
                pending, pending_packet = self.cold_packet(waiting)
                self.assertIsNotNone(pending["active_improve"])
                self.assertEqual(navigator.current_stage(pending), stage)
                self.assertIn("Current action: Improve the completed " + stage, pending_packet)
                assert_packet(stage, pending_packet)
                if stage == "discovery":
                    self.assertIn(prior_baseline_ref, pending_packet)
                    self.assertIn(incoming_delta_ref, pending_packet)
                if stage == "step-plan":
                    self.assertIn("Work item context: " + item_context, pending_packet)
                    self.assertIn(prior_baseline_ref, pending_packet)
                    self.assertIn(incoming_delta_ref, pending_packet)
                observed.append(stage)
                state = navigator.finish_improve(pending, action["id"], receipt(stage))
            else:
                state, _action_id = self.complete_stage(recovered, **extra)

        self.assertEqual(tuple(observed), tuple(CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS))

    def test_cold_lifecycle_packets_keep_clause_surface_and_due_phase(self) -> None:
        """A compact requirement survives planning and due-stage reconciliation.

        This tests supplied guidance and recovery, not whether a host obeys it.
        The expected stages/clauses are declared here independently of routing.
        """
        duties = {
            "spec": "independently verifiable clauses",
            "test-strategy": "required surface and due phase",
            "test-spec": "every assigned clause",
            "test-author": "Authoring is complete",
            "test-refine": "removed or narrowed case",
            "product-acceptance": "pending release verification",
            "release-verify": "usable consumer entry",
        }
        reconciles = {"verify", "integration-verify", "system-test",
                      "product-acceptance", "release-verify", "handoff"}
        locator = str(REFERENCES / "testing-and-documentation.md#stage-readiness-and-completion")
        state = self.state()
        clause = "docs/requirements.md#capture: observe capture in the deployed UI; due release-verify"
        visited = set()
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            recovered, packet = self.cold_packet(state)
            with self.subTest(stage=stage):
                self.assertIn(locator, packet)
                self.assertIn("Definition of Ready", normalized(packet))
                self.assertIn("Definition of Done", normalized(packet))
                if stage in duties:
                    self.assertIn(duties[stage], normalized(packet))
                if stage in reconciles:
                    self.assertIn("required surface and due phase", normalized(packet))
                    self.assertIn("supporting evidence", normalized(packet))
                    self.assertIn("not yet due", normalized(packet))
                if navigator._current_work_item(recovered) is not None:
                    self.assertIn(clause, packet)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Capture behavior", "context": clause}]
            state, _ = self.complete_stage(state, **extra)
            visited.add(stage)
        self.assertEqual(len(visited), 34)

    def test_quality_guidance_keeps_planning_review_and_product_review_distinct(self) -> None:
        for stage in ("spec", "test-spec", "baseline", "release-verify"):
            with self.subTest(stage=stage):
                text = normalized(prompts.improve_prompt(stage))
                self.assertIn("selected staged/unstaged/untracked candidate paths", text)
                self.assertIn("required surface and due phase", text)
                self.assertIn("Repeated wording is a review cue", text)
                self.assertIn("does not require future product checks to pass", text)
        # Inspection of an untracked candidate must not grant edit authority.
        baseline = normalized(prompts.improve_prompt("baseline"))
        self.assertIn("may not edit product source, tests", baseline)

    def test_each_current_v3_packet_renders_its_selected_stage_references(self) -> None:
        state = self.state()
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            packet = navigator.render(None, self.run, state)
            for label, locator in prompts.STAGE_REFERENCES[stage]:
                with self.subTest(stage=stage, locator=locator):
                    self.assertIn(label + ": " + str(REFERENCES / locator), packet)
            if stage in ("plan", "step-plan"):
                # Independent of the catalog: removing this route must not
                # redefine the expected guidance available after cold recovery.
                _recovered, cold_packet = self.cold_packet(state)
                self.assertIn(
                    str(REFERENCES / "project-knowledge.md#investigate-git-history-for-planning"),
                    cold_packet,
                )
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

    def test_cold_local_skill_routes_cover_early_and_late_decisions(self) -> None:
        """Fresh producer and pending-child packets retain the local skill route.

        Navigation and child state here are synthetic protocol setup only.  The
        assertions prove packet routing and cold recovery, not that a host
        interpreted an index or authored a child contract.
        """
        index = self.repo / "SHIPLOOP.md"
        index.write_text("# Fixture local skill index\n", encoding="utf-8")
        index_route = "Repository knowledge index (host-authored, if present): " + str(index)
        observed: list[str] = []

        for target in LOCAL_SKILL_ROUTE_STAGES:
            with self.subTest(stage=target):
                state = self.state()
                while navigator.current_stage(state) != target:
                    stage = navigator.current_stage(state)
                    extra: dict[str, object] = {}
                    if stage == "plan":
                        extra["work_items"] = [{"id": "W1", "title": "Fixture item"}]
                    state, _action_id = self.complete_stage(state, **extra)

                producer, producer_packet = self.cold_packet(state)
                self.assertEqual(navigator.current_stage(producer), target)
                self.assertTrue(index.is_file())
                self.assertEqual(producer_packet.count(LOCAL_SKILL_GUIDE_ROUTE), 1, producer_packet)
                self.assertEqual(producer_packet.count(index_route), 1, producer_packet)

                action = dict(navigator.current_action(producer))
                pending = navigator.apply(producer, action["id"], result(target))
                recovered_pending, pending_packet = self.cold_packet(pending)
                self.assertIsNotNone(recovered_pending["active_improve"])
                self.assertEqual(navigator.current_stage(recovered_pending), target)
                self.assertEqual(pending_packet.count(LOCAL_SKILL_GUIDE_ROUTE), 1, pending_packet)
                self.assertEqual(pending_packet.count(index_route), 1, pending_packet)
                observed.append(target)

        self.assertEqual(tuple(observed), LOCAL_SKILL_ROUTE_STAGES)

    def test_coding_guide_is_selective_in_cold_producer_and_improve_packets(self) -> None:
        """Route locators, not every card body; retain the same owner on recovery."""
        state = self.state()
        observed = []
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            recovered, packet = self.cold_packet(state)
            expected_count = int(stage in CODING_GUIDE_STAGES)
            self.assertEqual(packet.count(CODING_GUIDE_ROUTE), expected_count)
            self.assertNotIn("google.script.run", packet)
            self.assertNotIn("set -euo pipefail", packet)
            if stage in CODING_GUIDE_STAGES:
                action = dict(navigator.current_action(recovered))
                waiting = navigator.apply(recovered, action["id"], result(stage))
                pending, child_packet = self.cold_packet(waiting)
                self.assertEqual(child_packet.count(CODING_GUIDE_ROUTE), 1)
                self.assertIn("Current action: Improve the completed " + stage, child_packet)
                self.assertIn(action["id"], child_packet)
                self.assertEqual(navigator.current_stage(pending), stage)
                self.assertEqual(pending["active_improve"], waiting["active_improve"])
                # Bind only synthetic identity to test the separate bound-child
                # render path; no skill or model is executed by this fixture.
                child = pending["active_improve"]
                child.update({
                    "version": 1,
                    "contract_marker": "ShipLoop standalone Improve binding: " + child["binding_id"],
                    "skill": {
                        "skill_card": str(self.repo / "improve/SKILL.md"),
                        "runtime_card": str(self.repo / "until-loop/SKILL.md"),
                        "runtime_cli": str(self.repo / "until-loop/scripts/until-loop"),
                        "skill_version": "synthetic",
                        "runtime_version": "synthetic",
                    },
                })
                navigator.validate(pending)
                bound, bound_packet = self.cold_packet(pending)
                self.assertEqual(bound["active_improve"], pending["active_improve"])
                self.assertEqual(bound_packet.count(CODING_GUIDE_ROUTE), 1)
                self.assertIn("selected practice/platform locators", normalized(bound_packet))
                observed.append(stage)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state, _ = self.complete_stage(state, **extra)
        self.assertEqual(tuple(observed), CODING_GUIDE_STAGES)

    def test_coding_reference_links_survive_package_relocation(self) -> None:
        """A packaged selector and its cards must work outside this checkout."""
        relocated = (self.repo / "copied-package" / "references").resolve()
        shutil.copytree(REFERENCES, relocated)
        new_files = ["coding-guidance.md", "coding-practices.md"] + [
            "platforms/" + name + ".md"
            for name in ("ui", "apps-script", "salesforce", "python", "bash")
        ]
        selector = (relocated / "coding-guidance.md").read_text(encoding="utf-8")
        for card in new_files[1:]:
            self.assertIn(card, selector)
        for filename in new_files:
            page = relocated / filename
            body = page.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", body)
            self.assertNotIn("shiploop-coding-guidance-experiment-plan", body)
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
                if link.startswith(("https://", "http://")):
                    continue
                with self.subTest(page=filename, link=link):
                    path, _, anchor = link.partition("#")
                    destination = (page.parent / path).resolve() if path else page
                    self.assertTrue(destination.is_relative_to(relocated), link)
                    self.assertTrue(destination.is_file(), link)
                    if anchor:
                        headings = {
                            heading_anchor(match.group(2)) for match in re.finditer(
                                r"(?m)^(#{1,6})\s+(.+?)\s*$",
                                destination.read_text(encoding="utf-8"),
                            )
                        }
                        self.assertIn(anchor, headings)

    def test_accepted_coding_plan_can_survive_later_test_decisions_without_new_fields(self) -> None:
        """Exercise host-authored evidence handoff, not automatic model compliance."""
        state = self.state()
        plan_ref = "docs/item-plan.md#accepted-decisions"
        card_ref = str(REFERENCES / "platforms/python.md")
        plan_action = ""
        latest_decision = ""
        while navigator.current_stage(state) != "implement":
            stage = navigator.current_stage(state)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic Python change"}]
            if stage == "step-plan":
                extra["evidence_refs"] = ["draft://not-accepted"]
                state, plan_action = self.complete_stage_with_final(
                    state, result(stage, evidence_refs=[plan_ref, card_ref]), **extra
                )
            else:
                if stage in {"test-spec", "test-author"}:
                    # A host follows the handoff instruction using ordinary fields.
                    extra["summary"] = "Retain accepted decisions; refine only test cases."
                    extra["evidence_refs"] = [plan_ref, card_ref, "tests/cases.py"]
                state, action_id = self.complete_stage(state, **extra)
                if stage in {"test-spec", "test-author"}:
                    latest_decision = action_id
            state = self.save_reload(state)
        _, packet = self.cold_packet(state)
        self.assertIn("Current item test-decision source action: " + latest_decision, packet)
        self.assertIn(plan_ref, packet)
        self.assertIn(card_ref, packet)
        self.assertNotIn("draft://not-accepted", packet)
        self.assertEqual(state["accepted"][plan_action]["evidence_refs"], [plan_ref, card_ref])

    def test_next_item_reopens_repo_index_without_inheriting_prior_skill_selection(self) -> None:
        """The generic item context keeps selections scoped to their owner.

        This is synthetic navigation and packet recovery.  It deliberately does
        not parse the index or a product skill: the host still decides whether a
        current task fits either one.
        """
        index = self.repo / "SHIPLOOP.md"
        selected_card = self.repo / "skills/release-evidence-triage/SKILL.md"
        index_ref = str(index) + "#local-skills"
        w1_selection = (
            "W1 selected local skill: " + str(selected_card)
            + "; effective input contract: docs/release-contract.md#v1; "
            + "revalidate when the contract moves."
        )
        w2_context = (
            "W2 start by reopening the current repository index " + index_ref
            + "; no prior skill selection applies until task fit is reassessed."
        )
        index.write_text(
            "# Fixture repository index\n\n## Local skills\n\n"
            "- [Release evidence](skills/release-evidence-triage/SKILL.md)\n",
            encoding="utf-8",
        )
        selected_card.parent.mkdir(parents=True)
        selected_card.write_text("# Fixture local skill\n", encoding="utf-8")
        state = self.state()
        while navigator.current_stage(state) != "plan":
            state, _action_id = self.complete_stage(state)
        state, plan_action = self.complete_stage(
            state,
            evidence_refs=[index_ref],
            work_items=[
                {"id": "W1", "title": "Assess release evidence", "context": w1_selection},
                {"id": "W2", "title": "Reassess another boundary", "context": w2_context},
            ],
        )
        state = self.save_reload(state)
        self.assertEqual(state["accepted"][plan_action]["evidence_refs"], [index_ref])

        while navigator.current_stage(state) != "step-plan":
            state, _action_id = self.complete_stage(state)
            state = self.save_reload(state)
        first_item, first_packet = self.cold_packet(state)
        self.assertEqual(navigator._current_work_item(first_item), "W1")
        self.assertIn("Work item context: " + w1_selection, first_packet)
        self.assertIn("Repository knowledge index (host-authored, if present): " + str(index), first_packet)

        while not (
            navigator.current_stage(state) == "step-plan"
            and navigator._current_work_item(state) == "W2"
        ):
            state, _action_id = self.complete_stage(state)
            state = self.save_reload(state)
        second_item, second_packet = self.cold_packet(state)
        self.assertEqual(navigator._current_work_item(second_item), "W2")
        self.assertIn("Work item context: " + w2_context, second_packet)
        self.assertIn("Repository knowledge index (host-authored, if present): " + str(index), second_packet)
        self.assertNotIn(str(selected_card), second_packet)
        self.assertNotIn(w1_selection, second_packet)

    def test_ui_ownership_and_failed_readiness_survive_planning_review(self) -> None:
        """Synthetic host judgments test routing and blocking, not model quality."""
        locator = str(REFERENCES / "behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner")
        docs = self.repo / "docs"
        docs.mkdir()
        design = docs / "ui.md"
        design.write_text("# UI premises\n\nPreserve components, draft interaction and navy tokens.\n")
        readiness = docs / "readiness.md"
        readiness.write_text("# Current target\n\nStorage unavailable. Host owner must resolve it before draft work.\n")
        sources = [str(design) + "#ui-premises", str(readiness) + "#current-target"]
        context = "Draft item depends on host-owned storage readiness; " + "; ".join(sources)
        state = self.state()
        observed = []
        while navigator.current_stage(state) != "step-plan":
            stage = navigator.current_stage(state)
            if stage in {"discovery", "plan", "prepare"}:
                state, packet = self.cold_packet(state)
                self.assertIn(locator, packet)
                observed.append(stage)
            extra = {}
            if stage == "plan":
                extra = {"evidence_refs": sources,
                         "work_items": [{"id": "W1", "title": "Recover drafts", "context": context}]}
            state, _ = self.complete_stage(state, **extra)
        state, packet = self.cold_packet(state)
        self.assertEqual(observed, ["discovery", "plan", "prepare"])
        self.assertIn(locator, packet)
        self.assertIn(context, packet)
        action = dict(navigator.current_action(state))
        blocked = {"outcome": "blocked", "summary": "Host storage prerequisite is unavailable; supplier decision pending.",
                   "evidence_refs": sources}
        waiting = navigator.apply(state, action["id"], blocked)
        waiting, review_packet = self.cold_packet(waiting)
        self.assertEqual(waiting["active_improve"]["seed_result"], blocked)
        for source in sources:
            self.assertIn(source, review_packet)
        # The host's actual review is replaced only for this structural fixture.
        stopped = navigator.finish_improve(waiting, action["id"], receipt("step-plan"))
        stopped, stopped_packet = self.cold_packet(stopped)
        self.assertEqual(stopped["status"], "blocked")
        self.assertEqual(navigator.current_stage(stopped), "step-plan")
        self.assertNotIn("W1", stopped["completed_work_items"])
        self.assertIn("Host storage prerequisite", stopped_packet)

    def test_ui_supersession_handoff_keeps_replacement_current_after_cold_recovery(self) -> None:
        """A reviewed plan can replace a UI premise without erasing its seed evidence."""
        original_locator = "docs/ui-plan.md#original-premise"
        replacement_locator = "docs/ui-review.md#accepted-replacement"
        original_context = (
            "Original UI premise: use the original storage order from " + original_locator
        )
        replacement_context = (
            "Reviewed replacement: " + replacement_locator
            + "; precedence: this reviewed replacement supersedes the original storage order."
        )
        state = self.state()
        while navigator.current_stage(state) != "plan":
            state, _ = self.complete_stage(state)

        action = dict(navigator.current_action(state))
        waiting = navigator.apply(
            state,
            action["id"],
            result(
                "plan",
                evidence_refs=[original_locator],
                work_items=[{"id": "W1", "title": "Recover drafts", "context": original_context}],
            ),
        )
        waiting, _review_packet = self.cold_packet(waiting)
        final_plan = result(
            "plan",
            summary="Improve accepted a reviewed UI replacement with explicit precedence.",
            evidence_refs=[replacement_locator],
            work_items=[{"id": "W1", "title": "Recover drafts", "context": replacement_context}],
        )
        state = navigator.finish_improve(waiting, action["id"], receipt("plan"), final_plan)
        self.assertEqual(
            state["improve_results"][action["id"]]["seed_result"]["evidence_refs"],
            [original_locator],
        )
        self.assertEqual(state["accepted"][action["id"]]["evidence_refs"], [replacement_locator])
        self.assertEqual(
            state["improve_results"][action["id"]]["seed_result"]["work_items"][0]["context"],
            original_context,
        )

        state, replacement_packet = self.cold_packet(state)
        self.assertIn(replacement_locator, replacement_packet)
        self.assertIn("reviewed UI replacement with explicit precedence", replacement_packet)
        self.assertNotIn(original_locator, replacement_packet)
        state, _ = self.complete_stage(state)
        self.assertEqual(navigator.current_stage(state), "select-work")
        state, _ = self.complete_stage(state)
        state, cold_packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "step-plan")
        self.assertIn("Work item context: " + replacement_context, cold_packet)
        self.assertIn(replacement_locator, cold_packet)
        self.assertNotIn(original_context, cold_packet)
        self.assertIn(
            "Carry reviewed replacement locators and their precedence through the existing handoff when these decisions change.",
            normalized(prompts.improve_prompt("step-plan")),
        )

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

    def test_reusable_test_facilities_route_and_recover_without_new_state(self) -> None:
        """Facility locators are ordinary cold-context records, never execution proof."""
        guide = (REFERENCES / "repeatable-test-suites.md").read_text(encoding="utf-8")
        guide_normalized = normalized(guide)
        for clause in (
            "reuse and define test facilities",
            "selected skill and MCP capability references",
            "reuse, configure or extend",
            "missing facility",
            "definition locator",
            "before dependent checks",
            "repository test documentation",
            "repository index",
        ):
            self.assertIn(clause.lower(), guide_normalized.lower())

        for stage in prompts.STAGES:
            routed = ("Reusable test facilities", "repeatable-test-suites.md#reuse-and-define-test-facilities") in prompts.STAGE_REFERENCES[stage]
            self.assertEqual(routed, stage in TEST_FACILITY_STAGES, stage)
        self.assertIsInstance(prompts.TEST_FACILITY_HANDOFF, str)
        facility_handoff = normalized(prompts.TEST_FACILITY_HANDOFF)
        for clause in (
            "selected skill and MCP capability references",
            "reuse, configure or extend",
            "missing facility",
            "definition locator",
            "Discovery or readiness is not test execution",
            "expected check state",
        ):
            self.assertIn(clause, facility_handoff)
        for stage in TEST_FACILITY_STAGES:
            self.assertIn(prompts.TEST_FACILITY_HANDOFF, prompts.prompt(stage))
            self.assertIn(prompts.TEST_FACILITY_HANDOFF, prompts.improve_prompt(stage))
        self.assertIn(
            "A missing test facility is a prerequisite gap, not meaningful RED.",
            normalized(prompts.prompt("test-red")),
        )
        self.assertIn(
            "Revalidate retained facility definitions and readiness for this regression target",
            normalized(prompts.prompt("regression")),
        )

        skill_ref = "docs/testing.md#local-framework-skill-v2"
        mcp_ref = "docs/testing.md#required-mcp-operation-missing-helper"
        context = (
            "Facility: local framework skill via " + skill_ref
            + "; required MCP helper is planned, readiness unresolved; revalidate version."
        )
        state = self.state()
        strategy_action = ""
        plan_action = ""
        author_action = ""
        while navigator.current_stage(state) != "test-author":
            stage = navigator.current_stage(state)
            extra: dict[str, object] = {"evidence_refs": ["synthetic://" + stage]}
            if stage == "test-strategy":
                extra["evidence_refs"] = [skill_ref, mcp_ref]
            elif stage == "plan":
                extra.update({
                    "evidence_refs": [skill_ref, mcp_ref],
                    "work_items": [{"id": "W1", "title": "Facility item", "context": context}],
                })
            state, action = self.complete_stage(state, **extra)
            if stage == "test-strategy":
                strategy_action = action
            if stage == "plan":
                plan_action = action
        state, author_packet = self.cold_packet(state)
        self.assertIn(REUSABLE_TEST_FACILITY_ROUTE, author_packet)
        action = dict(navigator.current_action(state))
        waiting = navigator.apply(
            state, action["id"],
            result(
                "test-author",
                summary="Required MCP helper remains planned; readiness is not test execution.",
                evidence_refs=[skill_ref, mcp_ref],
            ),
        )
        state = navigator.finish_improve(waiting, action["id"], receipt("test-author"))
        author_action = action["id"]
        state, packet = self.cold_packet(state)
        packet = normalized(packet)
        self.assertIn(skill_ref, packet)
        self.assertIn(mcp_ref, packet)
        self.assertIn("Work item context: " + context, packet)
        self.assertIn("Run-wide test strategy source action: " + strategy_action, packet)
        self.assertIn("Current item test-decision source action: " + author_action, packet)
        self.assertIn("Required MCP helper remains planned; readiness is not test execution.", packet)
        for action in (strategy_action, plan_action, author_action):
            self.assertIn(action, state["accepted"])
        self.assertEqual(set(state).intersection({"test_facilities", "facility_definitions"}), set())
        self.assertIn("untrusted locators; not read by the navigator", packet)
        self.assertEqual(
            state["accepted"][author_action]["summary"],
            "Required MCP helper remains planned; readiness is not test execution.",
        )

    def test_outer_test_handshake_recovers_replan_aware_sources_cold(self) -> None:
        """The packet routes existing records; it does not certify their contents."""
        label = "OUTER test-planning handshake"
        locator = "repeatable-test-suites.md#outer-test-planning-handshake"
        outer_sources = (
            "latest done system-test-author and release-plan records",
            "most recent accepted replan",
            "pending, repeat, and blocked results are not plan authority",
        )

        # The shared contract must reach each root-owned OUTER producer and its
        # standalone Improve handoff without adding a Navigator state field.
        self.assertIsInstance(prompts.OUTER_TEST_HANDOFF, str)
        system_author = normalized(prompts.prompt("system-test-author"))
        for clause in (
            "latest done test-decision record for every relevant completed item",
            "Do not infer whole-product coverage from the last transition",
            "current candidate/boundaries, selected cases and oracles",
            "required post-release checks stay assigned to release-verify",
        ):
            self.assertIn(clause, system_author)
        release_plan = normalized(prompts.prompt("release-plan"))
        for clause in (
            "Revalidate the integrated test plan for the release target",
            "pre/post check owners, commands/case selectors",
            "execution versus target locations, remote test-definition revision",
        ):
            self.assertIn(clause, release_plan)
        system_test = normalized(prompts.prompt("system-test"))
        self.assertIn("acknowledge the applicable integrated test plan", system_test)
        self.assertIn("remote framework availability", system_test)
        for stage in prompts.OUTER:
            with self.subTest(stage=stage):
                self.assertIn((label, locator), prompts.STAGE_REFERENCES[stage])
                packet = normalized(prompts.prompt(stage))
                improve_packet = normalized(prompts.improve_prompt(stage))
                for source in outer_sources:
                    self.assertIn(source, packet)
                    self.assertIn(source, improve_packet)

        strategy_ref = "docs/testing.md#strategy"
        decisions = {
            "W1": "docs/testing.md#w1-refined",
            "W2": "docs/testing.md#w2-regression",
            "W3": "docs/testing.md#w3-corrective",
        }
        state = self.state()
        decision_actions: dict[str, str] = {}
        while navigator.current_stage(state) != "plan":
            stage = navigator.current_stage(state)
            state, _action = self.complete_stage(
                state,
                evidence_refs=[strategy_ref if stage == "test-strategy" else "unrelated://" + stage],
            )
        state, _plan = self.complete_stage(
            state,
            evidence_refs=["docs/plan.md#items"],
            work_items=[
                {"id": "W1", "title": "First boundary", "context": "W1 isolated fixture."},
                {"id": "W2", "title": "Second boundary", "context": "W2 compatibility fixture."},
            ],
        )
        state = self.save_reload(state)

        # Complete W1/W2 while retaining their latest local test-decision action.
        while navigator.current_stage(state) != "system-test-author":
            stage = navigator.current_stage(state)
            owner = navigator._current_work_item(state)
            refs = ["unrelated://" + stage]
            if owner in decisions and stage == "regression":
                refs = [decisions[owner]]
            state, action = self.complete_stage(state, evidence_refs=refs)
            state = self.save_reload(state)
            if owner in decisions and stage == "regression":
                decision_actions[owner] = action

        state, packet = self.cold_packet(state)
        packet = normalized(packet)
        self.assertIn(label + ": " + str(REFERENCES / locator), packet)
        self.assertIn("latest done system-test-author and release-plan records", packet)
        # Neither current-item context nor an item-local projection leaks into
        # root-owned outer planning. The handshake directs a bounded history lookup.
        self.assertNotIn("W1 isolated fixture.", packet)
        self.assertNotIn("W2 compatibility fixture.", packet)
        for action in decision_actions.values():
            self.assertTrue((self.run / "results" / (action + ".md")).is_file())
            self.assertIn(action, state["accepted"])

        state, system_author_action = self.complete_stage(
            state, evidence_refs=["docs/testing.md#integrated-system-plan"]
        )
        state = self.save_reload(state)
        state, _system_test_action = self.complete_stage(
            state, evidence_refs=["docs/testing.md#system-execution"]
        )
        state = self.save_reload(state)
        state, _acceptance_action = self.complete_stage(
            state, evidence_refs=["docs/testing.md#acceptance"]
        )
        state = self.save_reload(state)
        release_plan_action = dict(navigator.current_action(state))["id"]
        release_plan_draft = "untrusted://release-plan-pending-draft"
        waiting = navigator.apply(
            state,
            release_plan_action,
            result("release-plan", evidence_refs=[release_plan_draft]),
        )
        navigator.save(self.run, waiting)
        pending = store.read_record(self.run / "state.md")
        selected_skill = standalone_improve.resolve_skill(str(IMPROVE_CARD))
        bound_pending = dict(pending)
        bound_pending["active_improve"] = standalone_improve.binding(
            pending,
            release_plan_action,
            "release-plan",
            pending["active_improve"]["seed_result"],
            selected_skill,
        )
        navigator.save(self.run, bound_pending)
        pending = store.read_record(self.run / "state.md")
        pending_bytes = (self.run / "state.md").read_bytes()
        pending_packet = normalized(navigator.render(None, self.run, pending))
        self.assertEqual((self.run / "state.md").read_bytes(), pending_bytes)
        self.assertEqual(pending["active_improve"]["action_id"], release_plan_action)
        self.assertEqual(
            pending["active_improve"]["seed_result"]["evidence_refs"],
            [release_plan_draft],
        )
        self.assertNotIn(release_plan_action, pending["accepted"])
        self.assertFalse(any(entry["action"] == release_plan_action for entry in pending["history"]))
        self.assertIn("Parent step remains pending until actual Improve completion is imported.", pending_packet)
        self.assertIn(label + ": " + str(REFERENCES / locator), pending_packet)
        self.assertIn("latest done system-test-author and release-plan records", pending_packet)
        self.assertIn(system_author_action, pending["accepted"])

        release_plan_final = "docs/release.md#revalidated-target-and-checks"
        state = navigator.finish_improve(
            pending,
            release_plan_action,
            receipt("release-plan"),
            result("release-plan", evidence_refs=[release_plan_final]),
        )
        state = self.save_reload(state)
        self.assertEqual(state["accepted"][release_plan_action]["evidence_refs"], [release_plan_final])
        self.assertNotIn(release_plan_draft, state["accepted"][release_plan_action]["evidence_refs"])
        self.assertEqual(
            [entry for entry in state["history"] if entry["action"] == release_plan_action][0]["outcome"],
            "done",
        )
        self.assertEqual(navigator.current_stage(state), "release-check")

        # An outer corrective replan is accepted history, then returns through a
        # new INNER item. Its predecessor records remain durable, but are no
        # longer presented as current outer-plan authority.
        replan_result = result(
            "release-check",
            outcome="replan",
            summary="A changed target needs a corrective compatibility item.",
            evidence_refs=["docs/release.md#replan-target-change"],
            work_items=[
                {"id": "W3", "title": "Correct target compatibility", "context": "W3 new target fixture."}
            ],
        )
        state, replan_action = self.complete_stage_with_final(
            state, replan_result, evidence_refs=["unrelated://release-check-draft"]
        )
        state = self.save_reload(state)
        self.assertEqual(navigator.current_stage(state), "select-work")
        self.assertEqual(navigator._current_work_item(state), "W3")

        while navigator.current_stage(state) != "system-test-author":
            stage = navigator.current_stage(state)
            owner = navigator._current_work_item(state)
            refs = ["unrelated://" + stage]
            if owner == "W3" and stage == "regression":
                refs = [decisions["W3"]]
            state, action = self.complete_stage(state, evidence_refs=refs)
            state = self.save_reload(state)
            if owner == "W3" and stage == "regression":
                decision_actions["W3"] = action

        state, packet = self.cold_packet(state)
        packet = normalized(packet)
        self.assertIn(label + ": " + str(REFERENCES / locator), packet)
        for source in outer_sources:
            self.assertIn(source, packet)
        self.assertNotIn("W3 new target fixture.", packet)
        self.assertIn(
            "If this action depends on earlier accepted context, read the durable state",
            packet,
        )
        # The original records remain immutable/reachable in accepted state and
        # result files, while the recovery instructions mark them historical.
        for action in (system_author_action, release_plan_action, replan_action):
            self.assertIn(action, state["accepted"])
            self.assertTrue((self.run / "results" / (action + ".md")).is_file())
        self.assertEqual(state["accepted"][replan_action]["outcome"], "replan")
        self.assertTrue(any(
            entry["action"] == replan_action and entry["outcome"] == "replan"
            for entry in state["history"]
        ))

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
