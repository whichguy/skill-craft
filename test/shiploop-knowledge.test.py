#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's repository knowledge home (docs/shiploop/) and its closes.

Real Git repositories in temporary directories.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(ROOT / "test"))
import shiploop_git  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_knowledge_support as support  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


class KnowledgeTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-knowledge-")
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve() / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "k@example.invalid")
        git(self.repo, "config", "user.name", "K")
        (self.repo / "app.py").write_text("x = 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        self.state = {"repo": str(self.repo), "prompt": "Add a Fleet command tab to the Battleship game.",
                      "run_id": "nav-0123456789abcdef"}

    def test_feature_directory_and_stage_lines(self) -> None:
        self.assertEqual(knowledge.feature_dir(self.state),
                         "docs/shiploop/features/add-a-fleet-command-tab-to-abcdef")
        lines = "\n".join(knowledge.stage_lines(self.state, "spec"))
        self.assertIn(str(self.repo / "docs/shiploop/README.md"), lines)
        self.assertIn(str(self.repo / "docs/shiploop/spec.md"), lines)
        self.assertIn("ShipLoop refuses a spec that loses an earlier ID", lines)
        self.assertNotIn("On done ShipLoop checks", lines)
        self.assertIn("On done ShipLoop checks these files", "\n".join(knowledge.stage_lines(self.state, "prepare")))

    def test_a_close_needs_its_files_and_commits_only_the_home(self) -> None:
        refusal = knowledge.check(self.state, "prepare")
        self.assertIn("Before prepare is done, write:", refusal)
        self.assertIn("docs/shiploop/spec.md", refusal)
        support.write(self.state)
        (self.repo / "app.py").write_text("x = 2\n")
        git(self.repo, "add", "app.py")  # the user's own staged work stays out of the knowledge commit
        self.assertEqual(knowledge.check(self.state, "prepare"), "")
        commit = knowledge.commit(self.state, "prepare").commit
        self.assertTrue(commit)
        files = git(self.repo, "show", "--name-only", "--format=%s", commit).split("\n")
        self.assertEqual(files[0], "docs(shiploop): record add-a-fleet-command-tab-to-abcdef knowledge at prepare")
        self.assertTrue(all(name.startswith("docs/shiploop/") for name in files[1:] if name))
        self.assertIn("app.py", git(self.repo, "diff", "--cached", "--name-only"))
        self.assertEqual(knowledge.commit(self.state, "test-spec").commit, "")  # nothing changed

    def test_the_living_spec_keeps_every_committed_requirement_id(self) -> None:
        support.write(self.state)
        spec = self.repo / "docs/shiploop/spec.md"
        spec.write_text("# spec\n\nR-1: Place a fleet.\nR-2: Reload keeps the fleet.\n")
        knowledge.commit(self.state, "prepare")
        spec.write_text("# spec\n\nR-1: Place a fleet on a 10x10 board.\nR-3: Show a tab.\n")
        self.assertIn("no longer mentions R-2", knowledge.check(self.state, "release-plan"))
        spec.write_text("# spec\n\nR-1: Place a fleet on a 10x10 board.\nR-3: Show a tab.\n\n## Retired\n\n"
                        "R-2: replaced by R-1's board rule.\n")
        self.assertEqual(knowledge.check(self.state, "release-plan"), "")

    def test_release_verify_commits_the_runs_learnings_as_its_message(self) -> None:
        support.write(self.state)
        outcome = self.repo / knowledge.feature_dir(self.state) / "outcome.md"
        outcome.write_text("# outcome\n\n## Learned\n\nlightning__Tab creates no tab.\n\n## Key considerations\n\n")
        refusal = knowledge.check(self.state, "release-verify")
        self.assertIn("'## Key considerations', '## Open for the next run'", refusal)
        outcome.write_text("# outcome\n\n## Learned\n\nlightning__Tab creates no tab.\n\n"
                           "## Key considerations\n\nConfirm tabs with sf org list metadata.\n\n"
                           "## Open for the next run\n\nTC-13 and TC-14 need a person in a browser.\n")
        self.assertEqual(knowledge.check(self.state, "release-verify"), "")
        commit = knowledge.commit(self.state, "release-verify").commit
        body = git(self.repo, "log", "-1", "--format=%B", commit)
        self.assertIn("knowledge at release-verify\n\nLearned\nlightning__Tab creates no tab.", body)
        self.assertIn("Open for the next run\nTC-13 and TC-14 need a person in a browser.", body)

    def test_intake_quotes_the_last_three_commit_messages(self) -> None:
        for number in (1, 2, 3, 4):
            (self.repo / ("f" + str(number))).write_text("x\n")
            git(self.repo, "add", "-A")
            git(self.repo, "commit", "-qm", "change " + str(number), "-m", "Learned: lesson " + str(number) + ".")
        lines = "\n".join(knowledge.stage_lines(self.state, "intake"))
        self.assertIn("Inherited learnings: the last 3 commit messages", lines)
        self.assertIn("  | Learned: lesson 4.", lines)
        self.assertIn("  | Learned: lesson 2.", lines)
        self.assertNotIn("lesson 1.", lines)
        self.assertNotIn("Inherited learnings", "\n".join(knowledge.stage_lines(self.state, "plan")))

    def test_credentials_in_the_home_are_refused(self) -> None:
        support.write(self.state)
        (self.repo / "docs/shiploop/environment.md").write_text("Authorization: Bearer 0123456789abcdefghij\n")
        self.assertIn("docs/shiploop/environment.md:1", knowledge.check(self.state, "prepare"))

    def test_the_workspace_return_keeps_the_home(self) -> None:
        rows = workspace._plan_rows({"docs/shiploop/spec.md": "added", "src/a.py": "added"}, [], [])
        self.assertEqual({row["path"]: row["disposition"] for row in rows},
                         {"docs/shiploop/spec.md": "keep", "src/a.py": "pending"})


class KnowledgeAfterEveryStageTests(KnowledgeTests):
    """P3b: ShipLoop commits the home after any accepted stage that changed it, with the closes' checks."""

    def test_a_non_close_stage_that_changed_the_home_is_committed(self) -> None:
        support.write(self.state)
        knowledge.commit(self.state, "prepare")
        notes = self.repo / "docs/shiploop/environment.md"
        notes.write_text(notes.read_text() + "\nThe service listens on PORT.\n")
        self.assertEqual(knowledge.check(self.state, "integration-verify"), "")
        committed = knowledge.commit(self.state, "integration-verify")
        self.assertTrue(committed.commit)
        self.assertEqual(committed.paths, ["docs/shiploop/environment.md"])
        subject = git(self.repo, "log", "-1", "--format=%s")
        self.assertTrue(subject.endswith("knowledge after integration-verify\n"), subject)
        self.assertEqual(knowledge.commit(self.state, "handoff").commit, "")  # unchanged: no empty commit

    def test_a_non_close_stage_that_drops_an_id_is_refused(self) -> None:
        support.write(self.state)
        spec = self.repo / "docs/shiploop/spec.md"
        spec.write_text("# spec\n\nR-1: Import files.\nR-2: Report totals.\n")
        knowledge.commit(self.state, "prepare")
        spec.write_text("# spec\n\nR-1: Import files.\n")
        self.assertIn("no longer mentions R-2", knowledge.check(self.state, "verify"))

    def test_an_unchanged_home_is_not_checked_outside_a_close(self) -> None:
        self.assertEqual(knowledge.check(self.state, "implement"), "")  # no home at all: nothing to require


class CommitHelperTests(unittest.TestCase):
    """The one commit path (shiploop_git.commit_paths) every ShipLoop commit uses."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-git-")
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve() / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "-c", "user.email=u@example.invalid", "-c", "user.name=U", "commit", "-q",
            "--allow-empty", "-m", "base")

    def test_stages_exactly_the_given_paths_and_names_a_file_that_looks_like_a_secret(self) -> None:
        git(self.repo, "config", "user.email", "u@example.invalid")
        git(self.repo, "config", "user.name", "U")
        (self.repo / "lib.py").write_text("VALUE = 1\n")
        (self.repo / "settings.env").write_text("Authorization: Bearer 0123456789abcdefghij\n")
        (self.repo / "other.txt").write_text("not part of this commit\n")
        committed = shiploop_git.commit_paths(self.repo, ["lib.py", "settings.env"], "feat: lib")
        self.assertEqual(committed.paths, ["lib.py"])
        self.assertEqual(committed.skipped, ["settings.env"])
        self.assertEqual(git(self.repo, "show", "--name-only", "--format=", "HEAD").split(), ["lib.py"])
        status = git(self.repo, "status", "--porcelain")
        self.assertIn("?? settings.env", status)
        self.assertIn("?? other.txt", status)
        notice = shiploop_git.skipped_notice(committed.skipped)
        self.assertIn("settings.env", notice)
        self.assertNotIn("0123456789abcdefghij", notice)

    def test_workspace_identity_only_without_a_configured_identity(self) -> None:
        (self.repo / "a.txt").write_text("a\n")
        env = {"GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
        import os
        from unittest import mock
        with mock.patch.dict(os.environ, env):
            committed = shiploop_git.commit_paths(self.repo, ["a.txt"], "docs: a")
        self.assertEqual(git(self.repo, "log", "-1", "--format=%ae", committed.commit).strip(),
                         "shiploop-workspace@local.invalid")
        git(self.repo, "config", "user.email", "u@example.invalid")
        git(self.repo, "config", "user.name", "U")
        (self.repo / "a.txt").write_text("b\n")
        with mock.patch.dict(os.environ, env):
            again = shiploop_git.commit_paths(self.repo, ["a.txt"], "docs: b")
        self.assertEqual(git(self.repo, "log", "-1", "--format=%ae", again.commit).strip(), "u@example.invalid")

    def test_empty_commit_and_nothing_to_commit(self) -> None:
        git(self.repo, "config", "user.email", "u@example.invalid")
        git(self.repo, "config", "user.name", "U")
        self.assertEqual(shiploop_git.commit_paths(self.repo, ["absent.txt"], "x").commit, "")
        empty = shiploop_git.commit_paths(self.repo, [], "baseline", allow_empty=True)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD").strip(), empty.commit)


if __name__ == "__main__":
    unittest.main()
