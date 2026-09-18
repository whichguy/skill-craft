#!/usr/bin/env python3
"""Focused v3 prompt, reference-routing, and cold-context guidance checks.

These tests verify the durable material supplied to a fresh agent. They do not
claim that an LLM interpreted a locator correctly or that Improve executed.
"""

from __future__ import annotations

from pathlib import Path
import re
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
