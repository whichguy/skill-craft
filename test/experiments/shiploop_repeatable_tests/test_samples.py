"""Keep observed sample bytes immutable without executing expected-RED suites."""
import hashlib
import json
from pathlib import Path
import unittest


class SampleRetentionTests(unittest.TestCase):
    def test_manifest_binds_complete_nonimportable_sample_inventory(self):
        root = Path(__file__).resolve().parent / "samples"
        manifest = json.loads((root / "manifest.json").read_text())
        samples = manifest["samples"]
        self.assertTrue(samples)
        self.assertFalse((root / "__init__.py").exists())
        self.assertEqual(
            {p.name for p in root.iterdir()},
            {"README.md", "manifest.json", *(s["sample"] for s in samples)},
        )
        for sample in samples:
            directory = root / sample["sample"]
            self.assertEqual(directory.parent, root)
            self.assertFalse(directory.is_symlink())
            declared = {f["path"] for f in sample["files"]}
            self.assertEqual(len(declared), len(sample["files"]))
            self.assertNotIn("__init__.py", declared)
            self.assertTrue(declared)
            self.assertEqual(
                {str(p.relative_to(directory)) for p in directory.rglob("*") if p.is_file()},
                declared,
            )
            for path in directory.rglob("*"):
                self.assertFalse(path.is_symlink(), str(path))
            for entry in sample["files"]:
                self.assertFalse(Path(entry["path"]).is_absolute())
                self.assertNotIn("..", Path(entry["path"]).parts)
                path = directory / entry["path"]
                self.assertTrue(path.is_relative_to(directory))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"])


if __name__ == "__main__":
    unittest.main()
