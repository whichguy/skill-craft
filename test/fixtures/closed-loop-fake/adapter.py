#!/usr/bin/env python3
"""A fake subject for the closed-loop tests, with its adapter in one file.

The subject is a program with three planted defects, each exposed only by cases of one style (d1 by A1, d2 by B1 and B2, d3 by C1),
so a campaign must widen from style alpha to beta before it can find d2, and C1 is a hosted case that only the owner may release.
A scripted improver fixes the first unfixed defect a sweep or iteration found. Everything is deterministic and stdlib-only.

Verbs follow the closed-loop-adapter/1 protocol (skills/closed-loop/references/adapter-schema.md). `CLOSED_LOOP_WORKSPACE` names the
subject's working directory, where it keeps subject-state.json; `fake-config.json` there lets a test change behaviour between calls:

  scoring            scoring identity token (default "score-1"); changing it makes earlier evidence stale
  poll_delay         polls before a started step reports done (default 0: done at once)
  invalid_review_at  iteration numbers whose review is invalid
  extra_records      records added to `records` (for example a deferred material record)
  outcome            the improver's candidate outcome (default PROMOTE; anything else leaves the defect unfixed)
  no_acceptance      true: a promoted candidate carries no acceptance evidence
  baseline           {case: "comparable"|"none"|"unknown"} (default comparable)
  consumed           what each step reports consuming (default {"seconds": 10, "turns": 5})
  sensitive, calibrated, bounded   probe answers

Queries never write inside the workspace: the tests run them as exit checks, and a check that changed the workspace tree would
invalidate its own recorded run.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys

WORKSPACE = Path(os.environ.get("CLOSED_LOOP_WORKSPACE", "."))
STATE = WORKSPACE / "subject-state.json"
CONFIG = WORKSPACE / "fake-config.json"
STEPS = WORKSPACE / "fake-steps"
STARTS = WORKSPACE / "fake-starts.log"
HISTORY = WORKSPACE / "fake-history.json"

CATALOG = [
    {"id": "A1", "dimensions": {"style": "alpha"}, "cost": 1, "requires": [], "hosted": False},
    {"id": "B1", "dimensions": {"style": "beta"}, "cost": 2, "requires": [], "hosted": False},
    {"id": "B2", "dimensions": {"style": "beta"}, "cost": 5, "requires": [], "hosted": False},
    {"id": "C1", "dimensions": {"style": "gamma"}, "cost": 3, "requires": ["hosted"], "hosted": True},
]
DEFECTS = {"d1": ["A1"], "d2": ["B1", "B2"], "d3": ["C1"]}


def load(path: Path, default):
    return json.loads(path.read_text()) if path.is_file() else default


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def state() -> dict:
    return load(STATE, {"version": 0, "fixed": [], "known": []})


def config() -> dict:
    return load(CONFIG, {})


def flags(argv: list) -> dict:
    return {argv[i][2:]: argv[i + 1] for i in range(0, len(argv) - 1, 2) if argv[i].startswith("--")}


def emit(obj: dict) -> None:
    print(json.dumps(obj))


def start(argv: list) -> None:
    given = flags(argv)
    handle = "h-" + hashlib.sha256(given["key"].encode()).hexdigest()[:8]
    step_file = STEPS / f"{handle}.json"
    if step_file.is_file():  # idempotent on the key: the same handle, and nothing is launched again
        known = load(step_file, {})
        emit({"handle": handle, "status": "running" if known["polls_left"] > 0 else "done",
              **({"iteration": known["iteration"]} if known["polls_left"] == 0 else {})})
        return
    with open(STARTS, "a") as log:
        log.write(given["key"] + "\n")
    st, cfg = state(), config()
    history = load(HISTORY, [])
    number = len(history) + 1
    before = f"b{st['version']}"
    review_valid = number not in cfg.get("invalid_review_at", [])
    results, discoveries, found = {}, [], []
    for case in given["cases"].split(","):
        unfixed = [d for d, exposed in DEFECTS.items() if case in exposed and d not in st["fixed"]]
        results[case] = {"ran": True, "floors_met": not unfixed, "baseline": cfg.get("baseline", {}).get(case, "comparable")}
        for defect in unfixed:
            discoveries.append({"id": f"D-{defect}", "material": True, "repeat": defect in st["known"]})
            if defect not in st["known"]:
                st["known"].append(defect)
            found.append(defect)
    candidate = acceptance = None
    if given["mode"] == "iterate" and review_valid and found:
        defect = min(set(found))
        outcome = cfg.get("outcome", "PROMOTE")
        candidate = {"id": f"C-{defect}", "hash": f"h-{defect}-b{st['version'] + 1}", "outcome": outcome}
        if outcome == "PROMOTE":
            st["fixed"].append(defect)
            st["version"] += 1
            if not cfg.get("no_acceptance"):
                acceptance = {"candidate": candidate["hash"], "evidence": f"{defect} checked in b{st['version']}"}
    after = f"b{st['version']}"
    iteration = {
        "build_before": before, "build_after": after, "scoring": cfg.get("scoring", "score-1"), "cases": results,
        "review": {"valid": review_valid, "complete": review_valid}, "judge": {"valid": True, "complete": True},
        "discoveries": discoveries if review_valid else [], "candidate": candidate,
        "invalid": [] if review_valid else ["review invalid"],
        "cleanup": {"verified": True, "receipt": f"cleanup-{given['key']}"}, "tier": {"green": True, "build": after},
        "acceptance": acceptance, "consumed": cfg.get("consumed", {"seconds": 10, "turns": 5})}
    save(STATE, st)
    history.append(given["key"])
    save(HISTORY, history)
    STEPS.mkdir(exist_ok=True)
    delay = cfg.get("poll_delay", 0)
    save(step_file, {"key": given["key"], "polls_left": delay, "iteration": iteration})
    emit({"handle": handle, "status": "running" if delay > 0 else "done", **({"iteration": iteration} if delay == 0 else {})})


def poll(argv: list) -> None:
    given = flags(argv)
    step_file = STEPS / f"{given['handle']}.json"
    known = load(step_file, None)
    if known is None:
        emit({"status": "failed", "error": "no such step"})
        return
    if known.get("cancelled"):
        emit({"status": "cancelled"})
        return
    if known["polls_left"] > 0:
        known["polls_left"] -= 1
        save(step_file, known)
    emit({"status": "running"} if known["polls_left"] > 0 else {"status": "done", "iteration": known["iteration"]})


def cancel(argv: list) -> None:
    given = flags(argv)
    step_file = STEPS / f"{given['handle']}.json"
    known = load(step_file, {})
    known["cancelled"] = True
    save(step_file, known)
    emit({"status": "cancelled"})


def records() -> dict:
    st = state()
    out = [{"id": f"R-{d}", "title": f"defect {d}", "material": True, "target": "subject", "cases": DEFECTS[d],
            "status": "verified" if d in st["fixed"] else "open",
            "evidence": f"{d} fixed and checked" if d in st["fixed"] else None} for d in sorted(st["known"])]
    return {"records": out + config().get("extra_records", [])}


def probe(claim: str) -> dict:
    kind, _, name = claim.partition(":")
    cfg = config()
    if kind == "cases.runs":
        return {"state": "runs", "evidence": f"{name or 'a case'} ran at {state()['version']} and cleaned up"}
    if kind == "grading.scores":
        return {"state": "scores", "evidence": "evaluate returned floors for a real run"}
    if kind == "grading.sensitive":
        hit = cfg.get("sensitive", {}).get(name)
        return {"state": "sensitive" if hit else "unknown", "evidence": "a seeded defect was caught" if hit else "no probe"}
    if kind == "grading.calibrated":
        hit = cfg.get("calibrated", {}).get(name)
        return {"state": "calibrated" if hit else "unmeasured", "evidence": "an A/A report" if hit else None}
    if kind == "improver.bounded":
        ok = cfg.get("bounded", True)
        return {"state": "bounded" if ok else "declared", "evidence": "an out-of-bounds edit was caught" if ok else None}
    if kind == "improver.invocable":
        return {"state": "invocable", "evidence": "a trivial in-bounds change landed on a throwaway branch"}
    raise SystemExit(f"unknown claim {claim}")


def main(argv: list) -> int:
    verb = argv[1]
    if verb == "cases":
        emit({"cases": CATALOG})
    elif verb == "identity":
        emit({"scoring": config().get("scoring", "score-1"), "build": f"b{state()['version']}"})
    elif verb == "records":
        emit(records())
    elif verb == "probe":
        emit(probe(argv[2]))
    elif verb == "step":
        {"start": start, "poll": poll, "cancel": cancel}[argv[2]](argv[3:])
    elif verb == "cleanup":
        emit({"verified": True})
    else:
        raise SystemExit(f"unknown verb {verb}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
