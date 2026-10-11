#!/usr/bin/env python3
"""The run reference file (`<run>/reference.md`, shiploop_reference): run-wide detail packets name by section.

Owner, 2026-10-10: a packet holds the key file references, what to do, when it is complete and what to execute;
detail a stage seldom needs lives in this file, in labelled sections a packet cites as reference#<anchor>. These
checks: save() writes it with every anchor; every policy it lists resolves to a package file; a run saved before the
file existed (or by another version) gets it on its next `next`, with its cursor unchanged.
"""
from __future__ import annotations

import io
import contextlib
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_reference as reference  # noqa: E402
import shiploop_store as store  # noqa: E402


class ReferenceFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-reference-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "run"
        self.root.mkdir()
        self.state = navigator.new_state(self.temp.name, "Build a thing.", delegation="inline")
        navigator.save(self.root, self.state)
        self.path = self.root / reference.REFERENCE_FILE

    def test_save_writes_every_section_with_its_anchor_and_the_package_version(self):
        text = self.path.read_text()
        self.assertEqual(text.splitlines()[0], reference.VERSION_LINE.format(version=reference.package_version()))
        self.assertTrue(reference.package_version())
        anchors = re.findall(r"^## .+ \{#([\w-]+)\}$", text, re.M)
        self.assertEqual(anchors, [anchor for anchor, _ in reference.SECTIONS])

    def test_every_policy_and_guide_resolves_to_a_package_file_and_section(self):
        for label, target in reference.POLICIES:
            path, _, anchor = target.partition("#")
            with self.subTest(label):
                file = reference.REFERENCES / path
                self.assertTrue(file.is_file(), file)
                if anchor:
                    slugs = {re.sub(r"[^\w\s-]", "", line.lstrip("#").strip().lower()).replace(" ", "-")
                             for line in file.read_text().splitlines() if line.startswith("#")}
                    self.assertIn(anchor, slugs)

    def test_a_run_without_the_file_gets_it_on_next_and_its_cursor_does_not_move(self):
        self.path.unlink()
        before = store.read_record(self.root / "state.md")
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.root, before)
        self.assertTrue(self.path.is_file())
        after = store.read_record(self.root / "state.md")
        self.assertEqual((after["revision"], after["action"]), (before["revision"], before["action"]))

    def test_a_file_written_by_another_version_is_replaced(self):
        self.path.write_text(reference.VERSION_LINE.format(version="0.0.1") + "\nold\n")
        self.assertTrue(reference.stale(self.root, reference.package_version()))
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.root, store.read_record(self.root / "state.md"))
        self.assertFalse(reference.stale(self.root, reference.package_version()))
        self.assertIn("{#rules}", self.path.read_text())


if __name__ == "__main__":
    unittest.main()
