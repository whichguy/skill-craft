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


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
REFERENCES = SCRIPTS.parent / "references"
IMPROVE_CARD = ROOT / "skills" / "improve" / "SKILL.md"
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
