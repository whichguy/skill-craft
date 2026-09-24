"""Incorporated until-loop continuation policy, with ShipLoop evidence semantics.

Adapted from the repeat/verify/continue contract of until-loop 0.1.3,
scripts/until-loop (local source commit 7fb7057056552438fa39ccf11b70fa7c63f80077,
declared MIT). This is an internal adaptation, not the standalone CLI.
README.md records this provenance; references/execution-planning.md
(Until-loop incorporation and limits) states the intentional differences.
Action reasoning guidance also adapts until-loop 0.2.1 at 7d24bbc; the
standalone runtime and its state/completion semantics are not imported.

The repeated unit is a review-and-improve cycle: review changes, consider
improvements, plan from recent full Git messages, implement, check and commit.
The caller owns the existing Markdown transaction, validates evidence and audit
commits, and passes completed cycle receipts. This module performs no I/O, creates no
second state store, and never trusts a host-supplied done flag or cached streak.
Readiness is not final success: the caller must still perform fresh final checks.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


class UntilError(ValueError):
    """The completed-pass evidence cannot support a continuation decision."""


def action_reasoning() -> str:
    """Allow same-loop continuity without making memory an evidence source."""
    return (
        "Reset-safe context: read selected Markdown; same-loop memory is optional, Markdown wins. "
        "Record gaps/new evidence; adapt failed strategies. "
        "Check all clauses; missing proof is incomplete. Only scripts advance/count cycles."
    )


def review_improve_cycle(history_limit: int) -> str:
    """Project the common cycle into cold packets; owners retain their gates."""
    if type(history_limit) is not int or history_limit < 1:
        raise UntilError("review-and-improve history limit must be a positive integer")
    return (
        "Review-and-improve cycle (owning loop):\n"
        "1. Review changes.\n"
        "2. Consider improvements.\n"
        f"3. Plan improvements using the last {history_limit} full Git commit bodies "
        "(all if fewer).\n"
        "4. Implement every approved improvement, including trivial fixes. "
        "Run required checks and create the verbose learning commit, including Key learnings.\n"
        "5. Repeat until two consecutive completed trivial reviews, not callbacks. "
        "Material changes reset the streak; apply fixes, run checks, and commit before counting a pass."
    )


def decide(passes: list[dict[str, Any]], *, open_findings: list[Any]) -> dict[str, Any]:
    """Compatibility facade for Improve's canonical receipt-derived decision.

    Legacy callers keep their existing phase ownership. Managed invocations use
    the same implementation from their child controller; no second algorithm or
    cached parent streak can substitute for completed evidence.
    """
    from _improve_managed import ManagedImproveError, decide as improve_decide
    try:
        return improve_decide(passes, open_findings=open_findings)
    except ManagedImproveError as exc:
        raise UntilError(str(exc)) from exc
