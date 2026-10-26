#!/usr/bin/env python3
"""The promotion contract (SPEC "The promotion contract"): promote, drop or leave undecided a candidate change to ShipLoop,
from the scorecards of a control arm and a candidate arm, under a registration written before the runs.

    python3 test/shiploop_e2e/promotion.py --registration REG.json --control RUN_OR_CARDS ... --candidate RUN_OR_CARDS ... [--json]

An arm is any mix of run folders (scored with scorecard.py) and card files (`scorecard.py --out`). Exit 0 PROMOTE,
3 DROP, 4 UNDECIDED; a registration that cannot be used exits 1 with the reason. Nothing is written and no model is called.

The registration (JSON)::

    {"contract": "promotion/4",
     "registered_at": 1792900000,                       # epoch seconds; a run that began earlier makes the decision UNDECIDED
     "cases": {"hello": "regression",                   # a role, or {"role": ..., "attempts": n}: the expected attempts per arm
               "battleship": {"role": "capability", "attempts": 2}},
     "floors": ["accuracy", "fidelity"],                # the required floors (the default)
     "quality_tolerance": 0.0,                          # a share change within it is "equal quality"
     "efficiency": ["cost_usd", "minutes"],             # cost per successful case, in order; the first that decides wins
     "tolerance": 0.10,                                 # relative; within it a metric decides nothing
     "budget": {"cost_usd": 40.0}}                      # optional: candidate per-success cost above it is DROP

The rule, in order: the registration time, coverage (fewer attempts than registered), one evaluator (a case's attempts graded
by different or unrecorded evaluator, oracle or case digests) and unknown quality (UNDECIDED); a
fallen regression case (DROP); the budget (DROP); a capability gain (PROMOTE at its stated cost); a fallen capability case
(DROP); then, at equal quality, each efficiency metric in turn on the cards that are evidence for it (build step 8:
minutes need valid timing and attribution; cost, turns and tokens need valid attribution and a total that is not a lower
bound, so a resumed attempt's own cost counts): no case dearer beyond the tolerance and one cheaper beyond it is PROMOTE,
one dearer beyond it is DROP, and otherwise the next metric is asked; none deciding is UNDECIDED. Refusals and Improve
children are diagnostics on the card, never a metric here (R4).

An attempt's quality is known only when its card's correctness is valid (``scorecard/6`` validity) and each required floor
is ``pass`` or ``fail``: an ``unobserved`` or ``not_applicable`` required floor, or correctness that is false or not
observed, leaves its case's quality unknown. So a run that overlapped others is still quality evidence, never speed
evidence (SPEC "The promotion contract", build step 2). Every attempt of a case, in both arms, must carry the same
``boundary`` digests (``scorecard/6``): a harness or oracle change is an experiment of its own (build step 3).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import boundary  # noqa: E402  (boundary.GROUPS: the grading digests)
import metrics  # noqa: E402  (metrics.span: the one span reader)
import scorecard  # noqa: E402  (the cards the contract reads)

CONTRACT_ID = "promotion/4"
ROLES = ("regression", "capability")
FLOORS = ("accuracy", "enterprise", "fidelity")
DEFAULT_FLOORS = ("accuracy", "fidelity")  # enterprise is not_applicable until its rubric exists, so it cannot be required
METRICS = ("cost_usd", "minutes", "turns", "tokens", "output_tokens")  # a card's efficiency targets; the rest are diagnostics
SUMMED = ("cost_usd", "turns", "tokens", "output_tokens")  # added over the run's sessions: a lower bound when one never reported
EXIT = {"PROMOTE": 0, "DROP": 3, "UNDECIDED": 4}


def load_registration(path: Path) -> dict:
    """The registration, checked; a registration that cannot be used is refused with its reason."""
    try:
        raw = path.read_bytes()
        reg = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"the registration {path} cannot be read: {exc}") from None
    if not isinstance(reg, dict) or reg.get("contract") != CONTRACT_ID:
        raise SystemExit(f"the registration names contract {reg.get('contract') if isinstance(reg, dict) else None!r}, "
                         f"not {CONTRACT_ID!r}")
    cases = reg.get("cases")
    if not isinstance(cases, dict) or not cases:
        raise SystemExit("the registration names no cases")
    for name, entry in list(cases.items()):
        entry = {"role": entry} if isinstance(entry, str) else entry
        attempts = entry.get("attempts", 1) if isinstance(entry, dict) else None
        if not isinstance(entry, dict) or entry.get("role") not in ROLES or not isinstance(attempts, int) or attempts < 1:
            raise SystemExit(f"the registration's case {name!r} needs a role ({', '.join(ROLES)}) and attempts of at least 1")
        cases[name] = {"role": entry["role"], "attempts": attempts}
    floors = reg.setdefault("floors", list(DEFAULT_FLOORS))
    if not floors or any(floor not in FLOORS for floor in floors):
        raise SystemExit(f"the registration's floors must be a non-empty subset of {', '.join(FLOORS)}")
    efficiency = reg.setdefault("efficiency", ["cost_usd", "minutes"])
    if not efficiency or any(name not in METRICS for name in efficiency):
        raise SystemExit(f"the registration's efficiency metrics must come from {', '.join(METRICS)}")
    for name in ("quality_tolerance", "tolerance"):
        if not isinstance(reg.setdefault(name, 0.0 if name == "quality_tolerance" else 0.10), (int, float)) or reg[name] < 0:
            raise SystemExit(f"the registration's {name} must be a number of at least 0")
    if any(name not in METRICS for name in reg.setdefault("budget", {})):
        raise SystemExit(f"the registration's budget keys must come from {', '.join(METRICS)}")
    reg["sha256"] = hashlib.sha256(raw).hexdigest()[:12]
    return reg


def arm(paths) -> list[tuple[dict, float | None]]:
    """(card, run start) for every attempt of an arm: run folders are scored here, card files are read as they are (their
    start is unknown, so the registration time is not checked for them)."""
    attempts = []
    for path in map(Path, paths):
        if path.is_file():
            data = json.loads(path.read_text())
            attempts += [(card, None) for card in (data.get("cards") if isinstance(data, dict) else data) or []]
            continue
        for folder in scorecard.run_folders([path]):
            attempts.append((scorecard.score(folder), metrics.span(folder / "timeline.jsonl")["started"]))
    return attempts


def succeeded(card: dict, floors) -> bool | None:
    """Whether an attempt met every required floor: None when its card was not observed, its correctness is not valid, or a
    required floor is neither pass nor fail."""
    if not card.get("observed") or ((card.get("validity") or {}).get("correctness") or {}).get("valid") is not True:
        return None
    values = [(card.get("floors") or {}).get(floor) for floor in floors]
    return None if any(value not in ("pass", "fail") for value in values) else all(value == "pass" for value in values)


def comparable(card: dict, metric: str) -> bool:
    """Whether a card is evidence for ``metric`` (SPEC build step 8): minutes need its timing and attribution valid; a
    summed metric needs its attribution valid and a total that is not a lower bound, so a resumed or overlapped attempt's
    own tokens and dollars count, and a total that may miss a session that never reported never does."""
    validity = card.get("validity") or {}
    if (validity.get("attribution") or {}).get("valid") is not True:
        return False
    if metric in SUMMED:
        return (card.get("efficiency") or {}).get("totals_lower_bound") is False
    return (validity.get("timing") or {}).get("valid") is True


def per_success(cards: list[dict], metric: str, successes: int) -> float | None:
    """All-attempt cost per successful case: the metric summed over every attempt, divided by the successes. None when an
    attempt is not evidence for the metric (``comparable``) or did not measure it."""
    values = [(card.get("efficiency") or {}).get(metric) for card in cards]
    if (successes == 0 or not all(comparable(card, metric) for card in cards)
            or any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in values)):
        return None
    return sum(values) / successes


def decide(reg: dict, control, candidate) -> dict:
    """The decision: {contract, decision, reasons, cases, registration}. ``control`` and ``candidate`` are lists of (card,
    run start)."""
    report = {"contract": CONTRACT_ID, "registration": reg["sha256"], "decision": "UNDECIDED", "reasons": [], "cases": {},
              "notes": []}

    def finish(decision: str, *reasons: str) -> dict:
        report["decision"], report["reasons"] = decision, list(reasons)
        return report

    registered = reg.get("registered_at")
    starts = [start for _, start in [*control, *candidate] if start is not None]
    if registered is None:
        report["notes"].append("the registration carries no registered_at, so it was not checked against the runs' starts")
    elif any(start < registered for start in starts):
        return finish("UNDECIDED", "the registration was written after a run it judges began")
    if any(start is None for _, start in [*control, *candidate]):
        report["notes"].append("card files carry no run start; the registration time was checked for run folders only")
    arms = {"control": control, "candidate": candidate}
    by_case = {name: {side: [card for card, _ in attempts if card.get("case") == name] for side, attempts in arms.items()}
               for name in reg["cases"]}
    missing = [f"{name} ({side}: {len(cards)} of {reg['cases'][name]['attempts']})" for name, sides in by_case.items()
               for side, cards in sides.items() if len(cards) < reg["cases"][name]["attempts"]]
    if missing:
        return finish("UNDECIDED", "fewer attempts than registered for " + ", ".join(missing))
    graders = {name: {tuple((card.get("boundary") or {}).get(group) for group in boundary.GROUPS)
                      for cards in sides.values() for card in cards} for name, sides in by_case.items()}
    unrecorded = [name for name, seen in graders.items() if any(None in digests for digests in seen)]
    if unrecorded:
        return finish("UNDECIDED", "no grading digest (evaluator, oracle, case) is recorded on every attempt of "
                      + ", ".join(unrecorded))
    mixed = [name for name, seen in graders.items() if len(seen) > 1]
    if mixed:
        return finish("UNDECIDED", "attempts were graded by different evaluator, oracle or case digests for " + ", ".join(mixed)
                      + ": a harness or oracle change is an experiment of its own")
    unknown, shares = [], {}
    for name, sides in by_case.items():
        row = report["cases"][name] = {"role": reg["cases"][name]["role"]}
        for side, cards in sides.items():
            outcomes = [succeeded(card, reg["floors"]) for card in cards]
            if any(outcome is None for outcome in outcomes):
                unknown.append(f"{name} ({side})")
            successes = sum(1 for outcome in outcomes if outcome)
            row[side] = {"attempts": len(cards), "successes": successes, "share": round(successes / len(cards), 4)}
        shares[name] = row["candidate"]["share"] - row["control"]["share"]
    if unknown:
        return finish("UNDECIDED", "quality is unknown (correctness not valid, or a required floor unobserved) for "
                      + ", ".join(unknown))
    tol = reg["quality_tolerance"]
    regressions = [name for name, delta in shares.items() if reg["cases"][name]["role"] == "regression" and delta < -tol]
    if regressions:
        return finish("DROP", "an established requirement fell: " + ", ".join(regressions))
    for metric, limit in reg["budget"].items():
        over = [name for name, sides in by_case.items()
                if (cost := per_success(sides["candidate"], metric, report["cases"][name]["candidate"]["successes"])) is not None
                and cost > limit]
        if over:
            return finish("DROP", f"over the registered budget of {limit} {metric} per success: " + ", ".join(over))
    for name, sides in by_case.items():
        report["cases"][name]["cost_per_success"] = {
            metric: {side: per_success(cards, metric, report["cases"][name][side]["successes"]) for side, cards in sides.items()}
            for metric in reg["efficiency"]}
    gains = [name for name, delta in shares.items() if reg["cases"][name]["role"] == "capability" and delta > tol]
    if gains:
        return finish("PROMOTE", "quality rose on " + ", ".join(gains) + "; its cost per success is in cases")
    falls = [name for name, delta in shares.items() if delta < -tol]
    if falls:
        return finish("DROP", "quality fell on " + ", ".join(falls) + " with no gain elsewhere")
    for metric in reg["efficiency"]:
        changes, unmeasured, not_evidence = {}, [], []
        for name, sides in by_case.items():
            pair = report["cases"][name]["cost_per_success"][metric]
            if not all(comparable(card, metric) for cards in sides.values() for card in cards):
                not_evidence.append(name)
            elif pair["control"] is None or pair["candidate"] is None:
                unmeasured.append(name)
            elif pair["control"] > 0:
                changes[name] = (pair["candidate"] - pair["control"]) / pair["control"]
        if not_evidence:
            report["notes"].append(f"{metric} per success is not evidence for " + ", ".join(not_evidence) + (
                ": a total that may miss a session that never reported, or attribution not valid" if metric in SUMMED
                else ": timing or attribution not valid"))
        if unmeasured or not_evidence or not changes:
            if unmeasured or not not_evidence:
                report["notes"].append(f"{metric} per success is not measured for " + (", ".join(unmeasured) or "any case"))
            continue
        dearer = [name for name, change in changes.items() if change > reg["tolerance"]]
        cheaper = [name for name, change in changes.items() if change < -reg["tolerance"]]
        if dearer:
            return finish("DROP", f"equal quality, and {metric} per success is higher beyond the tolerance on " + ", ".join(dearer))
        if cheaper:
            return finish("PROMOTE", f"equal quality, and {metric} per success is lower beyond the tolerance on " + ", ".join(cheaper))
        report["notes"].append(f"{metric} per success changed within the tolerance")
    return finish("UNDECIDED", "equal quality, and no efficiency metric moved beyond the tolerance: an inconclusive optimisation")


def render(report: dict) -> str:
    lines = [f"{report['contract']} (registration {report['registration']}): {report['decision']}",
             *(f"  because {reason}" for reason in report["reasons"])]
    for name, row in report["cases"].items():
        if "control" in row:
            lines.append(f"  {name:<22} {row['role']:<10} control {row['control']['successes']}/{row['control']['attempts']}"
                         f"  candidate {row['candidate']['successes']}/{row['candidate']['attempts']}")
    lines += [f"  note: {note}" for note in report["notes"]]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--control", nargs="+", required=True, help="run folders or card files of the control arm")
    parser.add_argument("--candidate", nargs="+", required=True, help="run folders or card files of the candidate arm")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = decide(load_registration(args.registration), arm(args.control), arm(args.candidate))
    print(json.dumps(report, indent=1) if args.json else render(report), end="\n" if args.json else "")
    return EXIT[report["decision"]]


if __name__ == "__main__":
    sys.exit(main())
