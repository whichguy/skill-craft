import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import materialize
import scope_evidence as scope

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e" / "stage_suite"))
from stage_live import snapshot

CASE = {"allowed_source_subtrees": ["src/**"],
        "allowed_documentation_paths": ["SHIPLOOP.md"],
        "scope_exclusions": ["docs/shiploop/**", ".shiploop-improve/**"]}


def tempdir():
    scratch = ROOT / "reports" / "security-harness" / "tmp"
    return tempfile.TemporaryDirectory(dir=scratch if scratch.is_dir() else None)


def git(root, *args):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.check_output(["git", "-C", str(root), *args], env=env,
                                   stderr=subprocess.PIPE, text=True).strip()


class NativeScope(unittest.TestCase):
    def setUp(self):
        folder = tempdir()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        self.fixture = self.root / "fixture"
        self.fixture.mkdir()
        (self.fixture / "src").mkdir()
        ledger = self.fixture / "src" / "ledger.json"
        ledger.write_text('{"total":0}\n')
        ledger.chmod(0o644)
        (self.fixture / ".gitignore").write_text("*.log\n")
        (self.fixture / ".gitignore").chmod(0o644)
        git(self.fixture, "init", "-q")
        git(self.fixture, "add", "src/ledger.json", ".gitignore")
        git(self.fixture, "-c", "user.name=Scratch", "-c", "user.email=scratch@example.invalid",
            "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "fixture")
        self.before_fixture = scope.inventory(self.fixture)
        # Fixture directory also contains its own .git; actual selections exclude it.
        self.before_fixture = {k: v for k, v in self.before_fixture.items() if not k.startswith(".git/")}

    def worktree(self, mask, name):
        target = self.root / name
        previous = os.umask(mask)
        try:
            git(self.fixture, "worktree", "add", "--detach", "-q", str(target))
        finally:
            os.umask(previous)
        return target

    def capture(self, work, trial, phase, binding):
        receipt = scope.capture(snapshot, work, trial, phase, binding)
        return receipt, scope.verify(trial, phase, receipt, binding)

    def test_git_umasks_do_not_count_as_subject_changes(self):
        for umask, expected in ((0o022, 0o644), (0o077, 0o600)):
            with self.subTest(umask=umask):
                work = self.worktree(umask, f"work-{umask:o}")
                trial = self.root / f"trial-{umask:o}"
                trial.mkdir()
                (work / "ignored.log").write_text("not selected")
                binding = scope.binding(trial, work, "cosmetic", "baseline", "a0")
                _, start = self.capture(work, trial, "start", binding)
                _, final = self.capture(work, trial, "terminal", binding)
                self.assertEqual(start["entries"]["src/ledger.json"]["mode"], expected)
                self.assertNotIn("ignored.log", start["entries"])
                self.assertNotIn(".git", start["entries"])
                result = scope.compare(CASE, start["entries"], final["entries"], fixture=self.before_fixture)
                self.assertTrue(result["pass"])
                self.assertEqual(result["changed_paths"], [])
                self.assertEqual("src/ledger.json" in result["fixture_to_native_mode_differences"], umask == 0o077)

    def test_real_subject_chmod_is_visible_without_git_diff(self):
        work = self.worktree(0o022, "work")
        trial = self.root / "trial"
        trial.mkdir()
        binding = scope.binding(trial, work, "cosmetic", "baseline", "a0")
        _, start = self.capture(work, trial, "start", binding)
        (work / "src" / "ledger.json").chmod(0o600)
        self.assertEqual(git(work, "status", "--porcelain"), "")
        _, final = self.capture(work, trial, "terminal", binding)
        result = scope.compare(CASE, start["entries"], final["entries"], fixture=self.before_fixture)
        self.assertFalse(result["pass"])
        self.assertEqual(result["regular_file_mode_changes"], {"src/ledger.json": {"start": 0o644, "terminal": 0o600}})
        self.assertEqual(result["new_executable_files"], [])

    def test_missing_stale_and_post_capture_mode_tampering_are_not_evidence(self):
        work = self.worktree(0o022, "work")
        trial = self.root / "trial"
        trial.mkdir()
        binding = scope.binding(trial, work, "cosmetic", "baseline", "a0")
        with self.assertRaisesRegex(ValueError, "missing"):
            scope.verify(trial, "start", "absent", binding)
        first, _ = self.capture(work, trial, "start", binding)
        stale = {**binding, "seed_action": "older-a0"}
        with self.assertRaisesRegex(ValueError, "identity"):
            scope.verify(trial, "start", first, stale)
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.capture(work, trial, "start", binding)
        final, _ = self.capture(work, trial, "terminal", binding)
        (trial / "product-export" / "src" / "ledger.json").chmod(0o600)
        with self.assertRaisesRegex(ValueError, "mode mismatch"):
            scope.verify(trial, "terminal", final, binding)
        # A receipt altered to match changed permissions still fails its external digest.
        path = scope.receipt_path(trial, "terminal")
        data = json.loads(path.read_text())
        data["entries"]["src/ledger.json"]["mode"] = 0o600
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            scope.verify(trial, "terminal", final, binding)

    def test_root_document_is_visible_but_does_not_widen_the_scope(self):
        work = self.worktree(0o022, "work")
        before = scope.inventory(work)
        target = work / "SHIPLOOP.md"
        target.write_text("Product knowledge index\n")
        ok = scope.compare(CASE, before, scope.inventory(work))
        self.assertTrue(ok["pass"])
        self.assertEqual(ok["changed_paths"], ["SHIPLOOP.md"])
        target.chmod(0o755)
        self.assertEqual(scope.compare(CASE, before, scope.inventory(work))["new_executable_files"], ["SHIPLOOP.md"])
        target.unlink()
        target.symlink_to("/outside/product")
        self.assertEqual(scope.compare(CASE, before, scope.inventory(work))["link_paths"], ["SHIPLOOP.md"])
        target.unlink()
        (work / "other-root.md").write_text("not allowed\n")
        self.assertEqual(scope.compare(CASE, before, scope.inventory(work))["outside_allowed_subtrees"], ["other-root.md"])

    def test_skipped_tracked_child_below_link_cannot_hide_escape(self):
        work = self.worktree(0o022, "work")
        trial = self.root / "trial"
        trial.mkdir()
        binding = scope.binding(trial, work, "cosmetic", "baseline", "a0")
        _, start = self.capture(work, trial, "start", binding)
        (work / "src/ledger.json").unlink()
        (work / "src").rmdir()
        (work / "src").symlink_to(self.fixture / "src")
        _, final = self.capture(work, trial, "terminal", binding)
        self.assertNotIn("src/ledger.json", final["entries"])
        result = scope.compare(CASE, start["entries"], final["entries"], skipped=final["export"]["skipped"])
        self.assertFalse(result["pass"])
        self.assertEqual(result["native_skipped_paths"], ["src/ledger.json"])


class Materializer(unittest.TestCase):
    def setUp(self):
        folder = tempdir()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name).resolve()
        self.source = self.root / "frozen"
        self.source.mkdir()
        self.out = self.root / "fresh"
        self.recipe = self.root / "recipe"
        self.recipe.mkdir()
        (self.source / "registration.json").write_bytes(b"frozen-registration")
        (self.source / "fixture.txt").write_bytes(b"original\n")
        (self.source / "credentials-that-must-not-copy").write_text("inert canary")
        (self.recipe / "scope_evidence.py").write_text("inert\n")
        (self.recipe / "logger_failure.cjs").write_text("inert\n")
        (self.recipe / "controls.py").write_text("inert\n")
        (self.recipe / "v6.patch").write_text(
            "--- a/fixture.txt\n+++ b/fixture.txt\n@@ -1 +1 @@\n-original\n+repaired\n")
        bindings = patch.multiple(materialize, HERE=self.recipe, CASES=(), FILES=("fixture.txt",),
            V5_REGISTRATION=hashlib.sha256(b"frozen-registration").hexdigest(),
            V5_PATHS=hashlib.sha256(b'["fixture.txt"]').hexdigest(),
            V5_SOURCES=materialize.source_digest([("fixture.txt", (self.source / "fixture.txt").stat().st_mode & 0o777,
                                                   b"original\n")]))
        bindings.start()
        self.addCleanup(bindings.stop)
        adder = patch.object(materialize, "add_controls", lambda _: None)
        adder.start()
        self.addCleanup(adder.stop)

    def test_only_pinned_source_files_materialize_and_never_overwrite(self):
        receipt = materialize.materialize(self.source, self.out)
        self.assertEqual(receipt["source_files"], 1)
        self.assertEqual((self.out / "fixture.txt").read_text(), "repaired\n")
        self.assertEqual((self.source / "fixture.txt").read_text(), "original\n")
        self.assertFalse((self.out / "credentials-that-must-not-copy").exists())
        self.assertFalse((self.out / "registration.json").exists())
        with self.assertRaisesRegex(ValueError, "already exists"):
            materialize.materialize(self.source, self.out)
        with self.assertRaisesRegex(ValueError, "separate"):
            materialize.materialize(self.source, self.source / "nested")
        alias = self.root / "alias"
        alias.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "symlink"):
            materialize.materialize(alias, self.root / "another")

    def test_mutated_source_or_symlink_refuses_before_output(self):
        (self.source / "fixture.txt").write_text("mutated\n")
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            materialize.materialize(self.source, self.out)
        (self.source / "fixture.txt").unlink()
        (self.source / "fixture.txt").symlink_to(self.recipe / "scope_evidence.py")
        with self.assertRaisesRegex(ValueError, "source type"):
            materialize.materialize(self.source, self.out)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
