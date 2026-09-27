"""Judge v2: criteria before and after the plan, anchored grades, and a quoted evidence span before every grade.

Changes from judge.py, following the LLM-as-judge literature (G-Eval form filling, evidence-before-verdict,
lost-in-the-middle): each criterion's grade must follow a quote from the plan; "met"/"partial" need a
supporting quote, "overbuilt" must quote the unrequested complexity, "missed" records "none".
"""
import json, re, pathlib, subprocess, os, sys
from concurrent.futures import ThreadPoolExecutor
HERE = pathlib.Path(__file__).resolve().parent
R = json.loads((HERE / "rubric.json").read_text()); SC = json.loads((HERE / "scenarios.json").read_text())
SCN = {s["id"]: s for s in SC["scenarios"]}
RT = {"GAS": "Google Apps Script web app", "SF": "Salesforce DX with Lightning Web Components", "CF": "Cloudflare Workers",
      "VERCEL": "Vercel with Next.js", "AWS": "AWS serverless", "GCP": "Google Cloud Run", "NODE": "self-hosted Node.js with Express"}
ANCHORS = """Grade anchors:
- met: the plan adopts a concrete mechanism or rule for this criterion, sized to the request. Quote it.
- partial: the plan names the concern but leaves a material part undecided, vague ("handle errors appropriately") or wrong. Quote the vague or wrong text.
- missed: the criterion applies and the plan has no text that addresses it. Evidence is "none".
- overbuilt: the plan adopts more than the request needs for this criterion. Quote the unrequested machinery.
- na: the criterion does not apply to this plan. Evidence is "na"."""
PROMPT = """You grade an architecture plan against a rubric. Judge what the plan ADOPTS, not what it mentions or rejects.
Runtime: {rt}
Request: {req}
Expected tier: {tier} — {tierdef}
Overbuild note: {over}

{anchors}

Criteria to grade:
{crit}

For each criterion, first copy the shortest exact quote from the plan that decides the grade (or "none"/"na"), then give the grade that quote supports. Never grade met or partial without a quote.

Plan:
<<<
{plan}
>>>

Grade these criteria now: {ids}.
Return only JSON: {{"tier_chosen": one of {tiers}, "criteria": {{criterion id: {{"evidence": quote, "grade": grade}}}}, "overbuilt_items": [short strings], "platform_errors": [factually wrong claims about the runtime]}}
"""
def claude(t, timeout=300):
    """One judge call; a hung call times out instead of stalling the pool."""
    try:
        return subprocess.run(["claude", "-p", "--model", "sonnet", "--tools", "", "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}'],
                              input=t, capture_output=True, text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return ""
def grade(plan, sid, rt, dest):
    s = SCN[sid]; ext = rt in s.get("runtimes_ext", [])
    applies = s["applies"] + (s.get("applies_ui", []) if ext and s.get("ui") else [])
    req = s["request"] + (f" Use {s['ui']} for the UI." if ext and s.get("ui") else "")
    crit = "\n".join(f"{c} {R['criteria'][c][0]}: {R['criteria'][c][1]}" for c in applies)
    t = PROMPT.format(rt=RT[rt], req=req, tier=s["tier"], tierdef=SC["tiers"][s["tier"]], over=s["overbuild"], anchors=ANCHORS,
                      crit=crit, ids=", ".join(applies), tiers=list(SC["tiers"]), plan=plan)
    out = ""
    for _ in range(3):  # retry on timeout or unparseable output
        out = claude(t)
        m = re.search(r"\{.*\}", out, re.S)
        try:
            j = json.loads(m.group(0)); j["grades"] = {c: v["grade"] for c, v in j["criteria"].items()}
            dest.write_text(json.dumps(j, indent=1)); return
        except Exception: continue
    with open(dest.parent / "judge_failures.log", "a") as log:  # never drop a failure silently
        log.write(f"{dest.name}\t{len(out)} chars\t{out[:300]!r}\n")
def run(jobs, workers=10):
    with ThreadPoolExecutor(workers) as ex: list(ex.map(lambda a: grade(*a), jobs))
