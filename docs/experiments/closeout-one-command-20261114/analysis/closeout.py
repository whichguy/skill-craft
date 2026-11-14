import json, sys, os, re, collections
exec(open(os.path.join(os.path.dirname(sys.argv[0]),"turns.py")).read().split("for ev in")[0])
def c2(cmd):
    c=cat(cmd)
    if c=="read loop file" and "_assessment" in cmd: return "loop done"
    return c
pat=collections.Counter(); gaps=[]; ncalls=collections.Counter(); runs=0; outs=collections.Counter()
for ev in (l.strip() for l in open(sys.argv[1])):
    d=os.path.dirname(ev); tl=os.path.join(d,"timeline.jsonl")
    if not os.path.exists(tl): continue
    lines=open(ev).read().splitlines(); times={}
    for l in open(tl):
        try: r=json.loads(l); times[r["line"]]=r["t"]
        except Exception: pass
    calls=[]; upd={}
    for i,l in enumerate(lines):
        try: r=json.loads(l)
        except Exception: continue
        if r.get("type")=="tool_call" and r.get("toolName")=="run_terminal_command":
            calls.append([times.get(i), c2((r.get("rawInput") or {}).get("command","")), r["toolCallId"], None])
        if r.get("type")=="tool_call_update" and r.get("status") in ("completed","failed"):
            txt=json.dumps(r.get("content"))[:3000]; upd[r["toolCallId"]]=(times.get(i), txt)
    if not any(c[1].startswith("loop") for c in calls): continue
    runs+=1
    for j,c in enumerate(calls):
        if c[1]!="shiploop complete": continue
        k=j-1
        while k>=0 and calls[k][1]!="shiploop check" and j-k<8: k-=1
        if k<0 or calls[k][1]!="shiploop check": continue
        chk_out=upd.get(calls[k][2],(None,""))[1]
        if "yes" not in chk_out.lower(): continue
        mid=tuple(x[1] for x in calls[k+1:j]); pat[mid]+=1
        t_end=upd.get(c[2],(None,))[0]; t_chk=upd.get(calls[k][2],(None,))[0]
        if t_end and t_chk: gaps.append(t_end-t_chk)
print("runs",runs,"check-yes...complete sequences",sum(pat.values()))
for p,n in pat.most_common(8): print(n, p)
gaps.sort(); print("seconds from check yes to complete done: med %.1f p90 %.1f total %.0f"%(gaps[len(gaps)//2], gaps[int(.9*len(gaps))], sum(gaps)))
