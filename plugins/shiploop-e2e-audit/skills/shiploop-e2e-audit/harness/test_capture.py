#!/usr/bin/env python3
"""No-model tests for the bounded E2E subprocess capture helper."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("shiploop_e2e_capture_under_test", HERE / "capture.py")
assert SPEC and SPEC.loader
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)


class CaptureProcessTest(unittest.TestCase):
    def capture_code(
        self,
        temporary: Path,
        code: str,
        *,
        timeout: float = 3.0,
        max_log_bytes: int = 1_000_000,
        max_event_line_chars: int = 4 * 1024 * 1024,
        on_tick: object | None = None,
        should_stop: object | None = None,
        before_stop: object | None = None,
    ) -> tuple[dict[str, object], Path]:
        output = temporary / "capture"
        result = capture.capture_process(
            [sys.executable, "-c", code],
            temporary,
            output,
            timeout,
            on_tick=on_tick,
            max_log_bytes=max_log_bytes,
            should_stop=should_stop,
            max_event_line_chars=max_event_line_chars,
            before_stop=before_stop,
        )
        return result, output

    def events(self, output: Path) -> list[dict[str, object]]:
        return [
            json.loads(line)
            for line in (output / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]

    def test_interleaved_streams_and_unknown_json_event_are_recorded(self) -> None:
        code = """import sys, time
sys.stdout.write('{\\"type\\":\\"future.event\\",\\"value\\":7}\\n'); sys.stdout.flush()
time.sleep(0.02)
sys.stderr.write('diagnostic\\n'); sys.stderr.flush()
time.sleep(0.02)
sys.stdout.write('after\\n'); sys.stdout.flush()
"""
        with tempfile.TemporaryDirectory() as temporary:
            result, output = self.capture_code(Path(temporary), code)
            self.assertEqual(result["exit_code"], 0)
            self.assertIsNone(result["termination_reason"])
            self.assertNotIn("success", result)
            self.assertEqual((output / "stdout.log").read_text(encoding="utf-8"), '{"type":"future.event","value":7}\nafter\n')
            self.assertEqual((output / "stderr.log").read_text(encoding="utf-8"), "diagnostic\n")
            events = self.events(output)
            self.assertEqual({event["stream"] for event in events}, {"stdout", "stderr"})
            unknown = next(event for event in events if event["line"].startswith('{"type":"future.event"'))
            self.assertEqual(unknown["payload"], {"type": "future.event", "value": 7})
            self.assertIn("received_at", unknown)

    def test_large_stderr_without_newline_is_bounded(self) -> None:
        code = "import sys; sys.stderr.write('x' * 300000); sys.stderr.flush()"
        with tempfile.TemporaryDirectory() as temporary:
            result, output = self.capture_code(
                Path(temporary),
                code,
                max_log_bytes=4096,
                max_event_line_chars=128 * 1024,
            )
            stderr = result["streams"]["stderr"]
            self.assertEqual(result["exit_code"], 0)
            self.assertGreaterEqual(stderr["received_bytes"], 300000)
            self.assertTrue(stderr["truncated"])
            self.assertGreater(stderr["dropped_bytes"], 0)
            self.assertGreater(stderr["line_truncations"], 0)
            self.assertLessEqual((output / "stderr.log").stat().st_size, 4096)
            self.assertTrue(result["truncated"])

    def test_native_event_larger_than_legacy_limit_is_not_line_truncated(self) -> None:
        content_size = 220 * 1024
        code = f"""import json
print(json.dumps({{
    "type": "tool_call_update",
    "toolCallId": "large-native-event",
    "status": "completed",
    "rawOutput": {{"content": "x" * {content_size}}},
}}), flush=True)
"""
        with tempfile.TemporaryDirectory() as temporary:
            result, output = self.capture_code(Path(temporary), code)
            event = next(event for event in self.events(output) if event.get("payload", {}).get("type") == "tool_call_update")
        self.assertEqual(result["exit_code"], 0)
        self.assertFalse(result["truncated"])
        self.assertEqual(result["streams"]["stdout"]["line_truncations"], 0)
        self.assertEqual(event["payload"]["rawOutput"]["content"], "x" * content_size)
        self.assertEqual(
            result["capture_limits"],
            {"max_log_bytes": 1_000_000, "max_event_line_chars": 4 * 1024 * 1024},
        )

    def test_event_line_limit_must_be_a_positive_integer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for invalid in (0, -1, True, 1.5):
                with self.subTest(invalid=invalid):
                    with self.assertRaisesRegex(ValueError, "max_event_line_chars"):
                        self.capture_code(root, "print('unused')", max_event_line_chars=invalid)

    def test_split_credentials_and_utf8_are_sanitized_before_persistence(self) -> None:
        code = """import os, time
os.write(1, b'Bearer spl')
time.sleep(0.02)
os.write(1, b'it-bearer-secret\\n')
os.write(1, b'xai-spl')
time.sleep(0.02)
os.write(1, b'it-xai-secret\\n')
os.write(1, b'{\\"type\\":\\"future.event\\",\\"api_key\\":\\"super')
time.sleep(0.02)
os.write(1, b'secret\\",\\"message\\":\\"caf\\xc3')
time.sleep(0.02)
os.write(1, b'\\xa9\\"}\\n')
"""
        forbidden = ("split-bearer-secret", "split-xai-secret", "supersecret")
        with tempfile.TemporaryDirectory() as temporary:
            result, output = self.capture_code(Path(temporary), code)
            persisted = "\n".join(
                [
                    (output / "stdout.log").read_text(encoding="utf-8"),
                    (output / "stderr.log").read_text(encoding="utf-8"),
                    (output / "events.jsonl").read_text(encoding="utf-8"),
                    json.dumps(result, ensure_ascii=False),
                ]
            )
            for secret in forbidden:
                self.assertNotIn(secret, persisted)
            self.assertIn("Bearer [redacted]", persisted)
            self.assertIn("[redacted]", persisted)
            self.assertIn("café", persisted)
            unknown = next(event for event in self.events(output) if "payload" in event)
            self.assertEqual(unknown["payload"]["type"], "future.event")
            self.assertEqual(unknown["payload"]["api_key"], "[redacted]")

    def test_field_prefix_split_across_a_newline_remains_redacted(self) -> None:
        sanitizer = capture._StreamingSanitizer()
        first = sanitizer.feed('{"api_key"\n')
        second = sanitizer.feed(': "supersecret"}\n')
        persisted = first + second + sanitizer.finish()
        self.assertNotIn("supersecret", persisted)
        self.assertIn('"api_key"\n: "[redacted]"}', persisted)

    def test_raw_token_redaction_preserves_escaped_quote_across_chunk_boundaries(self) -> None:
        value = 'See "https://github.com/xai-org/example" then continue.'
        source = json.dumps(
            {"type": "tool_call_update", "rawOutput": {"content": value}},
            separators=(",", ":"),
        )
        expected = {
            "type": "tool_call_update",
            "rawOutput": {"content": 'See "https://github.com/[redacted]" then continue.'},
        }
        escaped_quote = source.index('\\"', source.index("xai-"))

        for split in (escaped_quote, escaped_quote + 1, escaped_quote + 2):
            with self.subTest(split=split):
                sanitizer = capture._StreamingSanitizer()
                persisted = sanitizer.feed(source[:split]) + sanitizer.feed(source[split:]) + sanitizer.finish()
                self.assertNotIn("xai-org/example", persisted)
                self.assertEqual(json.loads(persisted), expected)

    def test_capture_process_redacts_raw_tokens_without_invalidating_json(self) -> None:
        value = 'See "https://github.com/xai-org/example" then continue.'
        source = json.dumps(
            {"type": "tool_call_update", "rawOutput": {"content": value}},
            separators=(",", ":"),
        )
        synthetic_secret = "xai-actual-synthetic-secret"
        secret_source = json.dumps(
            {"type": "tool_call_update", "rawOutput": {"content": synthetic_secret}},
            separators=(",", ":"),
        )
        escaped_quote = source.index('\\"', source.index("xai-"))
        chunks = (
            source[: escaped_quote + 1].encode("utf-8"),
            (source[escaped_quote + 1 :] + "\n").encode("utf-8"),
            (secret_source + "\n").encode("utf-8"),
        )
        code = f"""import os, time
chunks = {chunks!r}
os.write(1, chunks[0])
time.sleep(0.02)
os.write(1, chunks[1])
time.sleep(0.02)
os.write(1, chunks[2])
"""

        with tempfile.TemporaryDirectory() as temporary:
            result, output = self.capture_code(Path(temporary), code)
            persisted = "\n".join(
                [
                    (output / "stdout.log").read_text(encoding="utf-8"),
                    (output / "stderr.log").read_text(encoding="utf-8"),
                    (output / "events.jsonl").read_text(encoding="utf-8"),
                    json.dumps(result, ensure_ascii=False),
                ]
            )
            events = self.events(output)

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["invalid_json_count"], 0)
        self.assertNotIn("xai-org/example", persisted)
        self.assertNotIn(synthetic_secret, persisted)
        self.assertEqual(
            events[0]["payload"]["rawOutput"]["content"],
            'See "https://github.com/[redacted]" then continue.',
        )
        self.assertEqual(events[1]["payload"]["rawOutput"]["content"], "[redacted]")

    def test_final_callback_event_triggers_boundary_before_process_eof(self) -> None:
        payload = {
            "type": "tool_call_update",
            "toolCallId": "final-callback",
            "status": "completed",
            "rawOutput": {"exitCode": 0},
        }
        code = f"""import json, time
print(json.dumps({payload!r}), flush=True)
time.sleep(5)
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            observed: list[dict[str, object]] = []
            output = root / "capture"

            def callback_event_seen() -> bool:
                events_path = output / "events.jsonl"
                if not events_path.exists():
                    return False
                for event in self.events(output):
                    if event.get("payload") == payload:
                        observed.append(event)
                        return True
                return False

            result, output = self.capture_code(
                root,
                code,
                timeout=2.0,
                should_stop=callback_event_seen,
            )
            self.assertEqual((output / "stdout.log").read_text(encoding="utf-8"), json.dumps(payload) + "\n")
        self.assertTrue(observed)
        self.assertEqual(result["termination_reason"], "requested_boundary")
        self.assertFalse(result["timed_out"])
        self.assertIsNone(result["capture_error"])

    def test_nonzero_exit_is_an_observation_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, _ = self.capture_code(Path(temporary), "import sys; print('failed'); sys.exit(7)")
        self.assertEqual(result["exit_code"], 7)
        self.assertIsNone(result["termination_reason"])
        self.assertFalse(result["timed_out"])
        self.assertNotIn("success", result)

    def test_timeout_terminates_the_whole_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "timeout-child-survived"
            code = f"""import os, time
marker = {str(marker)!r}
if os.fork() == 0:
    time.sleep(0.7)
    open(marker, 'w', encoding='utf-8').write('alive')
    os._exit(0)
time.sleep(5)
"""
            result, _ = self.capture_code(root, code, timeout=0.15)
            time.sleep(0.9)
            self.assertFalse(marker.exists())
        self.assertEqual(result["termination_reason"], "timeout")
        self.assertTrue(result["timed_out"])
        self.assertTrue(result["group_termination"]["term_sent"])
        self.assertEqual(result["group_termination"]["descendant_cleanup"], {"attempted": False})

    def test_requested_boundary_terminates_the_whole_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "boundary-child-survived"
            code = f"""import os, sys, time
marker = {str(marker)!r}
print('boundary-ready', flush=True)
if os.fork() == 0:
    time.sleep(0.7)
    open(marker, 'w', encoding='utf-8').write('alive')
    os._exit(0)
time.sleep(5)
"""
            calls = 0

            def reached_boundary() -> bool:
                nonlocal calls
                calls += 1
                return calls >= 3

            result, output = self.capture_code(root, code, should_stop=reached_boundary)
            time.sleep(0.9)
            self.assertFalse(marker.exists())
            self.assertIn("boundary-ready", (output / "stdout.log").read_text(encoding="utf-8"))
        self.assertGreaterEqual(calls, 3)
        self.assertEqual(result["termination_reason"], "requested_boundary")
        self.assertFalse(result["timed_out"])
        self.assertIsNone(result["capture_error"])
        self.assertTrue(result["group_termination"]["term_sent"])

    def test_parent_exit_with_pipe_holding_descendant_is_cleaned_up(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "lingering-child-survived"
            code = f"""import os, time
marker = {str(marker)!r}
if os.fork() == 0:
    time.sleep(0.7)
    open(marker, 'w', encoding='utf-8').write('alive')
    os._exit(0)
os._exit(0)
"""
            result, _ = self.capture_code(root, code, timeout=3.0)
            time.sleep(0.9)
            self.assertFalse(marker.exists())
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["termination_reason"], "descendant_pipe_holders")
        self.assertTrue(result["group_termination"]["term_sent"])

    def test_literal_argv_is_never_shell_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / "shell-was-used"
            literal = f"literal; touch {marker}"
            output = root / "capture"
            result = capture.capture_process(
                [sys.executable, "-c", "import sys; print(sys.argv[1])", literal],
                root,
                output,
                3.0,
            )
            self.assertFalse(marker.exists())
            self.assertEqual((output / "stdout.log").read_text(encoding="utf-8"), literal + "\n")
        self.assertEqual(result["exit_code"], 0)
        self.assertIn(literal, result["argv"])

    def test_tick_failure_is_retained_and_stops_safely(self) -> None:
        def bad_tick() -> None:
            raise RuntimeError("snapshot failed")

        with tempfile.TemporaryDirectory() as temporary, mock.patch.object(capture, "TICK_INTERVAL_SECONDS", 0.02):
            result, _ = self.capture_code(Path(temporary), "import time; time.sleep(5)", on_tick=bad_tick)
        self.assertEqual(result["termination_reason"], "capture_error")
        self.assertFalse(result["timed_out"])
        self.assertIsInstance(result["capture_error"], str)
        self.assertIn("on_tick", result["capture_error"])

    def test_boundary_predicate_failure_is_a_capture_error(self) -> None:
        def bad_boundary() -> bool:
            raise RuntimeError("boundary lookup failed")

        with tempfile.TemporaryDirectory() as temporary:
            result, _ = self.capture_code(
                Path(temporary),
                "import time; time.sleep(5)",
                should_stop=bad_boundary,
            )
        self.assertEqual(result["termination_reason"], "capture_error")
        self.assertFalse(result["timed_out"])
        self.assertIsInstance(result["capture_error"], str)
        self.assertIn("should_stop", result["capture_error"])


if __name__ == "__main__":
    unittest.main()
