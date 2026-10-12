"""The commit-message grammar ShipLoop reads: lessons, a remote change and cited commits (SPEC S-12).

One pure module, standard library only, importing nothing from ShipLoop, so the navigator and the E2E harness
read a message the same way and can never disagree about what counts.  A section is a label plus a body, found
in one of three forms, each anchored at the start of a line (an optional ``- ``, ``* `` or ``> `` before it and
a ``**`` or ``__`` wrapper around the label are tolerated):

    ## Key learnings           heading, one to three #: the body runs to the next heading
    Key learnings: the text    label and colon: the rest of the line, then the lines after it
    Key learnings              the label alone on its line: the lines after it

There is no form for a label inside a sentence, so a one-paragraph message ("... Validation: x. Key learnings: y.")
has no section; a refusal names the forms that are read.  Labels match without regard to case.

A colon or bare body ends at a blank line, a heading or a known label with its colon: the Improve card's six, the
lesson labels, ``Learned-from``, ``Remote change`` and the four trailers ShipLoop's commits end with
(``Co-Authored-By``, ``Signed-off-by``, ``No-Change-Note``, ``Skill-Craft-Release``).  A heading body runs across
blank lines and ends at the same things, so a section that holds only the ``Co-Authored-By:`` trailer is empty.  A
trailer is known by its name, not its shape: ``Root-cause: x`` and ``Follow-up: y`` are lesson text wherever they
stand.  A label word without a colon (``Review the logs``) or a lone label line (``Plan``) does not end a body, since
either can be a lesson's own words.  When the label has no text of its own, blank lines are skipped and the first
line after them is the body, whatever it looks like, unless it is a known label or a heading: ``Key learnings:``
then ``Pitfall: x`` is a lesson, ``Key learnings:`` then ``Remaining work: x`` is an empty section.

A section counts as a lesson when its body holds a letter or a digit; ``Key learnings: none`` counts, because the
script cannot judge a lesson's truth and measures instead of refusing on content.  ``Learned-from`` is the key of
a citation, never a lesson label.
"""

from __future__ import annotations

import re
from typing import Callable, List, NamedTuple, Optional, Sequence

# "Key learnings" is the Improve card's label and the E2E data's most common one; "Lessons learned" is the owner's
# phrase; "Learned" is release-verify's bare section.  "Key considerations" and "Open for the next run" are decisions
# and follow-ups, not lessons, and "Learned-from" cites a commit.
LESSON_LABELS = ("Key learnings", "Key learning", "Lessons learned", "Lessons", "Learnings", "Learning", "Lesson",
                 "Learned")
_REMOTE_LABEL = "Remote change"
_CITATION_LABEL = "Learned-from"
_IMPROVE_LABELS = ("Review", "Plan", "Changes", "Validation", "Key learnings", "Remaining work")
# The trailers ShipLoop's own commits end with (this repository's history on 2026-10-10: Co-Authored-By 787, No-Change-Note
# 162, Skill-Craft-Release 57; Signed-off-by is Git's own).  Known by name: a lesson line such as ``Root-cause: x`` has
# the same shape and must stay lesson text.
_TRAILERS = ("Co-Authored-By", "Signed-off-by", "No-Change-Note", "Skill-Craft-Release")
# What ends a body: the labels ShipLoop's own messages use and those trailers.  re.ASCII keeps "case-insensitive" to
# ASCII, so a dotless i or a long s is no label (it used to match and then miss the lookup in ``sections``).
_KNOWN_LABELS = _IMPROVE_LABELS + LESSON_LABELS + (_CITATION_LABEL, _REMOTE_LABEL) + _TRAILERS

_BULLET = r"(?:[-*>][ \t]+)?"
_WRAP = r"(?:\*\*|__)?"
_HEADING = re.compile(r"^#{1,3}[ \t]+\S")
_CITATION = re.compile(rf"^{_BULLET}{_WRAP}{re.escape(_CITATION_LABEL)}{_WRAP}[ \t]*:{_WRAP}[ \t]*(?P<rest>.*)$",
                       re.IGNORECASE | re.ASCII)
# Around a commit ID a model writes backticks, quotes, brackets and a trailing colon, comma or period.
_TOKEN_EDGE = "`'\"[](){}<>:,.;"


def _names(labels: Sequence[str]) -> str:
    return "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True))


def _line_pattern(labels: Sequence[str]) -> "re.Pattern[str]":
    return re.compile(rf"^{_BULLET}{_WRAP}(?P<label>{_names(labels)}){_WRAP}(?P<colon>[ \t]*:)?{_WRAP}[ \t]*(?P<rest>.*)$",
                      re.IGNORECASE | re.ASCII)


def _heading_pattern(labels: Sequence[str]) -> "re.Pattern[str]":
    return re.compile(rf"^#{{1,3}}[ \t]+{_WRAP}(?P<label>{_names(labels)}){_WRAP}[ \t]*:?[ \t]*$",
                      re.IGNORECASE | re.ASCII)


_KNOWN = _line_pattern(_KNOWN_LABELS)


class Section(NamedTuple):
    """One labelled section of a commit message: the label as asked for and its stripped text (empty when absent).
    """
    label: str   # the label as spelled in the ``labels`` argument
    body: str    # the section text, stripped; empty when the label has none


class Citation(NamedTuple):
    """One ``Learned-from:`` line of a commit message: its line number, the commit ID cited and the contribution
    described.
    """
    line: int          # 1-based line of the ``Learned-from:`` line
    token: str         # the commit ID as written, without quotes, brackets or trailing punctuation ('' when absent)
    contribution: str  # the rest of the line, stripped


def _lines(text: str) -> List[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _has_content(body: str) -> bool:
    return re.search(r"[^\W_]", body) is not None


def _ends_body(row: str) -> bool:
    if _HEADING.match(row):
        return True
    known = _KNOWN.match(row)
    return known is not None and known.group("colon") is not None


def sections(text: str, labels: Sequence[str]) -> List[Section]:
    """Every section of ``text`` whose label is one of ``labels``, in message order."""
    lines = _lines(text)
    wanted = {label.lower(): label for label in labels}
    heading, plain = _heading_pattern(labels), _line_pattern(labels)
    found: List[Section] = []
    index = 0
    while index < len(lines):
        row = lines[index]
        match = heading.match(row)
        if match:
            end = index + 1
            while end < len(lines) and not _ends_body(lines[end]):
                end += 1
            found.append(Section(wanted[match.group("label").lower()], "\n".join(lines[index + 1:end]).strip()))
            index = end
            continue
        match = plain.match(row)
        first = match.group("rest").strip() if match else ""
        if match and (match.group("colon") or not first):
            body = [first] if first else []
            end = index + 1
            while not first and end < len(lines) and not lines[end].strip():
                end += 1
            while end < len(lines) and lines[end].strip() and not _ends_body(lines[end]):
                body.append(lines[end])
                end += 1
            found.append(Section(wanted[match.group("label").lower()], "\n".join(body).strip()))
            index = end
            continue
        index += 1
    return found


def lessons(text: str) -> str:
    """The text of every lessons section that holds a letter or a digit, joined by newlines; '' when there is none."""
    return "\n".join(section.body for section in sections(text, LESSON_LABELS) if _has_content(section.body))


def remote_change(text: str) -> str:
    """The text of the first non-empty ``Remote change`` section; '' when there is none."""
    for section in sections(text, (_REMOTE_LABEL,)):
        if _has_content(section.body):
            return section.body
    return ""


def citations(text: str) -> List[Citation]:
    """Every ``Learned-from: <commit id> <what it contributed>`` line, with its 1-based line number."""
    found: List[Citation] = []
    for number, row in enumerate(_lines(text), 1):
        match = _CITATION.match(row)
        if not match:
            continue
        words = match.group("rest").split(None, 1)
        if len(words) == 2 and words[0].lower() == "commit":
            words = words[1].split(None, 1)
        token = words[0].strip(_TOKEN_EDGE) if words else ""
        found.append(Citation(number, token, words[1].strip() if len(words) > 1 else ""))
    return found


def with_full_ids(text: str, resolver: Callable[[str], Optional[str]]) -> str:
    """``text`` with each citation line rewritten as ``Learned-from: <full id> <contribution>``.

    ``resolver`` maps the token as written to the full commit ID; a falsy answer leaves that line as written.
    Every other line is kept, and the line endings become ``\\n``.
    """
    lines = _lines(text)
    for citation in citations(text):
        full = resolver(citation.token) if citation.token else None
        if full:
            lines[citation.line - 1] = (_CITATION_LABEL + ": " + full
                                        + (" " + citation.contribution if citation.contribution else ""))
    return "\n".join(lines)


__all__ = ("LESSON_LABELS", "Citation", "Section", "citations", "lessons", "remote_change", "sections", "with_full_ids")
