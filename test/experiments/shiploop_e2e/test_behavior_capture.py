#!/usr/bin/env python3
"""No-model checks for the sanitized retained-trial behavior export."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "shiploop_e2e_behavior_capture_under_test", HERE / "behavior_capture.py"
)
assert SPEC and SPEC.loader
behavior_capture = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = behavior_capture
SPEC.loader.exec_module(behavior_capture)


SHA256 = re.compile(r"^[0-9a-f]{64}$")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def state_markdown(state: dict[str, object]) -> bytes:
    return ("# retained state\n\n```shiploop-state\n" + json.dumps(state) + "\n```\n").encode()


class BehaviorCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-e2e-behavior-")
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def make_trial(
        self,
        *,
        name: str = "trial",
        protocol: int = 2,
        outcome: str = "done",
        original_overall: str = "passed",
        initial_state: dict[str, object] | None = None,
        malformed_event: bool = False,
        unknown_stage: str | None = None,
    ) -> Path:
        trial = self.root / name
        trial.mkdir()
        prompt = "/shiploop Create harmless app with token secret-prompt-value at /Users/private/project"
        prompt_bytes = prompt.encode()
        (trial / "prompt.txt").write_bytes(prompt_bytes)
        manifest = {
            "schema_version": 1,
            "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
            "timeout_seconds": 7200,
            "max_turns": 1000,
            "reasoning_effort_requested": "xhigh",
            "permission_mode": "bypassPermissions",
            "partial": False,
            "stop_after_stage": None,
            "harness_sha256": "a" * 64,
            "scenario": {"kind": "create", "prompt": prompt},
        }
        write_json(trial / "manifest.json", manifest)
        work_items = [
            {"id": "first-secret-work-item", "title": "Sensitive title at /Users/user"},
            {"id": "second-secret-work-item", "title": "Other sensitive title"},
        ]
        stages = ["intake", "plan", "plan-improve", "step-plan", "carry-forward", "handoff"]
        if unknown_stage is not None:
            stages[2] = unknown_stage
        action_ids = [f"opaque-action-{index}" for index in range(len(stages))]
        history = []
        accepted: dict[str, object] = {}
        for index, (stage, action) in enumerate(zip(stages, action_ids)):
            owner = None if stage in {"intake", "plan", "plan-improve", "handoff"} else "first-secret-work-item"
            history.append({
                "action": action,
                "stage": stage,
                "outcome": outcome,
                "summary": "Secret model prose at /Users/private and secret-prompt-value",
                "workitem": owner,
            })
            result: dict[str, object] = {
                "outcome": outcome,
                "summary": "A raw result containing secret-prompt-value and /Users/private",
            }
            if stage == "plan":
                result["work_items"] = work_items
            accepted[action] = result
        state = {
            "navigator_protocol_version": protocol,
            "run_id": "opaque-live-run-id",
            "prompt": prompt.removeprefix("/shiploop "),
            "stage": "done",
            "status": "done",
            "revision": len(history),
            "work_items": work_items,
            "accepted": accepted,
            "history": history,
        }
        write_json(trial / "navigation.json", {"states": [{"state": state}]})
        result = {
            "schema_version": 1,
            "process": {
                "exit_code": 0,
                "timed_out": False,
                "truncated": False,
                "duration_seconds": 12.34567,
                "termination_reason": None,
            },
            "statuses": {
                "overall": original_overall,
                "product": "passed" if original_overall == "passed" else "unverified",
                "process": "exited",
                "skill": "selected-stable",
                "protocol": "declared-complete-return-observed",
            },
            "skill_digest": "b" * 64,
            "skill_stable": True,
            "observer_digest": "c" * 64,
            "observer_after_digest": "c" * 64,
            "observer_stable": True,
            "candidate_digest": "d" * 64,
            "baseline_digest": None,
            "host_observations": {"cli_calls": []},
        }
        write_json(trial / "result.json", result)
        archive = trial / "artifacts"
        archive.mkdir()
        initial = {"schema": "shiploop-e2e-artifacts/v1", "output": str(archive), "artifacts": []}
        if initial_state is not None:
            data = state_markdown(initial_state)
            digest = hashlib.sha256(data).hexdigest()
            blob = archive / "blobs" / digest
            blob.parent.mkdir(parents=True)
            blob.write_bytes(data)
            initial["artifacts"] = [{"kind": "state", "archive_path": f"blobs/{digest}", "sha256": digest}]
        write_json(trial / "initial-evidence.json", initial)
        events = trial / "capture" / "events.jsonl"
        events.parent.mkdir()
        rows = [
            {"payload": {"type": "tool_call", "status": "started", "command": "secret command /Users/private"}},
            {"payload": {"type": "tool_call_update", "status": "completed", "rawOutput": {"exitCode": 0, "content": "secret output"}}},
            {"payload": {"type": "end", "exitCode": 0}},
        ]
        contents = "\n".join(json.dumps(row) for row in rows) + "\n"
        if malformed_event:
            contents += "{not-json\n"
        events.write_text(contents, encoding="utf-8")
        return trial

    def test_complete_v2_capture_is_sanitized_and_derives_a_case(self) -> None:
        trial = self.make_trial()
        bundle = behavior_capture.export_trial(trial)
        encoded = json.dumps(bundle, sort_keys=True)

        self.assertEqual(bundle["schema"], behavior_capture.SCHEMA)
        self.assertEqual(bundle["capture_status"], "complete")
        self.assertEqual(bundle["replay"], {
            "status": "derivable", "reason": "complete-all-done-v2-initial-scope"
        })
        self.assertEqual(bundle["dag"]["work_items"], [
            {"id": "W1", "title": "Synthetic work item W1"},
            {"id": "W2", "title": "Synthetic work item W2"},
        ])
        self.assertEqual(bundle["dag"]["accepted_count"], 6)
        self.assertEqual(len(bundle["dag"]["accepted_history"]), 6)
        self.assertTrue(all(SHA256.fullmatch(row["accepted_result_sha256"])
                            for row in bundle["dag"]["accepted_history"]))
        self.assertNotIn("secret-prompt-value", encoded)
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("first-secret-work-item", encoded)
        self.assertNotIn("opaque-live-run-id", encoded)

        case = behavior_capture._replay_case(bundle)
        self.assertIsNotNone(case)
        assert case is not None
        self.assertEqual(case["schema"], behavior_capture.CASE_SCHEMA)
        self.assertEqual(case["protocol_version"], 2)
        self.assertEqual(case["steps"][1]["result"]["work_items"], bundle["dag"]["work_items"])
        self.assertEqual(case["expected_final"], {"stage": "done", "status": "done"})
        self.assertEqual(len(case["provenance"]["accepted_result_sha256"]), 6)

    def test_missing_trial_is_unavailable_without_throwing(self) -> None:
        bundle = behavior_capture.export_trial(self.root / "absent")
        self.assertEqual(bundle["capture_status"], "unavailable")
        self.assertEqual(bundle["limitations"], ["trial-directory-unavailable"])
        self.assertNotIn(str(self.root), json.dumps(bundle))

    def test_malformed_native_event_is_partial_and_never_green(self) -> None:
        bundle = behavior_capture.export_trial(self.make_trial(malformed_event=True))
        self.assertEqual(bundle["capture_status"], "partial")
        self.assertIn("native-events-partial", bundle["limitations"])
        self.assertEqual(bundle["native_events"]["error_counts"]["malformed-json"], 1)
        self.assertEqual(bundle["replay"]["status"], "not-replayable")

    def test_tool_exit_buckets_require_terminal_updates_and_accept_both_aliases(self) -> None:
        # An in-progress zero is a Grok placeholder, not terminal tool evidence.
        for exit_key in ("exitCode", "exit_code"):
            for final_status, final_code, expected_exits, expected_errors in (
                (None, None, {}, {}),
                ("completed", None, {}, {}),
                ("completed", 9, {"nonzero": 1}, {"native-nonzero-exit": 1}),
                ("completed", 0, {"zero": 1}, {}),
                ("failed", 9, {"nonzero": 1}, {
                    "native-failed-status": 1, "native-nonzero-exit": 1,
                }),
            ):
                with self.subTest(exit_key=exit_key, status=final_status, code=final_code):
                    trial = self.make_trial(
                        name=f"terminal-exit-{exit_key}-{final_status}-{final_code}"
                    )
                    rows = [{
                        "payload": {
                            "type": "tool_call_update", "status": "in_progress",
                            "rawOutput": {exit_key: 0},
                        },
                    }]
                    if final_status is not None:
                        rows.append({
                            "payload": {
                                "type": "tool_call_update", "status": final_status,
                                "rawOutput": {} if final_code is None else {exit_key: final_code},
                            },
                        })
                    events = trial / "capture" / "events.jsonl"
                    events.write_text(
                        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
                    )

                    native = behavior_capture.export_trial(trial)["native_events"]
                    expected_statuses = {"in_progress": 1}
                    if final_status is not None:
                        expected_statuses[final_status] = 1
                    self.assertEqual(native["native_status_counts"], expected_statuses)
                    self.assertEqual(native["exit_code_counts"], expected_exits)
                    self.assertEqual(native["error_counts"], expected_errors)

    def test_unhashable_tool_update_status_remains_partial_without_exit_evidence(self) -> None:
        trial = self.make_trial(name="unhashable-tool-update-status")
        events = trial / "capture" / "events.jsonl"
        events.write_text(json.dumps({
            "payload": {
                "type": "tool_call_update", "status": ["secret-status"],
                "rawOutput": {"exit_code": 0},
            },
        }) + "\n", encoding="utf-8")

        bundle = behavior_capture.export_trial(trial)
        native = bundle["native_events"]
        self.assertEqual(bundle["capture_status"], "partial")
        self.assertEqual(native["native_status_counts"], {})
        self.assertEqual(native["exit_code_counts"], {})
        self.assertEqual(native["error_counts"], {"unknown-native-status": 1})
        self.assertNotIn("secret-status", json.dumps(bundle, sort_keys=True))

    def test_end_top_level_exit_aliases_remain_observable(self) -> None:
        for exit_key, exit_code, expected_exits, expected_errors in (
            ("exitCode", 0, {"zero": 1}, {}),
            ("exit_code", 9, {"nonzero": 1}, {"native-nonzero-exit": 1}),
        ):
            with self.subTest(exit_key=exit_key):
                trial = self.make_trial(name=f"end-exit-{exit_key}")
                events = trial / "capture" / "events.jsonl"
                events.write_text(json.dumps({
                    "payload": {"type": "end", exit_key: exit_code},
                }) + "\n", encoding="utf-8")

                native = behavior_capture.export_trial(trial)["native_events"]
                self.assertEqual(native["native_event_counts"], {"end": 1})
                self.assertEqual(native["native_status_counts"], {})
                self.assertEqual(native["exit_code_counts"], expected_exits)
                self.assertEqual(native["error_counts"], expected_errors)

    def test_unsupported_stage_or_control_does_not_invent_a_replay(self) -> None:
        bundle = behavior_capture.export_trial(
            self.make_trial(protocol=3, outcome="replan", unknown_stage="secret-control-at-/Users/private")
        )
        encoded = json.dumps(bundle, sort_keys=True)
        self.assertEqual(bundle["capture_status"], "partial")
        self.assertEqual(bundle["replay"]["status"], "not-replayable")
        self.assertIn("unsupported-history-stage", bundle["limitations"])
        self.assertNotIn("secret-control", encoded)
        self.assertNotIn("/Users/", encoded)
        self.assertIsNone(behavior_capture._replay_case(bundle))

    def test_mismatched_accepted_result_and_incomplete_process_block_replay(self) -> None:
        trial = self.make_trial()
        navigation = json.loads((trial / "navigation.json").read_text(encoding="utf-8"))
        first_action = navigation["states"][0]["state"]["history"][0]["action"]
        navigation["states"][0]["state"]["accepted"][first_action]["outcome"] = "repeat"
        write_json(trial / "navigation.json", navigation)
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        result["process"]["exit_code"] = 7
        write_json(trial / "result.json", result)

        bundle = behavior_capture.export_trial(trial)
        self.assertEqual(bundle["capture_status"], "partial")
        self.assertIn("accepted-result-outcome-mismatch", bundle["limitations"])
        self.assertIn("process-incomplete", bundle["limitations"])
        self.assertEqual(bundle["replay"]["status"], "not-replayable")

    def test_catalog_scenario_kinds_are_preserved_and_unknown_text_stays_unverified(self) -> None:
        catalog = json.loads((HERE / "scenarios.json").read_text(encoding="utf-8"))
        kinds = sorted({
            step["kind"]
            for scenario in catalog["scenarios"]
            for step in scenario["steps"]
        })
        self.assertTrue(kinds)
        for kind in kinds:
            with self.subTest(kind=kind):
                trial = self.make_trial(name=f"catalog-{kind}")
                manifest_path = trial / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["scenario"]["kind"] = kind
                write_json(manifest_path, manifest)
                bundle = behavior_capture.export_trial(trial)
                self.assertEqual(kind, bundle["requested_settings"]["scenario_kind"])

        trial = self.make_trial(name="unknown-catalog-kind")
        manifest_path = trial / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["scenario"]["kind"] = "unsafe-catalog-kind"
        write_json(manifest_path, manifest)
        self.assertEqual(
            "unverified",
            behavior_capture.export_trial(trial)["requested_settings"]["scenario_kind"],
        )

    def test_missing_or_null_process_completion_fields_are_partial_and_nonderivable(self) -> None:
        for field in ("exit_code", "timed_out", "truncated"):
            for mutation in ("remove", "null"):
                with self.subTest(field=field, mutation=mutation):
                    trial = self.make_trial(name=f"{field}-{mutation}")
                    result_path = trial / "result.json"
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                    if mutation == "remove":
                        del result["process"][field]
                    else:
                        result["process"][field] = None
                    write_json(result_path, result)
                    bundle = behavior_capture.export_trial(trial)
                    self.assertEqual(bundle["capture_status"], "partial")
                    self.assertIn("process-incomplete", bundle["limitations"])
                    self.assertEqual(bundle["replay"]["status"], "not-replayable")

    def test_bad_enums_and_stderr_wrapper_cannot_raise_or_count_as_native(self) -> None:
        trial = self.make_trial()
        manifest = json.loads((trial / "manifest.json").read_text(encoding="utf-8"))
        manifest["reasoning_effort_requested"] = ["secret-effort"]
        manifest["permission_mode"] = {"secret": "permission"}
        manifest["scenario"]["kind"] = ["secret-kind"]
        write_json(trial / "manifest.json", manifest)
        result = json.loads((trial / "result.json").read_text(encoding="utf-8"))
        result["statuses"]["overall"] = ["secret-status"]
        write_json(trial / "result.json", result)
        events = trial / "capture" / "events.jsonl"
        with events.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "stream": "stderr",
                "payload": {"type": "tool_call", "status": "completed", "command": "secret command"},
            }) + "\n")
            handle.write(json.dumps({
                "stream": "stdout", "line_truncated": True,
                "payload": {"type": "tool_call", "status": "completed"},
            }) + "\n")

        bundle = behavior_capture.export_trial(trial)
        encoded = json.dumps(bundle, sort_keys=True)
        self.assertEqual(bundle["capture_status"], "partial")
        self.assertEqual(bundle["requested_settings"]["reasoning_effort"], "unverified")
        self.assertEqual(bundle["original_statuses"]["overall"], "unverified")
        self.assertEqual(bundle["native_events"]["error_counts"]["stderr-wrapper"], 1)
        self.assertEqual(bundle["native_events"]["error_counts"]["line-truncated"], 1)
        self.assertNotIn("secret-effort", encoded)
        self.assertNotIn("secret command", encoded)

    def test_preexisting_matching_run_keeps_invalid_trial_qualification(self) -> None:
        prompt = "Create harmless app with token secret-prompt-value at /Users/private/project"
        initial = {
            "navigator_protocol_version": 2,
            "run_id": "opaque-live-run-id",
            "prompt": prompt,
            "stage": "discovery",
            "status": "active",
            "revision": 1,
        }
        bundle = behavior_capture.export_trial(
            self.make_trial(initial_state=initial, original_overall="invalid-trial")
        )
        self.assertTrue(bundle["dag"]["preexisting"]["selected_run_preexisting"])
        self.assertEqual(bundle["original_statuses"]["overall"], "invalid-trial")
        self.assertEqual(bundle["replay"], {
            "status": "not-replayable", "reason": "preexisting-run-not-fresh-one-shot"
        })
        self.assertIsNone(behavior_capture._replay_case(bundle))

    def test_hashes_change_when_source_changes(self) -> None:
        trial = self.make_trial()
        before = behavior_capture.export_trial(trial)
        result_path = trial / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["statuses"]["overall"] = "invalid-trial"
        write_json(result_path, result)
        after = behavior_capture.export_trial(trial)
        self.assertNotEqual(
            before["provenance"]["source_hashes"]["result.json"]["sha256"],
            after["provenance"]["source_hashes"]["result.json"]["sha256"],
        )
        self.assertNotEqual(
            before["provenance"]["canonical_result_sha256"],
            after["provenance"]["canonical_result_sha256"],
        )

    def test_cli_requires_a_new_output_file_and_writes_no_raw_input(self) -> None:
        trial = self.make_trial()
        output = self.root / "portable.json"
        command = [sys.executable, "-B", str(HERE / "behavior_capture.py"),
                   "--trial", str(trial), "--output", str(output)]
        first = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertTrue(output.is_file())
        self.assertNotIn("secret-prompt-value", output.read_text(encoding="utf-8"))
        second = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertNotEqual(second.returncode, 0)
        self.assertIn("new JSON", second.stderr)

    def test_replay_case_refuses_to_overwrite_a_retained_fixture(self) -> None:
        trial = self.make_trial()
        directory = self.root / "cases"
        first = behavior_capture.write_replay_case(trial, directory)
        self.assertIsNotNone(first)
        assert first is not None
        original = first.read_bytes()
        with self.assertRaises(FileExistsError):
            behavior_capture.write_replay_case(trial, directory)
        self.assertEqual(first.read_bytes(), original)

    def test_checked_in_retained_cases_are_complete_v2_and_provenanced(self) -> None:
        fixtures = HERE / "fixtures" / "dag"
        paths = [
            fixtures / "captured_ttt_create_v2.json",
            fixtures / "captured_checkers_create_v2.json",
        ]
        self.assertTrue(all(path.is_file() for path in paths))
        cases = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
        self.assertEqual({len(case["steps"]) for case in cases}, {25, 35})
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(case["schema"], behavior_capture.CASE_SCHEMA)
                self.assertEqual(case["kind"], "retained-trace")
                self.assertEqual(case["protocol_version"], 2)
                self.assertEqual(case["expected_final"], {"stage": "done", "status": "done"})
                self.assertTrue(SHA256.fullmatch(case["provenance"]["canonical_result_sha256"]))
                self.assertEqual(len(case["provenance"]["accepted_result_sha256"]), len(case["steps"]))
                self.assertTrue(all(step["command"] == "done" for step in case["steps"]))
                self.assertNotIn("/Users/", json.dumps(case, sort_keys=True))
        two_item = next(case for case in cases if len(case["steps"]) == 35)
        self.assertEqual(len(two_item["steps"][7]["result"]["work_items"]), 2)
        product_failed = next(case for case in cases if len(case["steps"]) == 25)
        self.assertEqual(product_failed["provenance"]["original_outcome"], "product-failed")

    def test_checked_in_invalid_feature_behavior_remains_invalid(self) -> None:
        path = HERE / "fixtures" / "behavior" / "captured_ttt_guidance.json"
        bundle = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(bundle["schema"], behavior_capture.SCHEMA)
        self.assertEqual(bundle["original_statuses"]["overall"], "invalid-trial")
        self.assertTrue(bundle["dag"]["preexisting"]["selected_run_preexisting"])
        self.assertEqual(bundle["replay"]["status"], "not-replayable")
        self.assertNotIn("/Users/", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
