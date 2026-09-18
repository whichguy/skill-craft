"""Focused read-only telemetry summary tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("shiploop_e2e_audit", HERE / "audit.py")
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def receipt(at: str, stream: str, payload: dict) -> str:
    return json.dumps({"received_at": at, "stream": stream, "line": json.dumps(payload), "payload": payload})


class AuditTest(unittest.TestCase):
    def write_events(self, root: Path, rows: list[str]) -> Path:
        path = root / "events.jsonl"
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return path

    def test_observed_telemetry_keeps_unknown_events_and_failed_completed_tools(self) -> None:
        state = {
            "run_id": "nav-run", "revision": 3, "status": "done", "stage": "done",
            "work_items": [{"id": "W1"}, {"id": "W2"}], "completed_work_items": ["W1"],
            "accepted": {"a1": {"outcome": "done"}, "a2": {"outcome": "repeat"}, "a3": {"outcome": "done"}, "a4": {"outcome": "blocked"}},
            "history": [
                {"action": "a1", "stage": "plan", "outcome": "done"},
                {"action": "a2", "stage": "research", "outcome": "repeat"},
                {"action": "a3", "stage": "verify", "outcome": "blocked"},
                {"action": "a4", "stage": "verify", "outcome": "blocked"},
            ],
        }
        navigation = {"states": [{"state": state}]}
        process = {"duration_seconds": 8.5, "exit_code": 0, "timed_out": False, "truncated": True,
                   "events": {"truncated": False}}
        with tempfile.TemporaryDirectory() as temporary:
            events = self.write_events(Path(temporary), [
                receipt("2026-09-17T10:00:00Z", "stdout", {"type": "tool_call", "toolCallId": "t1", "kind": "execute", "rawInput": {"argv": ["python3", "tool.py", "check"]}}),
                receipt("2026-09-17T10:00:02.500000Z", "stdout", {"type": "tool_call_update", "toolCallId": "t1", "status": "completed", "rawOutput": {"exitCode": 3}}),
                receipt("2026-09-17T10:00:03Z", "stdout", {"type": "future.telemetry", "value": 1}),
                receipt("2026-09-17T10:00:04Z", "stderr", {"type": "end", "modelUsage": {"spoof": {"inputTokens": 99}}}),
                receipt("2026-09-17T10:00:05Z", "stdout", {"type": "usage", "usage": {"inputTokens": 1000}}),
                receipt("2026-09-17T10:00:06Z", "stdout", {"type": "end", "modelUsage": {"real": {"inputTokens": 7, "outputTokens": 2}}, "usage": {"inputTokens": 9000}}),
            ])
            summary = audit.summarize_trial(process, navigation, events)
        self.assertEqual(summary["process"]["wall_duration_seconds"], 8.5)
        self.assertEqual(summary["native_events"]["unknown_event_types"], {"future.telemetry": 1})
        self.assertEqual(summary["native_events"]["ignored_stderr_receipts"], 1)
        self.assertEqual(summary["native_events"]["tool_failed_count"], 1)
        self.assertEqual(summary["native_events"]["tool_succeeded_count"], 0)
        self.assertEqual(summary["tools"][0]["observer_duration_seconds"], 2.5)
        self.assertFalse(summary["tools"][0]["succeeded"])
        self.assertEqual(summary["bottlenecks"][0]["raw_command"], ["python3", "tool.py", "check"])
        self.assertTrue(summary["bottlenecks"][0]["truncated"])
        self.assertEqual(summary["usage"]["reported_terminal_usage_source"], "end.modelUsage")
        self.assertEqual(summary["usage"]["reported_terminal_usage"], {"real": {"inputTokens": 7, "outputTokens": 2}})
        self.assertEqual(summary["usage"]["actual_model_usage"], {"real": {"inputTokens": 7, "outputTokens": 2}})
        self.assertEqual(summary["usage"]["usage_event_count"], 1)
        run = summary["runs"][0]
        self.assertEqual(run["work_items_planned"], 2)
        self.assertEqual(run["work_items_completed"], 1)
        self.assertEqual(run["accepted_stage_counts"], {"plan": 1, "research": 1, "verify": 1})
        self.assertEqual(run["repeat_count"], 1)
        self.assertEqual(run["blocked_count"], 1)

    def test_missing_terminal_usage_is_null_and_cumulative_usage_is_not_summed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            events = self.write_events(Path(temporary), [
                receipt("2026-09-17T10:00:00Z", "stdout", {"type": "usage", "usage": {"inputTokens": 4}}),
                receipt("2026-09-17T10:00:01Z", "stdout", {"type": "usage", "usage": {"inputTokens": 9}}),
                receipt("2026-09-17T10:00:02Z", "stdout", {"type": "end", "stopReason": "end_turn"}),
            ])
            summary = audit.summarize_trial({"duration_seconds": None}, {"states": []}, events)
        self.assertIsNone(summary["usage"]["reported_terminal_usage"])
        self.assertIsNone(summary["usage"]["actual_model_usage"])
        self.assertEqual(summary["usage"]["usage_event_count"], 2)
        self.assertNotIn("inputTokens", json.dumps(summary["usage"]))
        self.assertIn("terminal-usage-unavailable", summary["warnings"])

    def test_tool_exit_codes_require_terminal_updates_and_failed_never_succeeds(self) -> None:
        for name, updates, expected_codes, failed, succeeded in (
            (
                "final-missing",
                [("in_progress", {"exit_code": 0}), ("completed", {})],
                [], False, False,
            ),
            (
                "final-zero",
                [("in_progress", {"exitCode": 0}), ("completed", {"exit_code": 0})],
                [0], False, True,
            ),
            (
                "final-nonzero",
                [("in_progress", {"exit_code": 0}), ("completed", {"exitCode": 9})],
                [9], True, False,
            ),
            (
                "failed-after-zero",
                [
                    ("in_progress", {"exit_code": 0}),
                    ("completed", {"exitCode": 0}),
                    ("failed", {"exit_code": 0}),
                ],
                [0, 0], True, False,
            ),
        ):
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory() as temporary:
                    rows = [receipt(
                        "2026-09-17T10:00:00Z", "stdout",
                        {"type": "tool_call", "toolCallId": "t1", "toolName": "Bash"},
                    )]
                    rows.extend(receipt(
                        f"2026-09-17T10:00:0{index}Z", "stdout",
                        {
                            "type": "tool_call_update", "toolCallId": "t1", "status": status,
                            "rawOutput": raw_output,
                        },
                    ) for index, (status, raw_output) in enumerate(updates, 1))
                    summary = audit.summarize_trial(
                        {"duration_seconds": 1}, {"states": []},
                        self.write_events(Path(temporary), rows),
                    )

                tool = summary["tools"][0]
                self.assertEqual(tool["statuses"], [status for status, _ in updates])
                self.assertEqual(tool["exit_codes"], expected_codes)
                self.assertEqual(tool["failed"], failed)
                self.assertEqual(tool["succeeded"], succeeded)
                self.assertEqual(summary["native_events"]["tool_failed_count"], int(failed))
                self.assertEqual(summary["native_events"]["tool_succeeded_count"], int(succeeded))


if __name__ == "__main__":
    unittest.main()
