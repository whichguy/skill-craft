#!/usr/bin/env python3
"""The shipped ShipLoop package, run the way a stranger's machine would run it (portability audit, Round 5).

Every other ShipLoop suite runs the source tree inside a developer's own environment: a PATH with Homebrew and the
newest python3, a configured git identity, a home directory full of settings.  This one runs the *built package copy*
(``package_build``, the same bytes the marketplace ships) with a scrubbed environment and the interpreter under test (the
floor, 3.9, in CI's python-floor leg): ``shiploop --help`` and ``workspace start`` on a repository with no git identity,
and every hook entry with ``python3`` absent from PATH, where each must exit 0 and print nothing.  It is the hermetic
form of ``docs/experiments/clean-install-20261101/probes.sh``, minus the network install and the containers; the live
sessions that check the rest are in that folder's README.

The progress observer is switched off (``SHIPLOOP_PROGRESS=off``): it starts a detached process, which a hermetic suite
must not leave behind.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import package_build
import state_home

state_home.isolate()

SCRIPTS = package_build.plugins() / "skill-craft" / "skills" / "shiploop" / "scripts"
HOOK_ENTRIES = (
    "shiploop-keepalive-observe",
    "shiploop-keepalive-stop",
    "shiploop-keepalive-session-end",
    "shiploop-skill-call",
    "shiploop-status-hook",
)
# What an entry needs from the system besides python3: a shell, and the few tools the shell wrappers call.
COREUTILS = ("sh", "cat", "dirname", "grep", "tr", "head", "env", "sed")
PAYLOAD = '{"hook_event_name": "PostToolUse", "session_id": "s1", "cwd": "/tmp"}'


def scrubbed_env(home: Path, path: str) -> dict:
    """Only what a bare machine has: a home, a PATH, and the switches this suite needs; nothing inherited."""
    return {
        "HOME": str(home),
        "PATH": path,
        "PYTHONDONTWRITEBYTECODE": "1",
        "SHIPLOOP_PROGRESS": "off",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
    }


def tree(root: Path) -> set:
    return {str(p.relative_to(root)) for p in root.rglob("*")}


class CleanConsumerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.git = shutil.which("git")
        if cls.git is None:
            raise unittest.SkipTest("git is not installed")
        cls.tmp = Path(tempfile.mkdtemp(prefix="shiploop-consumer-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, True)
        cls.home = cls.tmp / "home"
        cls.home.mkdir()
        cls.bare_path = str(cls.tmp / "coreutils-only")
        (cls.tmp / "coreutils-only").mkdir()
        for tool in COREUTILS:
            found = shutil.which(tool)
            if found is None:
                raise unittest.SkipTest(f"{tool} is not installed")
            os.symlink(found, cls.tmp / "coreutils-only" / tool)
        # python3 is present for the CLI tests: only the interpreter under test, so no other python can answer.
        cls.python_dir = cls.tmp / "python"
        cls.python_dir.mkdir()
        os.symlink(sys.executable, cls.python_dir / "python3")
        cls.cli_path = os.pathsep.join([str(cls.python_dir), os.path.dirname(cls.git), cls.bare_path])

    def run_entry(self, argv: list, *, path: str, cwd: Path, stdin: str = "") -> subprocess.CompletedProcess:
        return subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=120, cwd=str(cwd),
                              env=scrubbed_env(self.home, path))

    def test_help_runs_on_the_interpreter_under_test(self) -> None:
        before = tree(SCRIPTS)
        done = self.run_entry([str(self.python_dir / "python3"), str(SCRIPTS / "shiploop"), "--help"],
                              path=self.cli_path, cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("usage:", done.stdout)
        self.assertEqual(tree(SCRIPTS), before, "running the package wrote into it (bytecode or state)")

    def test_workspace_start_prints_a_packet_with_no_git_identity(self) -> None:
        repo = self.tmp / "repo"
        repo.mkdir()
        # The fixture needs an identity to make its one commit; the run under test gets none (scrubbed_env has no
        # GIT_AUTHOR_* and its global config is /dev/null), as a fresh machine would.
        fixture = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
        subprocess.run([self.git, "init", "-q", str(repo)], check=True, env=fixture)
        subprocess.run([self.git, "-C", str(repo), "commit", "-q", "--allow-empty", "-m", "init"], check=True, env=fixture)
        done = self.run_entry([str(self.python_dir / "python3"), str(SCRIPTS / "shiploop"), "workspace", "start",
                               "--repo", str(repo), "--prompt", "Create hello.py that prints Hello, world!"],
                              path=self.cli_path, cwd=self.tmp)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("ShipLoop navigator |", done.stdout)
        self.assertEqual(done.stderr.strip(), "", "a clean start printed a notice: " + done.stderr)

    def test_every_hook_entry_is_silent_and_succeeds_without_python3(self) -> None:
        for name in HOOK_ENTRIES:
            with self.subTest(entry=name):
                done = self.run_entry([str(SCRIPTS / name)], path=self.bare_path, cwd=self.tmp, stdin=PAYLOAD)
                self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""), name)


if __name__ == "__main__":
    unittest.main()
