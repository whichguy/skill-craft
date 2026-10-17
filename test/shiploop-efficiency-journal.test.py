#!/usr/bin/env python3
"""The ShipLoop efficiency journal's rows are well formed (efficiency plan G-NOTE, unit U5).

Every result of the efficiency work is a dated row. Rows live in two places and this suite reads both:

* the journal, ``docs/shiploop-efficiency-journal-2026-10-16.md``, when the checkout has it (it is merged from the docs branch);
* the row fragments each unit writes to its own file under ``docs/experiments/shiploop-eff-journal-rows/`` (the integrator folds
  them into the journal; two units never edit the same file).

A row is a heading ``### YYYY-MM-DD <unit> <title>`` followed by ``- key: value`` bullets. Required: ``status`` (firm, interim,
exploratory or superseded), ``snapshot`` (the git sha measured), ``fixture``, ``run-dir length`` (a number of characters, or
``n/a``), ``unit``, ``evidence`` (at least one path that exists in this repository: evidence kept only in a scratchpad is
purged), and ``key learning``. A fragment row also names its ``exit items``, ``suites run`` and ``suites skipped`` (with the
reason). A superseded row stays and names what replaced it and why (``superseded by``): a claim is edited, never deleted.

The checks run on the rows the checkout has and on synthetic rows, so a missing journal does not make the suite empty.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "docs" / "shiploop-efficiency-journal-2026-10-16.md"
FRAGMENTS = ROOT / "docs" / "experiments" / "shiploop-eff-journal-rows"
STATUSES = ("firm", "interim", "exploratory", "superseded")
ROW_HEADING = re.compile(r"^### (?P<date>\d{4}-\d{2}-\d{2})\b(?P<rest>.*)$", re.M)
BULLET = re.compile(r"^- (?P<key>[a-z][a-z -]*?):[ \t]*(?P<value>.*)$")
SHA = re.compile(r"^[0-9a-f]{7,40}$")
UNIT = re.compile(r"^(?:U\d+[a-z]?\*?|UE|UP|INT|round-0|final)(?:, ?(?:U\d+[a-z]?\*?|UE|UP|INT))*$")
REQUIRED = ("status", "snapshot", "fixture", "run-dir length", "unit", "evidence", "key learning")
FRAGMENT_REQUIRED = ("exit items", "suites run", "suites skipped")
PATH = re.compile(r"`([^`\s]+)`")


def parse_rows(text: str, source: str) -> list[dict]:
    """The rows of a markdown text: ``{"source", "date", "title", "fields"}`` for each ``### <date>`` heading, with its
    ``- key: value`` bullets (a bullet continues on the indented lines under it) as ``fields``."""
    rows = []
    heads = list(ROW_HEADING.finditer(text))
    for index, head in enumerate(heads):
        end = heads[index + 1].start() if index + 1 < len(heads) else len(text)
        next_heading = re.search(r"^#{1,3} ", text[head.end():end], re.M)  # a later non-row heading ends the row
        body = text[head.end():head.end() + next_heading.start()] if next_heading else text[head.end():end]
        fields: dict[str, str] = {}
        key = None
        for line in body.splitlines():
            found = BULLET.match(line)
            if found:
                key = found.group("key").strip()
                fields[key] = found.group("value").strip()
            elif key and line.startswith((" ", "\t")) and line.strip():
                fields[key] += " " + line.strip()
        rows.append({"source": source, "date": head.group("date"), "title": head.group("rest").strip(), "fields": fields})
    return rows


def problems(row: dict, fragment: bool, root: Path = ROOT) -> list[str]:
    """What is wrong with one row (an empty list when it is well formed)."""
    fields, found = row["fields"], []
    for key in (*REQUIRED, *(FRAGMENT_REQUIRED if fragment else ())):
        if not fields.get(key):
            found.append(f"missing {key}")
    if fields.get("status") and fields["status"].split()[0] not in STATUSES:
        found.append(f"status {fields['status']!r} is not one of {', '.join(STATUSES)}")
    if fields.get("snapshot") and not SHA.match(fields["snapshot"].split()[0]):
        found.append(f"snapshot {fields['snapshot']!r} is not a git sha")
    if fields.get("run-dir length") and not re.fullmatch(r"\d+|n/a", fields["run-dir length"].split()[0]):
        found.append(f"run-dir length {fields['run-dir length']!r} is not a number or n/a")
    if fields.get("unit") and not UNIT.match(fields["unit"]):
        found.append(f"unit {fields['unit']!r} is not a unit id")
    if fields.get("evidence"):
        paths = PATH.findall(fields["evidence"])
        if not any((root / p).exists() for p in paths if not p.startswith(("/", "SP/"))):
            found.append("evidence names no path that exists in this repository")
    if fields.get("status", "").startswith("superseded") and not fields.get("superseded by"):
        found.append("a superseded row must say what superseded it and why (superseded by)")
    return found


def rows_here() -> list[tuple[dict, bool]]:
    """Every row this checkout has, with whether it is a fragment row."""
    rows = []
    if JOURNAL.is_file():
        rows += [(row, False) for row in parse_rows(JOURNAL.read_text(), "journal")]
    for path in sorted(FRAGMENTS.glob("*.md")) if FRAGMENTS.is_dir() else []:
        rows += [(row, True) for row in parse_rows(path.read_text(), str(path.relative_to(ROOT)))]
    return rows


GOOD = """# Journal

### 2026-10-17 U5b measurement and ledger
- status: interim
- snapshot: da9e2e75
- fixture: node-fix-bug, offline
- run-dir length: 83
- unit: U5b
- evidence: `test/shiploop_e2e/arms.py`
- exit items: 1 met, 2 met
- suites run: shiploop-e2e-slice
- suites skipped: shiploop-chain (not in the footprint)
- key learning: the first line of the learning
  continues here.
"""


class RowParserTests(unittest.TestCase):
    def test_a_row_is_its_heading_and_its_bullets(self) -> None:
        (row,) = parse_rows(GOOD, "x")
        self.assertEqual((row["date"], row["title"]), ("2026-10-17", "U5b measurement and ledger"))
        self.assertEqual(row["fields"]["unit"], "U5b")
        self.assertEqual(row["fields"]["key learning"], "the first line of the learning continues here.")

    def test_a_good_row_has_no_problems_as_a_fragment_and_as_a_journal_row(self) -> None:
        (row,) = parse_rows(GOOD, "x")
        self.assertEqual(problems(row, fragment=True), [])
        self.assertEqual(problems(row, fragment=False), [])

    def test_each_required_field_is_required(self) -> None:
        for key in (*REQUIRED, *FRAGMENT_REQUIRED):
            with self.subTest(key=key):
                text = "\n".join(line for line in GOOD.splitlines() if not line.startswith(f"- {key}:"))
                (row,) = parse_rows(text, "x")
                found = problems(row, fragment=True)
                self.assertTrue(any(f"missing {key}" in p for p in found), found)

    def test_a_journal_row_does_not_need_the_fragment_fields(self) -> None:
        text = "\n".join(line for line in GOOD.splitlines() if not line.startswith(("- exit items", "- suites")))
        (row,) = parse_rows(text, "x")
        self.assertEqual(problems(row, fragment=False), [])
        self.assertTrue(problems(row, fragment=True))

    def test_bad_values_are_named(self) -> None:
        cases = {"status": ("- status: probably", "status"), "snapshot": ("- snapshot: main", "snapshot"),
                 "run-dir length": ("- run-dir length: long", "run-dir length"), "unit": ("- unit: five", "unit"),
                 "evidence": ("- evidence: `docs/not-a-file.md`", "evidence"), "scratchpad": ("- evidence: `SP/v9/x`", "evidence")}
        for name, (line, word) in cases.items():
            with self.subTest(name):
                key = line.split(":")[0]
                text = "\n".join(line if row_line.startswith(key) else row_line for row_line in GOOD.splitlines())
                (row,) = parse_rows(text, "x")
                self.assertTrue(any(word in p for p in problems(row, fragment=True)), problems(row, fragment=True))

    def test_the_test_economy_unit_is_a_unit_id(self) -> None:
        # The economy units (UE, UP) are not in the plan's numbered list, but their rows are a unit's row like any other.
        for unit in ("UE", "UE, INT", "U7, UE", "UP", "UP, INT", "U7, UP"):
            self.assertTrue(UNIT.match(unit), unit)
        self.assertFalse(UNIT.match("UF"))

    def test_a_superseded_row_stays_and_names_its_successor(self) -> None:
        text = GOOD.replace("- status: interim", "- status: superseded")
        (row,) = parse_rows(text, "x")
        self.assertTrue(any("superseded by" in p for p in problems(row, fragment=True)))
        (kept,) = parse_rows(text + "- superseded by: 2026-10-18 U31, the paired round measured it\n", "x")
        self.assertEqual(problems(kept, fragment=True), [])

    def test_text_between_rows_does_not_leak_into_the_previous_row(self) -> None:
        text = GOOD + "\n## Decisions\n- status: not a row field\n"
        (row,) = parse_rows(text, "x")
        self.assertEqual(row["fields"]["status"], "interim")


class JournalHereTests(unittest.TestCase):
    """The rows this checkout actually has: the journal when present, and every unit's fragment."""

    def test_every_row_here_is_well_formed(self) -> None:
        for row, fragment in rows_here():
            with self.subTest(source=row["source"], heading=row["title"]):
                self.assertEqual(problems(row, fragment), [])

    def test_the_row_of_the_unit_that_made_the_suite_is_in_a_fragment_or_folded_into_the_journal(self) -> None:
        # An integrator folds the fragments into the journal and removes them, so U5b's row is in one place or the other.
        self.assertTrue(FRAGMENTS.is_dir(), "the journal rows are written under docs/experiments/shiploop-eff-journal-rows/")
        units = {str(row["fields"].get("unit")) for row, _ in rows_here()}
        self.assertIn("U5b", units)
        self.assertTrue(all(parse_rows(p.read_text(), p.name) for p in FRAGMENTS.glob("*.md")), "a fragment file holds a row")

    def test_the_journal_when_present_has_its_title_and_no_duplicate_rows(self) -> None:
        rows = rows_here()
        keys = [(r["fields"].get("unit"), r["date"], r["fields"].get("snapshot")) for r, _ in rows]
        self.assertEqual(len(keys), len(set(keys)), "two rows share a unit, a date and a snapshot")
        if JOURNAL.is_file():
            self.assertTrue(JOURNAL.read_text().startswith("# ShipLoop efficiency work"))

    def test_the_two_sources_are_both_read(self) -> None:
        sources = {row["source"] for row, _ in rows_here()}
        self.assertTrue(any(s.startswith("docs/experiments/shiploop-eff-journal-rows/") for s in sources))
        if JOURNAL.is_file() and parse_rows(JOURNAL.read_text(), "journal"):
            self.assertIn("journal", sources)


if __name__ == "__main__":
    unittest.main()
