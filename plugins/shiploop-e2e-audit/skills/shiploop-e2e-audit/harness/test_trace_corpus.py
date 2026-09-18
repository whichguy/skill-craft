"""Sanitized golden host-command shapes retained from live Grok captures.

The fixtures intentionally preserve only hashes, call IDs, and a reduced shell
shape.  They do not contain prompts, product content, absolute user paths, or
raw host transcripts.  They exercise the current observer without starting a
model or consulting the retained captures at test time.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from grok_adapter import summarize_events  # noqa: E402


FIXTURES = HERE / "fixtures" / "host"
CLI_TOKEN = "__SELECTED_CLI__"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_CASE_IDS = {
    "checkers-nested-heredoc-plan-callback-unattributed",
    "checkers-supported-python-heredoc-terminal-callback",
    "synthetic-failed-callback-followed-by-exit-zero",
    "ttt-dynamic-start-prelude-unattributed",
    "ttt-literal-standalone-complete",
}


class HostTraceCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-e2e-trace-corpus-")
        self.root = Path(self.temporary.name)
        self.skill_root = self.root / "shiploop"
        (self.skill_root / "scripts").mkdir(parents=True)
        self.selected_cli = self.skill_root / "scripts" / "shiploop"
        self.selected_cli.write_text("#!/bin/sh\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def fixtures(self) -> list[tuple[Path, dict[str, object]]]:
        cases = []
        for path in sorted(FIXTURES.glob("*.json")):
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsInstance(value, dict, path)
            cases.append((path, value))
        return cases

    def materialized_events(self, fixture: dict[str, object]) -> list[dict[str, object]]:
        encoded = json.dumps(fixture["events"])
        self.assertIn(CLI_TOKEN, encoded)
        materialized = json.loads(encoded.replace(CLI_TOKEN, str(self.selected_cli)))
        self.assertIsInstance(materialized, list)
        self.assertTrue(all(isinstance(event, dict) for event in materialized))
        return materialized

    def summary(self, fixture: dict[str, object], fixture_path: Path) -> dict[str, object]:
        events = self.materialized_events(fixture)
        events_path = self.root / f"{fixture_path.stem}.jsonl"
        events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
        return summarize_events(events_path, self.selected_cli)

    def test_corpus_is_complete_sanitized_and_bound_to_this_parser_source(self) -> None:
        cases = self.fixtures()
        self.assertEqual({case["id"] for _path, case in cases}, EXPECTED_CASE_IDS)
        parser_sha256 = hashlib.sha256((HERE / "grok_adapter.py").read_bytes()).hexdigest()

        for path, case in cases:
            with self.subTest(fixture=path.name):
                self.assertEqual(case["schema"], "shiploop-e2e-host-command-shape/v1")
                self.assertEqual(case["observer"]["grok_adapter_sha256"], parser_sha256)
                self.assertEqual(
                    case["observer"]["source_edit_policy"],
                    "parser-source-mismatch-invalidates-attribution",
                )
                self.assertEqual(case["sanitization"]["selected_cli_token"], CLI_TOKEN)
                self.assertTrue(case["sanitization"]["absolute_paths_replaced"])
                self.assertTrue(case["sanitization"]["prompts_removed"])
                self.assertTrue(case["sanitization"]["heredoc_bodies_reduced"])
                self.assertFalse(case["sanitization"]["raw_transcript_stored"])
                self.assertNotIn("/Users/", path.read_text(encoding="utf-8"))

                provenance = case["provenance"]
                if provenance["kind"] == "retained-trace":
                    self.assertRegex(provenance["capture_sha256"], SHA256)
                    self.assertRegex(provenance["tool_call"]["sha256"], SHA256)
                    self.assertRegex(provenance["completed_update"]["sha256"], SHA256)
                    self.assertEqual(provenance["tool_call"]["call_id"], case["events"][0]["toolCallId"])
                    self.assertEqual(provenance["completed_update"]["status"], "completed")
                    self.assertEqual(provenance["completed_update"]["exit_code"], 0)
                    self.assertEqual(provenance["hash_basis"]["capture_sha256"], "full events.jsonl byte stream")
                    self.assertEqual(
                        provenance["hash_basis"]["tool_call_and_completed_update_sha256"],
                        "UTF-8 source JSONL line without its terminal newline",
                    )
                    self.assertIsInstance(provenance["shape"]["reduced_shape"], str)
                else:
                    self.assertEqual(provenance["kind"], "synthetic-mutant")
                    self.assertEqual(provenance["base_fixture_id"], "ttt-literal-standalone-complete")
                    self.assertRegex(provenance["base_capture_sha256"], SHA256)
                    self.assertRegex(provenance["base_tool_call"]["sha256"], SHA256)
                    self.assertEqual(provenance["base_hash_basis"]["base_capture_sha256"], "full events.jsonl byte stream")
                    self.assertIn("not observed", provenance["mutation"])

    def test_golden_shapes_preserve_attribution_boundaries(self) -> None:
        for path, fixture in self.fixtures():
            with self.subTest(fixture=path.name):
                events = self.materialized_events(fixture)
                summary = self.summary(fixture, path)
                expectation = fixture["expectation"]
                expected_call_id = events[0]["toolCallId"]

                if expectation["attribution"] == "observed":
                    self.assertEqual(len(summary["cli_calls"]), 1)
                    call = summary["cli_calls"][0]
                    self.assertEqual(call["call_id"], expected_call_id)
                    self.assertEqual(call["argv_tail"], expectation["argv_tail"])
                    self.assertEqual(call["completed"], expectation["completed"])
                    self.assertEqual(call["exit_codes"], expectation["exit_codes"])
                    self.assertTrue(summary["shiploop_cli_completed"])
                    self.assertEqual(summary["shiploop_cli_success_observed"], expectation["success_observed"])
                    continue

                self.assertEqual(expectation["attribution"], "unknown")
                update = events[-1]
                self.assertEqual(update["type"], "tool_call_update")
                self.assertEqual(update["status"], "completed")
                self.assertEqual(update["rawOutput"]["exitCode"], 0)
                self.assertEqual(summary["cli_calls"], [])
                self.assertFalse(summary["cli_invocation_observed"])
                self.assertFalse(summary["shiploop_cli_completed"])
                self.assertFalse(summary["shiploop_cli_success_observed"])
                self.assertFalse(expectation["success_observed"])


if __name__ == "__main__":
    unittest.main()
