from pathlib import Path
import concurrent.futures, hashlib, json, os, subprocess, sys, time
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'apparatus'))
import seed
OUT=ROOT/'permission-probes-001'
OUT.mkdir(exist_ok=False)
script=OUT/'snapshot_probe.py'
script.write_text('''from pathlib import Path
import json, subprocess, sys, uuid
sys.path.insert(0, '/Users/dadleet/src/skill-craft-r05-20261115/skills/shiploop/scripts')
import shiploop_lint as lint
repo, run = map(Path, sys.argv[1:3])
p=repo/'permission-probe.txt'
p.write_text('untracked snapshot probe '+uuid.uuid4().hex+'\\n')
index=run/'lint/tmp/permission-probe.index'
result={'initial_bind_exists': bool(list((run/'improve').glob('*-bind.md')))}
try:
    result['tree']=lint.snapshot_tree(repo,run,index)
    result['status']='PASS'
except lint.LintError as e:
    result.update(status='BLOCKED', error=str(e))
finally:
    p.unlink()
    if index.exists(): index.unlink()
print(json.dumps(result))
''')
def one(mode):
    s=seed.Seed(OUT/mode/'subjects',OUT/mode/'seed-logs','unchecked-oracle','carry-forward')
    row=s.seed()
    seed.dump(OUT/mode/'fixture.json',row)
    prompt=f'Execute exactly this command once and return its JSON result. Do not diagnose, edit or repair anything; start no agents or advisors. This is a local-only disposable snapshot-permission probe.\npython3 -B {script} {s.repo} {s.run}\n'
    folder=OUT/mode
    (folder/'input.md').write_text(prompt)
    args=['codex','exec','--profile','shiploop','--model','gpt-6.1-sol','-c','model_reasoning_effort="medium"','--sandbox',mode,'-c','approval_policy="never"','--add-dir',str(OUT),'-C',str(s.repo),'--json','-o',str(folder/'native-final.md'),'-']
    env=s.env.copy(); env['SHIPLOOP_KEEPALIVE']='off'
    seed.dump(folder/'launch.json',{'argv':args,'source':seed.SHA,'input_sha256':hashlib.sha256(prompt.encode()).hexdigest()})
    t=time.monotonic()
    with (folder/'events.jsonl').open('w') as out,(folder/'stderr.log').open('w') as err:
        p=subprocess.run(args,input=prompt,text=True,cwd=s.repo,env=env,stdout=out,stderr=err)
    r={'mode':mode,'exit':p.returncode,'wall_seconds':round(time.monotonic()-t,3),'final':(folder/'native-final.md').read_text() if (folder/'native-final.md').exists() else None}
    seed.dump(folder/'receipt.json',r); print(json.dumps(r),flush=True)
    return r
before=seed.source_identity();seed.dump(OUT/'source-pre.json',before)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: rows=list(pool.map(one,['workspace-write','danger-full-access']))
after=seed.source_identity();seed.dump(OUT/'source-post.json',after)
seed.dump(OUT/'summary.json',{'results':rows,'source_unchanged':before==after})
