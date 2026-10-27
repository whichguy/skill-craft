"""Validate audit provenance, source anchors, plan references and example syntax; no runtime tests."""
from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess

E=Path(__file__).resolve().parent
R=E.parents[1]
P=R/'docs/shiploop-implement-step-fix-plan-2026-10-17.md'
J=R/'docs/shiploop-implement-prompt-audit-journal.md'
M=json.loads((E/'reference-code-map-2026-10-18.json').read_text())
errors=[]
cache={}
def check(ok,message):
    if not ok:errors.append(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def source(rev,path):
    key=(rev,path)
    if key not in cache:cache[key]=git('show',rev+':'+path)
    return cache[key]
def verify_anchors(directory,m):
    ex=(directory/'reference-code-excerpts-2026-10-18.md').read_text().splitlines()
    for a in m['anchors']:
        raw=source(m['revision'],a['path'])
        lines=raw.decode().splitlines(keepends=True)
        check(0<a['start']<=a['end']<=len(lines),'invalid source span '+a['id'])
        excerpt=''.join(lines[a['start']-1:a['end']])
        check(sha(raw)==a['source_sha256'],'source hash '+a['id'])
        check(excerpt==a['excerpt'] and sha(excerpt.encode())==a['excerpt_sha256'],'excerpt hash '+a['id'])
        pos=a['excerpt_document_line']-1
        check(ex[pos]==f"## {a['id']} — {a['symbol']}",'excerpt link '+a['id'])
        check(ex[pos+4].startswith('```'),'excerpt fence '+a['id'])
        actual='\n'.join(ex[pos+5:pos+5+len(excerpt.rstrip('\n').splitlines())])
        check(actual==excerpt.rstrip('\n'),'rendered excerpt '+a['id'])
        if directory==E:
            check((R/a['path']).read_bytes()==raw,'working source drift '+a['path'])

check(git('rev-parse','HEAD').decode().strip()==M['revision'],'HEAD differs from reference revision')
check(git('rev-parse','origin/main').decode().strip()==M['revision'],'origin/main differs from reference revision')
check(git('branch','--show-current').decode().strip()=='main','current branch is not main')
check(not git('diff','--name-only') and not git('diff','--cached','--name-only'),'tracked source/index changes')
verify_anchors(E,M)
archive=E/'integration-c70a33f4'
historical=json.loads((archive/'reference-code-map-2026-10-18.json').read_text())
verify_anchors(archive,historical)

text=P.read_text()
tids=re.findall(r'^\| (T\d+) \|',text,re.M)
check(len(tids)==len(set(tids))==52,'T1-T52 unique inventory')
check(set(tids)=={f'T{i}' for i in range(1,53)},'T1-T52 coverage')
rids={g['id'] for g in M['recommendations']}
aids={a['id'] for a in M['anchors']}
check(len(aids)==len(M['anchors'])==105,'105 unique source anchors')
check(len(M['considerations'])==8 and len(M['code_craft'])==14 and len(rids)==22,'consideration/rule/recommendation inventory')
for g in M['considerations']+M['code_craft']+M['recommendations']:
    for a in g['anchors']:check(a in aids,'unknown anchor '+a)
    for t in g['tests']:check(t in tids,'unknown proposed test '+t)

# These static assertions keep the most consequential main-versus-integration claims honest.
prefix='skills/shiploop/scripts/'
def module(name):return ast.parse(source(M['revision'],prefix+name+'.py'))
nav=module('shiploop_navigator');loop=module('shiploop_loops');tests=module('shiploop_test_loop')
nav_funcs={n.name:n for n in nav.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
test_funcs={n.name for n in tests.body if isinstance(n,ast.FunctionDef)}
for name in ('step_block','_step_proof_gate','_producer_blocks','_review_base_line'):
    check(name not in nav_funcs,'main unexpectedly contains '+name)
check('step_proof' not in test_funcs and '_reused' not in test_funcs,'main unexpectedly has step proof/reuse')
nav_values={n.targets[0].id:ast.literal_eval(n.value) for n in nav.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='STATE_VERSION'}
check(nav_values.get('STATE_VERSION')==6,'main state version is not six')
stage=module('shiploop_stage_spec')
implement=[n for n in ast.walk(stage) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='Stage' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='implement']
check(len(implement)==1,'implement stage declaration')
complete=next(k.value for k in implement[0].keywords if k.arg=='complete_runs')
check(ast.literal_eval(complete)==('loop-terminal','lint-gate'),'main implement complete-runs changed')
calls=[n for n in ast.walk(nav_funcs['improve_start_contract']) if isinstance(n,ast.Call) for k in n.keywords if k.arg=='required_trivial_reviews' and isinstance(k.value,ast.Constant) and k.value.value==2]
check(len(calls)==1,'main Improve gate is not the inspected two-review binding')
nav_source=source(M['revision'],prefix+'shiploop_navigator.py').decode().splitlines()
gate=nav_funcs['_improve_change_gate'];gate_text='\n'.join(nav_source[gate.lineno-1:gate.end_lineno])
check('step_proof' not in gate_text and '"carry-forward"' in gate_text,'main Improve re-proof status changed')

counts={}
for name in ('chess','battleship'):
    d=json.loads((E/f'{name}-analysis-disposition-2026-10-18.json').read_text())
    check(d['current_reference_revision']==M['revision'],'stale report reference '+name)
    data={}
    for item in d['source_files']:
        raw=Path(item['path']).read_bytes()
        check(sha(raw)==item['sha256'],'retained report source '+item['path'])
        data[Path(item['path']).name]=json.loads(raw)
    found=set()
    for f in d['findings']:
        value=data[f['source']]
        for part in f['json_pointer'].strip('/').split('/'):
            value=value[int(part)] if isinstance(value,list) else value[part]
        if 'reported_gap_sha256' in f:check(sha(value.encode())==f['reported_gap_sha256'],'report gap '+f['json_pointer'])
        else:check(value==f['reported_finding'],'report finding '+f['json_pointer'])
        found.add((f['source'],f['json_pointer']))
        for ref in f['reference_ids']:check(ref in rids,'report recommendation '+ref)
        for t in f['tests']:check(t in tids,'report test '+t)
    expected={(file,f'/steps/{i}/gaps/{j}') for file,v in data.items() if 'steps' in v for i,s in enumerate(v['steps']) for j,_ in enumerate(s.get('gaps',[]))}
    check(found==expected and len(found)==d['count'],'complete report mapping '+name)
    counts[name]=len(found)
    if name=='chess':check(len(d['ranked_fixes'])==len(data['meta-chess.json']['fixes'])==8,'ranked Chess fixes')

files=[P,J,E/'reference-code-map-2026-10-18.md',E/'reference-code-excerpts-2026-10-18.md',archive/'reference-code-map-2026-10-18.md',archive/'reference-code-excerpts-2026-10-18.md',E/'opus-loop-direction-2026-10-18.md']
links=0;fences={}
for f in files:
    content=f.read_text();number=sum(bool(re.match(r'^```',line)) for line in content.splitlines())
    check(number%2==0,'unclosed fence '+str(f));fences[str(f.relative_to(R))]=number//2
    prose=[];in_fence=False
    for line in content.splitlines():
        if re.match(r'^```',line):
            in_fence=not in_fence
        elif not in_fence:
            prose.append(line)
    # Exact source excerpts can contain template links or links relative to their
    # original source file. They are data here, not links in this document.
    for match in re.finditer(r'\]\(([^\n)]+)\)','\n'.join(prose)):
        target=match.group(1).strip('<>')
        if target.startswith(('https://','http://','#','mailto:')):continue
        loc=target.split('#',1)[0];end=re.search(r':(\d+)$',loc);lineno=None
        if end:lineno=int(end.group(1));loc=loc[:end.start()]
        if not loc or '<' in loc or '>' in loc:continue
        p=Path(loc);p=p if p.is_absolute() else f.parent/p
        check(p.exists(),'broken link '+str(f)+': '+target)
        if lineno and p.is_file():check(0<lineno<=len(p.read_text().splitlines()),'invalid linked line '+target)
        links+=1
examples=0
for match in re.finditer(r"python3 - <<'PY'\n(.*?)\nPY",text,re.S):
    compile(match.group(1),'<plan-example>','exec');examples+=1
for match in re.finditer(r"python3 -B -c '([^']+)'",text):
    compile(match.group(1),'<plan-example>','exec');examples+=1
advisor=json.loads((E/'opus-loop-direction-2026-10-18.json').read_text())
check(advisor['exit']==0 and advisor['fallback'] is False and advisor['model_verification']=='verified' and advisor['served_model']=='claude-opus-5-5' and bool(advisor['text']),'advisor envelope verification')
result=dict(status='passed' if not errors else 'failed',revision=M['revision'],rebase='main already up to date with fetched origin/main',code_anchors=len(M['anchors']),source_files=len({a['path'] for a in M['anchors']}),historical_anchors_revalidated=len(historical['anchors']),considerations=8,code_craft_rules=14,recommendation_groups=22,proposed_test_ids=len(tids),source_gap_entries=counts,ranked_chess_fixes=8,local_links_checked=links,fence_pairs=fences,python_examples_syntax_checked=examples,static_main_assertions='state v6; absent step proof/shared renderer/reuse; implement loop+lint; Improve gate two and carry-forward-only re-proof',runtime_tests='not run in this refresh; plan/evidence only',visual_render='not inspected; prior browser policy denial not bypassed',errors=errors)
(E/'reference-validation-2026-10-18.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(bool(errors))
