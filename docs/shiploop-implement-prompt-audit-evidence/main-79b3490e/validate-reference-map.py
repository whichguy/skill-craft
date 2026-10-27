"""Verify pinned source, exact excerpts, plan/report coverage and locators; not live acceptance."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
N=Path(__file__).resolve().parent;E=N.parent;R=E.parents[1];OUT=N/'reference-validation.json'
M=json.loads((N/'reference-code-map.json').read_text());errors=[];cache={}
def check(ok,why):
 if not ok:errors.append(why)
def sha(x):return hashlib.sha256(x).hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(R),*a])
def src(p):
 if p not in cache:cache[p]=git('show',M['revision']+':'+p)
 return cache[p]
head=git('rev-parse','HEAD').decode().strip();remote=git('rev-parse','origin/main').decode().strip()
check(head==M['revision'],'checkout differs from audited main');check(remote==M['revision'],'origin/main differs from audited main')
lines=(N/'reference-code-excerpts.md').read_text().splitlines();aids=set()
for a in M['anchors']:
 check(a['id'] not in aids,'duplicate anchor '+a['id']);aids.add(a['id'])
 raw=src(a['path']);part=''.join(raw.decode().splitlines(keepends=True)[a['start']-1:a['end']]);n=a['excerpt_document_line']-1
 check(sha(raw)==a['source_sha256'],'file hash '+a['id']);check(part==a['excerpt'] and sha(part.encode())==a['excerpt_sha256'],'excerpt '+a['id'])
 check(lines[n]==f"## {a['id']} — {a['symbol']}",'anchor heading '+a['id'])
 check(lines[n+4].startswith('```'),'fence '+a['id']);check('\n'.join(lines[n+5:n+5+len(part.rstrip('\n').splitlines())])==part.rstrip('\n'),'printed source '+a['id'])
P=R/'docs/shiploop-implement-step-fix-plan-2026-10-17.md';tids=re.findall(r'^\| (T\d+) \|',P.read_text(),re.M);rids={r['id'] for r in M['recommendations']}
check(rids=={f'R{i:02d}' for i in range(1,23)},'all recommendation IDs');check(len(tids)==len(set(tids))==52 and set(tids)=={f'T{i}' for i in range(1,53)},'all qualification IDs');check(len(M['considerations'])==8 and len(M['code_craft'])==14,'consideration and rule coverage')
for x in M['recommendations']+M['considerations']+M['code_craft']:
 check(bool(x['anchors']),'unanchored '+x['id'])
 for k in x['anchors']:check(k in aids,'unknown anchor '+k)
 for k in x['tests']:check(k in tids,'unknown qualification '+k)
check(next(r for r in M['recommendations'] if r['id']=='R08')['status']=='partial','do not call R08 fully open or fully fixed')
counts={}
for name in ['chess','battleship']:
 d=json.loads((N/f'{name}-analysis-disposition.json').read_text());check(d['current_reference_revision']==M['revision'],'report revision '+name);data={}
 for x in d['source_files']:
  p=Path(x['path']);raw=p.read_bytes();check(sha(raw)==x['sha256'],'retained report hash '+p.name);data[p.name]=json.loads(raw)
 seen=set()
 for x in d['findings']:
  val=data[x['source']]
  for bit in x['json_pointer'].strip('/').split('/'):val=val[int(bit)] if isinstance(val,list) else val[bit]
  check(sha(val.encode())==x['reported_gap_sha256'] if 'reported_gap_sha256' in x else val==x['reported_finding'],'report finding '+x['json_pointer']);seen.add((x['source'],x['json_pointer']))
  for k in x['reference_ids']:check(k in rids,'report recommendation '+k)
 expected={(file,f'/steps/{i}/gaps/{j}') for file,v in data.items() if 'steps' in v for i,s in enumerate(v['steps']) for j,_ in enumerate(s.get('gaps',[]))}
 check(seen==expected and len(seen)==d['count'],'complete report '+name);counts[name]=len(seen)
 if name=='chess':check(len(d['ranked_fixes'])==len(data['meta-chess.json']['fixes'])==8,'ranked fixes')
probe=json.loads((N/'judge-current-probe.json').read_text());check(probe['revision']==M['revision'],'probe revision');check([x['verdict']['status'] for x in probe['cases']]==['failed','failed','passed','passed','passed','passed'],'judge probe results');check(probe['stale_receipt']['reused'] and probe['stale_receipt']['returned_status']=='passed','old receipt reproduction')
nav=src('skills/shiploop/scripts/shiploop_navigator.py').decode();tree=ast.parse(nav)
values={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('STATE_VERSION','IMPROVE_TRIVIAL_REVIEWS','HEAD_LIMIT','HEAD_REQUIRED_END')}
check(values=={'STATE_VERSION':9,'IMPROVE_TRIVIAL_REVIEWS':1,'HEAD_LIMIT':20000,'HEAD_REQUIRED_END':19500},'current constants');check('_check_producer_bounds(child["stage"], final_result)' in nav,'revised Improve result bounds')
links=0
for p in [P,R/'docs/shiploop-implement-prompt-audit-journal.md',N/'reference-code-map.md',N/'reference-code-excerpts.md']:
 inside=False;prose=[]
 for line in p.read_text().splitlines():
  if line.startswith('```'):inside=not inside
  elif not inside:prose.append(line)
 check(not inside,'unclosed fence '+str(p))
 for m in re.finditer(r'\]\(([^\n)]+)\)','\n'.join(prose)):
  target=m.group(1).strip('<>')
  if target.startswith(('https://','http://','#','mailto:')):continue
  target=target.split('#',1)[0];num=None;match=re.search(r':(\d+)$',target)
  if match:num=int(match.group(1));target=target[:match.start()]
  if not target or '<' in target:continue
  q=Path(target);q=q if q.is_absolute() else p.parent/q
  check(q.exists() or q.resolve()==OUT,'broken link '+target)
  if num and q.is_file():check(0<num<=len(q.read_text().splitlines()),'line outside file '+target)
  links+=1
result={'status':'passed' if not errors else 'failed','revision':M['revision'],'head':head,'origin_main':remote,'scope':'committed source provenance, not working-tree or live acceptance','anchors':len(aids),'source_files':len(cache),'recommendations':len(rids),'considerations':8,'code_craft_rules':14,'qualification_ids':52,'source_gap_entries':counts,'ranked_chess_fixes':8,'local_links_checked':links,'static_assertions':values,'changed_prior_excerpts':M['changed_excerpt_ids'],'errors':errors}
OUT.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));raise SystemExit(bool(errors))
