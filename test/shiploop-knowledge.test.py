#!/usr/bin/env python3
"""Hermetic tests for ShipLoop's repository knowledge home (docs/shiploop/) and its closes.

Real Git repositories in temporary directories.
"""
from __future__ import annotations

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
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_knowledge_support as support  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


class KnowledgeTests(unittest.TestCase):
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

    def test_feature_directory_and_stage_lines(self) -> None:
        self.assertEqual(knowledge.feature_dir(self.state),
                         "docs/shiploop/features/add-a-fleet-command-tab-to-abcdef")
        lines = "\n".join(knowledge.stage_lines(self.state, "spec"))
        self.assertIn(str(self.repo / "docs/shiploop/README.md"), lines)
        self.assertIn(str(self.repo / "docs/shiploop/spec.md"), lines)
        self.assertIn("ShipLoop refuses a spec that loses an earlier ID", lines)
        self.assertNotIn("On done ShipLoop checks", lines)
        self.assertIn("On done ShipLoop checks these files", "\n".join(knowledge.stage_lines(self.state, "prepare")))

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
                 knowledge.HOME + "/test-strategy.md", feature + "/spec.md", feature + "/plan.md"]
        absolute = [str(self.repo / name) for name in names]
        self.assertEqual(lines[0], "Before prepare is done, write: " + ", ".join(absolute))
        self.assertIn(absolute[0], lines[0][:250])
        self.assertNotIn(" docs/shiploop/", lines[0])  # no relative path that could be written from the wrong directory
        self.assertEqual(re.findall(r"^- (/\S+)$", refusal, re.M), absolute)
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


if __name__ == "__main__":
    unittest.main()
