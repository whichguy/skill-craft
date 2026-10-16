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

    def test_rejects_json_float_overflow_and_round_trips_utf8_records(self) -> None:
        with self.assertRaises(store.StorageError):
            store.loads("# Overflow\n\n```shiploop-state\n1e999\n```\n")

        value = {"text": "café 🚀\u2028kept"}
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            store.transaction(root, {"state.md": store.dumps(value)})
            self.assertEqual(store.read_record(root / "state.md"), value)

    def test_rejects_non_utf8_write_values_before_disk_mutation(self) -> None:
        with self.assertRaises(store.StorageError):
            store.loads(
                '# Invalid Unicode\n\n```shiploop-state\n{"invalid":"\\ud800"}\n```\n'
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            with self.assertRaises(store.StorageError):
                store.dumps({"invalid": "\ud800"})
            with self.assertRaises(store.StorageError):
                store.dumps({}, title="\ud800")
            with self.assertRaises(store.StorageError):
                store.atomic_write_text(root / "direct.md", "\ud800")
            with self.assertRaises(store.StorageError):
                store.transaction(root, {"invalid.md": "\ud800"})

            self.assertFalse((root / "direct.md").exists())
            self.assertFalse((root / "invalid.md").exists())
            self.assertFalse((root / "transaction.md").exists())

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

    def test_rejects_ancestor_descendant_manifest_paths_before_mutation(self) -> None:
        cases = (
            ({"a": "file\n", "a/b": "child\n"}, []),
            ({"a": "file\n"}, ["a/b"]),
            ({"a/b": "child\n"}, ["a"]),
            ({}, ["a", "a/b"]),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, (writes, deletes) in enumerate(cases):
                with self.subTest(writes=writes, deletes=deletes):
                    root = Path(temp_dir) / f"run-{index}"
                    root.mkdir()
                    with self.assertRaises(store.StorageError):
                        store.transaction(root, writes, deletes)
                    self.assertFalse((root / "a").exists())
                    self.assertFalse((root / "transaction.md").exists())

    def test_recover_rejects_overlapping_journal_before_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            store.write_record(
                root / "transaction.md",
                {
                    "schema": store.JOURNAL_SCHEMA,
                    "transaction_id": "overlap",
                    "version": store.JOURNAL_VERSION,
                    "writes": [
                        {"path": "a", "text": "file\n"},
                        {"path": "a/b", "text": "child\n"},
                    ],
                    "deletes": [],
                },
                title="ShipLoop transaction",
            )

            with self.assertRaises(store.StorageError):
                store.recover(root)

            self.assertFalse((root / "a").exists())
            self.assertTrue((root / "transaction.md").exists())

    def test_rejects_physical_journal_alias_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            (root / "alias").symlink_to(root, target_is_directory=True)

            with self.assertRaises(store.StorageError):
                store.transaction(root, {"alias/transaction.md": "bad\n"})
            with self.assertRaises(store.StorageError):
                store.transaction(root, {"alias/TRANSACTION.md": "case alias\n"})

            self.assertFalse((root / "transaction.md").exists())

    def test_rejects_journal_descendant_alias_before_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            (root / "alias").symlink_to(root, target_is_directory=True)

            with self.assertRaises(store.StorageError):
                store.transaction(
                    root, {"alias/transaction.md/child.md": "must not appear\n"}
                )

            self.assertFalse((root / "transaction.md").exists())
            self.assertFalse((root / "alias" / "transaction.md").exists())

    def test_rejects_portable_case_and_unicode_normalization_aliases(self) -> None:
        cases = (
            {"A.md": "upper\n", "a.md": "lower\n"},
            {"café.md": "composed\n", "cafe\u0301.md": "decomposed\n"},
            {"Transaction.md": "journal alias\n"},
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, writes in enumerate(cases):
                with self.subTest(writes=writes):
                    root = Path(temp_dir) / f"run-{index}"
                    root.mkdir()
                    with self.assertRaises(store.StorageError):
                        store.transaction(root, writes)
                    self.assertFalse((root / "transaction.md").exists())
                    for path in writes:
                        self.assertFalse((root / path).exists())

    def test_allows_distinct_unicode_path_components(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()

            store.transaction(
                root,
                {"café.md": "coffee\n", "élan.md": "energy\n"},
            )

            self.assertEqual((root / "café.md").read_text(encoding="utf-8"), "coffee\n")
            self.assertEqual((root / "élan.md").read_text(encoding="utf-8"), "energy\n")

    def test_rejects_physical_duplicate_and_ancestor_targets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            (root / "sub").mkdir()
            (root / "alias").symlink_to(root, target_is_directory=True)
            with self.assertRaises(store.StorageError):
                store.transaction(
                    root,
                    {"alias/x.md": "alias\n", "x.md": "direct\n"},
                )
            self.assertFalse((root / "x.md").exists())
            self.assertFalse((root / "transaction.md").exists())
            with self.assertRaises(store.StorageError):
                store.transaction(root, {"alias/x.md": "alias\n"}, ["x.md"])
            self.assertFalse((root / "x.md").exists())
            self.assertFalse((root / "transaction.md").exists())

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            (root / "sub").mkdir()
            (root / "alias").symlink_to(root / "sub", target_is_directory=True)
            with self.assertRaises(store.StorageError):
                store.transaction(
                    root,
                    {"alias/new": "file\n", "sub/new/child": "child\n"},
                )
            self.assertFalse((root / "sub" / "new").exists())
            self.assertFalse((root / "transaction.md").exists())

    def test_rejects_replacing_symlink_parent_used_by_another_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            (root / "sub").mkdir()
            (root / "link").symlink_to(root / "sub", target_is_directory=True)
            (root / "alias").symlink_to("link", target_is_directory=True)

            with self.assertRaises(store.StorageError):
                store.transaction(
                    root,
                    {"link": "replace link\n", "alias/file.md": "child\n"},
                )

            self.assertTrue((root / "link").is_symlink())
            self.assertFalse((root / "sub" / "file.md").exists())
            self.assertFalse((root / "transaction.md").exists())

    def test_allows_safe_symlink_parent_and_nonconflicting_sibling_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            (root / "sub").mkdir()
            (root / "alias").symlink_to(root / "sub", target_is_directory=True)

            store.transaction(
                root,
                {"alias/a.md": "through alias\n", "sub/b.md": "sibling\n"},
            )

            self.assertEqual(
                (root / "sub" / "a.md").read_text(encoding="utf-8"),
                "through alias\n",
            )
            self.assertEqual(
                (root / "sub" / "b.md").read_text(encoding="utf-8"),
                "sibling\n",
            )

    def test_atomic_write_fsyncs_each_created_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            resolved_root = root.resolve()
            fsynced = []
            original_fsync = store._fsync_directory

            def record_fsync(directory: Path) -> None:
                fsynced.append(Path(directory).resolve())
                original_fsync(directory)

            store._fsync_directory = record_fsync
            try:
                store.atomic_write_text(root / "a" / "b" / "state.md", "value\n")
            finally:
                store._fsync_directory = original_fsync

            self.assertEqual(
                fsynced,
                [resolved_root, resolved_root / "a", resolved_root / "a" / "b"],
            )

    def test_transaction_fsyncs_nested_parents_before_journal_removal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            resolved_root = root.resolve()
            events = []
            original_fsync = store._fsync_directory
            original_remove = store._remove_journal

            def record_fsync(directory: Path) -> None:
                events.append(("fsync", Path(directory).resolve()))
                original_fsync(directory)

            def record_remove(directory: Path) -> None:
                events.append(("remove", Path(directory).resolve()))
                original_remove(directory)

            store._fsync_directory = record_fsync
            store._remove_journal = record_remove
            try:
                store.transaction(root, {"a/b/state.md": "value\n"})
            finally:
                store._fsync_directory = original_fsync
                store._remove_journal = original_remove

            remove_index = next(
                index for index, event in enumerate(events) if event[0] == "remove"
            )
            before_remove = [
                directory
                for kind, directory in events[:remove_index]
                if kind == "fsync"
            ]
            self.assertEqual(
                before_remove,
                [
                    resolved_root,
                    resolved_root,
                    resolved_root / "a",
                    resolved_root / "a" / "b",
                ],
            )

    def test_recovery_resyncs_parent_chain_after_fsync_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            resolved_root = root.resolve()
            original_fsync = store._fsync_directory
            root_calls = 0

            def fail_second_root_sync(directory: Path) -> None:
                nonlocal root_calls
                if Path(directory) == resolved_root:
                    root_calls += 1
                    if root_calls == 2:
                        raise store.StorageError("injected parent fsync failure")
                original_fsync(directory)

            store._fsync_directory = fail_second_root_sync
            try:
                with self.assertRaises(store.StorageError):
                    store.transaction(root, {"a/b/state.md": "value\n"})
            finally:
                store._fsync_directory = original_fsync

            self.assertTrue((root / "transaction.md").exists())
            self.assertTrue((root / "a").is_dir())
            self.assertFalse((root / "a" / "b").exists())

            fsynced = []

            def record_fsync(directory: Path) -> None:
                fsynced.append(Path(directory).resolve())
                original_fsync(directory)

            store._fsync_directory = record_fsync
            try:
                self.assertTrue(store.recover(root))
            finally:
                store._fsync_directory = original_fsync

            self.assertEqual(
                fsynced,
                [
                    resolved_root,
                    resolved_root / "a",
                    resolved_root / "a" / "b",
                    resolved_root,
                ],
            )
            self.assertTrue((root / "a" / "b" / "state.md").exists())
            self.assertFalse((root / "transaction.md").exists())

    def test_recover_requires_exact_integer_journal_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            for index, version in enumerate((True, 1.0)):
                with self.subTest(version=version):
                    root = Path(temp_dir) / f"run-{index}"
                    root.mkdir()
                    store.write_record(
                        root / "transaction.md",
                        {
                            "schema": store.JOURNAL_SCHEMA,
                            "transaction_id": "version",
                            "version": version,
                            "writes": [
                                {"path": "state.md", "text": "must not replay\n"}
                            ],
                            "deletes": [],
                        },
                        title="ShipLoop transaction",
                    )

                    with self.assertRaises(store.StorageError):
                        store.recover(root)

                    self.assertFalse((root / "state.md").exists())
                    self.assertTrue((root / "transaction.md").exists())

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

    def test_rejects_dangling_or_file_symlink_parents_before_journaling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "run"
            root.mkdir()
            (root / "file.md").write_text("keep\n", encoding="utf-8")
            (root / "dangling").symlink_to(root / "missing", target_is_directory=True)
            (root / "file-parent").symlink_to(root / "file.md")

            for parent in ("dangling", "file-parent"):
                with self.subTest(parent=parent):
                    with self.assertRaises(store.StorageError):
                        store.transaction(root, {f"{parent}/child.md": "bad\n"})
                    self.assertFalse((root / "transaction.md").exists())
                    self.assertFalse((root / "missing" / "child.md").exists())
                    self.assertEqual(
                        (root / "file.md").read_text(encoding="utf-8"), "keep\n"
                    )

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
