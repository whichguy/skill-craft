import json,os,glob,sys
C="/Users/dadleet/src/backchain/results/backchain-efficiency-20261101/cohort"
case=sys.argv[1]
def edges(plan):
    out=[]
    for s in plan["steps"]:
        for i in s.get("inputs",[]):
            if i.get("from"): out.append(f'{s["id"]}<-{i["from"]}')
    return out
for r in (1,2,3):
  d=f"{C}/runs/{case}-candidate-r{r}/artifacts/run"
  print("=========== candidate r",r)
  res=json.load(open(d+"/result.json"))
  print("result.status:",res.get("status"))
  print("final edges:",edges(res["plan"]), "steps",[s["id"] for s in res["plan"]["steps"]], "unresolved",res["plan"].get("unresolved"))
  rv=res.get("review",{})
  print("result.review keys", list(rv) if isinstance(rv,dict) else rv)
  fr=json.load(open(d+"/final-review.json"))
  for k in ["planning_gaps","execution_blockers","unresolved","coverage"]:
    print(f"final-review.{k}:",json.dumps(fr.get(k),indent=1)[:2500])
  print("final-review.findings:")
  for f in fr.get("findings",[]): print("   *",json.dumps(f)[:1200])
  for c in sorted(glob.glob(d+"/cycles/*")):
    rvw=json.load(open(c+"/review.json"))
    print(" cycle",os.path.basename(c),"change_class",rvw.get("change_class"),"next_action",rvw.get("next_action"))
    print("   planning_gaps:",json.dumps(rvw.get("planning_gaps"))[:2500])
    print("   execution_blockers:",json.dumps(rvw.get("execution_blockers"))[:1500])
    for f in rvw.get("findings",[]): print("   F:",json.dumps(f)[:1500])
    rep=json.load(open(c+"/report.json")); print("   report:",json.dumps(rep)[:1500])
