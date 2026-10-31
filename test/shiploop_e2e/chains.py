#!/usr/bin/env python3
"""A follow-on chain: the cases a case follows, read to their end (SPEC, "Follow-on chains and the delta ledger", 2026-10-31).

A follow-on starts from the run before it, so a case's ``follows`` names one case and that case may follow another. Before this
module ``run.load_case`` read one level: link 3 of a chain re-ran link 2's own checks and dropped link 1's, and lost link 1's
quality acceptance when link 2 declared none. The scorecard read a case's own ``quality`` and so would not have required an
acceptance a third link inherited. Both now read the chain here, so neither can read a different one (SPEC S-12: one
implementation per mechanism).

Pure functions over the ``cases.json`` mapping; nothing is read from disk and nothing is written.
"""

from __future__ import annotations

# The keys of a case's ``quality`` block that a follow-on inherits, key by key, from the nearest case that declares them.
QUALITY_KEYS = ("mutation", "acceptance", "refuse_ports")


class ChainError(ValueError):
    """A chain that cannot be read: a name that is no case, or a chain that comes back to a case it passed."""


def of(cases: dict, name: str) -> list[str]:
    """The case and every case it follows, oldest first. A name that is no case, and a loop, raise ChainError."""
    chain: list[str] = []
    current: str | None = name
    while current:
        if current in chain:
            raise ChainError(f"case {current!r} follows itself: {' -> '.join([*reversed(chain), current])}")
        if current not in cases:
            raise ChainError(f"case {chain[0]!r} follows {current!r}, which is no case" if chain else f"unknown case {current!r}")
        chain.insert(0, current)
        current = cases[current].get("follows")
    return chain


def regression(cases: dict, name: str) -> list[str]:
    """Each earlier link's own checks, oldest first. A check an earlier link already contributed is not run twice; one link's own
    list is never thinned, so a two-link chain's list is the followed case's ``checks`` exactly."""
    found: list[str] = []
    for ancestor in of(cases, name)[:-1]:
        held = list(found)
        found += [check for check in cases[ancestor]["checks"] if check not in held]
    return found


def quality(cases: dict, name: str) -> dict:
    """The quality measures of a case: its own declaration, else the nearest one among the cases it follows, key by key.
    ``{}`` for a case that declares none and for a name that is no case."""
    if name not in cases:
        return {}
    found: dict = {}
    for ancestor in reversed(of(cases, name)):  # the case itself first, then each case it follows
        declared = cases[ancestor].get("quality") or {}
        for key in QUALITY_KEYS:
            if not found.get(key) and declared.get(key):
                found[key] = declared[key]
    return found
