#!/usr/bin/env python3
"""Focused tests for ShipLoop's Markdown-authoritative storage layer."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "skills" / "shiploop" / "scripts" / "shiploop_store.py"
SPEC = importlib.util.spec_from_file_location("shiploop_store_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"could not load {MODULE_PATH}")
store = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = store
SPEC.loader.exec_module(store)


class SimulatedCrash(RuntimeError):
    """Models process death after a target operation reaches disk."""


class ShipLoopStoreTests(unittest.TestCase):
    def test_markdown_round_trip_and_no_raw_json_fallback(self) -> None:
        record = {
            "phase": "implement",
            "steps": [{"id": "S1", "status": "running"}],
            "flags": [True, False],
        }
        rendered = store.dumps(record)

        self.assertTrue(rendered.startswith("# ShipLoop record\n"))
        self.assertEqual(rendered.count("```shiploop-state"), 1)
        self.assertEqual(store.loads(rendered), record)
        with self.assertRaises(store.StorageError):
            store.loads(json.dumps(record))

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.md"
            store.write_record(path, record, title="Run state")
            self.assertEqual(store.read_record(path), record)
            self.assertIn("# Run state", path.read_text(encoding="utf-8"))

    def test_line_and_paragraph_separators_round_trip(self) -> None:
        # dumps() writes these unescaped; str.splitlines() used to break the record on them.
        value = {"summary": "a\u2028b\u2029c\u0085d", "crlf": "kept"}
        self.assertEqual(store.loads(store.dumps(value)), value)
        self.assertEqual(store.loads(store.dumps(value).replace("\n", "\r\n")), value)

    def test_rejects_malformed_duplicate_or_ambiguous_payloads(self) -> None:
        malformed = (
            '# Broken\n\n```shiploop-state\n{"phase": "plan"}\n',
            "# Duplicate\n\n```shiploop-state\n{}\n```\n\n```shiploop-state\n{}\n```\n",
            '# Duplicate key\n\n```shiploop-state\n{"phase": 1, "phase": 2}\n```\n',
            '# Invalid JSON\n\n```shiploop-state\n{"phase": NaN}\n```\n',
            "# Wrong fence\n\n```json\n{}\n```\n",
        )
        for text in malformed:
            with self.subTest(text=text):
                with self.assertRaises(store.StorageError):
                    store.loads(text)

    def test_recover_rolls_forward_after_crash_following_first_target_write(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()

            def crash_after_first_target(phase: str, index: int) -> None:
                if phase == "after-target" and index == 1:
                    raise SimulatedCrash("simulated process crash")

            with self.assertRaises(SimulatedCrash):
                store.transaction(
                    root,
                    {"b.md": "second\n", "a.md": "first\n"},
                    fault=crash_after_first_target,
                )

            self.assertEqual((root / "a.md").read_text(encoding="utf-8"), "first\n")
            self.assertFalse((root / "b.md").exists())
            self.assertTrue((root / "transaction.md").exists())

            self.assertTrue(store.recover(root))
            self.assertEqual((root / "a.md").read_text(encoding="utf-8"), "first\n")
            self.assertEqual((root / "b.md").read_text(encoding="utf-8"), "second\n")
            self.assertFalse((root / "transaction.md").exists())
            self.assertFalse(store.recover(root))

    def test_unsafe_manifest_has_no_partial_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            outside = Path(temp_dir) / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "escape").symlink_to(outside, target_is_directory=True)

            with self.assertRaises(store.StorageError):
                store.transaction(
                    root,
                    {
                        "a-before-unsafe.md": "must not appear\n",
                        "escape/owned.md": "bad\n",
                    },
                )

            self.assertFalse((root / "a-before-unsafe.md").exists())
            self.assertFalse((outside / "owned.md").exists())
            self.assertFalse((root / "transaction.md").exists())

    def test_transaction_applies_sorted_writes_and_deletes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            (root / "remove.md").write_text("old\n", encoding="utf-8")

            store.transaction(
                root,
                {"nested/b.md": "second\n", "a.md": "first\n"},
                ["remove.md"],
            )

            self.assertEqual((root / "a.md").read_text(encoding="utf-8"), "first\n")
            self.assertEqual(
                (root / "nested" / "b.md").read_text(encoding="utf-8"), "second\n"
            )
            self.assertFalse((root / "remove.md").exists())
            self.assertFalse((root / "transaction.md").exists())

    def test_refuses_symlink_targets_and_parents_that_escape_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            outside = Path(temp_dir) / "outside"
            root.mkdir()
            outside.mkdir()
            (root / "parent-link").symlink_to(outside, target_is_directory=True)
            (root / "target-link.md").symlink_to(outside / "outside.md")

            with self.assertRaises(store.StorageError):
                store.transaction(root, {"parent-link/new.md": "nope\n"})
            with self.assertRaises(store.StorageError):
                store.transaction(root, {"target-link.md": "nope\n"})

            self.assertFalse((outside / "new.md").exists())
            self.assertFalse((outside / "outside.md").exists())

    def test_refuses_edits_to_its_own_journal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            cases = (
                ({"transaction.md": "bad"}, []),
                ({"transaction.md/nested.md": "bad"}, []),
                ({}, ["transaction.md"]),
            )
            for index, (writes, deletes) in enumerate(cases):
                with self.subTest(writes=writes, deletes=deletes):
                    root = Path(temp_dir) / f"run-{index}"
                    root.mkdir()
                    with self.assertRaises(store.StorageError):
                        store.transaction(root, writes, deletes)
                    self.assertFalse((root / "transaction.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
