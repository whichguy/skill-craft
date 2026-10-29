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
STRICT_CONTRACT_ID = "promotion/5"
ROLES = ("regression", "capability")
FLOORS = ("accuracy", "enterprise", "fidelity")
DEFAULT_FLOORS = ("accuracy", "fidelity")  # enterprise is not_applicable until its rubric exists, so it cannot be required
METRICS = ("cost_usd", "minutes", "turns", "tokens", "output_tokens")  # a card's efficiency targets; the rest are diagnostics
SUMMED = ("cost_usd", "turns", "tokens", "output_tokens")  # added over the run's sessions: a lower bound when one never reported
EXIT = {"PROMOTE": 0, "DROP": 3, "UNDECIDED": 4}
PURPOSES = ("product_change", "calibration", "model_only")
STRICT_DEFAULT_EFFICIENCY = ("tokens", "minutes")


def _strict_json(raw: bytes):
    """Parse strict JSON without duplicate keys or non-standard NaN/Infinity values."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    def bad_constant(value):
        raise ValueError(f"invalid JSON number {value}")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)


def _finite_number(value, *, minimum=0) -> bool:
    import math
    try:
        return (isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
                and value >= minimum)
    except (OverflowError, ValueError):
        return False


def _strict_run_records(run: Path) -> str | None:
    """Validate the exact JSON and JSONL records covered by a strict run receipt."""
    for name in ("result.json", "metrics.json", "invocation.json"):
        try:
            value = _strict_json((run / name).read_bytes())
        except (OSError, ValueError) as error:
            return f"{name} is unreadable or malformed: {error}"
        if not isinstance(value, dict):
            return f"{name} must contain a JSON object"
    try:
        lines = (run / "timeline.jsonl").read_text().splitlines()
    except OSError as error:
        return f"timeline.jsonl is unreadable: {error}"
    seen = set()
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            item = _strict_json(line.encode("utf-8"))
        except (UnicodeError, ValueError) as error:
            return f"timeline.jsonl line {number} is malformed: {error}"
        if (not isinstance(item, dict) or not isinstance(item.get("line"), int) or isinstance(item.get("line"), bool)
                or not _finite_number(item.get("t"))):
            return f"timeline.jsonl line {number} needs a unique integer line and finite timestamp"
        if item["line"] in seen:
            return f"timeline.jsonl line number {item['line']} is duplicated"
        seen.add(item["line"])
    return None


def _valid_build(value) -> bool:
    return (isinstance(value, str) and len(value) in (12, 40, 64)
            and all(char in "0123456789abcdef" for char in value))


def _strict_registration(raw: dict, data: bytes) -> dict:
    """Validate promotion/5's immutable comparison plan; /4 remains the historical diagnostic contract."""
    if not isinstance(raw, dict) or raw.get("contract") != STRICT_CONTRACT_ID:
        raise SystemExit(f"the registration does not name {STRICT_CONTRACT_ID!r}")
    reg = dict(raw)
    if not _finite_number(reg.get("registered_at"), minimum=0):
        raise SystemExit("promotion/5 needs a finite registered_at epoch timestamp")
    if reg.get("purpose") not in PURPOSES:
        raise SystemExit("promotion/5 purpose must be product_change, calibration, or model_only")
    cases = reg.get("cases")
    if not isinstance(cases, dict) or not cases:
        raise SystemExit("promotion/5 names no cases")
    normalized = {}
    for name, entry in cases.items():
        if (not isinstance(name, str) or not name or not isinstance(entry, dict) or set(entry) != {"role", "attempts"}
                or entry.get("role") not in ROLES or not isinstance(entry.get("attempts"), int)
                or isinstance(entry.get("attempts"), bool) or entry["attempts"] < 1):
            raise SystemExit(f"promotion/5 case {name!r} needs a role and positive integer attempts")
        normalized[name] = {"role": entry["role"], "attempts": entry["attempts"]}
    reg["cases"] = normalized
    floors = reg.get("floors")
    if (not isinstance(floors, list) or not floors
            or any(not isinstance(floor, str) or floor not in FLOORS for floor in floors)
            or len(floors) != len(set(floors))):
        raise SystemExit("promotion/5 floors must be a non-empty list without duplicates from " + ", ".join(FLOORS))
    efficiency = reg.get("efficiency", list(STRICT_DEFAULT_EFFICIENCY))
    if (not isinstance(efficiency, list) or not efficiency
            or any(not isinstance(metric, str) or metric not in METRICS for metric in efficiency)
            or len(efficiency) != len(set(efficiency))):
        raise SystemExit("promotion/5 efficiency must be an ordered, non-empty list without duplicates from " + ", ".join(METRICS))
    reg["efficiency"] = list(efficiency)
    hard_floors = reg.get("hard_floors", [])
    if (not isinstance(hard_floors, list)
            or any(not isinstance(floor, str) or floor not in floors for floor in hard_floors)
            or len(hard_floors) != len(set(hard_floors))):
        raise SystemExit("promotion/5 hard_floors must be a unique list drawn from required floors")
    reg["hard_floors"] = list(hard_floors)
    for name in ("quality_tolerance", "tolerance"):
        if not _finite_number(reg.get(name)):
            raise SystemExit(f"promotion/5 {name} must be a finite non-negative number")
    budget = reg.get("budget")
    if not isinstance(budget, dict) or any(not isinstance(name, str) or name not in METRICS for name in budget):
        raise SystemExit("promotion/5 budget must be an object keyed by registered metrics")
    if any(not _finite_number(value) for value in budget.values()):
        raise SystemExit("promotion/5 budget values must be finite non-negative numbers")
    for field in ("qualification", "arms"):
        if not isinstance(reg.get(field), dict):
            raise SystemExit(f"promotion/5 needs a {field} object")
    qualification = reg["qualification"]
    if qualification.get("contract") != boundary.QUALIFICATION_CONTRACT or qualification.get("scorecard") != scorecard.SCORECARD_ID:
        raise SystemExit("promotion/5 needs a supported frozen qualification snapshot and scorecard/6")
    snapshot_cases = qualification.get("cases")
    if not isinstance(snapshot_cases, dict) or set(snapshot_cases) != set(normalized):
        raise SystemExit("promotion/5 frozen case definitions must cover exactly the registered cases")
    suites = qualification.get("suites")
    files = qualification.get("files")
    if (not isinstance(suites, dict) or not isinstance(files, dict) or not files
            or any(not isinstance(name, str) or not isinstance(digest, str) or len(digest) != 64
                   or any(char not in "0123456789abcdef" for char in digest) for name, digest in files.items())):
        raise SystemExit("promotion/5 frozen qualification files, suites, or digests are malformed")
    for case, frozen_case in snapshot_cases.items():
        if not isinstance(frozen_case, dict):
            raise SystemExit(f"promotion/5 frozen case {case!r} is malformed")
        if scorecard.requires_acceptance(case, frozen_case) is None:
            raise SystemExit(f"promotion/5 frozen case {case!r} has unknown acceptance requiredness")
    arms = reg["arms"]
    if set(arms) != {"control", "candidate"}:
        raise SystemExit("promotion/5 arms must name exactly control and candidate")
    for name, arm_spec in arms.items():
        if not isinstance(arm_spec, dict) or not _valid_build(arm_spec.get("shiploop_build")):
            raise SystemExit(f"promotion/5 {name} arm needs a ShipLoop build digest")
        driver = arm_spec.get("driver")
        if (not isinstance(driver, dict) or set(driver) != {"host", "model", "effort"}
                or any(not isinstance(driver.get(key), str) or not driver[key].strip()
                       for key in ("host", "model", "effort"))):
            raise SystemExit(f"promotion/5 {name} arm needs exact host, model, and effort driver bindings")
        if "product" in arm_spec and (not isinstance(arm_spec["product"], str) or not arm_spec["product"].strip()):
            raise SystemExit(f"promotion/5 optional {name} product pin must be a non-empty string")
    control, candidate = arms["control"], arms["candidate"]
    same_build = control["shiploop_build"] == candidate["shiploop_build"]
    control_driver, candidate_driver = control["driver"], candidate["driver"]
    if reg["purpose"] == "product_change" and (same_build or control_driver != candidate_driver):
        raise SystemExit("product_change needs different ShipLoop builds and the same host/model/effort driver")
    if reg["purpose"] == "calibration" and (not same_build or control_driver != candidate_driver):
        raise SystemExit("calibration requires the same ShipLoop build and host/model/effort driver")
    if reg["purpose"] == "model_only" and (not same_build or
            control_driver["model"] == candidate_driver["model"] or
            any(control_driver[key] != candidate_driver[key] for key in ("host", "effort"))):
        raise SystemExit("model_only requires the same ShipLoop build and host/effort, with a different model")
    attempts = reg.get("attempts")
    if not isinstance(attempts, list) or not attempts:
        raise SystemExit("promotion/5 needs a pre-registered attempts list")
    ids, counts = set(), {(arm_name, case): 0 for arm_name in ("control", "candidate") for case in normalized}
    for attempt in attempts:
        if (not isinstance(attempt, dict) or set(attempt) != {"id", "arm", "case"}
                or not isinstance(attempt.get("id"), str) or not attempt["id"].strip()
                or attempt.get("arm") not in ("control", "candidate") or attempt.get("case") not in normalized):
            raise SystemExit("each promotion/5 attempt needs exactly a non-empty id, arm, and registered case")
        if attempt["id"] in ids:
            raise SystemExit(f"promotion/5 attempt id {attempt['id']!r} is duplicated")
        ids.add(attempt["id"])
        counts[(attempt["arm"], attempt["case"])] += 1
    wrong = [f"{arm_name}/{case}: {count} of {normalized[case]['attempts']}" for (arm_name, case), count in counts.items()
             if count != normalized[case]["attempts"]]
    if wrong:
        raise SystemExit("promotion/5 attempts must exactly cover every registered case in each arm: " + ", ".join(wrong))
    try:
        expected = boundary.qualification_snapshot(Path(__file__).resolve().parent, normalized)
        changes = boundary.qualification_changes(qualification, Path(__file__).resolve().parent, normalized)
    except (OSError, ValueError) as error:
        raise SystemExit(f"promotion/5 frozen qualification inputs cannot be read: {error}") from None
    if changes:
        raise SystemExit("promotion/5 frozen qualification inputs do not match the current evaluator and catalogs")
    if qualification.get("sha256") != expected["sha256"]:
        raise SystemExit("promotion/5 qualification snapshot digest does not match its frozen contents")
    reg["sha256"] = hashlib.sha256(data).hexdigest()
    payload = {key: value for key, value in reg.items() if key not in ("sha256", "payload_sha256")}
    reg["payload_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()
    return reg


def load_registration(path: Path) -> dict:
    """The registration, checked; a registration that cannot be used is refused with its reason."""
    try:
        raw = path.read_bytes()
        reg = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"the registration {path} cannot be read: {exc}") from None
    if isinstance(reg, dict) and reg.get("contract") == STRICT_CONTRACT_ID:
        try:
            reg = _strict_json(raw)
        except ValueError as exc:
            raise SystemExit(f"the registration {path} cannot be read: {exc}") from None
        return _strict_registration(reg, raw)
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


def arm(paths, reg: dict | None = None) -> list[tuple[dict, float | None]]:
    """(card, run start) for every attempt of an arm: run folders are scored here, card files are read as they are (their
    start is unknown, so the registration time is not checked for them)."""
    if isinstance(reg, dict) and reg.get("contract") == STRICT_CONTRACT_ID:
        attempts = []
        frozen_cases = ((reg.get("qualification") or {}).get("cases") or {})
        for path in map(Path, paths):
            if path.is_file():
                raise SystemExit("promotion/5 cannot use card files; run-folder starts and sealed receipts are required")
            folders = scorecard.run_folders([path])
            for folder in folders:
                try:
                    result = _strict_json((folder / "result.json").read_bytes())
                except (OSError, ValueError) as error:
                    raise SystemExit(f"promotion/5 run result {folder} cannot be read: {error}") from None
                case = result.get("case") if isinstance(result, dict) else None
                card = scorecard.score(folder, required_case=frozen_cases.get(case))
                attempts.append((card, card.get("started")))
        return attempts
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


def _decide_legacy(reg: dict, control, candidate) -> dict:
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


def _attempt_id(card: dict):
    return card.get("attempt_id")


def _strict_outcome(card: dict, floors: list[str]) -> tuple[bool | None, list[str]]:
    """An observed required floor failure stays visible beside unrelated unknown requiredness."""
    floor_values = card.get("floors") if isinstance(card.get("floors"), dict) else {}
    failures = [floor for floor in floors if floor_values.get(floor) == "fail"]
    validity = card.get("validity") if isinstance(card.get("validity"), dict) else {}
    correctness_record = validity.get("correctness") if isinstance(validity.get("correctness"), dict) else {}
    correctness = correctness_record.get("valid")
    if correctness is not True:
        return None, failures
    if failures:
        return False, failures
    if any(floor_values.get(floor) != "pass" for floor in floors):
        return None, []
    return True, []


def _strict_comparable(card: dict, metric: str) -> bool:
    validity = card.get("validity") if isinstance(card.get("validity"), dict) else {}
    attribution = validity.get("attribution") if isinstance(validity.get("attribution"), dict) else {}
    timing = validity.get("timing") if isinstance(validity.get("timing"), dict) else {}
    if attribution.get("valid") is not True:
        return False
    if metric == "minutes":
        return timing.get("valid") is True
    efficiency = card.get("efficiency") if isinstance(card.get("efficiency"), dict) else {}
    return efficiency.get("totals_lower_bound") is False


def _strict_per_success(cards: list[dict], metric: str, successes: int) -> tuple[float | None, str | None]:
    if successes <= 0:
        return None, "no successful case to divide the all-attempt total by"
    values = []
    for card in cards:
        if not _strict_comparable(card, metric):
            return None, "attribution, timing, or complete-total evidence is not valid"
        efficiency = card.get("efficiency")
        value = efficiency.get(metric) if isinstance(efficiency, dict) else None
        if not _finite_number(value):
            return None, f"{metric} is missing, malformed, negative, boolean, or non-finite"
        values.append(value)
    return sum(values) / successes, None


def _strict_product_valid(card: dict) -> tuple[bool, str | None]:
    product = card.get("delivery_product")
    if not isinstance(product, dict) or product.get("observed") is not True:
        return False, "the delivery before/after product identity is not recorded"
    if (not isinstance(product.get("head"), str) or not product["head"]
            or not isinstance(product.get("tree"), str) or not product["tree"]):
        return False, "the delivered product identity has no head or tree"
    if product.get("unchanged_during_checks") is not True or product.get("head") != product.get("after_head") \
            or product.get("tree") != product.get("after_tree"):
        return False, "the delivered product identity changed while checks ran"
    return True, None


def _strict_decide(reg: dict, control, candidate, harness_root: Path | None = None) -> dict:
    """promotion/5: qualification is bound to frozen inputs, explicit arms, and unique sealed run attempts."""
    root = Path(harness_root or Path(__file__).resolve().parent)
    report = {"contract": STRICT_CONTRACT_ID, "registration": reg.get("sha256"), "purpose": reg.get("purpose"),
              "decision": "UNDECIDED", "reasons": [], "cases": {}, "attempts": [], "known_floor_failures": [],
              "hard_floor_failures": [], "unknown_floor_evidence": [], "notes": [],
              "global_errors": [], "evidence_issues": [],
              "qualification": {"claim": reg.get("purpose"), "scorecard": scorecard.SCORECARD_ID}}

    def finish(decision: str, *reasons: str) -> dict:
        if reg.get("purpose") == "calibration":
            report["diagnostic_decision"], report["diagnostic_reasons"] = decision, list(reasons)
            report["decision"] = "UNDECIDED"
            report["reasons"] = ["calibration is diagnostic and cannot qualify a ShipLoop product change"]
        else:
            report["decision"], report["reasons"] = decision, list(reasons)
            if reg.get("purpose") == "model_only":
                report["notes"].append("model-only result; it does not qualify a ShipLoop code change")
        return report

    def add_global_error(message: str) -> None:
        if message not in report["global_errors"]:
            report["global_errors"].append(message)

    def add_evidence_error(row: dict | None, message: str) -> None:
        if row is not None:
            row["evidence_valid"] = False
            if message not in row["evidence_errors"]:
                row["evidence_errors"].append(message)
        item = {"id": row.get("id") if row else None, "arm": row.get("arm") if row else None,
                "case": row.get("case") if row else None, "reason": message}
        if item not in report["evidence_issues"]:
            report["evidence_issues"].append(item)

    def undecided(*reasons: str) -> dict:
        all_reasons = list(report["global_errors"])
        all_reasons.extend(item["reason"] for item in report["evidence_issues"])
        all_reasons.extend(reasons)
        return finish("UNDECIDED", *dict.fromkeys(all_reasons))

    # Revalidate the loaded manifest object in case a controller mutated it after registration was read.
    try:
        clean = {key: value for key, value in reg.items() if key not in ("sha256", "payload_sha256")}
        checked = _strict_registration(clean, json.dumps(clean, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False, allow_nan=False).encode("utf-8"))
        if (checked.get("payload_sha256") != reg.get("payload_sha256")
                or not isinstance(reg.get("sha256"), str) or len(reg["sha256"]) != 64):
            raise ValueError("the frozen registration payload digest is missing or changed")
    except (SystemExit, TypeError, ValueError) as error:
        add_global_error(f"the promotion/5 registration is no longer valid: {error}")
        return undecided()
    cases = reg.get("cases") if isinstance(reg.get("cases"), dict) else {}
    changes = boundary.qualification_changes(reg.get("qualification"), root, cases)
    if changes:
        add_global_error("frozen qualification inputs changed or are unavailable: " + ", ".join(changes))
    report["qualification"]["snapshot"] = (reg.get("qualification") or {}).get("sha256")
    arms = reg.get("arms") if isinstance(reg.get("arms"), dict) else {}
    same_build = ((arms.get("control") or {}).get("shiploop_build")
                  == (arms.get("candidate") or {}).get("shiploop_build"))
    report["qualification"]["attribution"] = ("calibration" if reg.get("purpose") == "calibration" else
                                               "model-only" if reg.get("purpose") == "model_only" else
                                               "ShipLoop build change" if not same_build else "unattributed A/A")
    expected = {entry.get("id"): entry for entry in reg.get("attempts", []) if isinstance(entry, dict)}
    if len(expected) != len(reg.get("attempts", [])):
        add_global_error("the registered attempts list contains duplicate or malformed IDs")
    actual_by_case = {name: {"control": [], "candidate": []} for name in cases}
    all_rows = [("control", control), ("candidate", candidate)]

    # Find duplicates before evaluating individual receipts so every copy of a reused ID, path, or start is invalid.
    counts = {"id": {}, "path": {}, "start": {}}
    for side, attempts in all_rows:
        for item in attempts or []:
            if not isinstance(item, (tuple, list)) or len(item) != 2 or not isinstance(item[0], dict):
                continue
            card, start = item
            attempt_id = card.get("attempt_id")
            run_path = card.get("run")
            if isinstance(attempt_id, str) and attempt_id.strip():
                counts["id"][attempt_id] = counts["id"].get(attempt_id, 0) + 1
            if isinstance(run_path, str) and run_path.strip():
                canonical_path = str(Path(run_path).resolve())
                counts["path"][canonical_path] = counts["path"].get(canonical_path, 0) + 1
            if _finite_number(start, minimum=0):
                counts["start"][start] = counts["start"].get(start, 0) + 1

    seen_ids = {attempt_id for attempt_id in counts["id"]}
    case_issues: dict[str, list[str]] = {name: [] for name in cases}
    for side, attempts in all_rows:
        for item in attempts or []:
            if not isinstance(item, (tuple, list)) or len(item) != 2 or not isinstance(item[0], dict):
                add_evidence_error(None, f"{side} has a malformed attempt receipt; strict attempts are (card, start) pairs")
                continue
            card, start = item
            attempt_id = _attempt_id(card)
            case = card.get("case")
            attempt = expected.get(attempt_id)
            run_path = card.get("run")
            row = {"id": attempt_id, "arm": side, "case": case, "started": start,
                   "product": card.get("delivery_product"), "scorecard": card.get("scorecard"),
                   "evidence_valid": True, "evidence_errors": []}
            report["attempts"].append(row)
            if not isinstance(attempt_id, str) or not attempt_id.strip():
                add_evidence_error(row, f"{side}/{case}: attempt ID is missing")
            elif counts["id"].get(attempt_id, 0) > 1:
                add_evidence_error(row, f"attempt ID {attempt_id!r} is duplicated")
            if attempt is None:
                add_evidence_error(row, f"{side}/{case}: attempt ID {attempt_id!r} was not pre-registered")
            elif attempt.get("arm") != side or attempt.get("case") != case:
                add_evidence_error(row, f"attempt {attempt_id!r} arrived in the wrong arm or case")
            if not isinstance(case, str) or case not in cases:
                add_evidence_error(row, f"{side}: attempt {attempt_id!r} names an unregistered case")
                continue
            if not isinstance(run_path, str) or not run_path.strip():
                add_evidence_error(row, f"{attempt_id}: strict qualification needs a unique run-folder path")
            else:
                canonical_path = str(Path(run_path).resolve())
                if counts["path"].get(canonical_path, 0) > 1:
                    add_evidence_error(row, f"run path {canonical_path!r} is duplicated")
                frozen_case = ((reg.get("qualification") or {}).get("cases") or {}).get(case)
                invalid_records = _strict_run_records(Path(run_path))
                if invalid_records:
                    fresh = None
                    add_evidence_error(row, f"{attempt_id}: {invalid_records}")
                else:
                    try:
                        fresh = scorecard.score(Path(run_path), required_case=frozen_case)
                    except (OSError, ValueError, TypeError, AttributeError, KeyError) as error:
                        fresh = None
                        add_evidence_error(row, f"{attempt_id}: run folder cannot be rescored: {error}")
                if not isinstance(fresh, dict):
                    add_evidence_error(row, f"{attempt_id}: run folder did not produce a scorecard/6 card")
                else:
                    fresh_receipt = fresh.get("run_receipt")
                    if not isinstance(fresh_receipt, dict):
                        add_evidence_error(row, f"{attempt_id}: run folder produced no sealed evidence receipt")
                    else:
                        required_files = set(scorecard.RUN_RECEIPT_FILES)
                        receipt_files = fresh_receipt.get("files") if isinstance(fresh_receipt.get("files"), dict) else {}
                        missing_files = sorted(set(fresh_receipt.get("missing") or [])
                                                | (required_files - set(receipt_files)))
                        if missing_files:
                            add_evidence_error(row, f"{attempt_id}: sealed run receipt is incomplete: " + ", ".join(missing_files))
                        if fresh_receipt.get("observed") is not True or fresh_receipt.get("unsafe_symlinks"):
                            add_evidence_error(row, f"{attempt_id}: sealed run receipt has unsafe or unobserved evidence")
                        product_receipt = fresh_receipt.get("product")
                        if not isinstance(product_receipt, dict) or product_receipt.get("observed") is not True:
                            add_evidence_error(row, f"{attempt_id}: live work-tree fingerprint is not observed")
                        if (not isinstance(fresh_receipt.get("sha256"), str) or len(fresh_receipt["sha256"]) != 64
                                or card.get("run_receipt") != fresh_receipt):
                            add_evidence_error(row, f"{attempt_id}: sealed run receipt is missing or changed")
                    # The receipt also binds ambient overlap inputs. Derived diagnostics must agree with a fresh score;
                    # deleting a neighbour or changing the runs root cannot erase previously observed interference.
                    derived = ("attempt_id", "started", "run_receipt")
                    submitted_evidence = {key: value for key, value in card.items() if key not in derived}
                    fresh_evidence = {key: value for key, value in fresh.items() if key not in derived}
                    if submitted_evidence != fresh_evidence:
                        add_evidence_error(row, f"{attempt_id}: submitted card does not match a fresh score from its sealed run folder")
                    if card.get("started") != fresh.get("started"):
                        add_evidence_error(row, f"{attempt_id}: sealed card start does not match its run-folder timeline")
                    fresh["attempt_id"] = attempt_id
                    card = fresh
            if card.get("scorecard") != scorecard.SCORECARD_ID or card.get("observed") is not True:
                add_evidence_error(row, f"{attempt_id}: only observed scorecard/6 run-folder cards qualify")
            if not _finite_number(start, minimum=0):
                add_evidence_error(row, f"{attempt_id}: run start is missing, malformed, negative, or non-finite")
            else:
                if start < reg.get("registered_at", float("inf")):
                    add_evidence_error(row, f"{attempt_id}: the registration was written after the run began")
                if counts["start"].get(start, 0) > 1:
                    add_evidence_error(row, f"run start {start!r} is duplicated")
                if card.get("started") != start:
                    add_evidence_error(row, f"{attempt_id}: sealed card start does not match the run-folder start")
            arm_spec = arms.get(side) if isinstance(arms.get(side), dict) else {}
            grading_boundary = card.get("boundary") if isinstance(card.get("boundary"), dict) else {}
            if grading_boundary.get("candidate") != arm_spec.get("shiploop_build"):
                add_evidence_error(row, f"{attempt_id}: recorded ShipLoop build does not match the {side} arm binding")
            driver = card.get("driver") if isinstance(card.get("driver"), dict) else {}
            expected_driver = arm_spec.get("driver") if isinstance(arm_spec.get("driver"), dict) else {}
            if any(driver.get(key) != expected_driver.get(key) for key in ("host", "model", "effort")):
                add_evidence_error(row, f"{attempt_id}: recorded host/model/effort does not match the {side} arm binding")
            product_ok, product_why = _strict_product_valid(card)
            if not product_ok:
                add_evidence_error(row, f"{attempt_id}: {product_why}")
            # Parent controllers may keep a fixed product hash as an extra diagnostic constraint, but stochastic products
            # generated during a valid E2E attempt are otherwise identified independently from the ShipLoop build.
            pinned_product = arm_spec.get("product")
            product = card.get("delivery_product") if isinstance(card.get("delivery_product"), dict) else {}
            if pinned_product is not None and product.get("tree") != pinned_product:
                add_evidence_error(row, f"{attempt_id}: delivered product does not match the optional {side} product pin")
            actual_by_case[case][side].append((card, row))
            outcome, floor_failures = _strict_outcome(card, reg.get("floors", []))
            raw_outcome = "success" if outcome is True else "failure" if outcome is False else "unknown"
            row["reported_outcome"] = raw_outcome
            row["outcome"] = raw_outcome if row["evidence_valid"] else "unknown"
            row["hard_floor_failures"] = floor_failures
            floor_values = card.get("floors") if isinstance(card.get("floors"), dict) else {}
            unknown_floors = [floor for floor in reg.get("floors", []) if floor_values.get(floor) not in ("pass", "fail")]
            row["unknown_floors"] = unknown_floors
            if unknown_floors:
                report["unknown_floor_evidence"].append({"id": attempt_id, "arm": side, "case": case,
                                                         "floors": unknown_floors})
            if floor_failures:
                report["known_floor_failures"].append({"id": attempt_id, "arm": side, "case": case,
                                                        "floors": floor_failures,
                                                        "evidence_valid": row["evidence_valid"]})
                correctness = ((card.get("validity") if isinstance(card.get("validity"), dict) else {})
                               .get("correctness") or {})
                if (row["evidence_valid"] and correctness.get("valid") is True
                        and any(floor in reg.get("hard_floors", []) for floor in floor_failures)):
                    hard = [floor for floor in floor_failures if floor in reg.get("hard_floors", [])]
                    report["hard_floor_failures"].append({"id": attempt_id, "arm": side, "case": case,
                                                           "floors": hard})
    missing_ids = sorted(set(expected) - seen_ids)
    if missing_ids:
        add_evidence_error(None, "registered attempts have no sealed run receipt: " + ", ".join(missing_ids))
    extra_ids = sorted(seen_ids - set(expected))
    if extra_ids:
        add_evidence_error(None, "run receipts include unregistered attempt IDs: " + ", ".join(extra_ids))
    for name, sides in actual_by_case.items():
        digests = []
        for entries in sides.values():
            for card, _row in entries:
                grading = card.get("boundary") if isinstance(card.get("boundary"), dict) else {}
                values = tuple(grading.get(group) for group in boundary.GROUPS)
                if any(not isinstance(value, str) or not value for value in values):
                    case_issues[name].append(f"{name}: every attempt needs recorded evaluator, oracle, and case digests")
                else:
                    digests.append(values)
        if len(set(digests)) > 1:
            case_issues[name].append(f"{name}: attempts were graded by different evaluator, oracle, or case digests")
        for issue in dict.fromkeys(case_issues[name]):
            add_evidence_error(None, issue)
            for entries in sides.values():
                for _card, row in entries:
                    add_evidence_error(row, issue)

    unknown_quality, deltas = [], {}
    for name, case_spec in cases.items():
        row = report["cases"][name] = {"role": case_spec["role"]}
        sides = actual_by_case.get(name, {"control": [], "candidate": []})
        for side, entries in sides.items():
            cards = [card for card, _attempt_row in entries]
            outcomes = [_strict_outcome(card, reg["floors"])[0] if attempt_row["evidence_valid"] else None
                        for card, attempt_row in entries]
            known_successes = sum(outcome is True for outcome in outcomes)
            unknown = sum(outcome is None for outcome in outcomes)
            expected_ids = {entry["id"] for entry in reg["attempts"]
                            if entry["arm"] == side and entry["case"] == name}
            valid_ids = [attempt_row["id"] for _card, attempt_row in entries
                         if attempt_row["evidence_valid"] and attempt_row["id"] in expected_ids]
            complete = (len(cards) == case_spec["attempts"] and len(valid_ids) == case_spec["attempts"]
                        and set(valid_ids) == expected_ids and unknown == 0)
            row[side] = {"attempts": len(cards), "registered_attempts": case_spec["attempts"],
                         "successes": known_successes, "unknown": unknown,
                         "share": round(known_successes / len(cards), 4) if cards and complete else None}
            if not complete:
                unknown_quality.append(f"{name} ({side})")
        if row["control"]["share"] is not None and row["candidate"]["share"] is not None:
            deltas[name] = row["candidate"]["share"] - row["control"]["share"]
    if report["known_floor_failures"] and report["unknown_floor_evidence"]:
        report["notes"].append("known floor failures remain listed beside other unknown required-floor evidence")

    # A known established regression is decisive even if an unrelated case is unknown. Keep all known failures in the
    # report and test the protected cases before applying the general unknown-evidence gate.
    tolerance = reg.get("quality_tolerance", 0.0)
    regressions = [name for name, delta in deltas.items()
                   if cases[name]["role"] == "regression" and delta < -tolerance]
    if report["global_errors"]:
        return undecided()
    if regressions:
        return finish("DROP", "an established requirement fell: " + ", ".join(regressions))
    candidate_hard_failures = [item for item in report["hard_floor_failures"] if item["arm"] == "candidate"]
    if candidate_hard_failures:
        labels = [f"{item['case']} ({', '.join(item['floors'])})" for item in candidate_hard_failures]
        return finish("DROP", "a registered hard floor failed: " + ", ".join(labels))
    if unknown_quality:
        return undecided("required quality evidence is unknown for " + ", ".join(unknown_quality))

    budget_unknown = []
    over_budget = []
    for name, sides in actual_by_case.items():
        row = report["cases"][name]
        row["cost_per_success"] = {}
        for metric in dict.fromkeys([*reg["efficiency"], *reg["budget"]]):
            row["cost_per_success"][metric] = {}
            for side, entries in sides.items():
                cards = [card for card, _attempt_row in entries]
                value, why = _strict_per_success(cards, metric, row[side]["successes"])
                row["cost_per_success"][metric][side] = value
                if metric in reg["budget"] and side == "candidate":
                    if why:
                        budget_unknown.append(f"{name} ({why})")
                    elif value > reg["budget"][metric]:
                        over_budget.append(name)
            if metric in reg["budget"]:
                row.setdefault("budget", {})[metric] = {"limit": reg["budget"][metric],
                                                         "candidate": row["cost_per_success"][metric]["candidate"]}
    if over_budget:
        metric_names = sorted(reg["budget"])
        return finish("DROP", "over the registered budget(s) " + ", ".join(metric_names)
                      + " per success on " + ", ".join(sorted(set(over_budget))))
    if budget_unknown:
        return undecided("registered budget evidence is unknown for " + "; ".join(budget_unknown))

    gains = [name for name, delta in deltas.items() if cases[name]["role"] == "capability" and delta > tolerance]
    if gains:
        return finish("PROMOTE", "quality rose on " + ", ".join(gains) + "; measured budget evidence passed")
    falls = [name for name, delta in deltas.items() if delta < -tolerance]
    if falls:
        return finish("DROP", "quality fell on " + ", ".join(falls) + " with no gain elsewhere")

    for metric in reg["efficiency"]:
        changes_by_case, missing, no_evidence = {}, [], []
        for name, sides in actual_by_case.items():
            pair = report["cases"][name]["cost_per_success"].get(metric, {})
            if not all(_strict_comparable(card, metric) for entries in sides.values()
                       for card, _attempt_row in entries):
                no_evidence.append(name)
            elif pair.get("control") is None or pair.get("candidate") is None:
                missing.append(name)
            elif pair["control"] > 0:
                changes_by_case[name] = (pair["candidate"] - pair["control"]) / pair["control"]
        if no_evidence:
            report["notes"].append(f"{metric} is not comparable for " + ", ".join(no_evidence))
        if missing:
            report["notes"].append(f"{metric} is not measured for " + ", ".join(missing))
        if no_evidence or missing or not changes_by_case:
            continue
        dearer = [name for name, change in changes_by_case.items() if change > reg["tolerance"]]
        cheaper = [name for name, change in changes_by_case.items() if change < -reg["tolerance"]]
        if dearer:
            return finish("DROP", f"equal quality, and {metric} per success is higher beyond the tolerance on " + ", ".join(dearer))
        if cheaper:
            return finish("PROMOTE", f"equal quality, and {metric} per success is lower beyond the tolerance on " + ", ".join(cheaper))
        report["notes"].append(f"{metric} per success changed within the tolerance")
    return finish("UNDECIDED", "equal quality, and no efficiency metric moved beyond the tolerance: an inconclusive optimisation")


def decide(reg: dict, control, candidate, *, harness_root: Path | None = None) -> dict:
    """Use promotion/5 for strict qualification and retain promotion/4 for historical diagnostics."""
    if reg.get("contract") == STRICT_CONTRACT_ID:
        return _strict_decide(reg, control, candidate, harness_root)
    return _decide_legacy(reg, control, candidate)


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
    reg = load_registration(args.registration)
    report = decide(reg, arm(args.control, reg), arm(args.candidate, reg))
    print(json.dumps(report, indent=1) if args.json else render(report), end="\n" if args.json else "")
    return EXIT[report["decision"]]


if __name__ == "__main__":
    sys.exit(main())
