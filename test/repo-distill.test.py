#!/usr/bin/env python3
"""Hermetic checks for skills/repo-distill scripts (no model, no network)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "repo-distill" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from spec_check import builder_view  # noqa: E402


def git_repo(files: dict[str, str]) -> Path:
    repo = Path(tempfile.mkdtemp())
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    return repo


def run(*argv: str) -> tuple[int, dict]:
    proc = subprocess.run([sys.executable, *argv], capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout)


class BuilderViewTest(unittest.TestCase):
    def test_strips_evidence_lines_and_inline_citations(self):
        spec = ("D-1. Parses input. Evidence: `src/orig.ts:3`\n"
                "D-2. Prints output.\nEvidence: `bin/orig.js:1`\nTest: `prints`\nKept line.\n")
        view = builder_view(spec)
        self.assertNotIn("orig", view)
        self.assertIn("D-1. Parses input.", view)
        self.assertIn("Kept line.", view)


class SpecCheckTest(unittest.TestCase):
    def setUp(self):
        self.repo = git_repo({"src/orig.js": "a\nb\nc\n", "test/fixture.md": "x\n"})

    def check(self, spec: str, *forbid: str) -> tuple[int, dict]:
        path = self.repo / "spec.md"
        path.write_text(spec)
        args = [a for f in forbid for a in ("--forbid", f)]
        return run(str(SCRIPTS / "spec_check.py"), str(path), str(self.repo), *args)

    def test_passes_when_every_claim_cites_resolving_evidence(self):
        rc, report = self.check("D-1. A. Evidence: `src/orig.js:1-3`\nD-2. B. Evidence: `test/fixture.md`\n"
                                "## Unknowns\n", "orig")
        self.assertEqual(rc, 0, report)
        self.assertEqual(report["leaks"], [])  # the name in an evidence path is not a leak

    def test_reports_missing_evidence_bad_lines_and_prose_leaks(self):
        rc, report = self.check("D-1. A.\nD-2. B. Evidence: `src/orig.js:40`\nD-3. calls orig.parse.\n"
                                "Evidence: `src/orig.js:1`\n", "orig.")
        self.assertEqual(rc, 1)
        self.assertEqual(report["claims_without_evidence"], ["D-1"])
        self.assertTrue(any("src/orig.js:40" in b for b in report["citations_bad"]))
        self.assertEqual(report["leaks"], ["orig."])


class RepoValueTest(unittest.TestCase):
    def test_counts_own_code_and_excludes_tests(self):
        body = "".join(f"const v{i} = {i}\n" for i in range(1200))
        repo = git_repo({"src/main.js": body, "test/main.test.js": body, "package.json": '{"dependencies":{"a":"1"}}'})
        rc, report = run(str(SCRIPTS / "repo_value.py"), str(repo))
        self.assertEqual(rc, 0, report)
        self.assertEqual(report["own_code_lines"], 1200)
        self.assertEqual(report["runtime_deps"], 1)

    def test_monorepo_is_not_material_but_an_empty_workspace_list_is_fine(self):
        body = "".join(f"let v{i}\n" for i in range(1100))
        mono = git_repo({"src/a.js": body, "pnpm-workspace.yaml": "packages:\n  - packages/*\n"})
        single = git_repo({"src/a.js": body, "pnpm-workspace.yaml": "packages: []\n"})
        self.assertTrue(run(str(SCRIPTS / "repo_value.py"), str(mono))[1]["workspaces"])
        self.assertFalse(run(str(SCRIPTS / "repo_value.py"), str(single))[1]["workspaces"])


class OracleAdmissionTest(unittest.TestCase):
    def test_admits_an_oracle_that_passes_on_the_original_and_fails_on_the_stubs(self):
        oracle = Path(tempfile.mkdtemp())
        (oracle / "cli.test.mjs").write_text(
            "import test from 'node:test'\nimport assert from 'node:assert/strict'\n"
            "import { execSync } from 'node:child_process'\n"
            "test('prints hi', () => assert.equal(execSync(process.env.APP_CMD).toString().trim(), 'hi'))\n")
        original = Path(tempfile.mkdtemp()) / "hi.mjs"
        original.write_text("console.log('hi')\n")
        rc, report = run(str(SCRIPTS / "oracle_run.py"), str(oracle), "--admit", "--original", f"node {original}",
                         "--stub", f"node {SCRIPTS / 'stub_server.mjs'}", "--stub-timeout", "60")
        self.assertEqual(rc, 0, report)
        self.assertTrue(report["admitted"])
        self.assertEqual(report["stub"]["pass"], 0)


if __name__ == "__main__":
    unittest.main()
