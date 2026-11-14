import json, sys, os, re, collections
cat_time=collections.Counter(); cat_n=collections.Counter(); runs=0; tot=0
def cat(cmd):
    if "until_loop" in cmd:
        m=re.search(r"until_loop_\w+\.py\"?'?\s+(\w+)", cmd); return "loop "+(m.group(1) if m else "?")
    if re.search(r"shiploop['\"]?\s", cmd) or "/shiploop " in cmd:
        for v in ("check","complete","next","note","pause","status","trace","init","start","resume"):
            if re.search(r"\s"+v+r"(\s|$|')", cmd): return "shiploop "+v
        return "shiploop other"
    if re.search(r"packets/[^ ]*\.md", cmd) and re.search(r"\b(sed|cat|head|tail|nl|less|rg|grep)\b", cmd): return "read packet"
    if re.search(r"loops/[^ ]*(contract|terminal)", cmd): return "read loop file"
    return "work"
for ev in (l.strip() for l in open(sys.argv[1])):
    d=os.path.dirname(ev); tl=os.path.join(d,"timeline.jsonl")
    if not os.path.exists(tl): continue
    lines=open(ev).read().splitlines(); times={}
    for l in open(tl):
        try: r=json.loads(l); times[r["line"]]=r["t"]
        except Exception: pass
    rows=[]
    for i,l in enumerate(lines):
        try: r=json.loads(l)
        except Exception: continue
        if i in times: rows.append((times[i], r))
    if not any(r.get("type")=="tool_call" and "until_loop" in json.dumps(r.get("rawInput","")) for _,r in rows): continue
    runs+=1; prev_end=rows[0][0]; start_of={}
    for t,r in rows:
        if r.get("type")=="tool_call":
            raw=r.get("rawInput") or {}; cmd=raw.get("command") if isinstance(raw,dict) else str(raw)
            cmd = cmd if isinstance(cmd,str) else json.dumps(raw)
            if r.get("toolName") not in ("run_terminal_command",None) and not cmd: cmd=r.get("toolName","")
            c=cat(cmd or "") if r.get("toolName")=="run_terminal_command" else ("read packet" if "packets/" in json.dumps(raw) else "work:"+str(r.get("toolName")))
            start_of[r["toolCallId"]]=(t,c, t-prev_end)
        elif r.get("type")=="tool_call_update" and r.get("status") in ("completed","failed") and r.get("toolCallId") in start_of:
            t0,c,think=start_of.pop(r["toolCallId"]); cost=think+(t-t0)
            cat_time[c]+=cost; cat_n[c]+=1; tot+=cost; prev_end=t
print("runs with loops", runs, "tool time+think total %.0f s"%tot)
for c,v in cat_time.most_common(): print("%-22s n=%5d  %7.0f s  %5.1f%%  %.1f s each"%(c,cat_n[c],v,100*v/tot,v/cat_n[c]))
