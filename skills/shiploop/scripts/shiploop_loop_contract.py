"""The one shape of a ShipLoop-written Until Loop contract (SPEC S-12, S-10).

The test loop, the quality loop and every Improve child start the bound Until
Loop runtime from a contract ShipLoop writes. Each loop supplies its own
content; this module owns the shape, the serialization, and the exit clause a
review loop adds from its stage's own ``done_when`` criteria.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Optional, Sequence

import shiploop_stage_spec as stage_spec


def contract(*, workspace: str, work: str, exit_condition: str, repeat_condition: str,
             required_trivial_reviews: int, request: str, scope: str, authority: str, environment: str,
             resources: Sequence[Mapping[str, str]]) -> Dict[str, Any]:
    """A complete Until Loop start contract; every field is required."""
    return {
        "workspace": workspace,
        "work": work,
        "exit_condition": exit_condition,
        "repeat_condition": repeat_condition,
        "required_trivial_reviews": required_trivial_reviews,
        "context": {"request": request, "scope": scope, "authority": authority, "environment": environment,
                    "resources": [dict(resource) for resource in resources]},
    }


# The Until Loop runtime persists its whole state (frozen contract, latest report, progress) in at most
# STATE_LIMIT bytes (until_loop_ephemeral.MAX_STATE_BYTES; a test pins the two together). A contract that
# fills the file leaves no room for the first review report, which then cannot be saved. So a contract may
# use only STATE_LIMIT minus two reserves:
#   STATE_OVERHEAD  the state's own keys, run id, action number, streak, tree id and receipt path (about
#                   420 bytes measured with a 250-character path), rounded up for longer paths;
#   REPORT_RESERVE  the first report (evidence and a compact handoff). Observed sizes, batch 1003: a Luna
#                   Backchain plan report of 5,335 bytes (rejected for size) and Improve child reports up to
#                   2,928 bytes; a Codex xhigh child with a 12,448-byte contract had a report refused for size.
STATE_LIMIT = 16 * 1024
STATE_OVERHEAD = 1024
REPORT_RESERVE = 6 * 1024
CONTRACT_BUDGET = STATE_LIMIT - STATE_OVERHEAD - REPORT_RESERVE


def _bytes(value: Any) -> int:
    # Exactly the runtime's serialization: compact, sorted keys, and the default ensure_ascii, which writes a
    # non-ASCII character as 6 bytes (12 for an emoji), not the 3 or 4 of its UTF-8 form.
    return len(json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def compact_bytes(value: Mapping[str, Any]) -> int:
    """The contract's size as the runtime counts it in its state file."""
    return _bytes(value)


def text_bytes(text: str) -> int:
    """The bytes a piece of text costs inside the state file (escaped like the rest of the contract)."""
    return _bytes(text) - 2  # the surrounding quotes belong to the field, not to the text


def size_problem(value: Mapping[str, Any], *, writable: Optional[Mapping[str, str]] = None,
                 allowance: Optional[int] = None, sizes: Optional[Mapping[str, int]] = None) -> Optional[str]:
    """Why this contract would leave the loop no room for its first report, or None when it fits.

    ``writable`` maps the contract parts a model wrote (for example ``context.environment``) to the name a
    model knows them by (the opening's heading); only those parts are listed and told to be shortened, since
    ShipLoop's own text is not the model's to change. ``allowance`` is how many bytes those parts may use in
    all, known only to the caller (it depends on ShipLoop's fixed text and the run's paths). ``sizes`` gives
    each model-written section's own bytes by the name the model knows it by; the contract fields wrap those
    sections in ShipLoop's text, so only the section sizes are comparable to ``allowance``.
    """
    total = _bytes(value)
    if total <= CONTRACT_BUDGET:
        return None
    context = value.get("context") or {}
    parts = {name: _bytes(value.get(name)) for name in ("work", "exit_condition", "repeat_condition")}
    parts.update({"context." + name: _bytes(context.get(name))
                  for name in ("request", "scope", "authority", "environment", "resources")})
    if sizes:
        shown = {name: size for name, size in sizes.items()}
    elif writable:
        shown = {writable[part]: parts.get(part, 0) for part in writable}
    else:
        shown = parts
    largest = ", ".join(f"{name} {size:,}" for name, size in sorted(shown.items(), key=lambda kv: -kv[1])[:4])
    room = f" The text you wrote may use about {allowance:,} bytes in all." if allowance else ""
    remedy = ("Shorten the sections above" if writable else "Shorten the text you wrote") + (
        ", starting with the largest, and put long detail in a file whose path you name (a path costs a few "
        "bytes; keep the reasoning a later review needs inline)")
    return (f"the loop contract is {total:,} bytes, {total - CONTRACT_BUDGET:,} over its {CONTRACT_BUDGET:,}-byte "
            f"budget: the Until Loop keeps its whole state (contract, latest report, progress) in "
            f"{STATE_LIMIT:,} bytes and needs about {REPORT_RESERVE + STATE_OVERHEAD:,} free for its bookkeeping and "
            f"the first review report, so a larger contract can start yet fail to save that report. Largest "
            f"parts you wrote (bytes): {largest}.{room} {remedy}")


def dumps(value: Mapping[str, Any]) -> str:
    """The on-disk form of a contract: stable key order, so equal contracts are equal bytes."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def stage_exit(stage: str) -> str:
    """The stage's own done-when criteria, stated as part of a review loop's exit condition."""
    criteria = stage_spec.stage(stage).done_when
    return " The " + stage + " result meets its own done-when criteria: " + "; ".join(criteria) + "."


__all__ = ("CONTRACT_BUDGET", "REPORT_RESERVE", "STATE_LIMIT", "STATE_OVERHEAD", "compact_bytes", "contract", "dumps",
           "size_problem", "stage_exit", "text_bytes")
