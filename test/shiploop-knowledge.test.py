#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's repository knowledge home (docs/shiploop/) and its closes.

Real Git repositories in temporary directories.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import time
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(ROOT / "test"))
import shiploop_git  # noqa: E402
import shiploop_lessons as commit_lessons  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_knowledge_support as support  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


class HomeFixture(unittest.TestCase):
    """A real Git repository holding one commit, and the state of a run in it; no tests of its own."""

    def setUp(self) -> None:
        # Real-git tests must not read the machine's Git configuration: a CI runner's global config carries git-lfs
        # filters, which the workspace refuses (as in shiploop-workspace and shiploop-test-loop).
        isolated = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        isolated.start()
        self.addCleanup(isolated.stop)
        temp = tempfile.TemporaryDirectory(prefix="shiploop-knowledge-")
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name).resolve() / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "k@example.invalid")
        git(self.repo, "config", "user.name", "K")
        git(self.repo, "config", "commit.gpgsign", "false")
        git(self.repo, "config", "core.hooksPath", os.devnull)
        (self.repo / "app.py").write_text("x = 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        self.state = {"repo": str(self.repo), "prompt": "Add a Fleet command tab to the Battleship game.",
                      "run_id": "nav-0123456789abcdef"}


class KnowledgeTests(HomeFixture):
    def test_feature_directory_and_stage_lines(self) -> None:
        self.assertEqual(knowledge.feature_dir(self.state),
                         "docs/shiploop/features/add-a-fleet-command-tab-to-abcdef")
        lines = "\n".join(knowledge.stage_lines(self.state, "spec"))
        self.assertIn(str(self.repo / "docs/shiploop/README.md"), lines)
        self.assertIn(str(self.repo / "docs/shiploop/spec.md"), lines)
        self.assertIn("ShipLoop refuses a spec that loses an earlier ID", lines)
        self.assertNotIn("On done ShipLoop checks", lines)
        self.assertIn("On done ShipLoop checks these files", "\n".join(knowledge.stage_lines(self.state, "prepare")))

    def test_a_file_written_before_a_close_names_the_next_close_that_requires_it(self) -> None:
        self.assertEqual(knowledge.next_close("plan", "{feature}/plan.md"), "prepare")
        self.assertEqual(knowledge.next_close("discovery", "environment.md"), "prepare")
        self.assertEqual(knowledge.next_close("step-plan", "{feature}/plan.md"), "test-spec")  # prepare is behind it
        self.assertEqual(knowledge.next_close("system-test-author", "{feature}/system-tests.md"), "release-plan")
        self.assertIsNone(knowledge.next_close("plan", "{feature}/outcome.md.nope"))
        self.assertEqual(knowledge.required_earlier("prepare"),
                         ("README.md", "spec.md", "test-strategy.md", "architecture.md", "{feature}/spec.md",
                          "{feature}/plan.md"))
        lines = "\n".join(knowledge.stage_lines(self.state, "prepare"))
        self.assertIn("Written by earlier stages; ShipLoop refuses prepare if any is missing or empty: "
                      + str(self.repo / "docs/shiploop/README.md"), lines)
        self.assertIn("This stage keeps these up to date (create them if missing): "
                      + str(self.repo / "docs/shiploop/environment.md") + ".", lines)

    def test_a_close_packet_lists_every_file_its_refusal_names(self) -> None:
        # The refusal is the gate's own text: whatever it asks for must already be in the stage's packet.
        for stage in knowledge.CLOSES:
            with self.subTest(stage):
                named = [line[2:] for line in knowledge.check(self.state, stage).splitlines() if line.startswith("- /")]
                self.assertTrue(named)
                listed = "\n".join(knowledge.stage_lines(self.state, stage))
                for path in named:
                    self.assertIn(path, listed)

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

    def test_the_missing_file_refusal_puts_the_action_and_the_absolute_paths_on_its_first_line(self) -> None:
        # A model reads a refusal through `head -1` or `cut -c1-250`: the first line must say what to write, and where.
        # Absolute, because the shell's directory is the original checkout while the files belong in the execution one
        # (a relative path written from there lands in the user's repository).  The `- /abs` lines stay: the callback
        # contract suite follows them, and so does a model that reads on.
        refusal = knowledge.check(self.state, "prepare")
        lines = refusal.splitlines()
        feature = knowledge.feature_dir(self.state)
        names = [knowledge.HOME + "/README.md", knowledge.HOME + "/spec.md", knowledge.HOME + "/environment.md",
                 knowledge.HOME + "/test-strategy.md", knowledge.HOME + "/architecture.md", feature + "/spec.md",
                 feature + "/plan.md"]
        absolute = [str(self.repo / name) for name in names]
        self.assertEqual(lines[0], "Before prepare is done, write: " + ", ".join(absolute))
        self.assertIn(absolute[0], lines[0][:250])
        self.assertNotIn(" docs/shiploop/", lines[0])  # no relative path that could be written from the wrong directory
        self.assertEqual(re.findall(r"^- (/\S+)$", refusal, re.M), absolute)
        # a first prepare asks for every file at once, the architecture among them: its one hint line is printed once, here too
        self.assertEqual(re.findall(r"^(\S+) holds ", refusal, re.M), ["architecture.md"])
        self.assertIn("keeps this run's planning knowledge in the repository", refusal)
        self.assertTrue(refusal.endswith("See the packet's knowledge-home lines for what each file holds."))

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

    def test_the_repository_index_is_committed_and_screened_with_the_home(self) -> None:
        support.write(self.state)
        knowledge.commit(self.state, "prepare")
        index = self.repo / "SHIPLOOP.md"
        index.write_text("# Knowledge index\n\nSpec: docs/shiploop/spec.md\n")
        self.assertIn("SHIPLOOP.md", "\n".join(knowledge.stage_lines(self.state, "implement")))
        self.assertEqual(knowledge.check(self.state, "implement"), "")
        committed = knowledge.commit(self.state, "implement")
        self.assertEqual(committed.paths, ["SHIPLOOP.md"])
        self.assertEqual(git(self.repo, "status", "--porcelain").strip(), "")
        index.write_text("Authorization: Bearer 0123456789abcdefghij\n")
        self.assertIn("SHIPLOOP.md:1", knowledge.check(self.state, "implement"))
        rows = workspace._plan_rows({"SHIPLOOP.md": "modified"}, [], [])
        self.assertEqual(rows[0]["disposition"], "keep")

    def test_an_unchanged_home_is_not_checked_outside_a_close(self) -> None:
        self.assertEqual(knowledge.check(self.state, "implement"), "")  # no home at all: nothing to require


class ArchitectureTests(HomeFixture):
    """docs/shiploop/architecture.md: a living file that plan and step-plan keep and prepare requires."""

    ARCH = "docs/shiploop/architecture.md"
    DECISIONS = ("# Architecture\n\nNode 22, built-in http, no dependencies.\n\n## Decisions\n\n"
                 "### AD-1 Keep the board in memory\nChoice: a Map per game. Why: no storage is asked for. Status: current.\n\n"
                 "### AD-2 One module per concern\nChoice: rules.js, server.js. Why: tests load rules alone. Status: current.\n\n"
                 "### AD-3 JSON errors\nChoice: {error} bodies. Why: one parser on the page. Status: current.\n")

    def commit_home(self, architecture: str | None = None) -> Path:
        """The whole home written and committed once (a finished earlier run), with this architecture.md."""
        support.write(self.state)
        path = self.repo / self.ARCH
        path.write_text(self.DECISIONS if architecture is None else architecture, encoding="utf-8")
        self.assertTrue(knowledge.commit(self.state, "prepare").commit)
        return path

    def test_the_architecture_is_a_living_file_plan_and_step_plan_keep_and_prepare_requires(self) -> None:
        self.assertEqual(knowledge.ARCHITECTURE, "architecture.md")
        self.assertIn("architecture.md", knowledge.LIVING)
        self.assertIn("architecture.md", knowledge.CLOSES["prepare"])
        self.assertEqual(knowledge.next_close("plan", "architecture.md"), "prepare")
        self.assertIsNone(knowledge.next_close("step-plan", "architecture.md"))  # prepare is behind step-plan
        absolute = str(self.repo / self.ARCH)
        plan = "\n".join(knowledge.stage_lines(self.state, "plan"))
        self.assertRegex(plan, r"keeps these up to date \(create them if missing\): .*" + re.escape(absolute))
        self.assertRegex(plan, r"ShipLoop refuses prepare if any of these is missing or empty: .*" + re.escape(absolute))
        step_plan = [row for row in knowledge.stage_lines(self.state, "step-plan") if "keeps these up to date" in row]
        self.assertIn(absolute, step_plan[0])
        prepare = [row for row in knowledge.stage_lines(self.state, "prepare") if row.startswith("Written by earlier stages")]
        self.assertIn(absolute, prepare[0])
        # implement keeps it up to date since task A2 (a deviation recorded as an AD-<n>); verify reads it and writes nothing
        for stage in ("intake", "discovery", "spec", "test-strategy", "verify"):
            with self.subTest(stage):
                self.assertNotIn(absolute, "\n".join(knowledge.stage_lines(self.state, stage)))

    def test_the_architecture_is_ordered_after_the_other_living_files_and_before_the_feature_files(self) -> None:
        self.assertEqual(knowledge.CLOSES["prepare"][:5],
                         ("README.md", "spec.md", "environment.md", "test-strategy.md", "architecture.md"))
        self.assertEqual(knowledge.STAGE_FILES["plan"][-1], "architecture.md")  # the printed order of the others is kept
        self.assertEqual(knowledge.STAGE_FILES["step-plan"], ("{feature}/plan.md", "architecture.md"))
        self.assertEqual(knowledge.STAGE_FILES["prepare"], ("environment.md",))  # prepare requires it; plan writes it

    def test_a_home_without_an_architecture_is_refused_at_prepare_naming_only_that_file_and_what_it_holds(self) -> None:
        support.write(self.state)
        (self.repo / self.ARCH).unlink()
        refusal = knowledge.check(self.state, "prepare")
        self.assertEqual(refusal.splitlines()[0], "Before prepare is done, write: " + str(self.repo / self.ARCH))
        self.assertEqual(re.findall(r"^- (/\S+)$", refusal, re.M), [str(self.repo / self.ARCH)])
        # architecture.md is new: a cleared-context model has no other description of it, so the refusal carries one line
        self.assertIn("\narchitecture.md holds " + knowledge.ARCHITECTURE_HOLDS + ".\n", refusal)
        self.assertEqual(re.findall(r"^(\S+) holds ", refusal, re.M), ["architecture.md"])  # no per-file line for the others
        self.assertTrue(refusal.endswith("See the packet's knowledge-home lines for what each file holds."))
        # a refusal that asks for nothing about the architecture says nothing about it
        (self.repo / self.ARCH).write_text("# Architecture\n\nA script.\n")
        (self.repo / "docs/shiploop/environment.md").unlink()
        self.assertNotIn("architecture.md holds", knowledge.check(self.state, "prepare"))

    def test_the_wording_of_what_the_file_holds_keeps_runtime_in_the_environment_and_names_the_decision_ids(self) -> None:
        holds = knowledge.ARCHITECTURE_HOLDS
        self.assertTrue(holds.startswith("the stack (language, frameworks, dependencies and why)"), holds)
        self.assertIn("AD-<n>", holds)
        self.assertIn("'## Decisions'", holds)
        self.assertIn("'## Superseded'", holds)
        self.assertNotIn("runtime", holds)  # runtime versions and working commands are environment.md's: one home

    def test_an_empty_or_blank_architecture_is_missing(self) -> None:
        support.write(self.state)
        for body in ("", "  \n\n\t\n"):
            with self.subTest(body=body):
                (self.repo / self.ARCH).write_text(body)
                self.assertIn(str(self.repo / self.ARCH), knowledge.check(self.state, "prepare").splitlines()[0])
        (self.repo / self.ARCH).write_text("# Architecture\n\nA script, no decisions yet.\n")
        self.assertEqual(knowledge.check(self.state, "prepare"), "")  # no decision ID is required: only the file

    def test_a_first_run_has_nothing_to_drop(self) -> None:
        support.write(self.state)
        (self.repo / self.ARCH).write_text(self.DECISIONS)
        self.assertEqual(knowledge.check(self.state, "prepare"), "")  # HEAD holds no architecture.md yet
        (self.repo / self.ARCH).write_text("# Architecture\n\nRewritten before anything was committed.\n")
        self.assertEqual(knowledge.check(self.state, "prepare"), "")

    def test_a_later_version_that_loses_a_decision_id_is_refused_with_the_fix_the_file_and_the_command_on_line_1(self) -> None:
        path = self.commit_home()
        path.write_text(self.DECISIONS.replace("### AD-2 One module per concern", "### One module per concern")
                        .replace("### AD-3 JSON errors", "### JSON errors"))
        for stage in ("prepare", "step-plan", "release-plan"):
            with self.subTest(stage):
                first, second = knowledge.check(self.state, stage).split("\n")  # exactly two lines
                self.assertEqual(first, "Restore the lost AD-<n> in " + str(path) + " or move it under 'Superseded', "
                                 "then run the same complete command again.")
                self.assertNotIn("AD-2", first)  # a long list can never push the fix out of the first line
                self.assertEqual(second, "The architecture no longer mentions AD-2, AD-3. Keep every earlier decision ID: "
                                 "modify it in place, or move it under a 'Superseded' heading with the reason.")
        # The improve-complete route has its own sequence: a review's edit is committed with improve-commit before the import,
        # and line 2 (the IDs and the 'Superseded' reason) is the complete route's.
        first, second = knowledge.check(self.state, "step-plan", command="improve-complete").split("\n")
        self.assertEqual(first, "Restore AD-<n> in " + str(path)
                         + "; if the review changed it, improve-commit it; then run improve-complete.")
        self.assertNotIn("AD-2", first)
        self.assertIn("The architecture no longer mentions AD-2, AD-3. Keep every earlier decision ID: modify it in place, "
                      "or move it under a 'Superseded' heading with the reason.", second)

    # architecture.md sits 125 to 137 characters from the root in the saved E2E execution checkouts (the six
    # /Users/dadleet/e2e-runs/<date>/<case>/.shiploop-runs/<run>/worktree paths of 2026-10-1x), and the CLI prefixes line 1.
    REAL_WIDTHS = range(125, 138)
    PREFIX = "ShipLoop navigator: "

    def at_width(self, line: str, path: Path, width: int) -> tuple[str, str]:
        """(the CLI's line 1, the path it shows): the real path swapped for a synthetic one of exactly ``width`` characters.

        The cut a model reads through depends on the length of the path, which is the machine's (a temporary directory under
        a long ``TMPDIR`` made the earlier version of this test fail); the template around the path is the product's.
        """
        self.assertEqual(line.count(str(path)), 1)
        tail = "/" + self.ARCH
        synthetic = "/" + "w" * (width - len(tail) - 1) + tail
        self.assertEqual(len(synthetic), width)
        return self.PREFIX + line.replace(str(path), synthetic), synthetic

    def test_a_cut_of_line_1_at_250_characters_keeps_the_fix_the_file_and_the_commands_at_every_real_checkout_width(self) -> None:
        """A model reads a refusal through `cut -c1-250`: what survives is the fix, the whole path and the route's commands."""
        path = self.commit_home("".join("AD-" + str(n) + " choice\n" for n in range(1, 13)))  # twelve decisions to lose
        path.write_text("# Architecture\n")
        for command in ("complete", "improve-complete"):
            line_1 = knowledge.check(self.state, "step-plan", command=command).splitlines()[0]
            for width in self.REAL_WIDTHS:
                with self.subTest(command=command, width=width):
                    line, shown = self.at_width(line_1, path, width)
                    kept = line[:250]
                    if command == "complete":
                        wanted = ("Restore the lost AD-<n> in " + shown
                                  + " or move it under 'Superseded', then run the same complete command")
                    else:
                        wanted = ("Restore AD-<n> in " + shown + "; if the review changed it, improve-commit it; "
                                  "then run improve-complete.")
                    self.assertIn(wanted, kept)
                    self.assertNotIn("AD-12", kept)  # the IDs are on line 2, in full
        self.assertIn("AD-12.", knowledge.check(self.state, "step-plan").splitlines()[1])  # every ID, no cap

    def test_a_credential_looking_line_is_refused_with_the_place_the_fix_and_the_command_on_line_1(self) -> None:
        """architecture.md records auth shapes the screen flags ('Password: bcrypt', 'SECRET_KEY = os.environ[...]'), and the
        screen reads every home file: a model that sees only line 1 must know where, what to write instead, and what to run."""
        support.write(self.state)
        path = self.repo / self.ARCH
        path.write_text("# Architecture\n\nPassword: bcrypt, cost 12\nSECRET_KEY = os.environ['SECRET_KEY']\n"
                        "token = get_token()\nAPI keys come from the vault\n")
        environment = self.repo / "docs/shiploop/environment.md"
        environment.write_text("# environment\nAuthorization: Bearer 0123456789abcdefghij\n")
        places = [str(path) + ":3", str(path) + ":4", str(path) + ":5", str(environment) + ":2"]  # absolute, in walk order
        for command in ("complete", "improve-complete"):
            with self.subTest(command):
                refusal = knowledge.check(self.state, "prepare", command=command)
                lines = refusal.splitlines()
                self.assertEqual(lines[0], "Reword " + places[0] + " to name an alias, not a value or an assignment; "
                                 "then run the same " + command + " command again.")
                self.assertIn("look like credentials", lines[1])  # the words the refusal has always had, for counting them
                self.assertEqual(re.findall(r"^- (/\S+:\d+)$", refusal, re.M), places)  # every place, none capped
                for text in ("bcrypt", "get_token", "0123456789", "os.environ"):
                    self.assertNotIn(text, refusal)  # places, never the text
        # The improve route's commit step is named too, once: its first line keeps the room for the path.
        self.assertEqual(sum("improve-commit" in line for line in knowledge.check(self.state, "prepare").splitlines()), 0)
        improve = knowledge.check(self.state, "prepare", command="improve-complete").splitlines()
        self.assertEqual(sum("improve-commit" in line for line in improve), 1)
        self.assertIn("improve-commit", improve[-1])
        path.write_text("# Architecture\n\nPasswords are hashed with bcrypt (cost 12).\nThe signing key is read from the "
                        "environment variable SECRET_KEY.\nAPI keys come from the vault\n")
        environment.write_text("# environment\nThe CI token is the alias ci-token.\n")
        self.assertEqual(knowledge.check(self.state, "prepare"), "")  # the reworded lines are accepted

    def test_a_cut_of_the_credential_refusal_at_250_characters_keeps_the_place_the_fix_and_the_command_verb(self) -> None:
        support.write(self.state)
        path = self.repo / self.ARCH
        path.write_text("# Architecture\n\nPassword: bcrypt, cost 12\n")
        for command in ("complete", "improve-complete"):
            line_1 = knowledge.check(self.state, "prepare", command=command).splitlines()[0]
            for width in self.REAL_WIDTHS:
                with self.subTest(command=command, width=width):
                    line, shown = self.at_width(line_1, path, width)
                    self.assertIn("Reword " + shown + ":3 to name an alias, not a value or an assignment; then run the same "
                                  + command, line[:250])

    def test_the_spec_refusal_has_the_same_shape_and_still_names_what_it_lost(self) -> None:
        support.write(self.state)
        spec = self.repo / "docs/shiploop/spec.md"
        spec.write_text("# spec\n\nR-1: Place a fleet.\nR-2: Report.\n")
        knowledge.commit(self.state, "prepare")
        spec.write_text("# spec\n\nR-1: Place a fleet.\n")
        first, second = knowledge.check(self.state, "release-plan").split("\n")
        self.assertEqual(first, "Restore the lost R-<n> in " + str(spec) + " or move it under 'Retired', "
                         "then run the same complete command again.")
        self.assertEqual(second, "The living spec no longer mentions R-2. Keep every earlier requirement ID: modify it in "
                         "place, or move it under a 'Retired' heading with the reason.")
        # the route's own sequence is the spec's too (one template for both files)
        again, rest = knowledge.check(self.state, "release-plan", command="improve-complete").split("\n")
        self.assertEqual(again, "Restore R-<n> in " + str(spec)
                         + "; if the review changed it, improve-commit it; then run improve-complete.")
        self.assertEqual(rest, second)

    def test_the_id_prefix_the_wording_names_is_the_prefix_the_check_keeps(self) -> None:
        """ARCHITECTURE_HOLDS tells the model to number decisions AD-<n>; the check must keep exactly those."""
        prefix = re.search(r"\b([A-Z]+)-<n>", knowledge.ARCHITECTURE_HOLDS).group(1)
        path = self.commit_home("# Architecture\n\n" + prefix + "-1 one\n" + prefix + "-2 two\n")
        path.write_text("# Architecture\n\n" + prefix + "-1 one\n")
        self.assertIn("no longer mentions " + prefix + "-2.", knowledge.check(self.state, "step-plan"))

    def test_a_dropped_id_that_is_staged_but_not_committed_is_still_a_drop(self) -> None:
        """The baseline is what HEAD holds: ``git add`` of the lost version must not move it (the index would)."""
        path = self.commit_home()
        path.write_text(self.DECISIONS.replace("### AD-3 JSON errors", "### JSON errors"))
        git(self.repo, "add", self.ARCH)
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only").split(), [self.ARCH])
        self.assertIn("The architecture no longer mentions AD-3.", knowledge.check(self.state, "step-plan"))

    def test_a_decision_moved_under_superseded_or_named_anywhere_in_the_file_is_kept(self) -> None:
        path = self.commit_home()
        path.write_text("# Architecture\n\nNode 22.\n\n## Decisions\n\n### AD-1 Keep the board in memory\nStatus: current.\n\n"
                        "### AD-4 One module per concern, split by layer\nReplaces AD-2.\n\n## Superseded\n\n"
                        "AD-2: split by layer instead (AD-4).\n\nAD-3: the page parses the status code, not a body.\n")
        self.assertEqual(knowledge.check(self.state, "step-plan"), "")
        path.write_text(self.DECISIONS + "\nSee also the earlier choice in AD-3's table row.\n")  # a plain mention counts
        self.assertEqual(knowledge.check(self.state, "step-plan"), "")

    def test_ids_sort_by_number_and_a_deleted_file_loses_them_all(self) -> None:
        many = "# Architecture\n\n" + "".join("AD-" + str(n) + " choice\n" for n in (1, 2, 9, 10, 11))
        path = self.commit_home(many)
        path.write_text("# Architecture\n\nAD-1 choice\n")
        self.assertIn("no longer mentions AD-2, AD-9, AD-10, AD-11.", knowledge.check(self.state, "step-plan"))
        path.unlink()
        self.assertIn("no longer mentions AD-1, AD-2, AD-9, AD-10, AD-11.", knowledge.check(self.state, "step-plan"))

    def test_only_this_files_own_ids_count_in_each_direction(self) -> None:
        path = self.commit_home()
        spec = self.repo / "docs/shiploop/spec.md"
        spec.write_text("# spec\n\nR-1: Place a fleet.\nAD-1 AD-2 AD-3 are cited here as product choices.\n")
        knowledge.commit(self.state, "plan")
        path.write_text("# Architecture\n\nNode 22.\n")  # AD-1..AD-3 live on in the spec's prose, which does not count
        self.assertIn("no longer mentions AD-1, AD-2, AD-3", knowledge.check(self.state, "step-plan"))
        path.write_text(self.DECISIONS + "\nRequirement R-1 drives AD-1.\n")
        spec.write_text("# spec\n\nPlace a fleet.\n")  # R-1 is not kept by the architecture's mention of it
        refusal = knowledge.check(self.state, "step-plan")
        self.assertIn("no longer mentions R-1", refusal)
        self.assertNotIn("architecture", refusal)

    def test_a_token_that_only_contains_ad_n_is_not_a_decision_id(self) -> None:
        """Guard (mutants without a word boundary survived, the trailing one until AD-3a became AD-12a, an ID the committed
        decisions do not already hold): TAD-7, AD-12a and BAD-1 are other things, not decisions."""
        path = self.commit_home(self.DECISIONS + "\nSee TAD-7 (a tag), the AD-12a draft and BAD-1.\n")
        path.write_text(self.DECISIONS)
        self.assertEqual(knowledge.check(self.state, "step-plan"), "")

    def test_a_spec_that_numbers_its_own_product_decisions_d_n_is_not_held_to_them(self) -> None:
        """Real data: one saved run's spec.md names its product decisions D-1..D-6 and cites them from 7 files.  The
        architecture's prefix is AD-, so neither file's check reads the other's numbering."""
        support.write(self.state)
        spec = self.repo / "docs/shiploop/spec.md"
        spec.write_text("# spec\n\nR-1: Place a fleet.\n\n### D-1 Fleet and coordinates\n### D-2 Meanings\n")
        knowledge.commit(self.state, "prepare")
        spec.write_text("# spec\n\nR-1: Place a fleet.\n")
        self.assertEqual(knowledge.check(self.state, "step-plan"), "")

    def test_both_files_dropping_an_id_are_both_named_the_spec_first(self) -> None:
        path = self.commit_home()
        spec = self.repo / "docs/shiploop/spec.md"
        spec.write_text("# spec\n\nR-1: Place a fleet.\nR-2: Report.\n")
        knowledge.commit(self.state, "plan")
        spec.write_text("# spec\n\nR-1: Place a fleet.\n")
        path.write_text("# Architecture\n\nAD-1 only.\n")
        lines = knowledge.check(self.state, "step-plan").splitlines()
        self.assertEqual([line.split(" in ")[0] for line in lines[::2]],
                         ["Restore the lost R-<n>", "Restore the lost AD-<n>"])
        self.assertIn("The living spec no longer mentions R-2.", lines[1])
        self.assertIn("The architecture no longer mentions AD-2, AD-3.", lines[3])

    def test_a_step_plan_that_adds_a_decision_is_committed_with_the_home_and_kept_afterwards(self) -> None:
        path = self.commit_home()
        path.write_text(self.DECISIONS + "\n### AD-4 Retry the fire call once\nChoice: one retry. Status: current.\n")
        self.assertEqual(knowledge.check(self.state, "step-plan"), "")
        committed = knowledge.commit(self.state, "step-plan")
        self.assertEqual(committed.paths, [self.ARCH])
        self.assertTrue(git(self.repo, "log", "-1", "--format=%s").strip().endswith("knowledge after step-plan"))
        path.write_text(self.DECISIONS)  # AD-4 was committed, so a later version may not lose it
        self.assertIn("no longer mentions AD-4", knowledge.check(self.state, "test-spec"))

    def test_the_fixture_writer_satisfies_every_close_it_derives_from_the_closes(self) -> None:
        """Drift guard for test/shiploop_knowledge_support.write: a file added to a close is written without editing it."""
        support.write(self.state)
        for close in knowledge.CLOSES:
            with self.subTest(close):
                if close == "release-verify":
                    continue  # its outcome.md sections are the writer's job, checked by the release-verify test above
                self.assertEqual(knowledge.check(self.state, close), "")
        self.assertTrue((self.repo / self.ARCH).is_file())


class SectionsTests(HomeFixture):
    """The named sections of the four living files, and the stages that keep those files up to date (batch 1012 task A2)."""

    def test_the_four_files_have_their_sections_as_constants_in_the_order_a_reader_meets_them(self) -> None:
        self.assertEqual(knowledge.SECTIONS, {
            "spec.md": ("Requirements", "Non-functional requirements", "Retired"),
            "environment.md": ("Targets and runtimes", "Commands", "Access and accounts", "Platform facts"),
            "architecture.md": ("Stack", "Structure", "Conventions", "Interfaces and boundaries", "Decisions", "Superseded"),
            "test-strategy.md": ("Harnesses and suites", "Commands", "ID convention", "Real-boundary checks"),
        })
        self.assertIn("SECTIONS", knowledge.__all__)

    def test_the_sections_are_plain_words_of_the_living_files_with_no_marker_or_repeat(self) -> None:
        for name, headings in knowledge.SECTIONS.items():
            with self.subTest(name):
                self.assertIn(name, knowledge.LIVING)
                self.assertEqual(len(set(headings)), len(headings))
                for heading in headings:
                    self.assertEqual(heading, heading.strip())
                    self.assertFalse(heading.startswith("#"), heading)  # a packet adds the '## ' it quotes

    def test_the_architecture_wording_and_its_sections_are_one_list(self) -> None:
        holds, sections = knowledge.ARCHITECTURE_HOLDS, knowledge.SECTIONS[knowledge.ARCHITECTURE]
        for quoted in re.findall(r"'## ([^']+)'", holds):  # a heading the wording names is a section
            self.assertIn(quoted, sections)
        self.assertEqual(re.findall(r"'## ([^']+)'", holds), ["Decisions", "Superseded"])
        for heading in sections:  # and every section is a thing the wording says the file holds
            self.assertIn(heading.lower(), holds.lower())

    def test_every_stage_files_key_is_a_real_stage_and_every_name_a_living_or_feature_file(self) -> None:
        """A future change to the graph cannot leave a writer entry on a stage that no longer exists."""
        for stage in knowledge.STAGE_FILES:
            self.assertIn(stage, stage_spec.STAGES)
        for stage in knowledge.CLOSES:
            self.assertIn(stage, stage_spec.STAGES)
        for stage, names in knowledge.STAGE_FILES.items():
            for name in names:
                with self.subTest(stage=stage, name=name):
                    self.assertTrue(name in knowledge.LIVING or name.startswith("{feature}/"), name)

    # The stages that find commands, facts and decisions keep these files up to date (task A2, the 8-stage inner loop).
    WRITERS = {"research": ("environment.md",),
               "validate-existing": ("environment.md",),
               "implement": ("environment.md", "architecture.md"),
               "test": ("environment.md",),
               "carry-forward": ("architecture.md", "environment.md")}

    def test_the_stages_that_discover_commands_facts_and_decisions_keep_the_files_up_to_date(self) -> None:
        for stage, names in self.WRITERS.items():
            with self.subTest(stage):
                self.assertEqual(knowledge.STAGE_FILES[stage], names)
                expected = ("This stage keeps these up to date (create them if missing): "
                            + ", ".join(str(self.repo / knowledge.HOME / name) for name in names) + ".")
                self.assertIn(expected, knowledge.stage_lines(self.state, stage))

    def test_verify_reads_the_architecture_and_writes_nothing_and_the_planning_entries_are_unchanged(self) -> None:
        self.assertNotIn("verify", knowledge.STAGE_FILES)
        self.assertFalse([row for row in knowledge.stage_lines(self.state, "verify") if "keeps these up to date" in row])
        self.assertEqual(knowledge.STAGE_FILES["plan"], ("{feature}/plan.md", "README.md", "architecture.md"))
        self.assertEqual(knowledge.STAGE_FILES["step-plan"], ("{feature}/plan.md", "architecture.md"))
        self.assertEqual(knowledge.STAGE_FILES["prepare"], ("environment.md",))
        self.assertEqual(knowledge.STAGE_FILES["test-spec"], ("{feature}/test-spec.md",))
        self.assertEqual(knowledge.CLOSES["prepare"][:5],
                         ("README.md", "spec.md", "environment.md", "test-strategy.md", "architecture.md"))

    def test_a_writer_before_a_close_that_requires_its_file_names_that_close_and_one_after_every_close_names_none(self) -> None:
        # research feeds the prepare close; the inner stages feed the release-plan close (environment.md); architecture.md is
        # required only at prepare, which is behind every inner stage, so implement and carry-forward promise no close for it.
        research = knowledge.stage_lines(self.state, "research")
        self.assertIn("ShipLoop refuses prepare if any of these is missing or empty: "
                      + str(self.repo / "docs/shiploop/environment.md") + ".", research)
        for stage in ("validate-existing", "implement", "test", "carry-forward"):
            with self.subTest(stage):
                lines = knowledge.stage_lines(self.state, stage)
                self.assertIn("ShipLoop refuses release-plan if any of these is missing or empty: "
                              + str(self.repo / "docs/shiploop/environment.md") + ".", lines)
                self.assertFalse([row for row in lines if "ShipLoop refuses prepare" in row])


class SectionNoticeTests(HomeFixture):
    """knowledge.section_notices(state, stage): a counted notice, at the closes, for a named section a living file lacks."""

    HOME = "docs/shiploop/"

    def put(self, name: str, text: str) -> Path:
        path = self.repo / self.HOME / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    @staticmethod
    def full(name: str) -> str:
        """A file with every one of its sections, each with a line of text."""
        return "# " + name + "\n\n" + "".join("## " + heading + "\n\nSome text.\n\n" for heading in knowledge.SECTIONS[name])

    def put_full_home(self) -> None:
        for name in knowledge.SECTIONS:
            self.put(name, self.full(name))

    def notices(self, stage: str = "prepare") -> list:
        return knowledge.section_notices(self.state, stage)

    def test_a_home_with_every_section_gives_no_notice_at_any_close(self) -> None:
        self.put_full_home()
        for close in knowledge.CLOSES:
            with self.subTest(close):
                self.assertEqual(knowledge.section_notices(self.state, close), [])

    def test_a_missing_section_is_one_line_with_the_prefix_the_absolute_path_the_heading_and_the_fix(self) -> None:
        path = self.put("environment.md", "# Environment\n\n## Commands\n\nnpm test\n\n## Platform facts\n\nNode 22.\n")
        found = self.notices()
        self.assertEqual(found, [
            "ShipLoop knowledge notice: " + str(path) + " has no 'Targets and runtimes' section; add a '## Targets and "
            "runtimes' section (environment.md has the sections Targets and runtimes, Commands, Access and accounts, Platform "
            "facts), or write 'none' under it when nothing applies.",
            "ShipLoop knowledge notice: " + str(path) + " has no 'Access and accounts' section; add a '## Access and accounts' "
            "section (environment.md has the sections Targets and runtimes, Commands, Access and accounts, Platform facts), "
            "or write 'none' under it when nothing applies."])
        for line in found:
            self.assertTrue(line.startswith(knowledge.NOTICE_PREFIX + str(self.repo)), line)  # the absolute file comes first
            self.assertEqual(line.count(knowledge.NOTICE_PREFIX), 1)

    def test_an_empty_section_is_worded_apart_from_a_missing_one(self) -> None:
        path = self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n", "## Commands\n\n\n"))
        self.assertEqual(self.notices(), [
            "ShipLoop knowledge notice: " + str(path) + ": 'Commands' is empty; write under it (environment.md has the sections "
            "Targets and runtimes, Commands, Access and accounts, Platform facts), or write 'none' when nothing applies."])
        # a heading with only blanks after it, at the end of the file, is empty too; a heading no table names is nobody's concern
        self.put("environment.md", self.full("environment.md").replace("## Platform facts\n\nSome text.\n", "## Platform facts\n \t \n")
                 + "\n## Extras\n")
        found = self.notices()
        self.assertEqual(len(found), 1)
        self.assertIn(": 'Platform facts' is empty; write under it (", found[0])

    def test_a_heading_matches_in_any_case_at_levels_one_to_four_with_words_after_it(self) -> None:
        for title in ("commands", "COMMANDS", "Commands (working)", "Commands: how to run it", "Commands ##", "Commands\t"):
            for marks in ("#", "##", "###", "####"):
                with self.subTest(heading=marks + " " + title):
                    self.put("environment.md", self.full("environment.md").replace("## Commands", marks + " " + title))
                    self.assertEqual(self.notices(), [])

    def test_a_line_that_is_no_heading_or_does_not_start_with_the_name_does_not_count(self) -> None:
        for label, replacement in (("a plain line", "Commands"), ("five marks", "##### Commands"),
                                   ("no space after the marks", "##Commands"), ("the singular", "## Command"),
                                   ("a leading marker", "## **Commands**"), ("the name in the middle", "## Build commands")):
            with self.subTest(label):
                self.put("environment.md", self.full("environment.md").replace("## Commands", replacement))
                self.assertEqual([line.split("notice: ", 1)[1].split(" ", 1)[1][:19] for line in self.notices()],
                                 ["has no 'Commands' s"])

    def test_starts_with_is_a_plain_prefix_so_a_longer_word_still_counts(self) -> None:
        # The rule is "the text starts with the heading", case-insensitive: a plural and a longer word both count.  A prefix can
        # hide a missing section (Structured data for Structure); it cannot raise a notice for a section that is there.
        self.put("test-strategy.md", self.full("test-strategy.md").replace("## ID convention", "## ID conventions"))
        self.assertEqual(self.notices(), [])
        self.put("architecture.md", self.full("architecture.md").replace("## Structure", "## Structured data"))
        self.assertEqual(self.notices(), [])

    def test_a_heading_inside_a_fenced_code_block_is_no_heading_and_a_comment_in_it_does_not_end_the_section(self) -> None:
        fenced = "# Environment\n\n```md\n## Commands\n```\n"
        self.put("environment.md", fenced + "".join("## " + h + "\n\ntext\n\n" for h in knowledge.SECTIONS["environment.md"] if h != "Commands"))
        self.assertEqual([line.split("notice: ", 1)[1].split(" ", 1)[1][:19] for line in self.notices()], ["has no 'Commands' s"])
        # a shell comment under a real heading is body, and a section whose body is only a fence is present
        body = "## Commands\n\n```sh\n# install\nnpm ci\n```\n\n"
        self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n\n", body))
        self.assertEqual(self.notices(), [])
        self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n\n", "## Commands\n\n~~~\n# only a comment\n~~~\n\n"))
        self.assertEqual(self.notices(), [])

    def test_a_section_runs_to_the_next_heading_of_the_same_or_a_higher_level_and_a_deeper_heading_is_body(self) -> None:
        # architecture.md: "## Decisions" whose body is its own "### AD-n" headings is present
        text = self.full("architecture.md").replace("## Decisions\n\nSome text.\n", "## Decisions\n### AD-1 In memory\nWhy.\n")
        self.put("architecture.md", text)
        self.assertEqual(self.notices(), [])
        # the same level ends it
        self.put("architecture.md", self.full("architecture.md").replace("## Decisions\n\nSome text.\n\n", "## Decisions\n\n"))
        self.assertIn("'Decisions' is empty", self.notices()[0])
        self.put("architecture.md", self.full("architecture.md"))
        # a higher level ends it: "### Commands" followed by a "# Next" heading
        self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n\n", "### Commands\n# Next\ntext\n\n"))
        self.assertIn("'Commands' is empty", self.notices()[0])
        # a deeper-than-it heading but a "####" is still body; the next "###" is not
        self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n\n", "### Commands\n#### one\n### two\ntext\n\n"))
        self.assertEqual(self.notices(), [])

    def test_the_first_matching_heading_with_text_makes_the_section_present_and_crlf_files_read_the_same(self) -> None:
        text = self.full("environment.md").replace("## Commands\n\nSome text.\n", "## Commands\n\n## Commands (again)\n\nnpm test\n")
        self.put("environment.md", text)
        self.assertEqual(self.notices(), [])
        self.put("environment.md", self.full("environment.md").replace("\n", "\r\n"))
        self.assertEqual(self.notices(), [])
        self.put("environment.md", self.full("environment.md").replace("\n", "\r\n").replace("## Commands\r\n\r\nSome text.\r\n", "## Commands\r\n\r\n"))
        self.assertIn("'Commands' is empty", self.notices()[0])

    def test_only_a_close_gives_a_notice_and_every_close_gives_the_same_lines(self) -> None:
        self.put("environment.md", "# Environment\n\nNode 22.\n")
        for stage in ("intake", "plan", "step-plan", "implement", "verify", "handoff", "not-a-stage"):
            with self.subTest(stage):
                self.assertEqual(knowledge.section_notices(self.state, stage), [])
        for close in knowledge.CLOSES:
            with self.subTest(close):
                self.assertEqual(knowledge.section_notices(self.state, close), self.notices())
        self.assertEqual(len(self.notices()), len(knowledge.SECTIONS["environment.md"]))

    def test_a_file_that_is_absent_blank_or_not_a_file_gives_no_notice_and_the_other_files_still_do(self) -> None:
        self.assertEqual(self.notices(), [])  # nothing written: the close's own refusal asks for the files
        self.put("spec.md", "  \n\t\n")
        (self.repo / self.HOME / "environment.md").mkdir()
        self.put("architecture.md", "# Architecture\n\nA script.\n")
        names = {line.split("notice: ", 1)[1].split(" ", 1)[0] for line in self.notices()}
        self.assertEqual(names, {str(self.repo / self.HOME / "architecture.md")})
        self.assertEqual(len(self.notices()), len(knowledge.SECTIONS["architecture.md"]))

    def test_a_file_that_cannot_be_read_gives_no_notice_and_never_raises(self) -> None:
        self.put_full_home()
        (self.repo / self.HOME / "environment.md").write_text("# Environment\n\nNode 22.\n")
        with mock.patch.object(Path, "read_text", side_effect=PermissionError("denied")):
            self.assertEqual(self.notices(), [])
        # filled when the check looks, unreadable when the notice reads (a file changed between the two reads)
        reads = iter([OSError("gone")])

        def flaky(path: Path, *args, **kwargs) -> str:
            raise next(reads, OSError("gone"))

        with mock.patch.object(knowledge, "_filled", return_value=True), mock.patch.object(Path, "read_text", flaky):
            self.assertEqual(self.notices(), [])
        # bytes that are not UTF-8 read with replacement characters, like every other read of the home
        (self.repo / self.HOME / "environment.md").write_bytes(b"\xff\xfe\n## Commands\n\nok\xff\n")
        self.assertEqual(len(self.notices()), len(knowledge.SECTIONS["environment.md"]) - 1)

    def test_each_file_is_read_for_its_own_sections_in_the_order_of_the_table(self) -> None:
        for name in knowledge.SECTIONS:
            self.put(name, "# " + name + "\n\nProse with no heading.\n")
        found = self.notices()
        self.assertEqual(len(found), sum(len(headings) for headings in knowledge.SECTIONS.values()))
        expected = [(str(self.repo / self.HOME / name), heading) for name, headings in knowledge.SECTIONS.items() for heading in headings]
        self.assertEqual([(line.split("notice: ", 1)[1].split(" ", 1)[0], re.search(r"has no '([^']+)' section", line).group(1))
                          for line in found], expected)
        # the headings of one file do not satisfy another: "Commands" is in two files, and each is read for itself
        self.put("test-strategy.md", self.full("environment.md"))
        self.assertEqual(len([line for line in self.notices() if "test-strategy.md" in line]), 3)

    def test_the_architecture_lines_say_what_the_file_holds_in_the_words_of_the_one_constant(self) -> None:
        self.put("architecture.md", "# Architecture\n\nA script.\n")
        found = self.notices()
        self.assertEqual(len(found), 6)
        for line in found:
            self.assertIn("(architecture.md holds " + knowledge.ARCHITECTURE_HOLDS + ")", line)
        self.assertTrue(found[0].endswith("or write 'none' under it when nothing applies."))

    def test_it_reads_files_only_runs_no_process_and_writes_nothing(self) -> None:
        self.put("environment.md", "# Environment\n\nNode 22.\n")
        before = sorted((p.relative_to(self.repo).as_posix(), p.read_bytes()) for p in self.repo.rglob("*") if p.is_file() and ".git/" not in p.as_posix())
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("no process may run")):
            self.assertTrue(self.notices())
        after = sorted((p.relative_to(self.repo).as_posix(), p.read_bytes()) for p in self.repo.rglob("*") if p.is_file() and ".git/" not in p.as_posix())
        self.assertEqual(before, after)

    def test_the_prefix_is_fixed_so_one_grep_counts_the_lines_and_the_other_knowledge_lines_do_not_match_it(self) -> None:
        self.assertEqual(knowledge.NOTICE_PREFIX, "ShipLoop knowledge notice: ")
        self.assertIn("NOTICE_PREFIX", knowledge.__all__)
        self.assertIn("section_notices", knowledge.__all__)
        self.put("environment.md", "# Environment\n\nNode 22.\n")
        self.assertEqual(len(re.findall(r"^ShipLoop knowledge notice: ", "\n".join(self.notices()), re.M)), 4)
        self.assertIsNone(re.match(r"^ShipLoop knowledge notice: ", "ShipLoop knowledge: committed the removal of the feature spec"))

    def test_the_outcome_section_reader_keeps_its_levels_one_to_three_and_its_flat_bodies(self) -> None:
        """The learnings reader shares the heading syntax with the notice and must read exactly what it read before."""
        text = "# Title\nintro\n## Learned\nA\n#### deeper\nB\n### Open\nC\n##### five\nD\n"
        self.assertEqual(knowledge._sections(text), {"Title": "intro", "Learned": "A\n#### deeper\nB", "Open": "C\n##### five\nD"})


class GroundingTests(HomeFixture):
    """knowledge.grounding(state): what an inner stage reads before it decides, as labelled absolute paths."""

    def write_all(self) -> dict:
        support.write(self.state)
        feature = knowledge.feature_dir(self.state)
        return {"living spec": self.repo / "docs/shiploop/spec.md", "feature spec": self.repo / feature / "spec.md",
                "environment": self.repo / "docs/shiploop/environment.md",
                "architecture": self.repo / "docs/shiploop/architecture.md",
                "test strategy": self.repo / "docs/shiploop/test-strategy.md"}

    def test_the_labels_their_order_and_the_absolute_paths_in_the_execution_checkout(self) -> None:
        expected = self.write_all()
        self.assertEqual(knowledge.GROUNDING_LABELS, ("living spec", "feature spec", "environment", "architecture", "test strategy"))
        found = knowledge.grounding(self.state)
        self.assertEqual([label for label, _ in found], list(knowledge.GROUNDING_LABELS))
        self.assertEqual(dict(found), expected)
        for _, path in found:
            self.assertTrue(path.is_absolute() and path.is_file())
            self.assertTrue(str(path).startswith(str(self.repo) + "/"))

    def test_a_missing_empty_or_blank_file_is_absent_and_the_rest_keep_their_order(self) -> None:
        expected = self.write_all()
        expected["environment"].unlink()
        expected["feature spec"].write_text("")
        expected["test strategy"].write_text(" \n\t\n")
        self.assertEqual([label for label, _ in knowledge.grounding(self.state)], ["living spec", "architecture"])
        expected["architecture"].unlink()
        self.assertEqual(knowledge.grounding(self.state), [("living spec", expected["living spec"])])

    def test_an_absent_home_a_directory_in_a_files_place_and_an_unreadable_file_give_nothing(self) -> None:
        self.assertEqual(knowledge.grounding(self.state), [])
        expected = self.write_all()
        expected["architecture"].unlink()
        expected["architecture"].mkdir()
        self.assertNotIn("architecture", dict(knowledge.grounding(self.state)))
        expected["environment"].chmod(0)
        self.addCleanup(expected["environment"].chmod, 0o644)
        if os.access(expected["environment"], os.R_OK):  # a superuser reads it anyway: nothing unreadable to test
            return
        self.assertNotIn("environment", dict(knowledge.grounding(self.state)))

    def test_the_feature_file_is_this_runs_not_an_earlier_runs(self) -> None:
        expected = self.write_all()
        earlier = dict(self.state, run_id="nav-ffffffffffffff0001", prompt="An earlier request.")
        other = self.repo / knowledge.feature_dir(earlier) / "spec.md"
        other.parent.mkdir(parents=True)
        other.write_text("R-1: earlier.\n")
        self.assertEqual(dict(knowledge.grounding(self.state))["feature spec"], expected["feature spec"])
        self.assertEqual(dict(knowledge.grounding(earlier))["feature spec"], other)

    def test_it_runs_no_git_writes_nothing_and_needs_no_checkout(self) -> None:
        self.write_all()
        plain = Path(tempfile.mkdtemp(prefix="shiploop-grounding-plain-"))
        self.addCleanup(shutil.rmtree, plain, ignore_errors=True)
        copy = plain / "repo"
        shutil.copytree(self.repo, copy, ignore=shutil.ignore_patterns(".git"))  # not a checkout at all
        state = dict(self.state, repo=str(copy))

        def listing() -> list:
            return sorted((str(p.relative_to(copy)), p.stat().st_mtime_ns, p.stat().st_size) for p in copy.rglob("*"))

        before = listing()
        with mock.patch.object(knowledge, "_git", side_effect=AssertionError("git")), \
                mock.patch.object(subprocess, "run", side_effect=AssertionError("subprocess")), \
                mock.patch.object(subprocess, "Popen", side_effect=AssertionError("subprocess")):
            found = knowledge.grounding(state)
        self.assertEqual([label for label, _ in found], list(knowledge.GROUNDING_LABELS))
        self.assertEqual(before, listing())

    def test_grounding_and_the_close_agree_on_what_a_present_file_is(self) -> None:
        """One rule (knowledge._filled): the file the close counts as written is the file the packet points at."""
        expected = self.write_all()
        for body in (None, "", " \n", "text\n"):
            with self.subTest(body=body):
                if body is None:
                    expected["architecture"].unlink(missing_ok=True)
                else:
                    expected["architecture"].write_text(body)
                refusal = knowledge.check(self.state, "prepare")
                self.assertEqual("architecture" in dict(knowledge.grounding(self.state)),
                                 str(expected["architecture"]) not in refusal)


FIXTURES = ROOT / "test" / "fixtures" / "commit-contract"
TRAILER = "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
FULL = "3f2a9c1e0b7d4a5c8e6f1a2b3c4d5e6f708192a3"


class LessonsGrammarTests(unittest.TestCase):
    """shiploop_lessons: the one reader of the commit-message grammar (lessons, a remote change, citations)."""

    def test_the_shapes_saved_commits_use_are_read_as_expected(self) -> None:
        expected = json.loads((FIXTURES / "expected.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(expected), sorted(path.name for path in FIXTURES.glob("*.md") if path.name != "README.md"))
        for name, want in expected.items():
            message = (FIXTURES / name).read_text(encoding="utf-8")
            with self.subTest(shape=name):
                self.assertEqual(commit_lessons.lessons(message), want["lessons"])
                self.assertEqual(commit_lessons.remote_change(message), want["remote_change"])

    def test_every_lesson_label_is_read_in_any_case_and_other_labels_are_not(self) -> None:
        for label in ("Key learnings", "Key learning", "Lessons learned", "Lessons", "Learnings", "Learning", "Lesson",
                      "Learned"):
            for spelled in (label, label.upper(), label.lower()):
                with self.subTest(label=spelled):
                    self.assertEqual(commit_lessons.lessons("s\n\n" + spelled + ": reuse the oracle"), "reuse the oracle")
        for text in ("s\n\nKey considerations: x", "s\n\nOpen for the next run: x", "s\n\nWe learned: x",
                     "s\n\nLearned that x", "s\n\nKey learnings (this pass): x",
                     "s\n\nLearned-from: " + FULL + " the log format"):
            with self.subTest(text=text):
                self.assertEqual(commit_lessons.lessons(text), "")

    def test_a_bullet_a_quote_mark_or_a_bold_wrapper_around_the_label_is_tolerated(self) -> None:
        for line in ("- Key learnings: x", "* Key learnings: x", "> Key learnings: x", "**Key learnings:** x",
                     "**Key learnings**: x", "__Key learnings:__ x", "- **Key learnings:** x"):
            with self.subTest(line=line):
                self.assertEqual(commit_lessons.lessons("s\n\n" + line), "x")
        self.assertEqual(commit_lessons.lessons("s\n\n**Key learnings**\nthe text"), "the text")
        # indentation is not one of the tolerated forms
        self.assertEqual(commit_lessons.lessons("s\n\n    Key learnings: x"), "")

    def test_a_section_with_no_words_is_not_a_lesson_but_none_is(self) -> None:
        for text in ("s\n\nKey learnings:", "s\n\nKey learnings: -", "s\n\nKey learnings: ...", "s\n\n## Key learnings\n\n",
                     "s\n\n## Key learnings\n-\n", "s\n\nKey learnings\n\n"):
            with self.subTest(text=text):
                self.assertEqual(commit_lessons.lessons(text), "")
        self.assertEqual(commit_lessons.lessons("s\n\nKey learnings: none"), "none")
        self.assertEqual(commit_lessons.lessons("s\n\nLessons: 0"), "0")

    def test_an_empty_label_takes_the_first_non_blank_line_even_when_it_looks_like_word_colon_text(self) -> None:
        self.assertEqual(commit_lessons.lessons("s\n\nKey learnings:\nPitfall: the board is 0-based\n"),
                         "Pitfall: the board is 0-based")
        self.assertEqual(commit_lessons.lessons("s\n\nKey learnings\n\n\nDecision: use the real port\n"),
                         "Decision: use the real port")
        # ... unless that line is itself one of the known labels: then the section is empty
        for following in ("Remaining work: x", "Changes: x", "Remote change: x", "Learned-from: abcdef1 y", TRAILER):
            with self.subTest(following=following):
                self.assertEqual(commit_lessons.lessons("s\n\nKey learnings:\n" + following + "\n"), "")

    def test_a_colon_or_bare_body_stops_at_a_blank_line_a_heading_a_known_label_or_a_trailer(self) -> None:
        stops = ("\n\nnext paragraph", "\n## Next", "\nRemaining work: y", "\nRemote change: y", "\nLearned-from: abcdef1 y",
                 "\n" + TRAILER, "\n\n" + TRAILER)
        for stop in stops:
            with self.subTest(stop=stop):
                self.assertEqual(commit_lessons.lessons("s\n\nKey learnings: first\nsecond line" + stop), "first\nsecond line")
        # a line that merely looks like a label is body, not a stop
        self.assertEqual(commit_lessons.lessons("s\n\nKey learnings: first\nPitfall: second"), "first\nPitfall: second")

    def test_a_heading_body_spans_blank_lines_and_is_clipped_at_the_trailer_and_at_other_sections(self) -> None:
        self.assertEqual(commit_lessons.lessons("s\n\n## Key learnings\none\n\ntwo\n\n" + TRAILER + "\n"), "one\n\ntwo")
        self.assertEqual(commit_lessons.lessons("s\n\n### Key learnings:\none\n\nLearned-from: abcdef1 y\n\n" + TRAILER),
                         "one")
        self.assertEqual(commit_lessons.lessons("s\n\n## Key learnings\none\nRemote change: staging, purged\n"), "one")
        self.assertEqual(commit_lessons.remote_change("s\n\n## Remote change\nstaging, purged\n\nKey learnings: x\n"),
                         "staging, purged")
        # a four-hash heading is not one of the forms
        self.assertEqual(commit_lessons.lessons("s\n\n#### Key learnings\none\n"), "")
        # a known trailer ends the body wherever it stands, and a section holding only trailers is empty
        self.assertEqual(commit_lessons.lessons("s\n\n## Key learnings\n\nNo-Change-Note: internal helper\n"), "")
        self.assertEqual(commit_lessons.lessons("s\n\n## Key learnings\nthe text\n\nNo-Change-Note: x\nSkill-Craft-Release: y"),
                         "the text")
        self.assertEqual(commit_lessons.lessons("s\n\n## Key learnings\n\nthe text\nNo-Change-Note: x\n"), "the text")
        self.assertEqual(commit_lessons.lessons("Key-learnings: x\n"), "")
        # two signed lines in the last paragraph are trailers, not the lesson
        self.assertEqual(commit_lessons.lessons("s\n\n## Key learnings\n\nSigned-off-by: A <a@x.invalid>\n" + TRAILER), "")

    def test_a_hyphenated_line_that_is_not_a_known_trailer_is_lesson_text_not_a_trailer_block(self) -> None:
        """Fail-first (batch 1012 review): a last paragraph of `Hyphenated-Token: value` lines used to be clipped as the
        trailer block, so a real lesson read as empty and the refusal said the label had no text."""
        for lesson in ("Follow-up: add a test for the empty board next time", "Re-run: rerun the suite after a rename",
                       "Root-cause: the mock hid the seam\nFix-applied: guard the parse", "Cross-check: the log, not the exit code"):
            for text in ("s\n\n## Key learnings\n\n" + lesson + "\n", "s\n\nKey learnings:\n\n" + lesson + "\n",
                         "s\n\nKey learnings\n\n" + lesson + "\n\n" + TRAILER + "\n"):
                with self.subTest(text=text):
                    self.assertEqual(commit_lessons.lessons(text), lesson)
                    self.assertEqual([section.body for section in commit_lessons.sections(text, commit_lessons.LESSON_LABELS)],
                                     [lesson])
        # the lesson stays when a trailer follows it with no blank line between, and each known trailer still ends it
        self.assertEqual(commit_lessons.lessons("s\n\n## Key learnings\n\nRoot-cause: x\nFix-applied: y\n" + TRAILER),
                         "Root-cause: x\nFix-applied: y")
        for trailer in (TRAILER, "Co-authored-by: A <a@x.invalid>", "Signed-off-by: A <a@x.invalid>", "No-Change-Note: x",
                        "Skill-Craft-Release: 1.2.3"):
            with self.subTest(trailer=trailer):
                self.assertEqual(commit_lessons.lessons("s\n\n## Key learnings\n\n" + trailer + "\n"), "")
                self.assertEqual(commit_lessons.lessons("s\n\nKey learnings:\n\nthe text\n" + trailer + "\n"), "the text")

    def test_a_label_word_without_a_colon_does_not_end_a_body_and_neither_does_a_bare_label_line(self) -> None:
        """Pins (batch 1012 review: the mutants that ended a body at any known label word stayed green)."""
        self.assertEqual(commit_lessons.lessons("s\n\nKey learnings:\nReview the logs first"), "Review the logs first")
        self.assertEqual(commit_lessons.lessons("s\n\nKey learnings: first\nPlan to retry\nChanges are small"),
                         "first\nPlan to retry\nChanges are small")
        # a lone label word may be a lesson's own line, so only a label with a colon (or a heading) is a stop
        self.assertEqual(commit_lessons.lessons("s\n\nKey learnings:\n- Plan\n- Review"), "- Plan\n- Review")

    def test_a_label_spelled_with_a_letter_that_folds_onto_ascii_is_no_label_and_never_a_crash(self) -> None:
        """Fail-first: re.IGNORECASE matched dotless i and long s, and the label lookup then raised KeyError."""
        for text in ("s\n\nKey learn\u0131ngs: x", "s\n\nLesson\u017f: x", "s\n\n## Key learn\u0131ngs\nx",
                     "s\n\n\u212aey learnings: x", "s\n\nLearn\u0131ngs\nx"):
            with self.subTest(text=text):
                self.assertEqual(commit_lessons.lessons(text), "")
                self.assertEqual(commit_lessons.sections(text, commit_lessons.LESSON_LABELS), [])
                self.assertEqual(commit_lessons.remote_change(text), "")
        self.assertEqual(commit_lessons.citations("s\n\nLearned-from: abcdef1 x\nLEARNED-FROM: abcdef2 y")[1].token, "abcdef2")

    def test_the_lessons_of_every_section_are_joined_and_a_remote_change_needs_its_own_label(self) -> None:
        message = "s\n\nKey learnings: one\n\nLessons: two\n\nRemote change: staging, purged\n"
        self.assertEqual(commit_lessons.lessons(message), "one\ntwo")
        self.assertEqual(commit_lessons.remote_change(message), "staging, purged")
        self.assertEqual(commit_lessons.remote_change("s\n\nKey learnings: one"), "")
        self.assertEqual(commit_lessons.remote_change("s\n\nRemote change:\n\n"), "")
        sections = commit_lessons.sections(message, ("Key learnings", "Lessons"))
        self.assertEqual([(section.label, section.body) for section in sections], [("Key learnings", "one"), ("Lessons", "two")])

    def test_line_endings_and_a_very_long_line_do_not_matter(self) -> None:
        crlf = "s\r\n\r\nKey learnings:\r\n\r\n- one\r\n\r\n" + TRAILER + "\r\n"
        self.assertEqual(commit_lessons.lessons(crlf), "- one")
        started = time.monotonic()
        commit_lessons.lessons("s\n\nKey learnings" + " " * 200_000 + "x\n" + " " * 200_000 + "\n")
        self.assertLess(time.monotonic() - started, 2.0)

    def test_citations_tolerate_the_spellings_a_model_uses_and_report_their_line(self) -> None:
        message = "\n".join([
            "s", "",
            "Learned-from: " + FULL + " the release-check log format",
            "learned-from: `abcdef1`: the quoted one",
            "- Learned-from: commit abcdef2, the prefix one",
            "Learned-from: [abcdef3] bracketed.",
            "Learned-from: abcdef4",
            "Learned-from:",
            "Learned-from: sk-notacommit what it gave",
            "Key learnings: not a citation Learned-from: abcdef5 mid-line",
        ])
        found = [(c.line, c.token, c.contribution) for c in commit_lessons.citations(message)]
        self.assertEqual(found, [
            (3, FULL, "the release-check log format"), (4, "abcdef1", "the quoted one"),
            (5, "abcdef2", "the prefix one"), (6, "abcdef3", "bracketed."), (7, "abcdef4", ""), (8, "", ""),
            (9, "sk-notacommit", "what it gave")])
        self.assertEqual(commit_lessons.citations("s\n\nLEARNED-FROM: " + FULL[:7] + " x")[0].token, FULL[:7])

    def test_with_full_ids_rewrites_only_the_citation_lines_and_keeps_the_rest(self) -> None:
        message = ("s\n\n## Key learnings\nbody\n\nLearned-from: `abcdef1`: first\nLearned-from: bad second\n\n"
                   + TRAILER + "\n")
        full = {"abcdef1": FULL}
        rewritten = commit_lessons.with_full_ids(message, lambda token: full.get(token, token))
        self.assertEqual(rewritten, message.replace("Learned-from: `abcdef1`: first", "Learned-from: " + FULL + " first"))
        self.assertEqual(commit_lessons.with_full_ids("no citation\n", lambda token: FULL), "no citation\n")
        # a rewritten message is read the same way again
        self.assertEqual(commit_lessons.citations(rewritten)[0].token, FULL)
        self.assertEqual(commit_lessons.lessons(rewritten), "body")


class CommitHelperTests(unittest.TestCase):
    """The one commit path (shiploop_git.commit_paths) every ShipLoop commit uses."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="shiploop-git-")
        self.addCleanup(temp.cleanup)
        # Real Git must not read the machine's configuration or the user's home: a user setting such as
        # commit.cleanup=strip changes what a commit stores.
        isolated = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                                                "HOME": str(Path(temp.name).resolve() / "home")})
        isolated.start()
        self.addCleanup(isolated.stop)
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

    def committed_message(self, rev: str = "HEAD") -> str:
        return git(self.repo, "log", "-1", "--format=%B", rev).rstrip("\n") + "\n"

    def test_an_empty_commit_leaves_the_files_staged_for_something_else_staged(self) -> None:
        git(self.repo, "config", "user.email", "u@example.invalid")
        git(self.repo, "config", "user.name", "U")
        (self.repo / "staged.txt").write_text("someone else's staged work\n")
        git(self.repo, "add", "staged.txt")
        message = self.repo.parent / "message.md"
        message.write_text("chore: record a remote change\n\nRemote change: staging, purged the cache\n")
        committed = shiploop_git.commit_paths(self.repo, [], "", allow_empty=True, message_file=message)
        self.assertEqual(committed.paths, [])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD").strip(), committed.commit)
        self.assertEqual(git(self.repo, "show", "--name-only", "--format=", "HEAD").split(), [])
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only").split(), ["staged.txt"])
        self.assertIn("Remote change: staging, purged the cache", self.committed_message())  # the file, not an empty -m

    def test_an_empty_commit_on_an_unborn_branch_keeps_the_staged_file_and_needs_no_identity(self) -> None:
        fresh = self.repo.parent / "fresh"
        fresh.mkdir()
        git(fresh, "init", "-q")
        (fresh / "staged.txt").write_text("x\n")
        git(fresh, "add", "staged.txt")
        committed = shiploop_git.commit_paths(fresh, [], "Empty baseline", allow_empty=True)
        self.assertTrue(committed.commit)
        self.assertEqual(git(fresh, "show", "--name-only", "--format=", "HEAD").split(), [])
        self.assertEqual(git(fresh, "diff", "--cached", "--name-only").split(), ["staged.txt"])
        self.assertEqual(git(fresh, "log", "-1", "--format=%ae").strip(), "shiploop-workspace@local.invalid")

    def test_markdown_headings_survive_a_users_strip_cleanup_on_every_commit_path(self) -> None:
        git(self.repo, "config", "user.email", "u@example.invalid")
        git(self.repo, "config", "user.name", "U")
        git(self.repo, "config", "commit.cleanup", "strip")
        body = "subject\n\n## Key learnings\n- one\n\n## Remote change\n- staging, purged\n"
        message = self.repo.parent / "message.md"
        message.write_text(body + "\n\n\n")
        (self.repo / "a.txt").write_text("a\n")
        shiploop_git.commit_paths(self.repo, ["a.txt"], "", message_file=message)
        self.assertEqual(self.committed_message(), body)  # the headings stay, the trailing blank lines go
        (self.repo / "b.txt").write_text("b\n")
        shiploop_git.commit_paths(self.repo, ["b.txt"], body)
        self.assertEqual(self.committed_message(), body)
        shiploop_git.commit_paths(self.repo, [], "", allow_empty=True, message_file=message)
        self.assertEqual(self.committed_message(), body)
        shiploop_git.commit_paths(self.repo, [], body, allow_empty=True)
        self.assertEqual(self.committed_message(), body)

    def commit_on(self, name: str) -> str:
        git(self.repo, "-c", "user.email=u@example.invalid", "-c", "user.name=U", "commit", "-q", "--allow-empty",
            "-m", name)
        return git(self.repo, "rev-parse", "HEAD").strip()

    def test_resolve_commit_takes_a_prefix_or_the_full_id_of_a_commit_reachable_from_head(self) -> None:
        head = self.commit_on("second")
        for token in (head, head[:7], head[:12].upper(), head.upper()):
            with self.subTest(token=token):
                self.assertEqual(shiploop_git.resolve_commit(self.repo, token), (head, ""))

    def test_resolve_commit_takes_an_older_commit_and_refuses_one_that_is_ahead_of_head(self) -> None:
        """Guard, not fail-first (batch 1012 review): every citation in the other tests was HEAD itself or on another
        branch, so a resolver that accepted only HEAD, or that asked the ancestry question the wrong way round, stayed
        green.  An older commit is the normal citation: one of the last three the packet quotes."""
        base = git(self.repo, "rev-parse", "HEAD").strip()
        second = self.commit_on("second")
        third = self.commit_on("third")
        for token, want in ((base, base), (base[:7], base), (second, second), (second[:9].upper(), second)):
            with self.subTest(token=token):
                self.assertEqual(shiploop_git.resolve_commit(self.repo, token), (want, ""))
        git(self.repo, "reset", "-q", "--hard", second)  # `third` is now ahead of HEAD: it exists but is not an ancestor
        found, problem = shiploop_git.resolve_commit(self.repo, third)
        self.assertEqual(found, "")
        self.assertIn("is not reachable from HEAD", problem)
        self.assertEqual(shiploop_git.resolve_commit(self.repo, base[:8]), (base, ""))

    def test_resolve_commit_says_when_git_could_not_check_the_ancestry(self) -> None:
        """Guard: a Git failure that is neither 'ancestor' (0) nor 'not an ancestor' (1) is reported, not read as either."""
        head = git(self.repo, "rev-parse", "HEAD").strip()
        real = shiploop_git.git

        def broken(repo, *args, **kwargs):
            if args[:1] == ("merge-base",):
                return subprocess.CompletedProcess(args, 128, stdout="", stderr="fatal: Not a valid commit name\n")
            return real(repo, *args, **kwargs)

        with mock.patch.object(shiploop_git, "git", broken):
            found, problem = shiploop_git.resolve_commit(self.repo, head[:7])
        self.assertEqual(found, "")
        self.assertIn("could not be checked against HEAD: fatal: Not a valid commit name", problem)

    def test_resolve_commit_names_each_reason_it_refuses_without_echoing_the_token(self) -> None:
        base = git(self.repo, "rev-parse", "HEAD").strip()
        git(self.repo, "checkout", "-q", "-b", "other")
        elsewhere = self.commit_on("only on the other branch")
        git(self.repo, "checkout", "-q", "-")
        git(self.repo, "checkout", "-q", "-b", "mine")
        self.commit_on("mine")
        tree = git(self.repo, "rev-parse", "HEAD^{tree}").strip()
        unused = next(name for name in ("deadbee", "cafe123", "feed123", "badc0de") if not any(
            line.startswith(name) for line in git(self.repo, "rev-list", "--all", "--objects").split()))
        git(self.repo, "branch", unused)  # a branch spelled like hex must not be taken for a commit
        cases = {
            "main": "is not a commit ID", "HEAD~1": "is not a commit ID", "abc12": "is not a commit ID",
            "x" * 12: "is not a commit ID", "": "is not a commit ID",
            unused: "names no commit in this repository",
            tree[:10]: "names no commit in this repository",   # an object, but not a commit
            base[:7] + base[7:] + "0000": "names no commit in this repository",   # longer than any ID: not clamped
            elsewhere: "is not reachable from HEAD", elsewhere[:9]: "is not reachable from HEAD",
        }
        for token, reason in cases.items():
            with self.subTest(token=token):
                found, problem = shiploop_git.resolve_commit(self.repo, token)
                self.assertEqual(found, "")
                self.assertIn(reason, problem)
                if token:
                    self.assertNotIn(token, problem)

    def test_resolve_commit_names_an_ambiguous_prefix_and_an_unborn_branch(self) -> None:
        first = git(self.repo, "rev-parse", "HEAD").strip()
        # a real seven-digit collision cannot be built, so Git's answer is faked for one made-up neighbour
        neighbour = first[:7] + "f" * 33
        real = shiploop_git.git

        def two_matches(repo, *args, **kwargs):
            if "--disambiguate=" + first[:7] in args:
                return subprocess.CompletedProcess(args, 0, stdout=first + "\n" + neighbour + "\n", stderr="")
            if args[:2] == ("cat-file", "-t") and args[2] == neighbour:
                return subprocess.CompletedProcess(args, 0, stdout="commit\n", stderr="")
            return real(repo, *args, **kwargs)

        with mock.patch.object(shiploop_git, "git", two_matches):
            found, problem = shiploop_git.resolve_commit(self.repo, first[:7])
        self.assertEqual(found, "")
        self.assertIn("matches 2 commits (" + first[:12] + ", " + neighbour[:12] + "); write more digits", problem)
        unborn = self.repo.parent / "unborn"
        unborn.mkdir()
        git(unborn, "init", "-q")
        found, problem = shiploop_git.resolve_commit(unborn, first[:7])
        self.assertEqual(found, "")
        self.assertIn("this repository has no commit yet", problem)


STUB = "# Feature spec\nAdds: R-1 .. R-3. Modifies: R-2. Retires: R-4.\n"
LIVING = "# Living\n\n- R-1 one\n- R-2 two\n- R-3 three\n\n## Retired\n\n- R-4 four (replaced)\n"
SLUG = "add-a-fleet-command-tab-to-abcdef"


class HomeCase(unittest.TestCase):
    """A repository and a run state, with helpers that write a knowledge home the way a planning host does."""

    setUp = KnowledgeTests.setUp

    def feature(self) -> str:
        return knowledge.feature_dir(self.state)

    def write(self, relative: str, text: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    @contextlib.contextmanager
    def unwritable(self, relative: str):
        """Every write to one file fails with a permission error, whoever runs the test (a mode bit would not stop root)."""
        target = self.repo / relative

        def deny(real):
            def guarded(path, *args, **kwargs):
                if path == target:
                    raise PermissionError(13, "Permission denied", str(path))
                return real(path, *args, **kwargs)
            return guarded

        with mock.patch.object(Path, "write_text", deny(Path.write_text)), \
                mock.patch.object(Path, "write_bytes", deny(Path.write_bytes)):
            yield target

    def planned_home(self, living: str = LIVING, feature_spec: str = STUB) -> str:
        """The home as a real run leaves it before its prepare close: committed after the spec stage."""
        self.write("docs/shiploop/spec.md", living)
        self.write(self.feature() + "/spec.md", feature_spec)
        self.write(self.feature() + "/plan.md", "# Plan\n")
        done = knowledge.commit(self.state, "spec").commit
        self.assertTrue(done)
        return done


class RetireRecordTests(HomeCase):
    """The pieces of the handoff retire (plan 0a, owner decision D3): the ID check, the subject, the planned record, the
    commit message and the living spec's pin.  Real Git repositories; the retire step itself is tested further down."""

    # --- the ID check -----------------------------------------------------------------------------------------------------
    def test_the_check_reads_every_id_the_feature_spec_names_against_the_living_spec_whatever_its_format(self) -> None:
        formats = {
            "a stub with a range": "Adds: R-1 .. R-3. Modifies: none. Retires: none.\n",
            "delta headings": "## Added\n- R-1\n## Modified\n- R-2\n## Retired\n- R-4\n",
            "a full copy of the living spec": LIVING,
            "no id at all": "# Feature\nNothing changes in the requirements.\n",
        }
        for name, body in formats.items():
            with self.subTest(name):
                self.write(self.feature() + "/spec.md", body)
                self.write("docs/shiploop/spec.md", LIVING)
                self.assertEqual(knowledge._missing_ids(self.repo, self.feature()), [])
                self.write(self.feature() + "/spec.md", body + "\nAlso R-9 and R-12.\n")
                self.assertEqual(knowledge._missing_ids(self.repo, self.feature()), ["R-9", "R-12"])

    def test_a_range_is_read_by_its_two_ends_and_an_id_under_a_retired_heading_counts(self) -> None:
        self.write("docs/shiploop/spec.md", LIVING)
        self.write(self.feature() + "/spec.md", "Adds: R-1 .. R-9\n")
        self.assertEqual(knowledge._missing_ids(self.repo, self.feature()), ["R-9"])   # R-2 is inside the range, not read
        self.write(self.feature() + "/spec.md", "Retires: R-4\n")                   # present only under ## Retired
        self.assertEqual(knowledge._missing_ids(self.repo, self.feature()), [])

    def test_ids_are_whole_tokens_and_are_listed_in_numeric_order(self) -> None:
        self.write("docs/shiploop/spec.md", "- R-1 one\n- R-10 ten\n")
        self.write(self.feature() + "/spec.md", "R-10 R-2 R-100 R-4a R-1\n")
        self.assertEqual(knowledge._missing_ids(self.repo, self.feature()), ["R-2", "R-100"])   # R-4a is not an ID

    def test_nothing_can_be_judged_without_a_feature_spec_or_when_the_living_spec_names_no_id(self) -> None:
        self.write("docs/shiploop/spec.md", LIVING)
        self.assertIsNone(knowledge._missing_ids(self.repo, self.feature()))                   # no feature spec in the tree
        self.write(self.feature() + "/spec.md", "Adds: R-1\n")
        self.write("docs/shiploop/spec.md", "# Spec\nThe requirements live in the team document.\n")
        self.assertIsNone(knowledge._missing_ids(self.repo, self.feature()))                   # nothing to compare against
        (self.repo / "docs/shiploop/spec.md").unlink()
        self.assertIsNone(knowledge._missing_ids(self.repo, self.feature()))

    # --- the subjects -----------------------------------------------------------------------------------------------------
    def test_the_knowledge_subject_is_built_in_one_place(self) -> None:
        self.assertEqual(knowledge.knowledge_subject(self.state, "prepare"),
                         "docs(shiploop): record " + SLUG + " knowledge at prepare")
        self.assertEqual(knowledge.knowledge_subject(self.state, "spec"),
                         "docs(shiploop): record " + SLUG + " knowledge after spec")
        self.planned_home()
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s").strip(), knowledge.knowledge_subject(self.state, "spec"))

    def test_the_retire_subject_claims_the_check_not_a_result_the_check_may_not_have_had_anything_to_show(self) -> None:
        """Audit (batch 1012): "its requirement IDs are in the living spec" was vacuous, and so misleading, for a feature spec
        that names none; the subject says what was done, and the body says how many IDs that was."""
        subject = knowledge.retire_subject(self.state)
        self.assertNotIn("are in the living spec", subject)
        self.assertIn("checked its requirement IDs against the living spec", subject)
        self.write("docs/shiploop/spec.md", LIVING)
        self.write(self.feature() + "/spec.md", "# Feature\nNothing changes in the requirements.\n")
        self.write(self.feature() + "/plan.md", "# Plan\n")
        self.assertTrue(knowledge.commit(self.state, "spec").commit)
        done = knowledge.retire(self.state, True)
        self.assertTrue(done.commit)                                                         # none named: still retired
        message = git(self.repo, "log", "-1", "--format=%B")
        self.assertEqual(message.splitlines()[0], subject)
        self.assertIn("Requirement IDs checked in docs/shiploop/spec.md: none (the feature spec names none).", message)

    def test_the_retire_subject_says_what_was_checked_and_one_matcher_reads_it(self) -> None:
        subject = knowledge.retire_subject(self.state)
        self.assertEqual(subject, "docs(shiploop): retire " + SLUG + " spec: checked its requirement IDs against the living spec")
        self.assertTrue(knowledge.is_retire_subject(subject))
        self.assertTrue(knowledge.is_retire_subject(knowledge.retire_subject(dict(self.state, prompt="Another request", run_id="nav-1"))))
        for other in (knowledge.knowledge_subject(self.state, "prepare"), "",
                      "docs(shiploop): retire  spec: checked its requirement IDs against the living spec",          # no folder
                      "docs(shiploop): retire two words spec: checked its requirement IDs against the living spec",   # not a folder
                      subject + ".", "x " + subject, "docs(shiploop): retire " + SLUG + " spec"):
            with self.subTest(other=other):
                self.assertFalse(knowledge.is_retire_subject(other))

    # --- the planned record -----------------------------------------------------------------------------------------------
    def test_the_planned_record_is_this_runs_prepare_close_found_by_its_subject_never_by_a_path(self) -> None:
        self.planned_home()
        self.write("docs/shiploop/environment.md", "# env\n")                       # the prepare close rarely touches the feature folder
        prepare = knowledge.commit(self.state, "prepare").commit
        self.assertTrue(prepare)
        self.assertNotIn(prepare, git(self.repo, "log", "--format=%H", "--", self.feature()).split())
        self.assertEqual(knowledge._planned_record(self.repo, self.state), prepare)
        # a later commit of another run's prepare close, and one that only quotes the subject in its body, do not move it
        other = dict(self.state, run_id="nav-0000000000123456")
        self.write("docs/shiploop/features/" + knowledge.feature_dir(other).rsplit("/", 1)[-1] + "/plan.md", "# other\n")
        self.assertTrue(knowledge.commit(other, "prepare").commit)
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "note", "-m", knowledge.knowledge_subject(self.state, "prepare"))
        self.assertEqual(knowledge._planned_record(self.repo, self.state), prepare)

    def test_the_newest_prepare_close_of_this_run_is_the_record_and_none_found_is_empty(self) -> None:
        self.assertEqual(knowledge._planned_record(self.repo, self.state), "")                  # no run commit at all
        self.planned_home()
        self.assertEqual(knowledge._planned_record(self.repo, self.state), "")                  # a spec commit is not the prepare close
        self.write("docs/shiploop/environment.md", "# env\n")
        first = knowledge.commit(self.state, "prepare").commit
        self.write("docs/shiploop/environment.md", "# env changed\n")
        second = knowledge.commit(self.state, "prepare").commit
        self.assertNotEqual(first, second)
        self.assertEqual(knowledge._planned_record(self.repo, self.state), second)

    # --- the retire message -----------------------------------------------------------------------------------------------
    def test_the_retire_message_names_the_checked_ids_the_folder_the_recover_command_and_the_planned_record_in_prose(self) -> None:
        self.planned_home()
        self.write("docs/shiploop/environment.md", "# env\n")
        prepare = knowledge.commit(self.state, "prepare").commit
        message = knowledge._retire_message(self.repo, self.state, ["R-1", "R-2"])
        relative = self.feature() + "/spec.md"
        self.assertEqual(message.splitlines()[0], knowledge.retire_subject(self.state))
        self.assertEqual(message.splitlines()[1], "")
        for part in ("R-1, R-2", "docs/shiploop/spec.md", relative, "git show <this commit>^:" + relative,
                     "Planned at " + prepare + " (the prepare close)."):
            self.assertIn(part, message)
        # a script commit that taught nothing: no lessons, no citation line (owner rule: cite the commits that helped)
        self.assertNotIn("Learned-from", message)
        self.assertEqual(commit_lessons.lessons(message), "")
        self.assertEqual(commit_lessons.citations(message), [])
        self.assertTrue(message.endswith("\n"))

    def test_the_retire_message_says_none_when_no_id_was_named_and_omits_a_planned_record_it_cannot_find(self) -> None:
        message = knowledge._retire_message(self.repo, self.state, [])
        self.assertIn("none", message)
        self.assertNotIn("Planned at", message)

    # --- the pin ----------------------------------------------------------------------------------------------------------
    def test_the_pin_is_the_newest_commit_that_changed_the_living_spec_and_does_not_move_with_other_commits(self) -> None:
        self.assertIsNone(knowledge.spec_pin(self.state))                                       # no living spec committed
        self.write("docs/shiploop/spec.md", LIVING)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "spec")
        first = git(self.repo, "rev-parse", "HEAD").strip()
        self.assertEqual(knowledge.spec_pin(self.state), "docs/shiploop/spec.md @ " + first[:12])
        self.write("other.txt", "x\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "unrelated")
        self.assertEqual(knowledge.spec_pin(self.state), "docs/shiploop/spec.md @ " + first[:12])
        self.write("docs/shiploop/spec.md", LIVING + "- R-5 five\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "spec changed")
        self.assertEqual(knowledge.spec_pin(self.state),
                         "docs/shiploop/spec.md @ " + git(self.repo, "rev-parse", "HEAD").strip()[:12])

    def test_the_pin_runs_no_git_outside_a_checkout(self) -> None:
        plain = self.repo.parent / "plain"
        plain.mkdir()
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("no process may start")):
            self.assertIsNone(knowledge.spec_pin(dict(self.state, repo=str(plain))))


class FeatureListTests(HomeCase):
    """docs/shiploop/features/README.md (owner decision D7, plan 0c): ShipLoop's list of the feature folders, written from the
    tree alone, only inside a knowledge commit that is already happening, and never over a file that is not its own."""

    def header(self) -> str:
        """The generated text above the folder rows, from a tree with one folder."""
        self.write("docs/shiploop/features/a-run-aaaaaa/plan.md", "# p\n")
        text = knowledge.feature_list(self.repo)
        return text[:text.index("## Folders\n") + len("## Folders\n")]

    def test_the_list_names_every_folder_sorted_links_each_markdown_file_and_holds_no_requirement_id(self) -> None:
        self.assertEqual(knowledge.feature_list(self.repo), "")                          # no folder: nothing is written
        for name in ("b-run-bbbbbb", "a-run-aaaaaa"):
            self.write("docs/shiploop/features/" + name + "/plan.md", "# p\n")
            self.write("docs/shiploop/features/" + name + "/spec.md", "R-1\n")
        self.write("docs/shiploop/features/b-run-bbbbbb/notes.txt", "not markdown\n")
        (self.repo / "docs/shiploop/features/a-run-aaaaaa/linked.md").symlink_to(self.repo / "app.py")
        (self.repo / "docs/shiploop/features/c-run-cccccc").symlink_to(self.repo / "docs")     # a link is not a folder
        self.write("docs/shiploop/features/stray-file.md", "a file, not a folder\n")
        self.write("docs/shiploop/features/empty-dddddd/.keep", "")
        text = knowledge.feature_list(self.repo)
        rows = text.split("## Folders\n", 1)[1]
        self.assertEqual(rows, "\n- [a-run-aaaaaa](a-run-aaaaaa/)\n  - [plan.md](a-run-aaaaaa/plan.md)\n"
                                "  - [spec.md](a-run-aaaaaa/spec.md)\n- [b-run-bbbbbb](b-run-bbbbbb/)\n"
                                "  - [plan.md](b-run-bbbbbb/plan.md)\n  - [spec.md](b-run-bbbbbb/spec.md)\n"
                                "- [empty-dddddd](empty-dddddd/)\n")
        self.assertIsNone(re.search(r"R-\d", text))             # grep -w on an ID must never list the list itself
        self.assertFalse(any(knowledge.privacy.sensitive_text(line) for line in text.splitlines()))
        self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))

    def test_a_folder_name_with_a_space_is_linked_by_its_encoded_name(self) -> None:
        self.write("docs/shiploop/features/my notes/plan.md", "# p\n")
        self.assertIn("- [my notes](my%20notes/)\n  - [plan.md](my%20notes/plan.md)\n", knowledge.feature_list(self.repo))

    def test_a_folder_name_that_looks_like_a_credential_is_withheld_and_the_next_close_still_passes(self) -> None:
        self.planned_home()
        self.write("docs/shiploop/features/use-sk-abcdefghijklmnop-123456/plan.md", "# p\n")
        text = knowledge.feature_list(self.repo)
        self.assertNotIn("abcdefghijklmnop", text)
        self.assertIn("1 folder is not listed", text)
        self.assertIn(SLUG, text)                                                          # the others are still listed
        self.assertTrue(knowledge.commit(self.state, "plan").commit)
        self.assertEqual(knowledge.check(self.state, "plan"), "")                          # the credential screen finds nothing

    def test_the_generated_header_is_markdown_lint_friendly(self) -> None:
        """The lint gate lints a file a work item changed (the list first appears inside item 1), and the model cannot fix a
        file the script rewrites: one H1 first, no repeated heading, lines of at most 80 characters, a blank line on each
        side of a heading and of a fence, a language on each fence, no bare angle brackets outside code."""
        header = self.header()
        lines = header.splitlines() + [""]                     # the file goes on with a blank line after its last heading
        self.assertEqual(lines[0], "# Features")
        headings = [number for number, line in enumerate(lines) if line.startswith("#")]
        self.assertEqual([lines[number] for number in headings if lines[number].startswith("# ")], ["# Features"])
        self.assertEqual(len(headings), len({lines[number] for number in headings}))
        self.assertTrue(all(len(line) <= 80 for line in lines), [line for line in lines if len(line) > 80])
        fences = [number for number, line in enumerate(lines) if line.startswith("```")]
        self.assertEqual(len(fences) % 2, 0)
        self.assertTrue(all(lines[number] == "```sh" for number in fences[0::2]))
        self.assertTrue(all(lines[number] == "```" for number in fences[1::2]))
        for number in headings + fences[0::2]:
            self.assertEqual(lines[number - 1] if number else "", "", lines[number])
        for number in headings + fences[1::2]:
            self.assertEqual(lines[number + 1], "", lines[number])
        prose = re.sub(r"```.*?```", "", header, flags=re.S)
        self.assertNotIn("<", re.sub(r"`[^`\n]*`", "", prose))
        self.assertNotIn("\n\n\n", header)
        self.assertTrue(header.endswith("## Folders\n"))

    def test_the_header_states_the_retire_only_as_conditional_and_names_the_squash_limit(self) -> None:
        header = " ".join(self.header().split())
        self.assertIn("removes that `spec.md` when the run's commits reach the branch", header)
        self.assertIn("Git keeps each version committed at a knowledge close; a squash merge drops them.", header)
        self.assertNotIn("keeps every version", header)                                     # only committed versions reach Git
        self.assertNotIn("then removes that `spec.md`; the run's other files stay.", header)   # never unconditionally

    def test_the_headers_commands_run_literally_on_a_retired_fixture(self) -> None:
        """Plan 0c: each command in the header is run as printed (the placeholders filled), on a probe repository holding a
        retired feature spec, and answers what the header says it answers."""
        self.planned_home(feature_spec="Adds: R-9, R-12.\n")
        self.write(self.feature() + "/plan.md", "# Plan\n\nCovers R-9.\n")
        self.write("docs/shiploop/environment.md", "# env\n")
        prepare = knowledge.commit(self.state, "prepare").commit
        self.write("docs/shiploop/features/other-aaaaaa/plan.md", "R-10 only\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "other run plan")
        (self.repo / self.feature() / "spec.md").unlink()                                   # the removal, as the retire makes it
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", knowledge.retire_subject(self.state))
        text = knowledge.feature_list(self.repo)
        blocks = re.findall(r"^```sh\n(.*?)^```$", text, re.S | re.M)
        self.assertEqual(len(blocks), 4)
        mentions, added, removed, planned = blocks

        def run(block: str, requirement: str = "R-9", *, ok: tuple = (0,)) -> str:
            command = block.replace("<ID>", requirement).replace("<folder>", SLUG)
            done = subprocess.run(["sh", "-e", "-c", command], cwd=self.repo, capture_output=True, text=True)
            self.assertIn(done.returncode, ok, command + "\n" + done.stderr)
            return done.stdout

        found = run(mentions)                                                                # which features mention R-9
        self.assertEqual(found.split(), [self.feature() + "/plan.md"])
        self.assertEqual(run(mentions, "R-10").split(), ["docs/shiploop/features/other-aaaaaa/plan.md"])
        self.assertEqual(run(mentions, "R-1", ok=(1,)), "")                                  # -w: R-10 is not R-1
        changes = run(added)                                                                 # when R-9 was added or removed
        for subject in ("record " + SLUG + " knowledge after spec", "record " + SLUG + " knowledge at prepare",
                        knowledge.retire_subject(self.state)):
            self.assertIn(subject, changes)
        self.assertNotIn("other run plan", changes)
        self.assertIn("other run plan", run(added, "R-10"))
        self.assertNotIn("other run plan", run(added, "R-1"))                                # R-10 is not R-1 here either
        self.assertEqual(run(removed), "Adds: R-9, R-12.\n")                                 # the removed file, as last written
        self.assertEqual(run(planned), "# Plan\n\nCovers R-9.\n")                           # the plan at the prepare close
        self.assertEqual(run(planned), git(self.repo, "show", prepare + ":" + self.feature() + "/plan.md"))

    def test_the_list_is_written_inside_a_knowledge_commit_and_never_by_itself(self) -> None:
        self.planned_home()                                                                  # this commit wrote it
        self.assertIn(knowledge.FEATURE_LIST, git(self.repo, "show", "--name-only", "--format=", "HEAD"))
        count = git(self.repo, "rev-list", "--count", "HEAD")
        self.write("docs/shiploop/features/second-bbbbbb/plan.md", "# p\n")                 # a folder appears, nobody commits
        self.assertEqual(git(self.repo, "rev-list", "--count", "HEAD"), count)
        self.assertNotIn("second-bbbbbb", (self.repo / knowledge.FEATURE_LIST).read_text())
        self.write(knowledge.FEATURE_LIST, (self.repo / knowledge.FEATURE_LIST).read_text() + "- HANDWRITTEN-ROW\n")
        self.assertTrue(knowledge.commit(self.state, "plan").commit)                         # the next knowledge commit replaces it
        text = (self.repo / knowledge.FEATURE_LIST).read_text()
        self.assertIn("second-bbbbbb", text)
        self.assertNotIn("HANDWRITTEN-ROW", text)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_the_list_is_not_rewritten_or_committed_when_the_home_is_unchanged(self) -> None:
        self.planned_home()
        self.write("docs/shiploop/features/second-bbbbbb/plan.md", "# p\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "a model commit that adds a folder")                 # a clean tree with a stale list
        count = git(self.repo, "rev-list", "--count", "HEAD")
        self.assertEqual(knowledge.commit(self.state, "plan"), shiploop_git.Committed("", [], []))
        self.assertEqual(git(self.repo, "rev-list", "--count", "HEAD"), count)
        self.assertNotIn("second-bbbbbb", (self.repo / knowledge.FEATURE_LIST).read_text())
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_the_list_is_no_close_or_stage_file(self) -> None:
        listed = {name for names in list(knowledge.CLOSES.values()) + list(knowledge.STAGE_FILES.values()) for name in names}
        self.assertFalse({"features/README.md", knowledge.FEATURE_LIST} & listed)
        self.assertTrue(knowledge.in_home(knowledge.FEATURE_LIST))                           # a knowledge commit and a return keep it

    def test_a_file_at_the_list_path_that_is_not_shiploops_is_left_alone_with_a_notice(self) -> None:
        self.planned_home()
        path = self.repo / knowledge.FEATURE_LIST
        self.assertEqual(knowledge.feature_list_notice(self.repo), "")
        path.write_text("My own notes about the features.\n", encoding="utf-8")
        self.write("docs/shiploop/features/second-bbbbbb/plan.md", "# p\n")
        notice = knowledge.feature_list_notice(self.repo)
        self.assertIn(str(path), notice)
        self.assertIn("does not begin with ShipLoop's generated header", notice)
        self.assertTrue(knowledge.commit(self.state, "plan").commit)                         # the commit itself still happens
        self.assertEqual(path.read_text(), "My own notes about the features.\n")
        path.write_text("", encoding="utf-8")                                                 # an empty file is nobody's
        self.assertEqual(knowledge.feature_list_notice(self.repo), "")
        knowledge.write_feature_list(self.repo)
        self.assertIn("second-bbbbbb", path.read_text())

    def test_the_list_is_never_written_through_a_symbolic_link(self) -> None:
        self.planned_home()
        outside = self.repo.parent / "outside.md"
        outside.write_text("not ShipLoop's\n")
        path = self.repo / knowledge.FEATURE_LIST
        path.unlink()
        path.symlink_to(outside)
        self.write("docs/shiploop/features/second-bbbbbb/plan.md", "# p\n")
        self.assertIn("symbolic link", knowledge.feature_list_notice(self.repo))
        knowledge.write_feature_list(self.repo)
        knowledge.commit(self.state, "plan")
        self.assertEqual(outside.read_text(), "not ShipLoop's\n")
        self.assertTrue(path.is_symlink())

    def test_a_list_that_cannot_be_written_is_a_runtime_error_with_the_absolute_path_first_and_a_next_step(self) -> None:
        """Audit (batch 1012): the PermissionError escaped knowledge.commit as a raw traceback; the navigator catches only
        RuntimeError and turns it into "handoff remains pending" (terminal) or a notice."""
        self.planned_home()
        self.write("docs/shiploop/features/second-bbbbbb/plan.md", "# p\n")          # the list text would change
        before = git(self.repo, "rev-list", "--count", "HEAD")
        with self.unwritable(knowledge.FEATURE_LIST) as listed:
            with self.assertRaises(RuntimeError) as caught:
                knowledge.commit(self.state, "plan")
        message = str(caught.exception)
        self.assertTrue(message.startswith("cannot write " + str(listed) + ": "), message)   # absolute first, never the relative path
        self.assertIn("Permission denied", message)
        self.assertIn("write permission", message)                                          # a next step
        self.assertEqual(git(self.repo, "rev-list", "--count", "HEAD"), before)             # nothing was committed
        self.assertTrue(knowledge.commit(self.state, "plan").commit)                         # the same call works once it can write

    def test_earlier_features_says_none_yet_or_names_the_list(self) -> None:
        self.assertEqual(knowledge.earlier_features(self.state), "Earlier features: none yet.")
        self.planned_home()                                                                  # only this run's own folder
        self.assertEqual(knowledge.earlier_features(self.state), "Earlier features: none yet.")
        self.write("docs/shiploop/features/older-cccccc/plan.md", "# p\n")
        self.assertEqual(knowledge.earlier_features(self.state),
                         "Earlier features: " + str(self.repo / knowledge.FEATURE_LIST) + " lists every feature folder and "
                         "the commands that find a requirement ID in them.")

    def test_earlier_features_never_says_the_list_exists_when_it_is_absent_or_not_shiploops(self) -> None:
        """Audit (batch 1012): the sentence named the list in every state with an earlier folder, although a repository that
        predates the list has none until the first knowledge commit, and a file at that path may be someone else's."""
        folders, listed = str(self.repo / "docs/shiploop/features"), self.repo / knowledge.FEATURE_LIST
        self.write("docs/shiploop/features/older-cccccc/plan.md", "# p\n")                 # an earlier run, no list yet
        absent = knowledge.earlier_features(self.state)
        self.assertEqual(absent, "Earlier features: the folders in " + folders + "/ (ShipLoop has not written its list of "
                         "them, " + str(listed) + ", yet).")
        listed.write_text("My own notes about the features.\n", encoding="utf-8")            # a file that is not ShipLoop's
        foreign = knowledge.earlier_features(self.state)
        self.assertEqual(foreign, "Earlier features: the folders in " + folders + "/ (" + str(listed) + " is not ShipLoop's "
                         "list of them).")
        listed.write_text("", encoding="utf-8")                                              # an empty file is nobody's
        self.assertEqual(knowledge.earlier_features(self.state), absent)
        listed.unlink()
        listed.symlink_to(self.repo / "app.py")                                              # a link is not ShipLoop's
        self.assertEqual(knowledge.earlier_features(self.state), foreign)
        listed.unlink()
        generated = self.repo.parent / "generated-list.md"
        generated.write_text(knowledge.feature_list(self.repo), encoding="utf-8")            # even a link to a generated list
        listed.symlink_to(generated)
        self.assertEqual(knowledge.earlier_features(self.state), foreign)
        listed.unlink()
        self.assertTrue(knowledge.commit(dict(self.state, run_id="nav-0000000000999999"), "plan").commit)   # the list gets written
        self.assertIn("lists every feature folder", knowledge.earlier_features(self.state))

    def test_the_fixture_that_writes_every_close_file_also_writes_the_list(self) -> None:
        """Stands in for the knowledge commit a real run makes after its spec stage, long before any work item's base."""
        support.write(self.state)
        self.assertTrue((self.repo / knowledge.FEATURE_LIST).is_file())
        self.assertIn(SLUG, (self.repo / knowledge.FEATURE_LIST).read_text())


class RetireTests(HomeCase):
    """knowledge.retire: remove this run's feature spec in a commit of its own once the living spec holds its IDs and the
    run's commits reach the user's branch (owner decision D3).  Real Git repositories; the route and the terminal close are
    tested through the CLI in test/shiploop-retire.test.py."""

    def prepared(self) -> str:
        """The home at the handoff: the spec stage committed it, and the prepare close committed what changed since."""
        self.planned_home()
        self.write("docs/shiploop/environment.md", "# env\n")
        prepare = knowledge.commit(self.state, "prepare").commit
        self.assertTrue(prepare)
        return prepare

    def commits(self) -> int:
        return int(git(self.repo, "rev-list", "--count", "HEAD"))

    def test_retire_removes_the_feature_spec_and_its_list_row_in_a_commit_of_its_own_and_a_retry_changes_nothing(self) -> None:
        prepare = self.prepared()
        before = self.commits()
        done = knowledge.retire(self.state, True)
        self.assertTrue(done.commit)
        self.assertEqual(done.kept, "")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD").strip(), done.commit)
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s").strip(), knowledge.retire_subject(self.state))
        changed = sorted(line for line in git(self.repo, "show", "--name-status", "--format=", "HEAD").splitlines() if line)
        self.assertEqual(changed, sorted(["D\t" + self.feature() + "/spec.md", "M\t" + knowledge.FEATURE_LIST]))
        message = git(self.repo, "log", "-1", "--format=%B")
        self.assertIn("Requirement IDs checked in docs/shiploop/spec.md: R-1, R-2, R-3, R-4.", message)
        self.assertIn("Planned at " + prepare + " (the prepare close).", message)
        self.assertEqual(commit_lessons.lessons(message), "")
        self.assertIn("Adds: R-1", git(self.repo, "show", "HEAD^:" + self.feature() + "/spec.md"))
        listed = (self.repo / knowledge.FEATURE_LIST).read_text()
        self.assertNotIn("(" + SLUG + "/spec.md)", listed)                                  # the row follows the file
        self.assertIn("(" + SLUG + "/plan.md)", listed)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertEqual(knowledge.retire(self.state, True), knowledge.Retired("", ""))     # a retry: the file is gone
        self.assertEqual(self.commits(), before + 1)

    def test_the_route_decides_whether_the_file_is_removed_and_none_says_nothing(self) -> None:
        self.prepared()
        before = self.commits()
        self.assertEqual(knowledge.retire(self.state, None), knowledge.Retired("", ""))     # not returned yet: the route is unknown
        kept = knowledge.retire(self.state, False)
        self.assertEqual(kept.commit, "")
        self.assertEqual(kept.kept, knowledge.KEPT_AFTER_ROUTE)
        # True whenever it prints: it speaks of the return made before the close, not of what the branch holds now (the
        # follow-up return, which comes after the retire, may put the knowledge commits on it).
        self.assertIn("return made before this close", kept.kept)
        self.assertNotIn("do not reach", kept.kept)
        self.assertTrue((self.repo / self.feature() / "spec.md").is_file())
        self.assertEqual(self.commits(), before)

    def test_ids_the_living_spec_lacks_keep_the_file_and_the_reason_names_them_and_the_living_spec(self) -> None:
        """Owner decision (batch 1012): handoff is never refused for IDs; the file is kept and the reason says why."""
        self.planned_home(feature_spec="Adds: R-1, R-9, R-12.\n")
        before = self.commits()
        kept = knowledge.retire(self.state, True)
        self.assertEqual(kept.commit, "")
        self.assertEqual(kept.kept, "R-9, R-12 are not in the living spec " + str(self.repo / "docs/shiploop/spec.md"))
        self.assertTrue((self.repo / self.feature() / "spec.md").is_file())
        self.assertEqual(self.commits(), before)
        self.write("docs/shiploop/spec.md", LIVING + "- R-9 nine\n- R-12 twelve\n")        # the fix the next handoff would carry
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "model adds the IDs")
        self.assertTrue(knowledge.retire(self.state, True).commit)
        kept_one = knowledge.retire(dict(self.state, prompt="Another request", run_id="nav-0000000000654321"), True)
        self.assertEqual(kept_one, knowledge.Retired("", ""))                                # no file of its own: nothing to say

    def test_a_single_missing_id_reads_as_one(self) -> None:
        self.planned_home(feature_spec="Adds: R-1, R-9.\n")
        self.assertEqual(knowledge.retire(self.state, True).kept,
                         "R-9 is not in the living spec " + str(self.repo / "docs/shiploop/spec.md"))

    def test_a_living_spec_that_names_no_id_keeps_the_file(self) -> None:
        self.planned_home(living="# Spec\nThe requirements live in the team document.\n", feature_spec="Adds: R-1\n")
        kept = knowledge.retire(self.state, True)
        self.assertEqual(kept.commit, "")
        self.assertEqual(kept.kept, "the living spec names no requirement ID, so the IDs cannot be checked")
        self.assertTrue((self.repo / self.feature() / "spec.md").is_file())

    def test_a_feature_spec_with_uncommitted_changes_or_never_committed_is_kept(self) -> None:
        self.prepared()
        self.write(self.feature() + "/spec.md", STUB + "edited after the plan\n")
        kept = knowledge.retire(self.state, True)
        self.assertEqual(kept.kept, "it has changes that are not committed")
        self.assertTrue((self.repo / self.feature() / "spec.md").is_file())
        other = dict(self.state, prompt="Another request", run_id="nav-0000000000654321")
        self.write(knowledge.feature_dir(other) + "/spec.md", STUB)                           # never committed
        self.assertEqual(knowledge.retire(other, True).kept, "it was never committed")
        self.assertTrue((self.repo / knowledge.feature_dir(other) / "spec.md").is_file())

    def test_a_failed_commit_puts_the_file_and_the_list_back_and_a_retry_works(self) -> None:
        self.prepared()
        spec, listed = self.repo / self.feature() / "spec.md", self.repo / knowledge.FEATURE_LIST
        before = (spec.read_bytes(), listed.read_bytes())

        def stage_then_fail(repo, paths, message, **kwargs):               # `git commit` failing after `git add` staged the paths
            git(repo, "add", "-A", "--", *paths)
            self.assertIn("D  " + self.feature() + "/spec.md", git(repo, "status", "--porcelain"))
            raise shiploop_git.CommitError("cannot commit it")

        with mock.patch.object(shiploop_git, "commit_paths", side_effect=stage_then_fail):
            with self.assertRaisesRegex(RuntimeError, "cannot commit it"):
                knowledge.retire(self.state, True)
        self.assertEqual((spec.read_bytes(), listed.read_bytes()), before)
        self.assertEqual(git(self.repo, "diff", "--cached", "--name-only"), "")
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertTrue(knowledge.retire(self.state, True).commit)

    def test_a_file_that_cannot_be_removed_is_a_runtime_error_with_the_file_in_place(self) -> None:
        self.prepared()
        spec = self.repo / self.feature() / "spec.md"
        with mock.patch.object(Path, "unlink", side_effect=PermissionError("denied")):
            with self.assertRaises(RuntimeError) as caught:
                knowledge.retire(self.state, True)
        message = str(caught.exception)
        self.assertTrue(message.startswith("cannot retire " + str(spec) + ": "), message)   # the absolute path first
        self.assertIn("denied", message)
        self.assertIn("write permission", message)                                          # and a next step
        self.assertTrue(spec.is_file())
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_a_failed_commit_names_the_absolute_path_first_and_the_likely_causes(self) -> None:
        self.prepared()
        spec = self.repo / self.feature() / "spec.md"
        with mock.patch.object(shiploop_git, "commit_paths",
                               side_effect=shiploop_git.CommitError("cannot commit it:\nfatal: Unable to create index.lock")):
            with self.assertRaises(RuntimeError) as caught:
                knowledge.retire(self.state, True)
        message = str(caught.exception)
        self.assertTrue(message.startswith("cannot retire " + str(spec) + ": cannot commit it: fatal: Unable to create index.lock"),
                        message)
        self.assertEqual(len(message.splitlines()), 1)                                        # the causes are on line 1 too
        self.assertIn("index lock", message)
        self.assertIn("hook", message)

    def test_a_list_that_cannot_be_written_or_put_back_still_ends_in_a_runtime_error_with_the_file_in_place(self) -> None:
        """Audit (batch 1012): the restore inside the failure handler raised the PermissionError itself, out of the handler,
        so the wrapped refusal never came and a raw traceback replaced it."""
        self.prepared()
        spec = self.repo / self.feature() / "spec.md"
        original = spec.read_bytes()
        with self.unwritable(knowledge.FEATURE_LIST):
            with self.assertRaises(RuntimeError) as caught:
                knowledge.retire(self.state, True)
        self.assertTrue(str(caught.exception).startswith("cannot retire " + str(spec) + ": "), str(caught.exception))
        self.assertEqual(spec.read_bytes(), original)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        self.assertTrue(knowledge.retire(self.state, True).commit)                           # and the retry works

    def test_a_failed_commit_removes_a_list_that_the_attempt_wrote_when_none_existed_before(self) -> None:
        """The other rollback branch (audit): a repository without a list gets one written by the attempt; a failure must not
        leave it behind as an untracked file."""
        self.prepared()
        listed = self.repo / knowledge.FEATURE_LIST
        git(self.repo, "rm", "-q", "--", knowledge.FEATURE_LIST)
        git(self.repo, "commit", "-qm", "the list is gone")
        self.assertFalse(listed.exists())
        with mock.patch.object(shiploop_git, "commit_paths", side_effect=shiploop_git.CommitError("cannot commit it")):
            with self.assertRaisesRegex(RuntimeError, "cannot commit it"):
                knowledge.retire(self.state, True)
        self.assertFalse(listed.exists())
        self.assertTrue((self.repo / self.feature() / "spec.md").is_file())
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        done = knowledge.retire(self.state, True)                                           # the retry writes it and commits both
        self.assertEqual(sorted(git(self.repo, "show", "--name-status", "--format=", "HEAD").split("\n")[:-1]),
                         sorted(["D\t" + self.feature() + "/spec.md", "A\t" + knowledge.FEATURE_LIST]))
        self.assertTrue(done.commit)

    def test_a_feature_spec_that_is_a_symbolic_link_is_kept_and_stays_a_link(self) -> None:
        """Audit (batch 1012): the rollback re-created a link as a regular file (a type change) and a link's history holds the
        target path, not the text the retire message promises in the parent commit, so a link is never retired."""
        self.prepared()
        spec = self.repo / self.feature() / "spec.md"
        (spec.parent / "real-spec.md").write_bytes(spec.read_bytes())
        spec.unlink()
        spec.symlink_to("real-spec.md")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "the feature spec becomes a link")
        before = self.commits()
        kept = knowledge.retire(self.state, True)
        self.assertEqual(kept, knowledge.Retired("", "it is a symbolic link"))
        self.assertTrue(spec.is_symlink())
        self.assertEqual(self.commits(), before)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_a_removal_that_stopped_before_its_commit_is_committed_later_as_plain_knowledge(self) -> None:
        """Known limit (journal): a process killed between the removal and the commit leaves the deletion uncommitted; the
        retry finds no file, so the next knowledge commit records it under the generic subject and no body."""
        self.prepared()
        (self.repo / self.feature() / "spec.md").unlink()
        knowledge.write_feature_list(self.repo)
        self.assertEqual(knowledge.retire(self.state, True), knowledge.Retired("", ""))
        self.assertTrue(knowledge.commit(self.state, "handoff").commit)
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s").strip(), knowledge.knowledge_subject(self.state, "handoff"))
        self.assertFalse(knowledge.is_retire_subject(git(self.repo, "log", "-1", "--format=%s").strip()))
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_a_feature_spec_the_model_deleted_is_not_retired(self) -> None:
        self.prepared()
        (self.repo / self.feature() / "spec.md").unlink()
        self.assertTrue(knowledge.commit(self.state, "handoff").commit)
        before = self.commits()
        self.assertEqual(knowledge.retire(self.state, True), knowledge.Retired("", ""))
        self.assertEqual(self.commits(), before)

    def test_an_untracked_ignored_list_stays_out_of_the_retire_commit_and_the_retire_still_works(self) -> None:
        """A .gitignore that ignores README.md must not make the retire fail on every retry (audit): the deletion alone."""
        self.write(".gitignore", "README.md\n")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore every README.md")
        self.prepared()
        self.assertEqual(git(self.repo, "ls-files", "--", knowledge.FEATURE_LIST), "")      # never tracked
        done = knowledge.retire(self.state, True)
        self.assertTrue(done.commit)
        self.assertEqual(git(self.repo, "show", "--name-status", "--format=", "HEAD").split(),
                         ["D", self.feature() + "/spec.md"])
        self.assertNotIn("(" + SLUG + "/spec.md)", (self.repo / knowledge.FEATURE_LIST).read_text())   # still written on disk

    def test_a_tracked_list_is_staged_even_when_a_rule_ignores_it(self) -> None:
        self.prepared()
        self.write(".gitignore", "README.md\n")
        git(self.repo, "add", ".gitignore")
        git(self.repo, "commit", "-qm", "ignore every README.md after the list was tracked")
        self.assertTrue(knowledge.retire(self.state, True).commit)
        changed = sorted(git(self.repo, "show", "--name-status", "--format=", "HEAD").splitlines())
        self.assertEqual(changed, sorted(["D\t" + self.feature() + "/spec.md", "M\t" + knowledge.FEATURE_LIST]))

    def test_a_list_that_is_not_shiploops_is_never_staged_by_the_retire(self) -> None:
        self.prepared()
        path = self.repo / knowledge.FEATURE_LIST
        path.write_text("My own notes about the features.\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "the user takes over the list")
        path.write_text("My own notes, edited and not committed.\n", encoding="utf-8")
        self.assertTrue(knowledge.retire(self.state, True).commit)
        self.assertEqual(git(self.repo, "show", "--name-status", "--format=", "HEAD").split(), ["D", self.feature() + "/spec.md"])
        self.assertEqual(path.read_text(), "My own notes, edited and not committed.\n")
        self.assertEqual(git(self.repo, "status", "--porcelain").strip(), "M " + knowledge.FEATURE_LIST)

    def test_retired_by_names_the_retire_commit_and_no_other_removal(self) -> None:
        """The progress view and the harness tell ShipLoop's removal from a model's by the subject, never by the path alone."""
        self.prepared()
        done = knowledge.retire(self.state, True)
        found = knowledge.retired_by(self.repo, self.feature())
        self.assertGreaterEqual(len(found), 7)
        self.assertTrue(done.commit.startswith(found))
        self.write("docs/shiploop/features/other-aaaaaa/spec.md", "x\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "add other")
        git(self.repo, "rm", "-q", "docs/shiploop/features/other-aaaaaa/spec.md")
        git(self.repo, "commit", "-qm", "model removed it")
        self.assertEqual(knowledge.retired_by(self.repo, "docs/shiploop/features/other-aaaaaa"), "")
        self.assertEqual(knowledge.retired_by(self.repo, "docs/shiploop/features/never-committed-bbbbbb"), "")
        self.assertEqual(knowledge.retired_by(self.repo.parent, self.feature()), "")           # not a checkout

    def test_a_checkout_that_is_not_a_work_tree_is_exempt(self) -> None:
        plain = self.repo.parent / "plain"
        (plain / knowledge.feature_dir(self.state)).mkdir(parents=True)
        (plain / knowledge.feature_dir(self.state) / "spec.md").write_text(STUB)
        self.assertEqual(knowledge.retire(dict(self.state, repo=str(plain)), True), knowledge.Retired("", ""))
        self.assertTrue((plain / knowledge.feature_dir(self.state) / "spec.md").is_file())


if __name__ == "__main__":
    unittest.main()
