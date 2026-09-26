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

    def test_manual_dispatch_requires_quick_or_full(self):
        for tier in ("quick", "full"):
            self.assertEqual(policy.select(self.root, "workflow_dispatch", {}, tier)[0], tier)
        for tier in ("", "smoke"):
            with self.assertRaises(ValueError):
                policy.select(self.root, "workflow_dispatch", {}, tier)

    def test_only_a_release_commit_push_runs_full(self):
        self.write("code.py", "changed\n")
        change = self.commit()
        self.assertEqual(policy.select(self.root, "push", {"before": self.base}, ""),
                         ("quick", "pushed changes", self.base))
        self.write("CHANGELOG.md", "release\n")
        self.git("add", ".")
        self.git("commit", "-qm", "release: demo 1.0.0\n\nSkill-Craft-Release: demo@1.0.0")
        self.assertEqual(policy.select(self.root, "push", {"before": change}, "")[0], "full")
        self.assertTrue(policy.is_release(self.root))
        self.assertFalse(policy.is_release(self.root, change))
        # A release pushed under a later ordinary commit still runs full.
        self.write("code.py", "after the release\n")
        after = self.commit()
        self.assertEqual(policy.select(self.root, "push", {"before": change}, "")[0], "full")
        self.assertEqual(policy.select(self.root, "push", {}, "")[0], "quick")
        self.write("code.py", "later again\n")
        self.commit()
        self.assertEqual(policy.select(self.root, "push", {"before": after}, "")[0], "quick")

    def test_push_without_a_known_previous_commit_diffs_the_last_commit(self):
        self.write("code.py", "changed\n")
        self.commit()
        for event in ({}, {"before": "0" * 40}, {"before": "f" * 40}):
            self.assertEqual(policy.select(self.root, "push", event, "")[2], self.base)
        self.assertEqual(policy.select(self.root, "unknown", {}, "")[:1], ("quick",))

    def test_pr_diffs_from_the_merge_base_not_unrelated_main_changes(self):
        self.write("code.py", "main moved\n")
        main = self.commit()
        self.git("checkout", "-q", "--detach", self.base)
        self.write("docs/report.md", "explanation\n")
        head = self.commit()
        self.assertEqual(policy.select(self.root, "pull_request", self.event(main, head), ""),
                         ("quick", "pull request changes", self.base))
        self.assertEqual(policy.select(self.root, "pull_request", {}, "")[::2], ("quick", ""))

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
        self.assertEqual(workflow.count("check-latest: true"), 5)
        self.assertNotIn("ubuntu-24.04", workflow)
        self.assertIn("fail-fast: false", workflow)
        self.assertIn('--output "$RUNNER_TEMP/hermetic-$TEST_GROUP"', workflow)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertIn("uses: actions/upload-artifact@v7", workflow)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("run-integration", workflow)
        self.assertNotIn("--release-sync", workflow)

    def test_release_boundary_job_sees_full_history_and_the_pr_first_parent(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        job = workflow.split("\n  release-boundary:\n", 1)[1].split("\n  hermetic:\n", 1)[0]
        self.assertIn("fetch-depth: 0", job)
        self.assertIn("check-release-boundary.py --base", job)
        self.assertIn('base="$(git rev-parse HEAD^1)"', job)
        self.assertIn("node-version: 'latest'", job)
        self.assertNotIn("needs:", job)

    def test_actual_aggregate_commands_reject_every_incomplete_job_state(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        gate = workflow.split("\n  hermetic:\n", 1)[1]
        self.assertIn("needs: [plan, checks, release-boundary]", gate)
        self.assertIn("if: ${{ always() }}", gate)
        commands = "\n".join(line[10:] for line in gate.split("        run: |\n", 1)[1].splitlines())
        summary = self.root / "summary"
        for plan, checks, boundary in itertools.product(("success", "failure", "cancelled", "skipped", ""), repeat=3):
            env = dict(os.environ, PLAN_RESULT=plan, CHECKS_RESULT=checks, BOUNDARY_RESULT=boundary, TIER="full",
                       SOURCE_SHA=self.base, GITHUB_STEP_SUMMARY=str(summary))
            result = subprocess.run(["bash", "-c", commands], env=env)
            self.assertEqual(result.returncode == 0, plan == checks == boundary == "success", (plan, checks, boundary))

    def test_plan_cli_records_actual_checkout_and_rejects_wrong_candidate(self):
        event = self.root / "event.json"
        event.write_text(json.dumps({}))
        output, summary = self.root / "output", self.root / "summary"
        env = dict(os.environ, GITHUB_EVENT_PATH=str(event), GITHUB_EVENT_NAME="push", GITHUB_OUTPUT=str(output), GITHUB_STEP_SUMMARY=str(summary))
        command = ["python3", "-B", str(ROOT / "test/ci_policy.py"), "plan", "--expected-sha"]
        result = subprocess.run([*command, self.base], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tier=quick", output.read_text())
        self.assertIn('groups=["quick"]', output.read_text())
        self.assertEqual(json.loads(result.stdout)["source_sha"], self.base)
        output.unlink()
        result = subprocess.run([*command, "f" * 40], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
