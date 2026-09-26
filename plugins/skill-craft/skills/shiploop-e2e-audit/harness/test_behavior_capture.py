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
        protocol: int = 4,
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
        stages = ["intake", "plan", "prepare", "step-plan", "carry-forward", "handoff"]
        if unknown_stage is not None:
            stages[2] = unknown_stage
        action_ids = [f"opaque-action-{index}" for index in range(len(stages))]
        history = []
        accepted: dict[str, object] = {}
        for index, (stage, action) in enumerate(zip(stages, action_ids)):
            owner = None if stage in {"intake", "plan", "prepare", "handoff"} else "first-secret-work-item"
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

    def test_complete_v4_capture_is_sanitized(self) -> None:
        trial = self.make_trial()
        bundle = behavior_capture.export_trial(trial)
        encoded = json.dumps(bundle, sort_keys=True)

        self.assertEqual(bundle["schema"], behavior_capture.SCHEMA)
        self.assertEqual(bundle["capture_status"], "complete")
        self.assertEqual(bundle["replay"], {
            "status": "not-replayable", "reason": "callback-sequence-not-derivable"
        })
        self.assertEqual(bundle["dag"]["protocol_version"], 4)
        self.assertEqual(
            [row["at"] for row in bundle["dag"]["accepted_history"]],
            ["intake", "plan", "prepare", "step-plan", "carry-forward", "handoff"],
        )
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
        self.assertFalse(hasattr(behavior_capture, "write_replay_case"))

    def test_retired_protocols_are_unsupported_and_protocol_4_is_canonicalized(self) -> None:
        for protocol in (2, 3):
            with self.subTest(protocol=protocol):
                retired = behavior_capture.export_trial(
                    self.make_trial(name=f"protocol-{protocol}", protocol=protocol))
                encoded = json.dumps(retired, sort_keys=True)
                self.assertIn("unsupported-protocol", retired["limitations"])
                self.assertIsNone(retired["dag"]["protocol_version"])
                self.assertEqual(retired["replay"],
                                 {"status": "not-replayable", "reason": "unsupported-protocol"})
                self.assertEqual(retired["capture_status"], "partial")
                self.assertNotIn("secret-prompt-value", encoded)
                self.assertNotIn("/Users/", encoded)

        current = behavior_capture.export_trial(self.make_trial(name="protocol-4", protocol=4))
        self.assertNotIn("unsupported-protocol", current["limitations"])
        self.assertEqual(current["capture_status"], "complete")
        self.assertEqual(current["dag"]["protocol_version"], 4)
        self.assertEqual(
            [row["at"] for row in current["dag"]["accepted_history"]],
            ["intake", "plan", "prepare", "step-plan", "carry-forward", "handoff"],
        )
        self.assertEqual(current["replay"]["status"], "not-replayable")

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
            "navigator_protocol_version": 4,
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
        retired = subprocess.run(
            [*command[:-1], str(self.root / "other.json"), "--case-output", str(self.root / "cases")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(retired.returncode, 2)
        self.assertIn("unrecognized arguments: --case-output", retired.stderr)
        self.assertFalse((self.root / "other.json").exists())


if __name__ == "__main__":
    unittest.main()
