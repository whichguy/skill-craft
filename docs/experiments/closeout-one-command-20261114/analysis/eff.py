import json, datetime, sys, collections, statistics as st
cut = datetime.datetime(2026,10,29,15,0).timestamp()
INNER = {"step-plan","test-spec","validate-existing","implement","test","document","carry-forward"}
verb_ms = collections.defaultdict(list); verbs_per_action = collections.Counter()
stage_wall = collections.defaultdict(list); script_share=[]; checks_per=collections.Counter()
gap_checkyes_complete=[]; complete_after_yes_ms=[]; complete_nocheck_ms=[]; first_work=collections.defaultdict(list)
packets_per_action=collections.Counter(); packet_chars=collections.defaultdict(list)
runs=0
for f in (l.strip() for l in open(sys.argv[1])):
    stage_of={}; first_packet={}; ev=collections.defaultdict(list); inner=False
    for line in open(f, errors="replace"):
        try: r=json.loads(line)
        except Exception: continue
        if r.get("ts",0)<cut: continue
        a=r.get("action")
        if r.get("kind")=="packet":
            stage_of.setdefault(a, r.get("stage")); first_packet.setdefault(a, r["ts"])
            if stage_of.get(a) in INNER: packets_per_action[(f,a)]+=1; packet_chars[stage_of[a]].append(r.get("chars",0))
        if r.get("kind")=="command" and a in stage_of and stage_of[a] in INNER:
            ev[a].append(r); inner=True
    runs+=inner
    for a,rows in ev.items():
        s=stage_of[a]
        acc=[r for r in rows if r["verb"]=="complete" and r.get("exit")==0]
        if not acc: continue
        end=acc[0]["ts"]; rows=[r for r in rows if r["ts"]<=end]
        wall=end-first_packet[a]; stage_wall[s].append(wall)
        sms=sum(r.get("ms",0) for r in rows)/1000; script_share.append((sms,wall))
        for r in rows: verb_ms[(s,r["verb"])].append(r.get("ms",0)); verbs_per_action[r["verb"]]+=1
        ch=[r for r in rows if r["verb"]=="check"]; checks_per[len(ch)]+=1
        if ch: first_work[s].append(ch[0]["ts"]-first_packet[a])
        yes=[r for r in ch if r.get("exit")==0]
        if yes:
            gap_checkyes_complete.append(end-yes[-1]["ts"]); complete_after_yes_ms.append(acc[0].get("ms",0))
        else: complete_nocheck_ms.append(acc[0].get("ms",0))
def q(v): 
    v=sorted(v); return "n=%d med=%.1f p90=%.1f sum=%.0f"%(len(v), v[len(v)//2], v[int(len(v)*.9)], sum(v)) if v else "-"
print("runs",runs)
print("stage wall seconds:"); [print("  ",s,q(v)) for s,v in sorted(stage_wall.items())]
tw=sum(w for _,w in script_share); ts=sum(s for s,_ in script_share); print("script time share of inner wall: %.1f%% (%.0f of %.0f s)"%(100*ts/tw,ts,tw))
print("verb ms by stage:"); [print("  ",k,q([x/1000 for x in v])) for k,v in sorted(verb_ms.items()) if len(v)>20]
print("checks per accepted action", sorted(checks_per.items()))
print("gap last check yes -> complete (s)", q(gap_checkyes_complete))
print("complete ms after check yes", q([x/1000 for x in complete_after_yes_ms]), " without check", q([x/1000 for x in complete_nocheck_ms]))
print("packet prints per inner action", sorted(collections.Counter(packets_per_action.values()).items()))
print("packet chars by stage"); [print("  ",s,q(v)) for s,v in sorted(packet_chars.items())]
