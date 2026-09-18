"""Focused mechanical checks for the no-model requirements-study helper."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
import study  # noqa: E402


class StudyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-requirements-study-")
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "external-output"

    def _initialize_prepare(self) -> None:
        with mock.patch.object(study, "_head", return_value="1" * 40), redirect_stdout(io.StringIO()):
            study.initialize(self.output)
        with mock.patch.object(study.subprocess, "run", side_effect=AssertionError("no process launch")):
            with redirect_stdout(io.StringIO()):
                study.prepare(self.output)

    def _complete_discovery_notes(self, case: str) -> Path:
        trial = self.output / "trials" / "discovery" / case
        notes = trial / "notes"
        repo = trial / "repo"
        (notes / "sources.md").write_text("- README.md: status=inspected maintained index\n- docs/catalog-requirements.md: status=inspected accepted requirement\n")
        (notes / "artifact.md").write_text("Discovery artifact; question retained for later review.\n")
        (notes / "status.md").write_text("current_stage_status: drafted for review\nfeature_acceptance_status: unproven\n")
        (notes / "result.json").write_text(json.dumps({
            "outcome": "done", "summary": "Discovery draft retained for review.",
            "evidence_refs": [str(repo / "README.md"), str(repo / "docs" / "catalog-requirements.md")],
        }))
        return trial

    def test_initialize_refuses_nonempty_output(self) -> None:
        self.output.mkdir()
        (self.output / "existing.txt").write_text("preserve")
        with self.assertRaises(FileExistsError):
            study.initialize(self.output)

    def test_no_model_fixture_packets_and_cold_routing_are_structural_only(self) -> None:
        self._initialize_prepare()
        frozen = self.output / "frozen-skill"
        self.assertFalse((frozen / "scripts" / "__pycache__").exists())
        discovery = self.output / "trials" / "discovery" / "override"
        packet = (discovery / "run" / "packet.md").read_text()
        self.assertIn("ShipLoop navigator | discovery |", packet)
        self.assertIn(str(frozen / "references" / "requirements-definition.md"), packet)
        self.assertIn("Stop after writing the current producer outputs.", (discovery / "bootstrap.md").read_text())
        self.assertIn("Status: draft proposal only", (discovery / "repo" / "docs" / "later-design-draft.md").read_text())
        self.assertIn("filter_text", (discovery / "repo" / "tests" / "test_diagnostics.py").read_text())
        self._complete_discovery_notes("override")
        with mock.patch.object(study.subprocess, "run", side_effect=AssertionError("no process launch")):
            with redirect_stdout(io.StringIO()):
                study.next_trial(self.output, "override")
        spec = self.output / "trials" / "spec" / "override"
        self.assertIn("ShipLoop navigator | spec |", (spec / "run" / "packet.md").read_text())
        self.assertTrue((spec / "previous-discovery-notes" / "result.json").is_file())
        self.assertIn("not a live discovery-to-spec transition", (spec / "cold-context.md").read_text())
        report = study.audit(self.output)
        self.assertEqual(report["outcome"], "UNKNOWN")
        self.assertTrue(all(row["semantic_correctness"] == "NOT_GRADED" for row in report["trials"]))
        self.assertNotIn("PASSED", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
