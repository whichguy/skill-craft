import os, sys, json, subprocess, pathlib, hashlib, stat, datetime, re, time
R=pathlib.Path('/Users/dadleet/src/skill-craft-r19-20261115')
E=pathlib.Path(__file__).parent
HEAD='053195ab37d5c9830d3d14a82ebcbf3e90a7505c'
DEADLINE=datetime.datetime.fromisoformat('2026-11-16T02:23:14+00:00').timestamp()
CMDS=[['python3','-B','test/'+n+'.test.py'] for n in ['shiploop-loops','shiploop-e2e-fidelity','shiploop-callback-contract','shiploop-actual-improve-cli','shiploop-rehydration','shiploop-head-order','shiploop-packet-bounds','improve-runtime']]+[['ruff','check','--no-cache','--select','F,E9','skills/shiploop/scripts/shiploop_loops.py','test/shiploop-loops.test.py','test/shiploop-e2e-fidelity.test.py'],['git','-C',str(R),'diff','--check','4ec9ac4bb7425724f41cf3abd5e1776e8fdbd596','HEAD','--','skills/shiploop/scripts/shiploop_loops.py','test/shiploop-loops.test.py','test/shiploop-e2e-fidelity.test.py','changes/shiploop/r19-run-owned-loop-state.md']]
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*args): return subprocess.check_output(['git','-C',str(R),*args])
def write(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def snap(label):
    d=E/label; d.mkdir(exist_ok=False)
    h=git('rev-parse','HEAD').decode().strip(); status=git('status','--porcelain=v1','-z'); ignored=git('status','--porcelain=v1','--ignored','--untracked-files=all','-z')
    (d/'status.z').write_bytes(status); (d/'status-ignored.z').write_bytes(ignored)
    names=git('ls-files','-z').split(b'\0'); inv=[]
    for n in names:
        if not n: continue
        p=R/os.fsdecode(n)
        try:
            s=p.lstat(); b=os.fsencode(os.readlink(p)) if stat.S_ISLNK(s.st_mode) else p.read_bytes()
            inv.append({'path':os.fsdecode(n),'mode':stat.S_IMODE(s.st_mode),'type':'symlink' if stat.S_ISLNK(s.st_mode) else 'file','sha256':hashlib.sha256(b).hexdigest()})
        except FileNotFoundError: inv.append({'path':os.fsdecode(n),'missing':True})
    write(d/'tracked-inventory.json',inv)
    x={'head':h,'status_hex':status.hex(),'ignored_status_hex':ignored.hex(),'inventory_sha256':hashlib.sha256((d/'tracked-inventory.json').read_bytes()).hexdigest(),'timestamp':now()}
    write(d/'identity.json',x)
    if label=='before':
        (E/'preexisting-ignored-paths.z').write_bytes(git('ls-files','--others','--ignored','--exclude-standard','-z'))
        ok=h==HEAD and not status
    else:
        before=json.loads((E/'before/identity.json').read_text())
        ok=all(x[k]==before[k] for k in ['head','status_hex','ignored_status_hex','inventory_sha256']) and h==HEAD and not status
    print(json.dumps({'snapshot':label,'identity':x,'unchanged_clean':ok}),flush=True)
    return 0 if ok else 42

def run(i):
    d=E/('command-%02d'%i); d.mkdir(exist_ok=False); argv=CMDS[i-1]
    receipt={'index':i,'argv':argv,'cwd':str(R),'start':now(),'expected_head':HEAD,'env_overrides':{'PYTHONDONTWRITEBYTECODE':'1'},'stdout':str(d/'stdout.log'),'stderr':str(d/'stderr.log')}
    env=os.environ.copy(); env['PYTHONDONTWRITEBYTECODE']='1'
    try:
        with (d/'stdout.log').open('wb') as out,(d/'stderr.log').open('wb') as err:
            p=subprocess.Popen(argv,cwd=R,env=env,stdout=out,stderr=err,start_new_session=True)
            try: rc=p.wait(timeout=max(0.01,DEADLINE-time.time()))
            except subprocess.TimeoutExpired:
                import signal
                os.killpg(p.pid,signal.SIGKILL); p.wait(); rc=p.returncode; receipt['timeout']=True
        receipt['exit_code']=rc
        txt=(d/'stdout.log').read_text(errors='replace')+'\n'+(d/'stderr.log').read_text(errors='replace')
        counts=[int(n) for n in re.findall(r'^Ran (\d+) tests? in ',txt,re.M)]
        receipt['observed_unittest_counts']=counts
        receipt['terminal_ok']=bool(re.search(r'^OK\s*$',txt,re.M))
        receipt['skipped_required']=bool(re.search(r'^OK \(skipped=|\bskipped=\d+',txt,re.M))
        if receipt.get('timeout'): status='TIMEOUT'
        elif rc: status='FAIL'
        elif i<=8 and (not counts or not all(n>0 for n in counts) or not receipt['terminal_ok'] or receipt['skipped_required']): status='INCOMPLETE'
        else: status='PASS'
        receipt['status']=status
    except OSError as e: receipt.update(status='BLOCKED',error=str(e))
    receipt['end']=now(); write(d/'receipt.json',receipt)
    print(json.dumps(receipt),flush=True)
    return 0
if sys.argv[1]=='snapshot': sys.exit(snap(sys.argv[2]))
if sys.argv[1]=='run': sys.exit(run(int(sys.argv[2])))
