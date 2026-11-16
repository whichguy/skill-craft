import os,sys,json,subprocess,hashlib,stat,datetime,time,signal,concurrent.futures,re
from pathlib import Path
REPO=Path('/Users/dadleet/src/skill-craft-r19-20261115')
OUT=Path(__file__).parent
HEAD='541422e1e0b243579cb030cb09fc6422b28e7a4b'
BASE='4ec9ac4bb7425724f41cf3abd5e1776e8fdbd596'
DEADLINE=datetime.datetime(2026,11,16,2,38,tzinfo=datetime.timezone.utc).timestamp()
COMMANDS=[['python3','-B','test/shiploop-backchain-check.test.py'],['python3','-B','test/shiploop-navigator-dry-run.test.py'],['python3','-B','test/shiploop-head-order.test.py'],['python3','-B','test/shiploop-packet-bounds.test.py'],['python3','-B','test/shiploop-loops.test.py','InvokeLinesTests.test_emitted_start_owns_state_in_existing_loops_from_foreign_cwd','InvokeLinesTests.test_distinct_actions_and_runs_keep_independent_live_state','InvokeLinesTests.test_the_packet_prints_the_literal_start_command_and_it_starts_the_loop','NavigatorLoopTests.test_emitted_launch_resumes_and_check_done_complete_accepts_once','NavigatorLoopTests.test_active_restart_and_lost_state_refuse_without_replacing_receipt','MissingContractTests.test_next_writes_the_contract_of_a_run_seeded_at_step_plan','-v'],['python3','-B','test/shiploop-e2e-fidelity.test.py','LoopCommandsTest','-v'],['python3','-B','scripts/check-release-boundary.py','--base',BASE,'--head',HEAD],['git','-C',str(REPO),'diff','--check',BASE,'HEAD']]
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*args):return subprocess.check_output(['git','-C',str(REPO),*args])
def snap(label):
    data={'timestamp':stamp(),'head':git('rev-parse','HEAD').decode().strip(),'status':git('status','--porcelain=v1','--untracked-files=all').decode(),'ignored_inclusive_status':git('status','--porcelain=v1','--ignored','--untracked-files=all').decode(),'expected_source_outputs':[],'expected_external_outputs':str(OUT),'tracked':[]}
    for entry in git('ls-files','--stage','-z').split(b'\0'):
        if not entry:continue
        header,name=entry.split(b'\t',1); p=REPO/os.fsdecode(name)
        v={'path':os.fsdecode(name),'git_index':header.decode()}
        try:
            s=p.lstat();v['mode']=oct(stat.S_IMODE(s.st_mode));v['kind']='symlink' if p.is_symlink() else 'file' if p.is_file() else 'other'
            content=os.fsencode(os.readlink(p)) if p.is_symlink() else p.read_bytes()
            v['sha256']=hashlib.sha256(content).hexdigest()
            if p.is_symlink():v['symlink_target']=os.readlink(p)
        except FileNotFoundError:v['missing']=True
        data['tracked'].append(v)
    (OUT/(label+'.json')).write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'snapshot':label,'head':data['head'],'status':data['status'],'ignored_inclusive_status':data['ignored_inclusive_status'],'tracked_count':len(data['tracked'])}))
    return data

def run(n):
    argv=COMMANDS[n-1]; prefix=OUT/f'{n:02d}'
    record={'id':n,'argv':argv,'cwd':str(REPO),'environment':{'PYTHONDONTWRITEBYTECODE':'1'},'start':stamp(),'stdout':str(prefix)+'.stdout.log','stderr':str(prefix)+'.stderr.log','attempt':1,'selected_count':6 if n==5 else 2 if n==6 else None}
    env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
    with open(record['stdout'],'wb') as stdout,open(record['stderr'],'wb') as stderr:
        if time.time()>=DEADLINE:record.update(status='TIMEOUT',exit=None)
        else:
            try:
                proc=subprocess.Popen(argv,cwd=REPO,env=env,stdout=stdout,stderr=stderr,start_new_session=True)
                record['pid']=proc.pid
                try:record['exit']=proc.wait(timeout=max(.001,DEADLINE-time.time()))
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid,signal.SIGTERM)
                    try:proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
                    record.update(status='TIMEOUT',exit=proc.returncode)
            except OSError as e:record.update(status='BLOCKED',exit=None,error=str(e))
    record['end']=stamp()
    output=Path(record['stdout']).read_text(errors='replace')+Path(record['stderr']).read_text(errors='replace')
    counts=re.findall(r'Ran (\d+) tests? in ',output);record['completed_count']=int(counts[-1]) if counts else None
    record['skips_detected']=bool(re.search(r'\bskipped\b|\bSKIP\b',output))
    if 'status' not in record:
        if record['exit']!=0:record['status']='FAIL'
        elif record['skips_detected']:record['status']='INCOMPLETE'
        elif n<=6:record['status']='PASS' if record['completed_count'] and re.search(r'^OK\s*$',output,re.M) else 'INCOMPLETE'
        elif n==7:record['status']='PASS' if re.search(r'\bOK\b',output) else 'INCOMPLETE'
        else:record['status']='PASS' if not output else 'INCOMPLETE'
    if record['status']!='PASS':record['failure_excerpt']=output[-4000:]
    (OUT/f'{n:02d}.json').write_text(json.dumps(record,indent=2)+'\n')
    return record
if sys.argv[1]=='pre':
    d=snap('pre');sys.exit(0 if d['head']==HEAD and not d['status'] and not d['ignored_inclusive_status'] else 2)
elif sys.argv[1]=='post':snap('post')
elif sys.argv[1]=='run':
    nums=list(map(int,sys.argv[2:]));assert len(nums)<=2
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(run,nums):print(json.dumps(result))
