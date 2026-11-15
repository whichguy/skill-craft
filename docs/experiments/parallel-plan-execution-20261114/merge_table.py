#!/usr/bin/env python3
"""merge_table.py: the tables and the predictions for E13 (the write fixture), from the exported evidence.

Apparatus for docs/experiments/parallel-plan-execution-20261114 (README Amendment A10, journal entry E13). Reads evidence/e13-<host>-<cell>/
(score.json, ledger.jsonl, native.json, context.json, plan.json through phases.py). The cells, all at S = 30:

  w5-a0s   write5, one context does every task, shared checkout          (the control)
  w5-a3s   write5, fresh sub-agents, shared checkout                      (no isolation, no merge)
  w5-a3i   write5, fresh sub-agents, isolated worktrees, scripted merge   (isolation and merging)
  o5-a3s   overlap5 (W3 and W4 also register in an undeclared shared file), shared checkout
  o5-a3i   overlap5, isolated worktrees, scripted merge, retry on conflict

  python3 merge_table.py            the tables, R10 and R11, and P46 to P53 where the cells exist
  python3 merge_table.py --json     the points as JSON for a chart
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import phases  # noqa: E402

EV = Path(os.environ.get("PPE_EVIDENCE", HERE / "evidence"))
HOSTS = ("claude", "grok", "codex")
CELLS = ("w5-a0s", "w5-a3s", "w5-a3i", "o5-a3s", "o5-a3i")


def name(host: str, cell: str) -> str:
    return f"e13-{host}-{cell}"


def have(host: str, cell: str) -> bool:
    return (EV / name(host, cell) / "score.json").is_file()


def load(host: str, cell: str) -> dict:
    n = name(host, cell)
    sc = json.loads((EV / n / "score.json").read_text())
    ph = phases.split(n)
    ctx = EV / n / "context.json"
    calls = sum(t["calls"] for t in json.loads(ctx.read_text())["threads"].values()) if ctx.is_file() else None
    return {"name": n, "score": sc, "phases": ph, "whole": ph["whole"], "work": ph["work"], "valid": bool(sc.get("valid")), "write": sc.get("write") or {},
            "calls": calls, "tokens": (sc.get("tokens") or {}).get("input_all"), "cost": (sc.get("tokens") or {}).get("cost_usd"), "refused": sc.get("refused")}


def fmt(x, nd=1):
    return "n/a" if x is None else (f"{x:,.{nd}f}" if isinstance(x, float) else f"{x:,}")


def table() -> dict:
    data = {(h, c): load(h, c) for h in HOSTS for c in CELLS if have(h, c)}
    print("E13: the write fixture at S = 30 (whole run in seconds; calls and tokens over all contexts)\n")
    print(f"{'host':<7}{'cell':<8}{'whole':>8}{'work':>8}{'valid':>7}{'kit s':>7}{'merges':>8}{'confl':>7}{'retry':>7}{'calls':>7}{'input tokens':>14}{'cost':>8}  oracle detail")
    for h in HOSTS:
        for c in CELLS:
            if (h, c) not in data:
                continue
            d = data[(h, c)]
            w = d["write"]
            o = w.get("oracle") or {}
            detail = "" if d["valid"] else f"hidden {o.get('hidden_ok')} exports {o.get('exports')} answers {o.get('answers_ok')} suite {o.get('suite_passes')}"
            print(f"{h:<7}{c:<8}{d['whole']:>8.1f}{d['work']:>8.1f}{str(d['valid']):>7}{fmt(w.get('script_s'), 2):>7}{fmt(w.get('merges')):>8}{fmt(w.get('conflicts')):>7}{fmt(w.get('retries')):>7}"
                  f"{fmt(d['calls']):>7}{fmt(d['tokens']):>14}{fmt(d['cost'], 3):>8}  {detail}")
    print("\nR10, the merge price (A3 isolated minus A3 shared, then each against A0):")
    for h in HOSTS:
        if all((h, c) in data for c in ("w5-a0s", "w5-a3s", "w5-a3i")):
            a0, s, i = (data[(h, c)] for c in ("w5-a0s", "w5-a3s", "w5-a3i"))
            print(f"  {h:<7} whole {i['whole'] - s['whole']:+.1f} s (isolated {i['whole']:.1f}, shared {s['whole']:.1f}); against A0 {s['whole'] - a0['whole']:+.1f} s shared, {i['whole'] - a0['whole']:+.1f} s isolated; "
                  f"kit {fmt(i['write'].get('script_s'), 2)} s; calls {i['calls']} vs {s['calls']}; tokens {fmt(i['tokens'])} vs {fmt(s['tokens'])}; merge latency max {max(i['write'].get('merge_latency_s', {'-': 0}).values()):.1f} s")
    print("\nR11, the conflict price (overlap5 isolated minus write5 isolated, in task rounds of that host's write5 isolated work phase):")
    for h in HOSTS:
        if (h, "o5-a3i") in data and (h, "w5-a3i") in data:
            o, w = data[(h, "o5-a3i")], data[(h, "w5-a3i")]
            extra = o["whole"] - w["whole"]
            print(f"  {h:<7} +{extra:.1f} s = {extra / w['work']:.2f} rounds of {w['work']:.1f} s; conflicts {o['write'].get('conflicts')} on {o['write'].get('conflict_paths')}, retries {o['write'].get('retries')}, valid {o['valid']}")
    return data


def predictions(data: dict) -> None:
    need = [(h, c) for h in HOSTS for c in CELLS]
    missing = [k for k in need if k not in data]
    if missing:
        print(f"\n(cells missing: {len(missing)} of {len(need)}; predictions are not scored yet)")
        return
    w5 = [(h, c) for h in HOSTS for c in ("w5-a0s", "w5-a3s", "w5-a3i")]
    p46 = all(data[k]["valid"] for k in w5)
    p47 = all(not data[(h, "w5-a3i")]["write"].get("scope_notes") for h in HOSTS)
    p48 = {h: data[(h, "w5-a3i")]["whole"] < data[(h, "w5-a0s")]["whole"] for h in HOSTS}
    p49 = {h: round(data[(h, "w5-a3i")]["whole"] - data[(h, "w5-a3s")]["whole"], 1) for h in HOSTS}
    p50 = {h: (lambda w, v: (w.get("conflicts"), w.get("conflict_paths"), w.get("retries"), v))(data[(h, "o5-a3i")]["write"], data[(h, "o5-a3i")]["valid"]) for h in HOSTS}
    p51 = {h: round((data[(h, "o5-a3i")]["whole"] - data[(h, "w5-a3i")]["whole"]) / data[(h, "w5-a3i")]["work"], 2) for h in HOSTS}
    p52 = {h: not data[(h, "o5-a3s")]["valid"] for h in HOSTS}
    p53 = {h: round(data[(h, "w5-a3i")]["tokens"] / data[(h, "w5-a3s")]["tokens"], 2) for h in HOSTS}
    print("\nPredictions as registered (README A10):")
    print(f"  P46 all nine write5 trials valid: {p46}")
    print(f"  P47 no scope note in a write5 isolated trial: {p47} ({ {h: data[(h, 'w5-a3i')]['write'].get('scope_notes') for h in HOSTS} })")
    print(f"  P48 A3 isolated below A0 on every host: {all(p48.values())} {p48}")
    print(f"  P49 isolation and merging add under 15 s (A3i minus A3s) on every host: {all(v < 15 for v in p49.values())} {p49}")
    print(f"  P50 each overlap5 isolated: one conflict on pkg/__init__.py, one retry, valid: {all(v == (1, ['pkg/__init__.py'], 1, True) for v in p50.values())} {p50}")
    print(f"  P51 conflict cost between 0.6 and 2.0 task rounds on every host: {all(0.6 <= v <= 2.0 for v in p51.values())} {p51}")
    print(f"  P52 at least one overlap5 shared trial invalid: {any(p52.values())} {p52}")
    print(f"  P53 A3i input tokens within 15% of A3s on every host: {all(abs(v - 1) <= 0.15 for v in p53.values())} {p53}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.json:
        out = []
        for h in HOSTS:
            for c in CELLS:
                if have(h, c):
                    d = load(h, c)
                    out.append({"host": h, "cell": c, "whole_s": round(d["whole"], 1), "work_s": round(d["work"], 1), "valid": d["valid"], "kit_s": d["write"].get("script_s"),
                                "conflicts": d["write"].get("conflicts"), "retries": d["write"].get("retries"), "calls": d["calls"], "input_tokens": d["tokens"], "cost_usd": d["cost"]})
        print(json.dumps(out))
        return 0
    predictions(table())
    return 0


if __name__ == "__main__":
    sys.exit(main())
