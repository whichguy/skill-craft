import json
import re

RUNS='/Users/dadleet/e2e-runs/ratchet-reworded-20261121-08805f'
S=[('p3R-ticket-due-times-a','03-tests-1-1',{'A':[18,20,21,22,25,26,27,28,30,31,33,34],'B':[11,19,36],'C':[23]}),
('p3R-ticket-due-times-b','03-tests-1-1',{'A':[13,18,19,20,25],'B':[14],'C':[21]}),
('p1R-ticket-due-times','02-tests-1-1',{'A':[18,20,21,22,23,24,26,28],'B':[13],'C':[]}),
('p1R-ticket-assignment','02-tests-1-1',{'A':[19,22,25,26,28,29],'B':[31],'C':[14]}),
('p1R-stand-in-rules','02-tests-1-1',{'A':[14,15,19,21,23,24,25,27,28],'B':[16,17,20,22],'C':[11]})]
FAILRE=re.compile(r'not ok|✖|# fail [1-9]|ℹ fail [1-9]|\bFAIL\b|exit=[1-9]|^\w-\d+ [1-9] |Failing items [CU]|Failures \[.')
rows=[]
for run,ses,lab in S:
    d=f'{RUNS}/{run}/sessions/{ses}'
    with open(f'{RUNS}/{run}/run.json') as handle:
        record=json.load(handle)
    secs=next(s['seconds'] for s in record['sessions'] if s['label']==ses.split('-',1)[1])
    cmds=[];upd={}
    with open(d+'/events.jsonl') as handle:
        lines=handle.readlines()
    for l in lines:
        o=json.loads(l)
        if o['type']=='tool_call' and o['toolName']=='run_terminal_command': cmds.append((o['toolCallId'],o['rawInput']['command']))
        elif o['type']=='tool_call_update':
            r=o.get('rawOutput') or {}
            if r.get('type')=='command_execution': upd[o['toolCallId']]=(r.get('exit_code'),r.get('output_for_prompt',''))
    n=len(cmds); A=lab['A']
    ex=[upd[cmds[i-1][0]][0] for i in A]
    inout=[bool(FAILRE.search(upd[cmds[i-1][0]][1])) for i in A]
    rd=set();spec=plan=0
    for i,(cid,c) in enumerate(cmds,1):
        body=re.sub(r'^/bin/\w+ -lc ','',c)
        iswrite=bool(re.match(r'''^["']?\s*(mkdir -p [\w/ ]+\s+)?cat\s*>''',body)) or 'write_text' in body or 'writeFileSync' in body
        if iswrite: continue
        if re.search(r'\b(cat|sed|rg|grep|nl|head|tail|show)\b',body):
            for m in re.finditer(r'(?<![\w./-])((?:src|bin|scripts|docs)/[\w./-]*\w|README\.md)',body): rd.add(m.group(1))
        if re.search(r'ratchet/spec\.md|ratchet/\*|ratchet/build-\*',body) or 'ratchet/spec.md' in body: spec+=1
        if re.search(r'ratchet/plan\.md',body): plan+=1
    code=sorted(x for x in rd if x.startswith(('src/','bin/','scripts/')))
    docs=sorted(x for x in rd if x.startswith('docs/') or x=='README.md')
    firstA=A[0]; firstC=lab['C'][0] if lab['C'] else None
    firstAny=min(A+lab['B']+lab['C'])
    rows.append({'run':run,'secs':secs,'n':n,'runs':len(A)+len(lab['B'])+len(lab['C']),'a':len(A),'b':len(lab['B']),'c':len(lab['C']),'a_fail':sum(1 for e in ex if e!=0),'a_ok':sum(1 for e in ex if e==0),'a_inner':sum(inout),'firstA':firstA,'firstApct':round(100*firstA/n),'firstC':firstC,'firstCpct':round(100*firstC/n) if firstC else None,'firstAny':firstAny,'firstAnypct':round(100*firstAny/n),'code':len(code),'docs':len(docs),'spec':spec,'plan':plan,'ex':ex,'inout':inout,'A':A,'codefiles':code,'docfiles':docs})
for r in rows: print(r)
with open('/private/tmp/claude-501/-Users-dadleet-src-skill-craft/50835528-f438-4c91-9001-f1d0ee5b8f4d/scratchpad/parallel/act2.json','w') as handle:
    json.dump(rows,handle)
