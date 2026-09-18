#!/usr/bin/env python3
from pathlib import Path
import concurrent.futures,hashlib,json,os,shutil,signal,subprocess,time
b=Path('/var/folders/_n/cth41tgs171367b_gghs0kgm0000gn/T/shiploop-probe-strategy-pulxuyar');wt=b/'worktree';runner_pid=9766
log=(b/'hermetic-all-derived.log').read_text();assert 'Ran 4 tests in 968.980s\n\nOK' in log
command=subprocess.check_output(['ps','-p',str(runner_pid),'-o','args='],text=True).strip();assert command=='bash test/shiploop.test.sh'
os.kill(runner_pid,signal.SIGSTOP)
# Freeze this owned runner tree before stopping it; never signal unrelated jobs.
pids=[]
def freeze(pid):
 if pid!=runner_pid:
  try:os.kill(pid,signal.SIGSTOP)
  except ProcessLookupError:return
 pids.append(pid)
 try:kids=subprocess.check_output(['pgrep','-P',str(pid)],text=True).split()
 except subprocess.CalledProcessError:kids=[]
 for child in kids:freeze(int(child))
freeze(runner_pid)
log=(b/'hermetic-all-derived.log').read_text();started=[line[4:] for line in log.splitlines() if line.startswith('==> test/')];assert started
inventory=subprocess.check_output(['bash','test/shiploop.test.sh','--list'],cwd=wt,text=True).splitlines()
assert started==inventory[:len(started)]
# Prior entries finished because the serial runner is fail-fast. Retest the active
# final entry even if it completed immediately before the parent was frozen.
completed=started[:-1];remaining=inventory[len(completed):]
assert len(inventory)==84 and len(completed)>=73
for pid in reversed(pids):
 try:os.kill(pid,signal.SIGTERM);os.kill(pid,signal.SIGCONT)
 except ProcessLookupError:pass
before={str(p.relative_to(wt)):hashlib.sha256(p.read_bytes()).hexdigest() for p in wt.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.suffix!='.pyc' and '/evidence/' not in str(p)}
record={'reason':'slow serial legacy walks; remaining catalog checks run in isolated copies of identical source','serial_completed':completed,'remaining':remaining,'inventory':inventory,'stopped_owned_pids':pids,'serial_log':'hermetic-all-derived.log','source_hashes':before}
(b/'hermetic-continuation.json').write_text(json.dumps(record,indent=2)+'\n')
# Long full-walk cases get their own lane; other cases share a lane sequentially.
groups=[[],[],[],[]]
for rel in remaining:
 if rel.endswith('shiploop-action-walk.test.py'):groups[0].append(rel)
 elif rel.endswith('shiploop-managed-walk.test.py'):groups[1].append(rel)
 else:groups[2 if len(groups[2])<=len(groups[3]) else 3].append(rel)

def run_group(index,tests):
 root=b/f'verify-copy-{index}'
 subprocess.run(['git','worktree','add','--detach',str(root),'004447fd395d1820332cf454c9f966c4c85f63fe'],cwd=wt,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 shutil.copytree(wt,root,dirs_exist_ok=True,ignore=shutil.ignore_patterns('.git','__pycache__','*.pyc','evidence'))
 for rel,digest in before.items():assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest,rel
 results=[]
 for rel in tests:
  started=time.monotonic();dest=b/('remaining-'+Path(rel).stem+'.log')
  with dest.open('wb') as out:
   try:r=subprocess.run(['python3','-B',rel],cwd=root,stdout=out,stderr=subprocess.STDOUT,timeout=2400);code=r.returncode;reason=None
   except subprocess.TimeoutExpired:code=None;reason='2400-second suite bound'
  result={'suite':rel,'exit_code':code,'reason':reason,'elapsed_seconds':round(time.monotonic()-started,3),'log':dest.name,'checkout':str(root)}
  results.append(result);(b/f'verify-copy-{index}-results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(result),flush=True)
 return results
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 results=[x for group in pool.map(lambda x:run_group(*x),enumerate(groups,1)) for x in group]
assert sorted(r['suite'] for r in results)==sorted(remaining)
record.update({'results':results,'status':'passed' if all(r['exit_code']==0 for r in results) else 'failed','completed_catalog_count':len(completed)+sum(r['exit_code']==0 for r in results)})
(b/'hermetic-continuation.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'status':record['status'],'completed_catalog_count':record['completed_catalog_count'],'remaining_count':len(remaining)}),flush=True)
raise SystemExit(0 if record['status']=='passed' else 1)
