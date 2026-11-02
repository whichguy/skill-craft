#!/usr/bin/env python3
"""Preparation owns only its declared, clean-at-entry file deltas before item-base capture.

Each CLI case uses synthetic accepted results for the stages before prepare. It emits the first prepare packet and
submits the accepted prepare callback through the real ShipLoop CLI. No model is invoked.
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import state_home

state_home.isolate()

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(ROOT / "test"))
import git_fixture  # noqa: E402
import shiploop_git  # noqa: E402
import shiploop_inner_fixture as fx  # noqa: E402
import shiploop_lint as lint  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402

CLI = ROOT / "skills/shiploop/scripts/shiploop"


class PreparationCliTests(fx.RunDriver):
    """A real CLI callback after a clearly labeled synthetic pre-prepare seed."""

    def setUp(self) -> None:
        home = tempfile.TemporaryDirectory(prefix="shiploop-preparation-home-")
        self.addCleanup(home.cleanup)
        git_fixture.isolate_git_environment(self, home.name)
        super().setUp()

    def open_prepare(self, before_prelude=None, *, already_started: bool = False) -> str:
        """Drive earlier stages with fixture results, then issue the real first prepare packet."""
        if not already_started:
            self.start()
        if before_prelude is not None:
            before_prelude()
        self.drive_to("prepare")
        self.assertEqual(nav.current_stage(self.state()), "prepare")
        emitted = self.cli("next", "--run-dir", str(self.run_dir))
        self.assertEqual(emitted.returncode, 0, emitted.stdout + emitted.stderr)
        return str(nav.current_action(self.state())["id"])

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-B", str(CLI), *args], cwd=self.base, capture_output=True, text=True,
            check=False, timeout=120,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "SHIPLOOP_PROGRESS": "off",
                 "SHIPLOOP_KEEPALIVE": "off"},
        )

    def _result_file(self, result: dict) -> tuple[dict, Path]:
        state = self.state()
        action = str(nav.current_action(state)["id"])
        evidence = self.run_dir / "prepare-evidence.txt"
        evidence.write_text("Synthetic evidence for the prepare callback.\n", encoding="utf-8")
        value = {"outcome": "done", "summary": "The prepare-owned setup file is ready.",
                 "evidence_refs": [str(evidence)], **result}
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(store.dumps(value, "result"), encoding="utf-8")
        return state, path

    def submit(self, result: dict, *, through_cli: bool = True) -> subprocess.CompletedProcess | int:
        state, path = self._result_file(result)
        if "prepare" in fx.knowledge_support.knowledge.CLOSES:
            fx.knowledge_support.write(state)
        action = str(nav.current_action(state)["id"])
        args = ("complete", "--run-dir", str(self.run_dir), "--action", action, "--result", str(path))
        if through_cli:
            return self.cli(*args)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            nav.dispatch(fx.CORE, self.run_dir, state,
                         types.SimpleNamespace(command="complete", action=action, result=str(path)))
        return 0

    def git(self, *args: str) -> str:
        done = subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True)
        return done.stdout

    def git_at(self, repo: Path, *args: str) -> str:
        done = subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)
        return done.stdout

    def assert_prepare_commit_precedes_item_base(self, commit: str, paths: list[str]) -> None:
        self.assertTrue(commit)
        self.assertEqual(self.git("show", "--format=", "--name-only", commit).splitlines(), paths)
        base = lint.read_base(self.run_dir, "W1")
        self.assertIsNotNone(base)
        self.assertEqual(base["head"], commit, "the first item base must begin after the prepare commit")
        final_head = self.git("rev-parse", "HEAD").strip()
        self.assertIn(commit, self.git("rev-list", final_head).splitlines(),
                      "later knowledge close commits must preserve the accepted prepare commit as an ancestor")

    def rehome_repo_as_subdirectory(self) -> tuple[Path, Path]:
        """Keep the fixture's Git toplevel, but make the ShipLoop repository a tracked child directory."""
        top = self.repo
        child = top / "nested-project"
        child.mkdir()
        self.run_dir.rmdir()
        self.run_dir.parent.rmdir()
        for name in (".gitignore", "a.py"):
            (top / name).rename(child / name)
        self.git("add", "-A")
        self.git("commit", "-qm", "move fixture project under the Git toplevel")
        self.repo = child
        self.run_dir = child / "runs" / "r1"
        self.run_dir.mkdir(parents=True)
        return top, child

    def open_managed_workspace_prepare(self, *, exclude: tuple[str, ...]) -> str:
        """Open a real script-managed worktree and bind its run directory to the manifest."""
        root = self.base / "managed preparation workspace"
        manifest = workspace.prepare(self.repo, root, exclude=exclude)
        self.repo = Path(manifest["worktree"])
        self.run_dir = Path(manifest["run_dir"])
        state = nav.new_state(str(self.repo), "Inner fixture.", improve_skill=str(fx.IMPROVE_CARD),
                              lint_option="off", worktree=True)
        nav.save(self.run_dir, state)
        return self.open_prepare(already_started=True)

    def test_prepare_paths_are_optional_empty_or_literal_concrete_paths(self) -> None:
        base = {"outcome": "done", "summary": "Prepare declared a setup file.", "evidence_refs": []}
        for paths in (None, [], ["literal[1]*?.txt"]):
            with self.subTest(paths=paths):
                result = dict(base)
                if paths is not None:
                    result["paths"] = paths
                canonical = nav._canonical_result(result, stage="prepare")
                self.assertEqual(canonical.get("paths", []), paths or [])
        for path in ("/outside.txt", "../outside.txt"):
            with self.subTest(path=path), self.assertRaises(nav.NavigatorError):
                nav._canonical_result({**base, "paths": [path]}, stage="prepare")

    def test_real_cli_commits_declared_gitignore_before_first_item_base(self) -> None:
        self.open_prepare()
        before = self.git("rev-parse", "HEAD").strip()
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")

        done = self.submit({"paths": [".gitignore"]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        committed = self.git("log", "-1", "--format=%H", "--", ".gitignore").strip()
        self.assertNotEqual(committed, before)
        self.assert_prepare_commit_precedes_item_base(committed, [".gitignore"])

    def test_subdirectory_repo_commits_its_declared_path_under_the_git_toplevel(self) -> None:
        top, child = self.rehome_repo_as_subdirectory()
        self.open_prepare()
        (child / "setup.txt").write_text("inside the configured repository\n", encoding="utf-8")
        (top / "setup.txt").write_text("outside the configured repository\n", encoding="utf-8")
        (top / "sibling.txt").write_text("also outside the configured repository\n", encoding="utf-8")

        done = self.submit({"paths": ["setup.txt"]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        committed = self.git_at(top, "log", "-1", "--format=%H", "--", "nested-project/setup.txt").strip()
        self.assertTrue(committed, "the eligible file must be committed using its Git-root path")
        self.assertEqual(self.git_at(top, "show", "--format=", "--name-only", committed).splitlines(),
                         ["nested-project/setup.txt"])
        self.assertEqual((top / "setup.txt").read_text(encoding="utf-8"), "outside the configured repository\n")
        self.assertIn("?? setup.txt", self.git_at(top, "status", "--porcelain=v1", "--untracked-files=all"))
        self.assertIn("?? sibling.txt", self.git_at(top, "status", "--porcelain=v1", "--untracked-files=all"))

    def test_symlink_component_escape_does_not_stage_external_or_undeclared_files(self) -> None:
        external = self.base / "outside target"
        external.mkdir()
        (external / "sentinel.txt").write_text("external target remains external\n", encoding="utf-8")

        def add_external_link() -> None:
            (self.repo / "escape").symlink_to(external, target_is_directory=True)
            self.git("add", "--", "escape")
            self.git("commit", "-qm", "record a symlink component")

        self.open_prepare(add_external_link)
        (external / "declared.txt").write_text("must remain outside Git\n", encoding="utf-8")
        (self.repo / "unrelated.txt").write_text("must stay uncommitted\n", encoding="utf-8")

        done = self.submit({"paths": ["escape/declared.txt"]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual((external / "declared.txt").read_text(encoding="utf-8"), "must remain outside Git\n")
        self.assertEqual((external / "sentinel.txt").read_text(encoding="utf-8"),
                         "external target remains external\n")
        self.assertIn("?? unrelated.txt", self.git("status", "--porcelain=v1", "--untracked-files=all"))
        committed_paths = self.git("ls-tree", "-r", "--name-only", "HEAD").splitlines()
        self.assertIn("escape", committed_paths)
        self.assertNotIn("escape/declared.txt", committed_paths)

    def test_run_directory_is_excluded_even_when_git_does_not_ignore_it(self) -> None:
        def expose_run_directory() -> None:
            ignore = self.repo / ".gitignore"
            ignore.write_text(ignore.read_text(encoding="utf-8").replace("runs/\n", ""), encoding="utf-8")
            self.git("add", "--", ".gitignore")
            self.git("commit", "-qm", "fixture run directory is not gitignored")

        self.open_prepare(expose_run_directory)
        eligible = self.repo / "eligible.txt"
        eligible.write_text("declared product setup\n", encoding="utf-8")
        run_output = self.run_dir / "phase-output.txt"
        run_output.write_text("run-local output\n", encoding="utf-8")
        declared_run_path = run_output.relative_to(self.repo).as_posix()

        done = self.submit({"paths": ["eligible.txt", declared_run_path]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        eligible_commit = self.git("log", "-1", "--format=%H", "--", "eligible.txt").strip()
        self.assertTrue(eligible_commit)
        self.assertEqual(self.git("show", "--format=", "--name-only", eligible_commit).splitlines(), ["eligible.txt"])
        self.assertTrue(run_output.is_file())
        self.assertEqual(self.git("log", "--all", "--format=%H", "--", declared_run_path).strip(), "")

    def test_managed_workspace_runtime_and_caller_exclusions_leave_valid_path_commit_eligible(self) -> None:
        self.open_managed_workspace_prepare(exclude=("caller-excluded.txt",))
        eligible = self.repo / "eligible.txt"
        caller_excluded = self.repo / "caller-excluded.txt"
        runtime = self.repo / ".shiploop-improve" / "session" / "review.md"
        eligible.write_text("eligible setup\n", encoding="utf-8")
        caller_excluded.write_text("caller excluded setup\n", encoding="utf-8")
        runtime.parent.mkdir(parents=True)
        runtime.write_text("runtime evidence\n", encoding="utf-8")

        done = self.submit({"paths": ["eligible.txt", "caller-excluded.txt", ".shiploop-improve/session/review.md"]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        eligible_commit = self.git("log", "-1", "--format=%H", "--", "eligible.txt").strip()
        self.assertTrue(eligible_commit)
        self.assertEqual(self.git("show", "--format=", "--name-only", eligible_commit).splitlines(), ["eligible.txt"])
        self.assertTrue(caller_excluded.is_file())
        self.assertTrue(runtime.is_file())
        self.assertIn("?? caller-excluded.txt", self.git("status", "--porcelain=v1", "--", "caller-excluded.txt"))
        runtime_history = self.git("log", "--all", "--format=%H", "--",
                                   ".shiploop-improve/session/review.md").strip()
        self.assertEqual(runtime_history, "")
        self.assertIn("caller-excluded.txt", done.stdout + done.stderr)

    def test_omitted_paths_do_not_fall_back_to_all_prepare_deltas_or_evidence_refs(self) -> None:
        self.open_prepare()
        prior_ignore_commit = self.git("log", "-1", "--format=%H", "--", ".gitignore").strip()
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")

        done = self.submit({})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn(".gitignore", self.git("status", "--porcelain=v1", "--untracked-files=all"))
        self.assertEqual(self.git("log", "-1", "--format=%H", "--", ".gitignore").strip(), prior_ignore_commit,
                         "the existing knowledge-home close may commit docs, but cannot own omitted setup paths")

    def test_empty_paths_do_not_authorize_phase_changes(self) -> None:
        self.open_prepare()
        prior_ignore_commit = self.git("log", "-1", "--format=%H", "--", ".gitignore").strip()
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")

        done = self.submit({"paths": []})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn(".gitignore", self.git("status", "--porcelain=v1", "--untracked-files=all"))
        self.assertEqual(self.git("log", "-1", "--format=%H", "--", ".gitignore").strip(), prior_ignore_commit)

    def test_blocked_replacement_keeps_the_first_prepare_entry_snapshot(self) -> None:
        first_action = self.open_prepare()
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")

        blocked = self.submit({"outcome": "blocked", "summary": "A human must choose the setup target.",
                               "awaiting": {"kind": "answer", "question": "Which setup target?",
                                            "options": ["local", "shared"],
                                            "no_default": "The repository request does not choose one."}})
        self.assertEqual(blocked.returncode, 0, blocked.stdout + blocked.stderr)
        replacement = str(nav.current_action(self.state())["id"])
        self.assertNotEqual(replacement, first_action)
        resumed = self.cli("resume", "--run-dir", str(self.run_dir), "--answer", "Use the local target.")
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(str(nav.current_action(self.state())["id"]), replacement)
        # Resume issues the replacement packet; do not reinitialize the phase snapshot on this action.
        resumed = self.submit({"paths": [".gitignore"]})
        self.assertEqual(resumed.returncode, 0, resumed.stdout + resumed.stderr)
        self.assertEqual(self.git("status", "--porcelain=v1", "--", ".gitignore"), "")
        committed = self.git("log", "-1", "--format=%H", "--", ".gitignore").strip()
        self.assert_prepare_commit_precedes_item_base(committed, [".gitignore"])

    def test_entry_staged_modified_and_untracked_paths_are_preserved(self) -> None:
        def make_dirty_entry() -> None:
            (self.repo / "staged-only.txt").write_text("base\n", encoding="utf-8")
            self.git("add", "--", "staged-only.txt")
            self.git("commit", "-qm", "add staged-only fixture")
            (self.repo / "staged-only.txt").write_text("staged version\n", encoding="utf-8")
            self.git("add", "--", "staged-only.txt")
            (self.repo / "staged-only.txt").write_text("base\n", encoding="utf-8")
            (self.repo / "a.py").write_text("entry-time modification\n", encoding="utf-8")
            (self.repo / "entry-untracked.txt").write_text("keep me\n", encoding="utf-8")

        self.open_prepare(make_dirty_entry)
        before = sorted(self.git("status", "--porcelain=v1", "--untracked-files=all").splitlines())
        staged_before = self.git("show", ":staged-only.txt")
        working_before = (self.repo / "staged-only.txt").read_text(encoding="utf-8")
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")

        done = self.submit({"paths": [".gitignore"]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        after = sorted(self.git("status", "--porcelain=v1", "--untracked-files=all").splitlines())
        self.assertEqual(after, before)
        self.assertIn(" M a.py", after)
        self.assertIn("MM staged-only.txt", after)
        self.assertIn("?? entry-untracked.txt", after)
        self.assertEqual(self.git("show", ":staged-only.txt"), staged_before)
        self.assertEqual((self.repo / "staged-only.txt").read_text(encoding="utf-8"), working_before)

    def test_undeclared_concurrent_file_stays_visible_and_uncommitted(self) -> None:
        self.open_prepare()
        (self.repo / "concurrent.log").write_text("outside the declared path list\n", encoding="utf-8")
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")

        done = self.submit({"paths": [".gitignore"]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("?? concurrent.log", self.git("status", "--porcelain=v1", "--untracked-files=all"))
        committed = self.git("log", "-1", "--format=%H", "--", ".gitignore").strip()
        self.assert_prepare_commit_precedes_item_base(committed, [".gitignore"])

    def test_preexisting_ignored_file_stays_out_when_prepare_changes_ignore_rules(self) -> None:
        def make_ignored_entry() -> None:
            (self.repo / "ignored.txt").write_text("preexisting ignored data\n", encoding="utf-8")

        self.open_prepare(make_ignored_entry)
        ignore = self.repo / ".gitignore"
        rules = [line for line in ignore.read_text(encoding="utf-8").splitlines() if line != "ignored.txt"]
        ignore.write_text("\n".join(rules) + "\n", encoding="utf-8")

        done = self.submit({"paths": [".gitignore", "ignored.txt"]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        committed = self.git("log", "-1", "--format=%H", "--", ".gitignore").strip()
        self.assert_prepare_commit_precedes_item_base(committed, [".gitignore"])
        self.assertIn("?? ignored.txt", self.git("status", "--porcelain=v1", "--untracked-files=all"))

    def test_deleted_and_metacharacter_paths_are_committed_literally(self) -> None:
        def add_fixture_paths() -> None:
            (self.repo / "remove-me.txt").write_text("tracked at prepare entry\n", encoding="utf-8")
            self.git("add", "--", "remove-me.txt")
            self.git("commit", "-qm", "add deletion fixture")

        self.open_prepare(add_fixture_paths)
        (self.repo / "remove-me.txt").unlink()
        literal = "literal[1]*?.txt"
        (self.repo / literal).write_text("one literal file\n", encoding="utf-8")
        magic_name = ":(literal)setup.txt"
        (self.repo / magic_name).write_text("a filename beginning with pathspec-like text\n", encoding="utf-8")
        wildcard_neighbor = "literal1-neighbor.txt"
        (self.repo / wildcard_neighbor).write_text("a pathspec match that was not declared\n", encoding="utf-8")

        done = self.submit({"paths": ["remove-me.txt", literal, magic_name]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        base = lint.read_base(self.run_dir, "W1")
        self.assertIsNotNone(base)
        self.assert_prepare_commit_precedes_item_base(str(base["head"]),
                                                       [magic_name, literal, "remove-me.txt"])
        self.assertFalse((self.repo / "remove-me.txt").exists())
        self.assertEqual(self.git("status", "--porcelain=v1", "--", ":(literal)" + literal,
                                  ":(literal)" + magic_name, "remove-me.txt"), "")
        self.assertIn("?? " + wildcard_neighbor,
                      self.git("status", "--porcelain=v1", "--untracked-files=all"))

    def test_landed_prepare_commit_rejects_changed_result_then_accepts_exact_retry(self) -> None:
        self.open_prepare()
        (self.repo / ".gitignore").write_text(
            (self.repo / ".gitignore").read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")
        original = shiploop_git.commit_paths
        landed: list[str] = []

        def land_then_interrupt(repo, paths, message, **kwargs):
            result = original(repo, paths, message, **kwargs)
            landed.append(result.commit)
            raise shiploop_git.CommitError("simulated interruption after commit landed")

        with mock.patch.object(shiploop_git, "commit_paths", side_effect=land_then_interrupt):
            with self.assertRaises(nav.NavigatorError):
                self.submit({"paths": [".gitignore"]}, through_cli=False)
        self.assertEqual(nav.current_stage(self.state()), "prepare")
        self.assertEqual(len(landed), 1)
        preparation_record_path = self.run_dir / "preparation.md"
        original_record = store.read_record(preparation_record_path)
        pending = original_record["pending"]
        self.assertIsInstance(pending.get("result"), dict)
        self.assertEqual(pending["result"].get("paths"), [".gitignore"])
        saved_result_json = json.dumps(pending["result"], sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.assertEqual(pending.get("result_sha256"), hashlib.sha256(saved_result_json).hexdigest())

        with self.assertRaises(nav.NavigatorError) as refused:
            self.submit({"paths": [], "summary": "Withdraw the setup path after the commit landed."},
                        through_cli=False)
        self.assertIn("pending.result", str(refused.exception))
        self.assertIn("preparation.md", str(refused.exception))
        self.assertEqual(nav.current_stage(self.state()), "prepare")
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), landed[0])
        self.assertEqual(len(self.git("log", "--format=%H", "--", ".gitignore").splitlines()), 2,
                         "a changed callback must neither advance nor repeat the landed commit")

        for mutation in ("missing-result", "invalid-digest"):
            with self.subTest(pending_mutation=mutation):
                tampered = store.read_record(preparation_record_path)
                if mutation == "missing-result":
                    tampered["pending"].pop("result")
                else:
                    tampered["pending"]["result_sha256"] = (
                        "0" * 64 if pending["result_sha256"] != "0" * 64 else "1" * 64)
                store.write_record(preparation_record_path, tampered, "ShipLoop prepare ownership")
                with self.assertRaises(nav.NavigatorError) as invalid_pending:
                    self.submit(pending["result"], through_cli=False)
                self.assertIn("pending.result", str(invalid_pending.exception))
                self.assertEqual(nav.current_stage(self.state()), "prepare")
                self.assertEqual(self.git("rev-parse", "HEAD").strip(), landed[0])
                store.write_record(preparation_record_path, original_record, "ShipLoop prepare ownership")

        restored = store.read_record(preparation_record_path)["pending"]["result"]
        retry = self.submit(restored, through_cli=False)
        self.assertEqual(retry, 0)
        committed = self.git("log", "-1", "--format=%H", "--", ".gitignore").strip()
        self.assertEqual(committed, landed[0])
        self.assert_prepare_commit_precedes_item_base(committed, [".gitignore"])
        self.assertEqual(len(self.git("log", "--format=%H", "--", ".gitignore").splitlines()), 2,
                         "the retry must not create a duplicate preparation commit")

    def test_changed_pending_tree_is_refused_on_same_callback_retry(self) -> None:
        self.open_prepare()
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")
        before = self.git("rev-parse", "HEAD").strip()
        with mock.patch.object(shiploop_git, "commit_paths", side_effect=shiploop_git.CommitError("held")):
            with self.assertRaises(nav.NavigatorError):
                self.submit({"paths": [".gitignore"]}, through_cli=False)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), before)

        ignore.write_text(ignore.read_text(encoding="utf-8") + "another-change.tmp\n", encoding="utf-8")
        with self.assertRaises(nav.NavigatorError):
            self.submit({"paths": [".gitignore"]}, through_cli=False)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), before)
        self.assertEqual(nav.current_stage(self.state()), "prepare")

    def test_unrelated_head_movement_refuses_prepare_commit_without_advancing(self) -> None:
        self.open_prepare()
        (self.repo / ".gitignore").write_text(
            (self.repo / ".gitignore").read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")
        (self.repo / "operator.txt").write_text("unrelated commit\n", encoding="utf-8")
        self.git("add", "--", "operator.txt")
        self.git("commit", "-qm", "unrelated operator commit")
        unrelated = self.git("rev-parse", "HEAD").strip()

        done = self.submit({"paths": [".gitignore"]})
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), unrelated)
        self.assertEqual(nav.current_stage(self.state()), "prepare")
        self.assertIn(".gitignore", self.git("status", "--porcelain=v1", "--untracked-files=all"))

    def test_missing_issued_snapshot_never_reseeds_from_the_current_tree(self) -> None:
        self.open_prepare()
        snapshot = self.run_dir / "preparation.md"
        self.assertTrue(snapshot.is_file(), "the first prepare packet must persist its entry snapshot")
        snapshot.unlink()
        (self.repo / ".gitignore").write_text(
            (self.repo / ".gitignore").read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")
        prior_ignore_commit = self.git("log", "-1", "--format=%H", "--", ".gitignore").strip()

        done = self.submit({"paths": [".gitignore"]})
        output = done.stdout + done.stderr
        self.assertEqual(self.git("log", "-1", "--format=%H", "--", ".gitignore").strip(), prior_ignore_commit)
        self.assertIn(".gitignore", self.git("status", "--porcelain=v1", "--untracked-files=all"))
        self.assertIn("preparation", output.lower())
        self.assertTrue("unknown" in output.lower() or "snapshot" in output.lower(), output)

    def test_symlinked_prepare_record_is_not_followed_for_ownership(self) -> None:
        self.open_prepare()
        snapshot = self.run_dir / "preparation.md"
        saved = self.run_dir / "saved-preparation.md"
        original = snapshot.read_bytes()
        snapshot.unlink()
        saved.write_bytes(original)
        snapshot.symlink_to(saved.name)
        (self.repo / ".gitignore").write_text(
            (self.repo / ".gitignore").read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")
        prior_ignore_commit = self.git("log", "-1", "--format=%H", "--", ".gitignore").strip()

        done = self.submit({"paths": [".gitignore"]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(saved.read_bytes(), original)
        self.assertEqual(self.git("log", "-1", "--format=%H", "--", ".gitignore").strip(), prior_ignore_commit)
        self.assertIn(".gitignore", self.git("status", "--porcelain=v1", "--untracked-files=all"))

    def test_knowledge_home_uses_its_existing_close_after_phase_commit(self) -> None:
        self.open_prepare()
        knowledge_path = self.repo / "docs/shiploop/prepare-knowledge.md"
        knowledge_path.parent.mkdir(parents=True, exist_ok=True)
        knowledge_path.write_text("A separate knowledge-home close owns this file.\n", encoding="utf-8")
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "prepare-output.tmp\n", encoding="utf-8")

        done = self.submit({"paths": [".gitignore", "docs/shiploop/prepare-knowledge.md"]})
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        base = lint.read_base(self.run_dir, "W1")
        self.assertIsNotNone(base)
        prepare_commit = self.git("log", "-1", "--format=%H", "--", ".gitignore").strip()
        self.assertEqual(base["head"], prepare_commit)
        self.assertEqual(self.git("show", "--format=", "--name-only", prepare_commit).splitlines(), [".gitignore"])
        knowledge_commit = self.git("log", "-1", "--format=%H", "--", "docs/shiploop/prepare-knowledge.md").strip()
        self.assertTrue(knowledge_commit, "the existing knowledge-home close still owns knowledge-home changes")
        self.assertNotEqual(knowledge_commit, prepare_commit,
                            "knowledge-home files retain the later, separate close behavior")
        self.assertIn("Knowledge-home files remain under the existing separate knowledge close.",
                      done.stdout + done.stderr)


class PreparationRecoveryTests(unittest.TestCase):
    """Unrecoverable repository entry states stay unknown instead of widening to the whole tree."""

    def test_non_git_and_unborn_entries_are_not_owned(self) -> None:
        # Keep this import lazy so a missing helper cannot mask the real CLI path tests above.
        import shiploop_preparation as preparation  # noqa: PLC0415

        with tempfile.TemporaryDirectory(prefix="shiploop-preparation-recovery-") as temp:
            root = Path(temp)
            for label in ("non-git", "unborn"):
                with self.subTest(label=label):
                    repo = root / label
                    repo.mkdir()
                    (repo / "candidate.txt").write_text("must not be adopted\n", encoding="utf-8")
                    if label == "unborn":
                        subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
                    run_dir = root / (label + "-run")
                    state = {"run_id": "run-" + label, "repo": str(repo), "execution_mode": "navigator"}
                    preparation.capture_entry(run_dir, state, "prepare_1")
                    record = store.read_record(run_dir / "preparation.md")
                    self.assertEqual(record["status"], "unknown")
                    self.assertFalse(record.get("entry_head"))
                    self.assertTrue((repo / "candidate.txt").is_file())
                    if label == "unborn":
                        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "HEAD"],
                                              capture_output=True, check=False)
                        self.assertNotEqual(head.returncode, 0)
                    else:
                        self.assertFalse((repo / ".git").exists())


if __name__ == "__main__":
    unittest.main()
