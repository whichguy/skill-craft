#!/usr/bin/env python3
"""Hermetic checks for skills/spec-judge/scripts/spec_judge.py (no model)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills" / "spec-judge" / "scripts" / "spec_judge.py"


def repo() -> Path:
    root = Path(tempfile.mkdtemp())
    files = {
        "README.md": "# tool\n\n## Usage\n\nRun it.\n\n## License\n\nMIT\n",
        "src/main.js": "export function run() {\n  return 1\n}\n",
        "src/util.js": "export const x = 1\n",
        "test/main.test.js": "test('runs once', () => {})\nit('handles empty input', () => {})\n",
        "test/other.test.js": "it('runs once', () => {})\n",
    }
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    (root / "spec.md").write_text("### R-1 Runs\nEvidence: `src/main.js:1-3`\n\n### R-2 Empty input\n"
                                  "No anchor here.\n\n### R-3 Broken\nEvidence: `src/main.js:99`\n\n"
                                  "### R-4 Test-named\n- runs once (evidence: test `test/main.test.js`, \"runs once\")\n")
    return root


def call(*argv: str) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, str(SCRIPT), *argv], capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}


class SpecJudgeTest(unittest.TestCase):
    def setUp(self):
        self.repo = repo()
        self.out = Path(tempfile.mkdtemp()) / "judge"
        rc, self.report = call("sample", "--repo", str(self.repo), "--spec", str(self.repo / "spec.md"),
                               "--out", str(self.out), "--n", "40")
        self.assertEqual(rc, 0)
        self.sample = json.loads((self.out / "sample.json").read_text())

    def test_sample_draws_every_kind_and_checks_anchors(self):
        self.assertEqual(self.sample["requirements"], ["R-1", "R-2", "R-3", "R-4"])
        self.assertEqual(sorted((t["test"], t["file"]) for t in self.sample["tests"]),
                         [("handles empty input", "test/main.test.js"), ("runs once", "test/main.test.js"),
                          ("runs once", "test/other.test.js")])
        self.assertEqual(self.sample["sources"], ["src/main.js", "src/util.js"])
        self.assertEqual({d["section"] for d in self.sample["readme"]}, {"tool", "Usage", "License"})
        anchors = self.sample["anchors"]
        # R-4 cites an existing test file by name without a line: an anchor.
        self.assertEqual((anchors["requirements"], anchors["anchored"], anchors["all_anchors_resolve"]), (4, 3, 2))
        self.assertEqual(anchors["unanchored"], ["R-2"])

    def verdicts(self, drop_one: bool = False) -> dict:
        s = self.sample
        v = {"requirements": [{"id": i, "verdict": "correct"} for i in s["requirements"]],
             "tests": [{"test": t["test"], "file": t["file"], "verdict": "missing"} for t in s["tests"]],
             "sources": [{"file": f, "verdict": "internal" if "util" in f else "covered"} for f in s["sources"]],
             "readme": [{"section": d["section"], "verdict": "not-a-requirement" if d["section"] == "License"
                         else "covered"} for d in s["readme"]],
             "architecture": [{"item": a, "verdict": "absent"} for a in s["architecture"]]}
        v["requirements"][1]["verdict"] = "wrong"
        if drop_one:
            v["tests"].pop()
        return v

    def test_score_grades_both_gap_directions(self):
        (self.out / "verdicts.json").write_text(json.dumps(self.verdicts()))
        rc, grade = call("score", "--out", str(self.out))
        self.assertEqual(rc, 0, grade)
        self.assertEqual(grade["over_spec"], {"unanchored": 0.25, "broken_anchors": 0.25, "unsupported": 0.25})
        self.assertEqual(grade["under_spec"], {"tests_missing": 1.0, "sources_missing": 0.0, "readme_missing": 0.0})
        self.assertEqual(grade["architecture_true"], 0.0)

    def test_score_refuses_a_missing_verdict(self):
        (self.out / "verdicts.json").write_text(json.dumps(self.verdicts(drop_one=True)))
        rc, grade = call("score", "--out", str(self.out))
        self.assertEqual(rc, 1)
        self.assertFalse(grade["complete"])
        self.assertTrue(any(p.startswith("tests:") for p in grade["problems"]))


if __name__ == "__main__":
    unittest.main()
