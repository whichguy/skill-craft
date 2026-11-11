"""Independent process permission, publication and masked evidence controls."""
from pathlib import Path
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from v7 import report_context as report


class ReportContextTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()

    def test_nested_payload_bytes_and_modes_reproduce_at_022_and_077(self):
        script = r"""
from v7.report_context import write_tree
import os, sys
os.umask(int(sys.argv[2], 8))
write_tree(sys.argv[1], {"masked/S01.json": b'{"pass":true}\n',
                         "private/receipts/capture.json": b'{"count":3}\n'})
"""
        for mask in ("022", "077"):
            subprocess.run([sys.executable, "-B", "-c", script, str(self.root / mask), mask],
                           cwd=Path(__file__).resolve().parent, capture_output=True, check=True)
        def inspect(root):
            return {path.relative_to(root).as_posix():
                    (stat.S_IMODE(path.stat().st_mode), None if path.is_dir() else path.read_bytes())
                    for path in [root, *root.rglob("*")]}
        expected = {".": (0o700, None), "masked": (0o700, None),
                    "masked/S01.json": (0o600, b'{"pass":true}\n'), "private": (0o700, None),
                    "private/receipts": (0o700, None),
                    "private/receipts/capture.json": (0o600, b'{"count":3}\n')}
        self.assertEqual(inspect(self.root / "022"), expected)
        self.assertEqual(inspect(self.root / "077"), expected)

    def test_existing_and_racing_empty_destination_are_never_replaced(self):
        target = self.root / "bundle"
        target.mkdir()
        inode = target.stat().st_ino
        with self.assertRaises(ValueError):
            report.write_tree(target, {"nested/evidence.json": b"record"})
        self.assertEqual(target.stat().st_ino, inode)
        target.rmdir()
        published = []
        rename = report._rename_new
        def race(source, destination):
            destination.mkdir()
            published.append(destination.stat().st_ino)
            rename(source, destination)
        with patch.object(report, "_rename_new", side_effect=race):
            with self.assertRaises(FileExistsError):
                report.write_tree(target, {"nested/evidence.json": b"record"})
        self.assertEqual(target.stat().st_ino, published[0])
        self.assertEqual(list(target.iterdir()), [])
        stage, = self.root.glob(".report-stage-*")
        self.assertEqual((stage / "nested/evidence.json").read_bytes(), b"record")
        self.assertEqual(stat.S_IMODE(stage.stat().st_mode), 0o700)

    def test_path_conflicts_and_linked_outputs_cannot_mutate_protected_inputs(self):
        native = self.root / "native"
        native.mkdir()
        file = native / "artifact"
        file.write_bytes(b"retain")
        file.chmod(0o644)
        link = self.root / "redirect"
        link.symlink_to(native, target_is_directory=True)
        for output, files, inputs in (
            (native / "report", {"x": b"x"}, (native,)),
            (link / "report", {"x": b"x"}, ()),
            (self.root / "report", {"../native/artifact": b"change"}, ()),
            (self.root / "report", {"/outside": b"change"}, ()),
            (self.root / "report", {"a": b"one", "a/b": b"two"}, ()),
        ):
            with self.subTest(output=output, files=files):
                with self.assertRaises(ValueError):
                    report.write_tree(output, files, inputs=inputs)
        self.assertEqual(file.read_bytes(), b"retain")
        self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o644)
        self.assertEqual(list(native.iterdir()), [file])

    def test_tap_and_spec_parse_only_consistent_structural_counts(self):
        body = {"tests": 3, "pass": 1, "fail": 1, "cancelled": 0, "skipped": 1, "todo": 0}
        for prefix, reporter in (("#", "tap"), ("ℹ", "node_spec")):
            with self.subTest(reporter=reporter):
                raw = "/private/location SYNTHETIC-HIDDEN\n" + "\n".join(f"{prefix} {k} {v}" for k, v in body.items())
                self.assertEqual(report.public_counts(raw, 1, False),
                                 {"reporter": reporter, "status": "complete", "counts": body})
                self.assertEqual(report.public_counts(raw, 0, False)["status"], "inconsistent")
                self.assertEqual(report.public_counts(raw, 1, True)["status"], "timed_out")
                duplicate = report.public_counts(raw + f"\n{prefix} pass 0", 1, False)
                self.assertEqual(duplicate["status"], "partial_or_unknown")
                self.assertIsNone(duplicate["counts"]["pass"])

    def test_native_scope_distinguishes_fixture_drift_and_subject_mode_change(self):
        locator = "/private/source/example"
        scope = {"baseline": "native_start", "pass": False,
                 "changed_paths": [locator], "excluded_changes": [], "outside_allowed_subtrees": [],
                 "new_executable_files": [], "link_paths": [], "native_skipped_paths": [],
                 "regular_file_mode_changes": {locator: {"start": 0o600, "terminal": 0o640}},
                 "fixture_to_native_mode_differences": {locator: {"fixture": 0o644, "native_start": 0o600}}}
        public = report.scope_context(scope)
        self.assertEqual(public["changed_paths_count"], 1)
        self.assertEqual(public["regular_file_mode_changes"], [{"start": 0o600, "terminal": 0o640}])
        self.assertEqual(public["fixture_to_native_mode_differences"], [{"fixture": 0o644, "native_start": 0o600}])
        self.assertNotIn(locator, str(public))
        self.assertFalse(public["pass"])
        with self.assertRaises(ValueError):
            report.scope_context(dict(scope, baseline="reference_fixture"))


if __name__ == "__main__":
    unittest.main()
