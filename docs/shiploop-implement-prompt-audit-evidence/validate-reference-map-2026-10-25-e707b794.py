"""Check current plan provenance and historical references; this is not a runtime acceptance suite."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
E=Path(__file__).resolve().parent;R=E.parents[1];D='2026-10-25'
OUTPUT=E/f'reference-validation-{D}.json'
P=R/'docs/shiploop-implement-step-fix-plan-2026-10-17.md';J=R/'docs/shiploop-implement-prompt-audit-journal.md'
M=json.loads((E/f'reference-code-map-{D}.json').read_text());errors=[];cache={}
def check(ok,message):
 if not ok:errors.append(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def source(rev,path):
 key=(rev,path)
 if key not in cache:cache[key]=git('show',rev+':'+path)
 return cache[key]
def anchors(directory,m,date):
 lines=(directory/f'reference-code-excerpts-{date}.md').read_text().splitlines()
 for a in m['anchors']:
  raw=source(m['revision'],a['path']);part=''.join(raw.decode().splitlines(keepends=True)[a['start']-1:a['end']])
  check(0<a['start']<=a['end']<=len(raw.decode().splitlines()),'bad span '+a['id'])
  check(sha(raw)==a['source_sha256'],'source hash '+a['id'])
  check(part==a['excerpt'] and sha(part.encode())==a['excerpt_sha256'],'snippet hash '+a['id'])
  n=a['excerpt_document_line']-1
  check(lines[n]==f"## {a['id']} — {a['symbol']}",'heading link '+a['id'])
  check(lines[n+4].startswith('```'),'opening fence '+a['id'])
  check('\n'.join(lines[n+5:n+5+len(part.rstrip('\n').splitlines())])==part.rstrip('\n'),'printed excerpt '+a['id'])
check(git('rev-parse','HEAD').decode().strip()==M['revision'],'HEAD changed during refresh')
check(git('rev-parse','origin/main').decode().strip()==M['revision'],'origin/main changed during refresh')
anchors(E,M,D)
historic=[]
for directory in (E,E/'integration-c70a33f4'):
 h=json.loads((directory/'reference-code-map-2026-10-18.json').read_text());anchors(directory,h,'2026-10-18');historic.append({'revision':h['revision'],'anchors':len(h['anchors'])})
# Intentional source-only audit: preserve unrelated tracked edits and report them explicitly.
working_differences=sorted({a['path'] for a in M['anchors'] if (R/a['path']).read_bytes()!=source(M['revision'],a['path'])})
aids={a['id'] for a in M['anchors']};rids={r['id'] for r in M['recommendations']};tids=re.findall(r'^\| (T\d+) \|',P.read_text(),re.M)
check(len(aids)==len(M['anchors']),'duplicate anchor IDs')
check(rids=={f'R{i:02d}' for i in range(1,23)},'R01-R22 coverage')
check(len(M['considerations'])==8 and len(M['code_craft'])==14,'consideration/rule coverage')
check(len(tids)==len(set(tids))==52 and set(tids)=={f'T{i}' for i in range(1,53)},'T1-T52 coverage')
for g in M['recommendations']+M['considerations']+M['code_craft']:
 for a in g['anchors']:check(a in aids,'unknown anchor '+a)
 for t in g['tests']:check(t in tids,'unknown qualification '+t)
prefix='skills/shiploop/scripts/'
def module(name):return ast.parse(source(M['revision'],prefix+name+'.py'))
nav=module('shiploop_navigator');test=module('shiploop_test_loop');loop=module('shiploop_loops')
def functions(tree):return {n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
f=functions(nav);tf=functions(test)
for name in ('step_block','_step_proof_gate','_producer_blocks','_review_base_line','_improve_change_gate'):check(name in f,'missing current '+name)
for name in ('step_proof','_reused'):check(name in tf,'missing current '+name)
values={n.targets[0].id:ast.literal_eval(n.value) for n in nav.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('STATE_VERSION','IMPROVE_TRIVIAL_REVIEWS','HEAD_LIMIT','HEAD_REQUIRED_END','LOOK_BACK_COMMITS')}
check(values=={'STATE_VERSION':9,'IMPROVE_TRIVIAL_REVIEWS':1,'HEAD_LIMIT':20000,'HEAD_REQUIRED_END':19500,'LOOK_BACK_COMMITS':2},'current policy constants changed')
check('criterion_evidence' not in source(M['revision'],prefix+'shiploop_navigator.py').decode(),'lean port field status changed')
# Check exact implemented gate wiring rather than a nearby prompt.
navtext=source(M['revision'],prefix+'shiploop_navigator.py').decode();g=f['_improve_change_gate'];gtext='\n'.join(navtext.splitlines()[g.lineno-1:g.end_lineno]);check('test_loop.step_proof(' in gtext and 'improve-import' in gtext,'Improve re-proof wiring')
stage=module('shiploop_stage_spec');calls=[n for n in ast.walk(stage) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='Stage' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='implement'];check(len(calls)==1,'implement stage')
complete=next(k.value for k in calls[0].keywords if k.arg=='complete_runs');check('step-proof' in ast.literal_eval(complete),'missing step-proof completion gate')
counts={}
for name in ('chess','battleship'):
 d=json.loads((E/f'{name}-analysis-disposition-{D}.json').read_text());check(d['current_reference_revision']==M['revision'],'report reference drift '+name);data={}
 for item in d['source_files']:
  p=Path(item['path']);raw=p.read_bytes();check(sha(raw)==item['sha256'],'relocated report hash '+str(p));data[p.name]=json.loads(raw)
 found=set()
 for entry in d['findings']:
  val=data[entry['source']]
  for part in entry['json_pointer'].strip('/').split('/'):val=val[int(part)] if isinstance(val,list) else val[part]
  if 'reported_gap_sha256' in entry:check(sha(val.encode())==entry['reported_gap_sha256'],'gap hash '+entry['json_pointer'])
  else:check(val==entry['reported_finding'],'gap text '+entry['json_pointer'])
  found.add((entry['source'],entry['json_pointer']))
  for rid in entry['reference_ids']:check(rid in rids,'report recommendation '+rid)
  for tid in entry['tests']:check(tid in tids,'report qualification '+tid)
 expected={(file,f'/steps/{i}/gaps/{j}') for file,v in data.items() if 'steps' in v for i,s in enumerate(v['steps']) for j,_ in enumerate(s.get('gaps',[]))}
 check(found==expected and len(found)==d['count'],'report coverage '+name);counts[name]=len(found)
 if name=='chess':check(len(d['ranked_fixes'])==len(data['meta-chess.json']['fixes'])==8,'ranked fixes')
probe=json.loads((E/f'judge-zero-exit-probe-{D}.json').read_text());check(probe['revision']==M['revision'],'probe revision');check(probe['outcomes']['CASE-1']=='failed' and all(c['verdict']['counts']['failed']==1 and c['verdict']['status']=='passed' for c in probe['cases']),'recorded judge defect evidence')
advisor=json.loads((E/f'opus-main-refresh-{D}.json').read_text());check(advisor['exit']==0 and advisor['fallback'] is False and advisor['model_verification']=='verified' and advisor['served_model']=='claude-opus-5-5' and bool(advisor['text']),'advisor envelope')
checks=json.loads((E/f'checks-{D}/result.json').read_text());check(checks['total_tests']==329 and len(checks['tests'])==6 and all(t['exit_code']==0 for t in checks['tests']),'focused suite outcomes');check(checks['status']=='INCOMPLETE','preserve workspace-output caveat');check(checks['pre']['tracked_manifest_sha256']==checks['post']['tracked_manifest_sha256'],'suite source identity')
for t in checks['tests']:check(Path(t['log']).is_file(),'missing suite log')
files=[P,J,E/f'reference-code-map-{D}.md',E/f'reference-code-excerpts-{D}.md',E/f'opus-main-refresh-{D}.md'];links=0;fences={}
for p in files:
 raw=p.read_text();prose=[];inside=False;n=0
 for line in raw.splitlines():
  if line.startswith('```'):inside=not inside;n+=1
  elif not inside:prose.append(line)
 check(not inside,'unclosed fence '+str(p));fences[str(p.relative_to(R))]=n//2
 for m in re.finditer(r'\]\(([^\n)]+)\)','\n'.join(prose)):
  target=m.group(1).strip('<>')
  if target.startswith(('https://','http://','#','mailto:')):continue
  loc=target.split('#',1)[0];line=re.search(r':(\d+)$',loc);num=None
  if line:num=int(line.group(1));loc=loc[:line.start()]
  if not loc or '<' in loc or '>' in loc:continue
  f=Path(loc);f=f if f.is_absolute() else p.parent/f
  # This receipt is produced below, so its own link is valid on the first run too.
  check(f.exists() or f.resolve()==OUTPUT.resolve(),'broken link '+target)
  if num and f.is_file():check(0<num<=len(f.read_text().splitlines()),'bad linked line '+target)
  links+=1
result=dict(status='passed' if not errors else 'failed',revision=M['revision'],source_scope='committed main; unrelated local experiment edits excluded',working_tree_differences_in_anchored_files=working_differences,code_anchors=len(aids),source_files=len({a['path'] for a in M['anchors']}),historical_maps_revalidated=historic,recommendation_groups=len(rids),considerations=8,code_craft_rules=14,qualification_ids=len(tids),source_gap_entries=counts,ranked_chess_fixes=8,local_links_checked=links,fence_pairs=fences,static_assertions=values,focused_suites={'tests':329,'all_suites_exited_zero':True,'overall_receipt':'INCOMPLETE: unrelated non-exempt untracked experiment files appeared'},live_validation='not performed',visual_render='not inspected; prior policy denial not bypassed',errors=errors)
OUTPUT.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(bool(errors))
