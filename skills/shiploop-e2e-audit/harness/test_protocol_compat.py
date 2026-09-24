"""Navigator protocol 3/4 observer checks; no model or ShipLoop invocation."""

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


# The prelude planning checkpoints, stated literally rather than imported.
PRELUDE_CHECKPOINTS = frozenset(("spec", "test-strategy", "plan"))


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
            # Only planning checkpoints pass through an Improve child.
            "improve_results": {
                entry["action"]: {"summary": "Synthetic Improve receipt."}
                for entry in history if entry["stage"] in PRELUDE_CHECKPOINTS
            },
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

    def events_for(self, state: dict, producer_callback: str = "complete", *,
                   overrides: dict[str, str] | None = None) -> dict:
        """Emit the per-action callback a correct host would issue."""
        calls = [
            self.call(
                "start",
                ["init", "--repo", str(self.repo), "--run-dir", str(self.run_dir)],
            )
        ]
        for index, entry in enumerate(state["history"], start=1):
            action = entry["action"]
            callback = "improve-complete" if action in state["improve_results"] else producer_callback
            callback = (overrides or {}).get(action, callback)
            calls.append(self.call(
                f"callback-{index}",
                [
                    callback,
                    "--run-dir", str(self.run_dir),
                    "--action", action,
                    "--result", str(self.run_dir / "inbox" / f"{action}.md"),
                ],
            ))
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

    def test_v3_plan_stop_is_the_accepted_plan_after_improve(self) -> None:
        stages = ("intake", "discovery", "research", "spec", "test-strategy", "plan")
        self.assertEqual(stages, run.PARTIAL_STAGES)
        state, navigation, captured = self.state_and_navigation(3, stages, current_stage="prepare")

        observed = self.partial(navigation, self.events_for(state), captured, "plan")

        self.assertTrue(observed["durable_boundary_reached"])
        self.assertTrue(observed["reached"])
        self.assertEqual(3, observed["protocol_version"])
        self.assertEqual("plan", observed["requested_stage"])
        self.assertEqual("plan", observed["effective_stop_stage"])
        self.assertEqual(list(stages), observed["required_stages"])
        self.assertEqual(("research", stages[:3]), run._partial_boundary(3, "research"))
        self.assertEqual(("spec", stages[:4]), run._partial_boundary(3, "spec"))
        for retired in ("research-improve", "spec-improve", "plan-improve", "step-plan"):
            with self.subTest(retired=retired):
                self.assertIsNone(run._partial_boundary(3, retired))

        # The plan producer callback alone never accepts a planning checkpoint.
        producer_only = self.events_for(state, overrides={
            entry["action"]: "complete" for entry in state["history"] if entry["stage"] == "plan"
        })
        observed = self.partial(navigation, producer_only, captured, "plan")
        self.assertFalse(observed["reached"])
        self.assertEqual("prefix-callbacks-unverified", observed["reason"])

    def test_protocol_4_partial_boundary_matches_v3_prelude(self) -> None:
        self.assertEqual(("plan", run.PARTIAL_STAGES), run._partial_boundary(4, "plan"))
        self.assertEqual(run._partial_boundary(3, "spec"), run._partial_boundary(4, "spec"))
        state, navigation, captured = self.state_and_navigation(
            4, run.PARTIAL_STAGES, current_stage="prepare"
        )

        observed = self.partial(navigation, self.events_for(state), captured, "plan")

        self.assertTrue(observed["reached"], observed)
        self.assertEqual(4, observed["protocol_version"])
        self.assertEqual(list(run.PARTIAL_STAGES), observed["required_stages"])
        self.assertEqual("accepted-prefix-and-callbacks-observed", observed["reason"])

    def test_retired_protocols_have_no_boundary_or_lifecycle_credit(self) -> None:
        for protocol in (1, 2, None):
            with self.subTest(protocol=protocol):
                self.assertIsNone(run._partial_boundary(protocol, "plan"))
                state, navigation, captured = self.state_and_navigation(
                    protocol, ("intake",), current_stage="discovery"
                )
                events = self.events_for(state)
                observed = self.partial(navigation, events, captured, "intake")
                self.assertFalse(observed["reached"])
                self.assertEqual("unsupported-stop-stage-for-protocol", observed["reason"])
                lifecycle = self.lifecycle(navigation, events)
                self.assertFalse(lifecycle["complete"])
                self.assertEqual("unsupported-navigator-protocol", lifecycle["reason"])

    def test_v3_lifecycle_requires_matching_successful_improve_complete(self) -> None:
        state, navigation, _ = self.state_and_navigation(3, ("plan",), current_stage="prepare")
        action = state["history"][0]["action"]
        self.assertIn(action, state["improve_results"])
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

    def test_v3_and_v4_lifecycle_match_each_action_to_its_callback(self) -> None:
        for protocol in (3, 4):
            with self.subTest(protocol=protocol):
                state, navigation, _ = self.state_and_navigation(
                    protocol, ("intake", "plan"), current_stage="prepare"
                )
                intake, plan = (entry["action"] for entry in state["history"])
                self.assertEqual({plan}, set(state["improve_results"]))

                for producer in ("complete", "done"):
                    observed = self.lifecycle(navigation, self.events_for(state, producer))
                    self.assertTrue(observed["complete"], observed)
                    self.assertEqual([], observed["missing_callback_actions"])
                self.assertEqual(["complete", "done", "improve-complete"], observed["callback_commands"])
                self.assertEqual(
                    {intake: ["complete", "done"], plan: ["improve-complete"]},
                    observed["action_callback_commands"],
                )

                producer_for_plan = self.events_for(state, overrides={plan: "complete"})
                observed = self.lifecycle(navigation, producer_for_plan)
                self.assertFalse(observed["complete"])
                self.assertEqual([plan], observed["missing_callback_actions"])

                improve_for_intake = self.events_for(state, overrides={intake: "improve-complete"})
                observed = self.lifecycle(navigation, improve_for_intake)
                self.assertFalse(observed["complete"])
                self.assertEqual([intake], observed["missing_callback_actions"])

        # A stopped protocol-4 plan child is accepted only by improve-reconcile.
        state, navigation, _ = self.state_and_navigation(4, ("intake", "plan"), current_stage="spec")
        intake, plan = (entry["action"] for entry in state["history"])
        state["improve_results"][plan] = {"runtime_phase": "stopped"}
        observed = self.lifecycle(navigation, self.events_for(state, overrides={plan: "improve-reconcile"}))
        self.assertTrue(observed["complete"], observed)
        self.assertEqual(["improve-reconcile"], observed["action_callback_commands"][plan])
        observed = self.lifecycle(navigation, self.events_for(state))
        self.assertEqual([plan], observed["missing_callback_actions"])

    def test_unknown_exit_cannot_support_lifecycle_attribution(self) -> None:
        for protocol, stages in ((3, ("intake",)), (3, ("plan",)), (4, ("plan",))):
            state, navigation, _ = self.state_and_navigation(protocol, stages, current_stage="prepare")
            state["execution_mode"] = "navigator-worktree"
            events = self.events_for(state)
            events["cli_calls"].append(self.call(
                "return", ["workspace", "return", "--workspace-root", str(self.run_dir.parent)]
            ))
            self.assertTrue(self.lifecycle(navigation, events)["complete"])
            for call in events["cli_calls"]:
                with self.subTest(protocol=protocol, stages=stages, boundary=call["call_id"]):
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
