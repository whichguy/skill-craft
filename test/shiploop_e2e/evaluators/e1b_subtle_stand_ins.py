#!/usr/bin/env python3
"""E1b: do the item's tests reject subtle weaker implementations (round 1's crude stand-ins hit a ceiling)?

    python3 test/shiploop_e2e/evaluators/e1b_subtle_stand_ins.py score <sample>
    python3 test/shiploop_e2e/evaluators/e1b_subtle_stand_ins.py verify

Case ``stand-in-rules`` (fixture node-orders): the request states rules that four stand-ins each break while staying
plausible, every one modelling a weak test run 4 (2026-10-20, chess) let through:
- ``one-rule-missing``: status is not lower-cased; the totals stay right (run 4: perft sizes only, membership unchecked);
- ``tested-only``: rejects only qty 0, the example's input, and accepts -2 (run 4: absence asserted at fixed inputs);
- ``limit-never-trips``: fifty meter ticks per order, killed only by a bound below the meter's hard 10,000-tick limit
  (run 4: ``cpu < 10000`` cannot fail because the platform throws first);
- ``cross-field``: each field valid alone, open with a shipped_at date accepted (run 4: en-passant square unchecked).
Scoring is E1's (evaluators/e1_stand_ins.py): each stand-in is laid over a copy of the final tree and the focused
command runs; ``value`` is the fraction killed (0-1), not pass/fail; None when the tree's own tests fail. ``verify``:
the reference with a run-4-style weak test file lets all four survive (0.0); with a strong file all four die (1.0).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import e1_stand_ins  # noqa: E402

CASE = "stand-in-rules"


def score(sample: Path) -> dict:
    found = e1_stand_ins.score(sample, CASE)
    if found.get("value") is not None:
        found["all_killed"] = found["value"]
        found["value"] = found["killed_fraction"]
    return found


def verify() -> list[dict]:
    return e1_stand_ins.verify(CASE)


if __name__ == "__main__":
    raise SystemExit(common.cli(sys.modules[__name__], sys.argv[1:]))
