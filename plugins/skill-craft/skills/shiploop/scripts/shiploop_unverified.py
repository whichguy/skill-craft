#!/usr/bin/env python3
"""Script-owned checks for the request outcomes no executed check observed (SPEC S-14, the case end-state rule).

A done product-acceptance result carries ``unverified``: one entry for each request outcome that no executed
check observed, because the observation is not due yet or cannot be made here ("unachievable" in the case
end-state rule).  The model decides what belongs in the list.  ShipLoop refuses only mechanical faults here when a
result is submitted (a missing list, an entry without its seven texts, a requirement that is not one R-<n>, a template
placeholder left in, a due stage that is not a later stage) and records and prints the rest: it cannot judge whether
the list is complete or an outcome is true.  An empty list says every request outcome was observed by an executed
check; a result without the key says nothing (unmeasured is not zero).  What an entry's requirement and
lower-layer check must hold in the run (an entry in the living spec; for a primary requirement, a test ShipLoop saw
pass) is ``shiploop_primary.check_unverified``'s rule (run-5 batch F6).

Like the plan's assumption list, the stored shape is loose (a list of text mappings, so every saved run loads
whatever a later edit does to the field set) and the exact shape is held at the CLI gate only.

A later stage restates the list (E2E release-gate trio on 2.13.2, 2026-10-26): hello's release-verify settled R-1 in
prose ("Returned main prints the greeting") with no ``unverified`` key, so no reader could tell settled from not
restated.  The handoff, and any stage an entry is due at, carries the current list in its done result: an entry due at
that stage that it observed is dropped (settled), one it could not observe moves its due stage later, and every other
entry is copied unchanged; ``[]`` once none stays open.  ``current_list`` reads the latest restatement.
"""

from __future__ import annotations

import html
import re
from typing import Any, Mapping

import shiploop_planning_revision as planning_revision
import shiploop_stage_spec as stage_spec

STAGES = frozenset(("product-acceptance",))
FIELDS = ("outcome", "requirement", "reason", "lower_layer_check", "settle", "owner", "due_stage")
# The one row the result template prints, to replace or delete.  A text that starts with "<" and ends with ">" is
# a placeholder, so a row edited in one field only is refused as the whole row copied is.  The lower-layer check's
# placeholder states its bar (run-5 batch F6): for a primary requirement only a passed test ID is accepted.
TEMPLATE_ROW = {
    "outcome": "<request outcome no executed check observed>",
    "requirement": "<the R-<n> it maps to>",
    "reason": "<why not observed here, or not due yet>",
    "lower_layer_check": "<ID of a unit or component test of its logic that ShipLoop ran and saw pass; for a "
                         "requirement not in primary, that or why none exists>",
    "settle": "<what the owner does and reports>",
    "owner": "<who>",
    "due_stage": "handoff",
}
SHAPE = ("each entry is {outcome, requirement, reason, lower_layer_check, settle, owner, due_stage}: the request "
         "outcome no executed check observed, the R-<n> it maps to, why, the passed unit or component test of its "
         "logic (for a requirement not in primary, that or why none exists), what the owner does and reports to "
         "settle it, who the owner is, and the later stage that reports it")
_REQUIREMENT = re.compile(r"^R-\d+$")


class UnverifiedError(ValueError):
    """Raised when an unverified list is missing, malformed or still the template."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise UnverifiedError(message)


def _is_placeholder(text: str) -> bool:
    """A template placeholder: the whole text wrapped in angle brackets; markup inside a sentence is not one."""
    text = text.strip()
    return text.startswith("<") and text.endswith(">")


def due_stages(stage: str = "product-acceptance") -> tuple[str, ...]:
    """The stages after ``stage`` in graph order, where an unverified outcome can be reported."""
    outer = stage_spec.OUTER
    return outer[outer.index(stage) + 1:]


def current_list(state: Mapping[str, Any]) -> tuple[str | None, str | None, list[Mapping[str, str]] | None]:
    """(action, stage, entries) of the latest accepted done result that lists unverified: product-acceptance's, or a
    later stage's restatement; all None when no result has listed it (unmeasured, not zero)."""
    listing = ("product-acceptance", *due_stages())
    accepted = state.get("accepted", {})
    for row in reversed(state.get("history") or ()):
        if row.get("outcome") != "done" or row.get("stage") not in listing:
            continue
        result = accepted.get(row.get("action"), {})
        if isinstance(result, Mapping) and isinstance(result.get("unverified"), list):
            return row["action"], row["stage"], list(result["unverified"])
    return None, None, None


def must_restate(state: Mapping[str, Any], stage: str) -> bool:
    """Whether ``stage``'s done result restates the list: the handoff, or a stage an entry is due at."""
    _action, _source, entries = current_list(state)
    if entries is None or stage not in due_stages():
        return False
    return stage == "handoff" or any(str(row.get("due_stage", "")).strip() == stage for row in entries)


def _key(row: Mapping[str, Any]) -> tuple[str, str]:
    return str(row.get("requirement", "")).strip(), " ".join(str(row.get("outcome", "")).split())


def _check_entries(entries: list, allowed: tuple[str, ...],
                   carried: frozenset[tuple[str, str, str]] = frozenset()) -> None:
    """Each entry's shape: exactly the seven texts, none a placeholder, one R-<n>, and a due stage in ``allowed``
    unless the entry is carried from the current list with its due stage unchanged (``carried``)."""
    for index, entry in enumerate(entries):
        label = f"unverified[{index}]"
        _need(isinstance(entry, Mapping) and set(entry) == set(FIELDS),
              f"{label} needs exactly {', '.join(FIELDS)}; {SHAPE}")
        for name in FIELDS:
            text = entry[name]
            _need(isinstance(text, str) and bool(text.strip()), f"{label}.{name} must be nonempty text")
            _need(not _is_placeholder(text), f"{label}.{name} is still a template placeholder: "
                  "replace it, or delete the row when every request outcome was observed by an executed check")
        _need(_REQUIREMENT.fullmatch(entry["requirement"].strip()) is not None,
              f"{label}.requirement {entry['requirement'].strip()!r} is not one requirement ID: name the R-<n> whose "
              "acceptance lines the outcome maps to")
        _need((*_key(entry), entry["due_stage"].strip()) in carried or entry["due_stage"].strip() in allowed,
              f"{label}.due_stage {entry['due_stage'].strip()!r} is not a later stage; use one of {', '.join(allowed)}")


def check_restated(state: Mapping[str, Any], stage: str, result: Any) -> None:
    """Refuse a done result after product-acceptance that must restate the list, or does, without carrying the
    current list forward; CLI gates only."""
    if (not isinstance(result, Mapping) or result.get("outcome") != "done" or stage not in due_stages()
            or not (must_restate(state, stage) or "unverified" in result)):
        return
    _action, source, entries = current_list(state)
    entries = entries or []
    later = due_stages(stage) or (stage,)
    # The handoff is the last stage: nothing moves later, so what it could not observe stays listed as it is.
    move = ("" if stage == "handoff" else
            "move the due_stage of one it could not observe to " + " or ".join(later) + ", ")
    how = ("drop an entry due at " + stage + " that this stage observed (name the observation in summary), " + move
           + "and copy every other entry unchanged; [] when none stays open")
    _need("unverified" in result, f"a done {stage} result restates unverified, the list {source} left: {how}")
    restated = result["unverified"]
    _need(isinstance(restated, list), "unverified must be a list: " + how)
    carried = frozenset((*_key(row), str(row.get("due_stage", "")).strip()) for row in entries)
    _check_entries(restated, later, carried)
    kept = {_key(row) for row in restated}
    dropped = [row for row in entries if _key(row) not in kept and str(row.get("due_stage", "")).strip() != stage]
    _need(not dropped, "unverified drops " + "; ".join(
        _key(row)[0] + " (" + _key(row)[1] + ", due at " + str(row.get("due_stage", "")).strip() + ")"
        for row in dropped) + ": only an entry due at " + stage + " is dropped here, once observed; " + how)
    # An entry still due here after this stage would be due at a stage that has passed: settled or moved, never kept.
    stuck = [row for row in restated if stage != "handoff" and row["due_stage"].strip() == stage]
    _need(not stuck, "unverified keeps " + "; ".join(_key(row)[0] + " (" + _key(row)[1] + ")" for row in stuck)
          + " due at " + stage + ", the stage now ending: " + how)


def canonical(value: Any) -> list[dict[str, str]]:
    """The canonical list for a done result's ``unverified`` field: shape only, so a saved result always loads."""
    _need(isinstance(value, list), "unverified must be a list (empty when every request outcome was observed by "
          "an executed check); " + SHAPE)
    rows = []
    for index, entry in enumerate(value):
        _need(isinstance(entry, Mapping) and all(isinstance(key, str) and isinstance(text, str)
                                                 for key, text in entry.items()),
              f"unverified[{index}] must be an object of text values; " + SHAPE)
        rows.append({key: text.strip() for key, text in entry.items()})
    return rows


def check_submitted(stage: str, result: Any) -> None:
    """Refuse a submitted done result at ``stage`` without a usable list; runs at the CLI gates only."""
    if stage not in STAGES or not isinstance(result, Mapping) or result.get("outcome") != "done":
        return
    later = ", ".join(due_stages(stage))
    _need("unverified" in result, f"a done {stage} result must list unverified: a list, empty when every request "
          f"outcome was observed by an executed check; {SHAPE}; due_stage is one of {later}")
    entries = result["unverified"]
    _need(isinstance(entries, list), "unverified must be a list (empty when every request outcome was observed by "
          "an executed check); " + SHAPE)
    _check_entries(entries, due_stages(stage))


def open_assumptions(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The plan's assumptions whose recorded disposition is ``open``; the ledger never updates a disposition.

    A view of ``shiploop_assumptions.open_items``, the one reader of open rows (consumer contract X10).
    """
    import shiploop_assumptions as assumptions
    return [item.row for item in assumptions.open_items(state) if item.stage == "plan"]


def accepted_list(state: Mapping[str, Any]) -> tuple[str | None, list[Mapping[str, str]] | None]:
    """The action of the current accepted product-acceptance result and its list; None when it has no list."""
    action = planning_revision.current_actions(state).get((None, "product-acceptance"))
    result = state.get("accepted", {}).get(action, {}) if action else {}
    entries = result.get("unverified")
    return action, (list(entries) if isinstance(entries, list) else None)


def html_section(state: Mapping[str, Any]) -> list[str]:
    """The report's section on what product-acceptance left unverified, as the latest stage restated it; nothing
    before it is accepted.  An entry a later stage dropped is listed as settled there."""
    action, first = accepted_list(state)
    if action is None:
        return []
    current_action, source, entries = current_list(state)
    if current_action is None:
        entries = first
    settled = [row for row in first or () if entries is not None and _key(row) not in {_key(r) for r in entries}]
    settled_note = ("<p>Settled after product-acceptance (" + html.escape(str(source)) + " restated the list without "
                    "them): " + "; ".join(html.escape(_key(row)[0] + " " + _key(row)[1]) for row in settled) + "</p>"
                    if settled else "")
    if entries is None:
        note = ("<p>not recorded: this run's product-acceptance result has no unverified list, which is not the "
                "same as none.</p>")
    elif not entries:
        note = ("<p>none listed: " + html.escape(str(source or "product-acceptance")) + " recorded no request outcome "
                "as unverified. Open items another stage recorded are listed under Open items.</p>")
    else:
        heads = ("Outcome", "Requirement", "Reason", "Lower-layer check", "To settle", "Owner", "Due stage")
        rows = ["<tr>" + "".join("<td>" + html.escape(str(row.get(name, ""))) + "</td>" for name in FIELDS) + "</tr>"
                for row in entries]
        note = ("<p>No executed check observed these by the time " + html.escape(str(source or "product-acceptance"))
                + " recorded the list; each has an owner and the stage that reports it.</p>\n<table><thead><tr>" + "".join("<th>" + head + "</th>" for head in heads)
                + "</tr></thead><tbody>\n" + "\n".join(rows) + "\n</tbody></table>")
    return ["<h2>Unverified request outcomes</h2>", note, *([settled_note] if settled_note else [])]


__all__ = ("FIELDS", "STAGES", "SHAPE", "TEMPLATE_ROW", "UnverifiedError", "accepted_list", "canonical",
           "check_restated", "check_submitted", "current_list", "due_stages", "html_section",
           "must_restate", "open_assumptions")
