#!/usr/bin/env python3
"""a0p_table.py: the A0p control (README A11 and A12) against its registered predictions P54 to P63 (journal E14).

Reads the trials' score.json (from the trial folders you name, or evidence/ once exported) and the E12 and E13 baselines in evidence/.
Prints the cells and scores each prediction as written; nothing is rescored.

  python3 a0p_table.py [TRIAL_DIR]      TRIAL_DIR holds e14-<host>-s30-a0p and e14-<host>-w5-a0p (default: evidence/)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVID = HERE / "evidence"
HOSTS = ("claude", "grok", "codex")


def cell(path: Path):
    f = path / "score.json"
    if not f.is_file():
        return None
    m = json.loads(f.read_text())
    t, k = m.get("timings", {}), m.get("tokens", {})
    return {"whole": t.get("launch_to_exit_s"), "valid": m.get("valid"), "peak": m.get("peak_concurrency"), "in_all": k.get("input_all"),
            "cost": k.get("cost_usd"), "answers": (m.get("answers") or {}).get("all_correct"), "oracle": ((m.get("write") or {}).get("oracle") or {}).get("valid")}


def main(argv=None) -> int:
    trials = Path((argv or sys.argv[1:] or [str(EVID)])[0])
    rows = {}
    for host in HOSTS:
        rows[("s30", host)] = {"A0": cell(EVID / f"e12-{host}-s30-a0"), "A3": cell(EVID / f"e12-{host}-s30-a3"), "A0p": cell(trials / f"e14-{host}-s30-a0p")}
        rows[("w5", host)] = {"A0": cell(EVID / f"e13-{host}-w5-a0s"), "A3": cell(EVID / f"e13-{host}-w5-a3s"), "A0p": cell(trials / f"e14-{host}-w5-a0p")}
    for fixture, title in (("s30", "analysis5, S = 30 (A11)"), ("w5", "write5, S = 30 (A12)")):
        print(f"\n{title}: whole run (s), A0p against the same host's A0 and A3, input tokens over all contexts, cost")
        print("host    A0       A3       A0p      A0p/A0   A0p/A3   valid  peak  in A0p      in A3       in A0p/A3  cost A0p")
        for host in HOSTS:
            r = rows[(fixture, host)]
            a0, a3, p = r["A0"], r["A3"], r["A0p"]
            if not (a0 and a3):
                continue
            if not p:
                print(f"{host:<7}{a0['whole']:<9.1f}{a3['whole']:<9.1f}(no trial yet)")
                continue
            ok = p["valid"] if fixture == "s30" else (p["valid"] and p["oracle"])
            print(f"{host:<7}{a0['whole']:<9.1f}{a3['whole']:<9.1f}{p['whole']:<9.1f}{p['whole'] / a0['whole']:<9.2f}{p['whole'] / a3['whole']:<9.2f}{str(ok):<7}{p['peak']!s:<6}"
                  f"{p['in_all'] or 0:<12,}{a3['in_all'] or 0:<12,}{(p['in_all'] or 0) / (a3['in_all'] or 1):<11.2f}{p['cost'] if p['cost'] is not None else '-'}")
    print("\nPredictions as registered:")
    s30 = {h: rows[("s30", h)] for h in HOSTS}
    w5 = {h: rows[("w5", h)] for h in HOSTS}
    have = lambda rs, h: rs[h]["A0p"] and rs[h]["A0"] and rs[h]["A3"]
    if all(have(s30, h) for h in HOSTS):
        print("  P54 every analysis5 A0p valid:", all(s30[h]["A0p"]["valid"] for h in HOSTS), {h: s30[h]["A0p"]["valid"] for h in HOSTS})
        print("  P55 A0p at least 35% below A0:", all(s30[h]["A0p"]["whole"] <= 0.65 * s30[h]["A0"]["whole"] for h in HOSTS),
              {h: round(1 - s30[h]["A0p"]["whole"] / s30[h]["A0"]["whole"], 3) for h in HOSTS})
        near = {h: abs(s30[h]["A0p"]["whole"] / s30[h]["A3"]["whole"] - 1) <= 0.15 for h in HOSTS}
        print("  P56 A0p within 15% of A3 on at least two hosts:", sum(near.values()) >= 2, {h: round(s30[h]["A0p"]["whole"] / s30[h]["A3"]["whole"], 3) for h in HOSTS})
        print("  P57 A0p input tokens below A3's on every host:", all(s30[h]["A0p"]["in_all"] < s30[h]["A3"]["in_all"] for h in HOSTS))
        print("  P58 A0p not longer than A3 on Claude and Grok:", all(s30[h]["A0p"]["whole"] <= s30[h]["A3"]["whole"] for h in ("claude", "grok")))
    else:
        print("  P54 to P58: waiting for", [h for h in HOSTS if not have(s30, h)])
    if all(have(w5, h) for h in HOSTS):
        band = {"claude": (106, 144), "grok": (136, 184), "codex": (177, 240)}
        print("  P59 every write5 A0p valid:", all(w5[h]["A0p"]["valid"] and w5[h]["A0p"]["oracle"] for h in HOSTS))
        print("  P60 within 15% of A0 minus three settles:", all(band[h][0] <= w5[h]["A0p"]["whole"] <= band[h][1] for h in HOSTS), {h: round(w5[h]["A0p"]["whole"], 1) for h in HOSTS})
        print("  P61 Grok and Codex: A0p shorter than A3 shared:", all(w5[h]["A0p"]["whole"] < w5[h]["A3"]["whole"] for h in ("grok", "codex")))
        print("  P62 Claude: A0p longer than A3 shared:", w5["claude"]["A0p"]["whole"] > w5["claude"]["A3"]["whole"])
        print("  P63 A0p input tokens below A3 shared's on every host:", all(w5[h]["A0p"]["in_all"] < w5[h]["A3"]["in_all"] for h in HOSTS))
    else:
        print("  P59 to P63: waiting for", [h for h in HOSTS if not have(w5, h)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
