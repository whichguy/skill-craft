"""Fast, no-model calibration for the mock-Grok ShipLoop DAG replay harness."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dag_replay  # noqa: E402
import mock_grok  # noqa: E402


class DagReplayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-e2e-dag-replay-")
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _replay(self, name: str) -> dict:
        case = deepcopy(dag_replay.synthetic_cases()[name])
        fixture = {"kind": "in-code-synthetic", "sha256": dag_replay._canonical_fixture_digest(case)}
        return dag_replay.replay_case(case, fixture=fixture, output=self.root / name)

    def test_mock_transport_binds_exact_json_payload_bytes_for_lf_and_crlf(self) -> None:
        request = {
            "schema": mock_grok.REQUEST_SCHEMA,
            "simulation_only": True,
            "callback_id": "mock-binding",
            "action_id": "nav-binding",
            "stage": "intake",
            "owner": "root",
            "command": "produce",
            "result": {"outcome": "done", "summary": "Synthetic only."},
        }
        raw = dag_replay._json_bytes(request)
        for delimiter in (b"\n", b"\r\n"):
            with self.subTest(delimiter=delimiter):
                completed = subprocess.run(
                    [sys.executable, "-u", str(HERE / "mock_grok.py")],
                    input=raw + delimiter,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=5,
                )
                self.assertEqual(0, completed.returncode, completed.stderr.decode())
                lines = [json.loads(line) for line in completed.stdout.splitlines()]
                self.assertEqual(request, lines[0]["rawInput"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), lines[1]["rawOutput"]["request_sha256"])
                self.assertIn("SIMULATION_ONLY", completed.stderr.decode())
                self.assertEqual(0, lines[-1]["modelCalls"])

    def test_mock_transport_rejects_partial_terminal_or_callback_output(self) -> None:
        partial = self.root / "partial-mock.py"
        partial.write_text(
            "import sys\n"
            "sys.stdin.buffer.readline()\n"
            "sys.stdout.buffer.write(b'{\\\"type\\\":\\\"tool_call\\\"')\n"
            "sys.stdout.buffer.flush()\n",
            encoding="utf-8",
        )
        request = {
            "schema": dag_replay.MOCK_REQUEST_SCHEMA,
            "simulation_only": True,
            "callback_id": "mock-partial",
            "action_id": "nav-partial",
            "stage": "intake",
            "owner": "root",
            "command": "produce",
            "result": {"outcome": "done", "summary": "Synthetic only."},
        }
        with patch.object(dag_replay, "MOCK_PATH", partial):
            session = dag_replay._MockSession(self.root)
            with self.assertRaisesRegex(dag_replay.DagReplayError, "complete response"):
                session.call(request)
            with self.assertRaisesRegex(dag_replay.DagReplayError, "partial or missing terminal"):
                session.close()

    def test_full_route_exercises_34_stages_and_42_callback_boundaries(self) -> None:
        report = self._replay("synthetic-full")

        self.assertTrue(report["ok"], report.get("error"))
        self.assertEqual("synthetic-apparatus-passed", report["replay_status"])
        # 34 producer callbacks plus 8 Improve completions: seven planning
        # checkpoints and the final carry-forward.
        self.assertEqual(42, len(report["events"]))
        self.assertEqual({"W1"}, set(report["final"]["completed_work_items"]))
        self.assertEqual(["intake", "discovery", "research"], [event["from"] for event in report["events"][:3]])
        for producer in report["events"][:3]:
            with self.subTest(stage=producer["from"]):
                self.assertEqual("produce", producer["command"])
                self.assertFalse(producer["active_improve"])
                self.assertNotEqual(producer["post_action_id"], producer["submitted_action_id"])
        producer, improve = report["events"][3:5]
        self.assertEqual(("spec", "produce"), (producer["from"], producer["command"]))
        self.assertTrue(producer["active_improve"])
        self.assertEqual(producer["current_action_id"], producer["submitted_action_id"])
        self.assertEqual(producer["current_action_id"], producer["post_action_id"])
        self.assertEqual(("spec", "finish-improve"), (improve["from"], improve["command"]))
        self.assertFalse(improve["active_improve"])
        self.assertNotEqual(improve["post_action_id"], improve["submitted_action_id"])
        improved = [event["from"] for event in report["events"] if event["command"] == "finish-improve"]
        self.assertEqual([
            "spec", "test-strategy", "plan", "step-plan", "test-spec", "carry-forward",
            "system-test-author", "release-plan",
        ], improved)
        self.assertEqual(0, report["model_calls"])
        self.assertEqual("not-assessed", report["product_verdict"])
        self.assertEqual("not-assessed", report["live_verdict"])
        self.assertIn("SIMULATION_ONLY", report["mock_transport"]["stderr"])
        self.assertEqual(1, report["mock_transport"]["subprocesses"])

    def test_two_work_items_preserve_queue_identity(self) -> None:
        report = self._replay("synthetic-two-work-items")

        self.assertTrue(report["ok"], report.get("error"))
        self.assertEqual(62, len(report["events"]))
        self.assertEqual(["W1", "W2"], report["final"]["completed_work_items"])
        carry_forward = [event for event in report["events"] if event["from"] == "carry-forward"]
        # Only the carry-forward that leaves no item pending parks for Improve.
        self.assertEqual(["produce", "produce", "finish-improve"], [event["command"] for event in carry_forward])
        handoff = next(
            event for event in report["events"]
            if event["from"] == "carry-forward" and event["to"] == "select-work"
        )
        self.assertEqual("W2", handoff["next_owner"])
        self.assertEqual(["W1"], handoff["completed_work_items"])

    def test_improve_and_callback_replay_guards_are_observed(self) -> None:
        report = self._replay("synthetic-improve-replay-guards")

        self.assertTrue(report["ok"], report.get("error"))
        expected = [event for event in report["events"] if event.get("expected_error_observed")]
        self.assertEqual(3, len(expected))
        self.assertIn("step awaits actual Improve", expected[0]["engine_error"])
        self.assertIn("conflicting Improve completion replay", expected[1]["engine_error"])
        self.assertIn("stale Improve parent action", expected[2]["engine_error"])
        self.assertTrue(all(event["from"] in {"spec", "test-strategy"} for event in expected))
        for command in ("duplicate-produce", "duplicate-finish-improve"):
            with self.subTest(command=command):
                duplicate = next(event for event in report["events"] if event["command"] == command)
                self.assertEqual(duplicate["pre_state_sha256"], duplicate["post_state_sha256"])

    def test_pause_blocked_cold_recovery_repeat_and_corrective_replan(self) -> None:
        expectations = {
            "synthetic-pause-blocked-cold-recovery": [],
            "synthetic-repeat": [],
            "synthetic-corrective-replan": ["W1", "W2"],
        }
        for name, completed_items in expectations.items():
            with self.subTest(name=name):
                report = self._replay(name)
                self.assertTrue(report["ok"], report.get("error"))
                if completed_items:
                    self.assertEqual(completed_items, report["final"]["completed_work_items"])
                if name == "synthetic-pause-blocked-cold-recovery":
                    cold = [event for event in report["events"] if event["command"] == "cold-load"]
                    self.assertEqual(["intake", "discovery", "spec"], [event["from"] for event in cold])
                    self.assertTrue(all(event["pre_state_sha256"] == event["post_state_sha256"] for event in cold))
                    # A producer-only block at discovery; an Improve-returned block at spec.
                    blocked = [(event["from"], event["command"]) for event in report["events"]
                               if event["command"] in {"produce", "finish-improve"}
                               and event["expected"]["status"] == "blocked"]
                    self.assertEqual([("discovery", "produce"), ("spec", "finish-improve")], blocked)
                if name == "synthetic-repeat":
                    repeated = [event for event in report["events"] if event["from"] == "step-plan"]
                    self.assertEqual("step-plan", repeated[1]["to"])
                if name == "synthetic-corrective-replan":
                    replan = next(
                        event for event in report["events"]
                        if event["from"] == "system-test" and event["to"] == "select-work"
                    )
                    self.assertEqual("W2", replan["next_owner"])
                    self.assertEqual(["W1"], replan["completed_work_items"])
                    self.assertEqual("produce", replan["command"])
                    self.assertFalse(replan["active_improve"])

    def test_stale_malformed_and_wrong_edge_controls_cannot_turn_green(self) -> None:
        guarded = self._replay("synthetic-stale-and-malformed")
        self.assertTrue(guarded["ok"], guarded.get("error"))
        self.assertEqual(2, sum("expected_error_observed" in event for event in guarded["events"]))

        wrong = self._replay("synthetic-wrong-edge-control")
        self.assertTrue(wrong["ok"], wrong.get("error"))
        self.assertTrue(wrong["expected_failure_observed"])
        self.assertEqual("synthetic-apparatus-expected-failure-observed", wrong["replay_status"])
        self.assertIn("expected edge intake -> research/active, got discovery/active", wrong["error"])

        # With the true edge the control replays green, so its expected
        # failure is missing and the report must not pass.
        missing = deepcopy(dag_replay.synthetic_cases()["synthetic-wrong-edge-control"])
        missing["id"] = "synthetic-expected-failure-missing"
        missing["steps"][0]["expect"] = "discovery"
        fixture = {"kind": "in-code-synthetic", "sha256": dag_replay._canonical_fixture_digest(missing)}
        report = dag_replay.replay_case(missing, fixture=fixture, output=self.root / "missing-negative")
        self.assertFalse(report["ok"])
        self.assertTrue(report["expected_failure_missing"])

    def test_schema_and_drift_fail_closed_and_only_synthetic_v4_cases_are_accepted(self) -> None:
        invalid = deepcopy(dag_replay.synthetic_cases()["synthetic-full"])
        invalid["steps"] = []
        with self.assertRaisesRegex(dag_replay.DagReplayError, "1..500"):
            dag_replay.validate_case(invalid)
        invalid = deepcopy(dag_replay.synthetic_cases()["synthetic-full"])
        invalid["steps"][0]["unknown"] = True
        with self.assertRaisesRegex(dag_replay.DagReplayError, "unsupported"):
            dag_replay.validate_case(invalid)

        case = deepcopy(dag_replay.synthetic_cases()["synthetic-stale-and-malformed"])
        fixture = {"kind": "in-code-synthetic", "sha256": dag_replay._canonical_fixture_digest(case)}
        stable = dag_replay._source_fingerprint(dag_replay.DEFAULT_SKILL_ROOT)
        drifted = deepcopy(stable)
        drifted["package_sha256"] = "0" * 64
        with patch.object(dag_replay, "_source_fingerprint", side_effect=[stable, stable, drifted]):
            report = dag_replay.replay_case(case, fixture=fixture, output=self.root / "drift")
        self.assertFalse(report["ok"])
        self.assertEqual("synthetic-apparatus-invalid-drift", report["replay_status"])
        self.assertTrue((self.root / "drift" / "cases" / case["id"] / "report.json").is_file())

        for field, value, message in (
            ("protocol_version", 2, "protocol_version must be 4"),
            ("protocol_version", 3, "protocol_version must be 4"),
            ("kind", "retained-trace", "kind must be synthetic"),
        ):
            with self.subTest(field=field, value=value):
                invalid = deepcopy(dag_replay.synthetic_cases()["synthetic-stale-and-malformed"])
                invalid[field] = value
                with self.assertRaisesRegex(dag_replay.DagReplayError, message):
                    dag_replay.validate_case(invalid)
        self.assertFalse((HERE / "fixtures" / "dag").exists())

    def test_same_root_source_change_after_first_replay_is_reported_without_reusing_cached_code(self) -> None:
        root_key = str(dag_replay.DEFAULT_SKILL_ROOT.resolve())
        original_pin = dag_replay._PROCESS_LOADED_PACKAGE_SHA256.get(root_key)
        try:
            dag_replay._PROCESS_LOADED_PACKAGE_SHA256.pop(root_key, None)
            first = self._replay("synthetic-stale-and-malformed")
            self.assertTrue(first["ok"], first.get("error"))
            changed = deepcopy(first["source_before"])
            changed["package_sha256"] = "f" * 64
            second = deepcopy(dag_replay.synthetic_cases()["synthetic-stale-and-malformed"])
            second["id"] = "synthetic-same-root-cache-drift"
            fixture = {"kind": "in-code-synthetic", "sha256": dag_replay._canonical_fixture_digest(second)}
            with patch.object(dag_replay, "_source_fingerprint", return_value=changed):
                report = dag_replay.replay_case(second, fixture=fixture, output=self.root / "cache-drift")
            self.assertFalse(report["ok"])
            self.assertEqual("synthetic-apparatus-invalid-drift", report["replay_status"])
            self.assertIn("differs from the source first loaded", report["error"])
            self.assertEqual(0, report["mock_transport"]["subprocesses"])
            report_path = self.root / "cache-drift" / "cases" / second["id"] / "report.json"
            self.assertTrue(report_path.is_file())
            self.assertEqual(report["error"], json.loads(report_path.read_text(encoding="utf-8"))["error"])
        finally:
            if original_pin is None:
                dag_replay._PROCESS_LOADED_PACKAGE_SHA256.pop(root_key, None)
            else:
                dag_replay._PROCESS_LOADED_PACKAGE_SHA256[root_key] = original_pin

    def test_public_cli_replays_a_case_file_to_new_external_output(self) -> None:
        case = dag_replay.synthetic_cases()["synthetic-stale-and-malformed"]
        case_path = self.root / "case.json"
        case_path.write_text(json.dumps(case), encoding="utf-8")
        output = self.root / "cli-output"
        completed = subprocess.run(
            [sys.executable, "-B", str(HERE / "dag_replay.py"), "--case", str(case_path), "--output", str(output),
             "--skill-root", str(dag_replay.DEFAULT_SKILL_ROOT)],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        receipt = json.loads((output / "result.json").read_text(encoding="utf-8"))
        self.assertEqual("synthetic-apparatus-passed", receipt["status"])
        self.assertEqual(0, receipt["model_calls"])
        self.assertEqual([case["id"]], [report["id"] for report in receipt["reports"]])
        self.assertEqual(str(dag_replay.DEFAULT_SKILL_ROOT.resolve()), receipt["selected_subject"]["root"])

    def test_cursor_invariant_parks_only_at_literal_checkpoints(self) -> None:
        navigator = SimpleNamespace(
            current_action=lambda state: state["action"],
            current_stage=lambda state: state["stage"],
        )

        def state(stage: str, action: str, *, child: dict | None = None, work_index: int = 0) -> dict:
            return {
                "navigator_protocol_version": 4, "stage": stage, "action": {"id": action},
                "active_improve": child, "accepted": {}, "work_index": work_index,
                "work_items": [{"id": "W1"}, {"id": "W2"}],
            }

        def parked(stage: str, action: str, **extra) -> dict:
            return state(stage, action, child={"action_id": action, "stage": stage}, **extra)

        done = {"outcome": "done", "summary": "Synthetic."}
        check = dag_replay._assert_cursor_invariants
        # (b) A non-checkpoint producer advances with no child.
        check(navigator, state("intake", "a1"), state("discovery", "a2"), "produce", "a1", done)
        # A checkpoint producer parks its own action.
        check(navigator, state("spec", "a1"), parked("spec", "a1"), "produce", "a1", done)
        # A carry-forward that leaves a later item pending advances directly.
        check(navigator, state("carry-forward", "a1"), state("select-work", "a2", work_index=1),
              "produce", "a1", done)
        failures = (
            # (a) A checkpoint producer that advanced with no child.
            ("replaced the parent action", state("spec", "a1"), state("test-strategy", "a2"), done),
            # (c) A non-checkpoint producer that parked a child.
            ("parked Improve outside a checkpoint", state("intake", "a1"), parked("intake", "a1"), done),
            # (d) The last carry-forward that advanced with no child.
            ("replaced the parent action", state("carry-forward", "a1", work_index=1),
             state("system-test-author", "a2"), done),
            # Emptying the future queue also makes this carry-forward the last one.
            ("replaced the parent action", state("carry-forward", "a1"),
             state("system-test-author", "a2"), {**done, "work_items": []}),
            ("did not accept its result", state("intake", "a1"), state("intake", "a1"), done),
        )
        for index, (message, before, after, result) in enumerate(failures):
            with self.subTest(case=index, message=message):
                with self.assertRaisesRegex(dag_replay.DagReplayError, message):
                    check(navigator, before, after, "produce", "a1", result)

    def test_public_cli_rejects_output_inside_selected_subject(self) -> None:
        output = dag_replay.DEFAULT_SKILL_ROOT / "forbidden-e2e-output"
        completed = subprocess.run(
            [sys.executable, "-B", str(HERE / "dag_replay.py"), "--output", str(output),
             "--skill-root", str(dag_replay.DEFAULT_SKILL_ROOT)],
            capture_output=True, text=True, check=False, timeout=10,
        )
        self.assertEqual(2, completed.returncode)
        self.assertIn("outside the audit package", completed.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
