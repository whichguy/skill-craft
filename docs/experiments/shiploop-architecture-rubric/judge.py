"""Blind rubric judge: grade each plan on the criteria its scenario applies, then tabulate by variant."""
import json, re, pathlib, subprocess, collections, os, sys
from concurrent.futures import ThreadPoolExecutor
HERE = pathlib.Path(__file__).resolve().parent
EXP = pathlib.Path(os.environ.get("EXP_DIR", "."))
R = json.loads((HERE / "rubric.json").read_text()); SC = json.loads((HERE / "scenarios.json").read_text())
SCN = {s["id"]: s for s in SC["scenarios"]}
RT = {"GAS": "Google Apps Script web app", "SF": "Salesforce DX with Lightning Web Components", "CF": "Cloudflare Workers",
      "VERCEL": "Vercel with Next.js", "AWS": "AWS serverless", "GCP": "Google Cloud Run", "NODE": "self-hosted Node.js with Express"}
OUT = os.environ.get("OUT_SUBDIR", "out"); JDIR = os.environ.get("JUDGE_SUBDIR", "judge")
def plan_text(f):
    if f.suffix != ".jsonl": return f.read_text()
    for line in f.read_text().splitlines():
        try: e = json.loads(line)
        except Exception: continue
        if e.get("type") == "result": return e.get("result", "")
    return ""
PROMPT = """You grade an architecture plan against a rubric. Judge what the plan ADOPTS, not what it mentions or rejects.
Runtime: {rt}
Request: {req}
Expected tier: {tier} — {tierdef}
Overbuild note: {over}

Grades: {grades}

Criteria to grade:
{crit}

Return only JSON: {{"tier_chosen": one of {tiers}, "grades": {{criterion id: grade}}, "overbuilt_items": [short strings], "platform_errors": [factually wrong claims about the runtime]}}

Plan:
<<<
{plan}
>>>
"""
def claude(t):
    return subprocess.run(["claude", "-p", "--model", "sonnet", "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}'], input=t, capture_output=True, text=True).stdout
def job(f):
    dest = EXP / JDIR / (f.stem + ".json")
    if dest.exists() and dest.stat().st_size: return
    sid, rt, var, k = f.stem.split("_"); s = SCN[sid]
    ext = rt in s.get("runtimes_ext", [])
    applies = s["applies"] + (s.get("applies_ui", []) if ext and s.get("ui") else [])
    req = s["request"] + (f" Use {s['ui']} for the UI." if ext and s.get("ui") else "")
    crit = "\n".join(f"{c} {R['criteria'][c][0]}: {R['criteria'][c][1]}" for c in applies)
    t = PROMPT.format(rt=RT[rt], req=req, tier=s["tier"], tierdef=SC["tiers"][s["tier"]], over=s["overbuild"],
                      grades="; ".join(f"{k} = {v}" for k, v in R["grades"].items()), crit=crit, tiers=list(SC["tiers"]), plan=plan_text(f))
    dest.write_text(claude(t))
if __name__ == "__main__":
    (EXP / JDIR).mkdir(exist_ok=True)
    files = sorted(f for f in (EXP / OUT).iterdir() if f.suffix in (".md", ".jsonl") and f.stat().st_size)
    with ThreadPoolExecutor(10) as ex: list(ex.map(job, files))
    val = {"met": 1.0, "partial": 0.5, "missed": 0.0, "overbuilt": 0.0}
    by_var = collections.defaultdict(list); by_crit = collections.defaultdict(lambda: collections.defaultdict(list))
    tier_hit = collections.defaultdict(lambda: collections.defaultdict(list)); over = collections.defaultdict(collections.Counter)
    errs = collections.Counter(); rows = {}
    for f in sorted((EXP / JDIR).glob("*.json")):
        m = re.search(r"\{.*\}", f.read_text(), re.S)
        if not m: print("unparsed", f.name); continue
        j = json.loads(m.group(0)); rows[f.stem] = j
        sid, rt, var, k = f.stem.split("_")
        for c, g in j["grades"].items():
            if g in val: by_var[var].append(val[g]); by_crit[c][var].append(val[g])
            if g == "overbuilt": over[var][c] += 1
        tier_hit[sid][var].append(j["tier_chosen"] == SCN[sid]["tier"])
        errs[var] += len(j.get("platform_errors") or [])
    (EXP / f"verdicts_{JDIR}.json").write_text(json.dumps(rows, indent=1, sort_keys=True))
    mean = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    print("Overall score:", {v: f"{mean(x):.2f} (n={len(x)})" for v, x in by_var.items()}, "platform errors:", dict(errs))
    V = sorted(by_var)
    print(f"\nTier matched per scenario ({' | '.join(V)}):")
    for sid in SCN:
        t = tier_hit[sid]
        if any(t.values()): print(f"  {sid} {SCN[sid]['name']:26} {SCN[sid]['tier']:25} " + " | ".join(f"{sum(t[v])}/{len(t[v])}" for v in V))
    print(f"\nPer criterion ({' | '.join(V)}):")
    for c in R["criteria"]:
        if c in by_crit: print(f"  {c:3} {R['criteria'][c][0]:22} " + " | ".join(f"{mean(by_crit[c][v]):.2f}" for v in V))
    print("\nOverbuilt grades:", {v: dict(c) for v, c in over.items()})
