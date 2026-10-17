#!/usr/bin/env python3
"""Interaction-design guidance routing in cold navigator packets (protocol 3)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_packet_symbols as symbols  # noqa: E402
import shiploop_prompts as navigator_prompts  # noqa: E402
import shiploop_store as store  # noqa: E402
from shiploop_improve_route import with_route  # noqa: E402


class InteractionGuidanceTests(unittest.TestCase):
    """Focused contracts for the shared interaction-design guidance locator."""

    ANCHOR = "actors-channels-and-state-ownership"

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="shiploop-interaction-guide-")
        self.root = Path(self.tmp.name)
        self.repo = self.root / "project"
        self.repo.mkdir()
        self.guide = (
            ROOT / "skills" / "shiploop" / "references" / "behavioral-requirements.md"
        ).resolve()
        self.locator = f"Interaction design guide: {self.guide}#{self.ANCHOR}"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def navigator_state(self) -> dict:
        return navigator.new_state(
            str(self.repo),
            "Assess the requested interaction boundary.",
            str(self.root / "bound-plan.md"),
            improve_skill="",
        )

    def spec_state(self) -> dict:
        """Reach spec, the first Improve checkpoint, through direct producer returns."""
        state = self.navigator_state()
        for stage in ("intake", "discovery", "research"):
            self.assertEqual(navigator.current_stage(state), stage)
            action = dict(navigator.current_action(state))
            state = navigator.apply(
                state,
                action["id"],
                {"outcome": "done", "summary": f"Synthetic producer result for {stage}."},
            )
            self.assertIsNone(state["active_improve"])
        self.assertEqual(navigator.current_stage(state), "spec")
        return state

    def bind_synthetic_v3_child(self, state: dict) -> dict:
        """Use the established synthetic binding fixture without running Improve."""
        child = state["active_improve"]
        self.assertIsNotNone(child)
        child.update(
            {
                "version": 1,
                "contract_marker": (
                    "ShipLoop standalone Improve binding: " + child["binding_id"]
                ),
                "skill": {
                    "skill_card": str(
                        (self.repo / "selected-improve" / "SKILL.md").resolve()
                    ),
                    "runtime_card": str(
                        (self.repo / "until-loop" / "ADAPTER.md").resolve()
                    ),
                    "runtime_cli": str(
                        (
                            self.repo / "until-loop" / "scripts" / "until_loop_ephemeral.py"
                        ).resolve()
                    ),
                    "skill_version": "synthetic",
                    "runtime_version": "synthetic",
                },
            }
        )
        navigator.validate(state)
        return state

    def assert_cold_packet_keeps_locator_and_cursor(
        self, state: dict, *, label: str
    ) -> str:
        run_root = self.root / label
        run_root.mkdir()
        navigator.save(run_root, state)
        before_bytes = (run_root / "state.md").read_bytes()
        recovered = store.read_record(run_root / "state.md")
        before_state = deepcopy(recovered)
        before_action = dict(navigator.current_action(recovered))

        packet = symbols.guides_expanded(navigator.render(None, run_root, recovered))   # GUIDES/<file> as an absolute path
        if recovered.get("active_improve"):
            # The Improve packet is two instructions; the guidance rides in the handoff file it names (re-cut R3).
            packet += "\n" + symbols.guides_expanded(navigator.improve_handoff_text(None, run_root, recovered))

        # A packet prints a policy locator only when its stage text names that guide; every other packet points to
        # reference.md#policies, which lists the same locator (2026-10-11 dedupe).
        if self.locator not in packet:
            self.assertIn("reference.md (#policies", packet)
            self.assertIn(self.locator, (run_root / "reference.md").read_text(encoding="utf-8"))
        self.assertEqual(recovered, before_state)
        self.assertEqual(dict(navigator.current_action(recovered)), before_action)
        self.assertEqual((run_root / "state.md").read_bytes(), before_bytes)
        return packet

    def test_interaction_design_guide_has_canonical_heading(self) -> None:
        self.assertTrue(self.guide.is_absolute())
        self.assertTrue(self.guide.is_file())
        self.assertIn(
            "## Actors, channels, and state ownership",
            self.guide.read_text(encoding="utf-8"),
        )

    def test_cold_navigator_packets_keep_interaction_guide_without_cursor_mutation(
        self,
    ) -> None:
        self.assert_cold_packet_keeps_locator_and_cursor(
            self.navigator_state(), label="producer-v3"
        )

        child_state = self.spec_state()
        child_action = dict(navigator.current_action(child_state))
        waiting = navigator.apply(
            child_state,
            child_action["id"],
            {"outcome": "done", "summary": "Synthetic producer result."},
        )
        self.assertIsNotNone(waiting["active_improve"])
        self.assert_cold_packet_keeps_locator_and_cursor(
            waiting, label="pending-v3-improve-child"
        )

    def test_cold_bound_v3_child_keeps_interaction_guidance_without_running_improve(
        self,
    ) -> None:
        """A schema-valid synthetic child binding covers rendering, not execution."""
        state = self.spec_state()
        action = dict(navigator.current_action(state))
        waiting = navigator.apply(
            state,
            action["id"],
            {"outcome": "done", "summary": "Synthetic producer result."},
        )
        packet = self.assert_cold_packet_keeps_locator_and_cursor(
            self.bind_synthetic_v3_child(waiting),
            label="bound-v3-improve-child",
        )

        self.assertIn(self.locator, symbols.guides_expanded(packet))
        self.assertIn("Selected Improve skill:", packet)
        for term in (
            "actor interactions",
            "channels",
            "state ownership",
            "Carry those locators into the child contract",
        ):
            self.assertIn(term, with_route(packet))   # the review inputs moved to the Improve route file (plan U18)

    def test_prompt_catalogs_direct_relevant_work_to_interaction_design(self) -> None:
        shared_terms = (
            "interaction design guide",
            "discovery",
            "spec development",
            "global planning",
            "step planning",
            "actors",
            "channels",
            "state ownership",
        )
        normalized = " ".join(navigator_prompts.INTERACTION_DESIGN.split()).lower()
        for term in shared_terms:
            self.assertIn(term, normalized)
        # Stages that do not plan interactions do not carry the paragraph.
        for stage in ("test", "release", "operations"):
            self.assertNotIn("Interaction design guide and its", navigator_prompts.prompt(stage))

        for stage in ("discovery", "spec", "plan", "step-plan"):
            self.assertIn("Interaction design guide", navigator_prompts.prompt(stage))
            improve = navigator_prompts.improve_prompt(stage)
            for term in ("actor interactions", "channels", "state ownership"):
                self.assertIn(term, improve)

    def test_interaction_guide_has_canonical_shared_and_ui_subsections(self) -> None:
        """The specialized guidance remains nested under the shared interaction anchor."""
        text = self.guide.read_text(encoding="utf-8")
        anchor = text.index("## Actors, channels, and state ownership")
        next_peer_heading = text.index("\n## Behavior model", anchor)
        headings = (
            "Incoming events, connections, and state agreement",
            "UI-specific planning",
            "Review, evidence, and reuse",
        )
        positions = []
        for heading in headings:
            with self.subTest(heading=heading):
                position = text.find("\n### " + heading + "\n", anchor)
                self.assertNotEqual(position, -1)
                self.assertLess(anchor, position)
                self.assertLess(position, next_peer_heading)
                positions.append(position)
        self.assertEqual(positions, sorted(positions))

    def test_v3_step_plan_and_improve_cue_shared_and_ui_interactions(self) -> None:
        """Routing cues name the applicable concerns without testing design quality."""
        producer = navigator_prompts.prompt("step-plan").lower()
        improve = navigator_prompts.improve_prompt("step-plan").lower()
        # The improve prompt still names the guide's subsections.  The producer's duty (item 7, 2026-10-11 dedupe)
        # routes to them as "the interaction design guide's matching subsections" and lists the Design basis fields.
        for cue in (
            "incoming/outgoing events",
            "connection lifecycle",
            "baseline/delta",
            "ui-specific planning",
        ):
            with self.subTest(prompt="improve", cue=cue):
                self.assertIn(cue, improve)
        producer_flat = " ".join(producer.split())
        for cue in (
            "interaction design guide's matching subsections",
            "give baseline and delta",
            "actors, events, connections and state owner",
            "planned recovery checks",
            "design guidance identity and version or digest (or named fallback)",
            "evidence_refs",
        ):
            with self.subTest(prompt="producer", cue=cue):
                self.assertIn(cue, producer_flat)

    def test_v3_planning_stages_keep_design_basis_records_stage_local(self) -> None:
        """Require record-routing cues, not an LLM judgment about their substance."""
        # Packet re-cut (2026-10-11): plan's duty 8 writes the Design basis in `summary` and puts the per-item
        # locators in `context` and `evidence_refs`.
        required_cues = (
            "write a Design basis in `summary`",
            (
                "UI: component, interaction and skin premises, the design guidance locator with identity, "
                "version or digest (or the named fallback)"
            ),
            "evidence_refs",
        )
        # step-plan's duty (item 7, 2026-10-11 dedupe) states the Design basis paragraph in its own words.
        step_plan_cues = (
            "a Design basis paragraph",
            "rechecking the Interaction design guide's matching subsections",
            "Give baseline and delta;",
            "actors, events, connections and state owner;",
            "planned recovery checks;",
            "design guidance identity and version or digest (or named fallback)",
            "locators of sources and checks",
            "evidence_refs",
        )
        for stage, cues in (("plan", required_cues), ("step-plan", step_plan_cues)):
            with self.subTest(stage=stage):
                prompt = " ".join(navigator_prompts.prompt(stage).split())
                for cue in cues:
                    self.assertIn(cue, prompt)
        # The plan keeps its design basis as ordinary notes.  step-plan now records expectations, check commands
        # and step skills as result fields of its own (8-stage inner loop, 2026-10-10), so the cue is plan's alone.
        # The re-cut states the record's home outright ("in `summary`"), which replaces the old "ordinary notes" line.
        self.assertIn("write a Design basis in `summary`", " ".join(navigator_prompts.prompt("plan").split()))

        implementation_prompt = " ".join(
            navigator_prompts.prompt("implement").split()
        )
        self.assertNotIn(required_cues[0], implementation_prompt)

    @staticmethod
    def _synthetic_improve_record(stage: str) -> dict:
        """A state-machine fixture only; it makes no review-quality claim."""
        return {
            "summary": f"Synthetic Improve completion for {stage}; no runtime executed.",
            "review_refs": [],
            "check_refs": [],
            "lessons": f"Synthetic routing fixture for {stage}.",
        }

    def _finish_synthetic_v3_step(self, state: dict, **extra: object) -> dict:
        """Advance one v3 producer through the pure, explicitly synthetic return."""
        stage = navigator.current_stage(state)
        action = dict(navigator.current_action(state))
        waiting = navigator.apply(
            state,
            action["id"],
            {
                "outcome": "done",
                "summary": f"Synthetic producer result for {stage}.",
                **extra,
            },
        )
        if waiting["active_improve"] is None:
            # Not an Improve checkpoint: the producer result advanced directly.
            return waiting
        return navigator.finish_improve(
            waiting, action["id"], self._synthetic_improve_record(stage)
        )

    def _v3_step_plan_state(self, work_item: dict[str, str]) -> dict:
        """Reach a real v3 step-plan cursor through its regular producer returns."""
        state = self.navigator_state()
        for stage in ("intake", "discovery", "research", "spec", "test-strategy"):
            self.assertEqual(navigator.current_stage(state), stage)
            state = self._finish_synthetic_v3_step(state)

        self.assertEqual(navigator.current_stage(state), "plan")
        state = self._finish_synthetic_v3_step(state, work_items=[work_item])
        self.assertEqual(navigator.current_stage(state), "prepare")
        state = self._finish_synthetic_v3_step(state)

        self.assertEqual(navigator.current_stage(state), "step-plan")
        return state

    def test_cold_v3_step_plan_and_improve_preserve_ui_and_headless_context(
        self,
    ) -> None:
        """Synthetic receipt routing preserves locators and summaries, not their merit."""
        cases = (
            {
                "id": "UI1",
                "title": "Surface export completion in the existing interface",
                "source": "docs/ui-notifications.md#export-complete",
                "decision": (
                    "UI decision summary: reuse the existing notification component; "
                    "respect reduced motion and show recovered completion once."
                ),
                "design_basis": (
                    "Design guidance: skills/frontend-design/SKILL.md; "
                    "version fixture-v1; digest sha256:0123456789abcdef."
                ),
            },
            {
                "id": "EV1",
                "title": "Accept report-complete events without a user surface",
                "source": "docs/events.md#report-complete",
                "decision": (
                    "Headless decision summary: deduplicate event IDs, retain accepted "
                    "state, and recover the subscription cursor after reconnect."
                ),
            },
        )
        for case in cases:
            with self.subTest(work_item=case["id"]):
                work_item = {
                    "id": case["id"],
                    "title": case["title"],
                    "context": "\n".join(
                        value
                        for value in (
                            case["source"],
                            case["decision"],
                            case.get("design_basis"),
                        )
                        if value
                    ),
                }
                state = self._v3_step_plan_state(work_item)
                run_root = self.root / ("cold-" + case["id"])
                run_root.mkdir()

                navigator.save(run_root, state)
                producer_bytes = (run_root / "state.md").read_bytes()
                recovered = store.read_record(run_root / "state.md")
                self.assertEqual(recovered, state)
                producer_packet = navigator.render(None, run_root, recovered)
                self.assertEqual((run_root / "state.md").read_bytes(), producer_bytes)

                action = dict(navigator.current_action(recovered))
                waiting = navigator.apply(
                    recovered,
                    action["id"],
                    {
                        "outcome": "done",
                        "summary": "Synthetic step-plan decision: " + case["decision"],
                        "evidence_refs": [case["source"]],
                    },
                )
                navigator.save(run_root, waiting)
                pending_bytes = (run_root / "state.md").read_bytes()
                pending = store.read_record(run_root / "state.md")
                pending_packet = navigator.render(None, run_root, pending)
                self.assertEqual((run_root / "state.md").read_bytes(), pending_bytes)

                # Read before binding: bind_synthetic_v3_child updates the child in place.
                pending_handoff = navigator.improve_handoff_text(None, run_root, pending)
                bound = self.bind_synthetic_v3_child(pending)
                navigator.save(run_root, bound)
                bound_bytes = (run_root / "state.md").read_bytes()
                recovered_bound = store.read_record(run_root / "state.md")
                bound_packet = navigator.render(None, run_root, recovered_bound)
                self.assertEqual((run_root / "state.md").read_bytes(), bound_bytes)

                self.assertEqual(navigator.current_stage(recovered_bound), "step-plan")
                self.assertEqual(
                    recovered_bound["active_improve"]["action_id"], action["id"]
                )
                # The Improve packet is two instructions (re-cut R3); everything else the child needs, including
                # the producer's result (summary and evidence_refs), is in the handoff file the packet names.
                bound_handoff = navigator.improve_handoff_text(None, run_root, recovered_bound)
                self.assertIn("Interaction design guide", producer_packet)
                for packet in (producer_packet, pending_packet + pending_handoff, bound_packet + bound_handoff):
                    self.assertIn(self.locator, symbols.guides_expanded(packet))
                    self.assertIn(case["source"], packet)
                    self.assertIn(case["decision"], packet)
                if case.get("design_basis"):
                    self.assertIn(case["design_basis"], producer_packet)
                self.assertIn("/improve ShipLoop Improve: " + str(navigator.improve_handoff_path(recovered_bound["active_improve"])),
                              bound_packet)
                improve_id = recovered_bound["active_improve"]["improve_action"]
                self.assertIn("complete --run-dir=" + str(run_root) + " --action=" + improve_id, bound_packet)
                self.assertNotIn("improve-complete", bound_packet)
                self.assertIn("improve-bind", pending_packet)
                self.assertIn("The reviewed result stays pending until this Improve stage's complete imports the review", pending_handoff)
                self.assertIn("Load the actual Improve skill selected by this host.", pending_handoff)
                self.assertIn("Selected Improve skill:", bound_handoff)
                self.assertIn("Invoke the selected actual Improve skill for", bound_handoff)


if __name__ == "__main__":
    unittest.main()
