#!/usr/bin/env python3
"""Exercise real Git routing and qualification guards, not a second policy copy."""
import contextlib
import io
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import ci_policy as policy

ROOT = Path(__file__).resolve().parents[1]


class CIPolicyTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="skill-craft-ci-policy-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.write("README.md", "initial\n")
        self.write("code.py", "initial\n")
        self.write(".gitignore", "__pycache__/\nignored/\n")
        self.base = self.commit()

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, stderr=subprocess.PIPE).decode().strip()

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "fixture")
        return self.git("rev-parse", "HEAD")

    def event(self, base=None, head=None):
        return {"pull_request": {"base": {"sha": base or self.base}, "head": {"sha": head or self.git("rev-parse", "HEAD")}}}

    def test_allowlist_excludes_executable_markdown_and_unknown_paths(self):
        for paths in (["README.md"], ["docs/report.md", "docs/inventory.csv"], ["test/README.md"]):
            self.assertTrue(policy.docs_only(paths))
        for path in ("skills/ask-agent/SKILL.md", "plugins/shiploop/README.md", "test/test-groups.test.py",
                     "scripts/sync-plugin-views.sh", ".github/workflows/ci.yml", "docs/fixture.py", "AGENTS.md", "new.md"):
            self.assertFalse(policy.docs_only(["README.md", path]), path)
        self.assertFalse(policy.docs_only([]))
        self.assertFalse(policy.docs_only([""]))

    def test_main_unknown_and_manual_events(self):
        for event in ("push", "unknown"):
            self.assertEqual(policy.select(self.root, event, {}, "smoke")[0], "full")
        for tier in ("smoke", "full"):
            self.assertEqual(policy.select(self.root, "workflow_dispatch", {}, tier)[0], tier)
        with self.assertRaises(ValueError):
            policy.select(self.root, "workflow_dispatch", {}, "")
        self.assertEqual(policy.select(self.root, "pull_request", {}, "")[0], "full")
        event = self.event(base="f" * 40)
        self.assertEqual(policy.select(self.root, "pull_request", event, "")[0], "full")

    def test_pr_diff_uses_merge_base_not_unrelated_main_changes(self):
        self.write("code.py", "main moved\n")
        main = self.commit()
        self.git("checkout", "-q", "--detach", self.base)
        self.write("docs/report.md", "explanation\n")
        head = self.commit()
        self.assertEqual(policy.pr_paths(self.root, main, head), ["docs/report.md"])
        self.assertEqual(policy.select(self.root, "pull_request", self.event(main, head), "")[0], "smoke")

    def test_rename_keeps_both_paths_and_deletion_selects_full(self):
        self.git("mv", "code.py", "docs-renamed.md")
        head = self.commit()
        self.assertEqual(set(policy.pr_paths(self.root, self.base, head)), {"code.py", "docs-renamed.md"})
        self.assertEqual(policy.select(self.root, "pull_request", self.event(), "")[0], "full")
        self.git("reset", "--hard", self.base)
        (self.root / "code.py").unlink()
        self.commit()
        self.assertEqual(policy.select(self.root, "pull_request", self.event(), "")[0], "full")

    def test_guard_accepts_only_clean_source_and_declared_bytecode(self):
        self.write("__pycache__/module.pyc", "bytecode")
        with contextlib.redirect_stdout(io.StringIO()):
            policy.guard(self.root, self.base)
        self.write("ignored/result.json", "{}")
        with self.assertRaises(ValueError):
            policy.guard(self.root, self.base)

    def test_guard_rejects_head_tracked_staged_untracked_and_symlink_drift(self):
        for mode in ("head", "tracked", "staged", "untracked", "symlink"):
            with self.subTest(mode=mode):
                self.git("reset", "--hard", self.base)
                self.git("clean", "-fdx")
                if mode == "head":
                    self.write("code.py", "moved")
                    self.commit()
                elif mode in {"tracked", "staged"}:
                    self.write("code.py", "changed")
                    if mode == "staged":
                        self.git("add", "code.py")
                        self.git("restore", "--source=HEAD", "--worktree", "code.py")
                elif mode == "untracked":
                    self.write("new.txt", "output")
                else:
                    (self.root / "__pycache__").mkdir()
                    (self.root / "__pycache__/link.pyc").symlink_to(self.root / "code.py")
                with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                    with contextlib.redirect_stdout(io.StringIO()):
                        policy.guard(self.root, self.base)

    def test_workflow_uses_recorded_merge_candidate_latest_runtimes_and_evidence(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("EXPECTED_SHA: ${{ github.sha }}", workflow)
        self.assertIn("ref: ${{ needs.plan.outputs.source_sha }}", workflow)
        self.assertIn("fromJSON(needs.plan.outputs.groups)", workflow)
        self.assertIn("python-version: '3.x'", workflow)
        self.assertIn("node-version: 'latest'", workflow)
        self.assertEqual(workflow.count("check-latest: true"), 3)
        self.assertNotIn("ubuntu-24.04", workflow)
        self.assertIn("fail-fast: false", workflow)
        self.assertIn('--output "$RUNNER_TEMP/hermetic-$TEST_GROUP"', workflow)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertIn("uses: actions/upload-artifact@v7", workflow)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", workflow)
        self.assertIn("always() && (matrix.group == 'core' || matrix.group == 'smoke')", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("run-integration", workflow)

    def test_actual_aggregate_commands_reject_every_incomplete_job_state(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        gate = workflow.split("\n  hermetic:\n", 1)[1]
        self.assertIn("needs: [plan, checks]", gate)
        self.assertIn("if: ${{ always() }}", gate)
        commands = "\n".join(line[10:] for line in gate.split("        run: |\n", 1)[1].splitlines())
        summary = self.root / "summary"
        for plan, checks in itertools.product(("success", "failure", "cancelled", "skipped", ""), repeat=2):
            env = dict(os.environ, PLAN_RESULT=plan, CHECKS_RESULT=checks, TIER="full", SOURCE_SHA=self.base, GITHUB_STEP_SUMMARY=str(summary))
            result = subprocess.run(["bash", "-c", commands], env=env)
            self.assertEqual(result.returncode == 0, plan == checks == "success", (plan, checks))

    def test_plan_cli_records_actual_checkout_and_rejects_wrong_candidate(self):
        event = self.root / "event.json"
        event.write_text(json.dumps({}))
        output, summary = self.root / "output", self.root / "summary"
        env = dict(os.environ, GITHUB_EVENT_PATH=str(event), GITHUB_EVENT_NAME="push", GITHUB_OUTPUT=str(output), GITHUB_STEP_SUMMARY=str(summary))
        command = ["python3", "-B", str(ROOT / "test/ci_policy.py"), "plan", "--expected-sha"]
        result = subprocess.run([*command, self.base], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tier=full", output.read_text())
        self.assertEqual(json.loads(result.stdout)["source_sha"], self.base)
        output.unlink()
        result = subprocess.run([*command, "f" * 40], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
