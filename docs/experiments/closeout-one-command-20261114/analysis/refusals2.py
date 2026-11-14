import json, glob, os, collections, re, datetime
INNER = {"step-plan","test-spec","validate-existing","implement","test","document","carry-forward"}
cut = datetime.datetime(2026,10,29,15,0).timestamp()
files = [l.strip() for l in open(__import__("sys").argv[1])]
def fam(e):
    e = re.sub(r"/[^ \n]*", "<p>", e)
    m = re.match(r"(ShipLoop [a-z -]+?:|[^.:\n]{0,70})", e)
    return (m.group(1) if m else e[:60]).strip()
c = collections.Counter(); fams = collections.Counter(); per_action = collections.Counter(); runs=set()
stage_ref = collections.Counter(); after = collections.Counter(); first_check = collections.Counter()
for f in files:
    stage_of = {}; seen_check=set(); rows=[]
    for line in open(f, errors="replace"):
        try: r = json.loads(line)
        except Exception: continue
        if r.get("ts",0) < cut: continue
        if r.get("kind") == "packet": stage_of[r.get("action")] = r.get("stage")
        if r.get("kind") != "command" or r.get("verb") not in ("complete","check"): continue
        st = stage_of.get(r.get("action"))
        if st not in INNER: continue
        rows.append((r, st))
    for i,(r,st) in enumerate(rows):
        runs.add(f); v=r["verb"]; a=r.get("action"); ok = r.get("exit")==0
        c[(v,"ok" if ok else "refused")]+=1
        if v=="check": seen_check.add(a)
        if v=="complete" and ok: first_check["checked first" if a in seen_check else "no check first"]+=1
        if v=="complete" and not ok:
            per_action[(f,a)]+=1; stage_ref[st]+=1
            fams[fam(str(r.get("error") or ""))]+=1
print("runs", len(runs)); print(dict(c)); print(dict(first_check))
print("refused completes by stage", dict(stage_ref))
print("actions with >=1 refused complete", len(per_action), "max refusals one action", max(per_action.values()) if per_action else 0)
for k,v in fams.most_common(25): print(v, k)
