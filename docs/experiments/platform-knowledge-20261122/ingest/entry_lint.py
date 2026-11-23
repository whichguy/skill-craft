"""Check the form of the entries in a platform card's ``## Planning`` section.

Usage: python3 entry_lint.py CARD [--sourced] [--repo ROOT]

An entry is one bullet of the section: a bold id, the plan concerns it bears on in
square brackets, the fact, then the labelled parts ``Decision:`` and ``Proof:``.
The lint checks, for every entry:

- a bold id, used by no other entry of the file;
- at least one concern, each one of the fifteen names of ``CONCERNS`` in
  ``skills/shiploop/scripts/shiploop_concerns.py`` (copied below);
- some fact text before the first label;
- ``Decision:`` and ``Proof:`` present and not empty.

With ``--sourced`` it also asks for ``Applies when:``, ``Source:`` and ``Kind:``;
the Kind must be one of ``KINDS``, and the Source must name a file that exists
under ``--repo`` (default: the current directory). A Source names its file as
the first backticked path outside its quotation. When it quotes a phrase in
double quotes, the phrase must occur in that file (whitespace runs compared as
one space, since journals wrap their lines).

It prints one line for each finding, ``CARD: ID: message``, and exits 1 when
there are findings, 0 when there are none. A card with no ``## Planning``
section has nothing to check: the lint says so and exits 0. Bad arguments or an
unreadable card exit 2. Standard library only; Python 3.9 or later.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

# The fifteen names of CONCERNS in skills/shiploop/scripts/shiploop_concerns.py,
# copied here so the lint runs without ShipLoop (test_entry_lint.py compares them).
CONCERN_IDS = (
    "ui",
    "api",
    "messaging",
    "state",
    "migrate-before",
    "migrate-after",
    "switchover",
    "concurrency",
    "platform-services",
    "scale",
    "security",
    "observability",
    "config",
    "performance",
    "accessibility",
)
KINDS = (
    "hard constraint",
    "evidenced default",
    "question that needs an observation of the target",
)
REQUIRED = ("Decision", "Proof")
SOURCED = ("Applies when", "Source", "Kind")
LABELS = REQUIRED + SOURCED

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_BULLET = re.compile(r"^[-*]\s+(.*)$")
_HEAD = re.compile(r"^\*\*([^*]+)\*\*\s*(.*)$")
_CONCERNS = re.compile(r"^\[([^\]]*)\]\s*(.*)$")
_LABEL = re.compile(r"(?:^|(?<=\s))(" + "|".join(re.escape(x) for x in LABELS) + r"):")
_QUOTE = re.compile(r"[\"“]([^\"”]+)[\"”]")
_PATH = re.compile(r"`([^`\s]+)`")


class Entry:
    """One bullet of the Planning section: where it starts and its joined text."""

    def __init__(self, line: int, text: str) -> None:
        self.line = line
        self.text = text
        self.id = ""
        self.concerns: list[str] = []
        self.fact = ""
        self.parts: dict[str, str] = {}


def planning_lines(text: str) -> list[tuple[int, str]] | None:
    """The lines of the ``## Planning`` section with their 1-based numbers, or None
    when the card has no such section. The section ends at the next heading of
    level one or two."""
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        match = _HEADING.match(line)
        if match and len(match.group(1)) == 2 and match.group(2) == "Planning":
            start = index + 1
            break
    if start is None:
        return None
    section = []
    for index in range(start, len(lines)):
        match = _HEADING.match(lines[index])
        if match and len(match.group(1)) <= 2:
            break
        section.append((index + 1, lines[index]))
    return section


def split_entries(section: Sequence[tuple[int, str]]) -> list[Entry]:
    """Bullets at the left margin start an entry; indented lines continue it;
    anything else (a blank line, prose, a sub-heading) ends it."""
    entries: list[Entry] = []
    current: Entry | None = None
    for number, line in section:
        bullet = _BULLET.match(line)
        if bullet:
            current = Entry(number, bullet.group(1).strip())
            entries.append(current)
        elif current is not None and line[:1].isspace() and line.strip():
            current.text += " " + line.strip()
        else:
            current = None
    for entry in entries:
        entry.text = " ".join(entry.text.split())
        parse(entry)
    return entries


def parse(entry: Entry) -> None:
    """Fill the entry's id, concerns, fact and labelled parts from its text."""
    rest = entry.text
    head = _HEAD.match(rest)
    if head:
        entry.id = head.group(1).strip()
        rest = head.group(2)
    concerns = _CONCERNS.match(rest)
    if concerns:
        entry.concerns = [c for c in re.split(r"[,\s]+", concerns.group(1)) if c]
        rest = concerns.group(2)
    marks = list(_LABEL.finditer(rest))
    entry.fact = (rest[: marks[0].start()] if marks else rest).strip()
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(rest)
        label = mark.group(1)
        if label not in entry.parts:
            entry.parts[label] = rest[mark.end() : end].strip()


def _squash(text: str) -> str:
    return " ".join(text.split())


def check_source(source: str, repo: Path) -> list[str]:
    """Findings for one Source part: its file under ``repo`` and its quotation."""
    quote = _QUOTE.search(source)
    outside = source[: quote.start()] + source[quote.end() :] if quote else source
    path = _PATH.search(outside)
    if path is None:
        return ["Source names no file (give its path in backticks)"]
    root = repo.resolve()
    target = (root / path.group(1)).resolve()
    if target != root and root not in target.parents:
        return [
            "Source file " + path.group(1) + " is outside the repo root " + str(root)
        ]
    if not target.is_file():
        return ["Source file " + path.group(1) + " does not exist under " + str(root)]
    if quote is None:
        return []
    try:
        body = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return ["Source file " + path.group(1) + " cannot be read: " + str(exc)]
    if _squash(quote.group(1)) not in _squash(body):
        return [
            'Source quotes "' + quote.group(1) + '", which is not in ' + path.group(1)
        ]
    return []


def check_entry(entry: Entry, sourced: bool, repo: Path) -> list[str]:
    """The findings for one entry, in a fixed order."""
    found = []
    if not entry.id:
        found.append("no bold id at the start of the entry")
    if not entry.concerns:
        found.append("no concerns in square brackets after the id")
    for concern in entry.concerns:
        if concern not in CONCERN_IDS:
            found.append("unknown concern '" + concern + "'")
    if not entry.fact:
        found.append("no fact before the first label")
    for label in REQUIRED + (SOURCED if sourced else ()):
        if label not in entry.parts:
            found.append("no '" + label + ":' part")
        elif not entry.parts[label]:
            found.append("empty '" + label + ":' part")
    if sourced:
        kind = entry.parts.get("Kind", "").rstrip(".").strip().lower()
        if kind and kind not in KINDS:
            found.append(
                "Kind '" + entry.parts["Kind"] + "' is not one of: " + "; ".join(KINDS)
            )
        if entry.parts.get("Source"):
            found.extend(check_source(entry.parts["Source"], repo))
    return found


def lint(
    text: str, sourced: bool = False, repo: Path = Path(".")
) -> tuple[int | None, list[tuple[str, str]]]:
    """(the number of entries, or None without a Planning section; [(id, finding)])."""
    section = planning_lines(text)
    if section is None:
        return None, []
    entries = split_entries(section)
    findings: list[tuple[str, str]] = []
    seen: dict[str, int] = {}
    for entry in entries:
        name = entry.id or "line " + str(entry.line)
        if entry.id and entry.id in seen:
            findings.append(
                (name, "id used again (first at line " + str(seen[entry.id]) + ")")
            )
        elif entry.id:
            seen[entry.id] = entry.line
        findings.extend(
            (name, finding) for finding in check_entry(entry, sourced, repo)
        )
    return len(entries), findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the form of a platform card's ## Planning entries."
    )
    parser.add_argument("card", help="the card file to read")
    parser.add_argument(
        "--sourced",
        action="store_true",
        help="also require Applies when, Source and Kind",
    )
    parser.add_argument(
        "--repo", default=".", help="the root a Source path is read under (default: .)"
    )
    args = parser.parse_args(argv)
    try:
        text = Path(args.card).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(args.card + ": cannot be read: " + str(exc), file=sys.stderr)
        return 2
    count, findings = lint(text, args.sourced, Path(args.repo))
    if count is None:
        print(args.card + ": no ## Planning section, so there are no entries to check")
        return 0
    for name, finding in findings:
        print(args.card + ": " + name + ": " + finding)
    if not findings:
        print(args.card + ": " + str(count) + " entries, no findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
