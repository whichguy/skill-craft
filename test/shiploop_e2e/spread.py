#!/usr/bin/env python3
"""The spread of an A/A calibration epoch (docs/shiploop-e2e-closed-loop-plan-2026-10-30.md, stage 3): how far one
ShipLoop build differs from itself, and so how many attempts per arm and what efficiency tolerance a comparison needs.

    python3 test/shiploop_e2e/spread.py EPOCH_DIR [--attempts 3] [--metric tokens] [--out calibration.json]

Both arms of a calibration epoch run the same build, so every sealed attempt of a case is a sample of that build. For
each case it reports the attempts, successes and failure rate, and per measure the median, minimum and maximum. Then it
replays the promotion rule's own per-success comparison (``promotion._strict_per_success``) over every way of dealing
k attempts to a control and k others to a candidate (sampled, with a fixed seed, past ``--max-splits``): at each
tolerance t in the grid, the share of splits at equal quality that would have decided PROMOTE or DROP is a false
decision rate. The recommended t is the smallest at which that rate is at most 10% on every case (owner decision D1);
none in the grid means the metric cannot decide at k attempts. For a regression case it also gives the chance of at
least one failure in k attempts, the false-DROP risk at ``quality_tolerance`` 0.

``scoring`` digests only what turns a run folder into a card and a comparison (the scorecard's modules, promotion.py,
checks/ and the calibrated cases' catalog entries), not the whole evaluator: a later epoch built on a harness with new
modules can still use this calibration, and ``scoring_digest`` refuses it when anything that scores has changed.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import boundary  # noqa: E402
import promotion  # noqa: E402

CONTRACT = "calibration/1"
GRID = tuple(round(0.05 * step, 2) for step in range(1, 11))  # 0.05 .. 0.50
THRESHOLD = 0.10
MEASURES = ("tokens", "turns", "minutes", "output_tokens", "cost_usd")
# What turns a run folder into a card and two arms into a decision (boundary.qualification_snapshot's scorer modules).
SCORING_MODULES = ("scorecard.py", "boundary.py", "metrics.py", "delivery.py", "environment.py", "runrecord.py",
                   "promotion.py")


IMPORT = re.compile(r"^[ \t]*(?:import|from)[ \t]+([A-Za-z_][A-Za-z0-9_]*)", re.M)


def scoring_files(harness: Path = HERE) -> list[Path]:
    """SCORING_MODULES and every harness module they import, transitively. Editing a module the scorer reads (token
    counting in rollouts.py, say) changes what a card means, so it moves the digest; a module nothing in the closure
    imports does not. A listed module that is missing stays in the list, so reading it fails loudly."""
    seen: set[Path] = set()
    stack = [harness / name for name in SCORING_MODULES]
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        if path.is_file():
            for name in IMPORT.findall(path.read_text(encoding="utf-8", errors="replace")):
                if (harness / f"{name}.py").is_file():
                    stack.append(harness / f"{name}.py")
    return sorted(seen)


def scoring_digest(cases: dict, harness: Path = HERE) -> dict:
    """A digest of the scoring files and the named cases' catalog entries (``cases``: name to entry)."""
    files = scoring_files(harness) + boundary.oracle_files(harness)
    digest, why = boundary.files_digest(harness, files)
    if digest is None:
        raise ValueError(f"scoring files cannot be read: {why}")
    entries = json.dumps({name: cases[name] for name in sorted(cases)}, sort_keys=True).encode()
    combined = hashlib.sha256(digest.encode() + b"\n" + hashlib.sha256(entries).hexdigest().encode()).hexdigest()
    return {"sha256": combined, "files": digest, "cases": sorted(cases)}


def _successes(cards: list[dict], floors: list[str]) -> int:
    return sum(1 for card in cards if promotion._strict_outcome(card, floors)[0] is True)


def _splits(n: int, k: int, limit: int) -> list[tuple[tuple[int, ...], tuple[int, ...]]]:
    """Every (control, candidate) pair of disjoint k-sets of range(n), or `limit` of them drawn with a fixed seed."""
    every = [(left, right) for left in itertools.combinations(range(n), k)
             for right in itertools.combinations([i for i in range(n) if i not in left], k)]
    if len(every) <= limit:
        return every
    return random.Random(0).sample(every, limit)


def case_spread(cards: list[dict], floors: list[str], k: int, limit: int) -> dict:
    outcomes = [promotion._strict_outcome(card, floors)[0] for card in cards]
    successes, failures = outcomes.count(True), outcomes.count(False)
    known = successes + failures
    rate = failures / known if known else None
    report = {"attempts": len(cards), "successes": successes, "failures": failures,
              "unknown": len(cards) - known, "failure_rate": rate,
              "false_drop_risk": None if rate is None else round(1 - (1 - rate) ** k, 4), "measures": {},
              "false_decision": {}, "splits": 0, "quality_split_differs": None}
    for measure in MEASURES:
        values = [(card.get("efficiency") or {}).get(measure) for card in cards
                  if promotion._strict_comparable(card, measure)]
        values = [value for value in values if promotion._finite_number(value)]
        if values:
            report["measures"][measure] = {"n": len(values), "median": statistics.median(values),
                                           "min": min(values), "max": max(values)}
    if len(cards) < 2 * k:
        report["why"] = f"{len(cards)} attempts cannot make two arms of {k}"
        return report
    splits = _splits(len(cards), k, limit)
    report["splits"] = len(splits)
    differs = 0
    changes: dict[str, list[float]] = {measure: [] for measure in MEASURES}
    for left, right in splits:
        control, candidate = [cards[i] for i in left], [cards[i] for i in right]
        won_control, won_candidate = _successes(control, floors), _successes(candidate, floors)
        if won_control != won_candidate:
            differs += 1  # quality decides first: this split never reaches the efficiency rule
            continue
        for measure in MEASURES:
            ctrl, _ = promotion._strict_per_success(control, measure, won_control)
            cand, _ = promotion._strict_per_success(candidate, measure, won_candidate)
            if ctrl and cand is not None:
                changes[measure].append((cand - ctrl) / ctrl)
    report["quality_split_differs"] = round(differs / len(splits), 4)
    for measure, found in changes.items():
        if found:
            report["false_decision"][measure] = {f"{t:.2f}": round(sum(1 for c in found if abs(c) > t) / len(found), 4)
                                                 for t in GRID}
            report["false_decision"][measure]["compared"] = len(found)
    return report


def recommend(cases: dict, metric: str, k: int) -> dict:
    by_case = {}
    for name, report in cases.items():
        rates = report["false_decision"].get(metric)
        by_case[name] = (None if not rates else
                         next((t for t in GRID if rates[f"{t:.2f}"] <= THRESHOLD), None))
    usable = [t for t in by_case.values() if t is not None]
    tolerance = max(usable) if usable and len(usable) == len(by_case) else None
    return {"attempts": k, "metric": metric, "threshold": THRESHOLD, "tolerance": tolerance, "by_case": by_case,
            "why": None if tolerance is not None else
            f"no tolerance in {GRID[0]}..{GRID[-1]} keeps false {metric} decisions at or under {THRESHOLD} on every "
            "case at this many attempts: more attempts, or this metric cannot decide"}


def calibrate(root: Path, k: int = 3, metric: str = "tokens", limit: int = 5000) -> dict:
    import epoch
    import scorecard
    registration = epoch.registration(root)
    if registration.get("purpose") != "calibration":
        raise ValueError("spread reads a calibration epoch (purpose calibration: one build in both arms)")
    floors = list(registration.get("floors") or promotion.DEFAULT_FLOORS)
    frozen = registration["qualification"]["cases"]
    by_case: dict[str, list[dict]] = {name: [] for name in registration["cases"]}
    sealed = 0
    for attempt in registration["attempts"]:
        try:
            output, _ = epoch.sealed_run(root, attempt["id"])
        except (OSError, ValueError):
            continue
        sealed += 1
        by_case[attempt["case"]].append(scorecard.score(output, required_case=frozen[attempt["case"]]))
    cases = {name: case_spread(cards, floors, k, limit) for name, cards in by_case.items()}
    arms = registration.get("arms") or {}
    catalog = json.loads((HERE / "cases.json").read_text())
    return {"contract": CONTRACT, "epoch": str(root), "registration_sha256": epoch.digest(root / "registration.json"),
            "driver": (arms.get("control") or {}).get("driver"), "build": (arms.get("control") or {}).get("shiploop_build"),
            "attempts_sealed": sealed, "attempts_registered": len(registration["attempts"]), "floors": floors,
            "grid": list(GRID), "cases": cases, "recommended": recommend(cases, metric, k),
            "scoring": scoring_digest({name: catalog[name] for name in registration["cases"]})}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("epoch", type=Path)
    parser.add_argument("--attempts", type=int, default=3, help="attempts per arm the recommendation is for")
    parser.add_argument("--metric", default="tokens", choices=MEASURES)
    parser.add_argument("--max-splits", type=int, default=5000)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.attempts < 1:
        parser.error("--attempts must be at least 1")
    try:
        report = calibrate(args.epoch.resolve(), args.attempts, args.metric, args.max_splits)
    except (OSError, ValueError, KeyError) as error:
        print(f"spread: {error}", file=sys.stderr)
        return 1
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.out:
        args.out.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
