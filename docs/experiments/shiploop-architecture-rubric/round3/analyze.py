"""Round 3 analysis: review arms against the unreviewed plan, with paired bootstrap 95% intervals."""
import json, pathlib, random, collections, re, sys
HERE = pathlib.Path(__file__).resolve().parent
SC = json.loads((HERE.parent / "scenarios.json").read_text()); SCN = {s["id"]: s for s in SC["scenarios"]}
VAL = {"met": 1.0, "partial": 0.5, "missed": 0.0, "overbuilt": 0.0}
G = {"overall": None, "safeguards": ["D1", "D2", "D3", "D4", "I2", "I4"], "detail targets": ["D1", "D2", "D3", "R2", "O1"],
     "proportion": ["P1", "P2", "P3"], "state": ["S1", "S2", "S3", "S4"], "connectivity": ["C1", "C2", "C3", "C4", "C5"],
     "accuracy": ["R3"]}
def load(d):
    out = {}
    for f in pathlib.Path(d).glob("*.json"):
        try: out[f.stem] = json.loads(f.read_text())
        except Exception: pass
    return out
def score(j, cs):
    xs = [VAL[g] for c, g in j["grades"].items() if g in VAL and (cs is None or c in cs)]
    return sum(xs) / len(xs) if xs else None
def boot(diffs, n=4000, seed=3):
    rnd = random.Random(seed); m = len(diffs)
    means = sorted(sum(rnd.choice(diffs) for _ in range(m)) / m for _ in range(n))
    return sum(diffs) / m, means[int(0.025 * n)], means[int(0.975 * n)]
rows = load(HERE / "judge")
by = collections.defaultdict(dict)
for stem, j in rows.items():
    sid, rt, arm, k = stem.split("_"); by[arm][(sid, rt, k)] = j
arms = [a for a in ("none", "current", "safeguards", "prune") if a in by]
print("plans graded:", {a: len(by[a]) for a in arms})
print(f"\n{'group':15}" + "".join(f"{a:>12}" for a in arms))
for g, cs in G.items():
    vals = []
    for a in arms:
        xs = [x for x in (score(j, cs) for j in by[a].values()) if x is not None]
        vals.append(f"{sum(xs)/len(xs):12.3f}" if xs else f"{'-':>12}")
    print(f"{g:15}" + "".join(vals))
over = {a: sum(j["grades"].get(c) == "overbuilt" for j in by[a].values() for c in ("P1", "P3")) for a in arms}
tier = {a: f"{sum(j['tier_chosen'] == SCN[c[0]]['tier'] for c, j in by[a].items())}/{len(by[a])}" for a in arms}
errs = {a: sum(len(j.get("platform_errors") or []) for j in by[a].values()) for a in arms}
print("\noverbuilt P1/P3 grades:", over, "| tier matched:", tier, "| platform errors:", errs)
print("\nChange against no review (mean, 95% paired bootstrap interval, cells won/lost):")
for a in arms[1:]:
    for g, cs in G.items():
        d = []; w = l = 0
        for c, j in by[a].items():
            if c not in by["none"]: continue
            x, y = score(j, cs), score(by["none"][c], cs)
            if x is None or y is None: continue
            d.append(x - y); w += x > y + 1e-9; l += y > x + 1e-9
        if d:
            m, lo, hi = boot(d)
            print(f"  {a:10} {g:15} {m:+.3f}  [{lo:+.3f}, {hi:+.3f}]  {w:3}/{l:<3}  n={len(d)}")
print("\nPer criterion:")
cr = sorted({c for a in arms for j in by[a].values() for c in j["grades"]}, key=lambda c: (c[0], int(c[1:])))
for c in cr:
    print(f"  {c:3}" + "".join(f"{(lambda xs: sum(xs)/len(xs) if xs else float('nan'))([VAL[j['grades'][c]] for j in by[a].values() if j['grades'].get(c) in VAL]):9.2f}" for a in arms))
L = HERE / "lengths.json"
if L.exists():
    lens = json.loads(L.read_text()); print("\nmean words:", {a: round(sum(v)/len(v)) for a, v in lens.items() if v})
