import json,sys,re,os,collections
def load(p):
    try: t=open(p,errors='replace').read()
    except Exception: return None
    m=re.search(r"```shiploop-state\n(.*?)\n```",t,re.S)
    if not m: return None
    try: return json.loads(m.group(1))
    except Exception: return None
seen=set(); late=[]; early=0; multi_items_with_sb=0
for d in open(sys.argv[1]).read().split():
    rd=d+'/results'
    rs=[]
    for f in os.listdir(rd):
        if not f.endswith('.md'): continue
        j=load(rd+'/'+f)
        if j: rs.append((os.path.getmtime(rd+'/'+f),j,rd+'/'+f))
    if not rs: continue
    rid=rs[0][1].get('run_id')
    if rid in seen: continue
    seen.add(rid)
    rs.sort(key=lambda x:x[0])
    byitem=collections.defaultdict(list)
    for t,j,p in rs:
        if j.get('workitem'): byitem[j['workitem']].append((t,j,p))
    for wi,ev in byitem.items():
        docs_since_plan=0; nsteps=0
        for t,j,p in ev:
            st=j['stage']; res=j.get('result',{}); oc=res.get('outcome')
            if st=='step-plan' and oc=='done': docs_since_plan=0; nsteps=len(res.get('steps') or [])
            elif st=='document' and oc in('done',): docs_since_plan+=1
            elif oc=='send-back' and st in('implement','test','document','test-spec','validate-existing'):
                if docs_since_plan>=1: late.append((d,wi,st,nsteps,docs_since_plan,(res.get('summary') or res.get('headline') or '')[:260],p))
                else: early+=1
print('send-backs before any step committed:',early,' after >=1 step committed:',len(late))
for x in late: print('\n',x[0].replace('/Users/dadleet/',''),x[1],'stage',x[2],'steps',x[3],'done-steps',x[4],'\n   ',x[5],'\n   ',x[6])
