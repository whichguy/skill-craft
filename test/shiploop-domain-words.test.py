#!/usr/bin/env python3
"""ShipLoop's generic text names no platform or example app (owner rule 8; efficiency plan U29, rev 4 Step 10.1).

Platform detail lives in ``skills/shiploop/references/platforms/``; the scripts, the packets they print, the skill card and the
other references stay generic, so a model working on any program reads no other program's specifics. ``test/domain-words.json``
lists the denied words (chess terms, the example apps, Salesforce terms, host automation) and the few places allowed to name a
platform (the platform cards, the guidance selector's index row and the README's platform link). Adding a word is one line there.

The suite also holds the generic runner list to the code: the reference that tells a model which runner summaries ShipLoop reads
names every runner of ``shiploop_test_counts.READERS`` (the packets print ``RUNNERS``, generated from that table).
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "test" / "domain-words.json").read_text(encoding="utf-8"))
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
PROMPTS = "skills/shiploop/scripts/shiploop_prompts.py"


def words() -> list[str]:
    return [word for group in CONFIG["words"].values() for word in group]


def pattern(word: str) -> re.Pattern:
    """The word as a whole word, case-insensitively: `sf` does not match `sf_guard`, `Lightning` does not match `lightning__Tab`."""
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(word) + r"(?![A-Za-z0-9_])", re.IGNORECASE)


PATTERNS = [(word, pattern(word)) for word in words()]


def allowed(relative: str, line: str) -> bool:
    if any(relative.startswith(folder) for folder in CONFIG["allow_dirs"]):
        return True
    return any(relative == row["path"] and row["line_contains"] in line for row in CONFIG["allow"])


def findings(root: Path) -> list[str]:
    """``<path>:<line>: <word>`` for each denied word on a line that is not allowed, in every text file under the scan root."""
    found = []
    base = root / CONFIG["scan"]
    for path in sorted(base.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # a binary file holds no prose
        relative = path.relative_to(root).as_posix()
        for number, line in enumerate(text.splitlines(), 1):
            for word, compiled in PATTERNS:
                if compiled.search(line) and not allowed(relative, line):
                    found.append(f"{relative}:{number}: {word}")
    return found


class DomainWordTests(unittest.TestCase):
    def test_generic_text_names_no_domain_word(self) -> None:
        self.assertEqual(findings(ROOT), [], "move platform detail to skills/shiploop/references/platforms/ "
                                             "(or, for a new generic sense of a word, narrow test/domain-words.json)")

    def test_every_listed_word_is_caught_when_planted_in_the_prompt_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / PROMPTS
            target.parent.mkdir(parents=True)
            original = (ROOT / PROMPTS).read_text(encoding="utf-8")
            for word in words():
                with self.subTest(word=word):
                    target.write_text(original + f'\nEXAMPLE = "for example {word} here"\n', encoding="utf-8")
                    self.assertEqual(findings(Path(temp)), [f"{PROMPTS}:{len(original.splitlines()) + 2}: {word}"])

    def test_a_word_inside_a_longer_identifier_is_not_a_finding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / PROMPTS
            target.parent.mkdir(parents=True)
            target.write_text("guard = sf_guard_name\nnote = 'apexes and chessboards'\n", encoding="utf-8")
            self.assertEqual(findings(Path(temp)), [])

    def test_only_the_platform_cards_and_the_named_lines_may_name_a_platform(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            scan = Path(temp) / CONFIG["scan"]
            card = scan / "references" / "platforms" / "example.md"
            card.parent.mkdir(parents=True)
            card.write_text("Run `sf project deploy validate`; Apex and Lightning live here.\n", encoding="utf-8")
            index = Path(temp) / "skills/shiploop/references/coding-guidance.md"
            row = next(r for r in CONFIG["allow"] if r["path"].endswith("coding-guidance.md"))
            index.write_text(row["line_contains"] + " Apex, LWC |\nA Salesforce tab elsewhere.\n", encoding="utf-8")
            self.assertEqual(findings(Path(temp)), ["skills/shiploop/references/coding-guidance.md:2: Salesforce"])

    def test_the_reference_runner_list_names_every_runner_shiploop_reads(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        try:
            import shiploop_test_counts as counts
        finally:
            sys.path.remove(str(SCRIPTS))
        names = [name for name, _reader in counts.READERS] + ["pytest"]
        self.assertEqual(counts.RUNNERS, ", ".join(names))
        guide = (ROOT / "skills/shiploop/references/testing-and-documentation.md").read_text(encoding="utf-8")
        reading = guide.split("### Reading a run", 1)[1].split("\n\n", 2)[1]
        missing = [name for name in names if not pattern(name).search(reading)]
        self.assertEqual(missing, [], "the 'Reading a run' runner list must name every runner of shiploop_test_counts.READERS")


if __name__ == "__main__":
    unittest.main()
