"""No-network safety checks for the standalone acquisition probe."""

from __future__ import annotations

import contextlib
import io
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


sys.dont_write_bytecode = True
MODULE_PATH = Path(__file__).with_name("acquisition_probe.py")
SPEC = importlib.util.spec_from_file_location("acquisition_probe_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = probe
SPEC.loader.exec_module(probe)


class AcquisitionProbeOutputSafetyTests(unittest.TestCase):
    def test_existing_output_rejected_before_any_launch_or_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            evidence_root = Path(temporary_name) / "evidence"
            existing = evidence_root / "prior-run"
            existing.mkdir(parents=True)
            receipt = existing / "receipt.json"
            receipt.write_text("do-not-overwrite\n", encoding="utf-8")
            with mock.patch.object(
                probe, "compact_command", side_effect=AssertionError("network command must not start")
            ) as command, mock.patch.object(
                probe.tempfile, "TemporaryDirectory", side_effect=AssertionError("temporary process workspace must not start")
            ) as workspace:
                with self.assertRaises(probe.OutputDirectoryError):
                    probe.run_probe(existing)
            command.assert_not_called()
            workspace.assert_not_called()
            self.assertEqual(receipt.read_text(encoding="utf-8"), "do-not-overwrite\n")

    def test_dangling_symlink_output_is_rejected_before_any_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            evidence_root = Path(temporary_name) / "evidence"
            evidence_root.mkdir()
            dangling = evidence_root / "dangling-run"
            dangling.symlink_to(Path(temporary_name) / "missing-target")
            with mock.patch.object(
                probe, "compact_command", side_effect=AssertionError("network command must not start")
            ) as command:
                with self.assertRaises(probe.OutputDirectoryError):
                    probe.run_probe(dangling)
            command.assert_not_called()

    def test_fresh_external_output_is_accepted_without_a_network_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            requested = Path(temporary_name) / "new-access-evidence"
            with mock.patch.object(
                probe, "compact_command", side_effect=AssertionError("network command must not start")
            ) as command:
                actual = probe.prepare_new_output_directory(requested)
            command.assert_not_called()
            self.assertTrue(actual.is_dir())
            self.assertEqual(actual.name, "new-access-evidence")

    def test_failure_summary_does_not_claim_success(self) -> None:
        summary = probe.build_summary(
            {"status": "blocked_or_failed", "failures": [{"type": "RuntimeError"}]}
        )
        self.assertIn("The probe did not complete.", summary)
        self.assertIn("RuntimeError", summary)
        self.assertNotIn("The probe completed in a newly created evidence directory.", summary)

    def test_cli_requires_explicit_output(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            probe.main([])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
