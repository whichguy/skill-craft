#!/usr/bin/env python3
"""Script-owned checks for the assumption lists: the plan's, and the open items of later stages.

A ``done`` plan result carries ``assumptions``: every load-bearing assumption
with a disposition.  The model chooses which probes to run; these
checks make a skipped probe visible instead of silent.  They verify shape,
links and existence, never whether a list is complete or a locator true.

Open items (consumer contract X10, 2026-10-11): test-spec, verify, carry-forward, system-test-author, system-test,
release-plan and release-verify record what they leave unproven in the same list.  There an open row's consumer is a
later OUTER stage, or the same item's carry-forward when the producer is test-spec or verify, and it may name an
``owner`` (a person).  ``open_items`` is the one reader of the rows still open.
"""

from __future__ import annotations

import re
import stat
from pathlib import Path
from typing import Any, List, Mapping, NamedTuple, Tuple

import shiploop_planning_revision as planning_revision
import shiploop_stage_spec as stage_spec

# The plan (whose open rows name a work item) and the open-item stages after it (whose open rows name a stage).
OPEN_ITEM_STAGES = frozenset(("test-spec", "verify", "carry-forward", "system-test-author", "system-test",
                              "release-plan", "release-verify"))
STAGES = frozenset(("plan",)) | OPEN_ITEM_STAGES
# The producers whose open item may name their own item's carry-forward as its consumer.
CARRY_FORWARD_PRODUCERS = ("test-spec", "verify")
DISPOSITIONS = ("evidenced", "probed", "open")
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://\S+$")
# The fields each disposition must carry, beyond id, assumption and disposition.
_FIELDS = {
    "evidenced": frozenset(("evidence",)),
    "probed": frozenset(("check", "evidence")),
    "open": frozenset(("settle", "reason", "consumer")),
}
_SHAPE = (
    "each assumption is {id, assumption, disposition} plus: evidenced -> evidence "
    "(list of absolute paths or URLs); probed -> check (the read or command) and "
    "evidence (its captured output); open -> settle (what would settle it), reason "
    "(why it was not run) and consumer (the work item that settles or blocks on it)"
)


class AssumptionError(ValueError):
    """Raised when an assumption list is missing, malformed or dropped."""


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise AssumptionError(message)


def _text(value: Any, label: str) -> str:
    _need(isinstance(value, str) and bool(value.strip()), f"{label} must be nonempty text")
    return value


def canonical(value: Any, stage: str) -> list[dict[str, Any]]:
    """Return the canonical list for a ``done`` research or plan result."""
    _need(isinstance(value, list),
          f"a done {stage} result requires assumptions: a list (empty only when there "
          f"are none); {_SHAPE}")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, entry in enumerate(value):
        label = f"assumptions[{index}]"
        _need(isinstance(entry, Mapping), f"{label} must be an object; {_SHAPE}")
        ident = entry.get("id")
        _need(isinstance(ident, str) and _ID.fullmatch(ident) is not None,
              f"{label}.id must be a short identifier such as A1")
        _need(ident not in seen, f"assumption {ident} is listed twice")
        seen.add(ident)
        label = f"assumption {ident}"
        disposition = entry.get("disposition")
        _need(disposition in DISPOSITIONS,
              f"{label}.disposition must be one of {', '.join(DISPOSITIONS)}")
        required = _FIELDS[disposition]
        keys = set(entry) - {"id", "assumption", "disposition"}
        if "owner" in keys:
            _need(disposition == "open" and stage in OPEN_ITEM_STAGES,
                  f"{label}: owner is only for an open item at " + ", ".join(sorted(OPEN_ITEM_STAGES))
                  + "; delete it")
            keys = keys - {"owner"}
        _need(keys == required,
              f"{label} ({disposition}) needs exactly {', '.join(sorted(required))}; {_SHAPE}")
        row: dict[str, Any] = {
            "id": ident,
            "assumption": _text(entry.get("assumption"), f"{label}.assumption"),
            "disposition": disposition,
        }
        for key in sorted(required):
            if key == "evidence":
                refs = entry[key]
                _need(isinstance(refs, list) and bool(refs),
                      f"{label}.evidence must be a nonempty list of absolute paths or URLs")
                row[key] = [_text(ref, f"{label}.evidence entry") for ref in refs]
            else:
                row[key] = _text(entry[key], f"{label}.{key}")
        if "owner" in entry:
            row["owner"] = _text(entry["owner"], f"{label}.owner (a person)")
        rows.append(row)
    return rows


def check_consumers(current: list[Mapping[str, Any]], consumers: set[str]) -> None:
    """Refuse an open assumption that names no work item in the plan's queue."""
    for row in current:
        if row["disposition"] == "open":
            _need(row["consumer"] in consumers,
                  f"open assumption {row['id']} names consumer {row['consumer']!r}, which is "
                  "not a work item in this plan; name the work item that must settle or "
                  "block on it (" + ", ".join(sorted(consumers)) + ")")


def check_files(rows: list[Mapping[str, Any]]) -> None:
    """At submission, require every local evidence locator to exist.

    A probed assumption also needs at least one local, nonempty regular file:
    its captured output.  This rules out citing a probe from memory; it cannot
    prove the command ran.
    """
    for row in rows:
        label = f"assumption {row['id']}"
        local_outputs = 0
        for ref in row.get("evidence", ()):
            if _URL.fullmatch(ref):
                continue
            path = Path(ref)
            _need(path.is_absolute(),
                  f"{label} evidence {ref!r} must be an absolute path or a URL")
            try:
                metadata = path.stat()
            except OSError:
                raise AssumptionError(f"{label} evidence {ref} does not exist") from None
            if stat.S_ISREG(metadata.st_mode) and metadata.st_size > 0:
                local_outputs += 1
        if row["disposition"] == "probed":
            _need(local_outputs > 0,
                  f"{label} is probed but cites no captured output; save the probe's output "
                  "to a file and list its absolute path in evidence")


def allowed_consumers(stage: str) -> Tuple[str, ...]:
    """The consumers an open item at an open-item ``stage`` may name, in graph order.

    A later OUTER stage, or ``carry-forward`` (the same item's) when the producer is test-spec or verify.  Work for a
    later work item goes through carry-forward's work_items, as before (K12).
    """
    order = stage_spec.STAGES
    later = [name for name in stage_spec.OUTER if order.index(name) > order.index(stage)]
    return tuple((["carry-forward"] if stage in CARRY_FORWARD_PRODUCERS else []) + later)


def wrong_consumers(rows: List[Mapping[str, Any]], stage: str) -> List[Tuple[str, str]]:
    """``(id, consumer)`` of each open row at an open-item ``stage`` whose consumer is not allowed there."""
    allowed = allowed_consumers(stage)
    return [(str(row["id"]), str(row["consumer"])) for row in rows
            if row.get("disposition") == "open" and row.get("consumer") not in allowed]


class OpenItem(NamedTuple):
    """An open assumption row and where it was recorded: its stage, work item and action."""
    stage: str                 # the stage whose result recorded the row
    workitem: Any              # its work item, or None for a root stage
    action: str                # the result's action
    row: Mapping[str, Any]     # the open row, as recorded


def open_items(state: Mapping[str, Any]) -> List[OpenItem]:
    """Every open row still open, from each current result at ``STAGES``, in the order the results were accepted.

    Current means ``planning_revision.current_actions``.  The plan's rows (consumer: a work item) stay open, as the
    ledger never updates a disposition.  A later stage's row is settled once a done result of its consumer stage (for
    carry-forward, the same item's) is current and was accepted after the row's result; a row that result carries
    forward (the same ID, open again) is its own row from then on.  A consumer with no assumptions field settles by its
    done result.
    """
    current = planning_revision.current_actions(state)
    accepted = state.get("accepted") or {}
    order = {}
    for index, entry in enumerate(state.get("history") or ()):
        if isinstance(entry, Mapping) and isinstance(entry.get("action"), str):
            order[entry["action"]] = index
    found: List[Tuple[int, int, OpenItem]] = []
    for (workitem, stage), action in current.items():
        if stage not in STAGES:
            continue
        result = accepted.get(action)
        if not isinstance(result, Mapping):
            continue
        for position, row in enumerate(result.get("assumptions") or ()):
            if not isinstance(row, Mapping) or row.get("disposition") != "open":
                continue
            if stage != "plan" and _settled(row, order.get(action, -1), workitem, current, accepted, order):
                continue
            found.append((order.get(action, -1), position, OpenItem(stage, workitem, action, row)))
    return [item for _, _, item in sorted(found, key=lambda entry: (entry[0], entry[1]))]


def _settled(row: Mapping[str, Any], produced: int, workitem: Any, current: Mapping[Tuple[Any, str], str],
             accepted: Mapping[str, Any], order: Mapping[str, int]) -> bool:
    consumer = row.get("consumer")
    key = (workitem, "carry-forward") if consumer == "carry-forward" else (None, consumer)
    action = current.get(key)
    # The consumer's later done result settles the row.  A row it carries forward (the same ID, open again) is that
    # result's own open row, listed from there with its new consumer; keeping this one would list the item twice and
    # leave it open after its new consumer had finished.
    return action is not None and order.get(action, -1) > produced
