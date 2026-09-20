#!/usr/bin/env python3
"""Real-Git black-box tests for the Ask Agent workspace helper."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
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
        for key, value in (environment_overrides or {}).items():
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
