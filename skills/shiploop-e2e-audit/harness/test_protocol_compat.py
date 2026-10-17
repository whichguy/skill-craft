"""Navigator protocol 4 observer checks; no model or ShipLoop invocation."""

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
            # Only planning checkpoints pass through an Improve stage, an action of its own whose id the record holds.
            "improve_results": {
                entry["action"]: {"summary": "Synthetic Improve receipt.", "improve_action": f"improve-for-{entry['action']}"}
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
                   overrides: dict[str, str] | None = None, named: dict[str, str] | None = None) -> dict:
        """Emit the per-action callback a correct host would issue: the Improve stage's `complete` names the stage's id, a producer's
        names its own action. ``overrides`` swaps a verb, ``named`` swaps the id the call names."""
        calls = [
            self.call(
                "start",
                ["init", "--repo", str(self.repo), "--run-dir", str(self.run_dir)],
            )
        ]
        for index, entry in enumerate(state["history"], start=1):
            action = entry["action"]
            callback = (overrides or {}).get(action, producer_callback)
            named_id = (named or {}).get(action, state["improve_results"].get(action, {}).get("improve_action", action))
            calls.append(self.call(
                f"callback-{index}",
                [
                    callback,
                    "--run-dir", str(self.run_dir),
                    "--action", named_id,
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

    def test_plan_stop_is_the_accepted_plan_after_improve(self) -> None:
        stages = ("intake", "discovery", "research", "spec", "test-strategy", "plan")
        self.assertEqual(stages, run.PARTIAL_STAGES)
        state, navigation, captured = self.state_and_navigation(4, stages, current_stage="prepare")

        observed = self.partial(navigation, self.events_for(state), captured, "plan")

        self.assertTrue(observed["durable_boundary_reached"])
        self.assertTrue(observed["reached"])
        self.assertEqual(4, observed["protocol_version"])
        self.assertEqual("plan", observed["requested_stage"])
        self.assertEqual("plan", observed["effective_stop_stage"])
        self.assertEqual(list(stages), observed["required_stages"])
        self.assertEqual("accepted-prefix-and-callbacks-observed", observed["reason"])
        self.assertEqual(("plan", run.PARTIAL_STAGES), run._partial_boundary(4, "plan"))
        self.assertEqual(("research", stages[:3]), run._partial_boundary(4, "research"))
        self.assertEqual(("spec", stages[:4]), run._partial_boundary(4, "spec"))
        for retired in ("research-improve", "spec-improve", "plan-improve", "step-plan"):
            with self.subTest(retired=retired):
                self.assertIsNone(run._partial_boundary(4, retired))

        # The plan producer callback alone (it names the reviewed action, not its Improve stage) never accepts a planning checkpoint.
        producer_only = self.events_for(state, named={
            entry["action"]: entry["action"] for entry in state["history"] if entry["stage"] == "plan"
        })
        observed = self.partial(navigation, producer_only, captured, "plan")
        self.assertFalse(observed["reached"])
        self.assertEqual("prefix-callbacks-unverified", observed["reason"])

    def test_retired_protocols_have_no_boundary_or_lifecycle_credit(self) -> None:
        for protocol in (1, 2, 3, None):
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

    def test_lifecycle_requires_the_improve_stages_own_successful_complete(self) -> None:
        state, navigation, _ = self.state_and_navigation(4, ("plan",), current_stage="prepare")
        action = state["history"][0]["action"]
        stage_id = state["improve_results"][action]["improve_action"]
        start = self.call("start", ["init", "--repo", str(self.repo), "--run-dir", str(self.run_dir)])

        def complete(call_id: str, named: str, run_dir: Path | None = None, **extra) -> dict:
            return {"cli_calls": [start, self.call(
                call_id, ["complete", "--run-dir", str(run_dir or self.run_dir), "--action", named, "--result", "/tmp/result"], **extra
            )]}

        producer_only = complete("producer", action)  # parks the action at its Improve stage: accepts nothing
        wrong_action = complete("wrong-action", "other")
        wrong_run = complete("wrong-run", stage_id, self.root / "other-run")
        nonzero = complete("nonzero", stage_id, exit_codes=[7])
        retired_verb = {"cli_calls": [start, self.call(
            "retired", ["improve-complete", "--run-dir", str(self.run_dir), "--action", stage_id, "--result", "/tmp/result"]
        )]}
        accepted = complete("accepted", stage_id)

        for events in (producer_only, wrong_action, wrong_run, nonzero, retired_verb):
            observed = self.lifecycle(navigation, events)
            self.assertFalse(observed["complete"])
            self.assertEqual([action], observed["missing_callback_actions"])
        observed = self.lifecycle(navigation, accepted)
        self.assertTrue(observed["complete"])
        self.assertEqual(["complete"], observed["callback_commands"])

    def test_a_saved_run_of_the_older_layout_is_still_accepted_by_its_improve_complete(self) -> None:
        """A record without `improve_action` is a run from before the Improve stage was an action of its own."""
        state, navigation, _ = self.state_and_navigation(4, ("plan",), current_stage="prepare")
        action = state["history"][0]["action"]
        del state["improve_results"][action]["improve_action"]
        start = self.call("start", ["init", "--repo", str(self.repo), "--run-dir", str(self.run_dir)])
        accepted = {"cli_calls": [start, self.call(
            "accepted", ["improve-complete", "--run-dir", str(self.run_dir), "--action", action, "--result", "/tmp/result"]
        )]}
        producer_only = {"cli_calls": [start, self.call(
            "producer", ["complete", "--run-dir", str(self.run_dir), "--action", action, "--result", "/tmp/result"]
        )]}
        observed = self.lifecycle(navigation, accepted)
        self.assertTrue(observed["complete"])
        self.assertEqual(["improve-complete"], observed["callback_commands"])
        self.assertFalse(self.lifecycle(navigation, producer_only)["complete"])

    def test_lifecycle_matches_each_action_to_its_callback(self) -> None:
        state, navigation, _ = self.state_and_navigation(
            4, ("intake", "plan"), current_stage="prepare"
        )
        intake, plan = (entry["action"] for entry in state["history"])
        self.assertEqual({plan}, set(state["improve_results"]))

        observed = self.lifecycle(navigation, self.events_for(state))
        self.assertTrue(observed["complete"], observed)
        self.assertEqual([], observed["missing_callback_actions"])
        self.assertEqual(["complete"], observed["callback_commands"])
        self.assertEqual(
            {intake: ["complete"], plan: ["complete"]},
            observed["action_callback_commands"],
        )

        # The retired ``done`` alias is not a ShipLoop verb and earns no credit.
        retired_alias = self.lifecycle(navigation, self.events_for(state, "done"))
        self.assertFalse(retired_alias["complete"])
        self.assertEqual([intake, plan], retired_alias["missing_callback_actions"])

        # The producer complete naming the reviewed plan action parks it: the Improve stage's complete is what accepts it.
        producer_for_plan = self.events_for(state, named={plan: plan})
        observed = self.lifecycle(navigation, producer_for_plan)
        self.assertFalse(observed["complete"])
        self.assertEqual([plan], observed["missing_callback_actions"])

        # An Improve stage's id earns nothing for an action that has no Improve record.
        improve_for_intake = self.events_for(state, named={intake: f"improve-for-{intake}"})
        observed = self.lifecycle(navigation, improve_for_intake)
        self.assertFalse(observed["complete"])
        self.assertEqual([intake], observed["missing_callback_actions"])

        # A stopped initial plan child is accepted only by improve-reconcile, which names the Improve stage's id.
        state, navigation, _ = self.state_and_navigation(4, ("intake", "plan"), current_stage="spec")
        intake, plan = (entry["action"] for entry in state["history"])
        state["improve_results"][plan]["runtime_phase"] = "stopped"
        observed = self.lifecycle(navigation, self.events_for(state, overrides={plan: "improve-reconcile"}))
        self.assertTrue(observed["complete"], observed)
        self.assertEqual(["improve-reconcile"], observed["action_callback_commands"][plan])
        observed = self.lifecycle(navigation, self.events_for(state))
        self.assertEqual([plan], observed["missing_callback_actions"])

    def test_script_recorded_stages_need_no_callback_and_check_only_is_not_one(self) -> None:
        state, navigation, _ = self.state_and_navigation(
            4, ("step-plan", "validate-existing", "implement", "test", "document"), current_stage="inner-loop"
        )
        step_plan, validate, implement, test, document = (entry["action"] for entry in state["history"])
        # the engine's sentence now ends at "state." (the record is in evidence_refs); an earlier ShipLoop's went on
        # with "; validate-existing was recorded without running it. Records: <path>", and both are script-recorded
        earlier = ("ShipLoop ran every expectation check on the unchanged checkout and each matched its state; "
                   "validate-existing was recorded without running it. Records: /run/expectations/x.json")
        state["history"][1]["summary"] = (
            "ShipLoop ran every expectation check on the unchanged checkout and each matched its state.")
        for row in state["history"][3:]:
            row["summary"] = ("Not applicable to this item: the step plan declares only docs paths. "
                              "ShipLoop recorded this stage without running it.")
        # validate-existing, test and document were recorded by script: only step-plan and implement need callbacks.
        events = {"cli_calls": [self.call("start", ["init", "--repo", str(self.repo), "--run-dir", str(self.run_dir)])]
                  + [self.call(f"cb-{action}", ["complete", "--run-dir", str(self.run_dir), "--action", action])
                     for action in (step_plan, implement)]}
        observed = self.lifecycle(navigation, events)
        self.assertTrue(observed["complete"], observed)
        self.assertEqual(sorted((step_plan, implement)), sorted(observed["action_callback_commands"]))
        state["history"][1]["summary"] = earlier
        self.assertTrue(self.lifecycle(navigation, events)["complete"])
        # The same stage with a model-written summary is still owed its callback.
        state["history"][3]["summary"] = "Wrote the tests; every command passed."
        observed = self.lifecycle(navigation, events)
        self.assertEqual([test], observed["missing_callback_actions"])
        state["history"][3]["summary"] = state["history"][4]["summary"]
        # A check-only complete runs the gates without accepting, so it cannot stand in for the callback.
        check_only = {"cli_calls": events["cli_calls"][:2] + [self.call(
            "check-only", ["complete", "--run-dir", str(self.run_dir), "--action", implement, "--check-only"])]}
        observed = self.lifecycle(navigation, check_only)
        self.assertFalse(observed["complete"])
        self.assertEqual([implement], observed["missing_callback_actions"])
        del validate, document

    def test_unknown_exit_cannot_support_lifecycle_attribution(self) -> None:
        for protocol, stages in ((4, ("intake",)), (4, ("plan",))):
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
