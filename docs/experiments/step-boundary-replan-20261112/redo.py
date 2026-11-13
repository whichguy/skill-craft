import json,sys,re,os,collections
def load(p):
    try: t=open(p,errors='replace').read()
    except Exception: return None
    m=re.search(r"```shiploop-state\n(.*?)\n```",t,re.S)
    if not m: return None
    try: return json.loads(m.group(1))
    except Exception: return None
seen=set(); boundaries=0; cf_mid=0; cf_mid_replace=0; item_minutes=[]
rows=[]
for d in open(sys.argv[1]).read().split():
    rd=d+'/results'; ev=[]
    for f in os.listdir(rd):
        j=load(rd+'/'+f) if f.endswith('.md') else None
        if j: ev.append((os.path.getmtime(rd+'/'+f),j))
    if not ev: continue
    rid=ev[0][1].get('run_id')
    if rid in seen: continue
    seen.add(rid); ev.sort(key=lambda x:x[0])
    byitem=collections.OrderedDict()
    for t,j in ev:
        if j.get('workitem'): byitem.setdefault(j['workitem'],[]).append((t,j))
    keys=list(byitem)
    for i,(wi,e) in enumerate(byitem.items()):
        plans=[j for t,j in e if j['stage']=='step-plan' and j['result'].get('outcome')=='done']
        if plans: boundaries+=max(0,len(plans[-1]['result'].get('steps') or [])-1)
        for t,j in e:
            if j['stage']=='carry-forward' and j['result'].get('outcome')=='done' and i<len(keys)-1:
                cf_mid+=1; cf_mid_replace+= 'work_items' in j['result']
        docs=0
        for k,(t,j) in enumerate(e):
            st=j['stage']; oc=j['result'].get('outcome')
            if st=='step-plan' and oc=='done': docs=0
            elif st=='document' and oc=='done': docs+=1
            elif oc=='send-back' and docs>=1 and st in('implement','test','document'):
                # redo: time from send-back to the docs-th document after the next step-plan
                n=0; tend=None; seenplan=False
                for t2,j2 in e[k+1:]:
                    if j2['stage']=='step-plan' and j2['result'].get('outcome')=='done': seenplan=True; continue
                    if seenplan and j2['stage']=='document' and j2['result'].get('outcome')=='done':
                        n+=1
                        if n==docs: tend=t2; break
                rows.append((d.replace('/Users/dadleet/',''),wi,docs,round((tend-t)/60,1) if tend else None, round((e[-1][0]-e[0][0])/60,1)))
print('step boundaries (a later step remains):',boundaries)
print('carry-forwards with a later item:',cf_mid,' of which replaced the queue:',cf_mid_replace)
for r in rows: print(r)
