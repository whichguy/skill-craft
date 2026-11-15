"""rescore.py (journal E14): re-score the E0 census against a per-round fan-out overhead R (seconds): what is left of the ideal saving once each fan-out round
pays for spawn, a cold worker context, collection and integration?  Uses census/evidence/census.json rows and gated.py's own definitions
(overlap rule, deps mapping, longest-path schedule), unlimited workers, unchanged step times, no capacity limit.

Policy: a plan fans out a round only when that round's own saving exceeds R (a script predicate could do that from recorded times).
Rounds: steps at the same dependency level; steps whose declared paths overlap cannot share a round (greedy in list order, the rest run
serially after it).  Round saving = sum of the round's durations minus its longest.  Level barriers make this a conservative estimate of the
longest-path (CPM) saving, so both are printed.

  python3 -I rescore.py            prints the table (the output is kept in evidence/rescore.txt)
"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gated

rows = json.load(open(HERE / "evidence" / "census.json"))["plans"]
UNKNOWN_CONFLICTS = True  # STRICT: a step with no declared paths conflicts with every other step

def plan_rounds(row):
    d, deps, paths, level = row["durations_s"], row["deps"], row["paths"], row["level"]
    n = len(d)
    rounds = []
    for lv in sorted(set(level)):
        members = [i for i in range(n) if level[i] == lv]
        chosen = []
        for i in members:
            ok = True
            for j in chosen:
                unknown = not (paths[i] and paths[j])
                if (UNKNOWN_CONFLICTS if unknown else gated.overlap(paths[i], paths[j])):
                    ok = False
                    break
            if ok:
                chosen.append(i)
        if len(chosen) >= 2:
            ds = [d[i] for i in chosen]
            rounds.append({"width": len(chosen), "saving": sum(ds) - max(ds), "shortest": min(ds), "longest": max(ds)})
    return rounds

timed = []
for r in rows:
    a = gated.analyse(r, UNKNOWN_CONFLICTS)
    if a:
        timed.append((r, a))
T = sum(a["T"] for _, a in timed)
Tm = sum(a["T"] for _, a in timed if a["n"] >= 2)
gross_cpm = sum(a["T"] - a["C_gated"] for _, a in timed)
print(f"timed plans {len(timed)}, multi-step {sum(1 for _,a in timed if a['n']>=2)}, T_s {T:.0f} s; CPM gated gross saving {gross_cpm:.0f} s = {gross_cpm/T:.1%} of all timed, {gross_cpm/Tm:.1%} of multi-step time")
allrounds = [(r, plan_rounds(r)) for r, a in timed]
gross_rounds = sum(x["saving"] for _, rs in allrounds for x in rs)
nr = sum(len(rs) for _, rs in allrounds)
print(f"level-barrier gross saving {gross_rounds:.0f} s = {gross_rounds/T:.1%}; fan-out rounds available: {nr} in {sum(1 for _,rs in allrounds if rs)} plans; width histogram {sorted({x['width'] for _,rs in allrounds for x in rs})}")
print(f"round saving distribution (s): " + ", ".join(f"p{q}={sorted(x['saving'] for _,rs in allrounds for x in rs)[int(q/100*(nr-1))]:.0f}" for q in (10, 25, 50, 75, 90)) + f", max {max(x['saving'] for _,rs in allrounds for x in rs):.0f}")
print(f"shortest task in a round (s): median {sorted(x['shortest'] for _,rs in allrounds for x in rs)[nr//2]:.0f}")
print()
print("R (s per round)  rounds taken  plans gaining  net saving (s)  % of all timed  % of multi-step  note")
notes = {25: "toy host overhead alone (Claude 21 s, Codex 27 s)", 45: "toy host overhead, Grok-like (43 s)", 75: "+ one real cold worker context (F13: about 75 s)", 100: "toy overhead + real cold start (Opus's estimate)", 150: "+ merge and a re-verification on the combined tree", 200: "heavier real repository", 300: "pessimistic"}
for R in (0, 25, 45, 75, 100, 150, 200, 300):
    taken = net = 0.0
    plans = 0
    for r, rs in allrounds:
        got = 0
        for x in rs:
            if x["saving"] > R:
                taken += 1
                got += x["saving"] - R
        net += got
        plans += 1 if got > 0 else 0
    print(f"{R:>8}         {int(taken):>6}        {plans:>6}        {net:>9.0f}       {net/T:>7.1%}        {net/Tm:>7.1%}    {notes.get(R, 'ideal, no overhead' if R == 0 else '')}")
