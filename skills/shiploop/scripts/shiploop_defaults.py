"""The answers a specification chose for the requester, and where the requester is shown them.

A request never says everything, and where it does not say a run chooses.  Eleven archived deliveries of one request
(2026-11-21, docs/experiments/ratchet-pilot-20261120/shiploop-defaults/) each chose how tickets already on file get
their due times; four chose the answer the owner had ruled wrong and failed the held-out check for it.  In all eleven
the choice stands in the living spec as a plain line of a requirement, and no result and no report says it was a
choice or names the other answer.  What the requester never sees, the requester cannot answer.

So the spec stage's done result carries ``defaults``: one entry for each choice the specification made that the
request does not settle and that changes what a person who uses or runs the product sees or must do (``FIELDS``).
The model decides what belongs in the list: a script cannot tell a choice from a requirement that was asked for.
ShipLoop refuses only mechanical faults when the result is submitted (a missing list, an entry without its five
texts, one of the template's texts left in, a requirement with no current entry in the living spec) and records and
prints the rest.  An empty list says no choice of the specification qualifies; a result without the key says nothing
(unmeasured is not zero).

Shown three times, each to the requester: by the packet of the stage after the spec (``SHOWN_AT``), which tells the
host to name them in its progress line; by the done packet; and by the report, directly after the request.  Nothing
here asks a question, waits for an answer, adds a limit or blocks a stage for what an entry says.

What it does not do (the design's review, 2026-11-21): it gives the requester no way to change a default inside the
run.  An owner note reaches the next packet, but no script route replaces an accepted specification and what was
planned from it, so the surfaces promise only what holds: a new run on the delivered project.  The rows are what the
spec stage recorded; a later stage that changes a requirement does not change them, and the report says so.

Like ``primary`` and ``follow_on``, the stored shape is loose (a list of text mappings, so every saved run loads
whatever a later edit does to the field set) and the exact shape is held at the CLI gate only.
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import shiploop_knowledge_home as knowledge
import shiploop_planning_revision as planning_revision

STAGES = frozenset(("spec",))
FIELD = "defaults"
# The stage whose packet shows the list to the requester: the one after the spec, the first packet printed once the
# list is accepted.  test/shiploop-defaults.test.py holds it to the stage table's order.
SHOWN_AT = "test-strategy"
FIELDS = ("requirement", "question", "default", "alternative", "why")
# The one row the result template prints, to replace or delete.  A text equal to any of its texts is a placeholder, so
# a row edited in one field only is refused as the whole row copied is, and a text that merely starts and ends with
# angle brackets ("<details> opens on a click on its <summary>") is not.
TEMPLATE_ROW = {
    "requirement": "<R-<n> whose clause states this choice>",
    "question": "<what the request leaves open, as the requester would ask it>",
    "default": "<what happens, for the person who uses or runs the product>",
    "alternative": "<one workable other answer, and what it would change for that person>",
    "why": "<what in the request or the product points to this one, or that nothing does>",
}
WHAT = ("each choice this specification made that the request does not settle and that changes what a person who "
        "uses or runs the product sees or must do")
SHAPE = ("each entry is {requirement, question, default, alternative, why}: the R-<n> whose clause states the choice; "
         "what the request leaves open; the answer chosen; one workable other answer, with what it would change for "
         "that person; and why this one")
EMPTY = "[] when it chose none"
HEADING = "Decided for you"
# Display: the characters of rows the packet of ``SHOWN_AT`` prints by value (five or six rows of the size the template
# asks for).  A longer list prints the rows that fit and names the run file that holds every row whole
# (``shiploop_fields``); nothing is refused for its length.
ROWS_PRINT = 2_400
_REQUIREMENT = re.compile(r"^R-\d+$")
_PLACEHOLDERS = frozenset(" ".join(text.split()) for text in TEMPLATE_ROW.values())


class DefaultsError(ValueError):
    """Raised when a defaults list is missing, malformed, still the template, or names a requirement the spec lacks."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise DefaultsError(message)


def _is_placeholder(text: str) -> bool:
    """A template placeholder left in: the text is one of the template row's own texts, whichever field it sits in."""
    return " ".join(text.split()) in _PLACEHOLDERS


def canonical(value: Any) -> list[dict[str, str]]:
    """The canonical list for a done result's ``defaults`` field: shape only, so a saved result always loads."""
    _need(isinstance(value, list), f"defaults must be a list ({EMPTY}); " + SHAPE)
    rows = []
    for index, entry in enumerate(value):
        _need(isinstance(entry, Mapping) and all(isinstance(key, str) and isinstance(text, str)
                                                 for key, text in entry.items()),
              f"defaults[{index}] must be an object of text values; " + SHAPE)
        rows.append({key: text.strip() for key, text in entry.items()})
    return rows


def recorded(state: Mapping[str, Any]) -> list[Mapping[str, str]] | None:
    """The list of the current accepted done spec result; None when that result has none (unmeasured, not zero)."""
    action = planning_revision.current_actions(state).get((None, "spec"))
    result = (state.get("accepted") or {}).get(action) if action else None
    entries = result.get(FIELD) if isinstance(result, Mapping) else None
    return list(entries) if isinstance(entries, list) else None


def check_submitted(repo: Path, stage: str, result: Any) -> None:
    """Refuse a submitted done spec result without a usable list; runs at the CLI gates only.

    Every message says what the list is, because a refusal is the one text every host is sure to read whole.
    """
    if stage not in STAGES or not isinstance(result, Mapping) or result.get("outcome") != "done":
        return
    _need(FIELD in result, f"a done {stage} result lists defaults: " + WHAT + f"; {EMPTY}. " + SHAPE[0].upper()
          + SHAPE[1:] + ". Add no behaviour to fill it. ShipLoop shows the list to the requester")
    entries = result[FIELD]
    _need(isinstance(entries, list), f"defaults must be a list ({EMPTY}); " + SHAPE)
    held = None
    for index, entry in enumerate(entries):
        label = f"defaults[{index}]"
        _need(isinstance(entry, Mapping), f"{label} must be an object; " + SHAPE)
        extra = sorted(str(key) for key in entry if key not in FIELDS)
        missing = [name for name in FIELDS if name not in entry]
        _need(not extra and not missing, f"{label} "
              + " and ".join(part for part in ("lacks " + ", ".join(missing) if missing else "",
                                               "has the unknown " + ", ".join(extra) if extra else "") if part)
              + "; " + SHAPE)
        for name in FIELDS:
            text = entry[name]
            _need(isinstance(text, str), f"{label}.{name} must be text; " + SHAPE)
            _need(bool(text.strip()), f"{label}.{name} is empty; " + SHAPE)
            _need(not _is_placeholder(text), f"{label}.{name} still holds the template placeholder: write it, or "
                  f"delete the row when this specification did not choose it ({EMPTY})")
        requirement = entry["requirement"].strip()
        _need(_REQUIREMENT.fullmatch(requirement) is not None, f"{label}.requirement {requirement!r} is not one "
              "requirement ID: name the R-<n> whose clause states the choice; a choice two requirements touch is "
              "listed under the one that states it")
        if held is None:
            held = knowledge.entries(Path(repo), "spec.md")
        _need(requirement in held and not held[requirement].retired,
              f"{label}.requirement {requirement} has no current entry in "
              + str(Path(repo) / knowledge.HOME / "spec.md") + ": state the choice in a clause of an R-<n> under "
              "## Requirements and name that ID (current: "
              + (", ".join(sorted((key for key, found in held.items() if not found.retired),
                                  key=lambda key: int(key.split("-")[1]))) or "none") + ")")


def _text(value: Any) -> str:
    """One line of plain text: a model-written text with its line breaks and runs of spaces folded."""
    return " ".join(str(value).split())


def _end(value: Any) -> str:
    """The text as one sentence: a closing mark the model wrote is kept, a text without one gets a period."""
    text = _text(value)
    return text if not text or text[-1] in ".!?" else text + "."


def row_lines(entries: Sequence[Mapping[str, str]]) -> list[str]:
    """The rows as numbered lines, each whole: the requirement, what the request leaves open, the answer chosen and the
    other answer.  The reason stays in the report and the spec result."""
    return [f"{number}. {_text(row.get('requirement', ''))} {_end(row.get('question', ''))} "
            f"Decided: {_end(row.get('default', ''))} Otherwise: {_end(row.get('alternative', ''))}"
            for number, row in enumerate(entries, 1)]


def _count(entries: Sequence[Any]) -> str:
    return f"{len(entries)} answer" + ("" if len(entries) == 1 else "s")


def shows(state: Mapping[str, Any], stage: str) -> bool:
    """Whether ``stage``'s packet shows the list: the stage after the spec, in an active run, outside a stage review."""
    return stage == SHOWN_AT and state.get("status") == "active" and not state.get("active_improve")


def packet_lines(state: Mapping[str, Any], root: Path, stage: str, rows: Sequence[str]) -> list[str]:
    """What the packet of the stage after the spec says: where the list is, the rows as the navigator prints them
    (``rows``: every row, or those that fit ``ROWS_PRINT`` and the line naming the file that holds them all), and that
    the host names them to the user and waits for nothing.  Nothing for an empty or absent list or where ``shows`` says
    no."""
    entries = recorded(state)
    action = planning_revision.current_actions(state).get((None, "spec"))
    if not shows(state, stage) or not entries or action is None:
        return []
    head = (f"Defaults the spec recorded: {_count(entries)} it chose where the request does not say ("
            + str(Path(root) / "results" / (str(action) + ".md")) + ", `defaults`). In this stage's progress line tell "
            "the user there " + ("is" if len(entries) == 1 else "are") + f" {len(entries)} and name each in a few "
            "words; ask nothing and wait for no answer:")
    return [head, *rows]


def done_lines(state: Mapping[str, Any]) -> list[str]:
    """What the done packet says about the list: nothing for an empty or absent list."""
    entries = recorded(state)
    if not entries:
        return []
    head = (f"{HEADING}: {_count(entries)} the spec chose where the request does not say; the report lists them "
            "first, each with its reason.")
    return [head, *row_lines(entries),
            "To change one, start a new run on this project with a sentence that says what you want instead."]


def html_section(state: Mapping[str, Any]) -> list[str]:
    """The report's section on the list; nothing before a spec is accepted.  Every value is escaped."""
    if planning_revision.current_actions(state).get((None, "spec")) is None:
        return []
    entries = recorded(state)
    if entries is None:
        note = "<p>not recorded: this run's spec result has no defaults list, which is not the same as none.</p>"
    elif not entries:
        note = "<p>none: the specification recorded no answer of its own where the request does not say.</p>"
    else:
        heads = ("", "Requirement", "The request does not say", "Decided", "Otherwise", "Why this one")
        rows = ["<tr><td>" + str(number) + "</td>"
                + "".join("<td>" + html.escape(str(row.get(name, ""))) + "</td>" for name in FIELDS) + "</tr>"
                for number, row in enumerate(entries, 1)]
        action = planning_revision.current_actions(state).get((None, "spec"))
        note = ("<p>The request did not say, so the specification chose: " + html.escape(_count(entries)) + ", each "
                "stated in the requirement named. Nobody was asked. The rows are as the spec stage recorded them ("
                + html.escape(str(action)) + "); a later stage's change to a requirement is not shown here. To change "
                "one, start a new run on this project with a sentence that says what you want instead.</p>\n"
                "<table><thead><tr>" + "".join("<th>" + head + "</th>" for head in heads) + "</tr></thead><tbody>\n"
                + "\n".join(rows) + "\n</tbody></table>")
    return [f"<h2>{HEADING}</h2>", note]


__all__ = (
    "EMPTY",
    "FIELD",
    "FIELDS",
    "HEADING",
    "ROWS_PRINT",
    "SHAPE",
    "SHOWN_AT",
    "STAGES",
    "TEMPLATE_ROW",
    "WHAT",
    "DefaultsError",
    "canonical",
    "check_submitted",
    "done_lines",
    "html_section",
    "packet_lines",
    "recorded",
    "row_lines",
    "shows",
)
