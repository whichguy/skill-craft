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

    def _prepare_release_candidate(self, version="4.20.1", *, bad_sha=False):
        zip_helper = Path(__file__).resolve().parents[1] / "scripts" / "antigravity-zip.py"
        pkg = self.repo / "plugins" / "skill-craft"
        (pkg / ".antigravity-plugin").mkdir(parents=True, exist_ok=True)
        (pkg / ".antigravity-plugin" / "plugin.json").write_text(
            json.dumps({"name": "skill-craft", "version": version}) + "\n",
            encoding="utf-8",
        )
        (pkg / "skills" / "shiploop").mkdir(parents=True, exist_ok=True)
        (pkg / "skills" / "shiploop" / "SKILL.md").write_text(
            f"---\nname: shiploop\nversion: 2.21.0\n---\n",
            encoding="utf-8",
        )
        (self.repo / "scripts").mkdir(exist_ok=True)
        (self.repo / "scripts" / "antigravity-zip.py").write_text(
            zip_helper.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (self.repo / "catalog").mkdir(exist_ok=True)
        (self.repo / "catalog" / "skill-craft-plugin.json").write_text(
            json.dumps({"name": "skill-craft", "version": version}) + "\n",
            encoding="utf-8",
        )
        sha_out = subprocess.run(
            [sys.executable, "-B", str(self.repo / "scripts" / "antigravity-zip.py"), "--source", str(pkg), "--sha256"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        (self.repo / ".antigravity-plugin").mkdir(exist_ok=True)
        (self.repo / ".antigravity-plugin" / "marketplace.json").write_text(
            json.dumps({
                "name": "whichguy",
                "plugins": [{
                    "name": "skill-craft",
                    "version": version,
                    "source": {
                        "type": "archive",
                        "url": f"https://github.com/whichguy/skill-craft/releases/download/v{version}/skill-craft-{version}.zip",
                        "sha256": ("0" * 64) if bad_sha else sha_out,
                    },
                }],
            }) + "\n",
            encoding="utf-8",
        )
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-q", "-m", f"release: skill-craft {version}",
                 "-m", f"Skill-Craft-Release: skill-craft@{version}")
        self.head = self.git(self.repo, "rev-parse", "HEAD")
        self.tree = self.git(self.repo, "rev-parse", "HEAD^{tree}")
        return sha_out

    def _write_fake_gh(self, *, release_exists=False):
        gh_log = self.root / "gh-calls.jsonl"
        fake_gh = self.root / "gh"
        fake_gh.write_text(
            f"""#!{sys.executable} -B
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with Path({str(gh_log)!r}).open("a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
if args[:2] == ["release", "view"]:
    raise SystemExit(0 if {release_exists!r} else 1)
if args[:2] in (["release", "create"], ["release", "upload"]):
    asset = Path(args[3])
    assert asset.is_file(), f"missing asset: {{asset}}"
    raise SystemExit(0)
raise SystemExit(2)
""",
            encoding="utf-8",
        )
        fake_gh.chmod(0o755)
        env = dict(self.env, GH_BIN=str(fake_gh))
        return env, gh_log

    def test_github_release_creates_and_clobber_updates_asset(self):
        sha = self._prepare_release_candidate("4.20.1")
        env, gh_log = self._write_fake_gh(release_exists=False)
        res = self.invoke("--github-release", "require", "--github-repo", "whichguy/skill-craft", env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        receipt = json.loads(res.stdout)
        self.assertEqual(receipt["github_release"]["action"], "created")
        self.assertEqual(receipt["github_release"]["tag"], "v4.20.1")
        self.assertEqual(receipt["github_release"]["asset"], "skill-craft-4.20.1.zip")
        self.assertEqual(receipt["github_release"]["sha256"], sha)
        calls = [json.loads(line) for line in gh_log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(calls[0][:3], ["release", "view", "v4.20.1"])
        self.assertEqual(calls[1][:3], ["release", "create", "v4.20.1"])

        # Existing tag/release uses idempotent `gh release upload --clobber`.
        self.git(self.remote, "update-ref", "refs/heads/main", self.base)
        env2, gh_log2 = self._write_fake_gh(release_exists=True)
        gh_log2.unlink()
        res2 = self.invoke("--github-release", "require", "--github-repo", "whichguy/skill-craft", env=env2)
        self.assertEqual(res2.returncode, 0, res2.stderr)
        self.assertEqual(json.loads(res2.stdout)["github_release"]["action"], "updated")
        calls2 = [json.loads(line) for line in gh_log2.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(calls2[1][:3], ["release", "upload", "v4.20.1"])
        self.assertIn("--clobber", calls2[1])

    def test_github_release_sha_mismatch_blocks_before_push(self):
        self._prepare_release_candidate("4.20.1", bad_sha=True)
        env, gh_log = self._write_fake_gh(release_exists=False)
        res = self.invoke("--github-release", "require", "--github-repo", "whichguy/skill-craft", env=env)
        self.assert_blocked(res)
        self.assertIn("sha256", res.stderr)
        self.assertFalse(gh_log.exists())

    def test_refresh_hosts_flag_runs_release_refresh_after_push(self):
        refresh_log = self.root / "refresh-args.json"
        (self.repo / "scripts").mkdir(exist_ok=True)
        refresh_script = self.repo / "scripts" / "release-refresh.py"
        refresh_script.write_text(
            f"""#!/usr/bin/env python3
import json, sys
from pathlib import Path
Path({str(refresh_log)!r}).write_text(json.dumps(sys.argv[1:]), encoding="utf-8")
print(json.dumps({{"status": "refreshed", "hosts": {{"claude": {{"status": "ok"}}}}}}))
""",
            encoding="utf-8",
        )
        refresh_script.chmod(0o755)
        self.git(self.repo, "add", "scripts/release-refresh.py")
        self.git(self.repo, "commit", "-q", "-m", "chore: stub refresh")
        self.head = self.git(self.repo, "rev-parse", "HEAD")
        self.tree = self.git(self.repo, "rev-parse", "HEAD^{tree}")

        res = self.invoke("--refresh-hosts", "--refresh-host", "claude", "--allow-live")
        self.assertEqual(res.returncode, 0, res.stderr)
        receipt = json.loads(res.stdout)
        self.assertEqual(receipt["host_refresh"]["status"], "refreshed")
        recorded = json.loads(refresh_log.read_text(encoding="utf-8"))
        self.assertIn("--host", recorded)
        self.assertIn("claude", recorded)
        self.assertIn("--allow-live", recorded)
        self.assertEqual(self.remote_head(), self.head)


if __name__ == "__main__":
    unittest.main(verbosity=2)
