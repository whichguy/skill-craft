#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's repository knowledge home (docs/shiploop/) and its closes.

Real Git repositories in temporary directories.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import re
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
import shiploop_navigator as navigator  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_knowledge_support as support  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


# What a reader of one printed notice line takes from it: the file (the first word after the prefix), the headings it says are
# missing and the headings it says are empty; the quoted names stop at the first semicolon.
NOTICE_LINE = re.compile(r"^ShipLoop knowledge notice: (\S+) has (?:no ((?:'[^']+'(?:, )?)+) section)?(?: and )?"
                         r"(?:an empty ((?:'[^']+'(?:, )?)+) section)? \(this close is accepted\); ")
# The commands the reference gives to count a notice in a host's events log, as the reference writes them.
COUNT_FILES = "grep -o 'ShipLoop knowledge notice: ' events.jsonl | wc -l"
COUNT_HEADINGS = "grep -o 'ShipLoop knowledge notice: [^;]*' events.jsonl | grep -o \"'[^']*'\" | wc -l"
COUNT_PER_EVENT = "awk '{n=gsub(/ShipLoop knowledge notice: /,\"&\")} n{print NR\": \"n}' events.jsonl"


def read_notice(line: str) -> tuple:
    """``(file, missing headings, empty headings)`` of one printed notice line."""
    found = NOTICE_LINE.match(line)
    assert found, line
    return found.group(1), re.findall(r"'([^']+)'", found.group(2) or ""), re.findall(r"'([^']+)'", found.group(3) or "")


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
    def test_stage_lines_name_the_living_spec_and_only_a_close_says_it_checks(self) -> None:
        lines = "\n".join(knowledge.stage_lines(self.state, "spec"))
        self.assertNotIn("README.md", lines)
        self.assertIn(str(self.repo / "docs/shiploop/spec.md"), lines)
        self.assertIn("ShipLoop refuses a spec that loses an earlier ID", lines)
        self.assertNotIn("On done ShipLoop checks", lines)
        self.assertIn("On done ShipLoop checks these files", "\n".join(knowledge.stage_lines(self.state, "prepare")))

    def test_a_file_written_before_a_close_names_the_next_close_that_requires_it(self) -> None:
        self.assertEqual(knowledge.next_close("plan", "architecture.md"), "prepare")
        self.assertEqual(knowledge.next_close("discovery", "environment.md"), "prepare")
        self.assertIsNone(knowledge.next_close("step-plan", "spec.md"))  # prepare is behind it
        self.assertEqual(knowledge.next_close("system-test-author", "environment.md"), "release-plan")
        self.assertIsNone(knowledge.next_close("plan", "nope.md"))
        self.assertEqual(knowledge.required_earlier("prepare"), ("spec.md", "architecture.md"))
        lines = "\n".join(knowledge.stage_lines(self.state, "prepare"))
        self.assertIn("Written by earlier stages; ShipLoop refuses prepare if any is missing or empty: "
                      + str(self.repo / "docs/shiploop/spec.md"), lines)
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
        names = [knowledge.HOME + "/spec.md", knowledge.HOME + "/environment.md", knowledge.HOME + "/architecture.md"]
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

    def test_release_verify_commits_the_results_lessons_as_its_message_and_needs_no_outcome_file(self) -> None:
        """Consumer contract 3.4: the lessons are the release-verify result's field, not an outcome.md (removed in 4c)."""
        support.write(self.state)
        self.assertEqual(knowledge.check(self.state, "release-verify"), "")   # environment.md alone; no outcome.md
        lessons = {"learned": "lightning__Tab creates no tab.", "considerations": "Confirm tabs with sf org list metadata.",
                   "open_next": "TC-13 and TC-14 need a person in a browser."}
        state = dict(self.state, history=[{"stage": "release-verify", "outcome": "done", "action": "A-rv"}],
                     accepted={"A-rv": {"outcome": "done", "lessons": lessons}})
        commit = knowledge.commit(state, "release-verify").commit
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
        # implement keeps it up to date since task A2 (a deviation recorded as an AD-<n>), test-strategy since consumer
        # contract 4b (the real-boundary checks); verify reads it and writes nothing.  Line 1 names every living file.
        for stage in ("intake", "discovery", "spec", "verify"):
            with self.subTest(stage):
                self.assertNotIn(absolute, "\n".join(knowledge.stage_lines(self.state, stage)[2:]))

    def test_the_architecture_is_ordered_after_the_other_living_files(self) -> None:
        self.assertEqual(knowledge.CLOSES["prepare"][:3], ("spec.md", "environment.md", "architecture.md"))
        self.assertEqual(knowledge.STAGE_FILES["plan"][-1], "architecture.md")  # the printed order of the others is kept
        self.assertEqual(knowledge.STAGE_FILES["step-plan"], ("architecture.md", "environment.md"))
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
        # The Improve stage's complete (command "improve") has its own sequence: a review's edit is committed with
        # improve-commit before the import, and line 2 (the IDs and the 'Superseded' reason) is the complete route's.
        # The command to run again is the same complete command (improve-complete is gone, 2026-10-11).
        first, second = knowledge.check(self.state, "step-plan", command="improve").split("\n")
        self.assertEqual(first, "Restore AD-<n> in " + str(path)
                         + "; if the review changed it, improve-commit it; then run complete again.")
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
        for command in ("complete", "improve"):
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
                                  "then run complete again.")
                    # The Improve route's line 1 ends "then run complete again." (shortened with improve-complete's
                    # removal): the whole closing step survives the cut at every real checkout width.
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
        for command in ("complete", "improve"):
            with self.subTest(command):
                refusal = knowledge.check(self.state, "prepare", command=command)
                lines = refusal.splitlines()
                self.assertEqual(lines[0], "Reword " + places[0] + " to name an alias, not a value or an assignment; "
                                 "then run the same complete command again.")
                self.assertIn("look like credentials", lines[1])  # the words the refusal has always had, for counting them
                self.assertEqual(re.findall(r"^- (/\S+:\d+)$", refusal, re.M), places)  # every place, none capped
                for text in ("bcrypt", "get_token", "0123456789", "os.environ"):
                    self.assertNotIn(text, refusal)  # places, never the text
        # The improve route's commit step is named too, once: its first line keeps the room for the path.
        self.assertEqual(sum("improve-commit" in line for line in knowledge.check(self.state, "prepare").splitlines()), 0)
        improve = knowledge.check(self.state, "prepare", command="improve").splitlines()
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
        for command in ("complete", "improve"):
            line_1 = knowledge.check(self.state, "prepare", command=command).splitlines()[0]
            for width in self.REAL_WIDTHS:
                with self.subTest(command=command, width=width):
                    line, shown = self.at_width(line_1, path, width)
                    self.assertIn("Reword " + shown + ":3 to name an alias, not a value or an assignment; then run the same "
                                  "complete", line[:250])

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
        again, rest = knowledge.check(self.state, "release-plan", command="improve").split("\n")
        self.assertEqual(again, "Restore R-<n> in " + str(spec)
                         + "; if the review changed it, improve-commit it; then run complete again.")
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


class LivingFilesTests(HomeFixture):
    """Consumer contract slice 4b (docs/shiploop-consumer-contract-2026-10-11.md 2.1): three living files.

    test-strategy.md's content moved into environment.md (harnesses and suites, the ID convention) and architecture.md (the
    real-boundary checks); README.md was an index with no reader of its own.  Expected values are literal, from 2.1.
    """

    S, E, A = "spec.md", "environment.md", "architecture.md"

    def test_living_files_are_spec_environment_architecture(self) -> None:
        self.assertEqual(knowledge.LIVING, ("spec.md", "environment.md", "architecture.md"))

    def test_environment_gains_harnesses_and_id_convention_and_architecture_real_boundary_checks(self) -> None:
        self.assertEqual(knowledge.SECTIONS, {
            "spec.md": ("Requirements", "Non-functional requirements", "Retired"),
            "environment.md": ("Targets and runtimes", "Commands", "Skills", "Harnesses and suites", "ID convention",
                               "Access and accounts", "Platform facts"),
            "architecture.md": ("Stack", "Structure", "Conventions", "Interfaces and boundaries", "Real-boundary checks",
                                "Decisions", "Superseded"),
        })
        # No "Release and rollback" section (X11): the procedure lives in environment.md under the run's own heading.
        self.assertNotIn("Release and rollback", knowledge.SECTIONS["environment.md"])

    def test_test_spec_is_no_close_intake_keeps_no_file_and_no_table_names_the_readme_or_test_strategy(self) -> None:
        self.assertNotIn("test-spec", knowledge.CLOSES)        # its cases are in state (test_cases)
        self.assertNotIn("intake", knowledge.STAGE_FILES)      # its only file was README.md
        for table in (knowledge.CLOSES, knowledge.STAGE_FILES):
            for stage, names in table.items():
                for name in names:
                    with self.subTest(stage=stage, name=name):
                        self.assertNotIn(name, ("README.md", "test-strategy.md"))

    def test_architecture_holds_names_real_boundary_checks(self) -> None:
        self.assertIn("the real-boundary checks a local test cannot prove (each with its owner)", knowledge.ARCHITECTURE_HOLDS)

    def test_stage_lines_name_the_three_living_files_and_not_the_readme(self) -> None:
        for stage in stage_spec.STAGES:
            with self.subTest(stage):
                lines = knowledge.stage_lines(self.state, stage)
                self.assertNotIn("README.md", "\n".join(lines))
                self.assertNotIn("test-strategy.md", "\n".join(lines))
                for name in ("spec.md", "environment.md", "architecture.md"):
                    self.assertIn(str(self.repo / knowledge.HOME / name), lines[1])

    def test_the_test_strategy_lines_point_at_the_new_sections(self) -> None:
        lines = "\n".join(knowledge.stage_lines(self.state, "test-strategy"))
        environment, architecture = (str(self.repo / knowledge.HOME / name) for name in (self.E, self.A))
        self.assertIn("keeps these up to date (create them if missing): " + environment + ", " + architecture + ".", lines)
        for heading in ("'## Harnesses and suites'", "'## ID convention'", "'## Real-boundary checks'"):
            self.assertIn(heading, lines)
        self.assertIn("the one command that lists the IDs already taken", lines)


class RemovalTests(HomeFixture):
    """Consumer contract slice 4c (sections 7 and 8): the feature folder, the retire, outcome.md, the feature list and
    ShipLoop's SHIPLOOP.md are gone; an old repository's files are left in place and no longer named or written."""

    LOCATOR = "Repository knowledge index (host-authored, if present)"
    EXEMPT = (LOCATOR,)
    # The removed engine names, as patterns over the shipped skill tree (skills/shiploop).
    REMOVED = (r"\bretire\(", r"\b_put_back\b", r"\bretired_by\b", r"\bis_retired_spec\b", r"\bretire_subject\b",
               r"\bis_retire_subject\b", r"\b_RETIRE_SUBJECT\b", r"\bKEPT_AFTER_ROUTE\b", r"\bknowledge(?:_home)?\.Retired\b",
               r"\bwrite_feature_list\b", r"\bfeature_list\b", r"\bfeature_list_notice\b", r"\b_missing_ids\b",
               r"\blearnings\(", r"\bknowledge(?:_home)?\._sections\b", r"\bLEARNING_SECTIONS\b", r"\bKNOWLEDGE_INDEX\b",
               r"\bknowledge(?:_home)?\.INDEX\b", r"\b_run_commits_reach_branch\b", r"\bcheck_test_spec_ids\b",
               r"\b_planned_record\b", r"\b_retire_message\b", r"\boutcome\.md\b",
               # kept for the inner-loop renderer swap (edb831ba) and removed after it, the final 4c commit
               r"\bfeature_dir\b", r"\bFEATURE_LIST\b", r"\b_GROUNDING\b", r"\bGROUNDING_LABELS\b",
               r"\bknowledge(?:_home)?\.grounding\(", r"\bearlier_features\b", r"\bspec_pin\b", r"\{feature\}",
               r"removed after the renderer swap", r"features/README")
    # Engine scripts: SHIPLOOP.md is a user file there, named only by the host-authored locator line.
    ENGINE_SCRIPTS = ("shiploop_knowledge_home.py", "shiploop_navigator.py", "shiploop_workspace.py",
                      "shiploop_expectations.py", "shiploop_protocol.py", "shiploop_loops.py", "shiploop_progress_data.py",
                      "shiploop_progress_render.py", "shiploop_reference.py")
    OLD = ("docs/shiploop/README.md", "docs/shiploop/test-strategy.md", "docs/shiploop/features/README.md",
           *("docs/shiploop/features/old-run-aaaaaa/" + name for name in
             ("spec.md", "plan.md", "test-spec.md", "system-tests.md", "release-plan.md", "outcome.md")),
           "SHIPLOOP.md")

    def test_the_exemption_is_exactly_the_locator_line(self) -> None:
        self.assertEqual(self.EXEMPT, ("Repository knowledge index (host-authored, if present)",))

    def test_no_removed_engine_name_is_left_in_the_skill_tree(self) -> None:
        tree = ROOT / "skills" / "shiploop"
        for path in sorted(p for p in tree.rglob("*") if p.is_file() and p.suffix in (".py", ".md", ".json")):
            text = path.read_text(encoding="utf-8")
            for pattern in self.REMOVED:
                with self.subTest(file=str(path.relative_to(ROOT)), pattern=pattern):
                    self.assertEqual(re.findall(pattern, text), [])

    SKILL_INDEX_TEMPLATE = "each skill index file outside HOME/ and SHIPLOOP.md"

    def test_engine_scripts_name_shiploop_md_only_in_the_host_authored_locator_line(self) -> None:
        for name in self.ENGINE_SCRIPTS:
            for number, line in enumerate((ROOT / "skills/shiploop/scripts" / name).read_text(encoding="utf-8").splitlines(), 1):
                if self.SKILL_INDEX_TEMPLATE in line:
                    continue  # the carry-forward result template says a skill index outside HOME/ may sit beside SHIPLOOP.md
                if "SHIPLOOP.md" in line or "Repository knowledge index" in line:
                    with self.subTest(file=name, line=number):
                        self.assertIn(self.LOCATOR, line)

    def test_knowledge_home_exports_no_removed_machinery(self) -> None:
        for name in ("feature_dir", "FEATURE_LIST", "_GROUNDING", "GROUNDING_LABELS", "grounding", "earlier_features",
                     "spec_pin", "INDEX", "LEARNING_SECTIONS", "KEPT_AFTER_ROUTE", "Retired", "retire", "retire_subject",
                     "is_retire_subject", "retired_by", "is_retired_spec", "write_feature_list", "feature_list",
                     "feature_list_notice", "learnings", "_sections", "_missing_ids", "_put_back", "_planned_record",
                     "_retire_message", "_RETIRE_SUBJECT"):
            with self.subTest(name):
                self.assertFalse(hasattr(knowledge, name))
                self.assertNotIn(name, knowledge.__all__)
        self.assertEqual(knowledge.KNOWLEDGE, ("docs/shiploop",))
        for name in ("run_label", "LIVING", "READS", "reads_quotes", "entry_text", "spec_diff", "last_lessons", "lessons_body"):
            self.assertIn(name, knowledge.__all__)

    def test_closes_and_stage_files_name_only_living_files(self) -> None:
        S, E, A = "spec.md", "environment.md", "architecture.md"
        self.assertEqual(knowledge.CLOSES, {"prepare": (S, E, A), "release-plan": (E,), "release-verify": (E,)})
        self.assertEqual(knowledge.STAGE_FILES, {
            "discovery": (E,), "research": (E,), "spec": (S,), "test-strategy": (E, A), "plan": (A,), "prepare": (E,),
            "step-plan": (A, E), "validate-existing": (E,), "implement": (E, A), "test": (E,), "carry-forward": (A, E),
            "system-test-author": (E,), "release-plan": (E,), "release-check": (E,), "release-verify": (E,)})
        for table in (knowledge.CLOSES, knowledge.STAGE_FILES):
            for names in table.values():
                self.assertTrue(set(names) <= set(knowledge.LIVING), names)

    def test_run_label_is_the_old_folder_name_and_names_no_folder(self) -> None:
        self.assertEqual(knowledge.run_label(self.state), "add-a-fleet-command-tab-to-abcdef")
        self.assertEqual(knowledge.run_label(dict(self.state, prompt="!!!")), "feature-abcdef")
        self.assertEqual(knowledge.knowledge_subject(self.state, "prepare"),
                         "docs(shiploop): record add-a-fleet-command-tab-to-abcdef knowledge at prepare")

    def test_stage_lines_name_the_three_files_and_no_index(self) -> None:
        for stage in stage_spec.STAGES:
            with self.subTest(stage):
                text = "\n".join(knowledge.stage_lines(self.state, stage))
                for removed in ("SHIPLOOP.md", "/features/", "{feature}", "outcome.md", "README.md", "feature's spec"):
                    self.assertNotIn(removed, text)
        self.assertIn("On done ShipLoop checks these files, screens them for credentials and commits docs/shiploop/ in "
                      "the execution checkout.", knowledge.stage_lines(self.state, "prepare"))
        self.assertIn("If this stage changes docs/shiploop/, ShipLoop checks and commits it when the stage is accepted; "
                      "do not commit it yourself.", knowledge.stage_lines(self.state, "implement"))

    def test_release_verify_says_the_lessons_become_the_commit_body_the_next_intake_quotes(self) -> None:
        text = "\n".join(knowledge.stage_lines(self.state, "release-verify"))
        self.assertIn("The result's lessons (learned, considerations, open_next) hold what this run learned, the key "
                      "considerations and what a later run should pick up; ShipLoop writes them into this run's "
                      "release-verify knowledge commit, which the next run's intake quotes.", text)

    def test_the_spec_line_says_the_script_derives_the_runs_requirement_changes(self) -> None:
        text = "\n".join(knowledge.stage_lines(self.state, "spec"))
        self.assertIn("ShipLoop derives this run's requirement changes from the diff since the run began", text)

    def test_the_knowledge_commit_never_stages_shiploop_md(self) -> None:
        support.write(self.state)
        self.assertTrue(knowledge.commit(self.state, "prepare").commit)
        (self.repo / "SHIPLOOP.md").write_text("# My index\n\nAuthorization: Bearer 0123456789abcdefghij\n")
        self.assertEqual(knowledge.check(self.state, "implement"), "")      # not ShipLoop's: neither screened nor refused
        self.assertEqual(knowledge.commit(self.state, "implement").commit, "")
        self.assertIn("?? SHIPLOOP.md", git(self.repo, "status", "--porcelain"))
        self.assertFalse(knowledge.in_home("SHIPLOOP.md"))
        self.assertTrue(knowledge.in_home("docs/shiploop/spec.md"))
        self.assertTrue(knowledge.in_home("docs/shiploop"))

    def test_a_validate_existing_change_to_shiploop_md_is_a_stray_path(self) -> None:
        import shiploop_expectations as expectations
        self.assertFalse(expectations._knowledge("SHIPLOOP.md"))
        self.assertTrue(expectations._knowledge("docs/shiploop/environment.md"))

    def write_old_home(self) -> dict:
        written = {}
        for relative in self.OLD:
            text = "# " + relative + "\n\nAn earlier ShipLoop version wrote this.\n"
            self.write_file(relative, text)
            written[relative] = text
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "an earlier ShipLoop version's home")
        return written

    def write_file(self, relative: str, text: str) -> None:
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_a_home_with_every_old_file_passes_every_close_and_nothing_writes_them(self) -> None:
        old = self.write_old_home()
        support.write(self.state)
        for close in knowledge.CLOSES:
            with self.subTest(close):
                self.assertEqual(knowledge.check(self.state, close), "")
                knowledge.commit(self.state, close)
        for relative, text in old.items():
            self.assertEqual((self.repo / relative).read_text(encoding="utf-8"), text)
        self.assertEqual(sorted(p.name for p in (self.repo / "docs/shiploop/features").iterdir()), ["README.md", "old-run-aaaaaa"])
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_the_credential_screen_still_reads_an_old_file_under_the_home(self) -> None:
        self.write_old_home()
        support.write(self.state)
        self.write_file("docs/shiploop/test-strategy.md", "Authorization: Bearer 0123456789abcdefghij\n")
        self.assertIn("docs/shiploop/test-strategy.md:1", knowledge.check(self.state, "prepare"))

    def test_no_stage_line_names_an_old_file_present_in_the_home(self) -> None:
        self.write_old_home()
        for stage in stage_spec.STAGES:
            with self.subTest(stage):
                text = "\n".join(knowledge.stage_lines(self.state, stage))
                for relative in self.OLD:
                    self.assertNotIn(relative.rsplit("/", 1)[0] + "/" if relative.count("/") > 2 else relative, text)
                self.assertNotIn("test-strategy.md", text)
                self.assertNotIn("old-run-aaaaaa", text)


class SectionsTests(HomeFixture):
    """The named sections of the three living files, and the stages that keep those files up to date (batch 1012 task A2)."""

    def test_the_three_files_have_their_sections_as_constants_in_the_order_a_reader_meets_them(self) -> None:
        self.assertEqual(knowledge.SECTIONS, {
            "spec.md": ("Requirements", "Non-functional requirements", "Retired"),
            "environment.md": ("Targets and runtimes", "Commands", "Skills", "Harnesses and suites", "ID convention",
                               "Access and accounts", "Platform facts"),
            "architecture.md": ("Stack", "Structure", "Conventions", "Interfaces and boundaries", "Real-boundary checks",
                                "Decisions", "Superseded"),
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
                    # the notice quotes a heading in single quotes and the documented count reads up to the first semicolon
                    self.assertFalse(set("';") & set(heading), heading)

    def test_the_architecture_wording_and_its_sections_are_one_list(self) -> None:
        holds, sections = knowledge.ARCHITECTURE_HOLDS, knowledge.SECTIONS[knowledge.ARCHITECTURE]
        for quoted in re.findall(r"'## ([^']+)'", holds):  # a heading the wording names is a section
            self.assertIn(quoted, sections)
        self.assertEqual(re.findall(r"'## ([^']+)'", holds), ["Decisions", "Superseded"])
        for heading in sections:  # and every section is a thing the wording says the file holds
            self.assertIn(heading.lower(), holds.lower())

    def test_every_stage_files_key_is_a_real_stage_and_every_name_a_living_file(self) -> None:
        """A future change to the graph cannot leave a writer entry on a stage that no longer exists."""
        for stage in knowledge.STAGE_FILES:
            self.assertIn(stage, stage_spec.STAGES)
        for stage in knowledge.CLOSES:
            self.assertIn(stage, stage_spec.STAGES)
        for stage, names in knowledge.STAGE_FILES.items():
            for name in names:
                with self.subTest(stage=stage, name=name):
                    self.assertIn(name, knowledge.LIVING)

    def test_the_reference_table_names_every_section_of_its_file_and_says_the_check_is_a_counted_notice(self) -> None:
        """Docs follow the constants (S-12): a heading added to SECTIONS must reach the reference's table row."""
        text = (ROOT / "skills/shiploop/references/project-knowledge.md").read_text(encoding="utf-8")
        for name, headings in knowledge.SECTIONS.items():
            row = next(line for line in text.splitlines() if line.startswith("| `docs/shiploop/" + name + "` |"))
            for heading in headings:
                with self.subTest(file=name, heading=heading):
                    self.assertIn("`## " + heading + "`", row)
        flat = " ".join(text.split())
        self.assertIn(knowledge.NOTICE_PREFIX.strip(), flat)
        self.assertIn("a notice, not a refusal", flat)
        # the contract the notice keeps: counted by occurrence (a host logs a call's stdout as one event line), and the limits of
        # what it reads, so a file written another way knows why it is told to add a section
        for command in (COUNT_FILES, COUNT_HEADINGS, COUNT_PER_EVENT):  # the commands the test above runs, as the reference writes them
            self.assertIn(command, flat)
        self.assertIn("one line per file", flat)
        self.assertIn("`grep -c` count the notices of a close as one", flat)
        for limit in ("an indented heading", "(setext)", "code fence that is never closed", "even when the script records another stage"):
            self.assertIn(limit, flat)
        self.assertNotIn("a packet quotes them", flat)  # the code does not: a packet duty names headings, a test pins them to SECTIONS
        self.assertNotIn("One grep for", flat)

    # The stages that find commands, facts and decisions keep these files up to date (task A2, the 8-stage inner loop).
    WRITERS = {"research": ("environment.md",),
               "step-plan": ("architecture.md", "environment.md"),
               "validate-existing": ("environment.md",),
               "implement": ("environment.md", "architecture.md"),
               "test": ("environment.md",),
               "carry-forward": ("architecture.md", "environment.md")}

    def test_the_stages_that_discover_commands_facts_and_decisions_keep_the_files_up_to_date(self) -> None:
        for stage, names in self.WRITERS.items():
            with self.subTest(stage):
                self.assertEqual(knowledge.STAGE_FILES[stage], names)
                paths = [str(self.repo / knowledge.HOME / name) for name in names]
                expected = "This stage keeps these up to date (create them if missing): " + ", ".join(paths) + "."
                self.assertIn(expected, knowledge.stage_lines(self.state, stage))

    def test_step_plan_keeps_the_environment_file_up_to_date_because_its_duty_consults_it_for_commands_and_skills(self) -> None:
        """Its duty says to consult environment.md and add a newly working command under ## Commands (the inner-loop session)."""
        self.assertEqual(knowledge.STAGE_FILES["step-plan"][-1], "environment.md")
        self.assertIn("Skills", knowledge.SECTIONS["environment.md"])
        environment = str(self.repo / "docs/shiploop/environment.md")
        lines = knowledge.stage_lines(self.state, "step-plan")
        self.assertTrue([row for row in lines if "keeps these up to date" in row and environment in row], lines)
        self.assertIn("ShipLoop refuses release-plan if any of these is missing or empty: " + environment + ".", lines)

    DUTY_FILES = ("spec", "environment", "architecture")

    @classmethod
    def named_in_the_scripts(cls) -> dict:
        """Each living file -> the headings the scripts' packet and loop text name for it (``<file>.md (## A, ## B)`` or
        ``<file>.md ## A``, bare or as the packet's ``HOME/<file>.md``). The consult note it also read is gone: a stage
        reads whole files now (knowledge.READS, consumer contract D1)."""
        pattern = re.compile(r"(?:(?<=HOME/)|(?<![\w/{}-]))(" + "|".join(cls.DUTY_FILES)
                             + r")\.md (?:\(([^)]*)\)|## ([^;:,.()]*))")
        found = {name + ".md": set() for name in cls.DUTY_FILES}
        for script in sorted((ROOT / "skills/shiploop/scripts").glob("shiploop_*.py")):
            if script.name == "shiploop_knowledge_home.py":
                continue  # the constants themselves
            flat = " ".join(script.read_text(encoding="utf-8").split())
            for match in pattern.finditer(flat):
                if match.group(3) is not None:
                    items = [match.group(3)]
                elif "##" in match.group(2):  # a parenthesis with no heading in it is prose about the file
                    items = match.group(2).split(",")
                else:
                    continue
                for item in items:
                    item = re.sub(r'^\s*(##\s*)?', "", item).replace('" "', "")  # the source's string joins
                    found[match.group(1) + ".md"].add(item.strip())
        return found

    def test_every_heading_a_packet_duty_names_for_a_living_file_is_one_of_its_sections(self) -> None:
        """The duties name headings in their own words; SECTIONS is the one list, so the two cannot drift apart again.

        A heading a duty names that SECTIONS lacks would be written by a model and never counted by the notice (the
        environment file's ``## Skills`` was one); a duty is read by prefix, as the notice reads a heading.
        """
        named = self.named_in_the_scripts()
        # A stage reads whole files now (knowledge.READS), so a file may have no heading named anywhere; the scan must
        # still find some, or it no longer reads the duties.
        self.assertTrue(any(named.values()), "no heading found at all: the scan no longer reads the duties")
        for name, items in named.items():
            with self.subTest(file=name):
                for item in sorted(items):
                    self.assertTrue(any(item.startswith(heading) for heading in knowledge.SECTIONS[name]),
                                    repr(item) + " is named for " + name + " but is not in SECTIONS[" + repr(name) + "]")

    def test_verify_reads_the_architecture_and_writes_nothing_and_the_planning_entries_are_unchanged(self) -> None:
        self.assertNotIn("verify", knowledge.STAGE_FILES)
        self.assertFalse([row for row in knowledge.stage_lines(self.state, "verify") if "keeps these up to date" in row])
        self.assertEqual(knowledge.STAGE_FILES["plan"], ("architecture.md",))
        self.assertEqual(knowledge.STAGE_FILES["prepare"], ("environment.md",))
        self.assertNotIn("test-spec", knowledge.STAGE_FILES)
        self.assertEqual(knowledge.CLOSES["prepare"][:3], ("spec.md", "environment.md", "architecture.md"))

    def test_a_writer_before_a_close_that_requires_its_file_names_that_close_and_one_after_every_close_names_none(self) -> None:
        # research feeds the prepare close; the inner stages feed the release-plan close (environment.md); architecture.md is
        # required only at prepare, which is behind every inner stage, so implement and carry-forward promise no close for it.
        research = knowledge.stage_lines(self.state, "research")
        self.assertIn("ShipLoop refuses prepare if any of these is missing or empty: "
                      + str(self.repo / "docs/shiploop/environment.md") + ".", research)
        for stage in ("step-plan", "validate-existing", "implement", "test", "carry-forward"):
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

    def said(self, stage: str = "prepare") -> list:
        """``[(file name, missing, empty)]`` of the printed lines, in order."""
        return [(Path(file).name, missing, empty) for file, missing, empty in map(read_notice, self.notices(stage))]

    FIX = ("for each, write its content under a '## <heading>' (add the heading if missing), "
           "or write 'none' there if it does not apply.")

    def test_a_home_with_every_section_gives_no_notice_at_any_close(self) -> None:
        self.put_full_home()
        for close in knowledge.CLOSES:
            with self.subTest(close):
                self.assertEqual(knowledge.section_notices(self.state, close), [])

    def test_a_file_that_lacks_sections_is_one_line_that_names_them_all_and_the_fix(self) -> None:
        path = self.put("environment.md", "# Environment\n\n## Commands\n\nnpm test\n\n## Platform facts\n\nNode 22.\n")
        self.assertEqual(self.notices(), [
            "ShipLoop knowledge notice: " + str(path) + " has no 'Targets and runtimes', 'Skills', 'Harnesses and suites', "
            "'ID convention', 'Access and accounts' section (this close is accepted); " + self.FIX])
        line = self.notices()[0]
        self.assertTrue(line.startswith(knowledge.NOTICE_PREFIX + str(self.repo)), line)  # the absolute file comes first
        self.assertEqual(line.count(knowledge.NOTICE_PREFIX), 1)
        self.assertEqual(self.said(), [("environment.md", ["Targets and runtimes", "Skills", "Harnesses and suites",
                                                           "ID convention", "Access and accounts"], [])])

    def test_one_section_lacking_is_still_one_line_and_every_heading_is_quoted_as_the_table_has_it(self) -> None:
        path = self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n\n", ""))
        self.assertEqual(self.notices(), ["ShipLoop knowledge notice: " + str(path) + " has no 'Commands' section "
                                          "(this close is accepted); " + self.FIX])
        for name, headings in knowledge.SECTIONS.items():
            for heading in headings:
                with self.subTest(file=name, heading=heading):
                    self.put_full_home()
                    self.put(name, self.full(name).replace("## " + heading + "\n\nSome text.\n\n", ""))
                    self.assertEqual(self.said(), [(name, [heading], [])])

    def test_an_empty_section_is_worded_apart_from_a_missing_one_and_both_share_the_file_s_one_line(self) -> None:
        path = self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n", "## Commands\n\n\n"))
        self.assertEqual(self.notices(), ["ShipLoop knowledge notice: " + str(path) + " has an empty 'Commands' section "
                                          "(this close is accepted); " + self.FIX])
        # a heading with only blanks after it, at the end of the file, is empty too; a heading no table names is nobody's concern
        self.put("environment.md", self.full("environment.md").replace("## Platform facts\n\nSome text.\n", "## Platform facts\n \t \n")
                 + "\n## Extras\n")
        self.assertEqual(self.said(), [("environment.md", [], ["Platform facts"])])
        # missing and empty together: one line, the missing ones first, each list in the table's order
        text = (self.full("environment.md").replace("## Commands\n\nSome text.\n", "## Commands\n\n")
                .replace("## Platform facts\n\nSome text.\n", "## Platform facts\n\n")
                .replace("## Skills\n\nSome text.\n\n", "").replace("## Targets and runtimes\n\nSome text.\n\n", ""))
        path = self.put("environment.md", text)
        self.assertEqual(self.notices(), [
            "ShipLoop knowledge notice: " + str(path) + " has no 'Targets and runtimes', 'Skills' section and an empty 'Commands', "
            "'Platform facts' section (this close is accepted); " + self.FIX])
        self.assertEqual(self.said(), [("environment.md", ["Targets and runtimes", "Skills"], ["Commands", "Platform facts"])])

    def test_there_is_one_line_per_file_that_has_anything_to_report_and_at_most_one_per_living_file(self) -> None:
        for name in knowledge.SECTIONS:
            self.put(name, "# " + name + "\n\nProse with no heading.\n")
        found = self.notices()
        self.assertEqual(len(found), len(knowledge.SECTIONS))
        self.assertEqual(self.said(), [(name, list(headings), []) for name, headings in knowledge.SECTIONS.items()])
        for line, name in zip(found, knowledge.SECTIONS):
            self.assertTrue(line.startswith(knowledge.NOTICE_PREFIX + str(self.repo / self.HOME / name) + " has "), line)
            self.assertEqual(line.count(knowledge.NOTICE_PREFIX), 1)
            self.assertEqual(line.count("\n"), 0)
        # every heading of every file is named, once, in the table's order
        self.assertEqual([heading for _, missing, _ in map(read_notice, found) for heading in missing],
                         [heading for headings in knowledge.SECTIONS.values() for heading in headings])
        # a file that has all its sections adds no line; one that lacks one adds one
        self.put_full_home()
        self.assertEqual(self.notices(), [])
        self.put("spec.md", self.full("spec.md").replace("## Retired\n\nSome text.\n", ""))
        self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n\n", "## Commands\n\n"))
        self.assertEqual(self.said(), [("spec.md", ["Retired"], []), ("environment.md", [], ["Commands"])])

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
                self.assertEqual(self.said(), [("environment.md", ["Commands"], [])])

    def test_starts_with_is_a_plain_prefix_so_a_longer_word_still_counts(self) -> None:
        # The rule is "the text starts with the heading", case-insensitive: a plural and a longer word both count.  A prefix can
        # hide a missing section (Structured data for Structure); it cannot raise a notice for a section that is there.
        self.put("environment.md", self.full("environment.md").replace("## ID convention", "## ID conventions"))
        self.assertEqual(self.notices(), [])
        self.put("architecture.md", self.full("architecture.md").replace("## Structure", "## Structured data"))
        self.assertEqual(self.notices(), [])

    def test_a_heading_inside_a_fenced_code_block_is_no_heading_and_a_comment_in_it_does_not_end_the_section(self) -> None:
        fenced = "# Environment\n\n```md\n## Commands\n```\n"
        self.put("environment.md", fenced + "".join("## " + h + "\n\ntext\n\n" for h in knowledge.SECTIONS["environment.md"] if h != "Commands"))
        self.assertEqual(self.said(), [("environment.md", ["Commands"], [])])
        # a shell comment under a real heading is body, and a section whose body is only a fence is present
        body = "## Commands\n\n```sh\n# install\nnpm ci\n```\n\n"
        self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n\n", body))
        self.assertEqual(self.notices(), [])
        self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n\n", "## Commands\n\n~~~\n# only a comment\n~~~\n\n"))
        self.assertEqual(self.notices(), [])

    def test_a_fence_closes_only_with_its_own_mark_at_least_as_long_and_no_text(self) -> None:
        """What a block hides: a heading inside any fence is no heading, so the section stays missing until the fence closes."""
        hidden = (("a tilde fence", "~~~\n## Commands\n~~~\n"),
                  ("a tilde line does not close a backtick fence", "```\n~~~\n## Commands\n```\n"),
                  ("a shorter backtick line does not close a longer fence", "````\n```\n## Commands\n````\n"),
                  ("a line with text after the marks does not close it", "```\n```sh\n## Commands\n```\n"),
                  ("a fence indented by up to three spaces", "   ```\n## Commands\n   ```\n"))
        for label, block in hidden:
            with self.subTest(label):
                text = self.full("environment.md").replace("## Commands\n\nSome text.\n\n", block)
                self.put("environment.md", text)
                self.assertEqual(self.said(), [("environment.md", ["Commands"], [])])
        # once the fence is closed the next heading is a heading again
        text = self.full("environment.md").replace("## Commands\n\nSome text.\n\n", "```\ncode\n```\n## Commands\n\nnpm test\n\n")
        self.put("environment.md", text)
        self.assertEqual(self.notices(), [])

    def test_a_line_that_is_no_fence_opener_hides_nothing(self) -> None:
        """What opens a fence is the CommonMark rule: up to three spaces, three marks, and no backtick in a backtick fence's text.

        A wrongly opened fence hides every later heading, so each present section is reported missing and the model is told
        to add a duplicate; a false notice is worse than a missed one.
        """
        for label, line in (("four spaces make an indented code block, not a fence", "    ```"),
                            ("a tab makes one too", "\t```"),
                            ("inline code that starts a line", "```npm test``` is the command."),
                            ("a backtick in the text after the marks", "```sh `x`"),
                            ("two marks are no fence", "``"),
                            ("two tildes are no fence", "~~")):
            with self.subTest(label):
                text = self.full("environment.md").replace("## Targets and runtimes\n\nSome text.\n",
                                                            "## Targets and runtimes\n\n" + line + "\n")
                self.put("environment.md", text)
                self.assertEqual(self.notices(), [])
        # a tilde fence may carry a backtick in its text and is still a fence
        text = self.full("environment.md").replace("## Commands\n\nSome text.\n\n", "~~~sh `x`\n## Commands\n~~~\n\n")
        self.put("environment.md", text)
        self.assertEqual(self.said(), [("environment.md", ["Commands"], [])])

    def test_only_an_atx_heading_at_the_start_of_the_line_counts_as_the_reference_says(self) -> None:
        """The documented limits (references/project-knowledge.md, Named sections): an indented heading and a setext one are no
        heading to the notice, so a file written that way is told to add the section."""
        for label, replacement in (("indented one space", " ## Commands"), ("indented three spaces", "   ## Commands"),
                                   ("underlined (setext)", "Commands\n--------")):
            with self.subTest(label):
                self.put("environment.md", self.full("environment.md").replace("## Commands", replacement))
                self.assertEqual(self.said(), [("environment.md", ["Commands"], [])])

    def test_a_byte_order_mark_at_the_start_of_the_file_hides_nothing(self) -> None:
        """A tool that saves UTF-8 with a mark (Notepad, Windows PowerShell) puts it before a first-line heading."""
        for first in ("## Targets and runtimes", "# Targets and runtimes"):
            with self.subTest(first):
                body = "".join("## " + h + "\n\ntext\n\n" for h in knowledge.SECTIONS["environment.md"] if h != "Targets and runtimes")
                path = self.put("environment.md", first + "\n\ntext\n\n" + body)
                path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
                self.assertEqual(self.notices(), [])

    def test_a_section_runs_to_the_next_heading_of_the_same_or_a_higher_level_and_a_deeper_heading_is_body(self) -> None:
        # architecture.md: "## Decisions" whose body is its own "### AD-n" headings is present
        text = self.full("architecture.md").replace("## Decisions\n\nSome text.\n", "## Decisions\n### AD-1 In memory\nWhy.\n")
        self.put("architecture.md", text)
        self.assertEqual(self.notices(), [])
        # the same level ends it
        self.put("architecture.md", self.full("architecture.md").replace("## Decisions\n\nSome text.\n\n", "## Decisions\n\n"))
        self.assertIn("has an empty 'Decisions' section", self.notices()[0])
        self.put("architecture.md", self.full("architecture.md"))
        # a higher level ends it: "### Commands" followed by a "# Next" heading
        self.put("environment.md", self.full("environment.md").replace("## Commands\n\nSome text.\n\n", "### Commands\n# Next\ntext\n\n"))
        self.assertIn("has an empty 'Commands' section", self.notices()[0])
        # a sibling heading at the section's own level ends it, whatever that level is (the rule is not tied to "##")
        for marks in ("###", "####"):
            self.put("environment.md", self.full("environment.md").replace(
                "## Commands\n\nSome text.\n\n", marks + " Commands\n" + marks + " Sibling\nsome text\n\n"))
            self.assertIn("has an empty 'Commands' section", self.notices()[0])
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
        self.assertIn("has an empty 'Commands' section", self.notices()[0])

    def test_only_a_close_gives_a_notice_and_every_close_gives_the_same_lines(self) -> None:
        self.put("environment.md", "# Environment\n\nNode 22.\n")
        for stage in ("intake", "plan", "step-plan", "implement", "verify", "handoff", "not-a-stage"):
            with self.subTest(stage):
                self.assertEqual(knowledge.section_notices(self.state, stage), [])
        for close in knowledge.CLOSES:
            with self.subTest(close):
                self.assertEqual(knowledge.section_notices(self.state, close), self.notices())
        self.assertEqual(self.said(), [("environment.md", list(knowledge.SECTIONS["environment.md"]), [])])

    def test_a_file_that_is_absent_blank_or_not_a_file_gives_no_notice_and_the_other_files_still_do(self) -> None:
        self.assertEqual(self.notices(), [])  # nothing written: the close's own refusal asks for the files
        self.put("spec.md", "  \n\t\n")
        (self.repo / self.HOME / "environment.md").mkdir()
        self.put("architecture.md", "# Architecture\n\nA script.\n")
        self.assertEqual(self.said(), [("architecture.md", list(knowledge.SECTIONS["architecture.md"]), [])])
        self.assertEqual(read_notice(self.notices()[0])[0], str(self.repo / self.HOME / "architecture.md"))

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
        self.assertEqual(self.said(), [("environment.md", [h for h in knowledge.SECTIONS["environment.md"] if h != "Commands"], [])])

    def test_each_file_is_read_for_its_own_sections_in_the_order_of_the_table(self) -> None:
        for name in knowledge.SECTIONS:
            self.put(name, "# " + name + "\n\nProse with no heading.\n")
        expected = [(name, list(headings), []) for name, headings in knowledge.SECTIONS.items()]
        self.assertEqual(self.said(), expected)
        self.assertEqual([read_notice(line)[0] for line in self.notices()],
                         [str(self.repo / self.HOME / name) for name in knowledge.SECTIONS])
        # the headings of one file do not satisfy another: each file is read for itself
        self.put("architecture.md", self.full("environment.md"))
        found = [row for row in self.said() if row[0] == "architecture.md"]
        self.assertEqual(found, [("architecture.md", list(knowledge.SECTIONS["architecture.md"]), [])])
        # an old repository's test-strategy.md is no living file: it gets no line, whatever it lacks
        self.put("test-strategy.md", "# test strategy\n\nProse.\n")
        self.assertNotIn("test-strategy.md", [row[0] for row in self.said()])

    def test_the_path_is_the_same_token_in_every_variant_of_the_line(self) -> None:
        """A reader or the harness that takes the token after the prefix as the file gets the path, not 'path:'."""
        missing_only = self.full("environment.md").replace("## Skills\n\nSome text.\n\n", "")
        empty_only = self.full("environment.md").replace("## Commands\n\nSome text.\n", "## Commands\n\n")
        both = missing_only.replace("## Commands\n\nSome text.\n", "## Commands\n\n")
        for label, text, shape in (("missing", missing_only, "has no"), ("empty", empty_only, "has an empty"),
                                   ("both", both, "has no")):
            with self.subTest(label):
                path = self.put("environment.md", text)
                (line,) = self.notices()
                self.assertEqual(line.split(" ")[3], str(path), line)
                self.assertFalse(line.split(" ")[3].endswith(":"))
                self.assertTrue(line.startswith(knowledge.NOTICE_PREFIX + str(path) + " " + shape + " '"), line)

    def test_the_architecture_wording_is_printed_once_on_the_architecture_line_and_nowhere_else(self) -> None:
        """What the file holds is the one constant, said once in the block; no other line carries a per-file explanation."""
        self.put("architecture.md", "# Architecture\n\nA script.\n")
        (line,) = self.notices()
        self.assertEqual(self.said(), [("architecture.md", list(knowledge.SECTIONS["architecture.md"]), [])])
        self.assertTrue(line.endswith(" " + self.FIX + " architecture.md holds " + knowledge.ARCHITECTURE_HOLDS + "."), line)
        self.assertEqual(line.count(knowledge.ARCHITECTURE_HOLDS), 1)
        # one heading lacking is enough to print it; every other file's line has no explanation beyond the headings
        self.put("architecture.md", self.full("architecture.md").replace("## Structure\n\nSome text.\n\n", ""))
        (line,) = self.notices()
        self.assertEqual(self.said(), [("architecture.md", ["Structure"], [])])
        self.assertTrue(line.endswith(" architecture.md holds " + knowledge.ARCHITECTURE_HOLDS + "."), line)
        for name in ("spec.md", "environment.md"):
            self.put(name, "# " + name + "\n\nProse.\n")
        block = self.notices()
        self.assertEqual(len(block), 3)
        self.assertEqual("\n".join(block).count(knowledge.ARCHITECTURE_HOLDS), 1)
        for other in block:
            if "/architecture.md " not in other:
                self.assertTrue(other.endswith("; " + self.FIX), other)
                self.assertNotIn("holds", other)
        # a complete architecture file adds neither the line nor the wording
        self.put("architecture.md", self.full("architecture.md"))
        self.assertNotIn(knowledge.ARCHITECTURE_HOLDS, "\n".join(self.notices()))
        self.assertEqual(len(self.notices()), 2)

    def test_the_documented_commands_count_files_and_headings_in_an_events_log_and_a_single_close(self) -> None:
        """The commands the reference gives: lines are counted by occurrence (a host logs a call's stdout as one event line)."""
        for name in knowledge.SECTIONS:
            self.put(name, "# " + name + "\n\nProse with no heading.\n")
        prepare = self.notices("prepare")
        self.put("environment.md", self.full("environment.md").replace("## Skills\n\nSome text.\n\n", "")
                 .replace("## Commands\n\nSome text.\n", "## Commands\n\n"))
        self.put("architecture.md", self.full("architecture.md"))
        self.put("spec.md", self.full("spec.md"))
        test_spec = self.notices("release-plan")
        self.assertEqual(len(prepare), 3)
        self.assertEqual(len(test_spec), 1)

        def event(output: str) -> str:  # the shape a host logs a call's stdout in: one JSON line, newlines escaped
            return json.dumps({"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "content": "exit 0\n" + output + "\nShipLoop navigator | operations | revision 3\n"}]}})

        log = self.repo / "events.jsonl"
        log.write_text("\n".join([event("ShipLoop knowledge: committed the home.\n" + "\n".join(prepare)),
                                  event("ShipLoop knowledge: committed the home."),
                                  event("\n".join(test_spec))]) + "\n", encoding="utf-8")

        def run(command: str) -> str:
            done = subprocess.run(command, shell=True, cwd=self.repo, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            return done.stdout.strip()

        self.assertEqual(run(COUNT_FILES), "4")  # files that had something to report: 3 at the first close, 1 at the second
        self.assertEqual(run(COUNT_HEADINGS), str(sum(len(h) for h in knowledge.SECTIONS.values()) + 2))
        self.assertEqual(run(COUNT_PER_EVENT).splitlines(), ["1: 3", "3: 1"])  # one count per event line that has a notice
        self.assertEqual(run("grep -c 'ShipLoop knowledge notice: ' events.jsonl"), "2")  # grep -c counts event lines: wrong here
        self.assertEqual(run("sed -n 3p events.jsonl | grep -o 'ShipLoop knowledge notice: [^;]*' | grep -o \"'[^']*'\" | wc -l"), "2")
        # the sibling lines of a knowledge commit do not match the prefix
        self.assertEqual(run("grep -o 'ShipLoop knowledge: ' events.jsonl | wc -l"), "2")

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
        self.assertEqual(len(re.findall(r"^ShipLoop knowledge notice: ", "\n".join(self.notices()), re.M)), 1)
        self.assertIsNone(re.match(r"^ShipLoop knowledge notice: ", "ShipLoop knowledge: committed the removal of the feature spec"))

    def test_the_fixture_writer_writes_every_section_so_a_fixture_home_gets_no_notice_and_keeps_its_requirement(self) -> None:
        """Drift guard for test/shiploop_knowledge_support.write: a section added to SECTIONS is written without editing it."""
        support.write(self.state)
        for close in knowledge.CLOSES:
            with self.subTest(close):
                self.assertEqual(knowledge.section_notices(self.state, close), [])
        self.assertIn("R-1", (self.repo / self.HOME / "spec.md").read_text(encoding="utf-8"))
        self.assertEqual(knowledge.check(self.state, "prepare"), "")


class SectionNoticeCloseTests(HomeFixture):
    """The notice at the knowledge close the navigator makes after an accepted stage (``_knowledge_close``), on a real repository."""

    def close(self, stage: str, *, terminal: bool = False) -> tuple:
        after = dict(self.state, history=[{"stage": stage, "outcome": "done"}])
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            navigator._knowledge_close({"history": []}, after, Path("/ws/run"), terminal=terminal)
        return out.getvalue(), err.getvalue()

    def write_bare_home(self) -> None:
        """Every file the closes require, none of them with a named section (what the saved runs wrote)."""
        support.write(self.state)
        for name in knowledge.SECTIONS:
            (self.repo / "docs/shiploop" / name).write_text("# " + name + "\n\nProse with no sections.\n", encoding="utf-8")

    def test_a_close_prints_the_notice_lines_on_stdout_after_the_commit_and_the_close_stands(self) -> None:
        self.write_bare_home()
        out, err = self.close("prepare")
        lines = knowledge.section_notices(self.state, "prepare")
        self.assertEqual(len(lines), len(knowledge.SECTIONS))  # one line per file that has something to report
        self.assertEqual(out, "".join(line + "\n" for line in lines))
        self.assertEqual(err, "")
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s").strip(), knowledge.knowledge_subject(self.state, "prepare"))

    def test_every_close_prints_them_and_a_stage_that_is_no_close_prints_none(self) -> None:
        self.write_bare_home()
        for stage in knowledge.CLOSES:
            with self.subTest(stage):
                out, _ = self.close(stage)
                self.assertEqual(out.count(knowledge.NOTICE_PREFIX), len(knowledge.SECTIONS))
        for stage in ("implement", "plan", "verify", "carry-forward"):
            with self.subTest(stage):
                self.assertEqual(self.close(stage), ("", ""))

    def test_the_close_among_the_accepted_stages_prints_whatever_the_script_records_after_it(self) -> None:
        """The test-spec close and the validate-existing row the script records in the same transition are one call.

        The commit's subject names the last stage accepted, but a close that was accepted earlier in the call still checked
        its files and still owes its notice: counted from the last row alone, one of the four closes would print nothing on
        the common route (a reviewer's real-CLI probe, batch 1012 task A2 fix round).
        """
        self.write_bare_home()
        total = len(knowledge.SECTIONS)
        for rows, expected in ((["release-plan", "release-check"], total), (["step-plan", "prepare"], total),
                               (["test-spec", "validate-existing"], 0),   # test-spec is no close since consumer contract 4b
                               (["prepare", "step-plan"], total), (["release-verify"], total),
                               (["validate-existing", "implement"], 0), (["implement", "test"], 0), (["handoff"], 0)):
            with self.subTest(rows=rows):
                after = dict(self.state, history=[{"stage": stage, "outcome": "done"} for stage in rows])
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    navigator._knowledge_close({"history": []}, after, Path("/ws/run"))
                self.assertEqual(out.getvalue().count(knowledge.NOTICE_PREFIX), expected)

    def test_a_row_that_did_not_finish_is_no_accepted_close(self) -> None:
        self.write_bare_home()
        after = dict(self.state, history=[{"stage": "release-plan", "outcome": "done"}, {"stage": "prepare", "outcome": "blocked"}])
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            navigator._knowledge_close({"history": []}, after, Path("/ws/run"))
        self.assertEqual(out.getvalue().count(knowledge.NOTICE_PREFIX), len(knowledge.SECTIONS))
        blocked = dict(self.state, history=[{"stage": "prepare", "outcome": "blocked"}])
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            navigator._knowledge_close({"history": []}, blocked, Path("/ws/run"))
        self.assertEqual(out.getvalue(), "")

    def test_a_home_with_every_section_prints_nothing_at_a_close(self) -> None:
        support.write(self.state)
        self.assertEqual(self.close("prepare"), ("", ""))

    def test_the_terminal_close_at_handoff_prints_none_and_keeps_its_own_lines(self) -> None:
        self.write_bare_home()
        out, err = self.close("handoff", terminal=True)
        self.assertNotIn(knowledge.NOTICE_PREFIX, out + err)

    def test_a_commit_that_cannot_be_made_prints_its_own_notice_on_stderr_and_no_section_notice(self) -> None:
        self.write_bare_home()
        with mock.patch.object(knowledge, "commit", side_effect=RuntimeError("cannot commit")):
            out, err = self.close("prepare")
        self.assertEqual(out, "")
        self.assertEqual(err, "ShipLoop knowledge: cannot commit; the next accepted stage commits it.\n")

    def test_a_notice_never_changes_what_the_close_commits(self) -> None:
        self.write_bare_home()
        self.close("prepare")
        committed = set(git(self.repo, "show", "--name-only", "--format=", "HEAD").split())
        self.assertTrue(all(name.startswith("docs/shiploop/") for name in committed))
        self.assertIn("docs/shiploop/environment.md", committed)


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


LIVING = "# Living\n\n- R-1 one\n- R-2 two\n- R-3 three\n\n## Retired\n\n- R-4 four (replaced)\n"
SLUG = "add-a-fleet-command-tab-to-abcdef"


class HomeCase(unittest.TestCase):
    """A repository and a run state, with helpers that write a knowledge home the way a planning host does."""

    setUp = KnowledgeTests.setUp

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

    def planned_home(self, living: str = LIVING) -> str:
        """The home as a real run leaves it before its prepare close: committed after the spec stage."""
        self.write("docs/shiploop/spec.md", living)
        done = knowledge.commit(self.state, "spec").commit
        self.assertTrue(done)
        return done


class SubjectTests(HomeCase):
    """The knowledge commit's subject (``run_label``)."""

    def test_the_knowledge_subject_is_built_in_one_place(self) -> None:
        self.assertEqual(knowledge.knowledge_subject(self.state, "prepare"),
                         "docs(shiploop): record " + SLUG + " knowledge at prepare")
        self.assertEqual(knowledge.knowledge_subject(self.state, "spec"),
                         "docs(shiploop): record " + SLUG + " knowledge after spec")
        self.planned_home()
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s").strip(), knowledge.knowledge_subject(self.state, "spec"))


if __name__ == "__main__":
    unittest.main()
