"""Round 3: does a planning review with detail-safeguard checks fix v5 plans without overbuilding them?"""
import json, pathlib, sys, os
HERE = pathlib.Path(__file__).resolve().parent
SK = pathlib.Path(os.environ["SHIPLOOP_SRC"]) / "skills" / "shiploop"
sys.path.insert(0, str(SK / "scripts"))
import shiploop_prompts as p
SC = json.loads((HERE.parent / "scenarios.json").read_text()); SCN = {s["id"]: s for s in SC["scenarios"]}
ENV = SC["runtimes"]
def plan_text(f):
    for l in f.read_text().splitlines():
        try: e = json.loads(l)
        except Exception: continue
        if e.get("type") == "result": return e.get("result", "")
    return ""
SAFEGUARDS = """- personal data the plan holds, shows, logs or sends to a third party without
  saying how long it is kept, how it is removed, and that it stays out of logs
  and error messages;
- a runtime quota or limit the design depends on that the plan does not name
  and plan within;
- a background or asynchronous failure the plan does not record where someone
  who can act will see it;
"""
base = p.PLANNING_REVIEW_FOCUS
anchor = "- a missing prerequisite, wrong order or unowned verification in the steps.\n"
assert anchor in base
FOCUS = {"current": base, "safeguards": base.replace(anchor, SAFEGUARDS + anchor)}
T = """You are the Improve review of a ShipLoop plan-stage result. Review the plan against the focus below, fix what you find, and return the complete revised plan.

{focus}
Change only what a finding requires. Do not add features, infrastructure or a higher placement tier that the request does not need.

Request: {req}

Environment: {env}

Plan under review:
<<<
{plan}
>>>

Return two sections: "## Findings" (each finding and its fix, or "None"), then "## Revised plan" with the complete revised architecture decision and work items."""
src = HERE.parent / "r2" / "out"; n = 0
for f in sorted(src.glob("*_v5_*.jsonl")):
    sid, rt, _, k = f.stem.split("_"); s = SCN[sid]
    ui = s.get("ui") if rt in s.get("runtimes_ext", []) else None
    req = s["request"] + (f" Use {ui} for the UI." if ui else "")
    plan = plan_text(f); assert len(plan.split()) >= 150, f
    (HERE / "originals").mkdir(exist_ok=True); (HERE / "originals" / f"{sid}_{rt}_none_{k}.md").write_text(plan)
    for arm, focus in FOCUS.items():
        (HERE / "prompts" / f"{sid}_{rt}_{arm}_{k}.txt").write_text(T.format(focus=focus, req=req, env=ENV[rt], plan=plan)); n += 1
(HERE / "focus_safeguards.txt").write_text(FOCUS["safeguards"])
print(n, "review prompts;", len(list((HERE / "originals").iterdir())), "original plans")
