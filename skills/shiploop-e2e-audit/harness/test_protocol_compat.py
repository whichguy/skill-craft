"""Protocol-2/3 observer compatibility checks; no model or ShipLoop invocation."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import run  # noqa: E402


class ProtocolCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-e2e-protocol-compat-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "product"
        self.repo.mkdir()
        self.run_dir = self.root / "runs" / "run"
        self.run_dir.mkdir(parents=True)
        self.prompt = "/shiploop create a small game"

    def state_and_navigation(self, protocol: int, stages: tuple[str, ...], *, current_stage: str) -> tuple[dict, dict, dict]:
        history = [
            {"action": f"action-{index}", "stage": stage, "outcome": "done"}
            for index, stage in enumerate(stages, start=1)
        ]
        state = {
            "run_id": "nav-current",
            "navigator_protocol_version": protocol,
            "execution_mode": "navigator",
            "repo": str(self.repo),
            "prompt": self.prompt,
            "stage": current_stage,
            "status": "active",
            "history": history,
            "accepted": {entry["action"]: {"outcome": "done"} for entry in history},
        }
        navigation = {
            "states": [{"state": state, "source_path": str(self.run_dir / "state.md")}],
            "workspaces": [],
        }
        captured = {
            "artifacts": [
                {
                    "kind": "result",
                    "source_path": str(self.run_dir / "results" / f"{entry['action']}.md"),
                }
                for entry in history
            ]
        }
        return state, navigation, captured

    def call(self, call_id: str, argv_tail: list[str], *, completed: bool = True,
             exit_codes: list[int] | None = None) -> dict:
        return {
            "call_id": call_id,
            "argv_tail": argv_tail,
            "completed": completed,
            "exit_codes": [0] if exit_codes is None else exit_codes,
        }

    def events_for(self, state: dict, callback: str) -> dict:
        calls = [
            self.call(
                "start",
                ["init", "--repo", str(self.repo), "--run-dir", str(self.run_dir)],
            )
        ]
        calls.extend(
            self.call(
                f"callback-{index}",
                [
                    callback,
                    "--run-dir", str(self.run_dir),
                    "--action", entry["action"],
                    "--result", str(self.run_dir / "inbox" / f"{entry['action']}.md"),
                ],
            )
            for index, entry in enumerate(state["history"], start=1)
        )
        return {"cli_calls": calls}

    def partial(self, navigation: dict, events: dict, captured: dict, stop_stage: str) -> dict:
        # These pure observer cases construct navigation directly. The initial
        # archive matters only to reject preexisting run IDs, so keep it empty.
        with patch.object(run, "inspect_run_artifacts", return_value={"states": []}):
            return run.partial_observation(
                navigation, events, self.prompt, self.repo, {}, captured, stop_stage
            )

    def lifecycle(self, navigation: dict, events: dict) -> dict:
        with patch.object(run, "inspect_run_artifacts", return_value={"states": []}):
            return run.lifecycle_observation(events, navigation, self.prompt, self.repo, {})

    def test_v2_plan_improve_boundary_remains_exact(self) -> None:
        state, navigation, captured = self.state_and_navigation(
            2, run.PARTIAL_STAGES, current_stage="step-plan"
        )

        observed = self.partial(navigation, self.events_for(state, "complete"), captured, "plan-improve")

        self.assertTrue(observed["durable_boundary_reached"])
        self.assertTrue(observed["reached"])
        self.assertEqual(2, observed["protocol_version"])
        self.assertEqual("plan-improve", observed["effective_stop_stage"])
        self.assertEqual(list(run.PARTIAL_STAGES), observed["required_stages"])

    def test_v3_plan_improve_key_maps_to_accepted_plan_after_improve(self) -> None:
        stages = ("intake", "discovery", "research", "spec", "test-strategy", "plan")
        state, navigation, captured = self.state_and_navigation(3, stages, current_stage="prepare")

        observed = self.partial(navigation, self.events_for(state, "improve-complete"), captured, "plan-improve")

        self.assertTrue(observed["durable_boundary_reached"])
        self.assertTrue(observed["reached"])
        self.assertEqual(3, observed["protocol_version"])
        self.assertEqual("plan-improve", observed["requested_stage"])
        self.assertEqual("plan", observed["effective_stop_stage"])
        self.assertEqual(list(stages), observed["required_stages"])
        self.assertEqual(("research", stages[:3]), run._partial_boundary(3, "research-improve"))
        self.assertEqual(("spec", stages[:4]), run._partial_boundary(3, "spec-improve"))

    def test_v3_lifecycle_requires_matching_successful_improve_complete(self) -> None:
        state, navigation, _ = self.state_and_navigation(3, ("plan",), current_stage="prepare")
        action = state["history"][0]["action"]
        start = self.call("start", ["init", "--repo", str(self.repo), "--run-dir", str(self.run_dir)])

        producer_only = {"cli_calls": [start, self.call(
            "producer", ["complete", "--run-dir", str(self.run_dir), "--action", action, "--result", "/tmp/result"]
        )]}
        wrong_action = {"cli_calls": [start, self.call(
            "wrong-action", ["improve-complete", "--run-dir", str(self.run_dir), "--action", "other", "--result", "/tmp/result"]
        )]}
        wrong_run = {"cli_calls": [start, self.call(
            "wrong-run", ["improve-complete", "--run-dir", str(self.root / "other-run"), "--action", action, "--result", "/tmp/result"]
        )]}
        nonzero = {"cli_calls": [start, self.call(
            "nonzero", ["improve-complete", "--run-dir", str(self.run_dir), "--action", action, "--result", "/tmp/result"], exit_codes=[7]
        )]}
        accepted = {"cli_calls": [start, self.call(
            "accepted", ["improve-complete", "--run-dir", str(self.run_dir), "--action", action, "--result", "/tmp/result"]
        )]}

        for events in (producer_only, wrong_action, wrong_run, nonzero):
            observed = self.lifecycle(navigation, events)
            self.assertFalse(observed["complete"])
            self.assertEqual([action], observed["missing_callback_actions"])
        observed = self.lifecycle(navigation, accepted)
        self.assertTrue(observed["complete"])
        self.assertEqual(["improve-complete"], observed["callback_commands"])

    def test_v2_lifecycle_still_accepts_complete_and_done(self) -> None:
        state, navigation, _ = self.state_and_navigation(2, ("plan-improve",), current_stage="step-plan")

        for callback in ("complete", "done"):
            observed = self.lifecycle(navigation, self.events_for(state, callback))
            self.assertTrue(observed["complete"])
            self.assertEqual(["complete", "done"], observed["callback_commands"])

    def test_unknown_exit_cannot_support_lifecycle_attribution(self) -> None:
        for protocol, callback in ((2, "done"), (3, "improve-complete")):
            state, navigation, _ = self.state_and_navigation(protocol, ("intake",), current_stage="discovery")
            state["execution_mode"] = "navigator-worktree"
            events = self.events_for(state, callback)
            events["cli_calls"].append(self.call(
                "return", ["workspace", "return", "--workspace-root", str(self.run_dir.parent)]
            ))
            self.assertTrue(self.lifecycle(navigation, events)["complete"])
            for call in events["cli_calls"]:
                with self.subTest(protocol=protocol, boundary=call["call_id"]):
                    call["exit_codes"] = []
                    observed = self.lifecycle(navigation, events)
                    call["exit_codes"] = [0]
                    self.assertFalse(observed["complete"], observed)
                    if call["call_id"] == "start":
                        self.assertFalse(observed["start_observed"])
                    elif call["call_id"] == "return":
                        self.assertFalse(observed["return_observed"])
                    else:
                        self.assertEqual(0, observed["observed_callback_count"])
                        self.assertEqual([state["history"][0]["action"]], observed["missing_callback_actions"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
