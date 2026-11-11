"""Synthetic R1/R2 controls, independent of archives, products and hosts."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from v7 import git_context as context


BINDING = {
    "registration_sha256": "1" * 64,
    "scope_start_sha256": "2" * 64,
    "scope_terminal_sha256": "3" * 64,
    "trial_id": "synthetic-trial",
    "case_id": "synthetic-case",
    "lifecycle": {"endpoint": "inner"},
}
MARKER = b"test-only-committed-then-deleted-87b90c4"
OTHER = "test-only-base64-25938ca"


class GitContextTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="v7-git-tests-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.home = self.root / "home"
        self.home.mkdir()
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.env = {
            "PATH": os.environ["PATH"], "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home), "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CEILING_DIRECTORIES": str(self.root),
            "GIT_ATTR_NOSYSTEM": "1", "GIT_OPTIONAL_LOCKS": "0", "GIT_CONFIG_COUNT": "0",
        }
        self.git("init", "-q", "-b", "main", "--object-format=sha1", "--template=")
        self.git("config", "user.name", "Synthetic test")
        self.git("config", "user.email", "synthetic@example.invalid")
        self.put("keep", b"original\n")
        self.put("deleted", b"remove me\n")
        self.put(".gitignore", b"ignored\n")
        self.git("add", "--", ".gitignore", "deleted", "keep")
        self.git("commit", "-qm", "synthetic base")
        self.export = self.root / "export"
        self.retained = self.root / "context"
        self.output = self.root / "output"

    def git(self, *args, root=None, data=None, check=True):
        # Fixture commands must not start background maintenance during Git context capture.
        return subprocess.run(
            ["git", "-C", str(root or self.repo), "-c", "maintenance.auto=false", *args],
            env=self.env, input=data,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check, timeout=15,
        )

    def put(self, name, body, *, mode=0o644, root=None):
        path = (root or self.repo) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)
        path.chmod(mode)
        return path

    def product_export(self, names, *, repo=None):
        repo = repo or self.repo
        self.export.mkdir()
        for name in names:
            source = repo / name
            dest = self.export / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest, follow_symlinks=False)
        return self.export

    def capture(self, repo=None):
        return context.capture(repo or self.repo, self.export, self.retained, binding=BINDING)

    def restore(self, expected=BINDING):
        return context.restore(self.retained, self.export, self.output, expected_binding=expected)

    def scan(self, markers=(MARKER,)):
        return context.scan(self.retained, expected_binding=BINDING, markers=markers)

    def clean_context(self):
        self.product_export((".gitignore", "deleted", "keep"))
        return self.capture()

    def rewrite_receipt(self, receipt, *, pack=None):
        if pack is not None:
            (self.retained / "objects.pack").write_bytes(pack)
            receipt["pack_sha256"] = hashlib.sha256(pack).hexdigest()
        receipt.pop("context_sha256", None)
        compact = lambda data: json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        receipt["context_sha256"] = hashlib.sha256(compact(receipt)).hexdigest()
        (self.retained / "receipt.json").write_bytes(compact(receipt) + b"\n")

    def test_detached_linked_worktree_exact_modes_and_dirty_index(self):
        linked = self.root / "linked"
        self.git("worktree", "add", "--detach", "-q", str(linked))
        self.put("sub/staged", b"staged-only bytes\n", root=linked, mode=0o700)
        self.git("add", "--", "sub/staged", root=linked)
        staged = self.git("rev-parse", ":sub/staged", root=linked).stdout.strip()
        self.assertNotIn(staged, self.git("rev-list", "--objects", "--all", root=linked).stdout)
        self.git("rm", "-q", "--", "deleted", root=linked)
        self.put("keep", b"unstaged\n", root=linked, mode=0o600)
        self.put("sub/untracked", b"untracked\n", root=linked, mode=0o640)
        self.put("ignored", b"ignored content\n", root=linked)
        self.put(".shiploop-runs/private", b"omitted evidence\n", root=linked)
        (linked / "link").symlink_to("keep")
        self.product_export((".gitignore", "keep", "sub/staged", "sub/untracked", "link"), repo=linked)
        (self.export / "sub").chmod(0o750)
        receipt = self.capture(linked)
        self.assertIsNone(receipt["head"]["symbolic"])
        self.assertEqual(1, receipt["omitted_untracked"])
        self.assertEqual(receipt["reachable_count"] + 1, receipt["object_count"])
        # No replay depends on the original linked worktree or object store.
        self.git("worktree", "remove", "--force", str(linked))
        self.repo.rename(self.root / "former-source")
        self.assertEqual(receipt, self.restore())
        self.assertEqual(staged, self.git("rev-parse", ":sub/staged", root=self.output).stdout.strip())
        self.assertEqual(b"staged-only bytes\n", self.git("show", ":sub/staged", root=self.output).stdout)
        self.assertEqual(b"", self.git("ls-files", "--", "deleted", root=self.output).stdout)
        self.assertFalse((self.output / "deleted").exists())
        self.assertEqual(
            b" M keep\n?? link\n?? sub/untracked\nA  sub/staged\nD  deleted\n",
            b"\n".join(sorted(self.git("status", "--porcelain", "-uall", root=self.output).stdout.splitlines())) + b"\n",
        )
        self.assertEqual(0o600, stat.S_IMODE((self.output / "keep").stat().st_mode))
        self.assertEqual(0o750, stat.S_IMODE((self.output / "sub").stat().st_mode))
        self.assertEqual(0o700, stat.S_IMODE((self.output / "sub/staged").stat().st_mode))
        self.assertEqual(0o640, stat.S_IMODE((self.output / "sub/untracked").stat().st_mode))
        self.assertEqual("keep", os.readlink(self.output / "link"))
        self.assertEqual("CLEAN", self.scan((b"staged-only bytes",))["status"])

    def test_attached_branch_refs_public_check_and_unrelated_failure(self):
        self.git("branch", "side")
        self.git("tag", "-a", "-m", "named tag", "tagged")
        self.git("pack-refs", "--all")
        self.git("gc", "--quiet")
        receipt = self.clean_context()
        self.assertEqual("refs/heads/main", receipt["head"]["symbolic"])
        self.assertIn("refs/tags/tagged", receipt["refs"])
        self.assertEqual(0o700, stat.S_IMODE(self.retained.stat().st_mode))
        for file in self.retained.iterdir():
            self.assertEqual(0o600, stat.S_IMODE(file.stat().st_mode))
        self.restore()

        def git_dependent_check(root):
            version = self.git("show", "HEAD:keep", root=root, check=False)
            entry = self.git("ls-tree", "HEAD", "--", "keep", root=root, check=False)
            return (version.returncode == entry.returncode == 0 and
                    version.stdout == (root / "keep").read_bytes() and entry.stdout.startswith(b"100644 ") and
                    stat.S_IMODE((root / "keep").stat().st_mode) == 0o644)

        self.assertFalse(git_dependent_check(self.export))
        self.assertTrue(git_dependent_check(self.output))
        for root in (self.export, self.output):
            unrelated = subprocess.run(["sh", "-c", 'test -f "$1/nonexistent" && exit 0; exit 23',
                                        "control", str(root)], env=self.env, timeout=5)
            self.assertEqual(23, unrelated.returncode)
        self.assertEqual(b"refs/heads/main\n", self.git("symbolic-ref", "HEAD", root=self.output).stdout)
        self.assertEqual(self.git("show-ref").stdout, self.git("show-ref", root=self.output).stdout)
        self.assertFalse((self.export / ".git").exists())
        with self.assertRaises(context.ContextError):
            self.restore()
        with self.assertRaises(context.ContextError):
            self.capture()

    def test_history_finds_deleted_literal_and_base64_through_side_ref(self):
        self.put("marker", MARKER)
        self.git("add", "marker")
        self.git("commit", "-qm", "historical marker")
        self.git("rm", "-q", "marker")
        self.git("commit", "-qm", "remove historical marker")
        self.git("switch", "-qc", "side")
        self.put("encoded", base64.b64encode(OTHER.encode()))
        self.git("add", "encoded")
        self.git("commit", "-qm", "marker on side ref")
        self.git("switch", "-q", "main")
        self.clean_context()
        self.assertFalse((self.export / "marker").exists())
        self.assertFalse((self.export / "encoded").exists())
        self.assertEqual(b"", self.git("status", "--porcelain", "-uall").stdout)
        scan = self.scan((MARKER, OTHER))
        self.assertEqual("FOUND", scan["status"])
        self.assertEqual(2, scan["matched_blobs"])
        self.assertGreater(scan["verified_blobs"], 2)
        self.assertNotIn(MARKER.decode(), json.dumps(scan))
        self.assertNotIn(OTHER, json.dumps(scan))
        self.assertNotIn("encoded", json.dumps(scan))

    def test_clean_history_nonzero_and_unreachable_marker_excluded(self):
        unreachable = self.git("hash-object", "-w", "--stdin", data=MARKER).stdout.strip()
        receipt = self.clean_context()
        scan = self.scan()
        self.assertEqual("CLEAN", scan["status"])
        self.assertEqual(0, scan["matched_blobs"])
        self.assertGreater(scan["verified_blobs"], 0)
        self.assertEqual(receipt["reachable_count"], scan["reachable_objects"])
        self.restore()
        self.assertNotEqual(0, self.git("cat-file", "-e", unreachable.decode(), root=self.output, check=False).returncode)

    def test_wrong_binding_export_and_receipt_digest_rejected(self):
        receipt = self.clean_context()
        wrong = {**BINDING, "trial_id": "different-trial"}
        with self.assertRaises(context.ContextError):
            self.restore(wrong)
        with self.assertRaises(context.ContextError):
            context.scan(self.retained, expected_binding=wrong, markers=[MARKER])
        path = self.export / "keep"
        path.chmod(0o600)
        with self.assertRaises(context.ContextError):
            self.restore()
        path.chmod(0o644)
        path = self.retained / "receipt.json"
        path.write_bytes(path.read_bytes().replace(receipt["export_sha256"].encode(), b"0" * 64))
        with self.assertRaises(context.ContextError):
            self.restore()
        self.assertFalse(self.output.exists())

    def test_missing_staged_object_even_with_recomputed_digest(self):
        self.put("staged", b"only staged\n")
        self.git("add", "staged")
        self.product_export((".gitignore", "deleted", "keep", "staged"))
        receipt = self.capture()
        unrelated = self.git("hash-object", "-w", "--stdin", data=b"replacement").stdout
        history = self.git("rev-list", "--objects", "--no-object-names", "HEAD").stdout
        pack = self.git("pack-objects", "--stdout", "--window=0", "--no-reuse-delta",
                        "--no-reuse-object", data=history + unrelated).stdout
        self.rewrite_receipt(receipt, pack=pack)
        with self.assertRaises(context.ContextError):
            self.restore()
        with self.assertRaises(context.ContextError):
            self.scan()
        self.assertFalse(self.output.exists())

    def test_truncation_malformed_index_and_limits_are_incomplete(self):
        receipt = self.clean_context()
        path = self.retained / "objects.pack"
        original = path.read_bytes()
        path.write_bytes(original[:-1])
        with self.assertRaises(context.ContextError):
            self.scan()
        self.rewrite_receipt(dict(receipt), pack=original[:-1])
        with self.assertRaises(context.ContextError):
            self.scan()
        self.rewrite_receipt(dict(receipt), pack=original)
        with patch.object(context, "MAX_OBJECT_BYTES", 2):
            with self.assertRaises(context.ContextError):
                self.scan()
        with patch.object(context, "MAX_TOTAL_BYTES", 2):
            with self.assertRaises(context.ContextError):
                self.scan()
        with patch.object(context, "MAX_PACK_BYTES", 32):
            with self.assertRaises(context.ContextError):
                self.scan()
        invalid = dict(receipt, index=[[1, receipt["head"]["oid"], "aw=="]])
        self.rewrite_receipt(invalid)
        with self.assertRaises(context.ContextError):
            self.scan()

    def test_truncated_batch_after_valid_pack_is_incomplete(self):
        self.clean_context()
        git = context._git

        def truncate(*args, **kwargs):
            result = git(*args, **kwargs)
            if args[2:4] == ("cat-file", "--batch"):
                return result[:-1]
            return result

        with patch.object(context, "_git", side_effect=truncate):
            with self.assertRaisesRegex(context.ContextError, "truncated Git object body"):
                self.scan()

    def test_native_selection_and_mid_capture_change_rejected(self):
        self.product_export((".gitignore", "deleted", "keep"))
        self.put("keep", b"changed after export\n")
        with self.assertRaises(context.ContextError):
            self.capture()
        self.put("keep", b"original\n")
        git = context._git

        def mutate(*args, **kwargs):
            result = git(*args, **kwargs)
            if args[2] == "pack-objects":
                self.git("update-ref", "refs/heads/moved", "HEAD")
            return result

        with patch.object(context, "_git", side_effect=mutate):
            with self.assertRaises(context.ContextError):
                self.capture()
        self.assertFalse(self.retained.exists())

    def test_hooks_and_inherited_git_configuration_are_not_executed(self):
        sentinel = self.root / "executed"
        hook = self.put("hook", f"#!/bin/sh\ntouch '{sentinel}'\nexit 1\n".encode(), root=self.root, mode=0o700)
        hooks = self.root / "hooks"
        hooks.mkdir()
        shutil.copy2(hook, hooks / "pre-commit")
        self.git("config", "core.hooksPath", str(hooks))
        self.git("config", "core.fsmonitor", str(hook))
        self.product_export((".gitignore", "deleted", "keep"))
        with patch.dict(os.environ, {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.fsmonitor",
                                     "GIT_CONFIG_VALUE_0": str(hook), "GIT_DIR": str(self.home),
                                     "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(self.home)}):
            self.capture()
            self.restore()
            self.assertEqual("CLEAN", self.scan()["status"])
        self.assertFalse(sentinel.exists())
        self.assertNotIn(str(hook).encode(), (self.output / ".git" / "config").read_bytes())
        self.assertFalse((self.output / ".git" / "hooks").exists())
        self.git("-c", "user.name=Synthetic", "-c", "user.email=s@example.invalid",
                 "commit", "--allow-empty", "-qm", "replay only", root=self.output)
        self.assertFalse(sentinel.exists())

    def test_alternate_source_include_and_nested_discovery_rejected(self):
        self.product_export((".gitignore", "deleted", "keep"))
        alternates = self.put(".git/objects/info/alternates", b"/outside/objects\n")
        with self.assertRaises(context.ContextError):
            self.capture()
        alternates.unlink()
        alternates.symlink_to(self.home)
        with self.assertRaises(context.ContextError):
            self.capture()
        alternates.unlink()
        (self.repo / "sub").mkdir()
        with self.assertRaises(context.ContextError):
            self.capture(self.repo / "sub")
        external = self.put("external-config", b"[core]\n\tfilemode = false\n", root=self.root)
        self.git("config", "include.path", str(external))
        with self.assertRaises(context.ContextError):
            self.capture()
        self.assertFalse(self.retained.exists())

    def test_unsupported_index_flags_rejected(self):
        self.product_export((".gitignore", "deleted", "keep"))
        self.git("update-index", "--skip-worktree", "keep")
        with self.assertRaises(context.ContextError):
            self.capture()
        self.git("update-index", "--no-skip-worktree", "keep")
        self.put("intent", b"not in ordinary staged state\n")
        self.git("add", "-N", "intent")
        with self.assertRaises(context.ContextError):
            self.capture()
        self.assertFalse(self.retained.exists())

    def test_conflict_and_gitlink_rejected(self):
        self.product_export((".gitignore", "deleted", "keep"))
        oid = self.git("rev-parse", "HEAD:keep").stdout.strip()
        self.git("update-index", "--index-info",
                 data=b"0 " + b"0" * 40 + b"\tkeep\n100644 " + oid + b" 1\tkeep\n")
        with self.assertRaises(context.ContextError):
            self.capture()
        self.git("read-tree", "HEAD")
        commit = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("update-index", "--index-info", data=b"160000 " + commit + b"\tsubmodule\n")
        with self.assertRaises(context.ContextError):
            self.capture()
        self.assertFalse(self.retained.exists())


if __name__ == "__main__":
    unittest.main()
