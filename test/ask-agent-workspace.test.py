#!/usr/bin/env python3
"""Real-Git black-box tests for the Ask Agent workspace helper."""

from __future__ import annotations

import hashlib
import json
import re
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Iterable, Mapping


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "skills/ask-agent/scripts/ask_agent_workspace.py"


class AskAgentWorkspaceCliTests(unittest.TestCase):
    """Exercise the packaged command line against disposable real repositories."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="ask-agent-workspace-test-")
        self.root = Path(self.tmp.name)
        self.primary = self.root / "primary"
        self.source = self.root / "linked-caller"
        self.store = self.root / "workspace-store"
        self.invoke_from = self.root / "unrelated-invocation-directory"
        self.invoke_from.mkdir()
        self._init_linked_caller()
        self._acceptance_number = 0

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run(
        self,
        directory: Path,
        *args: str,
        input_text: str | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=directory,
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode:
            self.fail(
                "Git command failed:\n"
                f"  cwd: {directory}\n"
                f"  argv: git {' '.join(args)}\n"
                f"  stdout: {result.stdout}\n"
                f"  stderr: {result.stderr}"
            )
        return result

    def _run_bytes(
        self,
        directory: Path,
        *args: str,
        input_bytes: bytes | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(
            ["git", *args],
            cwd=directory,
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode:
            self.fail(
                "Git command failed:\n"
                f"  cwd: {directory}\n"
                f"  argv: git {' '.join(args)}\n"
                f"  stdout: {result.stdout.decode(errors='replace')}\n"
                f"  stderr: {result.stderr.decode(errors='replace')}"
            )
        return result

    def _init_linked_caller(self) -> None:
        self.primary.mkdir()
        self._run(self.primary, "init", "-q", "--initial-branch=main")
        self._run(self.primary, "config", "user.email", "ask-agent-test@example.invalid")
        self._run(self.primary, "config", "user.name", "Ask Agent Test")
        # A developer's global excludes file must not change what the tests
        # classify as ignored; linked worktrees share this repository setting.
        self._run(self.primary, "config", "core.excludesFile", os.devnull)

        (self.primary / "app.py").write_text("base application\n", encoding="utf-8")
        (self.primary / "dual.txt").write_text("base dual layer\n", encoding="utf-8")
        (self.primary / "delete-recreate.txt").write_text("original tracked content\n", encoding="utf-8")
        (self.primary / "linked-target.txt").write_text("tracked symlink target\n", encoding="utf-8")
        (self.primary / "script.sh").write_text("#!/bin/sh\necho original\n", encoding="utf-8")
        (self.primary / "payload.bin").write_bytes(b"\x00base\xffpayload\n")
        self._run(self.primary, "add", ".")
        self._run(self.primary, "commit", "-q", "-m", "initial fixture")
        self._run(self.primary, "worktree", "add", "-q", "-b", "caller", str(self.source), "main")

    def _helper_path(self, helper: Path | None = None) -> Path:
        resolved = helper or HELPER
        self.assertTrue(
            resolved.is_file(),
            f"packaged workspace helper is missing: {resolved}",
        )
        return resolved

    def _cli(
        self,
        *args: str,
        helper: Path | None = None,
        isolated_python: bool = False,
        invocation_directory: Path | None = None,
        environment_overrides: Mapping[str, str | None] | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        helper_path = self._helper_path(helper)
        command = [sys.executable]
        if isolated_python:
            command.extend(["-I", "-B"])
        else:
            command.append("-B")
        command.extend([str(helper_path), *args])
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONNOUSERSITE"] = "1"
        overrides = {**getattr(self, "helper_environment", {}), **(environment_overrides or {})}
        for key, value in overrides.items():
            if value is None:
                environment.pop(key, None)
            else:
                environment[key] = value
        result = subprocess.run(
            command,
            cwd=invocation_directory or self.invoke_from,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            self.fail(
                "workspace helper did not emit exactly one JSON result:\n"
                f"  argv: {' '.join(command)}\n"
                f"  returncode: {result.returncode}\n"
                f"  stdout: {result.stdout}\n"
                f"  stderr: {result.stderr}\n"
                f"  JSON error: {error}"
            )
        self.assertIsInstance(payload, dict)
        return result, payload

    def _cli_success(
        self,
        *args: str,
        helper: Path | None = None,
        isolated_python: bool = False,
    ) -> dict[str, Any]:
        result, payload = self._cli(*args, helper=helper, isolated_python=isolated_python)
        self.assertEqual(
            result.returncode,
            0,
            f"workspace helper failed: {payload}\nstderr: {result.stderr}",
        )
        self.assertNotEqual(payload.get("status"), "error", payload)
        return payload

    def _cli_error(self, *args: str) -> dict[str, Any]:
        result, payload = self._cli(*args)
        self.assertNotEqual(result.returncode, 0, payload)
        self.assertEqual(payload.get("status"), "error", payload)
        self.assertIsInstance(payload.get("error"), str, payload)
        return payload

    def _prepare(
        self,
        *,
        source: Path | None = None,
        store: Path | None = None,
        label: str | None = None,
        receipt: Path | None = None,
        helper: Path | None = None,
        isolated_python: bool = False,
    ) -> dict[str, Any]:
        arguments = ["prepare"]
        if receipt is None:
            arguments.extend(["--source", str((source or self.source).resolve())])
            arguments.extend(["--store", str((store or self.store).resolve())])
            if label:
                arguments.extend(["--label", label])
        else:
            arguments.extend(["--receipt", str(receipt.resolve())])
        arguments.append("--writers-quiescent")
        payload = self._cli_success(
            *arguments,
            helper=helper,
            isolated_python=isolated_python,
        )
        self.assertEqual(payload.get("status"), "prepared", payload)
        for key in ("receipt", "worktree", "branch", "baseline"):
            self.assertIn(key, payload)
            self.assertTrue(payload[key], payload)
        prepared_source = Path(payload.get("source", self.source)).resolve()
        self.assertEqual(prepared_source, (source or self.source).resolve(), payload)
        worktree = Path(payload["worktree"]).resolve()
        receipt_path = Path(payload["receipt"]).resolve()
        self.assertTrue(worktree.is_dir(), payload)
        self.assertTrue(receipt_path.is_file(), payload)
        self.assertNotEqual(worktree, prepared_source)
        self.assertFalse(self._is_within(receipt_path, worktree), payload)
        self.assertEqual(
            Path(self._run(worktree, "rev-parse", "--show-toplevel").stdout.strip()).resolve(),
            worktree,
        )
        self.assertEqual(self._run(worktree, "branch", "--show-current").stdout.strip(), payload["branch"])
        return payload

    def _inspect(
        self,
        receipt: Path,
        phase: str,
        *,
        artifacts: Iterable[str] = (),
        discard: Iterable[str] = (),
        expect_success: bool = True,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = ["inspect", "--receipt", str(receipt.resolve()), "--phase", phase]
        for artifact in artifacts:
            arguments.extend(["--artifact", artifact])
        for discarded in discard:
            arguments.extend(["--discard", discarded])
        result, payload = self._cli(*arguments)
        if expect_success:
            self.assertEqual(result.returncode, 0, f"inspect failed: {payload}\nstderr: {result.stderr}")
            self.assertNotEqual(payload.get("status"), "error", payload)
            self.assertIsInstance(payload.get("fingerprint"), str, payload)
            self.assertTrue(payload["fingerprint"], payload)
            self.assertIsInstance(payload.get("changed_paths"), list, payload)
            self.assertIsInstance(payload.get("contribution_paths"), list, payload)
        else:
            self.assertNotEqual(result.returncode, 0, payload)
            self.assertEqual(payload.get("status"), "error", payload)
        return result, payload

    def _check_context(
        self,
        receipt: Path,
        *,
        invocation_directory: Path,
        environment_overrides: Mapping[str, str | None] | None = None,
        expect_success: bool = True,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        result, payload = self._cli(
            "check-context",
            "--receipt",
            str(receipt.resolve()),
            invocation_directory=invocation_directory,
            environment_overrides=environment_overrides,
        )
        if expect_success:
            self.assertEqual(result.returncode, 0, f"context check failed: {payload}\nstderr: {result.stderr}")
            self.assertEqual(payload.get("status"), "verified", payload)
        else:
            self.assertNotEqual(result.returncode, 0, payload)
            self.assertEqual(payload.get("status"), "error", payload)
        return result, payload

    def _close(
        self,
        receipt: Path,
        acceptance: Path | None = None,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        arguments = ["close", "--receipt", str(receipt.resolve())]
        if acceptance is not None:
            arguments.extend(["--acceptance", str(acceptance.resolve())])
        return self._cli(*arguments)

    def _close_with_post_archive_write(
        self,
        receipt: Path,
        acceptance: Path,
        worktree: Path,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        """Run close in a subprocess with one deterministic post-copy worker write."""
        driver = self.root / "post-archive-write-driver.py"
        driver.write_text(
            """from __future__ import annotations
import importlib.util
from pathlib import Path
import sys

helper_path = Path(sys.argv[1])
worktree = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("ask_agent_workspace_race", helper_path)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
original = module._archive_artifact

def archive_then_write(*args, **kwargs):
    archived = original(*args, **kwargs)
    (worktree / "late-worker-write.txt").write_text("late worker write\\n", encoding="utf-8")
    return archived

module._archive_artifact = archive_then_write
raise SystemExit(module.main(sys.argv[3:]))
""",
            encoding="utf-8",
        )
        command = [
            sys.executable,
            "-B",
            str(driver),
            str(self._helper_path()),
            str(worktree),
            "close",
            "--receipt",
            str(receipt.resolve()),
            "--acceptance",
            str(acceptance.resolve()),
        ]
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONNOUSERSITE"] = "1"
        result = subprocess.run(
            command,
            cwd=self.invoke_from,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            self.fail(
                "post-archive close driver did not emit one JSON result:\n"
                f"  returncode: {result.returncode}\n"
                f"  stdout: {result.stdout}\n"
                f"  stderr: {result.stderr}\n"
                f"  JSON error: {error}"
            )
        return result, payload

    def _close_with_outcome_write_failure(
        self,
        receipt: Path,
        acceptance: Path,
    ) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        """Inject the sole crash window between Git removal and close receipt write."""
        driver = self.root / "close-outcome-failure-driver.py"
        driver.write_text(
            """from __future__ import annotations
import importlib.util
from pathlib import Path
import sys

helper_path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("ask_agent_workspace_close_failure", helper_path)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
original = module._write_new_json

def fail_only_close_outcome(path, value):
    if Path(path).name == "close.json":
        raise module.WorkspaceError("injected close outcome write failure")
    return original(path, value)

module._write_new_json = fail_only_close_outcome
raise SystemExit(module.main(sys.argv[2:]))
""",
            encoding="utf-8",
        )
        command = [
            sys.executable,
            "-B",
            str(driver),
            str(self._helper_path()),
            "close",
            "--receipt",
            str(receipt.resolve()),
            "--acceptance",
            str(acceptance.resolve()),
        ]
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONNOUSERSITE"] = "1"
        result = subprocess.run(
            command,
            cwd=self.invoke_from,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            self.fail(
                "post-removal close driver did not emit one JSON result:\n"
                f"  returncode: {result.returncode}\n"
                f"  stdout: {result.stdout}\n"
                f"  stderr: {result.stderr}\n"
                f"  JSON error: {error}"
            )
        return result, payload

    def _acceptance(
        self,
        fingerprint: str,
        *,
        decision: str,
        artifacts: list[dict[str, str]],
        discard: list[str] | None = None,
        **overrides: Any,
    ) -> Path:
        payload: dict[str, Any] = {
            "schema": "ask-agent.acceptance.v1",
            "inspection_fingerprint": fingerprint,
            "decision": decision,
            "workers_stopped": True,
            "completion_reference": "native test stopped",
            "acceptance_reference": "parent verified workspace result",
            "artifacts": artifacts,
            "discard": discard or [],
        }
        payload.update(overrides)
        self._acceptance_number += 1
        path = self.root / f"acceptance-{self._acceptance_number}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _git_dir(self, repository: Path) -> Path:
        value = self._run(repository, "rev-parse", "--git-dir").stdout.strip()
        git_dir = Path(value)
        if not git_dir.is_absolute():
            git_dir = repository / git_dir
        return git_dir.resolve()

    def _snapshot(self, repository: Path) -> dict[str, Any]:
        git_dir = self._git_dir(repository)
        return {
            "head": self._run(repository, "rev-parse", "HEAD").stdout.strip(),
            "branch": self._run(repository, "branch", "--show-current").stdout.strip(),
            "status": self._run_bytes(repository, "status", "--porcelain=v1", "-z", "--untracked-files=all").stdout,
            "cached_diff": self._run_bytes(repository, "diff", "--cached", "--binary").stdout,
            "working_diff": self._run_bytes(repository, "diff", "--binary").stdout,
            "index_entries": self._run_bytes(repository, "ls-files", "--stage").stdout,
            "raw_index": (git_dir / "index").read_bytes(),
        }

    @staticmethod
    def _filesystem_manifest(directory: Path) -> dict[str, tuple[str, str]]:
        """Capture local files, links, and directories without their read-time metadata."""
        manifest: dict[str, tuple[str, str]] = {}
        for path in sorted(directory.rglob("*")):
            relative = path.relative_to(directory).as_posix()
            mode = oct(path.lstat().st_mode)
            if path.is_symlink():
                manifest[relative] = ("symlink", f"{mode}:{os.readlink(path)}")
            elif path.is_file():
                manifest[relative] = ("file", f"{mode}:{hashlib.sha256(path.read_bytes()).hexdigest()}")
            elif path.is_dir():
                manifest[relative] = ("directory", mode)
            else:
                manifest[relative] = ("other", mode)
        return manifest

    @staticmethod
    def _is_within(path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
        except ValueError:
            return False
        return True

    def _make_dirty_caller(self) -> None:
        (self.source / "dual.txt").write_text("staged dual layer\n", encoding="utf-8")
        self._run(self.source, "add", "dual.txt")
        (self.source / "dual.txt").write_text("staged dual layer\nunstaged dual layer\n", encoding="utf-8")

        staged_add_edited = self.source / "staged-add-edited.txt"
        staged_add_edited.write_text("staged added content\n", encoding="utf-8")
        self._run(self.source, "add", staged_add_edited.name)
        staged_add_edited.write_text("staged added content\nunstaged edit\n", encoding="utf-8")

        staged_add_deleted = self.source / "staged-add-deleted.txt"
        staged_add_deleted.write_text("staged then deleted\n", encoding="utf-8")
        self._run(self.source, "add", staged_add_deleted.name)
        staged_add_deleted.unlink()

        self._run(self.source, "rm", "-q", "delete-recreate.txt")
        (self.source / "delete-recreate.txt").write_text("recreated only in working tree\n", encoding="utf-8")

        (self.source / "payload.bin").write_bytes(b"\x00staged\x80payload\n")
        self._run(self.source, "add", "payload.bin")
        (self.source / "payload.bin").write_bytes(b"\x00unstaged\x81payload\n")

        script = self.source / "script.sh"
        script.write_text("#!/bin/sh\necho executable worker input\n", encoding="utf-8")
        script.chmod(0o755)
        self._run(self.source, "add", script.name)

        untracked = self.source / "notes" / "untracked.txt"
        untracked.parent.mkdir()
        untracked.write_text("untracked inherited note\n", encoding="utf-8")
        (self.source / "untracked.bin").write_bytes(b"\x00untracked\xfeinput\n")
        (self.source / "untracked-link").symlink_to("linked-target.txt")

    def _assert_dirty_fidelity(self, worktree: Path) -> None:
        self.assertEqual(
            self._run_bytes(self.source, "diff", "--cached", "--binary").stdout,
            self._run_bytes(worktree, "diff", "--cached", "--binary").stdout,
        )
        self.assertEqual(
            self._run_bytes(self.source, "diff", "--binary").stdout,
            self._run_bytes(worktree, "diff", "--binary").stdout,
        )
        self.assertEqual(
            self._run_bytes(self.source, "ls-files", "--stage").stdout,
            self._run_bytes(worktree, "ls-files", "--stage").stdout,
        )
        for relative in (
            "dual.txt",
            "staged-add-edited.txt",
            "delete-recreate.txt",
            "payload.bin",
            "script.sh",
            "notes/untracked.txt",
            "untracked.bin",
        ):
            with self.subTest(relative=relative):
                self.assertEqual((worktree / relative).read_bytes(), (self.source / relative).read_bytes())
        self.assertFalse((worktree / "staged-add-deleted.txt").exists())
        self.assertEqual(
            self._run_bytes(self.source, "show", ":staged-add-deleted.txt").stdout,
            self._run_bytes(worktree, "show", ":staged-add-deleted.txt").stdout,
        )
        source_mode = (self.source / "script.sh").stat().st_mode & 0o777
        worktree_mode = (worktree / "script.sh").stat().st_mode & 0o777
        self.assertEqual(worktree_mode, source_mode)
        self.assertTrue(worktree_mode & 0o111)
        link = worktree / "untracked-link"
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), "linked-target.txt")

    def _write_returned_result(
        self,
        worktree: Path,
        *,
        code: bool = True,
        report: bool = True,
        scratch: bool = True,
    ) -> None:
        if code:
            (worktree / "app.py").write_text("base application\nworker contribution\n", encoding="utf-8")
        if report:
            result = worktree / "reports" / "result.md"
            result.parent.mkdir(exist_ok=True)
            result.write_text("# Worker result\n\nVerified review result.\n", encoding="utf-8")
        if scratch:
            (worktree / "scratch.tmp").write_text("discardable worker scratch\n", encoding="utf-8")

    def _assert_archive(self, close: dict[str, Any], expected: bytes) -> None:
        self.assertEqual(close.get("status"), "closed", close)
        self.assertTrue(close.get("removed"), close)
        results_root = Path(close["results_root"])
        self.assertTrue(results_root.is_dir(), close)
        archived = close.get("archived_artifacts")
        self.assertIsInstance(archived, list, close)
        self.assertEqual(len(archived), 1, close)
        archive = Path(archived[0]["archive"])
        self.assertTrue(archive.is_file(), close)
        self.assertFalse(self._is_within(archive.resolve(), self.source))
        self.assertEqual(archive.read_bytes(), expected)

    def _assert_retained(
        self,
        result: subprocess.CompletedProcess[str],
        close: dict[str, Any],
        worktree: Path,
    ) -> None:
        self.assertNotEqual(close.get("status"), "closed", close)
        self.assertFalse(close.get("removed", False), close)
        self.assertTrue(worktree.exists(), close)
        if result.returncode == 0:
            self.assertEqual(close.get("status"), "retained", close)

    def test_clean_linked_caller_retries_same_attempt_and_fresh_attempt_is_unique(self) -> None:
        source_before = self._snapshot(self.source)
        first = self._prepare(label="review pricing")
        first_worktree = Path(first["worktree"])
        first_receipt = Path(first["receipt"])
        self.assertEqual(self._snapshot(self.source), source_before)

        retry = self._prepare(receipt=first_receipt)
        self.assertEqual(Path(retry["receipt"]), first_receipt)
        self.assertEqual(Path(retry["worktree"]), first_worktree)
        self.assertEqual(retry["branch"], first["branch"])
        self.assertEqual(self._snapshot(self.source), source_before)

        fresh = self._prepare(label="review pricing")
        self.assertNotEqual(Path(fresh["receipt"]), first_receipt)
        self.assertNotEqual(Path(fresh["worktree"]), first_worktree)
        self.assertNotEqual(fresh["branch"], first["branch"])
        self.assertEqual(self._snapshot(self.source), source_before)

    def test_check_context_reports_actual_subdirectory_and_ignores_pwd(self) -> None:
        prepared = self._prepare(label="context subdirectory")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        subdirectory = worktree / "worker" / "operation"
        subdirectory.mkdir(parents=True)

        _, context = self._check_context(
            receipt,
            invocation_directory=subdirectory,
            environment_overrides={"PWD": str(self.source)},
        )

        self.assertEqual(context.get("schema"), "ask-agent.workspace.context.v1", context)
        self.assertEqual(context.get("receipt"), str(receipt.resolve()), context)
        self.assertEqual(context.get("attempt"), prepared["attempt"], context)
        self.assertEqual(Path(context["worktree"]), worktree.resolve(), context)
        self.assertEqual(Path(context["actual_cwd"]), subdirectory.resolve(), context)
        self.assertEqual(Path(context["git_root"]), worktree.resolve(), context)
        self.assertEqual(context.get("branch"), prepared["branch"], context)
        self.assertEqual(context.get("head"), self._run(worktree, "rev-parse", "HEAD").stdout.strip(), context)
        self.assertEqual(context.get("operation"), "current-process working directory and Git root", context)
        self.assertIn("does not attest", context.get("scope", ""), context)

        (worktree / "app.py").write_text("base application\nworker edit\n", encoding="utf-8")
        _, rechecked = self._check_context(receipt, invocation_directory=subdirectory)
        self.assertEqual(Path(rechecked["git_root"]), worktree.resolve(), rechecked)

    def test_check_context_rejects_caller_other_repo_and_mismatched_receipt(self) -> None:
        prepared = self._prepare(label="context assigned workspace")
        receipt = Path(prepared["receipt"])
        worktree = Path(prepared["worktree"])
        other_prepared = self._prepare(label="context other workspace")
        other_worktree = Path(other_prepared["worktree"])

        _, caller = self._check_context(
            receipt,
            invocation_directory=self.source,
            environment_overrides={"PWD": str(worktree)},
            expect_success=False,
        )
        self.assertIn("outside", caller["error"].lower(), caller)

        other_repo = self.root / "other-repository"
        other_repo.mkdir()
        self._run(other_repo, "init", "-q")
        _, other = self._check_context(receipt, invocation_directory=other_repo, expect_success=False)
        self.assertIn("outside", other["error"].lower(), other)

        _, mismatch = self._check_context(receipt, invocation_directory=other_worktree, expect_success=False)
        self.assertIn("outside", mismatch["error"].lower(), mismatch)

    def test_check_context_rejects_nested_repository_and_git_redirects(self) -> None:
        prepared = self._prepare(label="context nested repository")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        nested = worktree / "nested-repository"
        nested.mkdir()
        self._run(nested, "init", "-q")

        _, nested_context = self._check_context(
            receipt,
            invocation_directory=nested,
            expect_success=False,
        )
        self.assertIn("Git root", nested_context["error"], nested_context)

        redirect_environment = {
            "GIT_DIR": str(self._git_dir(self.source)),
            "GIT_WORK_TREE": str(self.source),
            "GIT_COMMON_DIR": self._run(self.source, "rev-parse", "--git-common-dir").stdout.strip(),
            "GIT_INDEX_FILE": str(self._git_dir(self.source) / "index"),
        }

        _, context = self._check_context(
            receipt,
            invocation_directory=worktree,
            environment_overrides=redirect_environment,
            expect_success=False,
        )

        self.assertIn("Git context environment overrides", context["error"], context)
        self.assertIn("GIT_DIR", context["error"], context)
        self.assertIn("GIT_WORK_TREE", context["error"], context)

    def test_check_context_rejects_closed_workspace(self) -> None:
        prepared = self._prepare(label="context closed workspace")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        self._write_returned_result(worktree, code=False, scratch=False)
        _, inspected = self._inspect(receipt, "returned", artifacts=["reports/result.md"])
        acceptance = self._acceptance(
            inspected["fingerprint"],
            decision="report-consumed",
            artifacts=[{"path": "reports/result.md", "purpose": "review"}],
        )
        closed = self._cli_success("close", "--receipt", str(receipt), "--acceptance", str(acceptance))
        self.assertEqual(closed.get("status"), "closed", closed)

        _, context = self._check_context(receipt, invocation_directory=self.source, expect_success=False)
        self.assertIn("closed", context["error"].lower(), context)

    def test_dirty_linked_caller_preserves_git_layers_entries_and_raw_index(self) -> None:
        self._make_dirty_caller()
        source_before = self._snapshot(self.source)
        prepared = self._prepare(label="dirty linked caller")
        worktree = Path(prepared["worktree"])

        self._assert_dirty_fidelity(worktree)
        self.assertEqual(self._snapshot(self.source), source_before)

    def test_dirty_worktree_inheritance_replays_two_generations_without_mutating_ancestors(self) -> None:
        self._make_dirty_caller()
        caller_before = self._snapshot(self.source)
        caller_files_before = {
            relative: (self.source / relative).read_bytes()
            for relative in (
                "dual.txt",
                "staged-add-edited.txt",
                "delete-recreate.txt",
                "payload.bin",
                "script.sh",
                "notes/untracked.txt",
                "untracked.bin",
            )
        }
        first = self._prepare(label="dirty first generation")
        first_worktree = Path(first["worktree"])
        self._assert_dirty_fidelity(first_worktree)

        first_app = first_worktree / "app.py"
        first_app.write_text("base application\nfirst staged layer\n", encoding="utf-8")
        self._run(first_worktree, "add", "app.py")
        first_app.write_text("base application\nfirst staged layer\nfirst unstaged layer\n", encoding="utf-8")
        first_untracked = first_worktree / "first-generation.bin"
        first_untracked_bytes = b"\x00first generation\xfeuntracked input\n"
        first_untracked.write_bytes(first_untracked_bytes)
        first_head = self._run(first_worktree, "rev-parse", "HEAD").stdout.strip()
        first_before = self._snapshot(first_worktree)
        first_files_before = {
            relative: (first_worktree / relative).read_bytes()
            for relative in (
                "app.py",
                "dual.txt",
                "staged-add-edited.txt",
                "delete-recreate.txt",
                "payload.bin",
                "script.sh",
                "notes/untracked.txt",
                "untracked.bin",
                "first-generation.bin",
            )
        }
        first_cached = self._run_bytes(first_worktree, "diff", "--cached", "--binary").stdout
        first_unstaged = self._run_bytes(first_worktree, "diff", "--binary").stdout
        first_untracked_manifest = self._run_bytes(
            first_worktree,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ).stdout

        second = self._prepare(source=first_worktree, label="dirty second generation")
        second_worktree = Path(second["worktree"])

        self.assertEqual(self._run(second_worktree, "rev-parse", "HEAD").stdout.strip(), first_head)
        self.assertEqual(self._run_bytes(second_worktree, "diff", "--cached", "--binary").stdout, first_cached)
        self.assertEqual(self._run_bytes(second_worktree, "diff", "--binary").stdout, first_unstaged)
        self.assertEqual(
            self._run_bytes(second_worktree, "ls-files", "--others", "--exclude-standard", "-z").stdout,
            first_untracked_manifest,
        )
        self.assertEqual((second_worktree / "first-generation.bin").read_bytes(), first_untracked_bytes)
        self.assertEqual((second_worktree / "app.py").read_bytes(), first_files_before["app.py"])

        self.assertEqual(self._snapshot(first_worktree), first_before)
        self.assertEqual(self._snapshot(self.source), caller_before)
        for relative, expected in first_files_before.items():
            self.assertEqual((first_worktree / relative).read_bytes(), expected, relative)
        for relative, expected in caller_files_before.items():
            self.assertEqual((self.source / relative).read_bytes(), expected, relative)

        second_app = first_files_before["app.py"] + b"second generation contribution\n"
        (second_worktree / "app.py").write_bytes(second_app)
        _, returned = self._inspect(Path(second["receipt"]), "returned")
        self.assertEqual(returned["contribution_paths"], ["app.py"])
        contribution_patch = Path(returned["evidence"]["contribution_patch"]).read_bytes()
        self.assertIn(b"+second generation contribution", contribution_patch)
        self.assertNotIn(b"+first staged layer", contribution_patch)
        self.assertNotIn(b"+first unstaged layer", contribution_patch)
        self.assertNotIn(b"staged dual layer", contribution_patch)
        replay = self.root / "second-generation-patch-replay"
        replay.mkdir()
        self._run(replay, "init", "-q")
        (replay / "app.py").write_bytes(first_files_before["app.py"])
        self._run_bytes(replay, "apply", "--check", input_bytes=contribution_patch)
        self._run_bytes(replay, "apply", input_bytes=contribution_patch)
        self.assertEqual((replay / "app.py").read_bytes(), second_app)
        self.assertEqual(self._snapshot(first_worktree), first_before)
        self.assertEqual(self._snapshot(self.source), caller_before)

    def test_prepare_refuses_missing_quiescence_non_git_conflicts_and_intent_to_add(self) -> None:
        source_before = self._snapshot(self.source)
        missing_quiescence = self._cli_error(
            "prepare",
            "--source",
            str(self.source),
            "--store",
            str(self.store),
        )
        self.assertIn("quies", missing_quiescence["error"].lower())
        self.assertEqual(self._snapshot(self.source), source_before)

        non_git = self.root / "not-a-repository"
        non_git.mkdir()
        non_git_error = self._cli_error(
            "prepare",
            "--source",
            str(non_git),
            "--store",
            str(self.store),
            "--writers-quiescent",
        )
        self.assertIn("git", non_git_error["error"].lower())

        intent = self.source / "intent-to-add.txt"
        intent.write_text("this is intentionally not fully staged\n", encoding="utf-8")
        self._run(self.source, "add", "-N", intent.name)
        intent_error = self._cli_error(
            "prepare",
            "--source",
            str(self.source),
            "--store",
            str(self.store),
            "--writers-quiescent",
        )
        self.assertRegex(intent_error["error"].lower(), "intent-to-add|special index")

        self._run(self.source, "reset", "-q", "--", intent.name)
        intent.unlink()
        (self.source / "dual.txt").write_text("caller conflict\n", encoding="utf-8")
        self._run(self.source, "add", "dual.txt")
        self._run(self.source, "commit", "-q", "-m", "caller conflict side")
        (self.primary / "dual.txt").write_text("main conflict\n", encoding="utf-8")
        self._run(self.primary, "add", "dual.txt")
        self._run(self.primary, "commit", "-q", "-m", "main conflict side")
        merge = self._run(self.source, "merge", "main", check=False)
        self.assertNotEqual(merge.returncode, 0, merge.stderr)
        conflict_error = self._cli_error(
            "prepare",
            "--source",
            str(self.source),
            "--store",
            str(self.store),
            "--writers-quiescent",
        )
        self.assertRegex(conflict_error["error"].lower(), "conflict|unmerged")

    def test_prepare_rejects_git_context_overrides_without_mutating_source_or_worktree(self) -> None:
        kept = self._prepare(label="prepare environment guard")
        kept_worktree = Path(kept["worktree"])
        kept_receipt = Path(kept["receipt"])
        source_before = self._snapshot(self.source)
        worktree_before = self._snapshot(kept_worktree)
        registrations_before = self._run_bytes(self.source, "worktree", "list", "--porcelain").stdout
        attempts = self.store / "attempts"
        attempts_before = sorted(path.name for path in attempts.iterdir())
        hostile_environments = {
            "GIT_NAMESPACE": "hostile-namespace",
            "GIT_CONFIG_GLOBAL": str(self.root / "hostile.gitconfig"),
            "GIT_CEILING_DIRECTORIES": str(self.root),
        }

        for mode in ("new", "retry"):
            for key, value in hostile_environments.items():
                with self.subTest(mode=mode, key=key):
                    if mode == "new":
                        arguments = [
                            "prepare",
                            "--source",
                            str(self.source),
                            "--store",
                            str(self.store),
                            "--label",
                            f"blocked-{key.lower()}",
                            "--writers-quiescent",
                        ]
                    else:
                        arguments = [
                            "prepare",
                            "--receipt",
                            str(kept_receipt),
                            "--writers-quiescent",
                        ]
                    result, rejected = self._cli(
                        *arguments,
                        environment_overrides={key: value},
                    )
                    self.assertNotEqual(result.returncode, 0, rejected)
                    self.assertEqual(rejected.get("status"), "error", rejected)
                    self.assertIn(key, rejected.get("error", ""), rejected)
                    self.assertEqual(self._snapshot(self.source), source_before)
                    self.assertEqual(self._snapshot(kept_worktree), worktree_before)
                    self.assertEqual(
                        self._run_bytes(self.source, "worktree", "list", "--porcelain").stdout,
                        registrations_before,
                    )
                    self.assertEqual(sorted(path.name for path in attempts.iterdir()), attempts_before)

    def test_inspect_rejects_prepared_drift_and_returned_delta_excludes_inheritance(self) -> None:
        self._make_dirty_caller()
        source_before = self._snapshot(self.source)
        prepared = self._prepare(label="prepared drift")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])

        _, baseline = self._inspect(receipt, "prepared")
        self.assertEqual(baseline["changed_paths"], baseline["contribution_paths"])
        self.assertEqual(baseline["contribution_paths"], [])
        (worktree / "dual.txt").write_text("worker drift before dispatch\n", encoding="utf-8")
        _, drift = self._inspect(receipt, "prepared", expect_success=False)
        self.assertRegex(drift["error"].lower(), "drift|baseline|prepared")
        _, context = self._check_context(receipt, invocation_directory=worktree)
        self.assertEqual(Path(context["git_root"]), worktree.resolve(), context)
        self.assertEqual(self._snapshot(self.source), source_before)

        returned = self._prepare(label="returned contribution")
        returned_worktree = Path(returned["worktree"])
        returned_receipt = Path(returned["receipt"])
        self._write_returned_result(returned_worktree)
        _, inspected = self._inspect(
            returned_receipt,
            "returned",
            artifacts=["reports/result.md"],
            discard=["scratch.tmp"],
        )
        self.assertCountEqual(inspected["changed_paths"], ["app.py", "reports/result.md", "scratch.tmp"])
        self.assertEqual(inspected["contribution_paths"], ["app.py"])
        self.assertNotIn("dual.txt", inspected["changed_paths"])
        self.assertNotIn("staged-add-edited.txt", inspected["contribution_paths"])
        self.assertEqual(self._snapshot(self.source), source_before)

    def test_returned_inspect_refuses_index_only_staged_changes_and_restored_delete(self) -> None:
        prepared = self._prepare(label="index-only worker change")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        source_before = self._snapshot(self.source)
        original_app = (worktree / "app.py").read_bytes()
        original_deleted = (worktree / "delete-recreate.txt").read_bytes()
        _, prepared_inspection = self._inspect(receipt, "prepared")

        (worktree / "app.py").write_text("staged worker-only content\n", encoding="utf-8")
        self._run(worktree, "add", "app.py")
        (worktree / "app.py").write_bytes(original_app)
        self._run(worktree, "rm", "-q", "delete-recreate.txt")
        (worktree / "delete-recreate.txt").write_bytes(original_deleted)
        self.assertTrue(self._run_bytes(worktree, "diff", "--cached", "--binary").stdout)
        self.assertEqual((worktree / "app.py").read_bytes(), original_app)
        self.assertEqual((worktree / "delete-recreate.txt").read_bytes(), original_deleted)

        _, inspection = self._inspect(receipt, "returned", expect_success=False)

        self.assertIn("index-only", inspection["error"].lower())
        self.assertTrue(worktree.exists())
        self.assertEqual(self._snapshot(self.source), source_before)

        acceptance = self._acceptance(
            prepared_inspection["fingerprint"],
            decision="integrated",
            artifacts=[],
        )
        result, close = self._close(receipt, acceptance)
        self._assert_retained(result, close, worktree)
        self.assertIn("index-only", str(close).lower())

    def test_close_without_acceptance_retains_owned_worktree(self) -> None:
        prepared = self._prepare(label="retain by default")
        worktree = Path(prepared["worktree"])
        source_before = self._snapshot(self.source)

        result, close = self._close(Path(prepared["receipt"]))

        self.assertEqual(result.returncode, 0, result.stderr)
        self._assert_retained(result, close, worktree)
        self.assertIn("reason", close)
        self.assertEqual(self._snapshot(self.source), source_before)

    def test_close_retains_when_native_stop_or_acceptance_references_are_missing(self) -> None:
        omissions = (
            {"workers_stopped": False},
            {"completion_reference": ""},
            {"acceptance_reference": ""},
        )
        for override in omissions:
            with self.subTest(override=override):
                prepared = self._prepare(label="acceptance evidence")
                worktree = Path(prepared["worktree"])
                self._write_returned_result(worktree, code=False, scratch=False)
                _, inspected = self._inspect(
                    Path(prepared["receipt"]),
                    "returned",
                    artifacts=["reports/result.md"],
                )
                acceptance = self._acceptance(
                    inspected["fingerprint"],
                    decision="report-consumed",
                    artifacts=[{"path": "reports/result.md", "purpose": "review"}],
                    **override,
                )
                result, close = self._close(Path(prepared["receipt"]), acceptance)
                self._assert_retained(result, close, worktree)

    def test_close_retains_when_worker_changes_after_inspection(self) -> None:
        prepared = self._prepare(label="stale fingerprint")
        worktree = Path(prepared["worktree"])
        self._write_returned_result(worktree, scratch=False)
        _, inspected = self._inspect(
            Path(prepared["receipt"]),
            "returned",
            artifacts=["reports/result.md"],
        )
        acceptance = self._acceptance(
            inspected["fingerprint"],
            decision="integrated",
            artifacts=[{"path": "reports/result.md", "purpose": "review"}],
        )
        (worktree / "app.py").write_text("base application\nchanged after inspection\n", encoding="utf-8")

        result, close = self._close(Path(prepared["receipt"]), acceptance)

        self._assert_retained(result, close, worktree)
        self.assertRegex(str(close).lower(), "fingerprint|stale|changed|inspection")

    def test_close_rechecks_complete_state_after_archive_before_removal(self) -> None:
        prepared = self._prepare(label="late archive write")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        source_before = self._snapshot(self.source)
        self._write_returned_result(worktree, code=False, scratch=False)
        _, inspected = self._inspect(receipt, "returned", artifacts=["reports/result.md"])
        acceptance = self._acceptance(
            inspected["fingerprint"],
            decision="report-consumed",
            artifacts=[{"path": "reports/result.md", "purpose": "review"}],
        )

        result, close = self._close_with_post_archive_write(receipt, acceptance, worktree)

        self._assert_retained(result, close, worktree)
        late_file = worktree / "late-worker-write.txt"
        self.assertTrue(late_file.is_file(), close)
        self.assertEqual(late_file.read_text(encoding="utf-8"), "late worker write\n")
        self.assertRegex(str(close).lower(), "fingerprint|changed|late|inspection")
        self.assertEqual(self._snapshot(self.source), source_before)

    def test_close_recovers_after_post_removal_outcome_write_failure(self) -> None:
        prepared = self._prepare(label="recover close outcome")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        source_before = self._snapshot(self.source)
        self._write_returned_result(worktree, code=False, scratch=False)
        report_bytes = (worktree / "reports" / "result.md").read_bytes()
        _, inspected = self._inspect(receipt, "returned", artifacts=["reports/result.md"])
        acceptance = self._acceptance(
            inspected["fingerprint"],
            decision="report-consumed",
            artifacts=[{"path": "reports/result.md", "purpose": "review"}],
        )

        first_result, first = self._close_with_outcome_write_failure(receipt, acceptance)

        self.assertNotEqual(first_result.returncode, 0, first)
        self.assertEqual(first.get("status"), "error", first)
        self.assertFalse(worktree.exists(), first)
        self.assertEqual(self._snapshot(self.source), source_before)

        recovered = self._cli_success("close", "--receipt", str(receipt), "--acceptance", str(acceptance))

        self._assert_archive(recovered, report_bytes)
        self.assertFalse(worktree.exists())
        self.assertEqual(self._snapshot(self.source), source_before)

    def test_close_retains_unknown_missing_worktree_without_eligibility(self) -> None:
        prepared = self._prepare(label="unknown missing worktree")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        source_before = self._snapshot(self.source)
        _, inspected = self._inspect(receipt, "returned")
        acceptance = self._acceptance(
            inspected["fingerprint"],
            decision="report-consumed",
            artifacts=[],
        )

        self._run(self.source, "worktree", "remove", "--force", str(worktree))
        self.assertFalse(worktree.exists())
        result, close = self._close(receipt, acceptance)

        self.assertNotEqual(close.get("status"), "closed", close)
        self.assertFalse(close.get("removed", False), close)
        self.assertFalse(worktree.exists())
        if result.returncode == 0:
            self.assertEqual(close.get("status"), "retained", close)
        self.assertRegex(str(close).lower(), "missing|binding|worktree|ownership")
        self.assertEqual(self._snapshot(self.source), source_before)

    def test_close_retains_unsafe_artifact_path_and_symlink(self) -> None:
        for unsafe_kind in ("traversal", "symlink"):
            with self.subTest(unsafe_kind=unsafe_kind):
                prepared = self._prepare(label=f"unsafe {unsafe_kind}")
                worktree = Path(prepared["worktree"])
                report = worktree / "reports" / "result.md"
                report.parent.mkdir()
                outside = self.root / f"outside-{unsafe_kind}.md"
                outside.write_text("outside result must survive\n", encoding="utf-8")
                artifact_path = "../outside.md"
                if unsafe_kind == "symlink":
                    report.symlink_to(outside)
                    artifact_path = "reports/result.md"
                else:
                    report.write_text("ordinary report\n", encoding="utf-8")
                _, inspected = self._inspect(Path(prepared["receipt"]), "returned")
                acceptance = self._acceptance(
                    inspected["fingerprint"],
                    decision="integrated",
                    artifacts=[{"path": artifact_path, "purpose": "review"}],
                )

                result, close = self._close(Path(prepared["receipt"]), acceptance)

                self._assert_retained(result, close, worktree)
                self.assertEqual(outside.read_text(encoding="utf-8"), "outside result must survive\n")
                self.assertRegex(str(close).lower(), "artifact|path|symlink|safe")

    def test_report_consumed_refuses_close_when_code_contribution_remains(self) -> None:
        prepared = self._prepare(label="report only gate")
        worktree = Path(prepared["worktree"])
        source_before = self._snapshot(self.source)
        self._write_returned_result(worktree, scratch=False)
        _, inspected = self._inspect(
            Path(prepared["receipt"]),
            "returned",
            artifacts=["reports/result.md"],
        )
        self.assertEqual(inspected["contribution_paths"], ["app.py"])
        acceptance = self._acceptance(
            inspected["fingerprint"],
            decision="report-consumed",
            artifacts=[{"path": "reports/result.md", "purpose": "review"}],
        )

        result, close = self._close(Path(prepared["receipt"]), acceptance)

        self._assert_retained(result, close, worktree)
        self.assertRegex(str(close).lower(), "contribution|report|code")
        self.assertEqual(self._snapshot(self.source), source_before)

    def test_report_consumed_cannot_classify_away_changed_inherited_file(self) -> None:
        for classification in ("artifact", "discard"):
            with self.subTest(classification=classification):
                prepared = self._prepare(label=f"misclassified {classification}")
                worktree = Path(prepared["worktree"])
                receipt = Path(prepared["receipt"])
                source_before = self._snapshot(self.source)
                self._write_returned_result(worktree, scratch=False)

                artifacts = ["reports/result.md"]
                discarded: list[str] = []
                accepted_artifacts = [{"path": "reports/result.md", "purpose": "review"}]
                if classification == "artifact":
                    artifacts.append("app.py")
                    accepted_artifacts.append({"path": "app.py", "purpose": "misclassified code"})
                else:
                    discarded.append("app.py")
                _, inspected = self._inspect(
                    receipt,
                    "returned",
                    artifacts=artifacts,
                    discard=discarded,
                )
                acceptance = self._acceptance(
                    inspected["fingerprint"],
                    decision="report-consumed",
                    artifacts=accepted_artifacts,
                    discard=discarded,
                )

                result, close = self._close(receipt, acceptance)

                self._assert_retained(result, close, worktree)
                self.assertEqual(
                    (worktree / "app.py").read_text(encoding="utf-8"),
                    "base application\nworker contribution\n",
                )
                self.assertRegex(str(close).lower(), "inherited|baseline|tracked|contribution|report")
                self.assertEqual(self._snapshot(self.source), source_before)

    def test_acceptance_fingerprint_binds_artifact_and_discard_classification(self) -> None:
        prepared = self._prepare(label="classification fingerprint")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        source_before = self._snapshot(self.source)
        self._write_returned_result(worktree, code=False, report=True, scratch=True)
        _, original = self._inspect(
            receipt,
            "returned",
            artifacts=["reports/result.md"],
            discard=["scratch.tmp"],
        )
        acceptance = self._acceptance(
            original["fingerprint"],
            decision="report-consumed",
            artifacts=[{"path": "scratch.tmp", "purpose": "reclassified result"}],
            discard=["reports/result.md"],
        )

        result, close = self._close(receipt, acceptance)

        self._assert_retained(result, close, worktree)
        self.assertRegex(str(close).lower(), "fingerprint|state changed|classification")
        self.assertEqual(self._snapshot(self.source), source_before)

    def test_report_consumed_archives_report_then_removes_worktree(self) -> None:
        prepared = self._prepare(label="report consumed")
        worktree = Path(prepared["worktree"])
        source_before = self._snapshot(self.source)
        self._write_returned_result(worktree, code=False, scratch=False)
        report_bytes = (worktree / "reports" / "result.md").read_bytes()
        _, inspected = self._inspect(
            Path(prepared["receipt"]),
            "returned",
            artifacts=["reports/result.md"],
        )
        self.assertEqual(inspected["contribution_paths"], [])
        acceptance = self._acceptance(
            inspected["fingerprint"],
            decision="report-consumed",
            artifacts=[{"path": "reports/result.md", "purpose": "review"}],
        )

        close = self._cli_success("close", "--receipt", prepared["receipt"], "--acceptance", str(acceptance))

        self._assert_archive(close, report_bytes)
        self.assertFalse(worktree.exists())
        self.assertEqual(self._snapshot(self.source), source_before)

    def test_integrated_close_archives_report_preserves_source_and_is_idempotent(self) -> None:
        prepared = self._prepare(label="integrated contribution")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        self._write_returned_result(worktree, scratch=False)
        report_bytes = (worktree / "reports" / "result.md").read_bytes()
        _, inspected = self._inspect(receipt, "returned", artifacts=["reports/result.md"])
        self.assertEqual(inspected["contribution_paths"], ["app.py"])

        worker_patch = self._run_bytes(worktree, "diff", "--binary").stdout
        self.assertTrue(worker_patch)
        self._run_bytes(self.source, "apply", "--binary", input_bytes=worker_patch)
        self.assertEqual(
            (self.source / "app.py").read_text(encoding="utf-8"),
            "base application\nworker contribution\n",
        )
        source_before_close = self._snapshot(self.source)
        acceptance = self._acceptance(
            inspected["fingerprint"],
            decision="integrated",
            artifacts=[{"path": "reports/result.md", "purpose": "review"}],
        )

        close = self._cli_success("close", "--receipt", str(receipt), "--acceptance", str(acceptance))

        self._assert_archive(close, report_bytes)
        self.assertFalse(worktree.exists())
        self.assertEqual(self._snapshot(self.source), source_before_close)

        repeated = self._cli_success("close", "--receipt", str(receipt), "--acceptance", str(acceptance))
        self.assertEqual(repeated.get("status"), "closed", repeated)
        self.assertTrue(repeated.get("removed"), repeated)
        self.assertEqual(self._snapshot(self.source), source_before_close)

    def test_copied_package_helper_runs_from_unrelated_directory_without_checkout_import(self) -> None:
        copied_skill = self.root / "frozen-installed-package" / "ask-agent"
        shutil.copytree(ROOT / "skills" / "ask-agent", copied_skill)
        copied_helper = copied_skill / "scripts" / "ask_agent_workspace.py"
        self.assertTrue(copied_helper.is_file())
        self.assertFalse(copied_helper.is_symlink())
        self.assertFalse(self._is_within(copied_helper.resolve(), ROOT))

        prepared = self._prepare(
            label="copied package smoke",
            helper=copied_helper,
            isolated_python=True,
        )

        self.assertTrue(Path(prepared["worktree"]).is_dir(), prepared)
        self.assertTrue(Path(prepared["receipt"]).is_file(), prepared)
        self.assertFalse(str(ROOT) in str(prepared["worktree"]))

    def test_identity_binds_a_host_selected_card_to_its_executing_package(self) -> None:
        copied_skill = self.root / "frozen-installed-package" / "ask-agent"
        shutil.copytree(ROOT / "skills" / "ask-agent", copied_skill)
        copied_card = copied_skill / "SKILL.md"
        copied_helper = copied_skill / "scripts" / "ask_agent_workspace.py"
        logical_directory = self.root / "logical-host-skill" / "ask-agent"
        logical_directory.parent.mkdir()
        logical_directory.symlink_to(copied_skill, target_is_directory=True)
        logical_card = logical_directory / "SKILL.md"
        card_alias_parent = self.root / "logical-card-alias"
        card_alias_parent.mkdir()
        card_alias = card_alias_parent / "SKILL.md"
        card_alias.symlink_to(copied_card)

        expected_card = copied_card.resolve()
        expected_helper = copied_helper.resolve()
        expected_version = next(
            line.split(":", 1)[1].strip()
            for line in expected_card.read_text(encoding="utf-8").splitlines()
            if line.startswith("version:")
        )
        expected = {
            "status": "verified",
            "schema": "ask-agent.skill.identity.v1",
            "resolved_skill_card": str(expected_card),
            "resolved_helper": str(expected_helper),
            "version": expected_version,
            "skill_card_sha256": hashlib.sha256(expected_card.read_bytes()).hexdigest(),
            "helper_sha256": hashlib.sha256(expected_helper.read_bytes()).hexdigest(),
        }
        for selected_card in (logical_card, card_alias):
            with self.subTest(selected_card=selected_card):
                identity = self._cli_success(
                    "identity",
                    "--skill-card",
                    str(selected_card),
                    helper=copied_helper,
                    isolated_python=True,
                )
                self.assertEqual(
                    set(identity),
                    {
                        "status",
                        "schema",
                        "skill_card",
                        "resolved_skill_card",
                        "resolved_helper",
                        "version",
                        "skill_card_sha256",
                        "helper_sha256",
                    },
                )
                self.assertEqual(identity["skill_card"], str(selected_card))
                for field, value in expected.items():
                    self.assertEqual(identity[field], value)

    def test_identity_rejects_relative_missing_mismatched_and_malformed_cards(self) -> None:
        copied_skill = self.root / "frozen-installed-package" / "ask-agent"
        shutil.copytree(ROOT / "skills" / "ask-agent", copied_skill)
        copied_helper = copied_skill / "scripts" / "ask_agent_workspace.py"
        other_skill = self.root / "other-installed-package" / "ask-agent"
        shutil.copytree(ROOT / "skills" / "ask-agent", other_skill)
        malformed_skill = self.root / "malformed-installed-package" / "ask-agent"
        shutil.copytree(ROOT / "skills" / "ask-agent", malformed_skill)
        (malformed_skill / "SKILL.md").write_text(
            "---\nname: ask-agent\nversion: not-a-version\n---\n# Ask agent\n",
            encoding="utf-8",
        )
        redirected_helper_skill = self.root / "redirected-helper-package" / "ask-agent"
        shutil.copytree(ROOT / "skills" / "ask-agent", redirected_helper_skill)
        redirected_card_skill = self.root / "redirected-card-package" / "ask-agent"
        shutil.copytree(ROOT / "skills" / "ask-agent", redirected_card_skill)
        redirected_card = redirected_card_skill / "SKILL.md"
        (redirected_helper_skill / "SKILL.md").unlink()
        (redirected_helper_skill / "SKILL.md").symlink_to(redirected_card)

        cases = (
            (
                "relative",
                copied_helper,
                Path("SKILL.md"),
                "absolute",
            ),
            (
                "missing",
                copied_helper,
                self.root / "missing-package" / "SKILL.md",
                "resolve",
            ),
            (
                "same-name other package",
                copied_helper,
                other_skill / "SKILL.md",
                "executing helper package",
            ),
            (
                "malformed metadata",
                malformed_skill / "scripts" / "ask_agent_workspace.py",
                malformed_skill / "SKILL.md",
                "semantic version",
            ),
            (
                "helper card redirected to another package",
                redirected_helper_skill / "scripts" / "ask_agent_workspace.py",
                redirected_card,
                "executing helper package",
            ),
        )
        for name, helper, card, message in cases:
            with self.subTest(name=name):
                result, identity = self._cli(
                    "identity",
                    "--skill-card",
                    str(card),
                    helper=helper,
                    isolated_python=True,
                )
                self.assertNotEqual(result.returncode, 0, identity)
                self.assertEqual(identity.get("status"), "error", identity)
                self.assertIn(message, str(identity.get("error", "")).lower(), identity)

    def test_capabilities_reports_verified_versions_without_filesystem_writes(self) -> None:
        source_card = ROOT / "skills" / "ask-agent" / "SKILL.md"
        current_version = next(
            line.split(":", 1)[1].strip()
            for line in source_card.read_text(encoding="utf-8").splitlines()
            if line.startswith("version:")
        )
        newer_version = f"{int(current_version.split('.', 1)[0]) + 1}.0.0"

        for label, version in (
            ("supported-0.6", "0.6.0"),
            ("current", current_version),
            ("newer", newer_version),
        ):
            with self.subTest(version=version):
                installed_skill = self.root / f"capabilities-{label}"
                shutil.copytree(ROOT / "skills" / "ask-agent", installed_skill)
                selected_card = installed_skill / "SKILL.md"
                if version != current_version:
                    selected_card.write_text(
                        source_card.read_text(encoding="utf-8").replace(
                            f"version: {current_version}",
                            f"version: {version}",
                            1,
                        ),
                        encoding="utf-8",
                    )
                state_home = self.root / f"capabilities-{label}-state"
                home = self.root / f"capabilities-{label}-home"
                before = self._filesystem_manifest(self.root)

                result, payload = self._cli(
                    "capabilities",
                    "--skill-card",
                    str(selected_card),
                    helper=installed_skill / "scripts" / "ask_agent_workspace.py",
                    isolated_python=True,
                    environment_overrides={
                        "XDG_STATE_HOME": str(state_home),
                        "HOME": str(home),
                    },
                )

                self.assertEqual(result.returncode, 0, f"capabilities failed: {payload}\nstderr: {result.stderr}")
                self.assertEqual(
                    payload,
                    {
                        "schema": "shiploop-chain-ask-agent-managed-worktree/v1",
                        "version": version,
                        "capabilities": [
                            "helper-managed-worktree",
                            "prepared-inspection",
                            "returned-commit-delivery",
                            "fingerprint-bound-close",
                            "ignored-output-report",
                        ],
                    },
                )
                self.assertFalse(state_home.exists(), payload)
                self.assertFalse(home.exists(), payload)
                self.assertEqual(self._filesystem_manifest(self.root), before)

    def test_capabilities_rejects_outside_and_mismatched_cards(self) -> None:
        executing_skill = self.root / "capabilities-executing-package"
        other_skill = self.root / "capabilities-other-package"
        shutil.copytree(ROOT / "skills" / "ask-agent", executing_skill)
        shutil.copytree(ROOT / "skills" / "ask-agent", other_skill)
        outside_directory = self.root / "capabilities-outside-card"
        outside_directory.mkdir()
        outside_card = outside_directory / "SKILL.md"
        outside_card.write_text(
            "---\nname: ask-agent\nversion: 0.6.0\n---\n# Outside card\n",
            encoding="utf-8",
        )
        helper = executing_skill / "scripts" / "ask_agent_workspace.py"

        for name, selected_card in (
            ("outside", outside_card),
            ("mismatched package", other_skill / "SKILL.md"),
        ):
            with self.subTest(name=name):
                result, payload = self._cli(
                    "capabilities",
                    "--skill-card",
                    str(selected_card),
                    helper=helper,
                    isolated_python=True,
                )
                self.assertNotEqual(result.returncode, 0, payload)
                self.assertEqual(payload.get("status"), "error", payload)
                self.assertIn("executing helper package", str(payload.get("error", "")).lower(), payload)

    # Pinned regressions for patch fidelity, snapshot tolerance, and retry safety.

    def _cli_with_injection(self, injection: str, *args: str) -> tuple[subprocess.CompletedProcess[str], dict[str, Any]]:
        """Run the helper CLI after executing `injection` against the loaded module."""
        self._acceptance_number += 1
        driver = self.root / f"injection-driver-{self._acceptance_number}.py"
        driver.write_text(
            "from __future__ import annotations\n"
            "import importlib.util\n"
            "from pathlib import Path\n"
            "import sys\n"
            "spec = importlib.util.spec_from_file_location('ask_agent_workspace_injected', Path(sys.argv[1]))\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "sys.modules[spec.name] = module\n"
            "spec.loader.exec_module(module)\n"
            f"{injection}\n"
            "raise SystemExit(module.main(sys.argv[2:]))\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment.pop("PYTHONPATH", None)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, "-B", str(driver), str(self._helper_path()), *args],
            cwd=self.invoke_from, env=environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(f"injected helper emitted no JSON (rc={result.returncode})\nstdout: {result.stdout}\nstderr: {result.stderr}")
        return result, payload

    def _prepare_args(self, label: str) -> tuple[str, ...]:
        return ("prepare", "--source", str(self.source.resolve()), "--store", str(self.store.resolve()),
                "--label", label, "--writers-quiescent")

    def _inspect_mode(self, receipt: Path, mode: str, *, artifacts: Iterable[str] = (), discard: Iterable[str] = ()) -> dict[str, Any]:
        arguments = ["inspect", "--receipt", str(receipt.resolve()), "--phase", "returned", "--delivery-mode", mode]
        for artifact in artifacts:
            arguments.extend(["--artifact", artifact])
        for discarded in discard:
            arguments.extend(["--discard", discarded])
        return self._cli_success(*arguments)

    def _exclude(self, *patterns: str) -> None:
        common = Path(self._run(self.source, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
        (common / "info").mkdir(exist_ok=True)
        with (common / "info" / "exclude").open("a", encoding="utf-8") as stream:
            stream.write("".join(f"{pattern}\n" for pattern in patterns))

    def _documented_apply_commands(self) -> list[list[str]]:
        """Return the caller apply commands exactly as result-handoff.md documents them."""
        text = (HELPER.parents[1] / "references" / "result-handoff.md").read_text(encoding="utf-8")
        block = text.split("```sh\n", 1)[1].split("```", 1)[0]
        commands = [shlex.split(line) for line in block.splitlines() if line.startswith("git -C ")]
        self.assertEqual([command[3] for command in commands], ["apply", "apply"], block)
        return commands

    def _apply_to_source(self, patch: Path) -> None:
        """Integrate a contribution patch with the documented caller commands."""
        for command in self._documented_apply_commands():
            substituted = [str(self.source) if part == "/actual/target checkout" else
                           str(patch) if part == "/actual/contribution.patch" else part for part in command]
            result = subprocess.run(substituted, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            self.assertEqual(result.returncode, 0, f"{substituted}\n{result.stderr}")

    def _hostile_home(self) -> Path:
        """A HOME whose global Git config and attributes corrupt naive diffs."""
        home = self.root / "hostile-home"
        (home / ".config").mkdir(parents=True)
        (home / "attributes").write_text("*.dat diff=hex\n*.bin diff=hex\n", encoding="utf-8")
        (home / ".gitconfig").write_text(
            "[color]\n\tui = always\n\tdiff = always\n"
            "[diff]\n\tnoprefix = true\n\tmnemonicPrefix = true\n\trenames = copies\n"
            "\tcontext = 0\n\tsrcPrefix = x/y/\n\tdstPrefix = z/w/\n\tsuppressBlankEmpty = true\n"
            "[diff \"hex\"]\n\ttextconv = od -An -c\n"
            f"[core]\n\tattributesFile = {home / 'attributes'}\n",
            encoding="utf-8",
        )
        return home

    def test_patch_is_verbatim_rename_safe_and_immune_to_hostile_diff_configuration(self) -> None:
        # Hostile but legitimate configuration at every level the helper's
        # diffs can see: global (through HOME), repository-local, and the
        # GIT_DIFF_OPTS environment variable.  Environment GIT_CONFIG_* cannot
        # carry it because prepare refuses those overrides.
        home = self._hostile_home()
        self.helper_environment = {"HOME": str(home), "XDG_CONFIG_HOME": str(home / ".config"),
                                   "GIT_DIFF_OPTS": "--unified=0"}
        for key, value in (("color.ui", "always"), ("diff.noprefix", "true"), ("diff.renames", "copies")):
            self._run(self.primary, "config", key, value)
        (self.source / "dual.txt").write_text("staged caller layer\n", encoding="utf-8")
        self._run(self.source, "add", "dual.txt")
        (self.source / "app.py").write_text("base application\ncaller unstaged edit\n", encoding="utf-8")
        (self.source / "payload.bin").write_bytes(b"\x00caller\xffpayload\n")
        prepared = self._prepare(label="hostile config")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])

        (worktree / "app.py").write_text(
            "base application\ncaller unstaged edit\n\nsee a/before/x and b/after/y\n", encoding="utf-8")
        (worktree / "moved").mkdir()
        (worktree / "delete-recreate.txt").rename(worktree / "moved" / "delete-recreate.txt")
        (worktree / "fixture.dat").write_bytes(b"GIF89a-ish payload\nsecond line\n")
        tool = worktree / "tool.sh"
        tool.write_text("#!/bin/sh\necho worker\n", encoding="utf-8")
        tool.chmod(0o755)

        inspected = self._inspect_mode(receipt, "patch")
        patch = Path(inspected["delivery"]["contribution_patch"])
        patch_bytes = patch.read_bytes()
        self.assertNotIn(b"\x1b[", patch_bytes)
        self.assertNotIn(b"rename from", patch_bytes)
        self.assertNotIn(b"copy from", patch_bytes)
        self.assertIn(b"+see a/before/x and b/after/y\n", patch_bytes)

        self._apply_to_source(patch)
        for relative in ("app.py", "moved/delete-recreate.txt", "fixture.dat", "tool.sh", "payload.bin"):
            self.assertEqual((self.source / relative).read_bytes(), (worktree / relative).read_bytes(), relative)
        self.assertFalse((self.source / "delete-recreate.txt").exists())
        self.assertTrue(os.access(self.source / "tool.sh", os.X_OK))
        self.assertEqual(
            self._run(self.source, "diff", "--cached", "--name-only").stdout.split(), ["dual.txt"],
            "plain git apply must leave the caller's index untouched",
        )

    def test_contribution_patch_ignores_a_repository_enclosing_the_store(self) -> None:
        # A store inside an unrelated repository must not let that repository
        # take part in the out-of-repository contribution diff.  An unknown
        # repository extension makes Git refuse to run inside it, so only the
        # diff's discovery ceiling lets this inspection succeed.
        outer = self.root / "outer-repository"
        outer.mkdir()
        self._run(outer, "init", "-q")
        self._run(outer, "config", "core.repositoryformatversion", "1")
        self._run(outer, "config", "extensions.enclosingStoreProbe", "true")
        self.store = outer / "nested" / "workspace-store"
        prepared = self._prepare(label="enclosed store")
        worktree = Path(prepared["worktree"])
        (worktree / "app.py").write_text("base application\n\nworker line after a blank\n", encoding="utf-8")
        inspected = self._inspect_mode(Path(prepared["receipt"]), "patch")
        patch = Path(inspected["delivery"]["contribution_patch"])
        self.assertIn(b"+worker line after a blank\n", patch.read_bytes())
        self._apply_to_source(patch)
        self.assertEqual((self.source / "app.py").read_bytes(), (worktree / "app.py").read_bytes())

    def test_documented_apply_keeps_worker_bytes_under_caller_whitespace_policy(self) -> None:
        for policy in ("fix", "error"):
            with self.subTest(policy=policy):
                self._run(self.source, "checkout", "--", ".")
                self._run(self.primary, "config", "apply.whitespace", policy)
                prepared = self._prepare(label=f"whitespace {policy}")
                worktree = Path(prepared["worktree"])
                (worktree / "app.py").write_text("base application\ntrailing   \n", encoding="utf-8")
                inspected = self._inspect_mode(Path(prepared["receipt"]), "patch")
                self._apply_to_source(Path(inspected["delivery"]["contribution_patch"]))
                self.assertEqual((self.source / "app.py").read_bytes(), b"base application\ntrailing   \n")

    def test_ignored_generated_output_is_reported_not_contributed(self) -> None:
        self._exclude("__pycache__/", ".worktrees/", "*.log")
        (self.source / ".worktrees" / "other").mkdir(parents=True)
        (self.source / ".worktrees" / "other" / "file.txt").write_text("unrelated worktree store\n", encoding="utf-8")
        (self.source / "odd\\name.log").write_text("ignored name with a backslash\n", encoding="utf-8")
        prepared = self._prepare(label="ignored output")
        self.assertIn(".worktrees/", prepared["ignored_dependencies_omitted"], prepared)
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])

        self._write_returned_result(worktree, scratch=False)
        (worktree / "__pycache__").mkdir()
        (worktree / "__pycache__" / "app.cpython-312.pyc").write_bytes(b"\x00compiled\xff")

        inspected = self._inspect_mode(receipt, "patch", artifacts=["reports/result.md"])
        self.assertEqual(inspected["contribution_paths"], ["app.py"], inspected)
        self.assertEqual(inspected["ignored_paths"], ["__pycache__/app.cpython-312.pyc"], inspected)
        self.assertNotIn(b"pyc", Path(inspected["delivery"]["contribution_patch"]).read_bytes())

        # An explicit classification wins over the ignored class.
        kept = self._inspect_mode(receipt, "patch", artifacts=["reports/result.md", "__pycache__"])
        self.assertNotIn("ignored_paths", kept, kept)

        # Report-only work that incidentally generated ignored output still closes.
        report_only = self._prepare(label="ignored report")
        report_tree = Path(report_only["worktree"])
        report_receipt = Path(report_only["receipt"])
        self._write_returned_result(report_tree, code=False, scratch=False)
        (report_tree / "__pycache__").mkdir()
        (report_tree / "__pycache__" / "m.pyc").write_bytes(b"\x00")
        reported = self._inspect_mode(report_receipt, "report-only", artifacts=["reports/result.md"])
        self.assertEqual(reported["delivery"]["contribution_paths"], [], reported)
        acceptance = self._acceptance(
            reported["fingerprint"], decision="report-consumed",
            artifacts=[{"path": "reports/result.md", "purpose": "review"}],
        )
        closed = self._cli_success("close", "--receipt", str(report_receipt), "--acceptance", str(acceptance))
        self.assertEqual(closed.get("status"), "closed", closed)

    def test_pathspec_like_names_are_classified_as_plain_paths(self) -> None:
        self._exclude("/config")
        prepared = self._prepare(label="pathspec names")
        worktree = Path(prepared["worktree"])
        (worktree / ":config").write_text("a real contribution\n", encoding="utf-8")
        (worktree / ":!notes.txt").write_text("another one\n", encoding="utf-8")
        inspected = self._inspect_mode(Path(prepared["receipt"]), "patch")
        self.assertEqual(sorted(inspected["contribution_paths"]), [":!notes.txt", ":config"], inspected)
        self.assertNotIn("ignored_paths", inspected)

    def test_fingerprint_binds_the_ignored_classification(self) -> None:
        self._exclude("__pycache__/")
        prepared = self._prepare(label="ignore rules move")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        self._write_returned_result(worktree, report=False, scratch=False)
        (worktree / "__pycache__").mkdir()
        (worktree / "__pycache__" / "m.pyc").write_bytes(b"\x00")
        ignored = self._inspect_mode(receipt, "patch")
        self.assertEqual(ignored["ignored_paths"], ["__pycache__/m.pyc"])

        common = Path(self._run(self.source, "rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip())
        exclude = common / "info" / "exclude"
        exclude.write_text(exclude.read_text(encoding="utf-8").replace("__pycache__/\n", ""), encoding="utf-8")
        unignored = self._inspect_mode(receipt, "patch")
        self.assertNotEqual(unignored["fingerprint"], ignored["fingerprint"])
        self.assertIn("__pycache__/m.pyc", unignored["contribution_paths"])

        acceptance = self._acceptance(ignored["fingerprint"], decision="integrated", artifacts=[])
        result, closed = self._close(receipt, acceptance)
        self._assert_retained(result, closed, worktree)

    def test_output_without_ignored_paths_keeps_its_exact_key_set(self) -> None:
        prepared = self._prepare(label="stable keys")
        self._write_returned_result(Path(prepared["worktree"]), report=False, scratch=False)
        inspected = self._inspect_mode(Path(prepared["receipt"]), "patch")
        self.assertNotIn("ignored_paths", inspected)
        record = json.loads(Path(inspected["evidence"]["inspection"]).read_text(encoding="utf-8"))
        self.assertNotIn("ignored_paths", record)

    def test_evidence_derived_by_an_earlier_helper_is_never_reused(self) -> None:
        prepared = self._prepare(label="legacy evidence")
        receipt = Path(prepared["receipt"])
        self._write_returned_result(Path(prepared["worktree"]), report=False, scratch=False)
        first = self._inspect_mode(receipt, "patch")
        patch = Path(first["delivery"]["contribution_patch"])
        self.assertEqual((patch.parent.parent.parent.name, patch.parent.parent.name), ("inspections", "v2"))
        # Simulate a pre-0.7.5 record under the same fingerprint: a corrupted
        # patch in the unversioned directory, and no current-derivation record.
        legacy = receipt.parent / "inspections" / first["fingerprint"]
        legacy.mkdir(parents=True)
        (legacy / "contribution.patch").write_bytes(b"legacy corrupted patch\n")
        (legacy / "inspection.json").write_text("{}", encoding="utf-8")
        shutil.rmtree(patch.parent)
        shutil.rmtree(receipt.parent / "delivery-evidence" / "v2")
        again = self._inspect_mode(receipt, "patch")
        rebuilt = Path(again["delivery"]["contribution_patch"])
        self.assertEqual(again["fingerprint"], first["fingerprint"])
        self.assertNotEqual(rebuilt.parent, legacy)
        self.assertIn(b"+worker contribution\n", rebuilt.read_bytes())

    def test_prepare_accepts_permission_bits_git_does_not_track(self) -> None:
        (self.source / "app.py").chmod(0o600)
        link = self.source / "extra-link"
        link.symlink_to("app.py")
        if hasattr(os, "lchmod"):
            os.lchmod(link, 0o700)
        self.assertEqual(self._run(self.source, "status", "--porcelain", "--", "app.py").stdout, "")
        prepared = self._prepare(label="private modes")
        worktree = Path(prepared["worktree"])
        self.assertEqual((worktree / "app.py").read_bytes(), (self.source / "app.py").read_bytes())
        self.assertEqual(os.readlink(worktree / "extra-link"), "app.py")
        _, inspected = self._inspect(Path(prepared["receipt"]), "prepared")
        self.assertEqual(inspected["changed_paths"], [], inspected)

    def _assert_failed_prepare_left_nothing(self, payload: dict[str, Any], label: str) -> str:
        error = payload["error"]
        self.assertIn("prepare failed before dispatch", error)
        branches = self._run(self.primary, "for-each-ref", "--format=%(refname)", f"refs/heads/ask-agent/{label}-*").stdout
        self.assertEqual(branches, "", error)
        registered = self._run(self.primary, "worktree", "list", "--porcelain").stdout
        self.assertNotIn(str(self.store.resolve()), registered, error)
        match = re.search(r"failure record: (\S+/failure\.json)\)", error)
        self.assertIsNotNone(match, error)
        failure = Path(match.group(1))
        self.assertTrue(failure.is_file(), error)
        self.assertTrue(self._is_within(failure, self.store.resolve()), error)
        record = json.loads(failure.read_text(encoding="utf-8"))
        self.assertEqual(record["status"], "failed")
        self.assertFalse(Path(record["worktree"]).exists(), record)
        return error

    def test_failed_prepare_removes_its_own_worktree_and_branch(self) -> None:
        injection = (
            "def fail(*args, **kwargs):\n"
            "    raise module.WorkspaceError('injected child verification failure')\n"
            "module._verify_child_capture = fail"
        )
        result, payload = self._cli_with_injection(injection, *self._prepare_args("doomed"))
        self.assertEqual(result.returncode, 2, payload)
        error = self._assert_failed_prepare_left_nothing(payload, "doomed")
        self.assertIn("injected child verification failure", error)
        self.assertIn("removed worktree", error)
        self.assertIn("deleted branch ask-agent/doomed-", error)

    def test_failed_prepare_cleans_up_after_any_exception(self) -> None:
        injection = (
            "import errno\n"
            "def fail(*args, **kwargs):\n"
            "    raise OSError(errno.ENOSPC, 'injected no space left')\n"
            "module._verify_child_capture = fail"
        )
        result, payload = self._cli_with_injection(injection, *self._prepare_args("nospace"))
        self.assertEqual(result.returncode, 2, payload)
        error = self._assert_failed_prepare_left_nothing(payload, "nospace")
        self.assertIn("injected no space left", error)

    def test_failed_worktree_add_cleans_up_what_git_left_behind(self) -> None:
        # Git creates the branch before checkout, and a timeout or checkout
        # error can leave the branch, or a worktree locked "initializing".
        cases = {
            "locked": (
                "original = module._git\n"
                "def wrapped(repo, *arguments, **kwargs):\n"
                "    result = original(repo, *arguments, **kwargs)\n"
                "    if arguments[:2] == ('worktree', 'add'):\n"
                "        original(repo, 'worktree', 'lock', '--reason', 'initializing', arguments[4])\n"
                "        raise module.WorkspaceError('injected timeout during worktree add')\n"
                "    return result\n"
                "module._git = wrapped"
            ),
            "branchonly": (
                "original = module._git\n"
                "def wrapped(repo, *arguments, **kwargs):\n"
                "    if arguments[:2] == ('worktree', 'add'):\n"
                "        original(repo, 'branch', arguments[3], arguments[5])\n"
                "        raise module.WorkspaceError('injected checkout failure')\n"
                "    return original(repo, *arguments, **kwargs)\n"
                "module._git = wrapped"
            ),
        }
        for label, injection in cases.items():
            with self.subTest(case=label):
                self.store = self.root / f"store-{label}"
                result, payload = self._cli_with_injection(injection, *self._prepare_args(label))
                self.assertEqual(result.returncode, 2, payload)
                error = self._assert_failed_prepare_left_nothing(payload, label)
                self.assertIn("deleted branch", error)
                self.assertNotIn("worktree add was not attempted", error)

    def test_failed_prepare_keeps_a_branch_that_moved(self) -> None:
        injection = (
            "def fail(worktree, *args, **kwargs):\n"
            "    module._git(worktree, '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',\n"
            "                'commit', '--allow-empty', '-qm', 'moved')\n"
            "    raise module.WorkspaceError('injected failure after a commit')\n"
            "module._verify_child_capture = fail"
        )
        result, payload = self._cli_with_injection(injection, *self._prepare_args("moved"))
        self.assertEqual(result.returncode, 2, payload)
        self.assertIn("because it moved", payload["error"])
        branches = self._run(self.primary, "for-each-ref", "--format=%(refname)", "refs/heads/ask-agent/moved-*").stdout
        self.assertTrue(branches.strip(), payload)

    def test_empty_repository_prepare_reports_an_actionable_error(self) -> None:
        empty = self.root / "empty"
        empty.mkdir()
        self._run(empty, "init", "-q")
        payload = self._cli_error("prepare", "--source", str(empty.resolve()),
                                  "--store", str(self.store.resolve()), "--writers-quiescent")
        self.assertIn("empty repository or unborn branch", payload["error"])

    def test_interrupted_inspection_build_is_rebuilt_not_trusted(self) -> None:
        prepared = self._prepare(label="interrupted inspection")
        receipt = Path(prepared["receipt"])
        self._write_returned_result(Path(prepared["worktree"]), report=False, scratch=False)
        injection = (
            "def fail(*args, **kwargs):\n"
            "    raise module.WorkspaceError('injected inspection copy failure')\n"
            "module._copy_filtered_state = fail"
        )
        arguments = ("inspect", "--receipt", str(receipt.resolve()), "--phase", "returned", "--delivery-mode", "patch")
        result, payload = self._cli_with_injection(injection, *arguments)
        self.assertEqual(result.returncode, 2, payload)
        self.assertIn("injected inspection copy failure", payload["error"])
        inspections = receipt.parent / "inspections" / "v2"
        self.assertEqual([item.name for item in inspections.iterdir()], [], "no partial record may persist")

        inspected = self._inspect_mode(receipt, "patch")
        patch = Path(inspected["delivery"]["contribution_patch"])
        self.assertIn(b"+worker contribution\n", patch.read_bytes())

        # A published record that lost its patch is rebuilt rather than trusted.
        record_dir = patch.parent
        patch.unlink()
        rebuilt = self._inspect_mode(receipt, "patch")
        self.assertEqual(rebuilt["fingerprint"], inspected["fingerprint"])
        self.assertIn(b"+worker contribution\n", Path(rebuilt["delivery"]["contribution_patch"]).read_bytes())
        self.assertTrue((record_dir / "inspection.json").is_file())

    def test_close_retry_records_the_acceptance_that_actually_removed(self) -> None:
        prepared = self._prepare(label="close retry")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        self._write_returned_result(worktree, code=False, scratch=False)

        kept = self._inspect_mode(receipt, "report-only", artifacts=["reports/result.md"])
        first = self._acceptance(kept["fingerprint"], decision="report-consumed",
                                 artifacts=[{"path": "reports/result.md", "purpose": "review"}])
        self._run(self.primary, "worktree", "lock", str(worktree))
        result, refused = self._close(receipt, first)
        self._assert_retained(result, refused, worktree)
        self.assertIn("Git refused", refused.get("reason", ""), refused)
        self._run(self.primary, "worktree", "unlock", str(worktree))

        dropped = self._inspect_mode(receipt, "report-only", discard=["reports/result.md"])
        second = self._acceptance(dropped["fingerprint"], decision="report-consumed", artifacts=[],
                                  discard=["reports/result.md"])
        closed = self._cli_success("close", "--receipt", str(receipt), "--acceptance", str(second))
        self.assertEqual(closed.get("status"), "closed", closed)
        self.assertEqual(closed["inspection_fingerprint"], dropped["fingerprint"], closed)
        self.assertEqual(closed["archived_artifacts"], [], closed)
        eligibility = json.loads((receipt.parent / "close-eligibility.json").read_text(encoding="utf-8"))
        self.assertEqual(eligibility["fingerprint"], dropped["fingerprint"])

    def test_git_timeout_is_configurable_and_bounded(self) -> None:
        for value in ("0", "-1", "nan", "inf", "1e20", "abc"):
            with self.subTest(value=value):
                result, payload = self._cli("prepare", "--source", str(self.source.resolve()), "--store",
                                            str(self.store.resolve()), "--writers-quiescent",
                                            environment_overrides={"ASK_AGENT_GIT_TIMEOUT": value})
                self.assertEqual(result.returncode, 2, payload)
                self.assertIn("ASK_AGENT_GIT_TIMEOUT must be a positive number", payload["error"])
        result, payload = self._cli("prepare", "--source", str(self.source.resolve()), "--store",
                                    str(self.store.resolve()), "--writers-quiescent",
                                    environment_overrides={"ASK_AGENT_GIT_TIMEOUT": "0.000001"})
        self.assertEqual(result.returncode, 2, payload)
        self.assertIn("Git timed out after 1e-06s", payload["error"])
        result, payload = self._cli("prepare", "--source", str(self.source.resolve()), "--store",
                                    str(self.store.resolve()), "--writers-quiescent",
                                    environment_overrides={"ASK_AGENT_GIT_TIMEOUT": "120"})
        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(payload["status"], "prepared", payload)

    def test_exported_pathspec_variables_do_not_break_inspect_or_close(self) -> None:
        # Git exports these to hooks and `!` aliases (for example under
        # --literal-pathspecs); check-ignore would then refuse every path.
        prepared = self._prepare(label="pathspec environment")
        worktree = Path(prepared["worktree"])
        receipt = Path(prepared["receipt"])
        self._write_returned_result(worktree, scratch=False)
        (worktree / "new_module.py").write_text("print('new')\n", encoding="utf-8")
        for variable in ("GIT_LITERAL_PATHSPECS", "GIT_GLOB_PATHSPECS", "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS"):
            with self.subTest(variable=variable):
                self.helper_environment = {variable: "1"}
                inspected = self._inspect_mode(receipt, "patch", artifacts=["reports/result.md"])
                self.assertEqual(sorted(inspected["contribution_paths"]), ["app.py", "new_module.py"])
        acceptance = self._acceptance(inspected["fingerprint"], decision="integrated",
                                      artifacts=[{"path": "reports/result.md", "purpose": "review"}])
        closed = self._cli_success("close", "--receipt", str(receipt), "--acceptance", str(acceptance))
        self.assertEqual(closed.get("status"), "closed", closed)

    def test_failed_prepare_removes_worktree_files_git_left_after_deregistering(self) -> None:
        # Git deregisters a worktree even when deleting its files fails (for
        # example while a killed checkout child still writes); the report must
        # match what is actually left.
        injection = (
            "original = module._git\n"
            "def wrapped(repo, *arguments, **kwargs):\n"
            "    result = original(repo, *arguments, **kwargs)\n"
            "    if arguments[:2] == ('worktree', 'remove'):\n"
            "        stray = module.Path(arguments[-1]) / 'late' / 'checkout.txt'\n"
            "        stray.parent.mkdir(parents=True)\n"
            "        stray.write_text('written after removal')\n"
            "    return result\n"
            "module._git = wrapped\n"
            "def fail(*args, **kwargs):\n"
            "    raise module.WorkspaceError('injected failure before stray files')\n"
            "module._verify_child_capture = fail"
        )
        result, payload = self._cli_with_injection(injection, *self._prepare_args("stray"))
        self.assertEqual(result.returncode, 2, payload)
        error = self._assert_failed_prepare_left_nothing(payload, "stray")
        self.assertIn("removed worktree and its leftover files", error)

    def test_failed_prepare_names_an_exception_without_a_message(self) -> None:
        injection = (
            "def fail(*args, **kwargs):\n"
            "    raise ValueError()\n"
            "module._verify_child_capture = fail"
        )
        result, payload = self._cli_with_injection(injection, *self._prepare_args("nameless"))
        self.assertEqual(result.returncode, 2, payload)
        error = self._assert_failed_prepare_left_nothing(payload, "nameless")
        self.assertTrue(error.startswith("ValueError (prepare failed before dispatch"), error)

    def test_ignored_listing_collapses_directories(self) -> None:
        self._exclude("*.log", "node_modules/")
        (self.source / "logs").mkdir()
        (self.source / "logs" / "x.log").write_text("only ignored content\n", encoding="utf-8")
        (self.source / "node_modules" / "pkg").mkdir(parents=True)
        (self.source / "node_modules" / "pkg" / "index.js").write_text("module.exports = 1\n", encoding="utf-8")
        (self.source / "top.log").write_text("ignored file\n", encoding="utf-8")
        prepared = self._prepare(label="ignored listing")
        omitted = prepared["ignored_dependencies_omitted"]
        self.assertIn("node_modules/", omitted)
        self.assertIn("top.log", omitted)
        for entry in omitted:
            for other in omitted:
                if other != entry and other.endswith("/"):
                    self.assertFalse(entry.startswith(other), omitted)

    def test_slice_prose_rules_are_pinned(self) -> None:
        skill = (HELPER.parents[1] / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("prompt-timer", skill)
        self.assertIn("native current-session wakeup", skill)
        hosts = (HELPER.parents[1] / "references" / "host-capabilities.md").read_text(encoding="utf-8")
        claude = hosts.split("## Claude Code", 1)[1].split("\n## ", 1)[0]
        self.assertIn("`SendMessage`", claude)
        self.assertIn("do not poll or schedule wakeups", claude)


if __name__ == "__main__":
    unittest.main(verbosity=2)
