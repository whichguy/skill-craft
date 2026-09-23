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

    def plan(self, event_name, event, **extra):
        """Run the actual planner CLI against this fixture checkout."""
        io_dir = tempfile.TemporaryDirectory(prefix="skill-craft-ci-plan-")
        self.addCleanup(io_dir.cleanup)
        # Keep planner inputs/outputs outside the fixture so later commits omit them.
        path, output, summary = (Path(io_dir.name) / name for name in ("event.json", "output", "summary"))
        path.write_text(json.dumps(event))
        env = dict(os.environ, GITHUB_EVENT_PATH=str(path), GITHUB_EVENT_NAME=event_name,
                   GITHUB_OUTPUT=str(output), GITHUB_STEP_SUMMARY=str(summary))
        env.pop("REQUESTED_TIER", None)
        env.update(extra)
        result = subprocess.run(
            ["python3", "-B", str(ROOT / "test/ci_policy.py"), "plan", "--expected-sha", self.git("rev-parse", "HEAD")],
            cwd=self.root, env=env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout), output.read_text()

    def assert_full(self, planned, output):
        self.assertEqual(planned["tier"], "full")
        self.assertEqual(planned["groups"], policy.FULL_GROUPS)
        self.assertIn("tier=full\n", output)
        self.assertIn("groups=" + json.dumps(policy.FULL_GROUPS) + "\n", output)

    def test_every_event_selects_full(self):
        for event in ("push", "pull_request", "workflow_dispatch", "merge_group", "unknown", ""):
            with self.subTest(event=event):
                tier, reason = policy.select(event)
                self.assertEqual(tier, "full")
                self.assertIn("every hermetic group", reason)

    def test_doc_only_pull_request_plans_every_group(self):
        # These path sets once qualified for a partial tier; none is exempt now.
        for paths in (["README.md"], ["docs/report.md", "docs/inventory.csv"], ["test/README.md"]):
            with self.subTest(paths=paths):
                self.git("checkout", "-q", "--detach", self.base)
                for path in paths:
                    self.write(path, "explanation\n")
                head = self.commit()
                self.assertEqual(
                    self.git("diff", "--name-only", self.base, head).splitlines(), sorted(paths)
                )
                self.assert_full(*self.plan("pull_request", self.event(head=head)))

    def test_code_rename_deletion_and_unresolvable_pull_requests_plan_every_group(self):
        self.git("mv", "code.py", "docs-renamed.md")
        self.commit()
        self.assert_full(*self.plan("pull_request", self.event()))
        self.git("reset", "-q", "--hard", self.base)
        (self.root / "code.py").unlink()
        self.commit()
        self.assert_full(*self.plan("pull_request", self.event()))
        self.assert_full(*self.plan("pull_request", self.event(base="f" * 40)))
        self.assert_full(*self.plan("pull_request", {}))

    def test_manual_dispatch_plans_every_group_without_a_tier_input(self):
        self.assert_full(*self.plan("workflow_dispatch", {}))
        # A stale caller-supplied tier is not an input any more and cannot narrow the run.
        self.assert_full(*self.plan("workflow_dispatch", {"inputs": {"tier": "smoke"}}, REQUESTED_TIER="smoke"))

    def test_main_push_plans_every_group(self):
        self.assert_full(*self.plan("push", {}))

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
        # Full-history clones served only the retired PR path diff.
        self.assertNotIn("fetch-depth", workflow)
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
        self.assertIn("always() && matrix.group == 'core'", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertNotIn("run-integration", workflow)

    def test_workflow_has_no_partial_tier_or_manual_tier_input(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertNotIn("smoke", workflow.lower())
        self.assertNotIn("inputs", workflow)
        self.assertNotIn("REQUESTED_TIER", workflow)
        self.assertIn("run-name: CI ${{ github.event_name }}\n", workflow)
        self.assertIn("  workflow_dispatch:\n\n", workflow)

    def test_living_docs_describe_only_full_ci_and_the_release_integration_step(self):
        # Dated reports under docs/ are historical records and stay unchanged.
        for relative in ("README.md", "test/README.md", "docs/ARCHITECTURE.md", "docs/skill-release-checklist.md"):
            with self.subTest(doc=relative):
                text = (ROOT / relative).read_text()
                for stale in ("--group smoke", "--smoke", "tier=", "smoke tier", "PR smoke", "test_tier"):
                    self.assertNotIn(stale, text)
        checklist = (ROOT / "docs/skill-release-checklist.md").read_text()
        self.assertIn("bash test/run-integration.sh --list", checklist)
        self.assertIn("gh workflow run ci.yml --ref <candidate-branch>`", checklist)

    def test_actual_aggregate_commands_reject_every_incomplete_job_state(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        gate = workflow.split("\n  hermetic:\n", 1)[1]
        self.assertIn("needs: [plan, checks]", gate)
        self.assertIn("if: ${{ always() }}", gate)
        commands = "\n".join(line[10:] for line in gate.split("        run: |\n", 1)[1].splitlines())
        summary = self.root / "summary"
        for plan, checks in itertools.product(("success", "failure", "cancelled", "skipped", ""), repeat=2):
            summary.unlink(missing_ok=True)
            env = dict(os.environ, PLAN_RESULT=plan, CHECKS_RESULT=checks, TIER="full", SOURCE_SHA=self.base, GITHUB_STEP_SUMMARY=str(summary))
            result = subprocess.run(["bash", "-c", commands], env=env)
            passed = plan == checks == "success"
            self.assertEqual(result.returncode == 0, passed, (plan, checks))
            # The aggregate states the tested SHA; the plan summary lists the groups.
            self.assertEqual(summary.read_text() if summary.exists() else None,
                             f"CI full passed for `{self.base}`.\n" if passed else None)

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
        self.assertEqual(json.loads(result.stdout)["groups"], policy.FULL_GROUPS)
        self.assertIn(f"Candidate: `{self.base}`", summary.read_text())
        self.assertIn("Groups: " + ", ".join(policy.FULL_GROUPS) + "\n", summary.read_text())
        output.unlink()
        result = subprocess.run([*command, "f" * 40], cwd=self.root, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
