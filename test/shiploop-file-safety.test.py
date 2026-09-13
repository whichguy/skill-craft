#!/usr/bin/env python3
"""Regression tests for ShipLoop-owned ignore and evidence-log paths."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CORE_PATH = SCRIPTS / "shiploop"
EVIDENCE_PATH = SCRIPTS / "shiploop_evidence.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_core():
    loader = importlib.machinery.SourceFileLoader(
        "shiploop_file_safety_core", str(CORE_PATH)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError(f"could not load {CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    loader.exec_module(module)
    return module


def load_evidence():
    spec = importlib.util.spec_from_file_location(
        "shiploop_file_safety_evidence", EVIDENCE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {EVIDENCE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = load_core()
EVIDENCE = load_evidence()


class ShipLoopFileSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-file-safety-")
        self.addCleanup(self.temp.cleanup)
        # macOS's /var is a system symlink; fixture paths use their physical form
        # so tests isolate the intentionally-created aliases below.
        self.root = Path(self.temp.name).resolve()

    def make_repo(self, name: str) -> Path:
        repo = self.root / name
        repo.mkdir()
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.email", "test@example.invalid")
        self.git(repo, "config", "user.name", "ShipLoop File Safety Test")
        self.git(repo, "commit", "--allow-empty", "-qm", "baseline")
        return repo

    def git(self, repo: Path, *argv: str, code: int = 0) -> str:
        result = subprocess.run(
            ["git", "-C", os.fspath(repo), *argv],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result.stdout.strip()

    def exclude_path(self, repo: Path) -> Path:
        raw = self.git(
            repo,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "info/exclude",
        )
        return Path(raw)

    def assert_core_blocked(self, callback) -> None:
        raised = None
        try:
            callback()
        except SystemExit as exc:
            raised = exc
        self.assertIsNotNone(raised, "unsafe ignore mutation must be blocked")
        self.assertEqual(raised.code, CORE.EXIT_BLOCKED)

    def assert_evidence_blocked(self, callback) -> None:
        raised = None
        try:
            callback()
        except EVIDENCE.EvidenceError as exc:
            raised = exc
        self.assertIsNotNone(raised, "unsafe evidence-log mutation must be blocked")

    def assert_unchanged(self, path: Path, content: bytes, mode: int) -> None:
        self.assertEqual(path.read_bytes(), content)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), mode)

    def test_ignore_aliases_block_without_changing_external_sentinel(self) -> None:
        for kind in ("symlink", "hardlink"):
            with self.subTest(kind=kind):
                repo = self.make_repo(kind)
                exclude = self.exclude_path(repo)
                exclude.unlink()
                sentinel = self.root / f"{kind}.sentinel"
                before = b"external sentinel\n"
                sentinel.write_bytes(before)
                sentinel.chmod(0o640)
                mode = stat.S_IMODE(sentinel.stat().st_mode)
                if kind == "symlink":
                    os.symlink(sentinel, exclude)
                else:
                    os.link(sentinel, exclude)

                raised = None
                try:
                    CORE.ensure_worktrees_excluded(repo)
                except SystemExit as exc:
                    raised = exc
                self.assert_unchanged(sentinel, before, mode)
                self.assertIsNotNone(raised, "unsafe ignore mutation must be blocked")
                self.assertEqual(raised.code, CORE.EXIT_BLOCKED)

    def test_ignore_rejects_symlink_ancestor_and_nonregular_leaf(self) -> None:
        repo = self.make_repo("ignore-ancestor")
        exclude = self.exclude_path(repo)
        info = exclude.parent
        safe_info = info.with_name("info.saved")
        info.rename(safe_info)
        external_info = self.root / "external-info"
        external_info.mkdir()
        sentinel = external_info / "exclude"
        before = b"ancestor sentinel\n"
        sentinel.write_bytes(before)
        sentinel.chmod(0o640)
        mode = stat.S_IMODE(sentinel.stat().st_mode)
        os.symlink(external_info, info)

        raised = None
        try:
            CORE.ensure_worktrees_excluded(repo)
        except SystemExit as exc:
            raised = exc
        self.assert_unchanged(sentinel, before, mode)
        self.assertIsNotNone(raised, "symlinked info parent must be blocked")
        self.assertEqual(raised.code, CORE.EXIT_BLOCKED)

        repo = self.make_repo("ignore-directory")
        exclude = self.exclude_path(repo)
        exclude.unlink()
        exclude.mkdir()
        self.assert_core_blocked(lambda: CORE.ensure_worktrees_excluded(repo))

    def test_ignore_validates_owned_metadata_before_check_ignore(self) -> None:
        repo = self.make_repo("ignore-order")
        exclude = self.exclude_path(repo)
        exclude.unlink()
        sentinel = self.root / "order.sentinel"
        before = b"order sentinel\n"
        sentinel.write_bytes(before)
        sentinel.chmod(0o640)
        mode = stat.S_IMODE(sentinel.stat().st_mode)
        os.link(sentinel, exclude)
        checked: list[tuple[str, ...]] = []
        original = CORE.git_run

        def record_probe(repo_arg: Path, *argv: str, **kwargs):
            if argv and argv[0] == "check-ignore":
                checked.append(argv)
            return original(repo_arg, *argv, **kwargs)

        raised = None
        with patch.object(CORE, "git_run", side_effect=record_probe):
            try:
                CORE.ensure_worktrees_excluded(repo)
            except SystemExit as exc:
                raised = exc
        self.assert_unchanged(sentinel, before, mode)
        self.assertEqual(checked, [])
        self.assertIsNotNone(raised, "unsafe exclude metadata must block first")
        self.assertEqual(raised.code, CORE.EXIT_BLOCKED)

    def test_ignore_is_added_once_and_works_from_a_linked_worktree(self) -> None:
        repo = self.make_repo("main")
        CORE.ensure_worktrees_excluded(repo)
        exclude = self.exclude_path(repo)
        first = exclude.read_bytes()
        first_mode = stat.S_IMODE(exclude.stat().st_mode)
        self.assertEqual(
            self.git(repo, "check-ignore", "-q", "--", ".worktrees/probe", code=0),
            "",
        )
        CORE.ensure_worktrees_excluded(repo)
        self.assert_unchanged(exclude, first, first_mode)
        self.assertEqual(exclude.read_text(encoding="utf-8").count(".worktrees/"), 1)

        linked = self.root / "linked"
        self.git(repo, "worktree", "add", "-q", "-b", "linked", os.fspath(linked))
        CORE.ensure_worktrees_excluded(linked)
        common = Path(
            self.git(
                linked,
                "rev-parse",
                "--path-format=absolute",
                "--git-common-dir",
            )
        )
        linked_exclude = common / "info" / "exclude"
        self.assertEqual(linked_exclude, self.exclude_path(linked))
        self.assertIn(".worktrees/", linked_exclude.read_text(encoding="utf-8"))
        self.git(linked, "check-ignore", "-q", "--", ".worktrees/probe", code=0)

    def test_ignore_reasserts_after_local_negation_and_blocks_product_negation(self) -> None:
        repo = self.make_repo("exclude-negation")
        exclude = self.exclude_path(repo)
        exclude.write_text(".worktrees/\n!.worktrees/\n", encoding="utf-8")
        mode = stat.S_IMODE(exclude.stat().st_mode)
        CORE.ensure_worktrees_excluded(repo)
        self.assertEqual(
            exclude.read_text(encoding="utf-8"),
            ".worktrees/\n!.worktrees/\n.worktrees/\n",
        )
        self.assertEqual(stat.S_IMODE(exclude.stat().st_mode), mode)
        self.git(repo, "check-ignore", "-q", "--", ".worktrees/probe", code=0)

        repo = self.make_repo("product-negation")
        exclude = self.exclude_path(repo)
        product_ignore = repo / ".gitignore"
        product_before = b"!.worktrees/\n"
        product_ignore.write_bytes(product_before)
        product_ignore.chmod(0o640)
        product_mode = stat.S_IMODE(product_ignore.stat().st_mode)
        self.assert_core_blocked(lambda: CORE.ensure_worktrees_excluded(repo))
        self.assertEqual(exclude.read_text(encoding="utf-8").splitlines()[-1], ".worktrees/")
        self.assert_unchanged(product_ignore, product_before, product_mode)
        self.git(repo, "check-ignore", "-q", "--", ".worktrees/probe", code=1)

    def test_log_aliases_and_symlink_ancestor_preserve_sentinels(self) -> None:
        logs = self.root / "logs"
        logs.mkdir()
        for kind in ("hardlink", "symlink"):
            with self.subTest(kind=kind):
                sentinel = self.root / f"log-{kind}.sentinel"
                before = b"private sentinel\n"
                sentinel.write_bytes(before)
                sentinel.chmod(0o640)
                mode = stat.S_IMODE(sentinel.stat().st_mode)
                target = logs / f"{kind}.log"
                if kind == "hardlink":
                    os.link(sentinel, target)
                else:
                    os.symlink(sentinel, target)

                raised = None
                try:
                    EVIDENCE._write_log(target, b"replacement\n")
                except EVIDENCE.EvidenceError as exc:
                    raised = exc
                self.assert_unchanged(sentinel, before, mode)
                self.assertIsNotNone(raised, "log alias must be blocked")

        external = self.root / "external-logs"
        external.mkdir()
        sentinel = external / "escape.log"
        before = b"ancestor sentinel\n"
        sentinel.write_bytes(before)
        sentinel.chmod(0o640)
        mode = stat.S_IMODE(sentinel.stat().st_mode)
        os.symlink(external, logs / "linked")
        raised = None
        try:
            EVIDENCE._write_log(logs / "linked" / "escape.log", b"replacement\n")
        except EVIDENCE.EvidenceError as exc:
            raised = exc
        self.assert_unchanged(sentinel, before, mode)
        self.assertIsNotNone(raised, "symlinked log ancestor must be blocked")

    def test_log_rejects_nonregular_leaf_and_allows_safe_retry_overwrite(self) -> None:
        logs = self.root / "retry-logs"
        logs.mkdir()
        directory_target = logs / "directory.log"
        directory_target.mkdir()
        self.assert_evidence_blocked(
            lambda: EVIDENCE._write_log(directory_target, b"must not write\n")
        )

        retry = logs / "retry.log"
        EVIDENCE._write_log(retry, b"first\n")
        EVIDENCE._write_log(retry, b"second\n")
        self.assertEqual(retry.read_bytes(), b"second\n")
        self.assertEqual(stat.S_IMODE(retry.stat().st_mode), 0o600)
        self.assertEqual(retry.stat().st_nlink, 1)

    def test_run_checks_rejects_a_symlinked_evidence_ancestor_before_creation(self) -> None:
        repo = self.make_repo("evidence-repo")
        logs = self.root / "run-check-logs"
        logs.mkdir()
        external = self.root / "external-evidence"
        external.mkdir()
        os.symlink(external, logs / "linked")
        manifest = {
            "checks": [
                {
                    "id": "lint",
                    "kind": "lint",
                    "argv": [sys.executable, "-c", "pass"],
                    "acceptance": [],
                },
                {
                    "id": "test",
                    "kind": "test",
                    "argv": [sys.executable, "-c", "pass"],
                    "acceptance": ["safe output"],
                },
            ]
        }
        raised = None
        try:
            EVIDENCE.run_checks(repo, manifest, logs / "linked" / "run", "A1")
        except EVIDENCE.EvidenceError as exc:
            raised = exc
        self.assertFalse((external / "run").exists())
        self.assertIsNotNone(raised, "symlinked evidence ancestor must be blocked")


if __name__ == "__main__":
    unittest.main(verbosity=2)
