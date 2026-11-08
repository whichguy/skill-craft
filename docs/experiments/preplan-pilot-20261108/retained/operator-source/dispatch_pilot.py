"""Frozen paired cohorts using the established ShipLoop planning-slice runner."""
from pathlib import Path
import concurrent.futures, hashlib, json, os, random, shutil, subprocess, sys, time

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'source'
SUITE=SOURCE/'docs/experiments/preplan-pilot-20261108'
OP=ROOT/'operator'
sys.path.insert(0,str(OP))
from collect import digest
sys.path.insert(0,str(SOURCE/'test/shiploop_e2e'))
import overlay

def prepare():
    manifest=OP/'manifest.json'
    if manifest.exists(): raise SystemExit('Manifest already frozen; refusing replacement')
    arms={}
    for arm in ['current','early']:
        build=ROOT/'arms'/arm/'build'
        shutil.copytree(ROOT/'smoke/current/build',build)
        plugin=build/'plugins/skill-craft'
        applied=overlay.apply_to_plugin(SUITE/'candidate-overlay.json',plugin) if arm=='early' else None
        arms[arm]={'plugin':str(plugin),'digest':digest(plugin),'overlay':applied}
    reg=json.loads((SUITE/'registration.json').read_text())
    rng=random.Random(reg['order_seed'])
    pairs=[(case,rep) for case in reg['cases'] for rep in range(1,reg['repetitions']+1)]
    rng.shuffle(pairs)
    cells=[]
    for pi,(case,rep) in enumerate(pairs):
        order=['current','early'] if pi%2==0 else ['early','current']
        for arm in order:
            ident=f'sample-{len(cells)+1:02}'
            out=ROOT/'runs'/ident
            argv=[sys.executable,'-B',str(SUITE/'run_slice.py'),'--case',case,'--host','codex','--model','gpt-6.1-sol','--effort','high','--seed-at','test-strategy','--stop-after','plan','--planning-review','stage','--delegation','inline','--plugin-dir',arms[arm]['plugin'],'--opening-note',str(SUITE/'opening.txt'),'--timeout',str(reg['deadline_seconds_per_slice']),'--output',str(out)]
            cells.append({'id':ident,'case':case,'rep':rep,'arm':arm,'cohort':pi//2+1,'out':str(out),'argv':argv})
    frozen={str(p.relative_to(SUITE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(SUITE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    doc={'registration':reg,'frozen_at':time.time(),'source_commit':subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD']).decode().strip(),'suite_files':frozen,'arms':arms,'cells':cells,'operator_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (OP/'queue.py',OP/'collect.py',OP/'judge_call.py')}}
    manifest.write_text(json.dumps(doc,indent=2)+'\n')
    print(json.dumps({'manifest':str(manifest),'cells':len(cells),'cohorts':4,'arms':arms},indent=2))

def execute(cell):
    ident=cell['id'];log=OP/(ident+'.log');start=time.time()
    if Path(cell['out']).exists():raise RuntimeError(f'Refusing existing output: {cell["out"]}')
    with log.open('w') as f:
        process=subprocess.Popen(cell['argv'],cwd=SOURCE,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
        (OP/(ident+'-launch.json')).write_text(json.dumps({'cell':cell,'pid':process.pid,'start':start},indent=2)+'\n')
        print(json.dumps({'event':'start','id':ident,'case':cell['case'],'rep':cell['rep'],'arm':cell['arm'],'pid':process.pid}),flush=True)
        code=process.wait()
    record={'id':ident,'exit':code,'start':start,'end':time.time(),'elapsed':time.time()-start,'log':str(log)}
    (OP/(ident+'-complete.json')).write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'event':'complete',**record}),flush=True)
    return record

def run():
    manifest=json.loads((OP/'manifest.json').read_text())
    for rel,expected in manifest['suite_files'].items():
        assert hashlib.sha256((SUITE/rel).read_bytes()).hexdigest()==expected,rel
    for arm,d in manifest['arms'].items():assert digest(Path(d['plugin']))==d['digest'],arm
    marker=OP/'queue-start.json'
    if marker.exists():raise SystemExit('Queue already started; operator must inspect existing attempts')
    marker.write_text(json.dumps({'started':time.time(),'pid':os.getpid()})+'\n')
    results=[]
    for cohort in range(1,5):
        cells=[c for c in manifest['cells'] if c['cohort']==cohort]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results.extend(pool.map(execute,cells))
    for arm,d in manifest['arms'].items():assert digest(Path(d['plugin']))==d['digest'],arm
    (OP/'queue-complete.json').write_text(json.dumps({'completed':time.time(),'results':results},indent=2)+'\n')
    print('QUEUE_COMPLETE',flush=True)

if __name__=='__main__':
    {'prepare':prepare,'run':run}[sys.argv[1]]()
