#!/usr/bin/env python3
"""Real filesystem and Git coverage for the worker-local chain handoff archive."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))

import shiploop_chain_handoff as handoff  # noqa: E402


GIT = shutil.which("git")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ShipLoopChainHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        if GIT is None:
            self.fail("Git must be available on PATH for chain handoff coverage")
        self.temporary = tempfile.TemporaryDirectory(prefix="shiploop-chain-handoff-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.workspace = self.base / "worker-worktree"
        self.archive_dir = self.base / "parent-archive"
        self.workspace.mkdir()
        self.archive_dir.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "ShipLoop Handoff Test")
        self.git("config", "user.email", "shiploop-handoff@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        (self.workspace / "README.md").write_text("baseline\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-qm", "baseline")
        self.base_commit = self.git("rev-parse", "HEAD").stdout.strip()
        self.expected = {
            "run_id": "run-42",
            "step": "implement-feature",
            "attempt": "attempt-42",
            "base_commit": self.base_commit,
            "workspace": str(self.workspace),
        }

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(GIT), "-C", str(self.workspace), *args],
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
            env={
                **os.environ,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0",
            },
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def handoff_path(self, attempt: str | None = None) -> Path:
        return self.workspace / ".shiploop-handoff" / (attempt or self.expected["attempt"]) / "handoff.json"

    def write_handoff(
        self,
        *,
        attempt: str | None = None,
        files: dict[str, bytes] | None = None,
        status: str = "SUCCEEDED",
        commit: str | None = None,
        payload_files: list[dict[str, str]] | None = None,
    ) -> tuple[Path, str]:
        selected_attempt = attempt or self.expected["attempt"]
        path = self.handoff_path(selected_attempt)
        path.parent.mkdir(parents=True, exist_ok=True)
        values = files if files is not None else {"result.json": b'{"result":"ok"}\n'}
        for relative, data in values.items():
            target = path.parent.joinpath(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        declared = payload_files
        if declared is None:
            declared = [{"path": relative, "sha256": digest(data)} for relative, data in values.items()]
        body = {
            "schema": "shiploop-chain-handoff/v1",
            "run_id": self.expected["run_id"],
            "step": self.expected["step"],
            "attempt": selected_attempt,
            "base_commit": self.base_commit,
            "status": status,
            "commit": self.base_commit if commit is None and status == "SUCCEEDED" else commit,
            "summary": "worker-local result",
            "files": declared,
        }
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
        path.write_bytes(raw)
        return path, digest(raw)

    def archive(
        self,
        path: Path,
        handoff_digest: str,
        *,
        expected: dict | None = None,
        archive_dir: Path | None = None,
    ) -> dict:
        return handoff.archive_handoff(
            self.workspace,
            path,
            handoff_digest,
            self.expected if expected is None else expected,
            self.archive_dir if archive_dir is None else archive_dir,
        )

    def test_success_cleanup_and_replay_after_worker_local_files_are_removed(self) -> None:
        source, handoff_digest = self.write_handoff(files={"result.json": b"result\n", "scratch/log.txt": b"log\n"})

        receipt = self.archive(source, handoff_digest)

        self.assertEqual(receipt["schema"], "shiploop-chain-import-receipt/v1")
        self.assertEqual(receipt["workspace"], str(self.workspace))
        self.assertEqual(receipt["handoff"]["sha256"], handoff_digest)
        self.assertEqual(receipt["status"], "SUCCEEDED")
        self.assertEqual(
            [(row["path"], Path(row["archived_path"]).read_bytes()) for row in receipt["archives"]],
            [("result.json", b"result\n"), ("scratch/log.txt", b"log\n")],
        )
        self.assertEqual(Path(receipt["handoff"]["archived_path"]).read_bytes(), source.read_bytes())
        self.assertFalse(os.stat(receipt["receipt_path"]).st_mode & 0o222)

        cleanup = handoff.remove_imported_files(receipt)

        self.assertEqual(cleanup["already_removed"], [])
        self.assertFalse(source.exists())
        self.assertFalse(source.parent.exists())
        replay = self.archive(source, handoff_digest)
        self.assertEqual(replay, receipt)

    def test_empty_failed_handoff_has_an_archive_and_replays(self) -> None:
        source, handoff_digest = self.write_handoff(files={}, status="FAILED")

        receipt = self.archive(source, handoff_digest)

        self.assertEqual(receipt["status"], "FAILED")
        self.assertIsNone(receipt["commit"])
        self.assertEqual(receipt["archives"], [])
        self.assertTrue((self.archive_dir / handoff_digest / "files").is_dir())
        handoff.remove_imported_files(receipt)
        self.assertEqual(self.archive(source, handoff_digest), receipt)

    def test_missing_exclusive_archive_directory_is_created(self) -> None:
        source, handoff_digest = self.write_handoff()
        missing = self.base / "parent-ledger" / "handoffs" / self.expected["attempt"]

        receipt = self.archive(source, handoff_digest, archive_dir=missing)

        self.assertTrue(missing.is_dir())
        self.assertEqual(receipt["archive_dir"], str(missing))

    def test_process_interruption_resumes_only_from_matching_persistent_intent(self) -> None:
        source, handoff_digest = self.write_handoff()
        interrupted = """
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.environ['HANDOFF_SCRIPTS'])
import shiploop_chain_handoff as helper

original = helper._write_new
def interrupt(path, data):
    original(path, data)
    if path.name == 'handoff.json':
        os._exit(73)
helper._write_new = interrupt
helper.archive_handoff(
    Path(os.environ['HANDOFF_WORKSPACE']),
    Path(os.environ['HANDOFF_SOURCE']),
    os.environ['HANDOFF_DIGEST'],
    json.loads(os.environ['HANDOFF_EXPECTED']),
    Path(os.environ['HANDOFF_ARCHIVE']),
)
"""
        process = subprocess.run(
            [sys.executable, "-B", "-c", interrupted],
            text=True,
            capture_output=True,
            timeout=30,
            env={
                **os.environ,
                "HANDOFF_SCRIPTS": str(SCRIPTS),
                "HANDOFF_WORKSPACE": str(self.workspace),
                "HANDOFF_SOURCE": str(source),
                "HANDOFF_DIGEST": handoff_digest,
                "HANDOFF_EXPECTED": json.dumps(self.expected),
                "HANDOFF_ARCHIVE": str(self.archive_dir),
            },
        )
        self.assertEqual(process.returncode, 73, process.stdout + process.stderr)
        target = self.archive_dir / handoff_digest
        self.assertTrue((target / "intent.json").exists())
        self.assertTrue((target / "handoff.json").exists())
        self.assertFalse((target / "receipt.json").exists())

        receipt = self.archive(source, handoff_digest)

        self.assertTrue(Path(receipt["receipt_path"]).exists())
        self.assertEqual(Path(receipt["handoff"]["archived_path"]).read_bytes(), source.read_bytes())

    def test_receipt_before_chmod_replay_seals_archive_before_any_cleanup(self) -> None:
        source, handoff_digest = self.write_handoff()
        interrupted = """
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.environ['HANDOFF_SCRIPTS'])
import shiploop_chain_handoff as helper

def interrupt_after_receipt(target):
    os._exit(74)
helper._make_immutable = interrupt_after_receipt
helper.archive_handoff(
    Path(os.environ['HANDOFF_WORKSPACE']),
    Path(os.environ['HANDOFF_SOURCE']),
    os.environ['HANDOFF_DIGEST'],
    json.loads(os.environ['HANDOFF_EXPECTED']),
    Path(os.environ['HANDOFF_ARCHIVE']),
)
"""
        process = subprocess.run(
            [sys.executable, "-B", "-c", interrupted],
            text=True,
            capture_output=True,
            timeout=30,
            env={
                **os.environ,
                "HANDOFF_SCRIPTS": str(SCRIPTS),
                "HANDOFF_WORKSPACE": str(self.workspace),
                "HANDOFF_SOURCE": str(source),
                "HANDOFF_DIGEST": handoff_digest,
                "HANDOFF_EXPECTED": json.dumps(self.expected),
                "HANDOFF_ARCHIVE": str(self.archive_dir),
            },
        )
        self.assertEqual(process.returncode, 74, process.stdout + process.stderr)
        target = self.archive_dir / handoff_digest
        raw_receipt = (target / "receipt.json").read_bytes()
        interrupted_receipt = {**json.loads(raw_receipt), "receipt_sha256": digest(raw_receipt)}
        self.assertTrue(stat.S_IMODE(os.lstat(target / "receipt.json").st_mode) & 0o222)

        with self.assertRaises(handoff.ChainHandoffError):
            handoff.remove_imported_files(interrupted_receipt)
        self.assertTrue(source.exists())

        receipt = self.archive(source, handoff_digest)

        for path in (
            target / "intent.json",
            target / "handoff.json",
            target / "receipt.json",
            target / "files" / "result.json",
        ):
            self.assertEqual(stat.S_IMODE(os.lstat(path).st_mode), 0o444)
        for path in (target, target / "files"):
            self.assertEqual(stat.S_IMODE(os.lstat(path).st_mode), 0o555)
        handoff.remove_imported_files(receipt)
        self.assertFalse(source.exists())

    def test_validate_archive_is_read_only_after_worker_workspace_removal(self) -> None:
        source, handoff_digest = self.write_handoff()
        receipt = self.archive(source, handoff_digest)
        handoff.remove_imported_files(receipt)
        target = self.archive_dir / handoff_digest
        before_bytes = {
            path.relative_to(target).as_posix(): path.read_bytes()
            for path in target.rglob("*")
            if path.is_file()
        }
        before_modes = {
            path.relative_to(target).as_posix(): stat.S_IMODE(os.lstat(path).st_mode)
            for path in [target, *target.rglob("*")]
        }
        shutil.rmtree(self.workspace)
        self.assertFalse(self.workspace.exists())

        validated = handoff.validate_archive(receipt)

        self.assertEqual(validated, receipt)
        self.assertEqual(
            {
                path.relative_to(target).as_posix(): path.read_bytes()
                for path in target.rglob("*")
                if path.is_file()
            },
            before_bytes,
        )
        self.assertEqual(
            {
                path.relative_to(target).as_posix(): stat.S_IMODE(os.lstat(path).st_mode)
                for path in [target, *target.rglob("*")]
            },
            before_modes,
        )

    def test_validate_archive_rejects_mutated_bytes(self) -> None:
        source, handoff_digest = self.write_handoff()
        receipt = self.archive(source, handoff_digest)
        target = self.archive_dir / handoff_digest
        artifact = target / "files" / "result.json"
        os.chmod(target, 0o755)
        os.chmod(artifact, 0o644)
        artifact.write_bytes(b"mutated parent archive\n")

        with self.assertRaises(handoff.ChainHandoffError):
            handoff.validate_archive(receipt)

    def test_validate_archive_rejects_deleted_or_mutable_archive(self) -> None:
        with self.subTest("deleted artifact"):
            source, handoff_digest = self.write_handoff(attempt="deleted-archive")
            expected = {**self.expected, "attempt": "deleted-archive"}
            receipt = self.archive(source, handoff_digest, expected=expected)
            target = self.archive_dir / handoff_digest
            os.chmod(target, 0o755)
            os.chmod(target / "files", 0o755)
            os.unlink(target / "files" / "result.json")
            with self.assertRaises(handoff.ChainHandoffError):
                handoff.validate_archive(receipt)

        with self.subTest("mutable directory"):
            source, handoff_digest = self.write_handoff(attempt="mutable-archive")
            expected = {**self.expected, "attempt": "mutable-archive"}
            receipt = self.archive(source, handoff_digest, expected=expected)
            target = self.archive_dir / handoff_digest
            os.chmod(target, 0o755)
            with self.assertRaises(handoff.ChainHandoffError):
                handoff.validate_archive(receipt)

    def test_exception_cleanup_removes_only_the_new_archive_paths(self) -> None:
        source, handoff_digest = self.write_handoff()
        original = handoff._write_new

        def fail_after_handoff(path: Path, data: bytes) -> None:
            original(path, data)
            if path.name == "handoff.json":
                raise RuntimeError("synthetic archive write failure")

        with mock.patch.object(handoff, "_write_new", side_effect=fail_after_handoff):
            with self.assertRaisesRegex(RuntimeError, "synthetic archive write failure"):
                self.archive(source, handoff_digest)
        self.assertFalse((self.archive_dir / handoff_digest).exists())

    def test_incomplete_archive_with_unknown_content_is_retained_as_a_blocker(self) -> None:
        source, handoff_digest = self.write_handoff()
        target = self.archive_dir / handoff_digest
        target.mkdir()
        intent = {
            "schema": "shiploop-chain-import-intent/v1",
            "run_id": self.expected["run_id"],
            "step": self.expected["step"],
            "attempt": self.expected["attempt"],
            "base_commit": self.expected["base_commit"],
            "workspace": str(self.workspace),
            "handoff_path": str(source),
            "handoff_sha256": handoff_digest,
        }
        (target / "intent.json").write_bytes(handoff._canonical_json(intent))
        unknown = target / "unrelated-parent-file.txt"
        unknown.write_bytes(b"do not remove\n")

        with self.assertRaises(handoff.ChainHandoffError):
            self.archive(source, handoff_digest)
        self.assertTrue(unknown.exists())
        self.assertFalse((target / "receipt.json").exists())

    def test_symlink_path_traversal_unknown_and_duplicate_declarations_are_rejected(self) -> None:
        with self.subTest("symlink"):
            path, handoff_digest = self.write_handoff(attempt="symlink-1")
            outside = self.base / "outside.txt"
            outside.write_bytes(b"outside\n")
            result = path.parent / "result.json"
            result.unlink()
            result.symlink_to(outside)
            expected = {**self.expected, "attempt": "symlink-1"}
            with self.assertRaises(handoff.ChainHandoffError):
                self.archive(path, handoff_digest, expected=expected)

        with self.subTest("path traversal"):
            path, handoff_digest = self.write_handoff(
                attempt="traversal-1",
                payload_files=[{"path": "../outside.txt", "sha256": digest(b"outside\n")}],
            )
            expected = {**self.expected, "attempt": "traversal-1"}
            with self.assertRaises(handoff.ChainHandoffError):
                self.archive(path, handoff_digest, expected=expected)

        with self.subTest("unknown"):
            path, handoff_digest = self.write_handoff(attempt="unknown-1")
            (path.parent / "not-declared.txt").write_bytes(b"surplus\n")
            expected = {**self.expected, "attempt": "unknown-1"}
            with self.assertRaises(handoff.ChainHandoffError):
                self.archive(path, handoff_digest, expected=expected)

        with self.subTest("duplicate"):
            duplicate = {"path": "result.json", "sha256": digest(b'{"result":"ok"}\n')}
            path, handoff_digest = self.write_handoff(
                attempt="duplicate-1", payload_files=[duplicate, dict(duplicate)]
            )
            expected = {**self.expected, "attempt": "duplicate-1"}
            with self.assertRaises(handoff.ChainHandoffError):
                self.archive(path, handoff_digest, expected=expected)

    def test_wrong_identity_and_digest_are_rejected(self) -> None:
        source, handoff_digest = self.write_handoff()
        with self.assertRaises(handoff.ChainHandoffError):
            self.archive(source, handoff_digest, expected={**self.expected, "run_id": "other-run"})
        with self.assertRaises(handoff.ChainHandoffError):
            self.archive(source, "0" * 64)
        self.assertFalse((self.archive_dir / handoff_digest).exists())

    def test_tracked_handoff_file_is_rejected(self) -> None:
        source, handoff_digest = self.write_handoff()
        artifact = source.parent / "result.json"
        self.git("add", str(artifact.relative_to(self.workspace)))
        self.git("commit", "-qm", "tracked handoff fixture")

        with self.assertRaises(handoff.ChainHandoffError):
            self.archive(source, handoff_digest)
        self.assertFalse((self.archive_dir / handoff_digest).exists())

    def test_existing_archive_with_another_receipt_is_a_conflict(self) -> None:
        source, handoff_digest = self.write_handoff()
        conflicting = self.archive_dir / handoff_digest
        conflicting.mkdir()
        (conflicting / "receipt.json").write_text("{}\n", encoding="utf-8")

        with self.assertRaises(handoff.ChainHandoffError):
            self.archive(source, handoff_digest)
        self.assertTrue(source.exists())

    def test_changed_source_bytes_refuse_cleanup(self) -> None:
        source, handoff_digest = self.write_handoff()
        receipt = self.archive(source, handoff_digest)
        artifact = source.parent / "result.json"
        artifact.write_bytes(b"changed after import\n")

        with self.assertRaises(handoff.ChainHandoffError):
            handoff.remove_imported_files(receipt)
        self.assertTrue(source.exists())
        self.assertTrue(artifact.exists())

    def test_partial_cleanup_recovers_without_deleting_unrecorded_files(self) -> None:
        source, handoff_digest = self.write_handoff(files={"scratch/result.txt": b"result\n"})
        receipt = self.archive(source, handoff_digest)
        result = source.parent / "scratch" / "result.txt"
        result.unlink()
        extra = source.parent / "keep.txt"
        extra.write_bytes(b"unrecorded\n")

        cleanup = handoff.remove_imported_files(receipt)

        self.assertIn(str(result), cleanup["already_removed"])
        self.assertFalse(source.exists())
        self.assertTrue(extra.exists())
        self.assertTrue(source.parent.exists())
        self.assertIn(str(source.parent), cleanup["directories_retained"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
