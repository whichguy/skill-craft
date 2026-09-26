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

    def test_supported_field_spellings_split_across_newline_remain_redacted(self) -> None:
        names = (
            "api-key", "api_key", "apikey",
            "secret", "secret-key", "secret_key", "secretkey",
            "password", "passwd", "token",
            "access-token", "access_token", "accessToken",
            "refresh-token", "refresh_token", "refreshToken",
            "client-secret", "client_secret", "clientSecret",
            "private-key", "private_key", "privateKey",
            "auth", "authorization", "credential", "key",
        )
        for name in names:
            with self.subTest(name=name):
                value = f"synthetic-{name}"
                sanitizer = capture._StreamingSanitizer()
                persisted = (
                    sanitizer.feed("{" + json.dumps(name) + "\n")
                    + sanitizer.feed(f': {json.dumps(value)}}}\n')
                    + sanitizer.finish()
                )
                self.assertNotIn(value, persisted)
                self.assertEqual(json.loads(persisted), {name: "[redacted]"})

    def test_multiline_field_colon_and_leading_space_value_remain_redacted(self) -> None:
        value = " synthetic-multiline-access"
        source = '{"pad":"' + "x" * 300 + '","access-token"\n:\n' + json.dumps(value) + "}"
        expected = {"pad": "x" * 300, "access-token": "[redacted]"}

        for split in range(len(source) + 1):
            with self.subTest(split=split):
                sanitizer = capture._StreamingSanitizer()
                persisted = (
                    sanitizer.feed(source[:split])
                    + sanitizer.feed(source[split:])
                    + sanitizer.finish()
                )
                self.assertNotIn(value, persisted)
                self.assertEqual(json.loads(persisted), expected)

    def test_field_state_handles_long_whitespace_and_escaped_serialization(self) -> None:
        value = " synthetic-spaced-value"
        before_separator = " " * 1_000 + "\n\t"
        before_value = "\t\n" + " " * 1_000
        source = '{"accessToken"' + before_separator + ":" + before_value + json.dumps(value) + "}"
        expected = {"accessToken": "[redacted]"}
        colon = source.index(":")

        for chunks in (
            [source[index : index + 257] for index in range(0, len(source), 257)],
            [source[: colon + 1], source[colon + 1 :]],
        ):
            sanitizer = capture._StreamingSanitizer()
            persisted = "".join(sanitizer.feed(chunk) for chunk in chunks) + sanitizer.finish()
            self.assertNotIn(value, persisted)
            self.assertEqual(json.loads(persisted), expected)

        inner = '{"accessToken"' + " " * 300 + ": " + json.dumps(value) + "}"
        escaped_source = json.dumps({"content": inner})
        sanitizer = capture._StreamingSanitizer()
        escaped_persisted = "".join(
            sanitizer.feed(escaped_source[index : index + 257])
            for index in range(0, len(escaped_source), 257)
        ) + sanitizer.finish()
        self.assertNotIn(value, escaped_persisted)
        self.assertEqual(
            json.loads(escaped_persisted),
            {"content": '{"accessToken"' + " " * 300 + ': "[redacted]"}'},
        )

        prose = '"token"' + before_separator + "ordinary prose"
        sanitizer = capture._StreamingSanitizer()
        persisted_prose = "".join(
            sanitizer.feed(prose[index : index + 257])
            for index in range(0, len(prose), 257)
        ) + sanitizer.finish()
        self.assertEqual(persisted_prose, prose)

    def test_field_state_redacts_value_forms_at_every_serialization_depth(self) -> None:
        values = (
            ("empty", ""),
            ("backslash", r"\synthetic-backslash"),
            ("escaped_quote", 'synthetic " quote'),
            ("newline", "synthetic\nnewline"),
        )
        expected_inner = {"nonsecret": "preserved", "accessToken": "[redacted]"}
        for name, value in values:
            for depth in range(3):
                inner = (
                    '{"nonsecret":"preserved","accessToken"'
                    + " " * 300
                    + ": "
                    + json.dumps(value)
                    + "}"
                )
                source = inner
                for _ in range(depth):
                    source = json.dumps({"content": source})
                sanitizer = capture._StreamingSanitizer()
                persisted = "".join(sanitizer.feed(character) for character in source) + sanitizer.finish()
                with self.subTest(value=name, depth=depth):
                    if value:
                        self.assertNotIn(value, persisted)
                    payload: object = json.loads(persisted)
                    for _ in range(depth):
                        self.assertIsInstance(payload, dict)
                        payload = json.loads(payload["content"])
                    self.assertEqual(payload, expected_inner)

    def test_normal_flush_preserves_left_boundaries_for_tokens_and_fields(self) -> None:
        def after_flush(prefix: str, suffix: str, split: int) -> str:
            sanitizer = capture._StreamingSanitizer()
            output: list[str] = []
            sanitizer._emit(output, prefix)
            return (
                "".join(output)
                + sanitizer.feed(suffix[:split])
                + sanitizer.feed(suffix[split:])
                + sanitizer.finish()
            )

        for prefix_length in (256, 257, 16 * 1024):
            command_prefix = "a" * (prefix_length + 1)
            for command in ("sk-codex", "sk-astra"):
                prefix = '{"available_commands":["' + command_prefix
                suffix = command + '"]}'
                source = prefix + suffix
                for split in range(len(suffix) + 1):
                    with self.subTest(prefix_length=prefix_length, command=command, split=split):
                        self.assertEqual(after_flush(prefix, suffix, split), source)
            prefix = command_prefix
            suffix = 'accessToken: "ordinary-value"'
            for split in range(len(suffix) + 1):
                with self.subTest(prefix_length=prefix_length, field_split=split):
                    self.assertEqual(after_flush(prefix, suffix, split), prefix + suffix)

        sanitizer = capture._StreamingSanitizer()
        self.assertEqual(sanitizer.feed("sk-synthetic") + sanitizer.finish(), "[redacted]")

    def test_escaped_json_credential_fields_are_redacted_at_every_chunk_boundary(self) -> None:
        source = json.dumps({
            "content": '{"accessToken":"synthetic-access", "refreshToken":"synthetic-refresh"}',
        })
        expected = {
            "content": '{"accessToken":"[redacted]", "refreshToken":"[redacted]"}',
        }

        for split in range(len(source) + 1):
            with self.subTest(split=split):
                sanitizer = capture._StreamingSanitizer()
                persisted = (
                    sanitizer.feed(source[:split])
                    + sanitizer.feed(source[split:])
                    + sanitizer.finish()
                )
                self.assertNotIn("synthetic-access", persisted)
                self.assertNotIn("synthetic-refresh", persisted)
                self.assertEqual(json.loads(persisted), expected)

    def test_escaped_json_fields_cover_every_supported_credential_key(self) -> None:
        names = sorted(capture._FIELD_NAMES | {
            "accessToken",
            "refreshToken",
            "apiKey",
            "clientSecret",
            "privateKey",
            "ACCESS_TOKEN",
            "Refresh-Token",
        })
        source = json.dumps({
            "content": json.dumps({name: f"synthetic-{index}" for index, name in enumerate(names)}),
        })
        expected = {name: "[redacted]" for name in names}

        sanitizer = capture._StreamingSanitizer()
        persisted = "".join(
            sanitizer.feed(source[index : index + 1]) for index in range(len(source))
        ) + sanitizer.finish()
        for index in range(len(names)):
            self.assertNotIn(f"synthetic-{index}", persisted)
        self.assertEqual(json.loads(json.loads(persisted)["content"]), expected)

    def test_quoted_field_value_split_after_colon_and_space_remains_redacted(self) -> None:
        source = json.dumps({
            "accessToken": "synthetic-access",
            "refreshToken": "synthetic-refresh",
        })
        quote = source.index('"', source.index(":") + 1)

        for split in (quote, quote + 1):
            with self.subTest(split=split):
                sanitizer = capture._StreamingSanitizer()
                persisted = (
                    sanitizer.feed(source[:split])
                    + sanitizer.feed(source[split:])
                    + sanitizer.finish()
                )
                self.assertNotIn("synthetic-access", persisted)
                self.assertNotIn("synthetic-refresh", persisted)
                self.assertEqual(
                    json.loads(persisted),
                    {"accessToken": "[redacted]", "refreshToken": "[redacted]"},
                )

    def test_quoted_credential_values_with_leading_spaces_remain_redacted(self) -> None:
        value = {
            "accessToken": " synthetic-leading-access",
            "refreshToken": " synthetic-leading-refresh",
        }
        expected = {name: "[redacted]" for name in value}
        sources = (
            (json.dumps(value), expected),
            (
                json.dumps({"rawOutput": {"output": list(json.dumps(value).encode("utf-8"))}}),
                {"rawOutput": {"output": list(json.dumps(expected).encode("utf-8"))}},
            ),
        )
        for source, expected_payload in sources:
            for split in range(len(source) + 1):
                with self.subTest(byte_transport="rawOutput" in source, split=split):
                    sanitizer = capture._StreamingSanitizer()
                    persisted = (
                        sanitizer.feed(source[:split])
                        + sanitizer.feed(source[split:])
                        + sanitizer.finish()
                    )
                    self.assertNotIn(value["accessToken"], persisted)
                    self.assertNotIn(value["refreshToken"], persisted)
                    self.assertEqual(json.loads(persisted), expected_payload)

    def test_nested_escaped_json_credential_fields_are_redacted_at_every_chunk_boundary(self) -> None:
        nested = json.dumps({
            "output_for_prompt": json.dumps({
                "accessToken": "synthetic-access",
                "refreshToken": "synthetic-refresh",
            }),
        })
        source = json.dumps({"content": nested})
        expected = {
            "output_for_prompt": json.dumps({
                "accessToken": "[redacted]",
                "refreshToken": "[redacted]",
            }),
        }

        for split in range(len(source) + 1):
            with self.subTest(split=split):
                sanitizer = capture._StreamingSanitizer()
                persisted = (
                    sanitizer.feed(source[:split])
                    + sanitizer.feed(source[split:])
                    + sanitizer.finish()
                )
                self.assertNotIn("synthetic-access", persisted)
                self.assertNotIn("synthetic-refresh", persisted)
                content = json.loads(persisted)["content"]
                self.assertEqual(json.loads(content), expected)

    def test_escaped_json_credential_values_can_contain_escapes_and_newlines(self) -> None:
        source = json.dumps({
            "content": (
                '{"accessToken":"synthetic-access\\nwith an \\"escaped\\" quote", '
                '"refreshToken":"synthetic-refresh\\nsecond line"}'
            ),
        })
        expected = {
            "content": '{"accessToken":"[redacted]", "refreshToken":"[redacted]"}',
        }

        sanitizer = capture._StreamingSanitizer()
        persisted = "".join(
            sanitizer.feed(source[index : index + 1]) for index in range(len(source))
        ) + sanitizer.finish()
        self.assertNotIn("synthetic-access", persisted)
        self.assertNotIn("synthetic-refresh", persisted)
        self.assertEqual(json.loads(persisted), expected)

    def test_grok_byte_array_transports_are_removed_before_persistence(self) -> None:
        embedded = json.dumps({
            "accessToken": "synthetic-access",
            "refreshToken": "synthetic-refresh",
        })
        encoded = list(embedded.encode("utf-8"))
        file_content = json.dumps({"content": embedded, "output": [79, 75]})
        source = json.dumps(
            {
                "type": "tool_call_update",
                "rawOutput": {
                    "content": embedded,
                    "output": encoded,
                    "stdout": [79, 75],
                    "stderr": [1, 2],
                    "exitCode": 0,
                },
                "FileContent": file_content,
            },
            indent=2,
        )
        expected_embedded = {
            "accessToken": "[redacted]",
            "refreshToken": "[redacted]",
        }
        expected_encoded = list(json.dumps(expected_embedded).encode("utf-8"))

        sanitizer = capture._StreamingSanitizer()
        persisted = "".join(
            sanitizer.feed(source[index : index + 1]) for index in range(len(source))
        ) + sanitizer.finish()
        payload = json.loads(persisted)
        self.assertNotIn("synthetic-access", persisted)
        self.assertNotIn("synthetic-refresh", persisted)
        self.assertEqual(json.loads(payload["rawOutput"]["content"]), expected_embedded)
        self.assertEqual(payload["rawOutput"]["output"], expected_encoded)
        self.assertEqual(payload["rawOutput"]["stdout"], [79, 75])
        self.assertEqual(payload["rawOutput"]["stderr"], [1, 2])
        self.assertEqual(payload["rawOutput"]["exitCode"], 0)
        nested = json.loads(payload["FileContent"])
        self.assertEqual(json.loads(nested["content"]), expected_embedded)
        self.assertEqual(nested["output"], [79, 75])

    def test_unclosed_grok_byte_array_is_discarded_without_retaining_its_values(self) -> None:
        encoded = list(b'{"accessToken":"synthetic-access"}')
        source = '{"rawOutput": {"output": ' + json.dumps(encoded)[:-1]
        sanitizer = capture._StreamingSanitizer()
        persisted = "".join(
            sanitizer.feed(source[index : index + 1]) for index in range(len(source))
        ) + sanitizer.finish()
        self.assertNotIn(json.dumps(encoded), persisted)
        self.assertNotIn("synthetic-access", persisted)

    def test_arrays_outside_raw_output_are_preserved(self) -> None:
        source = json.dumps({
            "type": "future.event",
            "rawOutput": {"stdout": [79, 75]},
            "output": [1, 2],
            "metrics": {"stdout": [3, 4], "stderr": [5, 6], "bytes": [7, 8]},
        })
        sanitizer = capture._StreamingSanitizer()
        persisted = sanitizer.feed(source) + sanitizer.finish()
        self.assertEqual(json.loads(persisted), json.loads(source))

    def test_raw_output_byte_array_preserves_multibyte_and_non_utf8_values(self) -> None:
        raw = "café".encode("utf-8") + b"\xff"
        source = json.dumps({"rawOutput": {"stdout": list(raw)}})
        sanitizer = capture._StreamingSanitizer()
        persisted = "".join(
            sanitizer.feed(source[index : index + 1]) for index in range(len(source))
        ) + sanitizer.finish()
        self.assertEqual(json.loads(persisted)["rawOutput"]["stdout"], list(raw))

    def test_invalid_raw_output_byte_array_marks_capture_incomplete(self) -> None:
        source = json.dumps({"rawOutput": {"output": [9999]}})
        code = f"import sys; sys.stdout.write({source!r} + '\\n'); sys.stdout.flush()"

        with tempfile.TemporaryDirectory() as temporary:
            result, output = self.capture_code(Path(temporary), code)
            payload = self.events(output)[0]["payload"]

        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(result["truncated"])
        self.assertEqual(result["invalid_byte_arrays"], 1)
        self.assertEqual(payload, {"rawOutput": {"output": []}})

    def test_capture_process_redacts_escaped_json_credentials_from_byte_chunks(self) -> None:
        embedded = '{"accessToken":"synthetic-access", "refreshToken":"synthetic-refresh"}'
        encoded = list(embedded.encode("utf-8"))
        source = json.dumps({
            "type": "tool_call_update",
            "rawOutput": {"content": embedded, "output": encoded, "exitCode": 0},
            "FileContent": embedded,
        })
        split = source.index("synthetic-access") + len("synthetic-access") // 2
        chunks = (source[:split].encode("utf-8"), (source[split:] + "\n").encode("utf-8"))
        code = f"""import os, time
chunks = {chunks!r}
os.write(1, chunks[0])
time.sleep(0.02)
os.write(1, chunks[1])
"""

        with tempfile.TemporaryDirectory() as temporary:
            result, output = self.capture_code(Path(temporary), code)
            persisted = "\n".join(
                [
                    (output / "stdout.log").read_text(encoding="utf-8"),
                    (output / "events.jsonl").read_text(encoding="utf-8"),
                    json.dumps(result, ensure_ascii=False),
                ]
            )
            events = self.events(output)

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["invalid_json_count"], 0)
        self.assertFalse(result["truncated"])
        self.assertEqual(result["redacted_byte_arrays"], 1)
        self.assertEqual(result["streams"]["stdout"]["redacted_byte_arrays"], 1)
        self.assertNotIn("synthetic-access", persisted)
        self.assertNotIn("synthetic-refresh", persisted)
        self.assertEqual(
            events[0]["payload"],
            {
                "type": "tool_call_update",
                "rawOutput": {
                    "content": '{"accessToken":"[redacted]", "refreshToken":"[redacted]"}',
                    "output": list(
                        b'{"accessToken":"[redacted]", "refreshToken":"[redacted]"}'
                    ),
                    "exitCode": 0,
                },
                "FileContent": '{"accessToken":"[redacted]", "refreshToken":"[redacted]"}',
            },
        )

    def test_line_limit_cannot_retain_a_grok_byte_array_prefix(self) -> None:
        embedded = '{"accessToken":"synthetic-access", "refreshToken":"synthetic-refresh"}'
        encoded = list(embedded.encode("utf-8"))
        source = json.dumps({
            "type": "tool_call_update",
            "rawOutput": {"output": encoded, "exitCode": 0},
            "FileContent": embedded,
            "after": "x" * 512,
        })
        code = f"import sys; sys.stdout.write({source!r} + '\\n'); sys.stdout.flush()"
        line_limit = source.index('"FileContent"')

        with tempfile.TemporaryDirectory() as temporary:
            result, output = self.capture_code(
                Path(temporary), code, max_event_line_chars=line_limit,
            )
            event = self.events(output)[0]
            stdout = (output / "stdout.log").read_text(encoding="utf-8")

        self.assertEqual(result["exit_code"], 0)
        self.assertTrue(event["line_truncated"])
        self.assertNotIn(json.dumps(encoded), event["line"])
        self.assertNotIn(json.dumps(encoded), stdout)

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
