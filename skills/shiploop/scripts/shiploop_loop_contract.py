"""The one shape of a ShipLoop-written Until Loop contract (SPEC S-12, S-10).

The test loop, the quality loop and every Improve child start the bound Until
Loop runtime from a contract ShipLoop writes. Each loop supplies its own
content; this module owns the shape, the serialization, and the exit clause a
review loop adds from its stage's own ``done_when`` criteria.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Mapping, Sequence

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


def dumps(value: Mapping[str, Any]) -> str:
    """The on-disk form of a contract: stable key order, so equal contracts are equal bytes."""
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def stage_exit(stage: str) -> str:
    """The stage's own done-when criteria, stated as part of a review loop's exit condition."""
    criteria = stage_spec.stage(stage).done_when
    return " The " + stage + " result meets its own done-when criteria: " + "; ".join(criteria) + "."


__all__ = ("contract", "dumps", "stage_exit")
