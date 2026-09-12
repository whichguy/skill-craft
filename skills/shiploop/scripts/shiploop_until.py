"""Incorporated until-loop continuation policy, with ShipLoop evidence semantics.

Adapted from the repeat/verify/continue contract of until-loop 0.1.3,
scripts/until-loop (local source commit 7fb7057056552438fa39ccf11b70fa7c63f80077,
declared MIT). This is an internal adaptation, not the standalone CLI. See
references/execution-planning.md for provenance and intentional differences.

The caller owns the existing Markdown transaction, validates evidence and audit
commits, and passes completed receipts. This module performs no I/O, creates no
second state store, and never trusts a host-supplied done flag or cached streak.
Readiness is not final success: the caller must still perform fresh final checks.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


class UntilError(ValueError):
    """The completed-pass evidence cannot support a continuation decision."""


def decide(passes: list[dict[str, Any]], *, open_findings: list[Any]) -> dict[str, Any]:
    """Derive two-trivial readiness from unique, verified, audited pass receipts.

    ``passes`` contains only completed passes in the current repair epoch.
    Interrupted attempts remain in the caller's Markdown audit history but
    cannot be supplied as completed evidence. Every pass must have a stable ID,
    outcome, verified=True and a distinct full Git commit SHA. Material passes
    reset the consecutive streak. Any open finding keeps the loop active.
    """
    if not isinstance(passes, list) or not isinstance(open_findings, list):
        raise UntilError("until-loop requires completed-pass and open-finding lists")
    ids: set[str] = set()
    commits: set[str] = set()
    streak = 0
    for row in passes:
        if not isinstance(row, Mapping):
            raise UntilError("until-loop pass must be a record")
        pass_id = row.get("id")
        commit = row.get("commit")
        if not isinstance(pass_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", pass_id):
            raise UntilError("until-loop pass requires a safe stable ID")
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
            raise UntilError("until-loop pass requires a full audit commit SHA")
        if pass_id in ids or commit in commits:
            raise UntilError("until-loop repeated pass or commit cannot count twice")
        if row.get("verified") is not True:
            raise UntilError("until-loop cannot count an unverified pass")
        if row.get("outcome") not in ("material", "trivial"):
            raise UntilError("until-loop pass outcome must be material or trivial")
        ids.add(pass_id)
        commits.add(commit)
        streak = streak + 1 if row["outcome"] == "trivial" else 0
    # Standalone until-loop's done-when + verification branch becomes readiness
    # derived from durable receipts. Neither a budget limit nor a done claim is
    # an alternative terminal condition in ShipLoop.
    done_when = streak >= 2 and not open_findings
    return {"phase": "ready" if done_when else "active", "trivial_streak": streak}
