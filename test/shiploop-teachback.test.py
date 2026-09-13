#!/usr/bin/env python3
"""Hermetic tests of the teach-back probe, not tests of model comprehension."""

import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch


PROBE = runpy.run_path(str(Path(__file__).with_name("shiploop-teachback.py")))


class TeachBackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="shiploop-teachback-test-")
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.export = Path(cls.tmp.name) / "cases"
        PROBE["prepare"](cls.export)
        cls.root = cls.export / "evaluator"

    def answer(self, case="review"):
        answer = json.loads((self.root / case / "oracle.json").read_text())["expected"]
        # Deliberately meaningless text: mechanics must never call this a PASS.
        answer.update({key: "UNREVIEWED" for key in PROBE["NARRATIVE"]})
        answer.update({key: ["UNREVIEWED"] for key in PROBE["LISTS"]})
        return answer

    def test_real_captures_separate_oracle_and_preserve_current_action_boundaries(self):
        self.assertEqual({p.name for p in (self.export / "prompts").iterdir()},
                         {"review.md", "plan.md", "paused.md"})
        for name, stage in (("review", "objective-review"), ("plan", "objective-plan"), ("paused", "objective-plan")):
            with self.subTest(case=name):
                folder = self.root / name
                prompt = (self.export / "prompts" / f"{name}.md").read_text()
                expected = json.loads((folder / "oracle.json").read_text())["expected"]
                self.assertEqual(expected["stage"], stage)
                self.assertIn("Use no tools", prompt)
                self.assertNotIn("Held-out teach-back rubric", prompt)
                self.assertNotIn("UNREVIEWED", prompt)
                if name == "paused":
                    self.assertIsNone(expected["completion_command"])
                    self.assertIsNone(expected["result_path"])
                    self.assertNotIn("Call this when done:", prompt)
                else:
                    self.assertIn("Call this when done: " + expected["completion_command"], prompt)
                    self.assertIn(expected["result_path"], prompt)

    def test_correct_mechanics_always_require_semantic_review_and_never_execute(self):
        with patch("subprocess.run", side_effect=AssertionError("answers must not execute")):
            result = PROBE["grade"](self.root / "review", self.answer())
        self.assertEqual(result["mechanical_errors"], [])
        self.assertEqual(result["verdict"], "NEEDS_SEMANTIC_REVIEW")

    def test_wrong_identity_callback_result_path_and_absent_fields_fail(self):
        for key in ("phase", "stage", "action_id", "completion_command", "result_path"):
            with self.subTest(key=key):
                answer = self.answer()
                answer[key] = "wrong-or-stale"
                self.assertEqual(PROBE["grade"](self.root / "review", answer)["verdict"], "FAIL")
                del answer[key]
                self.assertEqual(PROBE["grade"](self.root / "review", answer)["verdict"], "FAIL")

    def test_paused_cannot_invent_callback_or_result(self):
        answer = self.answer("paused")
        self.assertFalse(PROBE["grade"](self.root / "paused", answer)["mechanical_errors"])
        for key in ("completion_command", "result_path"):
            wrong = copy.deepcopy(answer)
            wrong[key] = "invented"
            self.assertEqual(PROBE["grade"](self.root / "paused", wrong)["verdict"], "FAIL")

    def test_empty_or_malformed_explanations_fail(self):
        for key, value in (("steps", []), ("read_first", "README"), ("orientation", " "), ("unknowns", [1])):
            with self.subTest(key=key):
                answer = self.answer()
                answer[key] = value
                self.assertEqual(PROBE["grade"](self.root / "review", answer)["verdict"], "FAIL")
        with self.assertRaises(ValueError):
            PROBE["grade"](self.root / "review", [])

    def test_exports_never_overwrite_existing_directory(self):
        before = (self.export / "prompts/review.md").read_bytes()
        with self.assertRaises(FileExistsError):
            PROBE["prepare"](self.export)
        self.assertEqual(before, (self.export / "prompts/review.md").read_bytes())

    def test_failed_capture_leaves_no_export_and_write_failure_never_claims_success(self):
        destination = Path(self.tmp.name) / "failed-capture"
        with patch.dict(PROBE["prepare"].__globals__, {"captures": lambda: (_ for _ in ()).throw(ValueError("capture failed"))}):
            self.assertEqual(PROBE["main"](["prepare", "--output", str(destination)]), 2)
        self.assertFalse(destination.exists())
        with patch.object(Path, "write_text", side_effect=OSError("write failed")):
            self.assertEqual(PROBE["main"](["prepare", "--output", str(destination)]), 2)
        self.assertTrue(destination.exists())  # Partial output remains explicit; never overwrite it.
        with self.assertRaises(FileExistsError):
            PROBE["prepare"](destination)

    def test_changed_prompt_is_refused_before_grading(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-teachback-tamper-") as raw:
            folder = Path(raw) / "evaluator/review"
            folder.mkdir(parents=True)
            (folder / "oracle.json").write_bytes((self.root / "review/oracle.json").read_bytes())
            (Path(raw) / "prompts").mkdir()
            (Path(raw) / "prompts/review.md").write_text("Changed evidence")
            with self.assertRaisesRegex(ValueError, "prompt changed"):
                PROBE["grade"](folder, self.answer())

    def test_malformed_oracle_reports_input_failure_without_traceback(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-teachback-oracle-") as raw:
            folder = Path(raw) / "evaluator/review"
            folder.mkdir(parents=True)
            (folder / "oracle.json").write_text("{}")
            (folder / "response.json").write_text(json.dumps(self.answer()))
            (Path(raw) / "prompts").mkdir()
            (Path(raw) / "prompts/review.md").write_text("Packet")
            self.assertEqual(PROBE["main"](["grade", "--case", str(folder),
                                            "--response", str(folder / "response.json")]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
