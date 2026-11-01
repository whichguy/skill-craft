"""Replay four candidate rules for a step Proof that runs tests the test stage has not written yet, when it names no test
file (read-only; step-plan review 2026-11-01).  Usage: python3 -I replay_proofs.py TRACES.txt OUT.jsonl

N1 the Proof is a focused command; N2 it names a focused test ID; N3 it is a regression command while the step's
criteria are named by a focused command; N4 it names the stem of a new test file the item declares (absent
expectation) and no earlier step declares.  Each step is linked to its implement outcome (done, send-back, none).
None of them is precise enough to gate on (see README).
"""
import json, os, re, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "skills", "shiploop", "scripts"))
import shiploop_item_scope as scope
def norm(c): return " ".join(str(c).split())
def state_of(run):
    t=open(os.path.join(run,'state.md')).read()
    m=re.search(r"```shiploop-state\n(.*?)\n```",t,re.S); return json.loads(m.group(1))
def res_of(run, st, action):
    r=st.get('accepted',{}).get(action)
    if isinstance(r,dict): return r
    f=os.path.join(run,'results',action+'.md')
    if os.path.exists(f):
        m=re.search(r"```shiploop-state\n(.*?)\n```",open(f).read(),re.S)
        if m:
            try: return json.loads(m.group(1)).get('result',{})
            except Exception: pass
    return {}
def new_test_paths(plan):
    absent=set(); known=set()
    for e in plan.get('expectations') or []:
        for p in e.get('paths') or []:
            (absent if e.get('state')=='absent' else known).add(p)
    return [p for p in (plan.get('paths') or []) if scope.classify(p)=='test' and p in absent and p not in known]
def stem(p):
    b=os.path.basename(p); return b.split('.')[0]
def rules(plan, idx):
    steps=plan.get('steps') or []; s=steps[idx]; proof=norm(s.get('proof',''))
    tcs=plan.get('test_commands') or []
    foc=[t for t in tcs if t.get('suite')=='focused']; reg=[t for t in tcs if t.get('suite')=='regression' or t.get('regression')]
    focused_crit={c for t in foc for c in (t.get('criteria') or [])}
    step_crit=set(s.get('criteria') or [])
    ids=[i for t in foc for i in (t.get('ids') or [])]
    wordset=set(re.findall(r"[A-Za-z0-9_]+", proof))
    earlier={p for st_ in steps[:idx] for p in (st_.get('paths') or [])}
    out=[]
    if any(proof==norm(t['command']) for t in foc): out.append('N1')
    if any(re.search(r'(?<![A-Za-z0-9_-])'+re.escape(i)+r'(?![A-Za-z0-9_])', proof) for i in ids): out.append('N2')
    if any(proof==norm(t['command']) for t in reg) and step_crit & focused_crit: out.append('N3')
    stems={stem(p):p for p in new_test_paths(plan) if p not in earlier}
    if any(w in stems for w in wordset): out.append('N4')
    return out
rows=[]
for p in open(sys.argv[1]).read().split():
    run=os.path.dirname(p)
    try: st=state_of(run)
    except Exception: continue
    hist=st.get('history',[])
    for i,h in enumerate(hist):
        if h.get('stage')!='step-plan' or h.get('outcome')!='done': continue
        plan=st.get('accepted',{}).get(h['action'])
        if not isinstance(plan,dict) or not plan.get('steps'): continue
        # walk implements until next step-plan of same item
        k=0; outcomes={}
        for h2 in hist[i+1:]:
            if h2.get('workitem')!=h.get('workitem'): continue
            if h2.get('stage')=='step-plan': break
            if h2.get('stage')=='implement':
                if h2.get('outcome')=='done': outcomes[k]='done'; k+=1
                elif h2.get('outcome')=='send-back':
                    outcomes[k]='send-back:'+str(res_of(run,st,h2['action']).get('headline') or '')[:80]; break
            if h2.get('stage') in ('test-spec','test') and h2.get('outcome')=='send-back': 
                outcomes.setdefault('other', h2['stage']+' send-back'); break
        for idx,s in enumerate(plan['steps']):
            rows.append({"run":run,"item":h.get('workitem'),"step":s.get('id'),"proof":s.get('proof'),"rules":rules(plan,idx),
                         "impl":outcomes.get(idx),"other":outcomes.get('other')})
with open(sys.argv[2],"w") as h:
    for r in rows: h.write(json.dumps({**r,"run":r["run"].replace("/Users/dadleet/","~/"),"proof":(r["proof"] or "")[:160]},sort_keys=True)+"\n")
from collections import Counter
print("steps",len(rows))
for rule in ('N1','N2','N3','N4'):
    hit=[r for r in rows if rule in r['rules']]
    c=Counter(('send-back' if (r['impl'] or '').startswith('send-back') else (r['impl'] or 'none')) for r in hit)
    print(rule, len(hit), dict(c))
print("implement send-backs total:", sum(1 for r in rows if (r['impl'] or '').startswith('send-back')))
for r in rows:
    if (r['impl'] or '').startswith('send-back'):
        print(f"  {','.join(r['rules']) or '-':10} {r['step']} {r['impl'][:100]} | proof: {(r['proof'] or '')[:70]}")
