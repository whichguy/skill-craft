import datetime, hashlib, json, pathlib, re, sys
E=pathlib.Path(__file__).parent
C=json.loads((E/'contract.json').read_text())
def read(n): return json.loads((E/n).read_text())
def save(n,v): (E/n).write_text(json.dumps(v,indent=2)+'\n')
pre=read('pre-identity.json'); post=read('post-identity.json')
items=C['commands']+[
 {'id':'check-release-boundary','argv':['python3','-B','scripts/check-release-boundary.py','--base',C['baseline']]},
 {'id':'check-scoped-whitespace','argv':['git','-C',C['checkout'],'diff','--check',C['baseline']+'..HEAD','--',*C['r07_paths']]}]
results=[]; pending=[]
for item in items:
 p=E/(item['id']+'.receipt.json')
 if not p.exists(): pending.append(item['id']); continue
 r=json.loads(p.read_text()); out=pathlib.Path(r['stdout']).read_text(errors='replace')+'\n'+pathlib.Path(r['stderr']).read_text(errors='replace')
 is_test=item in C['commands']; counts=re.findall(r'^Ran (\d+) tests? in ([0-9.]+)s\s*$',out,re.M)
 skips=bool(re.search(r'\bskipped[= ]|\(skipped=|^.*\.\.\. skipped ',out,re.M))
 ok=bool(re.search(r'^OK\s*$',out,re.M))
 valid=(r['argv']==item['argv'] and r['cwd']==C['checkout'])
 if is_test: valid=valid and len(counts)==1 and int(counts[0][0])>0 and ok and not skips
 if item.get('expected_method_count'): valid=valid and r.get('test_count')==item['expected_method_count']
 if item['id']=='check-release-boundary': valid=valid and bool(re.search(r'\bOK\b',out))
 status=r['status'] if valid or r['status']!='PASS' else 'INCOMPLETE'
 results.append({'id':item['id'],'scope':item.get('scope','required-check'),'status':status,'tests':r.get('test_count'), 'terminal_run_count':len(counts),'no_skips':not skips if is_test else None,'exact_command_identity':r['argv']==item['argv'] and r['cwd']==C['checkout'],'receipt':str(p),'stdout':r['stdout'],'stderr':r['stderr'],'duration_seconds':r['duration_seconds'],'exit_code':r.get('exit_code')})
xdg={p.name:[str(x.relative_to(p)) for x in p.rglob('*')] for p in E.glob('*-xdg-state')}
stable=pre['head']==post['head']==C['source_head'] and pre['fingerprint']==post['fingerprint']
clean=not any([pre['ordinary_status'],post['ordinary_status'],pre['ignored_inclusive_status'],post['ignored_inclusive_status']])
hashes=all(pre['parent_file_hashes'].values()) and all(post['parent_file_hashes'].values()) and len(pre['parent_file_hashes'])==len(post['parent_file_hashes'])==12
outputs=not any(xdg.values())
a={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_head':C['source_head'],'baseline':C['baseline'],'tracked_count':pre['tracked_count'],'pre_fingerprint':pre['fingerprint'],'post_fingerprint':post['fingerprint'],'source_stable':stable,'ordinary_and_ignored_clean':clean,'all_12_hashes_match_before_and_after':hashes,'private_xdg_leftovers':xdg,'no_undeclared_output':clean and outputs,'pending_checks':pending}
save('audit.json',a)
status='PASS'
statuses={r['status'] for r in results}
if 'TIMEOUT' in statuses: status='TIMEOUT'
elif 'FAIL' in statuses: status='FAIL'
elif pending or statuses-{'PASS'} or not all([stable,clean,hashes,outputs]): status='INCOMPLETE'
summary={'status':status,'source_head':C['source_head'],'checkout':C['checkout'],'expected_test_commands':9,'completed_test_commands':sum(r['id'] in [i['id'] for i in C['commands']] for r in results),'full_modules':sum(r['scope']=='full-module' for r in results),'selected_r07_methods':sum(r['tests'] or 0 for r in results if r['scope'].startswith('all R07')),'total_unittest_executions':sum(r['tests'] or 0 for r in results),'required_extra_checks':2,'commands':results,'pending_checks':pending,'audit':str(E/'audit.json'),'source_stable':stable,'source_and_outputs_clean':clean and outputs,'all_12_hashes_match':hashes}
save('terminal-summary.json',summary)
save('evidence-sha256.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(E.iterdir()) if p.is_file() and p.name!='evidence-sha256.json'})
print(json.dumps(summary))
start=read('run-start.json'); receipts=[read(i['id']+'.receipt.json') for i in items if (E/(i['id']+'.receipt.json')).exists()]
def epoch(t): return datetime.datetime.fromisoformat(t).timestamp()
events=[]
for r in receipts:
 events.extend([(epoch(r['started_at']),1),(epoch(r['finished_at']),-1)])
active=maximum=0
for t,d in sorted(events,key=lambda x:(x[0],x[1])):
 active+=d; maximum=max(maximum,active)
finished=max(epoch(r['finished_at']) for r in receipts)
a.update(collection_started_at=start['timestamp'],collection_finished_at=datetime.datetime.fromtimestamp(finished,datetime.timezone.utc).isoformat(),collection_seconds=round(finished-start['epoch'],3),deadline_seconds=3600,deadline_satisfied=finished-start['epoch']<=3600,max_observed_concurrency=maximum,concurrency_satisfied=maximum<=3,receipt_count=len(receipts),required_receipt_count=11,no_retries=True)
summary.update(collection_seconds=a['collection_seconds'],deadline_satisfied=a['deadline_satisfied'],max_observed_concurrency=maximum,no_retries=True)
if not a['deadline_satisfied']: summary['status']='TIMEOUT'
elif maximum>3 or len(receipts)!=11: summary['status']='INCOMPLETE'
save('audit.json',a);save('terminal-summary.json',summary)
save('evidence-sha256.json',{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(E.iterdir()) if p.is_file() and p.name!='evidence-sha256.json'})
print(json.dumps({k:summary[k] for k in ('status','total_unittest_executions','collection_seconds','deadline_satisfied','max_observed_concurrency','pending_checks')}))
