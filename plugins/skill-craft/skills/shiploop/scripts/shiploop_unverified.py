#!/usr/bin/env python3
"""Script-owned checks for the request outcomes no executed check observed (SPEC S-14, the case end-state rule).

A done product-acceptance result carries ``unverified``: one entry for each request outcome that no executed
check observed, because the observation is not due yet or cannot be made here ("unachievable" in the case
end-state rule).  The model decides what belongs in the list.  ShipLoop refuses only mechanical faults when a
result is submitted (a missing list, an entry without its five texts, a template placeholder left in, a due stage
that is not a later stage) and records and prints the rest: it cannot judge whether the list is complete or an
outcome is true.  An empty list says every request outcome was observed by an executed check; a result without
the key says nothing (unmeasured is not zero).

Like the plan's assumption list, the stored shape is loose (a list of text mappings, so every saved run loads
whatever a later edit does to the field set) and the exact shape is held at the CLI gate only.
"""

from __future__ import annotations

import html
from typing import Any, Mapping

import shiploop_planning_revision as planning_revision
import shiploop_stage_spec as stage_spec

STAGES = frozenset(("product-acceptance",))
FIELDS = ("outcome", "reason", "check", "owner", "due_stage")
# The one row the result template prints, to replace or delete.  A text that starts with "<" and ends with ">" is
# a placeholder, so a row edited in one field only is refused as the whole row copied is.
TEMPLATE_ROW = {
    "outcome": "<request outcome no executed check observed>",
    "reason": "<why not observed here, or not due yet>",
    "check": "<what the owner does and reports>",
    "owner": "<who>",
    "due_stage": "handoff",
}
SHAPE = ("each entry is {outcome, reason, check, owner, due_stage}: the request outcome no executed check "
         "observed, why, what the owner does and reports to settle it, who the owner is, and the later stage "
         "that reports it")


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
    for index, entry in enumerate(entries):
        label = f"unverified[{index}]"
        _need(isinstance(entry, Mapping) and set(entry) == set(FIELDS),
              f"{label} needs exactly {', '.join(FIELDS)}; {SHAPE}")
        for name in FIELDS:
            text = entry[name]
            _need(isinstance(text, str) and bool(text.strip()), f"{label}.{name} must be nonempty text")
            _need(not _is_placeholder(text), f"{label}.{name} is still a template placeholder: "
                  "replace it, or delete the row when every request outcome was observed by an executed check")
        _need(entry["due_stage"].strip() in due_stages(stage),
              f"{label}.due_stage {entry['due_stage'].strip()!r} is not a later stage; use one of {later}")


def open_assumptions(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The plan's assumptions whose recorded disposition is ``open``; the ledger never updates a disposition."""
    action = planning_revision.current_actions(state).get((None, "plan"))
    plan = state.get("accepted", {}).get(action, {}) if action else {}
    return [row for row in plan.get("assumptions") or () if isinstance(row, Mapping) and row.get("disposition") == "open"]


def accepted_list(state: Mapping[str, Any]) -> tuple[str | None, list[Mapping[str, str]] | None]:
    """The action of the current accepted product-acceptance result and its list; None when it has no list."""
    action = planning_revision.current_actions(state).get((None, "product-acceptance"))
    result = state.get("accepted", {}).get(action, {}) if action else {}
    entries = result.get("unverified")
    return action, (list(entries) if isinstance(entries, list) else None)


def due_entries(state: Mapping[str, Any], stage: str) -> list[Mapping[str, str]]:
    """The accepted entries whose due stage is ``stage``."""
    return [row for row in accepted_list(state)[1] or () if row.get("due_stage") == stage]


def html_section(state: Mapping[str, Any]) -> list[str]:
    """The report's section on what product-acceptance left unverified; nothing before it is accepted."""
    action, entries = accepted_list(state)
    if action is None:
        return []
    if entries is None:
        note = ("<p>not recorded: this run's product-acceptance result has no unverified list, which is not the "
                "same as none.</p>")
    elif not entries:
        note = ("<p>none listed: product-acceptance recorded no request outcome as unverified. Open items "
                "another stage recorded are in that stage's own result.</p>")
    else:
        heads = ("Outcome", "Reason", "Check", "Owner", "Due stage")
        rows = ["<tr>" + "".join("<td>" + html.escape(str(row.get(name, ""))) + "</td>" for name in FIELDS) + "</tr>"
                for row in entries]
        note = ("<p>No executed check observed these when product-acceptance ran; each has an owner and the stage "
                "that reports it.</p>\n<table><thead><tr>" + "".join("<th>" + head + "</th>" for head in heads)
                + "</tr></thead><tbody>\n" + "\n".join(rows) + "\n</tbody></table>")
    return ["<h2>Unverified request outcomes</h2>", note]


__all__ = ("FIELDS", "STAGES", "SHAPE", "TEMPLATE_ROW", "UnverifiedError", "accepted_list", "canonical",
           "check_submitted", "due_entries", "due_stages", "html_section", "open_assumptions")
