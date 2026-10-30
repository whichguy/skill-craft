#!/usr/bin/env python3
"""Predictions (SPEC mission clause, amended 2026-10-30): what a candidate is expected to change, bound to its epoch
before its first attempt runs (``epoch.py init --prediction``), and its verdict once the epoch has decided. The verdict
is recorded beside the promotion decision and never replaces it.

    {"contract": "prediction/1", "record": "LR-20261030-3f9a1c", "anchor": "S-14",
     "because": "one sentence: why this change should move this measure",
     "effects": [{"case": "ticket-escalation", "measure": "tokens", "direction": "down", "at_least": 0.15}],
     "guards":  [{"case": "*", "measure": "accuracy", "direction": "not_down"}]}

A measure is one of three kinds, each compared the way the rest of the harness compares it:
- an efficiency metric (``promotion.METRICS``): all-attempt cost per successful attempt, by promotion's own arithmetic,
  as a relative change;
- a floor (``promotion.FLOORS``): the share of attempts whose floor passed, as a change in that share;
- a diagnostic: a number on the ``scorecard/6`` card named by its dotted path (``efficiency.refusals``), as its mean
  over the attempts, relative to the control's (a control of 0 counts as 1, so 0 to 3 is +3.0).

"No worse" alone is not a prediction: every effect has a direction, ``up`` or ``down``, and an ``at_least``. An
efficiency effect smaller than the registration's ``tolerance`` is refused, because the epoch could not resolve it.

    python3 test/shiploop_e2e/prediction.py check PREDICTION.json --registration REG.json
    python3 test/shiploop_e2e/prediction.py verdict --epoch EPOCH_DIR
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import learning_records  # noqa: E402
import promotion  # noqa: E402

CONTRACT = "prediction/1"
VERDICT_CONTRACT = "prediction-verdict/1"
DIRECTIONS = ("up", "down")
GUARD_DIRECTIONS = ("not_up", "not_down")
VERDICTS = ("confirmed", "refuted", "no_effect", "unknown")
KEYS = ("contract", "record", "anchor", "because", "effects", "guards")
DIAGNOSTIC = re.compile(r"[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)+")


def kind(measure: str) -> str:
    if measure in promotion.METRICS:
        return "efficiency"
    if measure in promotion.FLOORS:
        return "floor"
    if isinstance(measure, str) and DIAGNOSTIC.fullmatch(measure):
        return "diagnostic"
    raise ValueError(f"measure {measure!r} is not an efficiency metric, a floor or a dotted scorecard path")


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate(prediction, registration: dict) -> dict:
    """The prediction, checked against the registration it is bound to; a ValueError names what is wrong."""
    if not isinstance(prediction, dict):
        raise ValueError("a prediction is a JSON object")
    unknown = set(prediction) - set(KEYS)
    if unknown:
        raise ValueError("unknown prediction keys: " + ", ".join(sorted(unknown)))
    if prediction.get("contract") != CONTRACT:
        raise ValueError(f"contract must be {CONTRACT}")
    if not learning_records.RECORD_ID.fullmatch(str(prediction.get("record"))):
        raise ValueError("record must be a learning-record id (LR-YYYYMMDD-xxxxxx)")
    for key in ("anchor", "because"):
        if not isinstance(prediction.get(key), str) or not prediction[key].strip():
            raise ValueError(f"{key} must be non-empty text")
    cases = set(registration.get("cases") or {})
    tolerance = registration.get("tolerance", 0.0)
    effects = prediction.get("effects")
    if not isinstance(effects, list) or not effects:
        raise ValueError('a prediction needs at least one effect with a direction ("no worse" alone is not one)')
    for index, effect in enumerate(effects):
        where = f"effects[{index}]"
        if not isinstance(effect, dict) or set(effect) != {"case", "measure", "direction", "at_least"}:
            raise ValueError(f"{where} needs exactly case, measure, direction and at_least")
        if effect["case"] not in cases:
            raise ValueError(f"{where}.case {effect['case']!r} is not a registered case")
        measured = kind(effect["measure"])
        if effect["direction"] not in DIRECTIONS:
            raise ValueError(f"{where}.direction must be up or down")
        if not _finite(effect["at_least"]) or effect["at_least"] <= 0:
            raise ValueError(f"{where}.at_least must be a positive number")
        if measured == "efficiency" and effect["at_least"] < tolerance:
            raise ValueError(f"{where}.at_least {effect['at_least']} is below the registered tolerance {tolerance}: "
                             "the epoch cannot resolve it")
    guards = prediction.get("guards", [])
    if not isinstance(guards, list):
        raise ValueError("guards must be a list")
    for index, guard in enumerate(guards):
        where = f"guards[{index}]"
        if not isinstance(guard, dict) or set(guard) != {"case", "measure", "direction"}:
            raise ValueError(f"{where} needs exactly case, measure and direction")
        if guard["case"] != "*" and guard["case"] not in cases:
            raise ValueError(f"{where}.case {guard['case']!r} is neither * nor a registered case")
        kind(guard["measure"])
        if guard["direction"] not in GUARD_DIRECTIONS:
            raise ValueError(f"{where}.direction must be not_up or not_down")
    return {key: prediction[key] for key in KEYS if key in prediction}


def _path(card: dict, dotted: str):
    value = card
    for part in dotted.split("."):
        value = value.get(part) if isinstance(value, dict) else None
    return value


def observe(cards: list[dict], measure: str, floors: list[str]) -> tuple[float | None, str | None]:
    """One arm's value of a measure over its attempts at one case, or None with the reason."""
    if not cards:
        return None, "no attempts"
    measured = kind(measure)
    if measured == "efficiency":
        successes = sum(1 for card in cards if promotion._strict_outcome(card, floors)[0] is True)
        return promotion._strict_per_success(cards, measure, successes)
    if measured == "floor":
        known = [(card.get("floors") or {}).get(measure) for card in cards]
        known = [value for value in known if value in ("pass", "fail")]
        if not known:
            return None, f"no attempt observed the {measure} floor"
        return known.count("pass") / len(known), None
    values = [_path(card, measure) for card in cards]
    numbers = [value for value in values if _finite(value)]
    if len(numbers) < len(values):
        return None, f"{len(values) - len(numbers)} attempt(s) do not record {measure}"
    return sum(numbers) / len(numbers), None


def change(measure: str, control: float, candidate: float) -> float:
    """A floor's change is in its share; any other measure's is relative to the control (a control of 0 counts as 1)."""
    if kind(measure) == "floor":
        return candidate - control
    return (candidate - control) / (abs(control) if control else 1.0)


def verdict(prediction: dict, registration: dict, control: list[dict], candidate: list[dict]) -> dict:
    """Each effect confirmed, refuted (moved the other way beyond the tolerance), no effect or unknown; each guard held,
    broken or unknown; and the prediction's overall verdict. Cards carry their ``case``."""
    floors = list(registration.get("floors") or promotion.DEFAULT_FLOORS)

    def tolerance(measure: str) -> float:
        return registration.get("quality_tolerance", 0.0) if kind(measure) == "floor" else registration.get("tolerance", 0.0)

    def compare(case: str, measure: str) -> dict:
        ctrl, why_ctrl = observe([c for c in control if c.get("case") == case], measure, floors)
        cand, why_cand = observe([c for c in candidate if c.get("case") == case], measure, floors)
        row = {"case": case, "measure": measure, "control": ctrl, "candidate": cand}
        if ctrl is None or cand is None:
            row["unknown"] = why_ctrl or why_cand
        else:
            row["change"] = round(change(measure, ctrl, cand), 4)
        return row

    effects = []
    for effect in prediction["effects"]:
        row = {**compare(effect["case"], effect["measure"]), "direction": effect["direction"],
               "at_least": effect["at_least"]}
        if "change" not in row:
            row["verdict"] = "unknown"
        else:
            moved = row["change"] * (1 if effect["direction"] == "up" else -1)
            row["verdict"] = ("confirmed" if moved >= effect["at_least"] else
                              "refuted" if moved < -tolerance(effect["measure"]) else "no_effect")
        effects.append(row)
    cases = sorted(registration.get("cases") or {})
    guards = []
    for guard in prediction.get("guards", []):
        for case in (cases if guard["case"] == "*" else [guard["case"]]):
            row = {**compare(case, guard["measure"]), "direction": guard["direction"]}
            if "change" not in row:
                row["held"] = None
            else:
                against = row["change"] * (1 if guard["direction"] == "not_up" else -1)
                row["held"] = against <= tolerance(guard["measure"])
            guards.append(row)
    found = [row["verdict"] for row in effects]
    if "refuted" in found or any(row["held"] is False for row in guards):
        overall = "refuted"
    elif "unknown" in found:
        overall = "unknown"
    elif all(value == "confirmed" for value in found):
        overall = "confirmed"
    else:
        overall = "no_effect"
    return {"contract": VERDICT_CONTRACT, "record": prediction["record"], "verdict": overall, "effects": effects,
            "guards": guards}


def outcome(decision: str, judged: dict, reasons: list[str] | None = None) -> dict:
    """What the learning record becomes, from the promotion decision and the prediction's verdict together."""
    found = judged["verdict"]
    why = "; ".join(reasons or [])
    if decision == "PROMOTE":
        if found == "confirmed":
            return {"outcome": "verified", "reason": "promoted, and the predicted effect was observed"}
        return {"outcome": "unexplained_gain", "reason": f"promoted, but the prediction was {found}: the gain is not "
                "yet explained", "reopen_when": "a new record explains the gain"}
    if decision == "DROP":
        if found == "confirmed":
            return {"outcome": "deferred", "reason": f"the predicted effect was observed, but the candidate was dropped: {why}",
                    "reopen_when": "a candidate keeps the effect without the regression"}
        if found == "refuted":
            return {"outcome": "refuted", "reason": f"dropped, and the prediction was refuted: {why}",
                    "reopen_when": "new evidence that the measure can move this way"}
        return {"outcome": "no_effect", "reason": f"dropped, and the prediction was {found}: {why}",
                "reopen_when": "new evidence that the change moves the measure"}
    return {"outcome": "admitted", "reason": f"undecided: {why or 'the comparison could not decide'}",
            "reopen_when": None}


def _epoch_cards(root: Path) -> tuple[dict, dict, list[dict], list[dict]]:
    import epoch
    import scorecard
    registration = epoch.registration(root)
    predicted = json.loads((root / "prediction.json").read_text())
    arms = {"control": [], "candidate": []}
    for attempt in registration["attempts"]:
        try:
            output, _ = epoch.sealed_run(root, attempt["id"])
        except (OSError, ValueError):
            continue
        card = scorecard.score(output, required_case=registration["qualification"]["cases"][attempt["case"]])
        card["case"] = attempt["case"]
        arms[attempt["arm"]].append(card)
    return registration, predicted, arms["control"], arms["candidate"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("check", "verdict"))
    parser.add_argument("prediction", nargs="?", type=Path)
    parser.add_argument("--registration", type=Path)
    parser.add_argument("--epoch", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            if args.prediction is None or args.registration is None:
                parser.error("check needs PREDICTION and --registration")
            print(json.dumps(validate(json.loads(args.prediction.read_text()),
                                      json.loads(args.registration.read_text())), indent=2))
        else:
            if args.epoch is None:
                parser.error("verdict needs --epoch")
            registration, predicted, control, candidate = _epoch_cards(args.epoch.resolve())
            print(json.dumps(verdict(predicted, registration, control, candidate), indent=2))
    except (OSError, ValueError) as error:
        print(f"prediction: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
