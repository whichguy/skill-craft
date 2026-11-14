import json, datetime, sys, collections
cut = datetime.datetime(2026,10,29,15,0).timestamp()
INNER = {"step-plan","test-spec","validate-existing","implement","test","document","carry-forward"}
res = collections.Counter(); waits=[]
for f in (l.strip() for l in open(sys.argv[1])):
    stage_of={}; rows=[]
    for line in open(f, errors="replace"):
        try: r=json.loads(line)
        except Exception: continue
        if r.get("ts",0)<cut: continue
        if r.get("kind")=="packet": stage_of[r.get("action")]=r.get("stage")
        if r.get("kind")=="command" and r.get("verb")=="complete" and stage_of.get(r.get("action")) in INNER: rows.append(r)
    done=set()
    for i,r in enumerate(rows):
        a=r.get("action")
        if r.get("exit")!=0 and a not in done:
            done.add(a)
            ok=[x for x in rows[i+1:] if x.get("action")==a and x.get("exit")==0]
            res["accepted later" if ok else "never accepted"]+=1
            if ok: waits.append(ok[0]["ts"]-r["ts"])
            else: print("UNRESOLVED", f)
print(dict(res)); waits.sort(); print("seconds to acceptance: median", waits[len(waits)//2] if waits else None, "max", max(waits) if waits else None)
