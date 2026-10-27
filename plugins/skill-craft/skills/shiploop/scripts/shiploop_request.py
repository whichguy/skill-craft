"""The run's request as a file: verbatim, then split into sentences S1..Sn (efficiency plan U17, rev 4 Step 4.2a).

``RUN/request.md`` is derived from ``state["prompt"]`` at every save.  The split is a display index a stage cites
(``S<n>``); the verbatim text governs.  The intake, spec and plan packets quote the request whole; every other packet
names this file (owner decision D2, 2026-10-17; ``shiploop_navigator.REQUEST_WHOLE_STAGES``).  Intake's summary
is measured against the index: a done intake whose summary leaves a sentence uncited (no S<n> covers it) is refused
(IN1, 2026-10-26; until then it was a counted notice that never refused).
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import List, Set

REQUEST_FILE = "request.md"
INTAKE = "intake"
# The pointer a packet prints beside the verbatim request (intake: the stage whose summary IN1 measures).
POINTER = ("Sentence index of this request (S1..Sn, the same text split at sentence ends; cite S<n>, the verbatim text "
           "governs): RUN/" + REQUEST_FILE)

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
# A piece that only numbers or letters a list entry ("1.", "b)") or ends in a common abbreviation joins the next piece.
_JOINS_NEXT = re.compile(r"(?:^(?:\d{1,3}|[A-Za-z])[.)]|\b(?:e\.g|i\.e|vs|cf|approx)\.)$", re.IGNORECASE)
# "S3", and a range "S2-S4", "S2 to S4" or "S2..S4" (each sentence in it counts as cited).
_CITED = re.compile(r"\bS(\d{1,4})(?:\s*(?:-|–|to|\.\.)\s*S?(\d{1,4}))?\b")


def sentences(prompt: str) -> List[str]:
    """The request's sentences in order: each non-blank line, split after ``.``, ``!`` or ``?`` before whitespace.

    Lossless up to whitespace: the sentences joined equal the request with its whitespace removed.
    """
    found: List[str] = []
    for line in str(prompt).splitlines():
        pending = ""
        for piece in _SENTENCE_END.split(line.strip()):
            if not piece:
                continue
            pending = pending + " " + piece if pending else piece
            if not _JOINS_NEXT.search(pending):
                found.append(pending)
                pending = ""
        if pending:
            found.append(pending)
    return found


def _fence(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"~+", text)), default=0)
    return "~" * max(3, longest + 1)


def render(prompt: str) -> str:
    """The text of ``RUN/request.md``: the request verbatim, then one ``- S<n>: <sentence>`` line per sentence."""
    text = str(prompt).rstrip("\n")
    fence = _fence(text)
    rows = ["- S" + str(number) + ": " + sentence for number, sentence in enumerate(sentences(prompt), 1)]
    return "\n".join([
        "# Request",
        "",
        "ShipLoop writes this file from the run's request: the request verbatim, then the same text split into "
        "sentences S1..Sn. The split is a display index for citing a sentence (S<n>); the verbatim text governs. The "
        "intake, spec and plan packets quote it too; every other packet names this file.",
        "",
        "## Verbatim",
        "",
        fence + "text",
        text,
        fence,
        "",
        "## Sentences",
        "",
        *(rows or ["- none (the request is empty)"]),
    ]) + "\n"


def index(text: str) -> List[str]:
    """The sentences listed under ``## Sentences`` of a rendered file, in S-order (the inverse of ``render``)."""
    body = text.split("\n## Sentences\n", 1)[1] if "\n## Sentences\n" in text else ""
    return [match.group(2) for match in re.finditer(r"(?m)^- S(\d+): (.*)$", body)]


def cited(summary: str) -> Set[int]:
    """The sentence numbers ``summary`` cites, ranges included."""
    found: Set[int] = set()
    for match in _CITED.finditer(str(summary or "")):
        first, last = int(match.group(1)), int(match.group(2) or match.group(1))
        found.update(range(first, last + 1) if first <= last else (first,))
    return found


class RequestError(ValueError):
    """A done intake whose summary leaves a request sentence uncited; the message names each and the fix."""


def check(prompt: str, stage: str, result: object) -> None:
    """IN1: a done intake result's ``summary`` cites every request sentence S1..Sn, ranges included."""
    if stage != INTAKE or not isinstance(result, Mapping) or result.get("outcome") != "done":
        return
    summary = result.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return   # a missing or blank summary is the result shape's refusal, which names the field
    count = len(sentences(prompt))
    missing = [number for number in range(1, count + 1) if number not in cited(summary)]
    if missing:
        raise RequestError("intake's summary cites no " + ", ".join("S" + str(number) for number in missing)
                           + " of the request's sentences S1..S" + str(count) + " (RUN/" + REQUEST_FILE + "): give each "
                           "the outcome, boundary, default or open question it maps to, with its S<n>, then run the same "
                           "callback again.")


__all__ = ["INTAKE", "POINTER", "REQUEST_FILE", "RequestError", "check", "cited", "index", "render", "sentences"]
