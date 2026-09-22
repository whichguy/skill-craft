#!/usr/bin/env python3
"""Hermetic real-Git acceptance tests for ShipLoop workspace return.

The test repository is deliberately dirty before ``prepare``.  That makes the
important boundary observable: ShipLoop may build a private candidate from the
user's starting state, but it must neither rewrite the user's index nor return
run-local artifacts when the candidate comes back.
"""

from __future__ import annotations

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
CLI = SCRIPTS / "shiploop"
GIT = shutil.which("git")
RETURN_POLICY = (
    "fast-forward only for a clean source and committed candidate with no tracked "
    "changes, when every history path is kept and its only untracked files are "
    "reviewed excluded .shiploop-improve evidence; otherwise apply only the "
    "reviewed working-tree delta without a merge or commit"
)
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_store as store  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402


class ShipLoopWorkspaceTests(unittest.TestCase):
    """Exercise the helper against disposable real repositories only."""

    def setUp(self) -> None:
        if GIT is None:
            self.fail("Git must be available on PATH for real workspace coverage")
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-workspace-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "source repository with spaces"
        self.repo.mkdir()
        self.env = {
            **os.environ,
            "PATH": os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        self.git("init", "-q")
        self.git("branch", "-M", "main")
        self.git("config", "user.name", "ShipLoop Workspace Test")
        self.git("config", "user.email", "shiploop-workspace@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", os.devnull)
        self._write_initial_tree()

    def git(
        self,
        *args: str,
        cwd: Path | None = None,
        code: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [str(GIT), "-C", str(cwd or self.repo), *args],
            text=True,
            capture_output=True,
            timeout=30,
            env=self.env,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def cli(self, *args: str, code: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, "-B", str(CLI), *args],
            cwd=self.base,
            text=True,
            capture_output=True,
            timeout=30,
            env=self.env,
        )
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def _call(self, function, *args, **kwargs):
        """Give helper-owned subprocesses the test's selected Git environment."""
        with mock.patch.dict(os.environ, self.env, clear=False):
            return function(*args, **kwargs)

    def _write(self, relative: str, content: str | bytes) -> Path:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def _write_initial_tree(self) -> None:
        self._write("tracked-staged.txt", "base staged\n")
        self._write("tracked-unstaged.txt", "base unstaged\n")
        self._write("delete-me.txt", "delete from candidate\n")
        self._write("rename-from.txt", "rename from candidate\n")
        mode = self._write("mode.sh", "#!/bin/sh\necho base\n")
        mode.chmod(0o644)
        self._write("binary.bin", b"\x00baseline\xff\x10")
        self._write("target.txt", "symlink target\n")
        self._write(
            ".gitignore",
            "*.secret\ncredentials/\nsecret.dat\n",
        )
        self._write("SHIPLOOP.md", "# Project knowledge\n\nBaseline decision.\n")
        self._write("environment.md", "# Environment\n\nBaseline environment.\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "baseline")

    def _seed_dirty_source(self) -> None:
        """Use distinct staged and unstaged paths so both layers are observable."""
        self._write("tracked-staged.txt", "captured staged input\n")
        self.git("add", "tracked-staged.txt")
        self._write("tracked-unstaged.txt", "captured unstaged input\n")
        self._write("selected-input.txt", "selected untracked input\n")
        self._write("not-selected.txt", "unselected input must not travel\n")
        self._write("credentials/token.secret", "not a test credential\n")

    @staticmethod
    def _file_tree(root: Path) -> dict[str, tuple[object, ...]]:
        """Return product files, modes, and link targets without following links."""
        entries: dict[str, tuple[object, ...]] = {}
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if ".git" in relative.parts:
                continue
            if path.is_symlink():
                entries[relative.as_posix()] = ("symlink", os.readlink(path))
            elif path.is_file():
                entries[relative.as_posix()] = (
                    "file",
                    stat.S_IMODE(path.stat().st_mode),
                    path.read_bytes(),
                )
        return entries

    def _source_snapshot(self) -> dict[str, object]:
        """Capture every source property a helper must never repair or rewrite."""
        index = self.repo / ".git" / "index"
        return {
            "head": self.git("rev-parse", "HEAD").stdout.strip(),
            "branch": self.git("symbolic-ref", "--short", "HEAD").stdout.strip(),
            "index": index.read_bytes(),
            "cached": self.git("diff", "--cached", "--binary").stdout,
            "unstaged": self.git("diff", "--binary").stdout,
            "status": self.git(
                "status", "--porcelain=v1", "--untracked-files=all"
            ).stdout,
            "tree": self._file_tree(self.repo),
        }

    def _assert_source_unchanged(self, before: dict[str, object]) -> None:
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), before["head"])
        self.assertEqual(
            self.git("symbolic-ref", "--short", "HEAD").stdout.strip(),
            before["branch"],
        )
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), before["index"])
        self.assertEqual(
            self.git("diff", "--cached", "--binary").stdout, before["cached"]
        )
        self.assertEqual(self.git("diff", "--binary").stdout, before["unstaged"])
        self.assertEqual(
            self.git("status", "--porcelain=v1", "--untracked-files=all").stdout,
            before["status"],
        )
        self.assertEqual(self._file_tree(self.repo), before["tree"])

    @staticmethod
    def _workspace_snapshot(root: Path) -> dict[str, tuple[object, ...]]:
        if not root.exists():
            return {}
        return ShipLoopWorkspaceTests._file_tree(root)

    def _common_object_snapshot(self) -> dict[str, tuple[object, ...]]:
        common = Path(
            self.git(
                "rev-parse", "--path-format=absolute", "--git-common-dir"
            ).stdout.strip()
        )
        return self._file_tree(common / "objects")

    def _prepare(
        self,
        *,
        include_untracked: tuple[str, ...] = (),
        exclude: tuple[str, ...] = (),
        name: str = "isolated workspace",
    ) -> dict:
        root = self.base / name
        record = self._call(
            workspace.prepare,
            self.repo,
            root,
            include_untracked=include_untracked,
            exclude=exclude,
        )
        self.assertEqual(record["schema"], "shiploop-workspace")
        self.assertEqual(record["version"], 1)
        self.assertEqual(record["status"], "prepared")
        self.assertEqual(Path(record["source_repo"]), self.repo.resolve())
        self.assertTrue((root / "workspace.md").is_file())
        self.assertEqual(store.read_record(root / "workspace.md"), record)
        self.assertTrue((root / "run").is_dir())
        self.assertTrue((root / "worktree").is_dir())
        self.assertEqual(Path(record["worktree"]), (root / "worktree").resolve())
        self.assertEqual(Path(record["run_dir"]), (root / "run").resolve())
        return record

    def _worktree(self, record: dict) -> Path:
        path = Path(record["worktree"])
        self.assertTrue(path.is_dir(), path)
        return path

    def _commit_all(self, worktree: Path, message: str) -> str:
        self.git("add", "-A", cwd=worktree)
        self.git("commit", "-qm", message, cwd=worktree)
        return self.git("rev-parse", "HEAD", cwd=worktree).stdout.strip()

    def _force_add_ignored_candidate(self, worktree: Path, content: str) -> None:
        """Make a candidate track a path that the source intentionally ignores."""
        (worktree / "secret.dat").write_text(content, encoding="utf-8")
        self.git("add", "-f", "secret.dat", cwd=worktree)
        self.git("commit", "-qm", "candidate tracks ignored collision", cwd=worktree)

    def _plan(self, root: Path) -> dict:
        record = self._call(workspace.plan_return, root)
        self.assertEqual(record["schema"], "shiploop-workspace-return-plan")
        self.assertEqual(record["version"], 1)
        self.assertEqual(record["status"], "pending")
        self.assertEqual(record["return_policy"], RETURN_POLICY)
        self.assertEqual(store.read_record(root / "return-plan.md"), record)
        return record

    def _resolve_plan(
        self,
        root: Path,
        *,
        keep: set[str] | None = None,
        exclude: set[str] | None = None,
    ) -> dict:
        """Make the host's only mutable decision explicit in Markdown."""
        keep = set() if keep is None else set(keep)
        exclude = set() if exclude is None else set(exclude)
        plan = store.read_record(root / "return-plan.md")
        for item in plan["paths"]:
            path = item["path"]
            if path in exclude:
                item["disposition"] = "exclude"
            elif keep:
                item["disposition"] = "keep" if path in keep else "exclude"
            elif item["disposition"] != "exclude":
                item["disposition"] = "keep"
        store.write_record(root / "return-plan.md", plan, "ShipLoop workspace return plan")
        return plan

    def _execute(self, root: Path) -> dict:
        receipt = self._call(workspace.execute_return, root)
        self.assertEqual(receipt["schema"], "shiploop-workspace-return-receipt")
        self.assertEqual(receipt["version"], 1)
        self.assertEqual(receipt["status"], "returned")
        self.assertEqual(store.read_record(root / "return-receipt.md"), receipt)
        return receipt

    def test_prepare_replays_selected_dirty_inputs_without_touching_source_index(self) -> None:
        self._seed_dirty_source()
        before = self._source_snapshot()

        record = self._prepare(include_untracked=("selected-input.txt",))
        worktree = self._worktree(record)

        self.assertEqual(
            (worktree / "tracked-staged.txt").read_text(encoding="utf-8"),
            "captured staged input\n",
        )
        self.assertEqual(
            (worktree / "tracked-unstaged.txt").read_text(encoding="utf-8"),
            "captured unstaged input\n",
        )
        self.assertEqual(
            (worktree / "selected-input.txt").read_text(encoding="utf-8"),
            "selected untracked input\n",
        )
        self.assertFalse((worktree / "not-selected.txt").exists())
        self.assertFalse((worktree / "credentials" / "token.secret").exists())
        self.assertEqual(record["selected_untracked"], ["selected-input.txt"])
        self._assert_source_unchanged(before)

    def test_prepare_uses_actual_working_content_for_staged_new_edit_and_delete(self) -> None:
        """The private baseline follows current files, not only the source index."""
        self._write("staged-new-edit.txt", "indexed new content\n")
        self.git("add", "staged-new-edit.txt")
        self._write("staged-new-edit.txt", "working new content\n")
        self._write("staged-new-delete.txt", "indexed then removed\n")
        self.git("add", "staged-new-delete.txt")
        (self.repo / "staged-new-delete.txt").unlink()
        before = self._source_snapshot()

        record = self._prepare(name="staged new working baseline")
        worktree = self._worktree(record)

        self.assertEqual(
            (worktree / "staged-new-edit.txt").read_text(encoding="utf-8"),
            "working new content\n",
        )
        self.assertFalse((worktree / "staged-new-delete.txt").exists())
        self._assert_source_unchanged(before)

    def test_prepare_accepts_an_empty_initial_commit_without_a_readme(self) -> None:
        """A new repository needs no bootstrap file before workspace capture."""
        empty_repo = self.base / "empty initial source"
        empty_repo.mkdir()
        self.git("init", "-q", cwd=empty_repo)
        self.git("branch", "-M", "main", cwd=empty_repo)
        self.git("config", "user.name", "ShipLoop Workspace Test", cwd=empty_repo)
        self.git("config", "user.email", "shiploop-workspace@example.invalid", cwd=empty_repo)
        self.git("config", "commit.gpgsign", "false", cwd=empty_repo)
        self.git("config", "core.hooksPath", os.devnull, cwd=empty_repo)
        self.git("commit", "--allow-empty", "-qm", "initial", cwd=empty_repo)
        source_index = (empty_repo / ".git" / "index").read_bytes()
        source_head = self.git("rev-parse", "HEAD", cwd=empty_repo).stdout.strip()
        root = self.base / "empty initial workspace"

        record = self._call(workspace.prepare, empty_repo, root)
        worktree = Path(record["worktree"])

        self.assertEqual(record["source_head"], source_head)
        self.assertEqual(record["baseline_tree"], self.git(
            "rev-parse", "HEAD^{tree}", cwd=empty_repo
        ).stdout.strip())
        self.assertTrue(record["start_clean"])
        self.assertFalse((empty_repo / "README.md").exists())
        self.assertFalse((worktree / "README.md").exists())
        self.assertEqual(self._file_tree(worktree), {})
        self.assertEqual((empty_repo / ".git" / "index").read_bytes(), source_index)
        self.assertEqual(self.git("rev-parse", "HEAD", cwd=empty_repo).stdout.strip(), source_head)
        self.assertEqual(
            self.git("status", "--porcelain=v1", "--untracked-files=all", cwd=empty_repo).stdout,
            "",
        )

    def test_prepare_sanitizes_ambient_git_redirection_and_disables_checkout_hooks(self) -> None:
        """A caller environment or repository hook cannot redirect workspace capture."""
        hooks = self.base / "hostile hooks"
        hooks.mkdir()
        sentinel = self.base / "hook ran"
        hook = hooks / "post-checkout"
        hook.write_text(
            "#!/bin/sh\nprintf hook-ran > \"$SHIPLOOP_WORKSPACE_HOOK_SENTINEL\"\n",
            encoding="utf-8",
        )
        hook.chmod(0o755)
        self.git("config", "core.hooksPath", str(hooks))
        foreign = self.base / "foreign git directory"
        foreign.mkdir()
        subprocess.run(
            [str(GIT), "init", "-q", str(foreign)],
            check=True,
            text=True,
            capture_output=True,
            env=self.env,
        )
        before = self._source_snapshot()
        root = self.base / "sanitized environment"
        hostile = {
            "GIT_DIR": str(foreign / ".git"),
            "GIT_WORK_TREE": str(foreign),
            "GIT_INDEX_FILE": str(foreign / "foreign.index"),
            "SHIPLOOP_WORKSPACE_HOOK_SENTINEL": str(sentinel),
        }

        with mock.patch.dict(os.environ, {**self.env, **hostile}, clear=False):
            record = workspace.prepare(self.repo, root)

        self.assertEqual(Path(record["source_repo"]), self.repo.resolve())
        self.assertFalse(sentinel.exists(), "ShipLoop Git subprocess must not run repo hooks")
        self._assert_source_unchanged(before)

    def test_prepare_rejects_a_transient_source_artifact_without_mutation(self) -> None:
        self._seed_dirty_source()
        transient = self.repo / ".shiploop" / "run-state.md"
        transient.parent.mkdir()
        transient.write_text("transient\n", encoding="utf-8")
        before = self._source_snapshot()
        root = self.base / "rejected transient source"

        with self.assertRaises(workspace.WorkspaceError):
            self._call(workspace.prepare, self.repo, root)

        self._assert_source_unchanged(before)
        self.assertFalse((root / "workspace.md").exists())

    def test_prepare_rejects_until_loop_runtime_artifacts_without_mutation(self) -> None:
        """Actual Improve runtime state is evidence, never candidate product input."""
        self._seed_dirty_source()
        runtime = self.repo / ".until-loop" / "working.md"
        runtime.parent.mkdir()
        runtime.write_text("runtime evidence only\n", encoding="utf-8")
        before = self._source_snapshot()
        root = self.base / "rejected until-loop runtime source"

        with self.assertRaises(workspace.WorkspaceError):
            self._call(workspace.prepare, self.repo, root)

        self._assert_source_unchanged(before)
        self.assertFalse((root / "workspace.md").exists())

    def test_prepare_refuses_a_staged_runtime_deletion_without_repairing_user_work(self) -> None:
        """A removed old run file is still an unsafe tracked baseline, not cleanup."""
        runtime = self.repo / ".shiploop" / "old-run.md"
        runtime.parent.mkdir()
        runtime.write_text("historical runtime artifact\n", encoding="utf-8")
        self.git("add", ".shiploop/old-run.md")
        self.git("commit", "-qm", "historic runtime artifact")
        self.git("rm", ".shiploop/old-run.md")
        before = self._source_snapshot()
        root = self.base / "staged runtime deletion"

        with self.assertRaises(workspace.WorkspaceError):
            self._call(workspace.prepare, self.repo, root)

        self._assert_source_unchanged(before)
        self.assertFalse((root / "workspace.md").exists())

    def test_prepare_rejects_ephemeral_child_receipts_without_mutation(self) -> None:
        """Saved terminal packets are parent evidence, never product baseline input."""
        self._seed_dirty_source()
        receipt = self.repo / ".shiploop-improve" / "parent-run" / "A-INTAKE-001" / "packet.json"
        receipt.parent.mkdir(parents=True)
        receipt.write_text('{"status":"complete"}\n', encoding="utf-8")
        before = self._source_snapshot()
        root = self.base / "rejected ephemeral receipt source"

        with self.assertRaises(workspace.WorkspaceError):
            self._call(workspace.prepare, self.repo, root)

        self._assert_source_unchanged(before)
        self.assertFalse((root / "workspace.md").exists())

    def test_runtime_artifact_removed_before_the_baseline_does_not_block_or_reappear(self) -> None:
        """Do not treat unrelated pre-baseline history as current candidate work."""
        runtime = self.repo / ".shiploop" / "historic.md"
        runtime.parent.mkdir()
        runtime.write_text("old removed run artifact\n", encoding="utf-8")
        self.git("add", ".shiploop/historic.md")
        self.git("commit", "-qm", "historic run artifact")
        self.git("rm", ".shiploop/historic.md")
        self.git("commit", "-qm", "remove historic run artifact")
        before = self._source_snapshot()

        record = self._prepare(name="post-historic-artifact")

        self._assert_source_unchanged(before)
        self.assertFalse((self._worktree(record) / ".shiploop" / "historic.md").exists())

    def test_dirty_return_applies_only_new_delta_and_preserves_source_index(self) -> None:
        self._seed_dirty_source()
        deleted = self.repo / "delete-me.txt"
        deleted.unlink()
        self.git("add", "-u", "delete-me.txt")
        deleted.write_text("recreated source input\n", encoding="utf-8")
        record = self._prepare(include_untracked=("selected-input.txt",))
        root = self.base / "isolated workspace"
        worktree = self._worktree(record)
        feature = worktree / "feature.py"
        feature.write_text("def feature():\n    return 'candidate'\n", encoding="utf-8")
        self._commit_all(worktree, "add candidate feature")
        # A receipt records actual working content, including an unstaged
        # candidate edit whose review disposition can still be exclude.
        (worktree / "tracked-unstaged.txt").write_text(
            "candidate unstaged tracked input\n", encoding="utf-8"
        )

        plan = self._plan(root)
        planned = {item["path"] for item in plan["paths"]}
        self.assertIn("feature.py", planned)
        self.assertIn("tracked-unstaged.txt", planned)
        self.assertNotIn("tracked-staged.txt", planned)
        self.assertNotIn("selected-input.txt", planned)
        self._resolve_plan(root, exclude={"tracked-unstaged.txt"})
        before_head = self.git("rev-parse", "HEAD").stdout.strip()
        before_index = (self.repo / ".git" / "index").read_bytes()
        before_dirty = {
            name: (self.repo / name).read_bytes()
            for name in (
                "tracked-staged.txt",
                "tracked-unstaged.txt",
                "selected-input.txt",
                "delete-me.txt",
            )
        }

        receipt = self._execute(root)

        self.assertEqual(receipt["kind"], "working-tree-return")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), before_head)
        self.assertEqual((self.repo / "feature.py").read_text(encoding="utf-8"), feature.read_text(encoding="utf-8"))
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), before_index)
        self.assertEqual(
            {name: (self.repo / name).read_bytes() for name in before_dirty}, before_dirty
        )
        self.assertNotEqual(
            self.git("ls-files", "--error-unmatch", "feature.py", code=1).returncode,
            0,
        )
        self.assertTrue((root / "worktree").is_dir())
        self.assertTrue((root / "run").is_dir())

        workspace_before = self._workspace_snapshot(root)
        source_index_before = (self.repo / ".git" / "index").read_bytes()
        objects_before = self._common_object_snapshot()
        self.assertEqual(
            self._call(workspace.completed_receipt_snapshot, root, self.repo), receipt
        )
        self.assertEqual(self._workspace_snapshot(root), workspace_before)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), source_index_before)
        self.assertEqual(self._common_object_snapshot(), objects_before)

        (self.repo / "feature.py").write_text(
            "source novel working-tree return blob\n", encoding="utf-8"
        )
        drift_workspace = self._workspace_snapshot(root)
        drift_index = (self.repo / ".git" / "index").read_bytes()
        drift_objects = self._common_object_snapshot()
        self.assertIsNone(
            self._call(workspace.completed_receipt_snapshot, root, self.repo)
        )
        self.assertEqual(self._workspace_snapshot(root), drift_workspace)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), drift_index)
        self.assertEqual(self._common_object_snapshot(), drift_objects)

    def test_receipt_snapshot_honors_disabled_filemode_for_executable_extras(self) -> None:
        """The display match follows Git mode policy for selected and returned files."""
        self.git("config", "core.filemode", "false")
        selected = self._write("selected-executable.sh", "#!/bin/sh\necho selected\n")
        selected.chmod(0o755)
        root = self.base / "filemode disabled return"
        record = self._prepare(
            include_untracked=("selected-executable.sh",), name=root.name
        )
        worktree = self._worktree(record)
        returned = worktree / "returned-executable.sh"
        returned.write_text("#!/bin/sh\necho returned\n", encoding="utf-8")
        self._commit_all(worktree, "return executable source extra")
        self._plan(root)
        self._resolve_plan(root)
        receipt = self._execute(root)
        self.assertEqual(receipt["kind"], "working-tree-return")

        returned_source = self.repo / "returned-executable.sh"
        returned_source.chmod(0o755)
        self.assertTrue(selected.stat().st_mode & stat.S_IXUSR)
        self.assertTrue(returned_source.stat().st_mode & stat.S_IXUSR)
        expected_tree = receipt["expected_source"]["working_tree"]
        for path in ("selected-executable.sh", "returned-executable.sh"):
            self.assertTrue(
                self.git("ls-tree", expected_tree, "--", path).stdout.startswith(
                    "100644 blob "
                )
            )

        workspace_before = self._workspace_snapshot(root)
        index_before = (self.repo / ".git" / "index").read_bytes()
        objects_before = self._common_object_snapshot()
        self.assertEqual(
            self._call(workspace.completed_receipt_snapshot, root, self.repo), receipt
        )
        self.assertEqual(self._workspace_snapshot(root), workspace_before)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), index_before)
        self.assertEqual(self._common_object_snapshot(), objects_before)

        self.git("config", "core.filemode", "true")
        drift_workspace = self._workspace_snapshot(root)
        drift_index = (self.repo / ".git" / "index").read_bytes()
        drift_objects = self._common_object_snapshot()
        self.assertIsNone(
            self._call(workspace.completed_receipt_snapshot, root, self.repo)
        )
        self.assertEqual(self._workspace_snapshot(root), drift_workspace)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), drift_index)
        self.assertEqual(self._common_object_snapshot(), drift_objects)

    def test_clean_candidate_fast_forwards_when_every_path_is_kept(self) -> None:
        record = self._prepare(name="clean fast forward")
        root = self.base / "clean fast forward"
        worktree = self._worktree(record)
        (worktree / "fast-forward.txt").write_text("safe candidate\n", encoding="utf-8")
        self._commit_all(worktree, "add fast forward candidate")
        (worktree / "durable-notes.md").write_text("second durable commit\n", encoding="utf-8")
        candidate = self._commit_all(worktree, "add second durable candidate commit")
        self._plan(root)
        self._resolve_plan(root)

        receipt = self._execute(root)

        self.assertEqual(receipt["kind"], "fast-forward-merge")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), candidate)
        self.assertEqual((self.repo / "fast-forward.txt").read_text(encoding="utf-8"), "safe candidate\n")
        self.assertEqual((self.repo / "durable-notes.md").read_text(encoding="utf-8"), "second durable commit\n")
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        self.assertTrue((root / "worktree").is_dir())
        self.assertTrue((root / "run").is_dir())

    def test_ordinary_untracked_output_prevents_committed_candidate_fast_forward(self) -> None:
        root = self.base / "ordinary untracked output"
        worktree = self._worktree(self._prepare(name=root.name))
        (worktree / "product-output.txt").write_text("reviewed product\n", encoding="utf-8")
        self.git("add", "product-output.txt", cwd=worktree)
        self.git("commit", "-qm", "commit reviewed product", cwd=worktree)
        (worktree / "worker.log").write_text("private scratch\n", encoding="utf-8")
        self._plan(root)
        self._resolve_plan(root, exclude={"worker.log"})
        before_head = self.git("rev-parse", "HEAD").stdout.strip()
        before_index = (self.repo / ".git" / "index").read_bytes()

        receipt = self._execute(root)

        self.assertEqual(receipt["kind"], "working-tree-return")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), before_head)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), before_index)
        self.assertEqual((self.repo / "product-output.txt").read_text(), "reviewed product\n")
        self.assertFalse((self.repo / "worker.log").exists())
        self.assertTrue((worktree / "worker.log").is_file())

    def test_clean_fast_forward_refuses_to_overwrite_an_ignored_source_sentinel(self) -> None:
        """`merge --ff-only` must not silently replace ignored untracked data."""
        (self.repo / "secret.dat").write_text("source sentinel\n", encoding="utf-8")
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        root = self.base / "clean ignored collision"
        record = self._prepare(name="clean ignored collision")
        worktree = self._worktree(record)
        self.assertFalse((worktree / "secret.dat").exists())
        self._force_add_ignored_candidate(worktree, "candidate replacement\n")
        self._plan(root)
        self._resolve_plan(root)
        source_before = self._source_snapshot()

        with self.assertRaises(workspace.WorkspaceError):
            self._call(workspace.execute_return, root)

        self._assert_source_unchanged(source_before)
        self.assertEqual((self.repo / "secret.dat").read_text(encoding="utf-8"), "source sentinel\n")

    def test_no_product_delta_returns_an_explicit_no_change_receipt(self) -> None:
        """Empty reviewed output is not a fake merge, commit, or empty apply."""
        clean_root = self.base / "clean no product delta"
        self._prepare(name="clean no product delta")
        self._plan(clean_root)
        self._resolve_plan(clean_root)
        clean_before = self._source_snapshot()

        clean_receipt = self._execute(clean_root)

        self.assertEqual(clean_receipt["kind"], "no-change-return")
        self._assert_source_unchanged(clean_before)
        self.assertTrue((clean_root / "worktree").is_dir())
        self.assertTrue((clean_root / "run").is_dir())

        self._seed_dirty_source()
        dirty_root = self.base / "dirty all output excluded"
        record = self._prepare(
            include_untracked=("selected-input.txt",),
            exclude=("transient-output.html",),
            name="dirty all output excluded",
        )
        worktree = self._worktree(record)
        (worktree / "transient-output.html").write_text(
            "intentionally omitted output\n", encoding="utf-8"
        )
        self._commit_all(worktree, "candidate output deliberately omitted")
        self._plan(dirty_root)
        self._resolve_plan(dirty_root)
        dirty_before = self._source_snapshot()

        dirty_receipt = self._execute(dirty_root)

        self.assertEqual(dirty_receipt["kind"], "no-change-return")
        self._assert_source_unchanged(dirty_before)
        self.assertFalse((self.repo / "transient-output.html").exists())
        self.assertTrue((dirty_root / "worktree").is_dir())
        self.assertTrue((dirty_root / "run").is_dir())

    def test_dirty_return_refuses_to_overwrite_an_ignored_source_sentinel(self) -> None:
        """The reviewed patch route has the same ignored-file safety boundary."""
        self._seed_dirty_source()
        (self.repo / "secret.dat").write_text("source sentinel\n", encoding="utf-8")
        root = self.base / "dirty ignored collision"
        record = self._prepare(
            include_untracked=("selected-input.txt",), name="dirty ignored collision"
        )
        worktree = self._worktree(record)
        self.assertFalse((worktree / "secret.dat").exists())
        self._force_add_ignored_candidate(worktree, "candidate replacement\n")
        self._plan(root)
        self._resolve_plan(root)
        source_before = self._source_snapshot()

        with self.assertRaises(workspace.WorkspaceError):
            self._call(workspace.execute_return, root)

        self._assert_source_unchanged(source_before)
        self.assertEqual((self.repo / "secret.dat").read_text(encoding="utf-8"), "source sentinel\n")

    def test_explicitly_omitted_output_never_returns_but_durable_documents_do(self) -> None:
        root = self.base / "filtered return"
        record = self._prepare(
            name="filtered return",
            exclude=("reports/transient-output.html",),
        )
        worktree = self._worktree(record)
        (worktree / "SHIPLOOP.md").write_text(
            "# Project knowledge\n\nDurable updated decision.\n", encoding="utf-8"
        )
        (worktree / "environment.md").write_text(
            "# Environment\n\nDurable updated environment.\n", encoding="utf-8"
        )
        requirements = worktree / "docs" / "requirements.md"
        requirements.parent.mkdir()
        requirements.write_text(
            "# Requirements\n\nCancel leaves the note and list unchanged.\n",
            encoding="utf-8",
        )
        output = worktree / "reports" / "transient-output.html"
        output.parent.mkdir()
        output.write_text("<p>run-local output</p>\n", encoding="utf-8")
        self._commit_all(worktree, "update knowledge and generate output")

        plan = self._plan(root)
        items = {item["path"]: item for item in plan["paths"]}
        self.assertEqual(items["reports/transient-output.html"]["disposition"], "exclude")
        self.assertEqual(items["SHIPLOOP.md"]["disposition"], "pending")
        self.assertEqual(items["environment.md"]["disposition"], "pending")
        self.assertEqual(items["docs/requirements.md"]["disposition"], "pending")
        self._resolve_plan(
            root,
            keep={"SHIPLOOP.md", "environment.md", "docs/requirements.md"},
            exclude={"reports/transient-output.html"},
        )
        source_head = self.git("rev-parse", "HEAD").stdout.strip()
        source_index = (self.repo / ".git" / "index").read_bytes()

        receipt = self._execute(root)

        self.assertEqual(receipt["kind"], "working-tree-return")
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), source_head)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), source_index)
        self.assertIn("Durable updated decision", (self.repo / "SHIPLOOP.md").read_text(encoding="utf-8"))
        self.assertIn("Durable updated environment", (self.repo / "environment.md").read_text(encoding="utf-8"))
        self.assertEqual(
            (self.repo / "docs" / "requirements.md").read_bytes(), requirements.read_bytes()
        )
        self.assertFalse((self.repo / "reports" / "transient-output.html").exists())

        # A newly returned document is untracked until an authorized commit.
        # The next isolated run explicitly includes it, per the knowledge policy.
        next_record = self._prepare(
            name="next feature with retained requirements",
            include_untracked=("docs/requirements.md",),
        )
        next_worktree = self._worktree(next_record)
        self.assertEqual(
            (next_worktree / "docs" / "requirements.md").read_bytes(),
            requirements.read_bytes(),
        )
        self.assertFalse((next_worktree / "reports" / "transient-output.html").exists())

    def test_dirty_return_preserves_binary_delete_rename_mode_and_symlink_changes(self) -> None:
        self._seed_dirty_source()
        root = self.base / "special delta"
        record = self._prepare(
            include_untracked=("selected-input.txt",), name="special delta"
        )
        worktree = self._worktree(record)
        (worktree / "binary.bin").write_bytes(b"\x00candidate\xfe\x01\xff")
        (worktree / "delete-me.txt").unlink()
        self.git("rm", "delete-me.txt", cwd=worktree)
        self.git("mv", "rename-from.txt", "renamed.txt", cwd=worktree)
        mode = worktree / "mode.sh"
        mode.chmod(0o755)

        link = worktree / "candidate-link"
        try:
            os.symlink("target.txt", link)
        except (NotImplementedError, OSError):
            link = None

        self._commit_all(worktree, "exercise special candidate changes")
        self._plan(root)
        self._resolve_plan(root)
        source_index = (self.repo / ".git" / "index").read_bytes()

        receipt = self._execute(root)

        self.assertEqual(receipt["kind"], "working-tree-return")
        self.assertEqual((self.repo / "binary.bin").read_bytes(), b"\x00candidate\xfe\x01\xff")
        self.assertFalse((self.repo / "delete-me.txt").exists())
        self.assertFalse((self.repo / "rename-from.txt").exists())
        self.assertEqual((self.repo / "renamed.txt").read_text(encoding="utf-8"), "rename from candidate\n")
        self.assertTrue((self.repo / "mode.sh").stat().st_mode & stat.S_IXUSR)
        if link is not None:
            returned = self.repo / "candidate-link"
            self.assertTrue(returned.is_symlink())
            self.assertEqual(os.readlink(returned), "target.txt")
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), source_index)

    def test_retained_child_evidence_keeps_uncommitted_and_committed_returns_distinct(self) -> None:
        for committed in (True, False):
            with self.subTest(committed=committed):
                root = self.base / ("retained committed child evidence" if committed else "retained child evidence")
                worktree = self._worktree(self._prepare(name=root.name))
                child_receipt = worktree / ".shiploop-improve" / "run" / "action" / "packet.json"
                child_receipt.parent.mkdir(parents=True)
                child_receipt.write_text('{"status":"complete"}\n', encoding="utf-8")
                review = child_receipt.parent / "reviews" / "review-one.md"
                review.parent.mkdir()
                review.write_text("retained child review evidence\n", encoding="utf-8")
                notebook = child_receipt.parent.parent / "planning-investigation.md"
                notebook.write_text("original allowance; retained observations\n", encoding="utf-8")
                prototype = child_receipt.parent / "probe.py"
                prototype.write_text("print(\"scratch experiment\")\n", encoding="utf-8")
                product = "committed-product-output.txt" if committed else "product-output.txt"
                (worktree / product).write_text("reviewed product\n", encoding="utf-8")
                candidate = None
                if committed:
                    self.git("add", product, cwd=worktree)
                    self.git("commit", "-qm", "commit reviewed product", cwd=worktree)
                    candidate = self.git("rev-parse", "HEAD", cwd=worktree).stdout.strip()
                plan = self._plan(root)
                for row in plan["paths"]:
                    row["disposition"] = "keep"
                store.write_record(root / "return-plan.md", plan)
                before = self._source_snapshot()
                with self.assertRaises(workspace.WorkspaceError):
                    self._call(workspace.execute_return, root)
                self._assert_source_unchanged(before)

                for row in plan["paths"]:
                    if row["path"].startswith(".shiploop-improve/"):
                        row["disposition"] = "exclude"
                store.write_record(root / "return-plan.md", plan)
                receipt = self._execute(root)
                self.assertEqual(
                    receipt["kind"], "fast-forward-merge" if committed else "working-tree-return"
                )
                if candidate is not None:
                    self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), candidate)
                self.assertEqual((self.repo / product).read_text(), "reviewed product\n")
                self.assertFalse((self.repo / ".shiploop-improve").exists())
                self.assertTrue(child_receipt.is_file())
                self.assertTrue(review.is_file())
                self.assertTrue(notebook.is_file())
                self.assertTrue(prototype.is_file())

    def test_tracked_or_historical_child_receipts_still_block_return(self) -> None:
        for kind in ("staged", "committed", "deleted-in-history"):
            with self.subTest(kind=kind):
                root = self.base / ("tracked child " + kind)
                worktree = self._worktree(self._prepare(name=root.name))
                receipt = worktree / ".shiploop-improve" / "run" / "action" / "packet.json"
                receipt.parent.mkdir(parents=True)
                receipt.write_text("private child evidence\n", encoding="utf-8")
                self.git("add", ".shiploop-improve", cwd=worktree)
                if kind != "staged":
                    self._commit_all(worktree, "accidentally commit runtime evidence")
                if kind == "deleted-in-history":
                    self.git("rm", str(receipt.relative_to(worktree)), cwd=worktree)
                    self._commit_all(worktree, "delete runtime evidence")
                before = self._source_snapshot()
                self._plan(root)
                self._resolve_plan(root)
                with self.assertRaises(workspace.WorkspaceError):
                    self._call(workspace.execute_return, root)
                self._assert_source_unchanged(before)
                self.assertFalse((root / "return-receipt.md").exists())

    def test_transient_candidate_and_transient_history_are_never_returnable(self) -> None:
        root = self.base / "forbidden candidate"
        record = self._prepare(name="forbidden candidate")
        worktree = self._worktree(record)
        transient = worktree / ".shiploop" / "run-state.md"
        transient.parent.mkdir()
        transient.write_text("transient candidate state\n", encoding="utf-8")
        self._commit_all(worktree, "add transient state")
        source_before = self._source_snapshot()
        before_plan = self._workspace_snapshot(root)

        try:
            plan = self._plan(root)
        except workspace.WorkspaceError:
            plan = None
            self.assertEqual(self._workspace_snapshot(root), before_plan)
        if plan is not None:
            self.assertIn(
                ".shiploop/run-state.md", {item["path"] for item in plan["paths"]}
            )
            self._resolve_plan(root)
            workspace_before = self._workspace_snapshot(root)
            with self.assertRaises(workspace.WorkspaceError):
                self._call(workspace.execute_return, root)
            self.assertEqual(self._workspace_snapshot(root), workspace_before)
        self._assert_source_unchanged(source_before)
        self.assertFalse((root / "return-receipt.md").exists())

        # A deleted transient file is still reachable in the candidate history.
        # Returning the final tree by fast-forward would silently retain that
        # unwanted historical artifact, so safety must win at plan or return.
        history_root = self.base / "forbidden history"
        record = self._prepare(name="forbidden history")
        worktree = self._worktree(record)
        transient = worktree / ".shiploop" / "temporary.md"
        transient.parent.mkdir()
        transient.write_text("must never enter source history\n", encoding="utf-8")
        self._commit_all(worktree, "add transient then delete it")
        transient.unlink()
        self.git("rm", ".shiploop/temporary.md", cwd=worktree)
        self._commit_all(worktree, "delete transient before return")
        source_before = self._source_snapshot()

        try:
            plan = self._plan(history_root)
        except workspace.WorkspaceError:
            plan = None
        if plan is not None:
            self._resolve_plan(history_root)
            workspace_before = self._workspace_snapshot(history_root)
            with self.assertRaises(workspace.WorkspaceError):
                self._call(workspace.execute_return, history_root)
            self.assertEqual(self._workspace_snapshot(history_root), workspace_before)
        self._assert_source_unchanged(source_before)
        self.assertFalse((history_root / "return-receipt.md").exists())

    def test_source_content_index_and_branch_drift_refuse_without_repairing_source(self) -> None:
        scenarios = ("content", "index", "branch")
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                # Use an independent repository per mutation so a rejected run
                # cannot conceal subsequent drift under a changed fingerprint.
                with tempfile.TemporaryDirectory(prefix="shiploop-workspace-drift-") as temp:
                    root_base = Path(temp)
                    repo = root_base / "repo"
                    subprocess.run(
                        [str(GIT), "init", "-q", str(repo)],
                        check=True,
                        text=True,
                        capture_output=True,
                        env=self.env,
                    )
                    subprocess.run(
                        [str(GIT), "-C", str(repo), "branch", "-M", "main"],
                        check=True,
                        text=True,
                        capture_output=True,
                        env=self.env,
                    )
                    for key, value in (
                        ("user.name", "ShipLoop Workspace Drift Test"),
                        ("user.email", "shiploop-workspace-drift@example.invalid"),
                        ("commit.gpgsign", "false"),
                        ("core.hooksPath", os.devnull),
                    ):
                        subprocess.run(
                            [str(GIT), "-C", str(repo), "config", key, value],
                            check=True,
                            text=True,
                            capture_output=True,
                            env=self.env,
                        )
                    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
                    subprocess.run(
                        [str(GIT), "-C", str(repo), "add", "tracked.txt"],
                        check=True,
                        text=True,
                        capture_output=True,
                        env=self.env,
                    )
                    subprocess.run(
                        [str(GIT), "-C", str(repo), "commit", "-qm", "base"],
                        check=True,
                        text=True,
                        capture_output=True,
                        env=self.env,
                    )
                    root = root_base / "workspace"
                    with mock.patch.dict(os.environ, self.env, clear=False):
                        record = workspace.prepare(repo, root)
                    if scenario == "content":
                        (repo / "tracked.txt").write_text("late working edit\n", encoding="utf-8")
                    elif scenario == "index":
                        (repo / "tracked.txt").write_text("late indexed edit\n", encoding="utf-8")
                        subprocess.run(
                            [str(GIT), "-C", str(repo), "add", "tracked.txt"],
                            check=True,
                            text=True,
                            capture_output=True,
                            env=self.env,
                        )
                    else:
                        subprocess.run(
                            [str(GIT), "-C", str(repo), "switch", "-qc", "late-branch"],
                            check=True,
                            text=True,
                            capture_output=True,
                            env=self.env,
                        )
                    before_index = (repo / ".git" / "index").read_bytes()
                    before_head = subprocess.run(
                        [str(GIT), "-C", str(repo), "rev-parse", "HEAD"],
                        check=True,
                        text=True,
                        capture_output=True,
                        env=self.env,
                    ).stdout
                    before_branch = subprocess.run(
                        [str(GIT), "-C", str(repo), "branch", "--show-current"],
                        check=True,
                        text=True,
                        capture_output=True,
                        env=self.env,
                    ).stdout
                    before_tree = self._file_tree(repo)
                    before_workspace = self._workspace_snapshot(root)

                    with self.assertRaises(workspace.WorkspaceError):
                        with mock.patch.dict(os.environ, self.env, clear=False):
                            workspace.plan_return(root)

                    self.assertEqual((repo / ".git" / "index").read_bytes(), before_index)
                    self.assertEqual(
                        subprocess.run(
                            [str(GIT), "-C", str(repo), "rev-parse", "HEAD"],
                            check=True,
                            text=True,
                            capture_output=True,
                            env=self.env,
                        ).stdout,
                        before_head,
                    )
                    self.assertEqual(
                        subprocess.run(
                            [str(GIT), "-C", str(repo), "branch", "--show-current"],
                            check=True,
                            text=True,
                            capture_output=True,
                            env=self.env,
                        ).stdout,
                        before_branch,
                    )
                    self.assertEqual(self._file_tree(repo), before_tree)
                    self.assertEqual(self._workspace_snapshot(root), before_workspace)
                    self.assertTrue(Path(record["worktree"]).is_dir())

    def test_execute_refuses_stale_candidate_and_stale_plan_without_mutation(self) -> None:
        root = self.base / "stale candidate"
        record = self._prepare(name="stale candidate")
        worktree = self._worktree(record)
        (worktree / "candidate.txt").write_text("candidate one\n", encoding="utf-8")
        self._commit_all(worktree, "candidate one")
        self._plan(root)
        self._resolve_plan(root)
        (worktree / "candidate.txt").write_text("candidate changed after plan\n", encoding="utf-8")
        source_before = self._source_snapshot()
        workspace_before = self._workspace_snapshot(root)

        with self.assertRaises(workspace.WorkspaceError):
            self._call(workspace.execute_return, root)

        self._assert_source_unchanged(source_before)
        self.assertEqual(self._workspace_snapshot(root), workspace_before)
        self.assertFalse((root / "return-receipt.md").exists())

        # A host may choose only dispositions.  It may not silently reuse a
        # plan whose expected candidate path set no longer describes reality.
        stale_root = self.base / "stale plan"
        record = self._prepare(name="stale plan")
        worktree = self._worktree(record)
        (worktree / "candidate.txt").write_text("candidate one\n", encoding="utf-8")
        self._commit_all(worktree, "candidate one")
        self._plan(stale_root)
        plan = store.read_record(stale_root / "return-plan.md")
        plan["paths"] = []
        store.write_record(stale_root / "return-plan.md", plan, "ShipLoop workspace return plan")
        source_before = self._source_snapshot()
        workspace_before = self._workspace_snapshot(stale_root)

        with self.assertRaises(workspace.WorkspaceError):
            self._call(workspace.execute_return, stale_root)

        self._assert_source_unchanged(source_before)
        self.assertEqual(self._workspace_snapshot(stale_root), workspace_before)
        self.assertFalse((stale_root / "return-receipt.md").exists())

    def test_execute_refuses_a_duplicate_return_plan_row_without_source_mutation(self) -> None:
        root = self.base / "duplicate plan row"
        record = self._prepare(name="duplicate plan row")
        worktree = self._worktree(record)
        (worktree / "candidate.txt").write_text("candidate one\n", encoding="utf-8")
        self._commit_all(worktree, "candidate for malformed plan")
        self._plan(root)
        plan = self._resolve_plan(root)
        plan["paths"].append(dict(plan["paths"][0]))
        store.write_record(root / "return-plan.md", plan, "ShipLoop workspace return plan")
        source_before = self._source_snapshot()
        workspace_before = self._workspace_snapshot(root)

        with self.assertRaises(workspace.WorkspaceError):
            self._call(workspace.execute_return, root)

        self._assert_source_unchanged(source_before)
        self.assertEqual(self._workspace_snapshot(root), workspace_before)
        self.assertFalse((root / "return-receipt.md").exists())

    def test_failed_named_git_reads_never_be_interpreted_as_an_empty_delta(self) -> None:
        """A nonzero empty read must block rather than erase history or changes."""
        self._seed_dirty_source()
        faults = (
            (
                "name-status",
                "plan",
                lambda args: len(args) >= 2 and args[0:2] == ("diff", "--name-status"),
            ),
            ("history", "plan", lambda args: bool(args) and args[0] == "log"),
            (
                "untracked",
                "plan",
                lambda args: bool(args)
                and args[0] == "status"
                and "--porcelain=v1" in args,
            ),
            (
                "index-paths",
                "plan",
                lambda args: len(args) >= 2 and args[0:2] == ("ls-files", "-z"),
            ),
            ("tree-paths", "return", lambda args: bool(args) and args[0] == "ls-tree"),
        )
        original_git = workspace._git
        for name, phase, predicate in faults:
            with self.subTest(name=name, phase=phase):
                root = self.base / f"named read fault {name}"
                record = self._prepare(name=f"named read fault {name}")
                worktree = self._worktree(record)
                (worktree / f"candidate-{name}.txt").write_text(
                    "candidate\n", encoding="utf-8"
                )
                self._commit_all(worktree, f"candidate for {name} fault")
                if phase == "return":
                    self._plan(root)
                    self._resolve_plan(root)
                source_before = self._source_snapshot()
                workspace_before = self._workspace_snapshot(root)

                def failed_read(repo, *args, **kwargs):
                    if predicate(args):
                        return subprocess.CompletedProcess(
                            args=("git", *args),
                            returncode=1,
                            stdout=b"",
                            stderr=b"injected named read failure",
                        )
                    return original_git(repo, *args, **kwargs)

                with mock.patch.object(workspace, "_git", side_effect=failed_read):
                    with self.assertRaises(workspace.WorkspaceError):
                        if phase == "plan":
                            self._call(workspace.plan_return, root)
                        else:
                            self._call(workspace.execute_return, root)

                self._assert_source_unchanged(source_before)
                self.assertEqual(self._workspace_snapshot(root), workspace_before)
                self.assertFalse((root / "return-receipt.md").exists())

    def test_return_receipt_is_idempotent_but_candidate_mutation_invalidates_handoff(self) -> None:
        root = self.base / "receipt lifecycle"
        record = self._prepare(name="receipt lifecycle")
        worktree = self._worktree(record)
        (worktree / "receipt-feature.txt").write_text("returned once\n", encoding="utf-8")
        self._commit_all(worktree, "candidate for receipt")
        self._plan(root)
        self._resolve_plan(root)

        receipt = self._execute(root)
        before = self._workspace_snapshot(root)
        self.assertEqual(self._call(workspace.execute_return, root), receipt)
        self.assertEqual(self._call(workspace.completed_receipt, root, self.repo), receipt)
        self.assertEqual(self._call(workspace.completed_receipt, root, self.repo), receipt)
        self.assertEqual(self._workspace_snapshot(root), before)
        self.assertTrue((root / "worktree").is_dir())
        self.assertTrue((root / "run").is_dir())

        (worktree / "receipt-feature.txt").write_text("candidate drift after return\n", encoding="utf-8")
        receipt_bytes = (root / "return-receipt.md").read_bytes()
        self.assertIsNone(self._call(workspace.completed_receipt, root, self.repo))
        self.assertEqual((root / "return-receipt.md").read_bytes(), receipt_bytes)

    def test_receipt_snapshot_never_mutates_workspace_or_git_objects(self) -> None:
        """Display reads refuse uncertainty instead of creating locks or recovery writes."""
        root = self.base / "read-only receipt snapshot"
        record = self._prepare(name=root.name)
        worktree = self._worktree(record)
        candidate = worktree / "snapshot-feature.txt"
        candidate.write_text("returned feature\n", encoding="utf-8")
        self._commit_all(worktree, "candidate for read-only receipt snapshot")
        self._plan(root)
        self._resolve_plan(root)
        receipt = self._execute(root)

        workspace_before = self._workspace_snapshot(root)
        source_index_before = (self.repo / ".git" / "index").read_bytes()
        objects_before = self._common_object_snapshot()
        self.assertEqual(
            self._call(workspace.completed_receipt_snapshot, root, self.repo), receipt
        )
        self.assertEqual(self._workspace_snapshot(root), workspace_before)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), source_index_before)
        self.assertEqual(self._common_object_snapshot(), objects_before)

        with mock.patch("fcntl.flock", side_effect=OSError("workspace is busy")):
            self.assertIsNone(
                self._call(workspace.completed_receipt_snapshot, root, self.repo)
            )
        self.assertEqual(self._workspace_snapshot(root), workspace_before)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), source_index_before)
        self.assertEqual(self._common_object_snapshot(), objects_before)

        def interrupted(phase: str, index: int) -> None:
            if phase == "after-target" and index == 1:
                raise RuntimeError("leave a pending workspace transaction")

        with self.assertRaisesRegex(RuntimeError, "pending workspace transaction"):
            store.transaction(
                root,
                {"pending-snapshot.md": "must not be recovered by display\n"},
                fault=interrupted,
            )
        pending_before = self._workspace_snapshot(root)
        pending_index = (self.repo / ".git" / "index").read_bytes()
        pending_objects = self._common_object_snapshot()
        self.assertTrue((root / "transaction.md").is_file())
        self.assertIsNone(
            self._call(workspace.completed_receipt_snapshot, root, self.repo)
        )
        self.assertEqual(self._workspace_snapshot(root), pending_before)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), pending_index)
        self.assertEqual(self._common_object_snapshot(), pending_objects)
        self.assertEqual(self._call(workspace.completed_receipt, root, self.repo), receipt)
        self.assertFalse((root / "transaction.md").exists())

        candidate.write_text("candidate novel blob after return\n", encoding="utf-8")
        candidate_before = self._workspace_snapshot(root)
        candidate_index = (self.repo / ".git" / "index").read_bytes()
        candidate_objects = self._common_object_snapshot()
        self.assertIsNone(
            self._call(workspace.completed_receipt_snapshot, root, self.repo)
        )
        self.assertEqual(self._workspace_snapshot(root), candidate_before)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), candidate_index)
        self.assertEqual(self._common_object_snapshot(), candidate_objects)

        candidate.write_text("returned feature\n", encoding="utf-8")
        source = self.repo / "snapshot-feature.txt"
        source.write_text("source novel blob after return\n", encoding="utf-8")
        source_before = self._workspace_snapshot(root)
        source_index = (self.repo / ".git" / "index").read_bytes()
        source_objects = self._common_object_snapshot()
        self.assertIsNone(
            self._call(workspace.completed_receipt_snapshot, root, self.repo)
        )
        self.assertEqual(self._workspace_snapshot(root), source_before)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), source_index)
        self.assertEqual(self._common_object_snapshot(), source_objects)

        lock = root / ".workspace.lock"
        self.assertTrue(lock.is_file())
        lock.unlink()
        absent_lock_before = self._workspace_snapshot(root)
        absent_lock_index = (self.repo / ".git" / "index").read_bytes()
        absent_lock_objects = self._common_object_snapshot()
        self.assertIsNone(
            self._call(workspace.completed_receipt_snapshot, root, self.repo)
        )
        self.assertEqual(self._workspace_snapshot(root), absent_lock_before)
        self.assertEqual((self.repo / ".git" / "index").read_bytes(), absent_lock_index)
        self.assertEqual(self._common_object_snapshot(), absent_lock_objects)

    def test_public_workspace_commands_start_plan_and_return(self) -> None:
        root = self.base / "public cli workspace"
        started = self.cli(
            "workspace",
            "start",
            "--repo",
            str(self.repo),
            "--workspace-root",
            str(root),
            "--protocol-version",
            "2",
            "--prompt",
            "Add one small isolated feature.",
        )
        self.assertIn("ShipLoop navigator | intake", started.stdout)
        self.assertIn("Call this when done:", started.stdout)
        manifest = store.read_record(root / "workspace.md")
        self.assertEqual(manifest["status"], "prepared")
        self.assertTrue((root / "run" / "state.md").is_file())
        worktree = root / "worktree"
        (worktree / "cli-feature.txt").write_text("CLI candidate\n", encoding="utf-8")
        self._commit_all(worktree, "CLI candidate")

        planned = self.cli(
            "workspace", "plan-return", "--workspace-root", str(root)
        )
        self.assertIn("Review all keep/exclude dispositions", planned.stdout)
        self._resolve_plan(root)
        # The return itself is a whole-run handoff: it is intentionally not
        # available during intake or an inner item.  Use a synthetic valid
        # graph walk here only to reach the public command's allowed boundary.
        state = self._advance_to_handoff(store.read_record(root / "run" / "state.md"))
        navigator.save(root / "run", state)
        returned = self.cli("workspace", "return", "--workspace-root", str(root))
        self.assertIn("Verified workspace return", returned.stdout)
        self.assertEqual(store.read_record(root / "return-receipt.md")["status"], "returned")

    def test_public_return_is_refused_before_release_or_handoff_without_mutation(self) -> None:
        root = self.base / "early return"
        self.cli(
            "workspace",
            "start",
            "--repo",
            str(self.repo),
            "--workspace-root",
            str(root),
            "--protocol-version",
            "2",
            "--prompt",
            "Do not return before the outer lifecycle is ready.",
        )
        source_before = self._source_snapshot()
        run_before = self._workspace_snapshot(root)

        refused = self.cli(
            "workspace", "return", "--workspace-root", str(root), code=2
        )

        self.assertIn("release or handoff", refused.stderr)
        self._assert_source_unchanged(source_before)
        self.assertEqual(self._workspace_snapshot(root), run_before)
        self.assertFalse((root / "return-receipt.md").exists())

    def test_workspace_start_replay_is_idempotent_and_rejects_changed_scope_or_capture(self) -> None:
        root = self.base / "replayed workspace start"
        prompt = "Make one isolated feature without replacing this run."
        self.cli(
            "workspace",
            "start",
            "--repo",
            str(self.repo),
            "--workspace-root",
            str(root),
            "--protocol-version",
            "2",
            "--prompt",
            prompt,
        )
        source_before = self._source_snapshot()
        manifest_before = (root / "workspace.md").read_bytes()
        state_before = (root / "run" / "state.md").read_bytes()

        replay = self.cli(
            "workspace",
            "start",
            "--repo",
            str(self.repo),
            "--workspace-root",
            str(root),
            "--protocol-version",
            "2",
            "--prompt",
            prompt,
        )
        self.assertIn("ShipLoop navigator | intake", replay.stdout)
        self._assert_source_unchanged(source_before)
        self.assertEqual((root / "workspace.md").read_bytes(), manifest_before)
        self.assertEqual((root / "run" / "state.md").read_bytes(), state_before)

        changed_prompt = self.cli(
            "workspace",
            "start",
            "--repo",
            str(self.repo),
            "--workspace-root",
            str(root),
            "--protocol-version",
            "2",
            "--prompt",
            "A distinct request must use a new workspace.",
            code=2,
        )
        self.assertIn("fresh workspace root", changed_prompt.stderr)
        changed_capture = self.cli(
            "workspace",
            "start",
            "--repo",
            str(self.repo),
            "--workspace-root",
            str(root),
            "--protocol-version",
            "2",
            "--prompt",
            prompt,
            "--include-untracked",
            "different-input.txt",
            code=2,
        )
        self.assertIn("capture options", changed_capture.stderr)
        self._assert_source_unchanged(source_before)
        self.assertEqual((root / "workspace.md").read_bytes(), manifest_before)
        self.assertEqual((root / "run" / "state.md").read_bytes(), state_before)

    def test_fresh_workspace_roots_isolate_identical_prompts(self) -> None:
        """Same text in a new root creates a new run and preserves the old cursor."""
        prompt = "Keep this request independent even when an identical run exists."
        for label, protocol_args, protocol_version in (
            ("default-v3", (), 3),
            ("explicit-v2", ("--protocol-version", "2"), 2),
        ):
            with self.subTest(protocol=label):
                old_root = self.base / f"{label} original workspace"
                fresh_root = self.base / f"{label} fresh workspace"
                self.cli(
                    "workspace",
                    "start",
                    "--repo",
                    str(self.repo),
                    "--workspace-root",
                    str(old_root),
                    *protocol_args,
                    "--prompt",
                    prompt,
                )
                old_workspace_before = (old_root / "workspace.md").read_bytes()
                old_state_before = (old_root / "run" / "state.md").read_bytes()
                old_state = store.read_record(old_root / "run" / "state.md")

                self.cli(
                    "workspace",
                    "start",
                    "--repo",
                    str(self.repo),
                    "--workspace-root",
                    str(fresh_root),
                    *protocol_args,
                    "--prompt",
                    prompt,
                )
                fresh_workspace_before = (fresh_root / "workspace.md").read_bytes()
                fresh_state_before = (fresh_root / "run" / "state.md").read_bytes()
                fresh_state = store.read_record(fresh_root / "run" / "state.md")

                self.assertEqual(old_state["status"], "active")
                self.assertEqual(fresh_state["status"], "active")
                self.assertEqual(old_state["navigator_protocol_version"], protocol_version)
                self.assertEqual(fresh_state["navigator_protocol_version"], protocol_version)
                self.assertEqual(old_state["prompt"].encode("utf-8"), prompt.encode("utf-8"))
                self.assertEqual(fresh_state["prompt"].encode("utf-8"), prompt.encode("utf-8"))
                self.assertNotEqual(old_state["run_id"], fresh_state["run_id"])
                self.assertNotEqual(old_state["action"]["id"], fresh_state["action"]["id"])
                self.assertEqual((old_root / "workspace.md").read_bytes(), old_workspace_before)
                self.assertEqual((old_root / "run" / "state.md").read_bytes(), old_state_before)

                recovered = self.cli("next", "--run-dir", str(old_root / "run"))
                self.assertIn("ShipLoop navigator | intake", recovered.stdout)
                self.assertEqual((old_root / "workspace.md").read_bytes(), old_workspace_before)
                self.assertEqual((old_root / "run" / "state.md").read_bytes(), old_state_before)
                self.assertEqual((fresh_root / "workspace.md").read_bytes(), fresh_workspace_before)
                self.assertEqual((fresh_root / "run" / "state.md").read_bytes(), fresh_state_before)

    @staticmethod
    def _advance_to_handoff(state: dict) -> dict:
        """Build a valid terminal-adjacent navigator fixture without host work."""
        while state["status"] != "done":
            action = navigator.current_action(state)
            if action["stage"] == "handoff":
                return state
            result: dict[str, object] = {
                "outcome": "done",
                "summary": "Synthetic transition for workspace handoff guard coverage.",
            }
            if action["stage"] == "plan":
                result["work_items"] = [
                    {
                        "id": "W1",
                        "title": "One synthetic item",
                        "context": "Only test navigator terminal gating.",
                    }
                ]
            if action["stage"] == "document":
                result["choices"] = {"skill_required": False}
            state = navigator.apply(state, action["id"], result)
        raise AssertionError("navigator reached done before handoff")

    def test_worktree_navigator_cannot_complete_handoff_without_return_receipt(self) -> None:
        root = self.base / "guarded handoff"
        self.cli(
            "workspace",
            "start",
            "--repo",
            str(self.repo),
            "--workspace-root",
            str(root),
            "--protocol-version",
            "2",
            "--prompt",
            "Guard the isolated workspace handoff.",
        )
        run = (root / "run").resolve()
        state = store.read_record(run / "state.md")
        self.assertEqual(state["execution_mode"], "navigator-worktree")
        state = self._advance_to_handoff(state)
        navigator.save(run, state)
        action = state["action"]
        result_path = run / "inbox" / f"{action['id']}.md"
        store.write_record(
            result_path,
            {
                "outcome": "done",
                "summary": "This completion must be rejected without a return receipt.",
            },
            "ShipLoop navigator result",
        )
        before = (run / "state.md").read_bytes()

        refused = self.cli(
            "complete",
            "--run-dir",
            str(run),
            "--action",
            action["id"],
            "--result",
            str(result_path),
            code=2,
        )

        self.assertIn("verified workspace return", refused.stderr)
        self.assertEqual((run / "state.md").read_bytes(), before)
        self.assertFalse((run / "report.html").exists())

    def test_verified_return_allows_the_same_worktree_handoff_to_complete(self) -> None:
        """The terminal guard rejects missing proof without making valid proof unusable."""
        root = self.base / "successful guarded handoff"
        self.cli(
            "workspace",
            "start",
            "--repo",
            str(self.repo),
            "--workspace-root",
            str(root),
            "--protocol-version",
            "2",
            "--prompt",
            "Complete one isolated handoff after a verified return.",
        )
        worktree = root / "worktree"
        (worktree / "handoff-feature.txt").write_text("returned feature\n", encoding="utf-8")
        self._commit_all(worktree, "candidate handoff feature")
        run = (root / "run").resolve()
        state = self._advance_to_handoff(store.read_record(run / "state.md"))
        navigator.save(run, state)
        self.cli("workspace", "plan-return", "--workspace-root", str(root))
        self._resolve_plan(root)
        returned = self.cli("workspace", "return", "--workspace-root", str(root))
        self.assertIn("Verified workspace return", returned.stdout)
        action = navigator.current_action(store.read_record(run / "state.md"))
        result_path = run / "inbox" / f"{action['id']}.md"
        store.write_record(
            result_path,
            {
                "outcome": "done",
                "summary": "Verified workspace return is available to the terminal guard.",
            },
            "ShipLoop navigator result",
        )

        completed = self.cli(
            "complete",
            "--run-dir",
            str(run),
            "--action",
            action["id"],
            "--result",
            str(result_path),
        )

        self.assertIn("It's all complete.", completed.stdout)
        self.assertEqual(store.read_record(run / "state.md")["status"], "done")
        self.assertEqual(
            (self.repo / "handoff-feature.txt").read_text(encoding="utf-8"),
            "returned feature\n",
        )
        self.assertEqual(store.read_record(root / "return-receipt.md")["status"], "returned")

    def test_return_projection_stays_current_across_terminal_cold_and_report_packets(self) -> None:
        """A historical handoff summary cannot keep a drifted receipt current."""
        root = self.base / "return projection"
        self.cli(
            "workspace",
            "start",
            "--repo",
            str(self.repo),
            "--workspace-root",
            str(root),
            "--protocol-version",
            "2",
            "--prompt",
            "Project the current guarded workspace return into packets.",
        )
        run = (root / "run").resolve()
        receipt_path = run.parent / "return-receipt.md"
        initial_state = store.read_record(run / "state.md")
        initial_state_bytes = (run / "state.md").read_bytes()
        with mock.patch.dict(os.environ, self.env, clear=False):
            initial_packet = navigator.render(None, run, initial_state)
        self.assertIn("Return receipt: " + str(receipt_path), initial_packet)
        self.assertIn("Current workspace return: not currently verified.", initial_packet)
        self.assertEqual((run / "state.md").read_bytes(), initial_state_bytes)

        worktree = root / "worktree"
        (worktree / "return-projection-feature.txt").write_text(
            "returned feature\n", encoding="utf-8"
        )
        self._commit_all(worktree, "candidate for return projection")
        state = self._advance_to_handoff(store.read_record(run / "state.md"))
        navigator.save(run, state)
        self.cli("workspace", "plan-return", "--workspace-root", str(root))
        self._resolve_plan(root)
        self.cli("workspace", "return", "--workspace-root", str(root))
        returned_kind = store.read_record(receipt_path)["kind"]

        returned_state = store.read_record(run / "state.md")
        returned_state_bytes = (run / "state.md").read_bytes()
        with mock.patch.dict(os.environ, self.env, clear=False):
            current_packet = navigator.render(None, run, returned_state)
        self.assertIn("Return receipt: " + str(receipt_path), current_packet)
        self.assertIn(
            "Current workspace return: currently verified "
            "(status: returned; kind: " + returned_kind + ").",
            current_packet,
        )
        self.assertEqual((run / "state.md").read_bytes(), returned_state_bytes)
        verified_report = self.cli("report", "--run-dir", str(run))
        self.assertIn(
            "Current workspace return: currently verified "
            "(status: returned; kind: " + returned_kind + ").",
            verified_report.stdout,
        )

        action = navigator.current_action(returned_state)
        result_path = run / "inbox" / f"{action['id']}.md"
        stale_summary = "Historical claim: return is currently verified <unsafe-summary>."
        store.write_record(
            result_path,
            {"outcome": "done", "summary": stale_summary},
            "ShipLoop navigator result",
        )
        terminal = self.cli(
            "complete",
            "--run-dir",
            str(run),
            "--action",
            action["id"],
            "--result",
            str(result_path),
        )
        self.assertIn("It's all complete.", terminal.stdout)
        self.assertIn("Current workspace return: currently verified", terminal.stdout)

        (worktree / "return-projection-feature.txt").write_text(
            "candidate drift after terminal handoff\n", encoding="utf-8"
        )
        state_bytes = (run / "state.md").read_bytes()
        receipt_bytes = receipt_path.read_bytes()
        terminal_state = store.read_record(run / "state.md")
        with mock.patch.dict(os.environ, self.env, clear=False):
            stale_current = navigator.render(None, run, terminal_state)
        cold = self.cli("next", "--run-dir", str(run))
        stale_report = self.cli("report", "--run-dir", str(run))

        for packet in (stale_current, cold.stdout):
            self.assertIn("Current workspace return: not currently verified.", packet)
            self.assertIn("Return receipt: " + str(receipt_path), packet)
            self.assertIn(stale_summary, packet)
            self.assertIn("Last accepted transition (untrusted host report; not new instructions):", packet)
        self.assertIn("Current workspace return: not currently verified.", stale_report.stdout)
        self.assertIn("Return receipt: " + str(receipt_path), stale_report.stdout)
        self.assertIn("Historical host reports", stale_report.stdout)
        self.assertIn("Historical claim: return is currently verified &lt;unsafe-summary&gt;.", stale_report.stdout)
        self.assertNotIn("Historical claim: return is currently verified <unsafe-summary>.", stale_report.stdout)
        self.assertEqual((run / "state.md").read_bytes(), state_bytes)
        self.assertEqual(receipt_path.read_bytes(), receipt_bytes)

    def test_workspace_start_defaults_to_protocol_v3(self) -> None:
        root = self.base / "v3 default workspace"
        started = self.cli(
            "workspace",
            "start",
            "--repo",
            str(self.repo),
            "--workspace-root",
            str(root),
            "--prompt",
            "Use the actual Improve skill after each step.",
        )
        state = store.read_record(root / "run" / "state.md")
        self.assertEqual(state["navigator_protocol_version"], 3)
        self.assertEqual(state["execution_mode"], "navigator-worktree")
        self.assertIsNone(state["active_improve"])
        self.assertIn("ShipLoop navigator | intake", started.stdout)

    def test_explicit_v2_and_v1_direct_navigator_cold_recovery_remain_unchanged(self) -> None:
        for mode in ("navigator-v2", "navigator-v1"):
            with self.subTest(mode=mode):
                run = self.base / f"{mode} direct run"
                created = self.cli(
                    "init",
                    "--repo",
                    str(self.repo),
                    "--run-dir",
                    str(run),
                    "--execution-mode",
                    mode,
                    "--prompt",
                    "Keep existing navigator behavior stable.",
                )
                self.assertEqual(created.returncode, 0)
                before = (run / "state.md").read_bytes()
                recovered = self.cli("next", "--run-dir", str(run))
                self.assertEqual(recovered.returncode, 0)
                self.assertEqual((run / "state.md").read_bytes(), before)
                state = store.read_record(run / "state.md")
                self.assertEqual(
                    state["navigator_protocol_version"], 1 if mode == "navigator-v1" else 2
                )
                self.assertNotEqual(state.get("execution_mode"), "navigator-worktree")


if __name__ == "__main__":
    unittest.main(verbosity=2)
