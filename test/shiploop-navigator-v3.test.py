#!/usr/bin/env python3
"""Protocol-v3 acceptance tests for ShipLoop-owned action/Improve handoff.

The expected graph is intentionally declared here instead of imported from the
navigator.  These are synthetic protocol tests: no child Improve runtime,
repository command, or project check is started.
"""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_navigator_v3_prompts as prompts  # noqa: E402
import shiploop_store as store  # noqa: E402


# This is the public v3 contract.  Never derive it from the implementation:
# otherwise a routing regression could silently change the test expectation.
EXPECTED_PRELUDE = (
    "intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare",
)
EXPECTED_INNER = (
    "select-work", "step-plan", "test-spec", "baseline", "test-author", "test-red",
    "implement", "test-green", "test-refine", "regression", "document", "skill-assess",
    "skill-validate", "static-checks", "verify", "integrate", "integration-verify",
    "carry-forward",
)
EXPECTED_OUTER = (
    "system-test-author", "system-test", "product-acceptance", "release-plan",
    "release-check", "release", "release-verify", "operations", "handoff",
)
EXPECTED_STAGES = EXPECTED_PRELUDE + EXPECTED_INNER + EXPECTED_OUTER


def result(*, outcome: str = "done", summary: str = "Synthetic producer result.", **extra):
    return {"outcome": outcome, "summary": summary, **extra}


def receipt(stage: str) -> dict:
    """Synthetic child completion accepted only by the pure v3 state API."""
    return {
        "summary": f"Synthetic Improve completion for {stage}.",
        "review_refs": [f"synthetic://review/{stage}"],
        "check_refs": [f"synthetic://check/{stage}"],
        "lessons": f"Keep the verified learning from {stage}.",
    }


class NavigatorV3Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-navigator-v3-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "project"
        self.repo.mkdir()

    def state(self) -> dict:
        return navigator.new_state(
            str(self.repo),
            "Build a small synthetic capability.",
            protocol_version=3,
            improve_skill="",
        )

    @staticmethod
    def _action(state: dict) -> dict:
        return dict(navigator.current_action(state))

    def _complete_improve(self, state: dict, action: dict, stage: str) -> dict:
        return navigator.finish_improve(state, action["id"], receipt(stage))

    def _produce(self, state: dict, stage: str, **extra) -> dict:
        self.assertEqual(navigator.current_stage(state), stage)
        action = self._action(state)
        after = navigator.apply(state, action["id"], result(**extra))
        self.assertEqual(navigator.current_stage(after), stage)
        self.assertEqual(after["active_improve"]["action_id"], action["id"])
        self.assertEqual(after["active_improve"]["stage"], stage)
        return self._complete_improve(after, action, stage)

    def _to_outer(self, state: dict) -> dict:
        while navigator.current_stage(state) not in EXPECTED_OUTER:
            stage = navigator.current_stage(state)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state = self._produce(state, stage, **extra)

            packet = navigator.render(None, self.repo / ".shiploop", state)
            self.assertIn(f"Keep the verified learning from {stage}.", packet)
            self.assertIn("Last accepted Improve lessons (untrusted observations", packet)
        return state

    def test_v3_declares_the_flat_sdlc_graph_independently(self) -> None:
        self.assertEqual(tuple(prompts.PRELUDE), EXPECTED_PRELUDE)
        self.assertEqual(tuple(prompts.INNER), EXPECTED_INNER)
        self.assertEqual(tuple(prompts.OUTER), EXPECTED_OUTER)
        self.assertEqual(len(EXPECTED_STAGES), 34)
        self.assertTrue(all(prompts.prompt(stage).strip() for stage in EXPECTED_STAGES))
        self.assertTrue(all(prompts.improve_prompt(stage).strip() for stage in EXPECTED_STAGES))

    def test_every_v3_stage_waits_for_one_actual_improve_completion(self) -> None:
        state = self.state()
        observed: list[str] = []
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            observed.append(stage)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state = self._produce(state, stage, **extra)

        self.assertEqual(tuple(observed), EXPECTED_STAGES)
        self.assertEqual(state["status"], "done")
        self.assertEqual(len(state["history"]), 34)
        self.assertIsNone(state["active_improve"])
        self.assertIn("<h2>Work item progress</h2>", navigator._render_report(state))

    def test_duplicate_or_conflicting_producer_callback_cannot_create_another_child(self) -> None:
        state = self.state()
        action = self._action(state)
        submitted = result(summary="Exact synthetic producer report.")
        waiting = navigator.apply(state, action["id"], submitted)
        duplicate = navigator.apply(waiting, action["id"], copy.deepcopy(submitted))
        self.assertEqual(duplicate, waiting)
        self.assertEqual(duplicate["active_improve"]["binding_id"], waiting["active_improve"]["binding_id"])
        with self.assertRaises(navigator.NavigatorError):
            navigator.apply(waiting, action["id"], result(summary="Conflicting producer report."))

    def test_incomplete_child_and_blocked_producer_do_not_advance_parent(self) -> None:
        state = self.state()
        action = self._action(state)
        waiting = navigator.apply(state, action["id"], result())
        binding = copy.deepcopy(waiting["active_improve"])
        paused = navigator.control(waiting, "pause", "Synthetic interruption.")
        self.assertEqual(paused["active_improve"], binding)
        resumed = navigator.control(paused, "resume", "Resume the saved child.")
        self.assertEqual(resumed["active_improve"], binding)
        self.assertEqual(navigator.current_stage(resumed), "intake")

        blocked_state = self.state()
        blocked_action = self._action(blocked_state)
        waiting_blocked = navigator.apply(
            blocked_state, blocked_action["id"],
            result(outcome="blocked", summary="Synthetic prerequisite missing."),
        )
        self.assertEqual(waiting_blocked["status"], "active")
        self.assertEqual(waiting_blocked["active_improve"]["action_id"], blocked_action["id"])
        blocked = navigator.finish_improve(
            waiting_blocked,
            blocked_action["id"],
            receipt("intake"),
            result(outcome="blocked", summary="Synthetic prerequisite missing."),
        )
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(navigator.current_stage(blocked), "intake")

    def test_cold_recovery_preserves_the_pending_child_binding_without_advancing(self) -> None:
        state = self.state()
        action = self._action(state)
        waiting = navigator.apply(state, action["id"], result())
        with tempfile.TemporaryDirectory(prefix="shiploop-v3-cold-") as temporary:
            root = Path(temporary)
            navigator.save(root, waiting)
            before = (root / "state.md").read_bytes()
            recovered = store.read_record(root / "state.md")
            navigator.validate(recovered)
            self.assertEqual(recovered, waiting)
            self.assertEqual((root / "state.md").read_bytes(), before)
            self.assertEqual(navigator.current_stage(recovered), "intake")
            self.assertEqual(recovered["active_improve"], waiting["active_improve"])

    def test_outer_replan_adds_corrective_work_without_rewinding_completed_work(self) -> None:
        state = self._to_outer(self.state())
        self.assertEqual(state["completed_work_items"], ["W1"])
        for completed_outer_stage in ("system-test-author", "system-test"):
            self.assertEqual(navigator.current_stage(state), completed_outer_stage)
            state = self._produce(state, completed_outer_stage)
        stage = navigator.current_stage(state)
        self.assertEqual(stage, "product-acceptance")
        action = self._action(state)
        waiting = navigator.apply(
            state,
            action["id"],
            result(
                outcome="replan",
                summary="A corrective capability is required.",
                work_items=[{"id": "W2", "title": "Corrective item"}],
            ),
        )
        self.assertEqual(navigator.current_stage(waiting), stage)
        self.assertEqual(waiting["active_improve"]["action_id"], action["id"])
        revised = navigator.finish_improve(waiting, action["id"], receipt(stage))
        self.assertEqual(revised["completed_work_items"], ["W1"])
        self.assertIn("W2", [item["id"] for item in revised["work_items"]])
        self.assertEqual(navigator.current_stage(revised), "select-work")
        self.assertNotEqual(navigator.current_stage(revised), stage)
        packet = navigator.render(None, self.repo.parent / "replan-progress", revised)
        self.assertIn("Outer stages: 0/9 accepted done.", packet)
        self.assertIn(
            "Outer stages pending: system-test-author, system-test, product-acceptance, "
            "release-plan, release-check, release, release-verify, operations, handoff",
            packet,
        )

    def test_malformed_bound_skill_fails_with_controlled_recovery_error(self) -> None:
        state = self.state()
        waiting = navigator.apply(state, self._action(state)["id"], result())
        child = waiting["active_improve"]
        child["version"] = 1
        child["contract_marker"] = "ShipLoop standalone Improve binding: " + child["binding_id"]
        child["skill"] = {}
        with self.assertRaisesRegex(navigator.NavigatorError, "Improve skill binding is invalid"):
            navigator.validate(waiting)
        with self.assertRaisesRegex(navigator.NavigatorError, "Improve skill binding is invalid"):
            navigator.render(None, self.repo / ".shiploop", waiting)

        child["skill"] = {
            "skill_card": "/skills/improve/SKILL.md", "runtime_card": "/runtime/SKILL.md",
            "runtime_cli": "relative/runtime", "skill_version": "unversioned",
            "runtime_version": "unversioned",
        }
        with self.assertRaisesRegex(navigator.NavigatorError, "paths must be absolute"):
            navigator.validate(waiting)


if __name__ == "__main__":
    unittest.main(verbosity=2)
