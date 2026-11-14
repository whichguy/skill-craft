import json,sys,re,os,collections
def load(p):
    try: t=open(p,errors='replace').read()
    except Exception: return None
    m=re.search(r"```shiploop-state\n(.*?)\n```",t,re.S)
    if not m: return None
    try: return json.loads(m.group(1))
    except Exception: return None
seen=set(); runs=0
items=0; multi_step_items=0; steps_total=0
sb=collections.Counter(); sb_items=set()
cf=0; cf_replace=0; cf_replace_changed=0; cf_blocked=0
doc=0; doc_open=0
plan_revs=collections.Counter()
mtime_rows=[]
for d in open(sys.argv[1]).read().split():
    rd=d+'/results'
    rs=[load(rd+'/'+f) for f in os.listdir(rd) if f.endswith('.md')]
    rs=[r for r in rs if r]
    if not rs: continue
    rid=rs[0].get('run_id')
    if rid in seen: continue
    seen.add(rid); runs+=1
    sp=collections.defaultdict(list)
    for r in rs:
        st=r.get('stage'); wi=r.get('workitem'); res=r.get('result',{}); oc=res.get('outcome')
        if st=='step-plan' and oc=='done': sp[wi].append(len(res.get('steps') or []))
        if oc=='send-back': sb[st]+=1; sb_items.add((rid,wi))
        if st=='carry-forward' and oc=='done':
            cf+=1
            if 'work_items' in res: cf_replace+=1
        if st=='carry-forward' and oc=='blocked': cf_blocked+=1
        if st=='document' and oc=='done':
            doc+=1
            if res.get('assumptions'): doc_open+=1
    for wi,ns in sp.items():
        items+=1; plan_revs[len(ns)]+=1
        if max(ns)>1: multi_step_items+=1
        steps_total+=ns[-1]
print('runs',runs,'items',items,'items with >1 step',multi_step_items,'steps(final plans)',steps_total)
print('step-plan versions per item',dict(plan_revs))
print('send-backs by stage',dict(sb),'items with any send-back',len(sb_items))
print('carry-forward done',cf,'with work_items (queue replaced)',cf_replace,'blocked',cf_blocked)
print('document done',doc,'with open items',doc_open)
