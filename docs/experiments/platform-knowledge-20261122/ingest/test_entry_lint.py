"""Unit tests for entry_lint.py, on small hand-written cards.

Usage: python3 -m unittest test_entry_lint   (from this folder)
"""

from __future__ import annotations

import contextlib
import importlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# Loaded by name after the path is set: the module sits beside this file.
entry_lint = importlib.import_module("entry_lint")

CONCERNS_SOURCE = (
    HERE.parents[3] / "skills" / "shiploop" / "scripts" / "shiploop_concerns.py"
)

GOOD = (
    "- **X-ONE** [state, config] A fact about the platform.\n"
    "  Decision: what the plan chooses. Proof: what would show it wrong.\n"
)
SOURCED_GOOD = (
    "- **X-ONE** [state] A fact. Decision: a choice. Proof: an observation.\n"
    "  Applies when: the plan lists `tool run`. Source: `notes/journal.md` F1,\n"
    '  "the tool refuses a second run". Kind: hard constraint.\n'
)


def card(planning: str, before: str = "# Card\n\nIntro.\n\n") -> str:
    return (
        before
        + "## Planning\n\n"
        + planning
        + "\n## Testing\n\n- **NOT-AN-ENTRY** text\n"
    )


class LintTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        (self.repo / "notes").mkdir()
        (self.repo / "notes" / "journal.md").write_text(
            "F1. Seen once: the tool\n   refuses a second run with an error.\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def findings(self, planning: str, sourced: bool = False) -> list:
        count, found = entry_lint.lint(card(planning), sourced, self.repo)
        self.assertIsNotNone(count)
        return found

    def assertOne(
        self, planning: str, entry_id: str, fragment: str, sourced: bool = False
    ) -> None:
        found = self.findings(planning, sourced)
        self.assertEqual(len(found), 1, found)
        self.assertEqual(found[0][0], entry_id)
        self.assertIn(fragment, found[0][1])

    def test_clean_card_has_no_findings(self) -> None:
        second = GOOD.replace("X-ONE", "X-TWO")
        self.assertEqual(self.findings(GOOD + second), [])
        self.assertEqual(entry_lint.lint(card(GOOD + second))[0], 2)

    def test_clean_sourced_card_has_no_findings(self) -> None:
        self.assertEqual(self.findings(SOURCED_GOOD, sourced=True), [])

    def test_sourced_parts_are_not_asked_without_the_flag(self) -> None:
        self.assertEqual(self.findings(GOOD, sourced=False), [])

    def test_only_the_planning_section_is_read(self) -> None:
        # The Testing section's bullet has no concerns or parts and is not reported.
        self.assertEqual(self.findings(GOOD), [])

    def test_no_bold_id(self) -> None:
        self.assertOne(
            "- [state] A fact. Decision: d. Proof: p.\n", "line 7", "no bold id"
        )

    def test_repeated_id(self) -> None:
        self.assertOne(GOOD + GOOD, "X-ONE", "id used again (first at line 7)")

    def test_no_concerns(self) -> None:
        self.assertOne(
            "- **X-ONE** A fact. Decision: d. Proof: p.\n", "X-ONE", "no concerns"
        )

    def test_empty_concern_list(self) -> None:
        self.assertOne(
            "- **X-ONE** [] A fact. Decision: d. Proof: p.\n", "X-ONE", "no concerns"
        )

    def test_unknown_concern(self) -> None:
        self.assertOne(
            "- **X-ONE** [state, testing] A fact. Decision: d. Proof: p.\n",
            "X-ONE",
            "'testing'",
        )

    def test_no_fact(self) -> None:
        self.assertOne(
            "- **X-ONE** [state] Decision: d. Proof: p.\n", "X-ONE", "no fact"
        )

    def test_missing_decision(self) -> None:
        self.assertOne(
            "- **X-ONE** [state] A fact. Proof: p.\n", "X-ONE", "no 'Decision:' part"
        )

    def test_empty_proof(self) -> None:
        self.assertOne(
            "- **X-ONE** [state] A fact. Decision: d. Proof:\n",
            "X-ONE",
            "empty 'Proof:' part",
        )

    def test_sourced_missing_applies_when(self) -> None:
        planning = SOURCED_GOOD.replace("Applies when: the plan lists `tool run`. ", "")
        self.assertOne(planning, "X-ONE", "no 'Applies when:' part", sourced=True)

    def test_sourced_missing_kind(self) -> None:
        self.assertOne(
            SOURCED_GOOD.replace(" Kind: hard constraint.", ""),
            "X-ONE",
            "no 'Kind:'",
            sourced=True,
        )

    def test_sourced_kind_outside_the_three(self) -> None:
        planning = SOURCED_GOOD.replace("hard constraint", "best practice")
        self.assertOne(planning, "X-ONE", "is not one of", sourced=True)

    def test_sourced_missing_source(self) -> None:
        planning = SOURCED_GOOD.replace(
            'Source: `notes/journal.md` F1,\n  "the tool refuses a second run". ', ""
        )
        self.assertOne(planning, "X-ONE", "no 'Source:' part", sourced=True)

    def test_source_names_no_file(self) -> None:
        planning = SOURCED_GOOD.replace("`notes/journal.md`", "the journal")
        self.assertOne(planning, "X-ONE", "names no file", sourced=True)

    def test_source_file_absent(self) -> None:
        planning = SOURCED_GOOD.replace("notes/journal.md", "notes/missing.md")
        self.assertOne(planning, "X-ONE", "does not exist", sourced=True)

    def test_source_file_outside_the_repo(self) -> None:
        planning = SOURCED_GOOD.replace("notes/journal.md", "../outside.md")
        self.assertOne(planning, "X-ONE", "outside the repo root", sourced=True)

    def test_quoted_phrase_not_in_the_file(self) -> None:
        planning = SOURCED_GOOD.replace("refuses a second run", "accepts a second run")
        self.assertOne(
            planning, "X-ONE", "which is not in notes/journal.md", sourced=True
        )

    def test_quoted_phrase_may_span_a_wrapped_line(self) -> None:
        # The journal breaks "the tool / refuses" across lines; the match ignores that.
        self.assertEqual(self.findings(SOURCED_GOOD, sourced=True), [])

    def test_backticked_text_inside_the_quote_is_not_the_path(self) -> None:
        (self.repo / "notes" / "journal.md").write_text(
            "it raises `Boom` at once\n", encoding="utf-8"
        )
        planning = SOURCED_GOOD.replace(
            '"the tool refuses a second run"', '"it raises `Boom` at once"'
        )
        self.assertEqual(self.findings(planning, sourced=True), [])

    def test_a_card_without_planning(self) -> None:
        self.assertEqual(
            entry_lint.lint("# Card\n\n## Testing\n\n- text\n"), (None, [])
        )

    def test_concern_list_matches_shiploop(self) -> None:
        if not CONCERNS_SOURCE.is_file():
            self.skipTest("shiploop_concerns.py not found at " + str(CONCERNS_SOURCE))
        sys.path.insert(0, str(CONCERNS_SOURCE.parent))
        try:
            import shiploop_concerns
        finally:
            sys.path.remove(str(CONCERNS_SOURCE.parent))
        self.assertEqual(entry_lint.CONCERN_IDS, shiploop_concerns.CONCERN_IDS)


class MainTest(unittest.TestCase):
    def run_main(self, text: str, *flags: str) -> tuple:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "card.md"
            path.write_text(text, encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = entry_lint.main([str(path), "--repo", tmp, *flags])
        return code, out.getvalue()

    def test_clean_exits_zero(self) -> None:
        code, out = self.run_main(card(GOOD))
        self.assertEqual(code, 0)
        self.assertIn("1 entries, no findings", out)

    def test_findings_exit_one_with_one_line_each(self) -> None:
        code, out = self.run_main(card("- **X-ONE** [nope] A fact.\n"))
        self.assertEqual(code, 1)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 3, lines)
        self.assertTrue(all(": X-ONE: " in line for line in lines), lines)

    def test_no_planning_section_says_so_and_exits_zero(self) -> None:
        code, out = self.run_main("# Card\n\n## Testing\n\nText.\n")
        self.assertEqual(code, 0)
        self.assertIn("no ## Planning section", out)

    def test_unreadable_card_exits_two(self) -> None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = entry_lint.main(["/nonexistent/card.md"])
        self.assertEqual(code, 2)
        self.assertIn("cannot be read", err.getvalue())


if __name__ == "__main__":
    unittest.main()
