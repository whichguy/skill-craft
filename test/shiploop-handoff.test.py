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
import html
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
        self.home("architecture.md", "## Decisions\n\n- AD-1: Plain modules.\n\n## Superseded decisions\n\n- AD-2: Classes.\n")
        self.assertTrue(knowledge.entries(self.repo, "architecture.md")["AD-2"].retired)   # the title starts with it
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


# ---------------------------------------------------------------------------------- hand-off fields: shapes (3, 0A)

import importlib.util  # noqa: E402
import types  # noqa: E402

import shiploop_assumptions as assumptions  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_workspace as workspace  # noqa: E402
import shiploop_unverified as unverified  # noqa: E402

CASE = {"id": "TC-1", "criterion": "C1", "requirement": "R-1", "oracle": "GET /api/new returns a game id",
        "red": "fails on the base: the route does not exist", "green": "200 with a game id"}
GOOD = {"follows": ("step-plan", ["R-1", "AD-2"]), "test_cases": ("test-spec", [CASE]),
        "lessons": ("release-verify", LESSONS),
        "not_covered": ("implement", [{"behaviour": "the helper rejects an empty board", "reason": "internal only"}])}


def canonical(value: dict, stage: str) -> dict:
    return navigator._canonical_result(value, stage=stage)


class HandoffShapeTests(unittest.TestCase):
    def refused(self, value: dict, stage: str) -> str:
        with self.assertRaises(navigator.NavigatorError) as caught:
            canonical(value, stage)
        return str(caught.exception)

    def test_the_state_version_is_six_and_a_version_five_run_is_refused_with_the_fresh_run_hint(self) -> None:
        self.assertEqual(navigator.STATE_VERSION, 6)
        state = navigator.new_state("/tmp/repo", "add hello")
        state["version"] = 5
        with self.assertRaises(navigator.NavigatorError) as caught:
            navigator.validate(state)
        self.assertIn(navigator.FRESH_RUN_HINT, str(caught.exception))

    def test_each_key_is_accepted_only_on_a_done_result_of_its_stage(self) -> None:
        for key, (stage, value) in GOOD.items():
            with self.subTest(key):
                done = canonical({"outcome": "done", "summary": "s", key: value}, stage)
                self.assertEqual(done[key], value)
                self.assertEqual(canonical(done, stage), done)               # a saved state reloads unchanged
                other = "verify" if stage != "verify" else "test"
                self.assertIn(key, self.refused({"outcome": "done", "summary": "s", key: value}, other))
                self.assertIn("belong to a done result",
                              self.refused({"outcome": "blocked", "summary": "s", "blocked_by": "user", key: value},
                                           stage))
        revise = self.refused({"outcome": "revise", "summary": "s", "test_cases": [CASE]}, "test-spec")
        self.assertIn("test_cases", revise)

    def test_each_key_shape_is_refused_with_the_route_free_ending(self) -> None:
        bad = [
            ("follows", "step-plan", "R-1"), ("follows", "step-plan", ["R1"]), ("follows", "step-plan", ["R-1", "R-1"]),
            ("follows", "step-plan", [3]),
            ("test_cases", "test-spec", "TC-1"), ("test_cases", "test-spec", [dict(CASE, surface="http")]),
            ("test_cases", "test-spec", [{k: v for k, v in CASE.items() if k != "red"}]),
            ("test_cases", "test-spec", [dict(CASE, oracle="  ")]), ("test_cases", "test-spec", [dict(CASE, id="TC 1")]),
            ("test_cases", "test-spec", [dict(CASE, criterion="C 1")]), ("test_cases", "test-spec", [CASE, CASE]),
            ("test_cases", "test-spec", [dict(CASE, requirement="the board")]),
            ("lessons", "release-verify", "learned a lot"),
            ("lessons", "release-verify", {"learned": "x", "considerations": "y"}),
            ("lessons", "release-verify", dict(LESSONS, learned=" \n ")),
            ("lessons", "release-verify", dict(LESSONS, open_next=None)),
            ("not_covered", "implement", {"behaviour": "b", "reason": "r"}),
            ("not_covered", "implement", [{"behaviour": "b"}]),
            ("not_covered", "implement", [{"behaviour": "b", "reason": ""}]),
        ]
        for key, stage, value in bad:
            with self.subTest(key=key, value=value):
                message = self.refused({"outcome": "done", "summary": "s", key: value}, stage)
                self.assertIn(key, message.splitlines()[0])
                self.assertTrue(message.splitlines()[0].endswith("then run the same command again."), message)

    def test_an_empty_follows_or_not_covered_is_a_valid_shape(self) -> None:
        self.assertEqual(canonical({"outcome": "done", "summary": "s", "follows": []}, "step-plan")["follows"], [])
        self.assertEqual(canonical({"outcome": "done", "summary": "s", "not_covered": []}, "implement")["not_covered"],
                         [])

    def test_open_items_are_allowed_at_the_new_stages_and_an_owner_only_there(self) -> None:
        self.assertEqual(assumptions.STAGES, frozenset(("plan", "test-spec", "verify", "carry-forward",
                                                        "system-test-author", "system-test", "release-plan",
                                                        "release-verify")))
        row = {"id": "A1", "assumption": "The tab renders.", "disposition": "open", "check": "open it",
               "reason": "no browser", "consumer": "release-verify", "owner": "Pat"}
        for stage in sorted(assumptions.STAGES - {"plan"}):
            with self.subTest(stage):
                done = canonical({"outcome": "done", "summary": "s", "assumptions": [row]}, stage)
                self.assertEqual(done["assumptions"], [row])
        self.assertIn("owner", self.refused({"outcome": "done", "summary": "s",
                                             "assumptions": [dict(row, consumer="W1")]}, "plan"))
        self.assertIn("owner", self.refused({"outcome": "done", "summary": "s",
                                             "assumptions": [dict(row, owner=" ")]}, "verify"))
        self.assertIn("assumptions", self.refused({"outcome": "done", "summary": "s", "assumptions": []}, "test"))


# ----------------------------------------------------------------------------------- hand-off gates (_handoff_gate)

def plan_row(action: str, item: str, focused: list, criteria: list) -> tuple:
    result = {"outcome": "done", "summary": "planned",
              "criteria": [{"id": c, "text": "criterion " + c} for c in criteria],
              "test_commands": ([{"command": "node --test", "suite": "focused", "ids": focused, "criteria": criteria}]
                                if focused else [])}
    return {"action": action, "stage": "step-plan", "workitem": item, "outcome": "done"}, result


def item_state(repo: Path, current: str, rows: list, stage: str) -> dict:
    """A run with two work items whose cursor is ``current`` at ``stage``; ``rows`` are (history row, result) pairs."""
    return {"repo": str(repo), "prompt": "Add a Fleet command tab.", "run_id": "nav-0123456789abcdef",
            "execution_mode": "navigator", "status": "active", "stage": "inner-loop",
            "work_items": [{"id": "W1", "title": "one"}, {"id": "W2", "title": "two"}],
            "work_index": 0 if current == "W1" else 1,
            "inner_loops": {current: {"stage": stage, "action": {"id": "nav-current", "stage": stage}}},
            "history": [row for row, _ in rows], "accepted": {row["action"]: result for row, result in rows},
            "revisions": {}}


class GateCase(RepoCase):
    """``_handoff_gate`` on the complete route at a run path whose result file is 173 characters long (X3)."""

    def setUp(self) -> None:
        super().setUp()
        self.home("spec.md", "## Requirements\n\n- R-1: Place a fleet.\n- **R-2** Reload keeps it.\n\n## Retired\n\n"
                             "- R-4: Dropped.\n")
        self.home("architecture.md", "## Decisions\n\n### AD-1 Plain modules\n\nWhy.\n")
        self.home("environment.md", "## Targets\n\nnode 22\n\n## Delivery\n\nnpm run deploy\n")  # heading variants

    def path_of(self, length: int, name: str) -> Path:
        """A result file path of exactly ``length`` characters, under the test's run folder."""
        stem = self.root / "inbox" / name
        pad = length - len(str(stem)) - 1
        self.assertGreater(pad, 0)
        return self.root / ("r" * pad) / "inbox" / name

    def steps(self) -> list:
        complete = self.path_of(173, "nav-current.md")
        final = self.path_of(173, "nav-current-final-result.md")
        return [("complete", navigator.NextStep(complete, "then run the same complete command again.", False)),
                ("improve-stage", navigator.NextStep(final, "then run the same complete command again.", False)),
                ("seed", navigator.NextStep(final, "then run the same complete command again with --final-result set "
                                                   "to that file.", True))]

    def refusal(self, state: dict, stage: str, result: dict, step=None) -> str:
        step = step or self.steps()[0][1]
        with self.assertRaises(navigator.NavigatorError) as caught:
            navigator._handoff_gate(self.root, state, stage, result, "complete", next_step=step)
        return str(caught.exception)

    def accepts(self, state: dict, stage: str, result: dict) -> None:
        navigator._handoff_gate(self.root, state, stage, result, "complete", next_step=self.steps()[0][1])

    def assert_line_one(self, message: str, step) -> None:
        """Line 1 is the fix, the one absolute path and the next step, inside 250 characters (the cut a model reads)."""
        first = message.splitlines()[0]
        if step.seed:
            self.assertTrue(first.startswith("Write a final result to " + str(step.path) + " that "), first)
            self.assertTrue(first.endswith(", " + step.tail), first)
            self.assertIn("then run the same complete", first[:250])   # the verb is inside the cut a model reads
        else:
            self.assertIn(str(step.path), first)
            self.assertTrue(first.endswith(", " + step.tail), first)
            self.assertLessEqual(len(first), 250, first)


def two_items(repo: Path, stage: str = "test-spec", current: str = "W2") -> dict:
    rows = [plan_row("sp1", "W1", ["TC-1", "TC-2"], ["C1", "C2"]), plan_row("sp2", "W2", ["TC-3"], ["C3"])]
    return item_state(repo, current, rows, stage)


class HandoffGateTests(GateCase):
    def test_step_plan_needs_follows_whose_ids_have_entries_in_the_living_files(self) -> None:
        state = item_state(self.repo, "W1", [], "step-plan")
        done = {"outcome": "done", "summary": "s"}
        message = self.refusal(state, "step-plan", done)
        self.assertTrue(message.startswith("Add follows to "), message)
        self.assertIn('"follows": ["R-3", "AD-2"]', message.splitlines()[1])
        self.accepts(state, "step-plan", dict(done, follows=[]))
        self.accepts(state, "step-plan", dict(done, follows=["R-1", "R-2", "AD-1", "R-4"]))   # retired still has an entry
        message = self.refusal(state, "step-plan", dict(done, follows=["R-1", "R-9", "AD-2"]))
        self.assertTrue(message.startswith("Fix the follows IDs in "), message)
        self.assertIn(str(self.repo / knowledge.HOME / "spec.md"), message.splitlines()[1])
        self.assertEqual(message.splitlines()[-1], "No entry: R-9, AD-2.")

    def test_a_wrong_type_is_a_refusal_with_its_route_not_a_crash(self) -> None:
        state = item_state(self.repo, "W1", [], "step-plan")
        message = self.refusal(state, "step-plan", {"outcome": "done", "summary": "s", "follows": "R-1"})
        self.assertIn("follows", message.splitlines()[0])

    def test_test_cases_match_this_items_focused_ids_both_ways_with_real_criteria_and_requirements(self) -> None:
        state = two_items(self.repo)
        done = {"outcome": "done", "summary": "s", "assumptions": []}
        case = dict(CASE, id="TC-3", criterion="C3")
        self.accepts(state, "test-spec", dict(done, test_cases=[case]))
        message = self.refusal(state, "test-spec", done)
        self.assertTrue(message.startswith("Add test_cases to "), message)
        self.assertEqual(message.splitlines()[-1], "Focused IDs: TC-3.")
        message = self.refusal(state, "test-spec", dict(done, test_cases=[case, dict(CASE, id="TC-1", criterion="C3")]))
        self.assertTrue(message.startswith("Fix the case IDs in "), message)        # W1's ID no longer counts
        self.assertIn("report revise", message)
        self.assertEqual(message.splitlines()[-1], "Not listed by a focused command of W2: TC-1.")
        message = self.refusal(state, "test-spec", dict(done, test_cases=[]))
        self.assertTrue(message.startswith("Add test_cases to "), message)
        first = item_state(self.repo, "W1", [plan_row("sp1", "W1", ["TC-1", "TC-2"], ["C1", "C2"])], "test-spec")
        message = self.refusal(first, "test-spec", dict(done, test_cases=[dict(CASE, criterion="C2")]))
        self.assertTrue(message.startswith("Add the missing cases to "), message)
        self.assertEqual(message.splitlines()[-1], "Focused IDs with no case: TC-2.")
        message = self.refusal(state, "test-spec", dict(done, test_cases=[dict(case, criterion="C9")]))
        self.assertTrue(message.startswith("Fix the case criteria in "), message)
        self.assertEqual(message.splitlines()[-1], "TC-3 names C9; the criteria are C3.")
        message = self.refusal(state, "test-spec", dict(done, test_cases=[dict(case, requirement="R-1 and R-12")]))
        self.assertTrue(message.startswith("Fix case requirements in "), message)
        self.assertEqual(message.splitlines()[-1], "TC-3 names R-12.")

    def test_an_item_with_no_focused_ids_needs_no_cases(self) -> None:
        state = item_state(self.repo, "W1", [plan_row("sp1", "W1", [], [])], "test-spec")
        self.accepts(state, "test-spec", {"outcome": "done", "summary": "s", "assumptions": []})
        self.accepts(state, "test-spec", {"outcome": "done", "summary": "s", "assumptions": [], "test_cases": []})

    def test_release_verify_needs_lessons_and_no_placeholder_is_accepted(self) -> None:
        state = item_state(self.repo, "W1", [], "release-verify")
        done = {"outcome": "done", "summary": "s", "assumptions": []}
        self.assertTrue(self.refusal(state, "release-verify", done).startswith("Add lessons to "))
        self.accepts(state, "release-verify", dict(done, lessons=LESSONS))
        template = navigator.HANDOFF_PLACEHOLDERS
        placeholder = dict(LESSONS, considerations=next(v for v in template if "risk" in v))
        message = self.refusal(state, "release-verify", dict(done, lessons=placeholder))
        self.assertTrue(message.startswith("Replace placeholders in "), message)
        self.assertEqual(message.splitlines()[-1], "Still a template placeholder: lessons.considerations.")

    def test_every_template_placeholder_is_refused(self) -> None:
        bare = {"repo": str(self.repo), "work_items": [], "history": [], "accepted": {}}
        shapes = str(navigator.HANDOFF_SHAPES)
        for value in navigator.HANDOFF_PLACEHOLDERS:
            self.assertTrue(value.startswith("<") and value.endswith(">"), value)
            self.assertIn(value, shapes)                       # every placeholder is one a printed shape carries
        self.assertIn(navigator.FOLLOWS_PLACEHOLDER, navigator._result_template(bare, "step-plan"))
        self.assertIn('"open_next": "<what a later run should pick up, or none>"',
                      navigator._result_template(bare, "release-verify"))
        # The aggressive re-cut (2026-10-11) puts each required hand-off key in the template itself; the fill line says a
        # blocked or other outcome drops them. implement's optional not_covered stays out.
        for stage in ("test-spec", "implement", "verify", "carry-forward"):
            printed = navigator._result_template(bare, stage)
            for key in ("test_cases", "not_covered", "assumptions", "lessons", "follows"):
                self.assertEqual('"' + key + '"' in printed, key in navigator._required_handoff_keys(stage),
                                 (stage, key))
        state = two_items(self.repo)
        oracle = next(v for v in navigator.HANDOFF_PLACEHOLDERS if "observes" in v)
        message = self.refusal(state, "test-spec", {"outcome": "done", "summary": "s", "assumptions": [],
                                                    "test_cases": [dict(CASE, id="TC-3", criterion="C3", oracle=oracle)]})
        self.assertEqual(message.splitlines()[-1], "Still a template placeholder: test_cases[0].oracle.")

    def test_open_items_at_the_new_stages_name_a_later_outer_stage_or_the_items_carry_forward(self) -> None:
        row = {"id": "A1", "assumption": "The tab renders.", "disposition": "open", "check": "open it",
               "reason": "no browser", "consumer": "release-verify"}
        done = {"outcome": "done", "summary": "s"}
        cases = {"test-spec": dict(done, test_cases=[dict(CASE, id="TC-3", criterion="C3")])}
        for stage in sorted(assumptions.STAGES - {"plan"}):
            with self.subTest(stage):
                state = two_items(self.repo, stage)
                result = dict(cases.get(stage, done), lessons=LESSONS) if stage == "release-verify" else cases.get(stage, done)
                message = self.refusal(state, stage, result)
                self.assertTrue(message.startswith("Add assumptions to "), message)
                later = [name for name in stage_spec.OUTER if stage_spec.STAGES.index(name) > stage_spec.STAGES.index(stage)]
                allowed = later + (["carry-forward"] if stage in ("test-spec", "verify") else [])
                for consumer in allowed:
                    self.accepts(state, stage, dict(result, assumptions=[dict(row, consumer=consumer)]))
                for consumer in ("W1", stage, "carry-forward", "intake"):
                    if consumer in allowed:
                        continue
                    message = self.refusal(state, stage, dict(result, assumptions=[dict(row, consumer=consumer)]))
                    self.assertTrue(message.startswith("Fix the consumers in "), message)
                    self.assertIn("A1 names '" + consumer + "'; the allowed consumers are " + ", ".join(sorted(allowed, key=stage_spec.STAGES.index)) + ".", message)

    def test_every_refusal_line_one_is_the_fix_the_result_path_and_the_next_step_on_each_route(self) -> None:
        state = two_items(self.repo)
        faults = [
            ("step-plan", item_state(self.repo, "W1", [], "step-plan"), {"outcome": "done", "summary": "s"}),
            ("step-plan", item_state(self.repo, "W1", [], "step-plan"),
             {"outcome": "done", "summary": "s", "follows": ["R-77"]}),
            ("test-spec", state, {"outcome": "done", "summary": "s", "assumptions": []}),
            ("test-spec", state, {"outcome": "done", "summary": "s", "assumptions": [],
                                  "test_cases": [dict(CASE, id="TC-9", criterion="C3")]}),
            ("test-spec", state, {"outcome": "done", "summary": "s", "assumptions": [],
                                  "test_cases": [dict(CASE, id="TC-3", criterion="C9")]}),
            ("test-spec", state, {"outcome": "done", "summary": "s", "assumptions": [],
                                  "test_cases": [dict(CASE, id="TC-3", criterion="C3", requirement="R-12")]}),
            ("test-spec", state, {"outcome": "done", "summary": "s",
                                  "test_cases": [dict(CASE, id="TC-3", criterion="C3")]}),
            ("verify", state, {"outcome": "done", "summary": "s", "assumptions": [
                {"id": "A1", "assumption": "x", "disposition": "open", "check": "c", "reason": "r", "consumer": "W1"}]}),
            ("verify", state, {"outcome": "done", "summary": "s", "assumptions": [
                {"id": "A1", "assumption": "x", "disposition": "evidenced", "evidence": ["/no/such/file"]}]}),
            ("release-verify", state, {"outcome": "done", "summary": "s", "assumptions": []}),
            ("release-verify", state, {"outcome": "done", "summary": "s", "assumptions": [],
                                       "lessons": dict(LESSONS, learned=next(v for v in navigator.HANDOFF_PLACEHOLDERS
                                                                               if "learned" in v))}),
        ]
        for route, step in self.steps():
            for stage, fault_state, result in faults:
                with self.subTest(route=route, stage=stage, result=result):
                    message = self.refusal(fault_state, stage, result, step)
                    self.assert_line_one(message, step)
                    self.assertGreaterEqual(len(message.splitlines()), 2, message)


# ------------------------------------------------------------------------------------------ CONSUMES and its resolver

EXPECTED_CONSUMES = {
    "intake": (), "discovery": (), "research": (), "spec": (), "test-strategy": ("spec_diff",),
    "plan": ("spec_diff",), "prepare": (), "step-plan": ("assumptions",),
    "test-spec": ("follows", "criteria", "test_commands"), "validate-existing": (),
    "implement": ("follows", "criteria", "test_cases"), "test": ("follows", "test_cases", "not_covered"),
    "document": ("follows", "spec_diff"), "verify": ("follows", "test_cases", "spec_diff"),
    "carry-forward": ("spec_diff", "assumptions"), "system-test-author": ("test_cases", "assumptions"),
    "system-test": ("system_commands", "assumptions"),
    "product-acceptance": ("system_commands", "spec_diff", "assumptions"),
    "release-plan": ("system_commands", "assumptions"), "release-check": ("assumptions",),
    "release": ("assumptions",), "release-verify": ("spec_diff", "assumptions"), "operations": ("assumptions",),
    "handoff": ("lessons", "assumptions"),
}
# The one stage that records each key with a single producer.  assumptions (every open-item stage) and spec_diff (the
# script, from the run baseline) have no single producer and are exempt.
PRODUCER = {"follows": "step-plan", "criteria": "step-plan", "test_commands": "step-plan", "test_cases": "test-spec",
            "not_covered": "implement", "system_commands": "system-test-author", "lessons": "release-verify"}


def open_row(ident: str, consumer: str, **extra) -> dict:
    return {"id": ident, "assumption": "It holds: " + ident, "disposition": "open", "check": "check " + ident,
            "reason": "not run", "consumer": consumer, **extra}


def row(action: str, stage: str, item, result: dict, outcome: str = "done") -> tuple:
    return {"action": action, "stage": stage, "workitem": item, "outcome": outcome}, dict(
        {"outcome": outcome, "summary": action}, **result)


class ConsumesTests(RepoCase):
    def test_every_stage_has_the_row_the_contract_names(self) -> None:
        self.assertEqual(dict(navigator.CONSUMES), EXPECTED_CONSUMES)
        self.assertEqual(set(navigator.CONSUMES), set(stage_spec.STAGES))
        keys = {key for row in EXPECTED_CONSUMES.values() for key in row} - {"spec_diff"}
        self.assertTrue(keys <= navigator._RESULT_KEYS, keys - navigator._RESULT_KEYS)

    def test_each_single_producer_is_in_the_consuming_stages_reads(self) -> None:
        for stage, keys in EXPECTED_CONSUMES.items():
            reads = [name.removeprefix("item:") for name in stage_spec.stage(stage).reads]
            for key in keys:
                if key in PRODUCER:
                    with self.subTest(stage=stage, key=key):
                        self.assertIn(PRODUCER[key], reads)

    def fixture(self, current_stage: str, current: str = "W2") -> dict:
        self.home("spec.md", "## Requirements\n\n- R-1: Place a fleet.\n  Ships may not overlap.\n- R-2: Reload.\n")
        self.home("architecture.md", "## Decisions\n\n- AD-1: Plain modules.\n")
        case1, case3 = dict(CASE, id="TC-1"), dict(CASE, id="TC-3", criterion="C3")
        rows = [
            row("p1", "plan", None, {"work_items": [{"id": "W1", "title": "one"}, {"id": "W2", "title": "two"}],
                                     "assumptions": [open_row("A1", "W2"), open_row("A9", "W1")]}),
            row("sp1", "step-plan", "W1", {"follows": ["R-1"], "criteria": [{"id": "C1", "text": "one"}],
                                           "test_commands": [{"command": "t", "suite": "focused", "ids": ["TC-1"]}]}),
            row("ts1", "test-spec", "W1", {"test_cases": [case1], "assumptions": [open_row("B1", "system-test")]}),
            row("im1", "implement", "W1", {"not_covered": []}),
            row("ve1", "verify", "W1", {"assumptions": [open_row("B2", "carry-forward")]}),
            row("cf1", "carry-forward", "W1", {"assumptions": []}),
            row("sp2", "step-plan", "W2", {"follows": ["R-1", "AD-1", "R-7"], "criteria": [{"id": "C3", "text": "c"}],
                                           "test_commands": [{"command": "t", "suite": "focused", "ids": ["TC-3"]},
                                                             {"command": "lint", "suite": "check"}]}),
            row("ts2", "test-spec", "W2", {"test_cases": [case3], "assumptions": [open_row("C1", "carry-forward"),
                                                                                    open_row("C2", "release-verify")]}),
            row("im2", "implement", "W2", {"not_covered": [{"behaviour": "b1", "reason": "r1"}]}),
            row("im3", "implement", "W2", {}),
        ]
        state = item_state(self.repo, current, rows, current_stage)
        return state

    def source(self, sources: list, key: str) -> list:
        return [found for found in sources if found.key == key]

    def test_item_stages_get_their_items_values_and_not_recorded_is_none(self) -> None:
        state = self.fixture("test")
        sources = navigator.handoff_sources(self.root, state, "test")
        self.assertEqual([found.key for found in sources], ["follows", "test_cases", "not_covered", "not_covered"])
        follows, = self.source(sources, "follows")
        self.assertEqual((follows.stage, follows.action, follows.workitem), ("step-plan", "sp2", "W2"))
        self.assertEqual(follows.value, [("R-1", "- R-1: Place a fleet.\n  Ships may not overlap."),
                                         ("AD-1", "- AD-1: Plain modules."), ("R-7", None)])
        cases, = self.source(sources, "test_cases")
        self.assertEqual((cases.action, cases.value), ("ts2", [dict(CASE, id="TC-3", criterion="C3")]))
        self.assertEqual([(found.action, found.value) for found in self.source(sources, "not_covered")],
                         [("im2", [{"behaviour": "b1", "reason": "r1"}]), ("im3", None)])
        sources = navigator.handoff_sources(self.root, state, "test-spec")
        self.assertEqual(self.source(sources, "criteria")[0].value, [{"id": "C3", "text": "c"}])
        self.assertEqual(self.source(sources, "test_commands")[0].value,
                         [{"command": "t", "suite": "focused", "ids": ["TC-3"]}])     # focused rows only
        verify = navigator.handoff_sources(self.root, state, "verify")
        self.assertEqual([found.key for found in verify], ["follows", "test_cases", "spec_diff"])
        self.assertIsNone(self.source(verify, "spec_diff")[0].value)                     # no baseline recorded

    def test_system_test_author_gets_every_items_latest_cases_and_outer_keys_come_from_their_producer(self) -> None:
        state = self.fixture("test")
        sources = navigator.handoff_sources(self.root, state, "system-test-author")
        self.assertEqual([(found.workitem, found.action, found.value) for found in self.source(sources, "test_cases")],
                         [("W1", "ts1", [dict(CASE, id="TC-1")]), ("W2", "ts2", [dict(CASE, id="TC-3", criterion="C3")])])
        system, = self.source(navigator.handoff_sources(self.root, state, "system-test"), "system_commands")
        self.assertEqual((system.stage, system.action, system.value), ("system-test-author", None, None))
        lessons, = self.source(navigator.handoff_sources(self.root, state, "handoff"), "lessons")
        self.assertEqual((lessons.stage, lessons.value), ("release-verify", None))

    def test_open_items_are_filtered_by_consumer_and_settled_by_the_consumers_later_done_result(self) -> None:
        state = self.fixture("test")
        ids = lambda found: [(item.stage, item.workitem, item.row["id"]) for item in found.value]  # noqa: E731
        step_plan = item_state(self.repo, "W2", [], "step-plan")
        step_plan.update(history=state["history"], accepted=state["accepted"])
        found, = self.source(navigator.handoff_sources(self.root, step_plan, "step-plan"), "assumptions")
        self.assertEqual(ids(found), [("plan", None, "A1")])
        found, = self.source(navigator.handoff_sources(self.root, state, "system-test"), "assumptions")
        self.assertEqual(ids(found), [("test-spec", "W1", "B1")])
        everything = [("plan", None, "A1"), ("plan", None, "A9"), ("test-spec", "W1", "B1"), ("test-spec", "W2", "C1"),
                      ("test-spec", "W2", "C2")]      # B2 is settled by W1's later carry-forward
        for stage in ("product-acceptance", "handoff", "carry-forward"):
            found, = self.source(navigator.handoff_sources(self.root, state, stage), "assumptions")
            self.assertEqual(ids(found), everything, stage)
        self.assertEqual([item.row for item in assumptions.open_items(state) if item.stage == "plan"],
                         unverified.open_assumptions(state))
        # system-test settles B1 by its done result; a B1 it carries forward is its own open row, listed once
        relisted = row("st1", "system-test", None, {"assumptions": [open_row("B1", "release-plan")]})
        again = dict(state, history=state["history"] + [relisted[0]], accepted=dict(state["accepted"], st1=relisted[1]))
        found = [(i.stage, i.workitem, i.row["id"], i.row["consumer"]) for i in assumptions.open_items(again)]
        self.assertNotIn(("test-spec", "W1", "B1", "system-test"), found)
        self.assertEqual([entry for entry in found if entry[2] == "B1"], [("system-test", None, "B1", "release-plan")])
        settles = row("rp1", "release-plan", None, {"assumptions": []})
        carried = dict(again, history=again["history"] + [settles[0]], accepted=dict(again["accepted"], rp1=settles[1]))
        self.assertNotIn("B1", [i.row["id"] for i in assumptions.open_items(carried)])
        # a consumer result accepted before the row was produced does not settle it
        early = row("st0", "system-test", None, {"assumptions": []})
        late = row("ts8", "test-spec", "W2", {"test_cases": [], "assumptions": [open_row("E1", "system-test")]})
        order = dict(state, history=state["history"] + [early[0], late[0]],
                     accepted=dict(state["accepted"], st0=early[1], ts8=late[1]))
        self.assertIn("E1", [i.row["id"] for i in assumptions.open_items(order)])
        settled = row("st1", "system-test", None, {"assumptions": []})
        done = dict(state, history=state["history"] + [settled[0]], accepted=dict(state["accepted"], st1=settled[1]))
        self.assertNotIn(("test-spec", "W1", "B1"), [(i.stage, i.workitem, i.row["id"]) for i in assumptions.open_items(done)])
        # a consumer with no assumptions field (release-verify has one; product-acceptance does not) settles by its done
        accepted = row("pa1", "product-acceptance", None, {})
        product = row("ts9", "test-spec", "W2", {"test_cases": [], "assumptions": [open_row("D1", "product-acceptance")]})
        later = dict(state, history=state["history"] + [product[0], accepted[0]],
                     accepted=dict(state["accepted"], ts9=product[1], pa1=accepted[1]))
        self.assertNotIn("D1", [i.row["id"] for i in assumptions.open_items(later)])

    def test_not_covered_comes_only_from_implement_steps_after_the_items_latest_step_plan(self) -> None:
        rows = [row("sp1", "step-plan", "W1", {"follows": [], "criteria": [{"id": "C1", "text": "one"}],
                                               "test_commands": [{"command": "t", "suite": "focused", "ids": ["TC-1"]}]}),
                row("im1", "implement", "W1", {"not_covered": [{"behaviour": "old", "reason": "before the replan"}]}),
                row("sp2", "step-plan", "W1", {"follows": [], "criteria": [{"id": "C1", "text": "one"}],
                                               "test_commands": [{"command": "t", "suite": "focused", "ids": ["TC-1"]}]}),
                row("im2", "implement", "W1", {"not_covered": []})]
        state = item_state(self.repo, "W1", rows, "test")
        found = self.source(navigator.handoff_sources(self.root, state, "test"), "not_covered")
        self.assertEqual([(entry.action, entry.value) for entry in found], [("im2", [])])

    def test_the_spec_diff_source_is_the_uncut_diff_since_the_run_baseline(self) -> None:
        state = self.fixture("document")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "home")
        knowledge.record_baseline(self.root, state)
        self.home("spec.md", "## Requirements\n\n- R-1: Place a fleet on a 10x10 board.\n")
        found, = self.source(navigator.handoff_sources(self.root, state, "document"), "spec_diff")
        self.assertIn("+- R-1: Place a fleet on a 10x10 board.", found.value)

    def test_an_unknown_stage_raises(self) -> None:
        with self.assertRaises(ValueError):
            navigator.handoff_sources(self.root, self.state, "select-work")

    def test_the_lessons_commit_lists_later_stages_open_items_but_not_the_plans(self) -> None:
        state = self.fixture("release-verify")
        self.assertEqual([(item.stage, item.row["id"]) for item in navigator._lessons_open_items(state)],
                         [("test-spec", "B1"), ("test-spec", "C1"), ("test-spec", "C2")])


# ------------------------------------------------------------------------------- the real CLI: refusal exits (routes)

def _load(name: str, filename: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, ROOT / "test" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_improve_cli = _load("shiploop_actual_improve_cli_for_handoff", "shiploop-actual-improve-cli.test.py")
import shiploop_inner_fixture as inner  # noqa: E402


class CompleteRouteTests(inner.RunDriver):
    def test_a_complete_refusals_named_exit_is_accepted_through_the_real_cli(self) -> None:
        self.start()
        state = self.drive_to("step-plan")
        result = inner.prepare(self.run_dir, state, dict(inner.DONE, paths=list(self.PATHS)))
        result.pop("follows", None)
        action = nav_action = navigator.current_action(state)["id"]
        path = self.run_dir / "inbox" / (action + ".md")
        path.parent.mkdir(exist_ok=True)
        store.write_record(path, result, "result")
        argv = [sys.executable, "-B", str(CLI), "complete", "--run-dir", str(self.run_dir), "--action", nav_action,
                "--result", str(path)]
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                   SHIPLOOP_PROGRESS="off", SHIPLOOP_KEEPALIVE="off")
        refused = subprocess.run(argv, capture_output=True, text=True, env=env)
        self.assertEqual(refused.returncode, 2, refused.stdout + refused.stderr)
        first = refused.stderr.splitlines()[0]
        self.assertEqual(first, "ShipLoop navigator: Add follows to " + str(path)
                         + ", then run the same complete command again.")
        store.write_record(path, dict(result, follows=[]), "result")      # the fix, then the same command
        accepted = subprocess.run(argv, capture_output=True, text=True, env=env)
        self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
        self.assertEqual(self.state()["active_improve"]["stage"], "step-plan")


class ImproveRouteTests(_improve_cli.ImproveCliFixture):
    def test_a_seed_refusal_on_the_improve_stage_complete_names_an_exit_the_real_cli_accepts(self) -> None:
        run = self.base / "parent-seed"
        self.invoke(_improve_cli.CLI, "init", "--repo", self.repo, "--run-dir", run, "--prompt",
                    "Synthetic predecessor navigation for the hand-off route.", "--improve-skill", _improve_cli.CARD)
        state = store.read_record(run / "state.md")
        while navigator.current_stage(state) != "step-plan":
            action = navigator.current_action(state)["id"]
            setup = {"outcome": "done", "summary": "Synthetic predecessor navigation only."}
            if navigator.current_stage(state) == "plan":
                setup["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state = navigator.apply(state, action, setup)
            if state.get("active_improve") is not None:
                state = navigator.finish_improve(state, action, {"summary": "Synthetic receipt only."})
        self.action = navigator.current_action(state)["id"]
        seed = {"outcome": "done", "summary": "A step plan without follows.", "evidence_refs": [],
                "test_commands": [], "test_commands_na": "Synthetic fixture; no test commands.", "paths": ["src/**"],
                "steps": [{"id": "S1", "task": "Make the planned change.", "paths": ["src/**"], "criteria": [],
                           "skills": []}],
                "expectations": [{"id": "E1", "state": "absent", "statement": "src/ does not exist yet.",
                                  "steps": ["S1"], "paths": ["src/**"], "check": "test ! -e src"}]}
        before = state
        state = navigator.apply(state, self.action, seed)        # the pure graph: the seed skipped complete's gates
        # complete's transition binds the recorded card and starts the review (owner, 2026-10-11); run it here too.
        state, writes, _payload = navigator._transition(inner.CORE, run, before, state)
        navigator.save(run, state, writes)
        self.run, self.state, self.parent_evidence_refs = run, state, []
        self.bind_current()
        packet = self.invoke(_improve_cli.CLI, "next", "--run-dir", run).stdout
        self.assertIn("revise at the INNER stages test-spec to verify", packet)   # X4: revise is a final outcome
        self.finish_ephemeral()
        flags, _receipt = self.completion_receipt()
        refused = self.invoke(_improve_cli.CLI, "complete", "--run-dir", run, "--action", self.improve, *flags,
                              status=2)
        final = run / "inbox" / (self.action + "-final-result.md")
        self.assertEqual(refused.stderr.splitlines()[0],
                         "ShipLoop navigator: Write a final result to " + str(final) + " that adds follows, then run "
                         "the same complete command again with --final-result set to that file.")
        store.write_record(final, dict(seed, follows=[]), "final result")
        self.invoke(_improve_cli.CLI, "complete", "--run-dir", run, "--action", self.improve, *flags,
                    "--final-result", final)
        after = store.read_record(run / "state.md")
        self.assertIsNone(after["active_improve"])
        self.assertEqual(after["accepted"][self.action]["follows"], [])


class ReportTests(RepoCase):
    """Consumer contract 4d (section 6.1): the completion report shows every hand-off a reader of the run needs.

    The run is walked with ``navigator.apply`` (pure, shape-checked) so each stage carries exactly the fields under test;
    expected values are literals written from section 6.1.
    """

    CASE = {"id": "TC-1", "criterion": "C1", "requirement": "R-1", "oracle": "GET /api/new returns a game",
            "red": "fails on the base", "green": "200 with a game id"}
    SYSTEM = {"command": "npm run e2e", "suite": "regression", "ids": ["ST-1"]}
    LESSONS = {"learned": "Board state lives in one Map.", "considerations": "Keep the server stateless.",
               "open_next": "Add a second player."}

    def setUp(self) -> None:
        super().setUp()
        self.home("spec.md", "## Requirements\n\n- R-1: Place a fleet.\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "living spec")
        (self.root / knowledge.RUN_BASELINE).write_text(git(self.repo, "rev-parse", "HEAD"), encoding="utf-8")
        self.home("spec.md", "## Requirements\n\n- R-1: Place a fleet.\n- R-2: Fire <a> shot & see it.\n")

    def walk(self, fields: dict, *, until: str = "done") -> dict:
        state = navigator.new_state(str(self.repo), "Add a Fleet command tab.", delegation="inline")
        for _ in range(120):
            here = navigator.current_stage(state)
            if here == until or state["status"] == "done":
                return state
            extra = dict(fields.get(here, {}))
            if here == "plan":
                extra.setdefault("work_items", [{"id": "W1", "title": "one", "context": "context"}])
                extra.setdefault("assumptions", [])
            if here == "step-plan":
                extra.setdefault("steps", [{"id": "S1", "task": "Make it.", "paths": ["src/**"], "criteria": ["C1"],
                                            "skills": []}])
                extra.setdefault("criteria", [{"id": "C1", "text": "It works. Confirm by: the focused command"}])
                extra.setdefault("test_commands", [{"command": "node --test", "suite": "focused", "ids": ["TC-1"],
                                                    "criteria": ["C1"]}])
            action = navigator.current_action(state)["id"]
            state = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic", **extra})
            if state.get("active_improve") is not None:
                state = navigator.finish_improve(state, action, {"summary": "Synthetic review"})
        self.fail("the walk did not reach " + until)

    FULL = {
        "step-plan": {"follows": ["R-1"]},
        "test-spec": {"test_cases": [CASE], "assumptions": [
            {"id": "A1", "assumption": "the deploy target accepts <html>", "disposition": "open",
             "check": "deploy and load the page", "reason": "no target here", "consumer": "release",
             "owner": "Dana"}]},
        "implement": {"not_covered": [{"behaviour": "the helper rejects an empty board", "reason": "internal"}]},
        "system-test-author": {"system_commands": [SYSTEM]},
        "release-verify": {"lessons": LESSONS},
    }

    def section(self, report: str, heading: str) -> str:
        start = report.index("<h2>" + heading + "</h2>")
        end = report.find("<h2>", start + 1)
        return report[start:end if end != -1 else len(report)]

    def test_the_report_shows_spec_diff_item_handoffs_open_items_system_tests_and_lessons(self) -> None:
        state = self.walk(self.FULL, until="release")
        report = navigator._render_report(state, self.root)
        baseline = (self.root / knowledge.RUN_BASELINE).read_text().strip()
        diff = self.section(report, "Spec and architecture changes")
        self.assertIn("baseline " + baseline[:12], diff)
        self.assertIn("+- R-2: Fire &lt;a&gt; shot &amp; see it.", diff)
        items = self.section(report, "Work item hand-offs")
        self.assertIn("<h3>W1 one</h3>", items)
        self.assertIn("Follows: R-1", items)
        self.assertIn("<td>TC-1</td><td>C1</td><td>R-1</td><td>GET /api/new returns a game</td><td>fails on the base</td>"
                      "<td>200 with a game id</td>", items)
        self.assertIn("Not covered by a test case (W1 implement S1): the helper rejects an empty board (internal)", items)
        opened = self.section(report, "Open items")
        self.assertIn("<td>test-spec W1</td><td>A1</td><td>the deploy target accepts &lt;html&gt;</td>"
                      "<td>deploy and load the page</td><td>no target here</td><td>release</td><td>Dana</td>", opened)
        system = self.section(report, "System tests")
        self.assertIn("<td>npm run e2e</td><td>regression</td><td>ST-1</td>", system)
        self.assertNotIn("<h2>Lessons</h2>", report)            # release-verify has not run yet: omitted
        done = self.walk(self.FULL)
        lessons = self.section(navigator._render_report(done, self.root), "Lessons")
        for label, key in (("Learned", "learned"), ("Key considerations", "considerations"),
                           ("Open for the next run", "open_next")):
            self.assertIn(label + "\n" + self.LESSONS[key], lessons)

    def test_a_stage_that_ran_without_the_field_says_not_recorded_and_one_that_never_ran_is_omitted(self) -> None:
        early = navigator._render_report(self.walk({}, until="step-plan"), self.root)
        for heading in ("Work item hand-offs", "System tests", "Lessons"):
            self.assertNotIn("<h2>" + heading + "</h2>", early)
        report = navigator._render_report(self.walk({}, until="handoff"), self.root)
        items = self.section(report, "Work item hand-offs")
        self.assertIn("Follows: not recorded", items)
        self.assertIn("Test cases: not recorded", items)
        self.assertIn("Not covered by a test case (W1 implement S1): not recorded", items)
        self.assertIn("System tests: not recorded", self.section(report, "System tests"))
        self.assertIn("Lessons: not recorded", self.section(report, "Lessons"))
        self.assertIn("None open.", self.section(report, "Open items"))

    def test_every_value_is_escaped(self) -> None:
        hostile = "<script>alert(1)</script>"
        fields = {"step-plan": {"follows": ["R-1"]},
                  "test-spec": {"test_cases": [dict(self.CASE, oracle=hostile)], "assumptions": []},
                  "implement": {"not_covered": [{"behaviour": hostile, "reason": hostile}]},
                  "system-test-author": {"system_commands": [dict(self.SYSTEM, command="echo " + hostile)]},
                  "release-verify": {"lessons": dict(self.LESSONS, learned=hostile)}}
        report = navigator._render_report(self.walk(fields), self.root)
        self.assertNotIn(hostile, report)
        self.assertIn(html.escape(hostile), report)


_return_review = _load("shiploop_return_review_for_handoff", "shiploop-return-review.test.py")
import shiploop_store as store  # noqa: E402


class LessonsReturnTests(_return_review.ReturnReviewCase):
    """The release-verify lessons commit reaches the user's branch on an isolated run (X1), through the real CLI."""

    LIVING = "# Living spec\n\n- R-1 one\n- R-2 two\n"

    def return_all(self, root: Path) -> None:
        self.plan_return(root)
        self.review(root, "--keep", *self.dispositions(root))
        self.do_return(root)

    def complete(self, run: Path, code: int = 0):
        state = store.read_record(run / "state.md")
        action = navigator.current_action(state)
        result = run / "inbox" / f"{action['id']}.md"
        store.write_record(result, {"outcome": "done", "summary": "Handed off."}, "ShipLoop navigator result")
        return self.cli("complete", "--run-dir", str(run), "--action", action["id"], "--result", str(result), code=code)

    def test_an_isolated_release_verify_that_changes_no_home_file_returns_its_lessons_commit_and_hands_off(self) -> None:
        """Consumer contract X1 end to end (moved from the retired shiploop-retire suite): the lessons commit is empty when
        release-verify changed no home file; the follow-up return still carries it to the source branch, so handoff sees a
        current receipt and the next run's intake finds the lessons there."""
        root, worktree = self.start("empty lessons")
        self.write(worktree, "app.js", "product\n")
        self.write(worktree, "docs/shiploop/spec.md", self.LIVING)
        self.commit(worktree, "work item and knowledge")
        run = self.at(root, "release")
        self.return_all(root)
        state = store.read_record(run / "state.md")
        state = navigator.apply(state, navigator.current_action(state)["id"], {"outcome": "done", "summary": "Released."})
        lessons = {"learned": "The empty commit still travels.", "considerations": "none", "open_next": "none"}
        before = state
        after = navigator.apply(state, navigator.current_action(state)["id"], {
            "outcome": "done", "summary": "Verified.", "lessons": lessons, "assumptions": []})
        navigator.save(run, after)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            navigator._knowledge_close(before, after, run)                 # what dispatch runs after the save
        self.assertIn("returned the knowledge commit with the earlier work (fast-forward-merge)", printed.getvalue())
        head = self.git("rev-parse", "HEAD", cwd=worktree).stdout.strip()
        self.assertEqual(self.git("rev-parse", "HEAD").stdout.strip(), head)
        self.assertEqual(self.git("show", "--name-only", "--format=", head).stdout.strip(), "")   # an empty commit
        found = knowledge.last_lessons(self.repo)
        self.assertEqual((found.commit, found.body), (head, knowledge.lessons_body(lessons)))
        navigator.save(run, navigator.apply(after, navigator.current_action(after)["id"],
                                            {"outcome": "done", "summary": "Operations ready."}))
        self.assertEqual(navigator.current_stage(store.read_record(run / "state.md")), "handoff")
        done = self.complete(run)                                          # no stale-return refusal
        self.assertNotIn("stale", done.stderr)
        self.assertEqual(store.read_record(run / "state.md")["status"], "done")

    def test_a_working_tree_return_reaches_done_and_the_report_prints_the_lessons_commit_message_to_commit(self) -> None:
        """Consumer contract X2: a working-tree return applies files, not commits, so the lessons commit never reaches the
        source branch.  The completion report prints the exact message and tells the user to commit it."""
        root, worktree = self.start("working tree lessons")
        self.write(worktree, "app.js", "product\n")
        self.write(worktree, "scratch.log", "run-local\n")
        self.write(worktree, "docs/shiploop/spec.md", self.LIVING)
        self.commit(worktree, "work item and knowledge")
        run = self.at(root, "release")
        self.plan_return(root)
        self.review(root, "--keep", *[path for path in self.dispositions(root) if path != "scratch.log"])
        self.review(root, "--exclude", "scratch.log")
        self.do_return(root)
        self.assertEqual(workspace.return_kind(root), "working-tree-return")
        state = store.read_record(run / "state.md")
        state = navigator.apply(state, navigator.current_action(state)["id"], {"outcome": "done", "summary": "Released."})
        lessons = {"learned": "A working-tree return carries <files>, not commits.", "considerations": "none",
                   "open_next": "none"}
        before = state
        after = navigator.apply(state, navigator.current_action(state)["id"], {
            "outcome": "done", "summary": "Verified.", "lessons": lessons, "assumptions": []})
        navigator.save(run, after)
        with contextlib.redirect_stdout(io.StringIO()):
            navigator._knowledge_close(before, after, run)
        message = self.git("log", "-1", "--format=%B", cwd=worktree).stdout.strip()
        self.assertTrue(message.startswith(knowledge.knowledge_subject(after, "release-verify")), message)
        self.assertNotIn(message.splitlines()[0], self.git("log", "--format=%s").stdout)   # not on the source branch
        navigator.save(run, navigator.apply(after, navigator.current_action(after)["id"],
                                            {"outcome": "done", "summary": "Operations ready."}))
        self.complete(run)
        self.assertEqual(store.read_record(run / "state.md")["status"], "done")
        report = (run / "report.html").read_text(encoding="utf-8")
        self.assertIn("This run&#x27;s commits did not reach main (working-tree return). Commit the returned files, or make "
                      "an empty commit when there are none, with exactly this message, so the next run&#x27;s intake "
                      "quotes the lessons:", report)
        self.assertIn("<pre>" + html.escape(message) + "</pre>", report)

    def test_handoff_makes_no_retire_commit_and_leaves_an_old_feature_folder_untouched(self) -> None:
        """Consumer contract 4c: the retire step is gone.  An earlier version's feature folder in the repository is history:
        handoff neither removes nor rewrites it, and no commit after the return is ShipLoop's retire."""
        old = {"docs/shiploop/features/old-run-aaaaaa/spec.md": "Adds: R-1.\n",
               "docs/shiploop/features/README.md": "# Features\n\nShipLoop writes this list from the folders beside it\n",
               "docs/shiploop/test-strategy.md": "# Test strategy\n", "docs/shiploop/README.md": "# Home\n"}
        for relative, text in old.items():
            path = self.repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "an earlier ShipLoop version's home")
        root, worktree = self.start("no retire")
        own = "docs/shiploop/features/" + knowledge.run_label(store.read_record(root / "run" / "state.md")) + "/spec.md"
        self.write(worktree, "app.js", "product\n")
        self.write(worktree, "docs/shiploop/spec.md", self.LIVING)
        self.write(worktree, own, "Adds: R-1.\n")       # what an earlier version's retire would have removed at handoff
        self.commit(worktree, "work item and knowledge")
        old[own] = "Adds: R-1.\n"
        run = self.at(root, "handoff")
        self.return_all(root)
        self.write(worktree, "docs/shiploop/environment.md", "# Environment\n")   # a knowledge commit at the handoff
        done = self.complete(run)
        self.assertEqual(store.read_record(run / "state.md")["status"], "done")
        self.assertNotIn("feature spec", done.stdout + done.stderr)
        subjects = self.git("log", "--format=%s").stdout.splitlines()
        self.assertFalse([subject for subject in subjects if subject.startswith("docs(shiploop): retire ")], subjects)
        for relative, text in old.items():
            self.assertEqual((self.repo / relative).read_text(encoding="utf-8"), text)


if __name__ == "__main__":
    unittest.main()
