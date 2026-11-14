#!/usr/bin/env python3
"""scaling_table.py: the tables and the predictions for E11 (host wording) and E12 (the settle dial), from the exported evidence.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (README Amendment A7, journal entries E11 and E12). It reads
evidence/<trial>/ (score.json, ledger.jsonl, native.json, context.json, events.trimmed.jsonl through phases.py) and prints

  E12  per host and settle S (0 is the pilot): A0 and A3 whole runs, their ratio, the model's prediction registered in A7
       (A0 = pilot + 5 S, A3 = pilot + 2 S on Claude and Grok, + 3 S on Codex), the cost outside the work phase, model calls,
       validity, then P35 to P40 and the break-even S* read from a least-squares line through the A3 minus A0 whole-run difference
  E11  Grok: the N trials against the H trials (spawn, join, whole run, parent calls, correctness), then P30 to P34

  python3 scaling_table.py [--e11] [--e12]       (both by default)
  python3 scaling_table.py --json                 the E12 points as JSON (host, S, arm, whole run, calls, cost, tokens) for a chart
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import phases  # noqa: E402

EV = HERE / "evidence"
PILOT = {"claude": ("r1h-claude-a0", "r1h-claude-a3"), "grok": ("r1-grok-a0", "r1-grok-a3"), "codex": ("r1-codex-a0", "r1-codex-a3")}
WAVES = {"claude": 1, "grok": 1, "codex": 2}     # A3's rounds of independent tasks: Codex's three slots run T1 to T3, then T4
OUTSIDE = ("orient", "spawn", "start", "join", "integrate", "tail")


def cell(host: str, s: int, arm: str) -> str:
    if s == 0:
        return PILOT[host][0 if arm == "A0" else 1]
    return f"e12-{host}-s{s}-{arm.lower()}"


def have(name: str) -> bool:
    return (EV / name / "score.json").is_file()


def calls(name: str) -> int | None:
    path = EV / name / "context.json"
    if not path.is_file():
        return None
    return sum(t["calls"] for t in json.loads(path.read_text())["threads"].values())


def load(name: str) -> dict:
    sc = json.loads((EV / name / "score.json").read_text())
    ph = phases.split(name)
    return {"name": name, "score": sc, "phases": ph, "calls": calls(name), "whole": ph["whole"], "valid": sc.get("valid"),
            "outside": sum(ph[k] for k in OUTSIDE), "work": ph["work"], "cost": (sc.get("tokens") or {}).get("cost_usd"),
            "tokens": (sc.get("tokens") or {}).get("input_all"), "refused": sc.get("refused"), "settled_all": sc.get("settled_all")}


def fit_break_even(points: list) -> float | None:
    """Least-squares line through (S, whole A3 minus whole A0); S where it crosses zero, or None when it never falls."""
    n = len(points)
    if n < 2:
        return None
    mx, my = sum(x for x, _ in points) / n, sum(y for _, y in points) / n
    sxx = sum((x - mx) ** 2 for x, _ in points)
    if sxx == 0:
        return None
    slope = sum((x - mx) * (y - my) for x, y in points) / sxx
    intercept = my - slope * mx
    return -intercept / slope if slope < 0 else None


def e12() -> None:
    rows, valid_all, total = {}, True, 0
    print("E12: the settle dial (S seconds of verification inside every task; S = 0 is the pilot)\n")
    print(f"{'host':<7}{'S':>4}{'A0 whole':>10}{'A3 whole':>10}{'ratio':>7}{'model A0':>10}{'model A3':>10}{'model ratio':>12}{'outside work A3-A0':>20}{'calls A0 / A3':>16}  valid A0 / A3")
    for host in PILOT:
        base = {arm: load(cell(host, 0, arm)) for arm in ("A0", "A3")}
        for s in (0, 30, 90):
            if not (have(cell(host, s, "A0")) and have(cell(host, s, "A3"))):
                continue
            a0, a3 = (base["A0"], base["A3"]) if s == 0 else (load(cell(host, s, "A0")), load(cell(host, s, "A3")))
            m0, m3 = base["A0"]["whole"] + 5 * s, base["A3"]["whole"] + (1 + WAVES[host]) * s
            rows[(host, s)] = {"a0": a0, "a3": a3, "model": (m0, m3)}
            valid_all = valid_all and bool(a0["valid"]) and bool(a3["valid"]) if s else valid_all
            total += 2 if s else 0
            print(f"{host:<7}{s:>4}{a0['whole']:>10.1f}{a3['whole']:>10.1f}{a3['whole'] / a0['whole']:>7.2f}{m0:>10.1f}{m3:>10.1f}{m3 / m0:>12.2f}"
                  f"{a3['outside'] - a0['outside']:>20.1f}{str(a0['calls']) + ' / ' + str(a3['calls']):>16}  {a0['valid']} / {a3['valid']}")
    print()
    for host in PILOT:
        pts = [(s, rows[(host, s)]["a3"]["whole"] - rows[(host, s)]["a0"]["whole"]) for s in (0, 30, 90) if (host, s) in rows]
        star = fit_break_even(pts)
        print(f"{host}: A3 minus A0 whole run over S {[p[0] for p in pts]}: {[round(p[1], 1) for p in pts]}"
              + (f"; break-even S* (least squares) = {star:.1f} s more per task than the pilot's" if star is not None else "; no break-even in range"))
    scored = [(h, s) for (h, s) in rows if s]
    if len(scored) < 6:
        print(f"\n(only {len(scored)} of 6 host/S cells complete; predictions are not scored yet)")
        return
    p36 = {h: rows[(h, 30)]["a3"]["whole"] < rows[(h, 30)]["a0"]["whole"] for h in PILOT}
    p37 = {h: rows[(h, 90)]["a3"]["whole"] < rows[(h, 90)]["a0"]["whole"] for h in PILOT}
    p38 = {h: abs((rows[(h, 90)]["a3"]["outside"] - rows[(h, 90)]["a0"]["outside"]) - (rows[(h, 30)]["a3"]["outside"] - rows[(h, 30)]["a0"]["outside"])) for h in PILOT}
    ratio = {(h, s): rows[(h, s)]["a3"]["whole"] / rows[(h, s)]["a0"]["whole"] for (h, s) in rows}
    p39 = all(ratio[(h, 90)] < ratio[(h, 30)] for h in PILOT) and all(ratio[(h, 90)] < 0.6 for h in ("claude", "grok"))
    pilot_calls = {h: (load(PILOT[h][0])["calls"], load(PILOT[h][1])["calls"]) for h in PILOT}
    p40 = {h: all(abs(rows[(h, 90)][arm]["calls"] / pilot_calls[h][i] - 1) <= 0.25 for i, arm in enumerate(("a0", "a3"))) for h in PILOT}
    print("\nPredictions as registered (README A7):")
    print(f"  P35 all twelve valid (with every task settled): {valid_all} ({total} trials seen)")
    print(f"  P36 A3 below A0 at S = 30: {p36}")
    print(f"  P37 A3 below A0 at S = 90: {p37}")
    p38_shown = {h: round(v, 1) for h, v in p38.items()}
    ratio_shown = {f"{h} S={s}": round(v, 2) for (h, s), v in ratio.items()}
    print(f"  P38 cost outside the work phase within 15 s from S = 30 to S = 90: {all(v <= 15 for v in p38.values())} (changes in seconds {p38_shown})")
    print(f"  P39 ratio falls from S = 30 to S = 90 on every host and is below 0.6 on Claude and Grok at S = 90: {p39} (ratios {ratio_shown})")
    print(f"  P40 model calls at S = 90 within 25% of the pilot's: {p40} (pilot calls A0 / A3 {pilot_calls})")


def e11() -> None:
    names = {"N": ["r1-grok-a3", "e11-grok-n2"], "H": ["e11-grok-h1", "e11-grok-h2"]}
    avail = {v: [n for n in ns if have(n)] for v, ns in names.items()}
    if not avail["H"]:
        print("E11: no H trial exported yet")
        return
    print("E11: Grok, packet N against packet N plus the host binding H (S = 0)\n")
    print(f"{'trial':<16}{'spawn':>8}{'start':>8}{'work':>8}{'join':>8}{'whole':>8}{'parent calls':>14}{'refused':>9}{'valid':>7}")
    stats = {"N": [], "H": []}
    for v in ("N", "H"):
        for n in avail[v]:
            t = load(n)
            ctx = json.loads((EV / n / "context.json").read_text())["threads"] if (EV / n / "context.json").is_file() else {}
            pc = ctx.get("parent", {}).get("calls")
            stats[v].append({"spawn": t["phases"]["spawn"], "join": t["phases"]["join"], "whole": t["whole"], "valid": t["valid"], "refused": t["refused"]})
            print(f"{n + ' (' + v + ')':<16}{t['phases']['spawn']:>8.1f}{t['phases']['start']:>8.1f}{t['phases']['work']:>8.1f}{t['phases']['join']:>8.1f}{t['whole']:>8.1f}{str(pc):>14}{t['refused']!s:>9}{t['valid']!s:>7}")

    def mean(v, key):
        xs = [x[key] for x in stats[v]]
        return sum(xs) / len(xs) if xs else None
    if stats["N"] and stats["H"]:
        d_spawn, d_whole = mean("N", "spawn") - mean("H", "spawn"), mean("N", "whole") - mean("H", "whole")
        print(f"\nmeans: spawn N {mean('N', 'spawn'):.1f} s, H {mean('H', 'spawn'):.1f} s (H shorter by {d_spawn:.1f}); whole N {mean('N', 'whole'):.1f} s, H {mean('H', 'whole'):.1f} s (H shorter by {d_whole:.1f})")
        print(f"  P30 H shortens the spawn phase by at least 8 s: {d_spawn >= 8}")
        print(f"  P31 every H trial valid with no refused attempt: {all(x['valid'] and not x['refused'] for x in stats['H'])}")
        print(f"  P32 H shortens the whole run by at least 8 s: {d_whole >= 8}")
    for host, key in (("claude", "P33"), ("codex", "P34")):
        h = f"e11-{host}-h1"
        if have(h):
            base = load(PILOT[host][1])
            t = load(h)
            print(f"  {key} ({host}): H whole {t['whole']:.1f} s against the pilot's N {base['whole']:.1f} s (difference {base['whole'] - t['whole']:+.1f} s)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--e11", action="store_true")
    parser.add_argument("--e12", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.json:
        out = []
        for host in PILOT:
            for s in (0, 30, 90):
                for arm in ("A0", "A3"):
                    if have(cell(host, s, arm)):
                        x = load(cell(host, s, arm))
                        out.append({"host": host, "S": s, "arm": arm, "whole_s": round(x["whole"], 1), "outside_work_s": round(x["outside"], 1), "calls": x["calls"],
                                    "cost_usd": x["cost"], "input_tokens": x["tokens"], "valid": x["valid"]})
        print(json.dumps(out))
        return 0
    both = not (args.e11 or args.e12)
    if args.e12 or both:
        e12()
    if args.e11 or both:
        print()
        e11()
    return 0


if __name__ == "__main__":
    sys.exit(main())
