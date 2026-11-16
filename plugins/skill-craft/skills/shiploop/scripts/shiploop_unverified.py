#!/usr/bin/env python3
"""Script-owned checks for the request outcomes no executed check observed (SPEC S-14, the case end-state rule).

A done product-acceptance result carries ``unverified``: one entry for each request outcome that no executed
check observed, because the observation is not due yet or cannot be made here ("unachievable" in the case
end-state rule).  The model decides what belongs in the list.  ShipLoop refuses only mechanical faults here when a
result is submitted (a missing list, an entry without its seven texts, a requirement that is not one R-<n>, a template
placeholder left in, a due stage that is not a later stage) and records and prints the rest: it cannot judge whether
the list is complete or an outcome is true.  An empty list says no request outcome remains listed as unverified;
a result without the key says nothing (unmeasured is not zero).  What an entry's requirement and
lower-layer check must hold in the run (an entry in the living spec; for a primary requirement, a test ShipLoop saw
pass) is ``shiploop_primary.check_unverified``'s rule (run-5 batch F6).

Like the plan's assumption list, the stored shape is loose (a list of text mappings, so every saved run loads
whatever a later edit does to the field set) and the exact shape is held at the CLI gate only.

A later stage restates the list (E2E release-gate trio on 2.13.2, 2026-10-26): hello's release-verify settled R-1 in
prose ("Returned main prints the greeting") with no ``unverified`` key, so no reader could tell settled from not
restated.  The handoff, and any stage an entry is due at, carries the current list in its done result: an entry due at
that stage that it observed is dropped with an explicit settlement, one it could not observe moves its due stage
later, and every other entry is carried; ``[]`` once none stays open.  ``current_list`` reads the latest restatement.
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
SETTLEMENT_FIELDS = ("requirement", "outcome", "basis", "evidence_refs")
SETTLEMENT_RULE = (
    "Every removed row needs exactly one settled entry {requirement, outcome, basis, evidence_refs}; "
    "basis is observed (current observation on the required surface) or user-correction (explicit user correction), "
    "with a nonempty list of nonblank, non-placeholder references attributing it. References are host claims, "
    "not proof of truth, currency or authority. A decline, silence, blocked test or lower-layer pass is not a "
    "scope withdrawal. Carry pending rows, defer their due_stage, or use the existing blocked/add-work routes; "
    "delivery-contract observation, correction and replanning gates still apply."
)
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
    seen = set()
    for index, entry in enumerate(entries):
        label = f"unverified[{index}]"
        _need(isinstance(entry, Mapping) and set(entry) == set(FIELDS),
              f"{label} needs exactly {', '.join(FIELDS)}; {SHAPE}")
        for name in FIELDS:
            text = entry[name]
            _need(isinstance(text, str) and bool(text.strip()), f"{label}.{name} must be nonempty text")
            _need(not _is_placeholder(text), f"{label}.{name} is still a template placeholder: "
                  "replace it, or delete the template row when no outcome remains unverified")
        _need(_REQUIREMENT.fullmatch(entry["requirement"].strip()) is not None,
              f"{label}.requirement {entry['requirement'].strip()!r} is not one requirement ID: name the R-<n> whose "
              "acceptance lines the outcome maps to")
        _need(_key(entry) not in seen, f"{label} duplicates a pending requirement/outcome identity")
        seen.add(_key(entry))
        _need((*_key(entry), entry["due_stage"].strip()) in carried or entry["due_stage"].strip() in allowed,
              f"{label}.due_stage {entry['due_stage'].strip()!r} is not a later stage; use one of {', '.join(allowed)}")


def check_restated(state: Mapping[str, Any], stage: str, result: Any) -> None:
    """CLI-only continuity against the latest accepted list, including acceptance revisits and voluntary lists."""
    if (not isinstance(result, Mapping) or result.get("outcome") != "done"
            or stage not in (*STAGES, *due_stages())
            or not (must_restate(state, stage) or "unverified" in result or "settled" in result)):
        return
    _action, source, entries = current_list(state)
    entries = entries or []
    later = due_stages(stage) or (stage,)
    how = ("record removed rows in settled; carry pending rows, "
           + ("or move due_stage later; " if stage != "handoff" else "") + "[] when none stays open")
    _need("unverified" in result, f"a done {stage} result restates unverified alongside settled, "
          f"the list {source} left: {how}")
    restated = result["unverified"]
    _need(isinstance(restated, list), "unverified must be a list: " + how)
    carried = frozenset((*_key(row), str(row.get("due_stage", "")).strip()) for row in entries)
    _check_entries(restated, later, carried)
    kept = {_key(row) for row in restated}
    removed = {_key(row) for row in entries} - kept
    settlements = result.get("settled", [])
    _need(isinstance(settlements, list), "settled must be a list; " + SETTLEMENT_RULE)
    keys = set()
    for index, row in enumerate(settlements):
        label = f"settled[{index}]"
        _need(isinstance(row, Mapping) and set(row) == set(SETTLEMENT_FIELDS),
              label + " needs exactly " + ", ".join(SETTLEMENT_FIELDS))
        for field in ("requirement", "outcome", "basis"):
            text = row[field]
            _need(isinstance(text, str) and bool(text.strip()) and not _is_placeholder(text),
                  f"{label}.{field} must be nonempty text without template placeholders")
        _need(_REQUIREMENT.fullmatch(row["requirement"].strip()) is not None,
              label + ".requirement must be one R-<n>")
        _need(row["basis"].strip() in ("observed", "user-correction"),
              label + ".basis must be observed or user-correction")
        refs = row["evidence_refs"]
        _need(isinstance(refs, list) and bool(refs) and all(
            isinstance(ref, str) and bool(ref.strip()) and not _is_placeholder(ref) for ref in refs),
            label + ".evidence_refs must be a nonempty list of nonblank text without template placeholders")
        key = _key(row)
        _need(key not in keys, label + " duplicates a settled requirement/outcome identity")
        _need(key not in kept, label + " overlaps a pending requirement/outcome identity")
        keys.add(key)
    _need(keys == removed, "settled keys must exactly equal prior pending keys minus submitted pending keys; "
          + "missing: " + repr(sorted(removed - keys)) + "; extra: " + repr(sorted(keys - removed))
          + ". " + SETTLEMENT_RULE)
    dropped = [row for row in entries if _key(row) in removed
               and str(row.get("due_stage", "")).strip() != stage]
    _need(stage == "product-acceptance" or not dropped,
          "unverified drops an outcome off-stage: only an entry whose previous due_stage equals "
          + stage + " may be removed here; " + how)
    stuck = [row for row in restated if stage != "handoff" and row["due_stage"].strip() == stage]
    _need(not stuck, "unverified keeps " + "; ".join(_key(row)[0] + " (" + _key(row)[1] + ")" for row in stuck)
          + " due at " + stage + ", the stage now ending: " + how)


def canonical_settled(value: Any) -> Any:
    """Copy recorded settlement data without retrospective CLI validation on load."""
    import copy
    return copy.deepcopy(value)


def canonical(value: Any) -> list[dict[str, str]]:
    """The canonical list for a done result's ``unverified`` field: shape only, so a saved result always loads."""
    _need(isinstance(value, list), "unverified must be a list (empty when none remains listed as unverified); " + SHAPE)
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
    _need("unverified" in result, f"a done {stage} result must list unverified: a list, empty when no request "
          f"outcome remains unverified; {SHAPE}; due_stage is one of {later}")
    entries = result["unverified"]
    _need(isinstance(entries, list), "unverified must be a list (empty when none remains listed as unverified); " + SHAPE)
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
    """Show the latest pending list and recorded dispositions, without treating omission as settlement."""
    action, first = accepted_list(state)
    if action is None:
        return []
    current_action, source, entries = current_list(state)
    if current_action is None:
        entries = first
    dispositions = []
    previous = []
    for event in state.get("history") or ():
        if event.get("outcome") != "done":
            continue
        result = state.get("accepted", {}).get(event.get("action"), {})
        if not isinstance(result, Mapping) or not isinstance(result.get("unverified"), list):
            continue
        recorded = result.get("settled", [])
        keys = set()
        for row in recorded if isinstance(recorded, list) else ():
            if not isinstance(row, Mapping):
                continue
            keys.add(_key(row))
            refs = row.get("evidence_refs", [])
            refs = refs if isinstance(refs, list) else [refs]
            dispositions.append("<li>" + html.escape(str(event.get("action")) + " / " + str(event.get("stage"))
                + ": " + " ".join(_key(row)) + " | basis: " + str(row.get("basis", ""))
                + " | refs: " + "; ".join(map(str, refs))) + "</li>")
        remaining = {_key(row) for row in result["unverified"]}
        omitted = {_key(row) for row in previous} - remaining - keys
        for key in sorted(omitted):
            dispositions.append("<li>Historical omission without a recorded settlement: "
                + html.escape(" ".join(key) + " / " + str(event.get("action")) + " / " + str(event.get("stage")))
                + "</li>")
        previous = result["unverified"]
    settled_note = ("<p>Recorded settlements (host claims); reopened outcomes remain pending in the current list.</p>"
                    + "<ul>" + "".join(dispositions) + "</ul>" if dispositions else "")
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
        note = ("<p>Currently pending, as of " + html.escape(str(source or "product-acceptance"))
                + " recorded the list; each has an owner and the stage that reports it.</p>\n<table><thead><tr>" + "".join("<th>" + head + "</th>" for head in heads)
                + "</tr></thead><tbody>\n" + "\n".join(rows) + "\n</tbody></table>")
    return ["<h2>Unverified request outcomes</h2>", note, *([settled_note] if settled_note else [])]


__all__ = ("FIELDS", "STAGES", "SHAPE", "SETTLEMENT_RULE", "TEMPLATE_ROW", "UnverifiedError", "accepted_list", "canonical",
           "canonical_settled",
           "check_restated", "check_submitted", "current_list", "due_stages", "html_section",
           "must_restate", "open_assumptions")
