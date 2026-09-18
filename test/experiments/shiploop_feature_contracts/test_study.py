"""Mechanical controls only; no model-quality claims."""

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

import study


class StudyTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.output = Path(self.scratch.name) / "export"
        with redirect_stdout(io.StringIO()):
            study.prepare(self.output)

    def seed_answers(self):
        answer = {key: [] for key in study.KEYS}
        answer.update(decision="Propose only", completion="Unverified")
        for case in study.CASES:
            for variant in ("A", "B"):
                (self.output / f"{case}-{variant}.json").write_text(json.dumps(answer))

    def test_exports_separate_conditions_and_refuses_overwrite(self):
        self.assertEqual(len(list(self.output.glob("*.md"))), 6)
        self.assertNotIn("must not be persisted", (self.output / "retry-A.md").read_text())
        self.assertIn("must not be persisted", (self.output / "retry-B.md").read_text())
        with self.assertRaises(FileExistsError):
            study.prepare(self.output)

    def test_missing_response_is_not_success(self):
        with self.assertRaises(FileNotFoundError):
            study.audit(self.output)

    def test_shape_pass_is_not_semantic_pass(self):
        self.seed_answers()
        stream = io.StringIO()
        with redirect_stdout(stream):
            study.audit(self.output)
        report = json.loads(stream.getvalue())
        self.assertEqual(report["structure"], "VALID")
        self.assertEqual(report["semantics"], "NOT_GRADED")

    def test_changed_packet_rejected(self):
        self.seed_answers()
        (self.output / "drag-A.md").write_text("different packet")
        with self.assertRaisesRegex(ValueError, "packet changed"):
            study.audit(self.output)

    def test_wrong_list_shape_rejected(self):
        self.seed_answers()
        path = self.output / "drag-A.json"
        answer = json.loads(path.read_text())
        answer["checks"] = "not an array"
        path.write_text(json.dumps(answer))
        with self.assertRaisesRegex(ValueError, "invalid list"):
            study.audit(self.output)

    def test_unexpected_path_is_rejected(self):
        path = self.output / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["trials"][0]["packet"] = "../outside.md"
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "unexpected packet path"):
            study.audit(self.output)


if __name__ == "__main__":
    unittest.main()
