#!/usr/bin/env python3
"""Hermetic real-Git tests for ShipLoop's narrow parallel-chain boundary."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
GIT = shutil.which("git")
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_chain_git as chain_git  # noqa: E402


class ShipLoopChainGitTests(unittest.TestCase):
    """Use linked worktrees so private-index and merge-destination boundaries show."""

    def setUp(self) -> None:
        if GIT is None:
            self.fail("Git must be available on PATH for real chain Git coverage")
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-chain-git-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.primary = self.base / "main checkout"
        self.primary.mkdir()
        self.env = {
            **os.environ,
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        self.git("init", "-q", cwd=self.primary)
        self.git("branch", "-M", "main", cwd=self.primary)
        self.git("config", "user.name", "ShipLoop Chain Test", cwd=self.primary)
        self.git("config", "user.email", "shiploop-chain@example.invalid", cwd=self.primary)
        self.git("config", "commit.gpgsign", "false", cwd=self.primary)
        self.git("config", "core.hooksPath", os.devnull, cwd=self.primary)
        (self.primary / "baseline.txt").write_text("baseline\n", encoding="utf-8")
        self.git("add", "baseline.txt", cwd=self.primary)
        self.git("commit", "-qm", "baseline", cwd=self.primary)
        self.main_head = self.git("rev-parse", "HEAD", cwd=self.primary).stdout.strip()

        self.initiating = self.base / "initiating linked checkout"
        self.git(
            "worktree",
            "add",
            "-q",
            "-b",
            "feature/initiating",
            str(self.initiating),
            "main",
            cwd=self.primary,
        )
        self.assertTrue((self.initiating / ".git").is_file())
        self.worktrees = self.base / "chain workers" / ".work-trees"
        self.worktrees.mkdir(parents=True)
        self.initial = self.call(chain_git.target_identity, self.initiating)

    def git(
        self,
        *args: str,
        cwd: Path | None = None,
        code: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(GIT), "-C", str(cwd or self.primary), *args],
            text=True,
            capture_output=True,
            timeout=30,
            env=self.env,
            shell=False,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def call(self, function, *args, **kwargs):
        with mock.patch.dict(os.environ, self.env, clear=False):
            return function(*args, **kwargs)

    def plan(
        self,
        *,
        workspace_parent: Path | None = None,
        run_id: str | None = None,
        attempt: str | None = None,
        base_commit: str | None = None,
    ) -> dict:
        return self.call(
            chain_git.allocation_plan,
            self.initial,
            workspace_parent or self.worktrees,
            run_id or str(uuid.uuid4()),
            attempt or str(uuid.uuid4()),
            base_commit or self.initial["head"],
        )

    def commit_worker(self, worker: Path, message: str) -> str:
        self.git("add", "-A", cwd=worker)
        self.git("commit", "-qm", message, cwd=worker)
        return self.git("rev-parse", "HEAD", cwd=worker).stdout.strip()

    def contribution(self, name: str) -> str:
        plan = self.plan()
        worker = self.call(chain_git.allocate, plan)
        root = Path(worker["repo"])
        (root / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
        return self.commit_worker(root, f"{name} contribution")

    def compatible_contributions(self) -> tuple[str, str]:
        plan = self.plan()
        worker = self.call(chain_git.allocate, plan)
        worker_root = Path(worker["repo"])
        (worker_root / "middle.txt").write_text("middle\n", encoding="utf-8")
        middle = self.commit_worker(worker_root, "middle contribution")

        descendant_root = self.base / "compatible descendant"
        self.git(
            "worktree",
            "add",
            "-q",
            "-b",
            "test/compatible-descendant",
            str(descendant_root),
            middle,
            cwd=self.primary,
        )
        (descendant_root / "descendant.txt").write_text("descendant\n", encoding="utf-8")
        descendant = self.commit_worker(descendant_root, "descendant contribution")
        return middle, descendant

    def run_fast_forward_process(
        self,
        identity: dict,
        commit: str,
        *,
        entered: Path | None = None,
        release: Path | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> subprocess.Popen[str]:
        script = """
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, os.environ["CHAIN_GIT_SCRIPTS"])
import shiploop_chain_git as chain_git

identity = json.loads(os.environ["CHAIN_GIT_IDENTITY"])
commit = os.environ["CHAIN_GIT_COMMIT"]
entered = os.environ.get("CHAIN_GIT_ENTERED")
release = os.environ.get("CHAIN_GIT_RELEASE")
if entered and release:
    original_validate_target = chain_git.validate_target
    validations = 0
    def pause_after_final_validation(*args, **kwargs):
        global validations
        result = original_validate_target(*args, **kwargs)
        validations += 1
        if validations == 2:
            Path(entered).write_text("entered\\n", encoding="ascii")
            deadline = time.monotonic() + 15
            while not Path(release).exists():
                if time.monotonic() >= deadline:
                    raise RuntimeError("chain Git test barrier timed out")
                time.sleep(0.01)
        return result
    chain_git.validate_target = pause_after_final_validation

try:
    destination = chain_git.fast_forward(identity, commit)
except chain_git.ChainGitError as exc:
    print(json.dumps({"ok": False, "error": str(exc)}))
    raise SystemExit(2)
else:
    print(json.dumps({"ok": True, "head": destination["head"]}))
"""
        environment = {
            **self.env,
            "CHAIN_GIT_SCRIPTS": str(SCRIPTS),
            "CHAIN_GIT_IDENTITY": json.dumps(identity),
            "CHAIN_GIT_COMMIT": commit,
        }
        if entered is not None:
            environment["CHAIN_GIT_ENTERED"] = str(entered)
        if release is not None:
            environment["CHAIN_GIT_RELEASE"] = str(release)
        if extra_env:
            environment.update(extra_env)
        return subprocess.Popen(
            [sys.executable, "-c", script],
            cwd=self.primary,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
        )

    def process_result(self, process: subprocess.Popen[str]) -> tuple[int, dict, str]:
        stdout, stderr = process.communicate(timeout=20)
        return process.returncode, json.loads(stdout), stderr

    def wait_for_path(self, path: Path) -> None:
        deadline = time.monotonic() + 15
        while not path.exists():
            if time.monotonic() >= deadline:
                self.fail(f"timed out waiting for {path}")
            time.sleep(0.01)

    def wait_for_head(self, expected: str) -> None:
        deadline = time.monotonic() + 15
        while True:
            if self.git("rev-parse", "HEAD", cwd=self.initiating).stdout.strip() == expected:
                return
            if time.monotonic() >= deadline:
                self.fail(f"timed out waiting for initiating HEAD {expected}")
            time.sleep(0.02)

    def test_linked_initiator_gets_independent_worker_indexes_and_fast_forwards_only_feature(self) -> None:
        first_plan = self.plan(
            run_id="11111111-1111-4111-8111-111111111111",
            attempt="22222222-2222-4222-8222-222222222222",
        )
        second_plan = self.plan(
            run_id="33333333-3333-4333-8333-333333333333",
            attempt="44444444-4444-4444-8444-444444444444",
        )
        self.assertEqual(set(first_plan), {"target", "path", "branch", "base_commit"})
        self.assertEqual(first_plan, self.plan(
            run_id="11111111-1111-4111-8111-111111111111",
            attempt="22222222-2222-4222-8222-222222222222",
        ))

        first = self.call(chain_git.allocate, first_plan)
        second = self.call(chain_git.allocate, second_plan)
        first_root = Path(first["repo"])
        second_root = Path(second["repo"])
        self.assertNotEqual(first["git_dir"], self.initial["git_dir"])
        self.assertNotEqual(first["git_dir"], second["git_dir"])
        self.assertEqual(first["common_dir"], self.initial["common_dir"])
        self.assertEqual(second["common_dir"], self.initial["common_dir"])
        self.assertNotEqual(
            self.git("rev-parse", "--git-path", "index", cwd=first_root).stdout.strip(),
            self.git("rev-parse", "--git-path", "index", cwd=second_root).stdout.strip(),
        )

        (first_root / "feature.txt").write_text("from first worker\n", encoding="utf-8")
        self.git("add", "feature.txt", cwd=first_root)
        self.assertEqual(self.git("diff", "--cached", "--name-only", cwd=second_root).stdout, "")
        self.assertEqual(self.git("diff", "--cached", "--name-only", cwd=self.initiating).stdout, "")
        commit = self.commit_worker(first_root, "worker contribution")

        inspected = self.call(chain_git.inspect_contribution, first_plan, commit)
        self.assertEqual(inspected["commit"], commit)
        self.assertEqual(inspected["identity"]["head"], commit)
        self.assertEqual(self.call(chain_git.recover_allocation, first_plan), inspected["identity"])
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.allocate, first_plan)

        destination = self.call(chain_git.fast_forward, self.initial, commit)
        self.assertEqual(destination["head"], commit)
        self.assertEqual((self.initiating / "feature.txt").read_text(encoding="utf-8"), "from first worker\n")
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.primary).stdout.strip(), self.main_head)
        self.assertEqual(self.git("symbolic-ref", "--short", "HEAD", cwd=self.primary).stdout.strip(), "main")
        self.assertFalse((self.primary / "feature.txt").exists())

    def test_plan_rejects_nested_symlink_and_foreign_workspace_containers(self) -> None:
        scoped_parent = self.worktrees / "repo-key"
        scoped_parent.mkdir()
        scoped = self.plan(workspace_parent=scoped_parent)
        self.assertEqual(Path(scoped["path"]).parent, scoped_parent.resolve())

        nested = self.initiating / ".work-trees"
        nested.mkdir()
        with self.assertRaises(chain_git.ChainGitError):
            self.plan(workspace_parent=nested)

        redirect_root = self.base / "redirect"
        redirect_root.mkdir()
        redirected = redirect_root / ".work-trees"
        redirected.symlink_to(self.worktrees, target_is_directory=True)
        with self.assertRaises(chain_git.ChainGitError):
            self.plan(workspace_parent=redirected)
        redirected_ancestor = self.base / "redirected ancestor"
        redirected_ancestor.symlink_to(self.worktrees.parent, target_is_directory=True)
        with self.assertRaises(chain_git.ChainGitError):
            self.plan(workspace_parent=redirected_ancestor / ".work-trees")

        foreign = self.base / "foreign repository"
        foreign.mkdir()
        self.git("init", "-q", cwd=foreign)
        foreign_parent = foreign / ".work-trees"
        foreign_parent.mkdir()
        with self.assertRaises(chain_git.ChainGitError):
            self.plan(workspace_parent=foreign_parent)

        metadata_parent = foreign / ".git" / ".work-trees"
        metadata_parent.mkdir()
        with self.assertRaises(chain_git.ChainGitError):
            self.plan(workspace_parent=metadata_parent)

    def test_identity_rejects_dirty_branch_drift_and_clean_paused_operation_markers(self) -> None:
        (self.initiating / "untracked.txt").write_text("dirty\n", encoding="utf-8")
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.target_identity, self.initiating)
        (self.initiating / "untracked.txt").unlink()

        self.git("checkout", "-qb", "feature/drift", cwd=self.initiating)
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.validate_target, self.initial)

        current = self.call(chain_git.target_identity, self.initiating)
        for marker in (
            "MERGE_HEAD",
            "CHERRY_PICK_HEAD",
            "REVERT_HEAD",
            "REBASE_HEAD",
            "rebase-apply",
            "rebase-merge",
            "sequencer",
            "BISECT_START",
        ):
            path = Path(current["git_dir"]) / marker
            with self.subTest(marker=marker):
                if marker in {"rebase-apply", "rebase-merge", "sequencer"}:
                    path.mkdir()
                else:
                    path.write_text(self.initial["head"] + "\n", encoding="ascii")
                try:
                    with self.assertRaises(chain_git.ChainGitError):
                        self.call(chain_git.target_identity, self.initiating)
                finally:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()

    def test_fast_forward_rejects_clean_target_head_drift_and_non_descendant_return(self) -> None:
        plan = self.plan()
        worker = self.call(chain_git.allocate, plan)
        worker_root = Path(worker["repo"])
        (worker_root / "worker.txt").write_text("worker change\n", encoding="utf-8")
        contribution = self.commit_worker(worker_root, "worker contribution")

        (self.initiating / "target.txt").write_text("target drift\n", encoding="utf-8")
        target_head = self.commit_worker(self.initiating, "target-only change")
        self.assertEqual(self.git("status", "--porcelain", cwd=self.initiating).stdout, "")
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.fast_forward, self.initial, contribution)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.initiating).stdout.strip(), target_head)

        current = self.call(chain_git.target_identity, self.initiating)
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.fast_forward, current, contribution)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=self.initiating).stdout.strip(), target_head)

    def test_inspection_requires_a_clean_exact_worker_head(self) -> None:
        plan = self.plan()
        worker = self.call(chain_git.allocate, plan)
        root = Path(worker["repo"])
        (root / "feature.txt").write_text("not committed yet\n", encoding="utf-8")
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.inspect_contribution, plan, self.initial["head"])

        commit = self.commit_worker(root, "exact contribution")
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.inspect_contribution, plan, commit[:12])
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.inspect_contribution, plan, self.initial["head"])
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.fast_forward, self.initial, commit[:12])

    def test_fast_forward_rejects_concurrent_and_stale_returns_in_separate_processes(self) -> None:
        middle, descendant = self.compatible_contributions()
        entered = self.base / "first-return-entered"
        release = self.base / "release-first-return"
        first = self.run_fast_forward_process(
            self.initial,
            descendant,
            entered=entered,
            release=release,
        )
        try:
            self.wait_for_path(entered)

            competing = self.run_fast_forward_process(self.initial, middle)
            code, result, stderr = self.process_result(competing)
            self.assertEqual(code, 2, stderr)
            self.assertFalse(result["ok"])
            self.assertIn("busy with another cooperative chain return", result["error"])
            self.assertEqual(
                self.git("rev-parse", "HEAD", cwd=self.initiating).stdout.strip(),
                self.initial["head"],
            )

            release.touch()
            code, result, stderr = self.process_result(first)
            self.assertEqual(code, 0, stderr)
            self.assertEqual(result, {"ok": True, "head": descendant})
            self.assertEqual(
                self.git("rev-parse", "HEAD", cwd=self.initiating).stdout.strip(),
                descendant,
            )

            stale = self.run_fast_forward_process(self.initial, middle)
            code, result, stderr = self.process_result(stale)
            self.assertEqual(code, 2, stderr)
            self.assertFalse(result["ok"])
            self.assertIn("target HEAD drifted", result["error"])
            self.assertEqual(
                self.git("rev-parse", "HEAD", cwd=self.initiating).stdout.strip(),
                descendant,
            )
        finally:
            release.touch(exist_ok=True)
            if first.poll() is None:
                first.kill()
                first.communicate(timeout=20)

    def test_fast_forward_releases_persistent_lock_after_a_failed_return(self) -> None:
        contribution = self.contribution("successful-after-failure")
        lock_path = Path(self.initial["git_dir"]) / chain_git._RETURN_LOCK_NAME
        missing = "0" * len(self.initial["head"])
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.fast_forward, self.initial, missing)
        self.assertTrue(lock_path.is_file())

        destination = self.call(chain_git.fast_forward, self.initial, contribution)
        self.assertEqual(destination["head"], contribution)

    def test_fast_forward_rejects_unsafe_or_caller_directed_lock_files(self) -> None:
        contribution = self.contribution("unsafe-lock")
        lock_path = Path(self.initial["git_dir"]) / chain_git._RETURN_LOCK_NAME
        caller_directed = self.base / "caller-directed.lock"
        altered = dict(self.initial)
        altered["git_dir"] = str(caller_directed)
        with self.assertRaises(chain_git.ChainGitError):
            self.call(chain_git.fast_forward, altered, contribution)
        self.assertFalse(caller_directed.exists())
        self.assertTrue(lock_path.is_file())
        lock_path.unlink()

        def assert_rejected_without_mutation() -> None:
            with self.assertRaises(chain_git.ChainGitError):
                self.call(chain_git.fast_forward, self.initial, contribution)
            self.assertEqual(
                self.git("rev-parse", "HEAD", cwd=self.initiating).stdout.strip(),
                self.initial["head"],
            )

        symlink_target = self.base / "symlink-target.lock"
        symlink_target.write_text("unsafe\n", encoding="ascii")
        lock_path.symlink_to(symlink_target)
        try:
            assert_rejected_without_mutation()
        finally:
            if os.path.lexists(lock_path):
                lock_path.unlink()
            symlink_target.unlink()

        os.mkfifo(lock_path, 0o600)
        try:
            started = time.monotonic()
            assert_rejected_without_mutation()
            self.assertLess(time.monotonic() - started, 5)
        finally:
            if os.path.lexists(lock_path):
                lock_path.unlink()

        hardlink_source = self.base / "hardlink-source.lock"
        hardlink_source.write_text("unsafe\n", encoding="ascii")
        os.link(hardlink_source, lock_path)
        try:
            self.assertEqual(lock_path.stat().st_nlink, 2)
            assert_rejected_without_mutation()
        finally:
            if os.path.lexists(lock_path):
                lock_path.unlink()
            hardlink_source.unlink()

    def test_merge_child_keeps_target_lock_after_parent_process_dies(self) -> None:
        middle, descendant = self.compatible_contributions()
        wrapper_dir = self.base / "git-wrapper"
        wrapper_dir.mkdir()
        entered = self.base / "merge-child-entered"
        release = self.base / "release-merge-child"
        wrapper = wrapper_dir / "git"
        wrapper.write_text(
            """#!/usr/bin/env python3
import os
from pathlib import Path
import sys
import time

if os.environ.get(\"SHIPLOOP_TEST_HOLD_MERGE\") == \"1\" and \"merge\" in sys.argv:
    entered = Path(os.environ[\"SHIPLOOP_TEST_MERGE_ENTERED\"])
    release = Path(os.environ[\"SHIPLOOP_TEST_MERGE_RELEASE\"])
    entered.write_text(\"entered\\n\", encoding=\"ascii\")
    deadline = time.monotonic() + 15
    while not release.exists():
        if time.monotonic() >= deadline:
            raise SystemExit(73)
        time.sleep(0.01)

real_git = os.environ[\"SHIPLOOP_TEST_REAL_GIT\"]
os.execv(real_git, [real_git, *sys.argv[1:]])
""",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        wrapper_environment = {
            "PATH": f"{wrapper_dir}{os.pathsep}{self.env['PATH']}",
            "SHIPLOOP_TEST_REAL_GIT": str(GIT),
            "SHIPLOOP_TEST_HOLD_MERGE": "1",
            "SHIPLOOP_TEST_MERGE_ENTERED": str(entered),
            "SHIPLOOP_TEST_MERGE_RELEASE": str(release),
        }
        first = self.run_fast_forward_process(self.initial, descendant, extra_env=wrapper_environment)
        try:
            self.wait_for_path(entered)
            first.kill()
            first.wait(timeout=20)
            self.assertEqual(first.returncode, -signal.SIGKILL)

            competing = self.run_fast_forward_process(
                self.initial,
                middle,
                extra_env={**wrapper_environment, "SHIPLOOP_TEST_HOLD_MERGE": "0"},
            )
            code, result, stderr = self.process_result(competing)
            self.assertEqual(code, 2, stderr)
            self.assertFalse(result["ok"])
            self.assertIn("busy with another cooperative chain return", result["error"])
            self.assertEqual(
                self.git("rev-parse", "HEAD", cwd=self.initiating).stdout.strip(),
                self.initial["head"],
            )

            release.touch()
            self.wait_for_head(descendant)
        finally:
            release.touch(exist_ok=True)
            if first.poll() is None:
                first.kill()
                first.wait(timeout=20)
            first.communicate(timeout=20)


if __name__ == "__main__":
    unittest.main(verbosity=2)
