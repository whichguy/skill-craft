#!/usr/bin/env python3
"""A fake subject for the closed-loop tests, with its adapter in one file.

The subject is a program with three planted defects, each exposed only by cases of one style (d1 by A1, d2 by B1 and B2, d3 by C1),
so a campaign must widen from style alpha to beta before it can find d2, and C1 is a hosted case that only the owner may release.
A scripted improver fixes the first unfixed defect a sweep or iteration found. Everything is deterministic and stdlib-only.

Verbs follow the closed-loop-adapter/1 protocol (skills/closed-loop/references/adapter-schema.md). `CLOSED_LOOP_WORKSPACE` names
the subject's working directory, where it keeps subject-state.json; `fake-config.json` there lets a test change behaviour between
calls:

  scoring            scoring identity token (default "score-1"); changing it makes earlier evidence stale
  poll_delay         polls before a started step reports done (default 0: done at once)
  invalid_review_at  iteration numbers whose review is invalid
  extra_records      records added to `records` (for example a deferred material record)
  outcome            the improver's candidate outcome (default PROMOTE; anything else leaves the defect unfixed)
  no_acceptance      true: a promoted candidate carries no acceptance evidence
  baseline           {case: "comparable"|"none"|"unknown"} (default comparable)
  consumed           what each step reports consuming (default {"seconds": 10, "turns": 5})
  sensitive, calibrated, bounded   probe answers
  catalog, defects   replace the case catalog and the defect map (for dimension and combination tests)
  omit_cases         requested cases the iteration leaves out of its results
  extra_cases        cases the iteration reports although nobody requested them
  iteration_overrides  {field: value} written over the iteration report, to make it malformed
  case_overrides     {case: {field: value}} written over a case result
  regress            {"case": id, "from_version": n}: that case misses its floors once the subject is at version n or later
  fail_poll          {"error": text, "consumed": {...}}: every poll answers failed, with what the failed step cost
  hang               {verb: seconds}: that verb sleeps before answering (to test the execution timeout)
  crash              {verb: true}: that verb exits non-zero without answering
  crash_step         ["poll", ...]: those `step` subcommands exit non-zero without answering
  crash_probe        [claim, ...]: those probes exit non-zero without answering
  probe_no_evidence  true: every probe answers its state without evidence
  probe_consumed     what every probe reports consuming
  cleanup_unverified true: the owned cleanup answers verified false

Queries never write inside the workspace: the tests run them as exit checks, and a check that changed the workspace tree would
invalidate its own recorded run.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import time

WORKSPACE = Path(os.environ.get("CLOSED_LOOP_WORKSPACE", "."))
STATE = WORKSPACE / "subject-state.json"
CONFIG = WORKSPACE / "fake-config.json"
STEPS = WORKSPACE / "fake-steps"
STARTS = WORKSPACE / "fake-starts.log"
HISTORY = WORKSPACE / "fake-history.json"
CLEANUPS = WORKSPACE / "fake-cleanups.log"

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


def catalog() -> list:
    return config().get("catalog", CATALOG)


def defects() -> dict:
    return config().get("defects", DEFECTS)


def flags(argv: list) -> dict:
    return {argv[i][2:]: argv[i + 1] for i in range(0, len(argv) - 1, 2) if argv[i].startswith("--")}


def emit(obj: dict) -> None:
    print(json.dumps(obj))


def floors_met(case: str, st: dict, cfg: dict, unfixed: list) -> bool:
    regress = cfg.get("regress")
    if regress and regress["case"] == case and st["version"] >= regress["from_version"]:
        return False
    return not unfixed


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
    requested = given["cases"].split(",")
    for case in requested + cfg.get("extra_cases", []):
        unfixed = [d for d, exposed in defects().items() if case in exposed and d not in st["fixed"]]
        results[case] = {"ran": True, "floors_met": floors_met(case, st, cfg, unfixed),
                         "baseline": cfg.get("baseline", {}).get(case, "comparable")}
        results[case].update(cfg.get("case_overrides", {}).get(case, {}))
        for defect in unfixed:
            discoveries.append({"id": f"D-{defect}", "material": True, "repeat": defect in st["known"]})
            if defect not in st["known"]:
                st["known"].append(defect)
            found.append(defect)
    for case in cfg.get("omit_cases", []):
        results.pop(case, None)
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
    iteration.update(cfg.get("iteration_overrides", {}))
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
    failing = config().get("fail_poll")
    if failing:
        emit({"status": "failed", "error": failing["error"], "iteration": {"consumed": failing.get("consumed", {})}})
        return
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
    out = [{"id": f"R-{d}", "title": f"defect {d}", "material": True, "target": "subject", "cases": defects()[d],
            "status": "verified" if d in st["fixed"] else "open",
            "evidence": f"{d} fixed and checked" if d in st["fixed"] else None} for d in sorted(st["known"])]
    return {"records": out + config().get("extra_records", [])}


def probe(claim: str) -> dict:
    kind, _, name = claim.partition(":")
    cfg = config()
    if claim in cfg.get("crash_probe", []):
        raise SystemExit(f"the fake adapter crashed probing {claim}")
    extra = {"consumed": cfg["probe_consumed"]} if cfg.get("probe_consumed") else {}
    if kind == "cases.runs":
        return {"state": "runs", "evidence": f"{name or 'a case'} ran at {state()['version']} and cleaned up", **extra}
    if kind == "grading.scores":
        return {"state": "scores", "evidence": "evaluate returned floors for a real run", **extra}
    if kind == "grading.sensitive":
        hit = cfg.get("sensitive", {}).get(name)
        return {"state": "sensitive" if hit else "unknown", **extra,
                "evidence": "a seeded defect was caught" if hit else "no probe"}
    if kind == "grading.calibrated":
        hit = cfg.get("calibrated", {}).get(name)
        return {"state": "calibrated" if hit else "unmeasured", "evidence": "an A/A report" if hit else None, **extra}
    if kind == "improver.bounded":
        ok = cfg.get("bounded", True)
        return {"state": "bounded" if ok else "declared", "evidence": "an out-of-bounds edit was caught" if ok else None, **extra}
    if kind == "improver.invocable":
        return {"state": "invocable", "evidence": "a trivial in-bounds change landed on a throwaway branch", **extra}
    raise SystemExit(f"unknown claim {claim}")


def cleanup(argv: list) -> dict:
    if config().get("cleanup_unverified"):
        return {"verified": False}
    keys = flags(argv).get("keys", "")
    with open(CLEANUPS, "a") as log:
        log.write(keys + "\n")
    return {"verified": True, "receipt": "cleanup-" + hashlib.sha256(keys.encode()).hexdigest()[:8]}


def main(argv: list) -> int:
    verb = argv[1]
    pause = config().get("hang", {}).get(verb, 0)
    if pause:
        time.sleep(pause)
    if config().get("crash", {}).get(verb):
        raise SystemExit(f"the fake adapter crashed in {verb}")
    if verb == "cases":
        emit({"cases": catalog()})
    elif verb == "identity":
        emit({"scoring": config().get("scoring", "score-1"), "build": f"b{state()['version']}"})
    elif verb == "records":
        emit(records())
    elif verb == "probe":
        answer = probe(argv[2])
        if config().get("probe_no_evidence"):
            answer["evidence"] = None
        emit(answer)
    elif verb == "step":
        if argv[2] in config().get("crash_step", []):
            raise SystemExit(f"the fake adapter crashed in step {argv[2]}")
        {"start": start, "poll": poll, "cancel": cancel}[argv[2]](argv[3:])
    elif verb == "cleanup":
        emit(cleanup(argv[2:]))
    else:
        raise SystemExit(f"unknown verb {verb}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
