#!/usr/bin/env python3
"""The release guard must prevent publication when any precondition fails."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/release-push.py"


class ReleasePushTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="release-push-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "candidate"
        self.remote = self.root / "remote.git"
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith("GIT_")}
        self.env.update(HOME=str(self.home), XDG_CONFIG_HOME=str(self.home / "config"))
        self.git(self.root, "init", "--bare", str(self.remote))
        self.git(self.root, "init", "-b", "main", str(self.repo))
        self.git(self.repo, "config", "user.name", "Release Test")
        self.git(self.repo, "config", "user.email", "release@example.invalid")
        self.git(self.repo, "config", "commit.gpgsign", "false")
        (self.repo / "data").write_text("base\n")
        self.git(self.repo, "add", "data")
        self.git(self.repo, "commit", "-m", "base")
        self.base = self.git(self.repo, "rev-parse", "HEAD")
        self.git(self.repo, "remote", "add", "origin", str(self.remote))
        self.git(self.repo, "push", "origin", "HEAD:refs/heads/main")
        (self.repo / "data").write_text("candidate\n")
        self.git(self.repo, "commit", "-am", "candidate")
        self.head = self.git(self.repo, "rev-parse", "HEAD")
        self.tree = self.git(self.repo, "rev-parse", "HEAD^{tree}")

    def git(self, cwd, *args):
        result = subprocess.run(["git", *args], cwd=cwd, env=self.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def invoke(self, *extra, checks=None, env=None):
        commands = checks if checks is not None else [[sys.executable, "-c", "pass"]]
        argv = [sys.executable, str(SCRIPT), "--repo", str(self.repo),
                "--expected-head", self.head, "--expected-tree", self.tree,
                "--expected-base", self.base]
        for command in commands:
            argv.extend(["--check", json.dumps(command)])
        return subprocess.run([*argv, *extra], env=env or self.env, capture_output=True,
                              text=True, timeout=30)

    def remote_head(self):
        return self.git(self.remote, "rev-parse", "refs/heads/main")

    def assert_blocked(self, result, *, expected_remote=None):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.remote_head(), expected_remote or self.base)

    def test_pushes_exact_candidate_after_success(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt["status"], "pushed")
        self.assertEqual(receipt["head"], self.head)
        self.assertEqual(self.remote_head(), self.head)

    def test_failed_check_stops_following_check_and_push(self):
        marker = self.root / "must-not-run"
        result = self.invoke(checks=[[sys.executable, "-c", "raise SystemExit(7)"],
                                    [sys.executable, "-c", f"open({str(marker)!r}, 'w').close()"]])
        self.assert_blocked(result)
        self.assertFalse(marker.exists())
        self.assertIn("check 1 failed (7)", result.stderr)

    def test_wrong_head_and_tree_block_before_checks(self):
        for option, value in (("--expected-head", self.base), ("--expected-tree", self.base)):
            with self.subTest(option=option):
                self.assert_blocked(self.invoke(option, value))

    def test_dirty_tracked_untracked_and_staged_checkouts_block(self):
        (self.repo / "data").write_text("dirty\n")
        self.assert_blocked(self.invoke())
        self.git(self.repo, "add", "data")
        self.assert_blocked(self.invoke())
        self.git(self.repo, "reset", "--hard", self.head)
        (self.repo / "new-file").write_text("dirty\n")
        self.assert_blocked(self.invoke())

    def test_check_mutation_of_files_or_head_blocks(self):
        self.assert_blocked(self.invoke(checks=[[sys.executable, "-c", "open('data', 'w').write('mutation')"]]))
        self.git(self.repo, "reset", "--hard", self.head)
        self.assert_blocked(self.invoke(checks=[["git", "reset", "--hard", self.base]]))

    def divergent_commit(self):
        # Manufacture a valid sibling commit without moving the candidate checkout.
        return self.git(self.repo, "commit-tree", "-m", "concurrent", "-p", self.base, self.tree)

    def publish_divergent(self):
        other = self.divergent_commit()
        self.git(self.repo, "push", "origin", f"{other}:refs/heads/main")
        return other

    def test_remote_advance_before_or_during_checks_blocks(self):
        other = self.publish_divergent()
        self.assert_blocked(self.invoke(), expected_remote=other)
        self.git(self.remote, "update-ref", "refs/heads/main", self.base)
        result = self.invoke(checks=[["git", "push", "origin", f"{other}:refs/heads/main"]])
        self.assert_blocked(result, expected_remote=other)

    def test_push_race_is_rejected_without_force(self):
        other = self.divergent_commit()
        hook = self.repo / ".git/hooks/pre-push"
        # Hook runs after the guard's remote check; publish a sibling first.
        hook.write_text("#!/bin/sh\n" +
                        f"git -c core.hooksPath=/dev/null push origin {other}:refs/heads/main >&2\n")
        hook.chmod(0o755)
        self.assert_blocked(self.invoke(), expected_remote=other)

    def test_multiple_push_destinations_refuse(self):
        self.git(self.repo, "config", "--add", "remote.origin.pushurl", str(self.remote))
        self.git(self.repo, "config", "--add", "remote.origin.pushurl", str(self.root / "other.git"))
        self.assert_blocked(self.invoke())

    def test_git_context_override_refuses(self):
        env = dict(self.env, GIT_INDEX_FILE=str(self.root / "other-index"))
        self.assert_blocked(self.invoke(env=env))

    def test_missing_checks_and_shell_string_refuse(self):
        self.assert_blocked(self.invoke(checks=[]))
        self.assert_blocked(self.invoke(checks=["git status; git push"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
