#!/usr/bin/env python3
"""A retired ShipLoop term does not come back (owner, 2026-10-24: one term per concept; E2E SPEC S-16).

``skills/shiploop/references/glossary.md`` defines each term once and lists the retired ones, with a pattern, in a
block this suite reads through ``test/shiploop_e2e/glossary.py``. The suite scans the text a model reads -- ShipLoop's
SKILL.md, references, command cards and scripts, and the Improve skill's ShipLoop route files -- and refuses a retired
term outside the files its row allows. A rename therefore lands with its glossary row in the same commit, or this
suite fails on the old term's next use.
"""

from __future__ import annotations

import ast
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


def printed_strings(source: str) -> list[tuple[int, str]]:
    """(line, text) of each string a script can print: every literal (the parser already joins adjacent ones, so a
    phrase split across two literals on two lines is one text here) and every ``+`` chain of them, with a non-literal
    part read as one space.  Run 5 (2026-10-24) printed a retired phrase that the line scan missed for that split."""
    found: list[tuple[int, str]] = []

    def chain(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = chain(node.left), chain(node.right)
            if left is not None or right is not None:
                return (left if left is not None else " ") + (right if right is not None else " ")
        return None

    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Constant, ast.BinOp)):
            text = chain(node)
            if text:
                found.append((node.lineno, text))
    return found


def hits(terms: list[dict], root: Path = ROOT) -> list[str]:
    """``path:line: retired term (use ...)`` for each retired-term match outside its allowed files: in the file's
    lines and, for a script, in each string it can print (``printed_strings``)."""
    found = []
    for path in scanned(root):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        strings = printed_strings(text) if path.suffix == ".py" else []
        for term in terms:
            if relative in term["allow"]:
                continue
            for match in term["regex"].finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                found.append(f"{relative}:{line}: {term['retired']} (use {term['use']})")
            for line, string in strings:
                if term["regex"].search(string):
                    found.append(f"{relative}:{line}: {term['retired']} (use {term['use']})")
    return list(dict.fromkeys(found))


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

    def test_a_retired_phrase_split_across_two_literals_is_found(self) -> None:
        """Run 5 (2026-10-24): "then run the same complete " "command again" passed the line scan in two scripts."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            script = root / "skills" / "shiploop" / "scripts" / "planted.py"
            script.parent.mkdir(parents=True)
            script.write_text('def refusal(path):\n    return ("Restore " + path + ", then run the same complete "\n'
                              '            "command again.")\n', encoding="utf-8")
            (root / "skills" / "shiploop" / "SKILL.md").write_text("Card.\n", encoding="utf-8")
            found = hits(glossary.retired_terms(), root)
        self.assertEqual(found, ["skills/shiploop/scripts/planted.py:2: complete command (the callback) (use callback)"])

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
