import subprocess,json,hashlib,pathlib,time,os
repo=pathlib.Path('/Users/dadleet/src/skill-craft-r08-integrated-20261115')
out=pathlib.Path('/Users/dadleet/.codex/visualizations/2026/10/18/01a14c60-cd70-7921-b457-5cf870234201/r08-20261115/lint-repair')
files=['test/shiploop-test-counts.test.py','test/shiploop-test-loop.test.py']
def snapshot(name):
    paths=subprocess.check_output(['git','-C',str(repo),'ls-files','-z']).decode().split('\0')
    data={'head':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip(),'status':subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1']).decode(),'tracked_sha256':{p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in paths if p and (repo/p).is_file()}}
    (out/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
    return data
def run(name,argv,env=None):
    start=time.monotonic()
    p=subprocess.run(argv,cwd=repo,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    elapsed=time.monotonic()-start
    (out/(name+'.stdout')).write_bytes(p.stdout)
    (out/(name+'.stderr')).write_bytes(p.stderr)
    result={'argv':argv,'cwd':str(repo),'exit':p.returncode,'duration_seconds':elapsed,'stdout':str(out/(name+'.stdout')),'stderr':str(out/(name+'.stderr'))}
    (out/(name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result
