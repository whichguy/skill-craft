from pathlib import Path
import tempfile
import unittest

from v7.auth_cleanup import cleanup_auth_link


class AuthLinkCleanup(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.base = Path(directory.name)
        self.trial = self.base / "trial"
        self.trial.mkdir()
        self.home = self.trial / "home"
        self.codex = self.home / ".codex"
        self.link = self.codex / "auth.json"
        self.target = self.base / "synthetic-target"
        self.target.write_bytes(b"inert fixture")

    def test_missing_at_each_prelaunch_stage_is_ok(self):
        for parent in (None, self.home, self.codex):
            if parent is not None:
                parent.mkdir()
            self.assertEqual(cleanup_auth_link(self.trial, drained=True)["status"], "absent")
            self.assertEqual(self.target.read_bytes(), b"inert fixture")

    def test_only_owned_link_removed_and_repeated_cleanup_is_safe(self):
        self.codex.mkdir(parents=True)
        self.link.symlink_to(self.target)
        sibling = self.codex / "unrelated"
        sibling.symlink_to(self.target)
        before = self.target.stat()
        self.assertEqual(cleanup_auth_link(self.trial, drained=True), {"status": "removed"})
        self.assertFalse(self.link.is_symlink())
        self.assertTrue(sibling.is_symlink())
        self.assertEqual(self.target.read_bytes(), b"inert fixture")
        after = self.target.stat()
        self.assertEqual((before.st_ino, before.st_mode, before.st_mtime_ns),
                         (after.st_ino, after.st_mode, after.st_mtime_ns))
        self.assertEqual(cleanup_auth_link(self.trial, drained=True)["status"], "absent")

    def test_broken_final_symlink_is_removed(self):
        self.codex.mkdir(parents=True)
        missing = self.base / "missing"
        self.link.symlink_to(missing)
        self.assertEqual(cleanup_auth_link(self.trial, drained=True)["status"], "removed")
        self.assertFalse(self.link.is_symlink())
        self.assertFalse(missing.exists())

    def test_linked_parent_is_refused_without_touching_external_link(self):
        outside = self.base / "outside"
        outside_codex = outside / ".codex"
        outside_codex.mkdir(parents=True)
        outside_link = outside_codex / "auth.json"
        outside_link.symlink_to(self.target)
        self.home.symlink_to(outside)
        self.assertEqual(cleanup_auth_link(self.trial, drained=True)["status"], "refused")
        self.assertTrue(self.home.is_symlink())
        self.assertTrue(outside_link.is_symlink())
        self.home.unlink()
        self.home.mkdir()
        self.codex.symlink_to(outside_codex)
        self.assertEqual(cleanup_auth_link(self.trial, drained=True)["status"], "refused")
        self.assertTrue(self.codex.is_symlink())
        self.assertTrue(outside_link.is_symlink())
        self.assertEqual(self.target.read_bytes(), b"inert fixture")

    def test_non_directory_parent_is_refused(self):
        self.home.mkdir()
        self.codex.write_bytes(b"unexpected parent")
        self.assertEqual(cleanup_auth_link(self.trial, drained=True)["status"], "refused")
        self.assertEqual(self.codex.read_bytes(), b"unexpected parent")

    def test_unexpected_regular_final_file_is_preserved(self):
        self.codex.mkdir(parents=True)
        self.link.write_bytes(b"unexpected file")
        self.assertEqual(cleanup_auth_link(self.trial, drained=True)["status"], "refused")
        self.assertEqual(self.link.read_bytes(), b"unexpected file")

    def test_link_kept_when_process_drain_is_unverified(self):
        self.codex.mkdir(parents=True)
        self.link.symlink_to(self.target)
        self.assertEqual(cleanup_auth_link(self.trial, drained=False)["status"], "not-drained")
        self.assertTrue(self.link.is_symlink())
