#!/usr/bin/env python3
"""Script-owned checks for the plan's assumption list.

A ``done`` plan result carries ``assumptions``: every load-bearing assumption
with a disposition.  The model chooses which probes to run; these
checks make a skipped probe visible instead of silent.  They verify shape,
links and existence, never whether a list is complete or a locator true.
"""

from __future__ import annotations

import re
import stat
from pathlib import Path
from typing import Any, Mapping

STAGES = frozenset(("plan",))
DISPOSITIONS = ("evidenced", "probed", "open")
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")
_URL = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://\S+$")
# The fields each disposition must carry, beyond id, assumption and disposition.
_FIELDS = {
    "evidenced": frozenset(("evidence",)),
    "probed": frozenset(("check", "evidence")),
    "open": frozenset(("check", "reason", "consumer")),
}
_SHAPE = (
    "each assumption is {id, assumption, disposition} plus: evidenced -> evidence "
    "(list of absolute paths or URLs); probed -> check (the read or command) and "
    "evidence (its captured output); open -> check (what would settle it), reason "
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
