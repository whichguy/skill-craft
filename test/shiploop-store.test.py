#!/usr/bin/env python3
"""Focused tests for ShipLoop's Markdown-authoritative storage layer."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from unittest import mock
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


class ObservationJSONDepthTests(unittest.TestCase):
    def test_deep_jsonl_is_skipped_with_coverage_and_neighbor_rows_retained(self):
        depth = sys.getrecursionlimit() + 50
        deep = '{"nested":' + '[' * depth + '0' + ']' * depth + '}'
        raw = ('{"before":true}\n' + deep + '\n{"after":true}\n').encode()
        # Python decoders have different nesting tolerances. Compare only
        # shallow facts, never recursively compare or format the nested value.
        try:
            json.loads(deep)
        except RecursionError:
            decoder_accepts = False
        else:
            decoder_accepts = True
        default_rows = store.parse_jsonl_bytes(raw)
        self.assertEqual(len(default_rows), 3 if decoder_accepts else 2)
        self.assertTrue(isinstance(default_rows[0], dict) and default_rows[0].get("before") is True)
        self.assertTrue(isinstance(default_rows[-1], dict) and default_rows[-1].get("after") is True)
        if decoder_accepts:
            self.assertTrue(isinstance(default_rows[1], dict) and "nested" in default_rows[1])
            node = default_rows[1]["nested"]
            for _ in range(depth):
                self.assertTrue(isinstance(node, list))
                self.assertEqual(len(node), 1)
                node = node[0]
            self.assertTrue(isinstance(node, int) and node == 0)
        rows, coverage = store.parse_jsonl_bytes(raw, coverage=True)
        self.assertEqual([number for number, row in rows], [1, 3])
        self.assertEqual(coverage["interior_damage"], 1)

    def test_optional_depth_guard_does_not_limit_default_read_semantics(self):
        depth = store.OBSERVATION_JSON_DEPTH + 10
        raw = ('{"nested":' + '[' * depth + '0' + ']' * depth + '}\n').encode()
        self.assertEqual(len(store.parse_jsonl_bytes(raw)), 1)
        rows, coverage = store.parse_jsonl_bytes(raw, coverage=True)
        self.assertEqual(len(rows), 0)
        self.assertEqual(coverage["damaged"], 1)

    def test_jsonl_decoder_recursion_is_skipped_and_diagnosed_deterministically(self):
        failing = '{"nested":[]}'
        raw = ('{"before":true}\n' + failing + '\n{"after":true}\n').encode()
        original_loads = json.loads
        def decoder(value, *args, **kwargs):
            if value == failing:
                raise RecursionError("injected JSON decoder failure")
            return original_loads(value, *args, **kwargs)
        with mock.patch.object(store.json, "loads", side_effect=decoder):
            self.assertEqual(store.parse_jsonl_bytes(raw), [{"before": True}, {"after": True}])
            rows, coverage = store.parse_jsonl_bytes(raw, coverage=True)
        self.assertEqual([number for number, row in rows], [1, 3])
        self.assertEqual(coverage["interior_damage"], 1)
        self.assertEqual(coverage["damaged"], 1)

    def test_authoritative_decoder_recursion_is_an_explicit_storage_error(self):
        with mock.patch.object(store.json, "loads", side_effect=RecursionError("injected JSON decoder failure")):
            with self.assertRaises(store.StorageError) as caught:
                store.loads('```shiploop-state\n{"nested":[]}\n```\n')
        self.assertIsInstance(caught.exception.__cause__, RecursionError)


if __name__ == "__main__":
    unittest.main(verbosity=2)
