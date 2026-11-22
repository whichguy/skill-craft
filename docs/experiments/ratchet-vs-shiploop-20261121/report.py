#!/usr/bin/env python3
"""The comparison's tables and the registered readings (journal section 5), from measure.py's records. No model.

    python3 report.py ROOT OUT_DIR [--judge JUDGE.json]

Reads ROOT/measure/*/measures.json, pairs the two arms of each case, applies readings R1 to R7 with the margins the
journal registered before any run, the overall rule, and scores predictions P1 to P8. Writes OUT_DIR/report.json (every
number and every reading) and OUT_DIR/report.md (the tables). JUDGE.json is judge.py's score file, for R7.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

CASE_ORDER = ("shared-expenses", "node-chess-engine", "ticket-assignment", "grokbot-local")
ARMS = ("shiploop", "ratchet")
NAMES = {"shiploop": "ShipLoop", "ratchet": "Ratchet"}


def get(row, *path, default=None):
    for key in path:
        if not isinstance(row, dict) or key not in row:
            return default
        row = row[key]
    return row


def held_out(point: dict) -> tuple[int | None, int | None]:
    rows = (point or {}).get("hidden") or {}
    if not rows or not all(row.get("observed") for row in rows.values()):
        return None, None
    return sum(row["passed"] for row in rows.values()), sum(row["of"] for row in rows.values())


def own_faults(point: dict) -> float | None:
    own = get(point, "mutation", "own")
    if not own or own.get("not_measured") and isinstance(own.get("not_measured"), str):
        return None
    return own.get("share")


def facts(record: dict) -> dict:
    final = get(record, "at", "final") or {}
    first = get(record, "at", "first-build") or {}
    passed, of = held_out(final)
    first_passed, first_of = held_out(first) if first else (None, None)
    coverage = get(final, "coverage", "own", "browser_free", "changed") or {}
    docs = get(final, "static", "docs", "user") or {}
    docs_all = get(final, "static", "docs", "all") or {}
    return {
        "label": record.get("label"),
        "minutes": get(record, "time", "minutes"),
        "first_build_minutes": get(record, "time", "first_build_minutes"),
        "stop": get(record, "time", "stop") or get(record, "time", "outcome"),
        "input": get(record, "tokens", "input"), "cached": get(record, "tokens", "cached"),
        "output": get(record, "tokens", "output"), "reasoning": get(record, "tokens", "reasoning"),
        "first_build_output": get(record, "tokens", "first_build", "output"),
        "held_out": passed, "held_out_of": of, "first_build_held_out": first_passed, "first_build_held_out_of": first_of,
        "held_out_failed": {kind: row.get("failed") for kind, row in (final.get("hidden") or {}).items()},
        "faults_own": own_faults(final),
        "faults_own_counts": get(final, "mutation", "own"),
        "faults_acceptance": get(final, "mutation", "acceptance", "share"),
        "faults_either": get(final, "mutation", "either", "share"),
        "calibrated": get(final, "calibrated", "caught"), "calibrated_pool": get(final, "calibrated", "pool"),
        "line_coverage": coverage.get("line_share"), "function_coverage": coverage.get("function_share"),
        "line_coverage_all_suites": get(final, "coverage", "all-suites", "browser_free", "changed", "line_share"),
        "coverage_left_out": get(final, "coverage", "own", "browser_free", "left_out"),
        "tests_run": get(final, "coverage", "own", "tests", "tests"),
        "tests_passed": get(final, "coverage", "own", "tests", "pass"),
        "docs_share": docs.get("share"), "docs_surfaces": docs.get("surfaces"), "docs_documented": docs.get("documented"),
        "docs_missing": docs.get("missing"), "docs_share_all": docs_all.get("share"),
        "user_words": get(final, "static", "docs", "user_words"), "process_words": get(final, "static", "docs", "process_words"),
        "comment_share": get(final, "static", "comments", "share"),
        "code": get(final, "static", "code") or {},
    }


def ahead_ratio(a, b):
    """'a', 'b' or None: the arm whose value is at most two thirds of the other's (lower is better)."""
    if a is None or b is None:
        return None
    if a <= b * 2 / 3:
        return "a"
    if b <= a * 2 / 3:
        return "b"
    return None


def ahead_margin(a, b, margin):
    """'a', 'b' or None: the arm higher by at least `margin` (higher is better)."""
    if a is None or b is None:
        return None
    if a - b >= margin:
        return "a"
    if b - a >= margin:
        return "b"
    return None


def readings(case: str, s: dict, r: dict, judge: dict | None) -> dict:
    to_arm = {"a": "shiploop", "b": "ratchet", None: None}
    out = {}
    out["R1 time"] = to_arm[ahead_ratio(s["minutes"], r["minutes"])]
    out_tokens = ahead_ratio(s["output"], r["output"]), ahead_ratio(s["input"], r["input"])
    out["R2 tokens"] = to_arm[out_tokens[0]] if out_tokens[0] == out_tokens[1] else None
    if s["held_out"] is not None and r["held_out"] is not None:
        checks = max(s["held_out_of"] or 0, r["held_out_of"] or 0)
        out["R3 breadth"] = to_arm[ahead_margin(s["held_out"], r["held_out"], max(2, math.ceil(0.1 * checks)))]
    else:
        out["R3 breadth"] = "not measured"
    a = ahead_margin(s["faults_own"], r["faults_own"], 0.10)
    depth = to_arm[a] if (s["faults_own"] is not None and r["faults_own"] is not None) else "not measured"
    if case == "ticket-assignment" and s["calibrated"] is not None and r["calibrated"] is not None:
        b = to_arm[ahead_margin(s["calibrated"], r["calibrated"], 3)]
        out["R4b calibrated defects"] = b
        if b and depth in ARMS and b != depth:
            depth = None
    out["R4 depth"] = depth
    if s["line_coverage"] is not None and r["line_coverage"] is not None:
        out["R5 coverage"] = to_arm[ahead_margin(s["line_coverage"], r["line_coverage"], 0.10)]
    else:
        out["R5 coverage"] = "not measured"
    if s["docs_share"] is not None and r["docs_share"] is not None:
        out["R6 documentation"] = to_arm[ahead_margin(s["docs_share"], r["docs_share"], 0.15)]
    else:
        out["R6 documentation"] = "not measured"
    if judge is None or case not in judge:
        out["R7 code quality"] = "not measured"
    else:
        out["R7 code quality"] = judge[case] if judge[case] in ARMS else None  # preferred in both orders, else no difference
    return out


QUALITY = ("R3 breadth", "R4 depth", "R5 coverage", "R6 documentation", "R7 code quality")


def overall(per_case: dict) -> dict:
    ahead = {arm: sum(1 for rows in per_case.values() for key in QUALITY if rows.get(key) == arm) for arm in ARMS}
    behind_breadth = {arm: [case for case, rows in per_case.items() if rows.get("R3 breadth") not in (arm, None, "not measured")]
                      for arm in ARMS}
    verdict = "no difference in results shown"
    for arm, other in (("shiploop", "ratchet"), ("ratchet", "shiploop")):
        if ahead[arm] - ahead[other] >= 3 and not behind_breadth[arm]:
            verdict = f"{NAMES[arm]} produces better results"
    return {"quality_cells_ahead": ahead, "behind_on_breadth": behind_breadth, "verdict": verdict}


def predictions(per_case: dict, result: dict) -> dict:
    cases = list(per_case.values())
    count = lambda key, value: sum(1 for rows in cases if rows.get(key) == value)
    none_or_split = lambda key: sum(1 for rows in cases if rows.get(key) is None)
    n = len(cases)
    return {
        "P1 ShipLoop ahead on time in 4 of 4": count("R1 time", "shiploop") == 4 == n,
        "P2 ShipLoop ahead on tokens in 4 of 4": count("R2 tokens", "shiploop") == 4 == n,
        "P3 breadth no difference in at least 3": none_or_split("R3 breadth") >= 3,
        "P4 ShipLoop ahead on depth (a) in at least 2": count("R4 depth", "shiploop") >= 2,
        "P5 coverage no difference in at least 3": none_or_split("R5 coverage") >= 3,
        "P6 documentation no difference in at least 3": none_or_split("R6 documentation") >= 3,
        "P7 judge split or absent in at least 3": none_or_split("R7 code quality") >= 3,
        "P8 overall no difference in results shown": result["verdict"] == "no difference in results shown",
    }


def fmt(value, kind="n"):
    if value is None:
        return "–"
    if kind == "pct":
        return f"{100 * value:.0f}%"
    if kind == "k":
        return f"{value / 1000:,.0f}k"
    if kind == "m":
        return f"{value / 1e6:.1f}M"
    return f"{value:,}" if isinstance(value, int) else str(value)


def markdown(rows: dict, per_case: dict, result: dict, scored: dict) -> str:
    lines = ["# Ratchet against ShipLoop: results", ""]
    header = "| Case | Arm | Minutes | Output tokens | Input tokens | Held-out checks | Faults caught by own tests | Line coverage (changed, Node) | Docs: new surfaces named | Tests run |"
    lines += [header, "|---" * (header.count("|") - 1) + "|"]
    for case in CASE_ORDER:
        for arm in ARMS:
            f = rows.get(case, {}).get(arm)
            if not f:
                continue
            minutes = fmt(f["minutes"]) + (f" (first build {fmt(f['first_build_minutes'])})" if f.get("first_build_minutes") else "")
            held = f"{fmt(f['held_out'])} of {fmt(f['held_out_of'])}" + (
                f" (first build {fmt(f['first_build_held_out'])})" if f.get("first_build_held_out") is not None and arm == "ratchet" else "")
            docs = f"{fmt(f['docs_documented'])} of {fmt(f['docs_surfaces'])}"
            lines.append(f"| {case} | {NAMES[arm]} | {minutes} | {fmt(f['output'], 'k')} | {fmt(f['input'], 'm')} | {held} | "
                         f"{fmt(f['faults_own'], 'pct')} | {fmt(f['line_coverage'], 'pct')} | {docs} | {fmt(f['tests_run'])} |")
    lines += ["", "## Readings (registered margins; a blank is no difference shown)", ""]
    keys = ("R1 time", "R2 tokens", *QUALITY)
    lines.append("| Case | " + " | ".join(keys) + " |")
    lines.append("|---|" + "---|" * len(keys))
    for case in CASE_ORDER:
        if case in per_case:
            cells = [NAMES.get(per_case[case].get(key), per_case[case].get(key)) or "" for key in keys]
            lines.append(f"| {case} | " + " | ".join(cells) + " |")
    summary = (f"**Overall:** {result['verdict']} (quality cells ahead: ShipLoop {result['quality_cells_ahead']['shiploop']}, "
               f"Ratchet {result['quality_cells_ahead']['ratchet']}).")
    lines += ["", summary, "", "## Predictions", ""]
    lines += [f"- {key}: {'right' if value else 'wrong'}" for key, value in scored.items()]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--judge", type=Path)
    args = parser.parse_args(argv)
    records = [json.loads(path.read_text()) for path in sorted((args.root / "measure").glob("*/measures.json"))]
    rows = {}
    for record in records:
        rows.setdefault(record["case"], {})[record["arm"]] = facts(record)
    judge = json.loads(args.judge.read_text()).get("verdicts") if args.judge else None
    per_case = {case: readings(case, pair["shiploop"], pair["ratchet"], judge) for case, pair in rows.items()
                if "shiploop" in pair and "ratchet" in pair}
    result = overall(per_case)
    scored = predictions(per_case, result) if len(per_case) == len(CASE_ORDER) else {}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps({"facts": rows, "readings": per_case, "overall": result,
                                                      "predictions": scored}, indent=1) + "\n")
    text = markdown(rows, per_case, result, scored)
    (args.out / "report.md").write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
