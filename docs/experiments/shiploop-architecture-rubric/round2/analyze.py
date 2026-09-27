"""Round-2 analysis: composites, paired per-cell comparison against shipped, per-tier proportion."""
import json, re, pathlib, collections, sys
HERE = pathlib.Path(__file__).resolve().parent
SC = json.loads((HERE.parent / "scenarios.json").read_text()); SCN = {s["id"]: s for s in SC["scenarios"]}
VAL = {"met": 1.0, "partial": 0.5, "missed": 0.0, "overbuilt": 0.0}
GROUPS = {"Proportion": ["P1", "P2", "P3"], "Safeguards": ["D1", "D2", "D3", "D4", "I2", "I4"], "Identity/access": ["I1", "I3"],
          "State": ["S1", "S2", "S3", "S4"], "Connectivity": ["C1", "C2", "C3", "C4", "C5"], "Caching": ["K1", "K2", "K3"],
          "Leverage/accuracy": ["R1", "R2", "R3"], "Verification": ["V1", "O1"], "UI": ["U1", "U2", "U3"]}
def load(jdir):
    rows = {}
    for f in sorted(pathlib.Path(jdir).glob("*.json")):
        m = re.search(r"\{.*\}", f.read_text(), re.S)
        if m:
            try: rows[f.stem] = json.loads(m.group(0))
            except Exception: pass
    return rows
def mean(x): return sum(x) / len(x) if x else float("nan")
def report(rows, base="shipped"):
    by = collections.defaultdict(dict)  # variant -> cell -> verdict
    for stem, j in rows.items():
        sid, rt, var, k = stem.split("_"); by[var][(sid, rt, k)] = j
    V = [base] + sorted(v for v in by if v != base)
    def score(j, crits=None):
        g = [VAL[x] for c, x in j["grades"].items() if x in VAL and (crits is None or c in crits)]
        return mean(g) if g else None
    print("variant   overall  " + "  ".join(f"{g[:11]:>11}" for g in GROUPS) + "   tier  P1-over  P3-over  errors")
    for v in V:
        cells = by[v].values()
        comp = []
        for g, cs in GROUPS.items():
            xs = [VAL[x] for j in cells for c, x in j["grades"].items() if c in cs and x in VAL]
            comp.append(f"{mean(xs):11.2f}" if xs else f"{'-':>11}")
        tier = sum(j["tier_chosen"] == SCN[c[0]]["tier"] for c, j in by[v].items())
        p1o = sum(j["grades"].get("P1") == "overbuilt" for j in cells); p3o = sum(j["grades"].get("P3") == "overbuilt" for j in cells)
        errs = sum(len(j.get("platform_errors") or []) for j in cells)
        allg = [VAL[x] for j in cells for x in j["grades"].values() if x in VAL]
        print(f"{v:9} {mean(allg):7.2f}  " + "  ".join(comp) + f"   {tier:2}/{len(by[v]):2}  {p1o:7}  {p3o:7}  {errs:6}")
    print(f"\nPaired per cell against {base} (wins / ties / losses), overall and safeguards:")
    for v in V[1:]:
        for label, crits in (("overall", None), ("safeguards", GROUPS["Safeguards"]), ("proportion", GROUPS["Proportion"])):
            w = t = l = 0
            for c, j in by[v].items():
                if c not in by[base]: continue
                a, b = score(j, crits), score(by[base][c], crits)
                if a is None or b is None: continue
                if a > b + 1e-9: w += 1
                elif b > a + 1e-9: l += 1
                else: t += 1
            print(f"  {v:4} {label:11} {w:3} / {t:3} / {l:3}")
    print("\nP1 by expected tier (mean):")
    tiers = sorted({SCN[c[0]]["tier"] for c in by[base]})
    print("  " + f"{'tier':26}" + "".join(f"{v:>9}" for v in V))
    for t in tiers:
        print("  " + f"{t:26}" + "".join(f"{mean([VAL[j['grades']['P1']] for c, j in by[v].items() if SCN[c[0]]['tier'] == t and j['grades'].get('P1') in VAL]):9.2f}" for v in V))
    print("\nPer criterion:")
    crits = sorted({c for v in V for j in by[v].values() for c in j["grades"]}, key=lambda c: (c[0], int(c[1:])))
    for c in crits:
        print(f"  {c:3}" + "".join(f"{mean([VAL[j['grades'][c]] for j in by[v].values() if j['grades'].get(c) in VAL]):8.2f}" for v in V))
if __name__ == "__main__":
    report(load(sys.argv[1]), base=sys.argv[2] if len(sys.argv) > 2 else "shipped")
