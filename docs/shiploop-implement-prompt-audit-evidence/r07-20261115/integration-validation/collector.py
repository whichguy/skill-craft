import concurrent.futures, datetime, hashlib, json, os, pathlib, re, stat, subprocess, sys, time
E=pathlib.Path(__file__).parent
C=json.loads((E.parent/'integration-validation-contract.json').read_text())
R=pathlib.Path(C['checkout'])
def save(name,value): (E/name).write_text(json.dumps(value,indent=2)+'\n')
def stamp(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*args): return subprocess.run(['git','-C',str(R),*args],capture_output=True,check=True).stdout

def audit(label):
    inventory=[]
    for raw in git('ls-files','-z').split(b'\0'):
        if not raw: continue
        name=os.fsdecode(raw); p=R/name
        if p.is_symlink(): data=os.fsencode(os.readlink(p)); kind='symlink'
        elif p.is_file(): data=p.read_bytes(); kind='file'
        else: data=b''; kind='missing'
        inventory.append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'mode':oct(stat.S_IMODE(p.lstat().st_mode)) if p.exists() or p.is_symlink() else None,'kind':kind})
    inventory.sort(key=lambda x:x['path'])
    save(label+'-tracked-inventory.json',inventory)
    ordinary=git('status','--porcelain=v1','--untracked-files=all').decode()
    inclusive=git('status','--porcelain=v1','--untracked-files=all','--ignored=matching').decode()
    (E/(label+'-status.txt')).write_text(ordinary)
    (E/(label+'-status-ignored.txt')).write_text(inclusive)
    source=json.loads((E.parent/'integrated-source.json').read_text())
    matches={n: hashlib.sha256((R/n).read_bytes()).hexdigest()==h for n,h in source['files'].items()}
    result={'timestamp':stamp(),'head':git('rev-parse','HEAD').decode().strip(),'tracked_count':len(inventory),'fingerprint':hashlib.sha256(json.dumps(inventory,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'ordinary_status':ordinary,'ignored_inclusive_status':inclusive,'parent_file_hashes':matches}
    save(label+'-identity.json',result)
    return result

def run(item):
    name=item['id']; argv=item['argv']; home=E/(name+'-xdg-state'); home.mkdir(exist_ok=True)
    env=os.environ.copy()
    for key in ('UNTIL_LOOP_STATE_DIR','SHIPLOOP_KEEPALIVE_HOME'): env.pop(key,None)
    env.update(PYTHONDONTWRITEBYTECODE='1',SHIPLOOP_PROGRESS='off',XDG_STATE_HOME=str(home))
    receipt={'id':name,'argv':argv,'cwd':str(R),'environment':{'PYTHONDONTWRITEBYTECODE':'1','SHIPLOOP_PROGRESS':'off','XDG_STATE_HOME':str(home),'unset':['UNTIL_LOOP_STATE_DIR','SHIPLOOP_KEEPALIVE_HOME']},'started_at':stamp(),'stdout':str(E/(name+'.stdout.log')),'stderr':str(E/(name+'.stderr.log'))}
    start=time.monotonic(); started=json.loads((E/'run-start.json').read_text())['epoch']; remaining=3600-(time.time()-started)
    status='BLOCKED'
    try:
        with open(receipt['stdout'],'wb') as out,open(receipt['stderr'],'wb') as err:
            proc=subprocess.Popen(argv,cwd=R,env=env,stdout=out,stderr=err,start_new_session=True)
            receipt['pid']=proc.pid
            try: rc=proc.wait(timeout=max(0.01,remaining))
            except subprocess.TimeoutExpired:
                import signal
                os.killpg(proc.pid,signal.SIGTERM)
                try: proc.wait(timeout=5)
                except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.wait()
                rc=proc.returncode; status='TIMEOUT'
        receipt['exit_code']=rc
        output=pathlib.Path(receipt['stdout']).read_text(errors='replace')+'\n'+pathlib.Path(receipt['stderr']).read_text(errors='replace')
        if status!='TIMEOUT':
            if name.startswith('check-'):
                status='PASS' if rc==0 and (name!='check-release-boundary' or re.search(r'\bOK\b',output)) else ('FAIL' if rc else 'INCOMPLETE')
            else:
                counts=re.findall(r'^Ran (\d+) tests? in ([0-9.]+)s\s*$',output,re.M)
                receipt['unittest_terminal_runs']=[{'tests':int(n),'seconds':float(t)} for n,t in counts]
                receipt['test_count']=sum(int(n) for n,t in counts)
                status='FAIL' if rc or re.search(r'^FAILED\b',output,re.M) else ('PASS' if len(counts)==1 and int(counts[0][0])>0 and re.search(r'^OK\s*$',output,re.M) and not re.search(r'\bskipped[= ]|\(skipped=',output) else 'INCOMPLETE')
        leftovers=[str(p.relative_to(home)) for p in home.rglob('*')]
        receipt['private_xdg_leftovers']=leftovers
        if leftovers and status=='PASS': status='INCOMPLETE'
    except Exception as exc: receipt['collector_error']=repr(exc)
    receipt.update(status=status,finished_at=stamp(),duration_seconds=round(time.monotonic()-start,3))
    save(name+'.receipt.json',receipt)
    print(json.dumps(receipt),flush=True)
    return receipt

mode=sys.argv[1]
if mode=='pre':
    save('run-start.json',{'epoch':time.time(),'timestamp':stamp(),'deadline_seconds':3600,'max_concurrency':3,'retry_policy':'none'})
    (E/'test-README.md').write_bytes((R/'test/README.md').read_bytes())
    save('contract.json',C)
    a=audit('pre'); print(json.dumps(a))
    if a['head']!=C['source_head'] or a['ordinary_status'] or a['ignored_inclusive_status'] or not all(a['parent_file_hashes'].values()): sys.exit(2)
elif mode=='batch':
    items=C['commands'][int(sys.argv[2]):int(sys.argv[2])+(int(sys.argv[3]) if len(sys.argv)>3 else 3)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(run,items))
elif mode=='checks':
    run({'id':'check-release-boundary','argv':['python3','-B','scripts/check-release-boundary.py','--base',C['baseline']]})
    run({'id':'check-scoped-whitespace','argv':['git','-C',str(R),'diff','--check',C['baseline']+'..HEAD','--',*C['r07_paths']]})
elif mode=='post':
    a=audit('post'); print(json.dumps(a))
