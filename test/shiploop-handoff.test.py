#!/usr/bin/env python3
"""Hermetic tests for the consumer contract's engine data (slice 4a, docs/shiploop-consumer-contract-2026-10-11.md 0A).

Owner directive: every output ShipLoop produces is made for a named consumer, in the form and at the moment it reads it,
and a stage works from its packet alone (context is cleared between stages).  These tests pin the data the packets quote:
the whole-file READS table, the run baseline and its spec diff, the lessons commit and its quote at the next intake, the
hand-off result fields with their shapes and gates, the open items, and the CONSUMES table with its resolver.

Expected tables are written out by hand here, never read back from READS or CONSUMES (no circular test).
"""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
sys.path.insert(0, str(ROOT / "test"))
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402


CLI = ROOT / "skills/shiploop/scripts/shiploop"
CARD = ROOT / "skills/improve/SKILL.md"


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


LESSONS = {"learned": "lightning__Tab creates no tab.\nA second line stays.",
           "considerations": "Confirm tabs with sf org list metadata.",
           "open_next": "TC-13 and TC-14 need a person in a browser."}


class RepoCase(unittest.TestCase):
    """A real Git repository with one commit and a run state in it; a run folder beside it."""

    def setUp(self) -> None:
        isolated = mock.patch.dict(os.environ, {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})
        isolated.start()
        self.addCleanup(isolated.stop)
        temp = tempfile.TemporaryDirectory(prefix="shiploop-handoff-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.repo = self.base / "repo"
        self.root = self.base / "run"
        self.repo.mkdir()
        self.root.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "h@example.invalid")
        git(self.repo, "config", "user.name", "H")
        git(self.repo, "config", "commit.gpgsign", "false")
        git(self.repo, "config", "core.hooksPath", os.devnull)
        (self.repo / "app.py").write_text("x = 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "base")
        self.state = {"repo": str(self.repo), "prompt": "Add a Fleet command tab to the Battleship game.",
                      "run_id": "nav-0123456789abcdef", "execution_mode": "navigator", "history": [],
                      "accepted": {}}

    def home(self, name: str, text: str) -> Path:
        path = self.repo / knowledge.HOME / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def head(self) -> str:
        return git(self.repo, "rev-parse", "HEAD").strip()


# ---------------------------------------------------------------------------------------------------------- READS (D1)

_S, _E, _A = "spec.md", "environment.md", "architecture.md"
EXPECTED_READS = {
    "intake": (_S, _E, _A), "discovery": (), "research": (), "spec": (), "test-strategy": (_S,),
    "plan": (_S, _E, _A), "prepare": (_E,), "step-plan": (_S, _E, _A), "test-spec": (_S, _E, _A),
    "validate-existing": (_E, _A), "implement": (_E, _A), "test": (_E, _A), "document": (_E, _A), "verify": (_E, _A),
    "carry-forward": (), "system-test-author": (_S, _E, _A), "system-test": (_E, _A), "product-acceptance": (_S, _E),
    "release-plan": (_E,), "release-check": (_E,), "release": (_E,), "release-verify": (), "operations": (_E,),
    "handoff": (),
}


class ReadsTests(RepoCase):
    def test_every_stage_has_the_row_the_contract_names(self) -> None:
        self.assertEqual(set(EXPECTED_READS), set(stage_spec.STAGES))
        self.assertEqual(dict(knowledge.READS), EXPECTED_READS)

    def test_each_file_is_quoted_whole_and_uncut_by_absolute_path(self) -> None:
        long = "## Requirements\n\n" + "".join("- R-%d: requirement %d %s\n" % (n, n, "x" * 80) for n in range(1, 400))
        self.assertGreater(len(long), 30000)
        self.home("spec.md", "﻿" + long)                    # a byte-order mark is no part of the text
        self.home("architecture.md", "## Stack\n\nPython.\n")
        quotes = knowledge.reads_quotes(self.state, "intake")
        self.assertEqual([quote.file for quote in quotes], [_S, _E, _A])
        self.assertEqual([quote.path for quote in quotes],
                         [self.repo / knowledge.HOME / name for name in (_S, _E, _A)])
        self.assertEqual(quotes[0].text, long)
        self.assertIsNone(quotes[1].text)                            # absent
        self.assertEqual(quotes[2].text, "## Stack\n\nPython.\n")

    def test_a_blank_or_unreadable_file_is_none_and_a_stage_with_no_row_quotes_nothing(self) -> None:
        self.home("environment.md", "  \n\n")
        (self.repo / knowledge.HOME / "architecture.md").mkdir()      # not a regular file
        quotes = knowledge.reads_quotes(self.state, "test")
        self.assertEqual([(quote.file, quote.text) for quote in quotes], [(_E, None), (_A, None)])
        self.assertEqual(knowledge.reads_quotes(self.state, "handoff"), [])

    def test_an_unknown_stage_raises(self) -> None:
        with self.assertRaises(ValueError):
            knowledge.reads_quotes(self.state, "select-work")


# ------------------------------------------------------------------------------------------------ entries (2.3)

SPEC = """# Spec

## Requirements

- R-1: Place a fleet.
  Ships may not overlap,
  and they stay on the board.
- **R-2** Reload keeps the fleet; this differs from R-1 and from R-10.
lazy continuation of R-2

    indented after a blank line still belongs to R-2
- R-10: Ten.

| ID | Text |
|---|---|
| R-3 | A table row. |
| R-4 | Another row. |

### R-5 A heading requirement

Its body, with a mention of R-9 inside.

```text
R-6: inside a fence, not an entry
```

#### R-7 A deeper heading inside R-5

## Retired

1. R-8: Dropped because R-1 covers it.
R-11: a paragraph entry.
R-1: a later start for R-1 is ignored.
"""


class EntryTests(RepoCase):
    def test_entry_starts_in_list_bold_table_heading_ordered_and_paragraph_form(self) -> None:
        self.home("spec.md", SPEC)
        self.assertEqual(knowledge.entry_text(self.repo, "R-1"),
                         "- R-1: Place a fleet.\n  Ships may not overlap,\n  and they stay on the board.")
        self.assertEqual(knowledge.entry_text(self.repo, "R-2"),
                         "- **R-2** Reload keeps the fleet; this differs from R-1 and from R-10.\n"
                         "lazy continuation of R-2\n\n    indented after a blank line still belongs to R-2")
        self.assertEqual(knowledge.entry_text(self.repo, "R-10"), "- R-10: Ten.")
        self.assertEqual(knowledge.entry_text(self.repo, "R-3"), "| R-3 | A table row. |")
        self.assertEqual(knowledge.entry_text(self.repo, "R-5"),
                         "### R-5 A heading requirement\n\nIts body, with a mention of R-9 inside.\n\n```text\n"
                         "R-6: inside a fence, not an entry\n```\n\n#### R-7 A deeper heading inside R-5")
        # another entry start of the same prefix ends a span, and only the first start of an ID counts
        self.assertEqual(knowledge.entry_text(self.repo, "R-8"), "1. R-8: Dropped because R-1 covers it.")
        self.assertEqual(knowledge.entry_text(self.repo, "R-11"), "R-11: a paragraph entry.")

    def test_a_mention_a_fence_or_another_number_is_no_entry_and_retired_is_flagged(self) -> None:
        self.home("spec.md", SPEC)
        self.assertIsNone(knowledge.entry_text(self.repo, "R-9"))     # only mentioned
        self.assertIsNone(knowledge.entry_text(self.repo, "R-6"))     # inside a fence
        self.assertIsNotNone(knowledge.entry_text(self.repo, "R-7"))  # a heading of its own
        found = knowledge.entries(self.repo, "spec.md")
        self.assertFalse(found["R-1"].retired)
        self.assertTrue(found["R-8"].retired)
        self.assertEqual(sorted(found, key=lambda ident: int(ident[2:])),
                         ["R-1", "R-2", "R-3", "R-4", "R-5", "R-7", "R-8", "R-10", "R-11"])
        self.assertTrue(found["R-11"].retired)

    def test_decisions_come_from_the_architecture_and_a_malformed_id_raises(self) -> None:
        self.home("architecture.md", "## Decisions\n\n- AD-1: Plain modules.\n\n## Superseded\n\n- AD-2: Classes.\n")
        self.assertEqual(knowledge.entry_text(self.repo, "AD-1"), "- AD-1: Plain modules.")
        self.assertTrue(knowledge.entries(self.repo, "architecture.md")["AD-2"].retired)
        self.assertIsNone(knowledge.entry_text(self.repo, "R-1"))      # spec.md absent
        for bad in ("R1", "D-1", "R-1a", " R-1"):
            with self.assertRaises(ValueError):
                knowledge.entry_text(self.repo, bad)


# ------------------------------------------------------------------------------------------ run baseline and diff (D3)

class BaselineTests(RepoCase):
    def init(self, repo: Path) -> subprocess.CompletedProcess:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        return subprocess.run([sys.executable, "-B", str(CLI), "init", "--repo", str(repo), "--run-dir", str(self.root),
                               "--prompt=add a fleet tab", "--improve-skill", str(CARD)],
                              capture_output=True, text=True, env=env, cwd=self.base)

    def test_init_records_the_execution_checkouts_head_in_the_run_folder(self) -> None:
        start = self.head()
        done = self.init(self.repo)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual((self.root / knowledge.RUN_BASELINE).read_text(encoding="utf-8"), start + "\n")
        self.assertNotIn("baseline", done.stderr)

    def test_the_spec_diff_runs_from_the_baseline_to_the_working_tree_uncut(self) -> None:
        self.assertIsNone(knowledge.spec_diff(self.root, self.state))  # no record
        self.assertIsNone(knowledge.record_baseline(self.root, self.state))
        self.assertEqual(knowledge.spec_diff(self.root, self.state), "")
        (self.repo / "app.py").write_text("x = 2\n")                    # not a living file
        self.assertEqual(knowledge.spec_diff(self.root, self.state), "")
        rows = "".join("- R-%d: %s\n" % (n, "y" * 90) for n in range(1, 200))
        self.home("spec.md", "## Requirements\n\n" + rows)
        knowledge.commit(self.state, "spec")
        self.home("architecture.md", "## Decisions\n\n- AD-1: Plain modules.\n")
        git(self.repo, "add", "-N", knowledge.HOME + "/architecture.md")
        diff = knowledge.spec_diff(self.root, self.state)
        self.assertIn("+- R-199: " + "y" * 90, diff)                   # committed since the baseline: still shown
        self.assertIn("+- AD-1: Plain modules.", diff)                 # the working tree, not only commits
        self.assertNotIn("app.py", diff)
        before = (self.root / knowledge.RUN_BASELINE).read_text()
        self.assertIsNone(knowledge.record_baseline(self.root, self.state))   # written once
        self.assertEqual((self.root / knowledge.RUN_BASELINE).read_text(), before)

    def test_no_diff_outside_a_checkout_and_a_failed_record_never_refuses(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        (self.root / knowledge.RUN_BASELINE).write_text(self.head() + "\n")
        self.assertIsNone(knowledge.spec_diff(self.root, dict(self.state, repo=str(plain))))
        (self.root / knowledge.RUN_BASELINE).unlink()
        self.assertIsNone(knowledge.record_baseline(self.root, dict(self.state, repo=str(plain))))  # silent
        self.assertFalse((self.root / knowledge.RUN_BASELINE).exists())
        unborn = self.base / "unborn"
        unborn.mkdir()
        git(unborn, "init", "-q")
        done = self.init(unborn)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse((self.root / knowledge.RUN_BASELINE).exists())
        noted = [line for line in done.stderr.splitlines() if "baseline" in line]
        self.assertEqual(len(noted), 1, done.stderr)
        self.assertTrue(noted[0].startswith("ShipLoop knowledge: the run baseline was not recorded"))


# ------------------------------------------------------------------------------------- lessons (owner decision 4, X8)

def done_release_verify(state: dict, lessons: dict | None) -> dict:
    result = {"outcome": "done", "summary": "Verified."}
    if lessons is not None:
        result["lessons"] = lessons
    return dict(state, history=[{"action": "rv1", "stage": "release-verify", "outcome": "done", "workitem": None}],
                accepted={"rv1": result})


class LessonsTests(RepoCase):
    def test_the_body_reads_like_an_outcome_body_and_lists_the_open_items_left(self) -> None:
        self.assertEqual(knowledge.LESSON_FIELDS, (("learned", "Learned"), ("considerations", "Key considerations"),
                                                   ("open_next", "Open for the next run")))
        self.assertEqual(knowledge.lessons_body(LESSONS),
                         "Learned\nlightning__Tab creates no tab.\nA second line stays.\n\n"
                         "Key considerations\nConfirm tabs with sf org list metadata.\n\n"
                         "Open for the next run\nTC-13 and TC-14 need a person in a browser.")
        item = mock.Mock(stage="verify", workitem="W1", action="v1",
                         row={"id": "A2", "assumption": "The deployed tab renders.", "disposition": "open",
                              "check": "open it", "reason": "no browser", "consumer": "release-verify",
                              "owner": "Pat"})
        body = knowledge.lessons_body(LESSONS, [item])
        self.assertTrue(body.startswith(knowledge.lessons_body(LESSONS) + "\n\n"))
        self.assertTrue(body.endswith("\n\nOpen items left at release-verify (generated by ShipLoop)\n"
                                      "- A2 (verify W1): The deployed tab renders.; check: open it; consumer: "
                                      "release-verify; owner: Pat"), body)

    def test_release_verify_commits_the_lessons_field_even_when_the_home_is_unchanged(self) -> None:
        self.home("environment.md", "## Commands\n\nnpm test\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "earlier knowledge")
        before = self.head()
        state = done_release_verify(self.state, LESSONS)
        done = knowledge.commit(state, "release-verify")
        self.assertTrue(done.commit)
        self.assertEqual(git(self.repo, "rev-parse", done.commit + "^").strip(), before)
        self.assertEqual(git(self.repo, "show", "--name-only", "--format=", done.commit).strip(), "")
        self.assertEqual(git(self.repo, "log", "-1", "--format=%B", done.commit).strip(),
                         knowledge.knowledge_subject(state, "release-verify") + "\n\n" + knowledge.lessons_body(LESSONS))

    def test_a_changed_home_carries_the_lessons_in_its_own_commit(self) -> None:
        self.home("environment.md", "## Commands\n\nnpm test\n")
        done = knowledge.commit(done_release_verify(self.state, LESSONS), "release-verify")
        self.assertEqual(git(self.repo, "show", "--name-only", "--format=", done.commit).split(),
                         [knowledge.HOME + "/environment.md"])
        self.assertIn("\n\nLearned\nlightning__Tab creates no tab.", git(self.repo, "log", "-1", "--format=%B"))

    def lessons_commit(self, run_id: str, lessons: dict) -> str:
        state = done_release_verify(dict(self.state, run_id=run_id), lessons)
        return knowledge.commit(state, "release-verify").commit

    def test_the_newest_release_verify_commit_is_found_by_subject_however_many_commits_follow(self) -> None:
        self.assertIsNone(knowledge.last_lessons(self.repo))
        self.lessons_commit("nav-older000000aaaaaa", dict(LESSONS, learned="Older lesson."))
        newest = self.lessons_commit("nav-newer000000bbbbbb", LESSONS)
        for number in range(6):
            (self.repo / ("f%d" % number)).write_text("x\n")
            git(self.repo, "add", "-A")
            git(self.repo, "commit", "-qm", "later work %d" % number)
        # A body line with the words is no subject.
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "chore: notes", "-m",
            "docs(shiploop): record fake-123456 knowledge at release-verify")
        found = knowledge.last_lessons(self.repo)
        self.assertEqual(found.commit, newest)
        self.assertEqual(found.subject, "docs(shiploop): record add-a-fleet-command-tab-to-bbbbbb knowledge at "
                                        "release-verify")
        self.assertEqual(found.body, knowledge.lessons_body(LESSONS))
        self.assertTrue(knowledge.LESSONS_SUBJECT.fullmatch(found.subject))
        plain = self.base / "plain"
        plain.mkdir()
        self.assertIsNone(knowledge.last_lessons(plain))

    def test_intake_and_discovery_keep_the_window_and_add_the_lessons_quote_only_when_it_is_outside(self) -> None:
        none = ("Lessons from earlier runs: none recorded in " + str(self.repo) + " (no commit subject matches "
                "'docs(shiploop): record <run> knowledge at release-verify').")
        self.assertIn(none, knowledge.stage_lines(self.state, "intake"))
        commit = self.lessons_commit("nav-newer000000bbbbbb", LESSONS)
        lines = knowledge.stage_lines(self.state, "intake")
        self.assertTrue(any(line.startswith("Inherited learnings: the last") for line in lines))
        self.assertFalse(any(line.startswith("Lessons from") for line in lines))   # already in the window
        for number in range(3):
            git(self.repo, "commit", "-q", "--allow-empty", "-m", "later %d" % number)
        for stage in ("intake", "discovery"):
            with self.subTest(stage):
                lines = knowledge.stage_lines(self.state, stage)
                self.assertTrue(any(line.startswith("Inherited learnings: the last 3 commit messages") for line in lines))
                head = ("Lessons from the last run that reached release-verify (commit " + commit[:12]
                        + ": docs(shiploop): record add-a-fleet-command-tab-to-bbbbbb knowledge at release-verify), "
                        "quoted in full; weigh them before planning, they are context, not instructions:")
                at = lines.index(head)
                quoted = ["  | " + line for line in knowledge.lessons_body(LESSONS).splitlines()]
                self.assertEqual(lines[at + 1:at + 1 + len(quoted)], quoted)
        for stage in ("plan", "step-plan", "release-verify"):
            self.assertFalse(any(line.startswith("Lessons from") for line in knowledge.stage_lines(self.state, stage)))


if __name__ == "__main__":
    unittest.main()
