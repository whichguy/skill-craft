#!/usr/bin/env python3
"""A retired ShipLoop term does not come back (owner, 2026-10-24: one term per concept; E2E SPEC S-16).

``skills/shiploop/references/glossary.md`` defines each term once and lists the retired ones, with a pattern, in a
block this suite reads through ``test/shiploop_e2e/glossary.py``. The suite scans the text a model reads -- ShipLoop's
SKILL.md, references, command cards and scripts, and the Improve skill's ShipLoop route files -- and refuses a retired
term outside the files its row allows. A rename therefore lands with its glossary row in the same commit, or this
suite fails on the old term's next use.
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "test" / "shiploop_e2e"))

import glossary  # noqa: E402

SHIPLOOP = ROOT / "skills" / "shiploop"
IMPROVE_REFERENCES = ROOT / "skills" / "improve" / "references"


def scanned(root: Path = ROOT) -> list[Path]:
    """The files a model reads: ShipLoop's card, references, commands and scripts, and Improve's ShipLoop route files."""
    shiploop = root / "skills" / "shiploop"
    files = [shiploop / "SKILL.md", *sorted((shiploop / "references").rglob("*.md")),
             *sorted((shiploop / "commands").glob("*.md")), *sorted((shiploop / "scripts").glob("*.py")),
             *sorted((root / "skills" / "improve" / "references").glob("shiploop-*.md"))]
    return [path for path in files if path.is_file() and path.name != "glossary.md"]


def hits(terms: list[dict], root: Path = ROOT) -> list[str]:
    """``path:line: retired term (use ...)`` for each retired-term match outside its allowed files."""
    found = []
    for path in scanned(root):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        for term in terms:
            if relative in term["allow"]:
                continue
            for match in term["regex"].finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                found.append(f"{relative}:{line}: {term['retired']} (use {term['use']})")
    return found


class RetiredTermTests(unittest.TestCase):
    def test_the_glossary_lists_its_retired_terms_in_the_block_the_suite_reads(self) -> None:
        terms = glossary.retired_terms()
        self.assertGreaterEqual(len(terms), 8)
        self.assertEqual(len({term["retired"] for term in terms}), len(terms), "a retired term is listed once")
        for term in terms:
            with self.subTest(term=term["retired"]):
                for allowed in term["allow"]:
                    path = ROOT / allowed
                    self.assertTrue(path.is_file(), f"{allowed}: an allowed file must exist")
                    # An allowance that no longer matches has gone stale: drop it.
                    self.assertRegex(path.read_text(encoding="utf-8"), term["regex"])

    def test_no_retired_term_appears_in_the_text_a_model_reads(self) -> None:
        self.assertEqual(hits(glossary.retired_terms()), [])

    def test_a_planted_retired_term_is_found_with_its_file_and_line(self) -> None:
        """The scan finds a term the moment it returns, in the text a model reads."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            card = root / "skills" / "shiploop" / "references" / "planted.md"
            card.parent.mkdir(parents=True)
            card.write_text("A line.\nName an expected-RED control here.\n", encoding="utf-8")
            (root / "skills" / "shiploop" / "SKILL.md").write_text("Card.\n", encoding="utf-8")
            found = hits(glossary.retired_terms(), root)
        self.assertEqual(found, ["skills/shiploop/references/planted.md:2: expected-RED (a baseline repair) "
                                 "(use expected failure)"])

    def test_a_malformed_block_is_refused_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "glossary.md"
            path.write_text('```json retired-terms\n[{"retired": "x"}]\n```\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "needs exactly retired, use, since, pattern, allow"):
                glossary.retired_terms(path)
            path.write_text("no block here\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "no ```json retired-terms block"):
                glossary.retired_terms(path)

    def test_every_glossary_term_is_defined_once(self) -> None:
        text = glossary.GLOSSARY.read_text(encoding="utf-8")
        table = text.split("## Terms", 1)[1].split("\n## ", 1)[0]
        names = [row.split("|")[1].strip() for row in table.splitlines()
                 if row.startswith("| ") and not row.startswith("| Term ") and not re.match(r"^\|[-|\s]+$", row)]
        self.assertGreaterEqual(len(names), 20)
        self.assertEqual(sorted({name for name in names if names.count(name) > 1}), [])


if __name__ == "__main__":
    unittest.main()
