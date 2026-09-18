#!/usr/bin/env python3
"""Check real fixture paths that a preview or local behavioral model cannot prove."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from fixtures import materialize


class FixtureRuntimeTest(unittest.TestCase):
    def test_preview_does_not_validate_the_committed_row_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            materialize("f1", root)
            spec = importlib.util.spec_from_file_location("fixture_writer", root / "app/export_writer.py")
            writer = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(writer)
            target = root / "output.txt"
            target.write_text("previous\n")
            rows = [{"total": "42"}]
            self.assertFalse(writer.write_export(target, rows, dry_run=True)["committed"])
            with self.assertRaises(KeyError):
                writer.write_export(target, rows, dry_run=False)
            self.assertEqual(target.read_text(), "previous\n")

    def test_javascript_ordering_matches_the_calibrated_model(self) -> None:
        program = """
import {createBoardRefresh} from './web/client.js';
const pending = [], rendered = [];
const refresh = createBoardRefresh(
  () => new Promise(resolve => pending.push(resolve)),
  state => rendered.push(state.version)
);
const older = refresh(), newer = refresh();
pending[1]({version: 2});
await newer;
pending[0]({version: 1});
await older;
console.log(JSON.stringify({rendered}));
"""
        for mutant in (False, True):
            with self.subTest(mutant=mutant), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                materialize("f4", root, mutant=mutant)
                result = subprocess.run(["node", "--input-type=module", "-e", program],
                                        cwd=root, capture_output=True, text=True, timeout=15, check=True)
                self.assertEqual(json.loads(result.stdout)["rendered"], [2, 1] if mutant else [2])


if __name__ == "__main__":
    unittest.main()
