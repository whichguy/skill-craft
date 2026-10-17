import sys,pathlib,json,os,hashlib,shutil,datetime,tempfile
repo=pathlib.Path('/Users/dadleet/src/skill-craft')
sys.path.insert(0,str(repo/'test/shiploop_e2e'))
import metrics
root=pathlib.Path(tempfile.mkdtemp(prefix='shiploop-timing-probe-'))
a=root/'original';b=root/'copied'
(a/'improve').mkdir(parents=True)
p=a/'improve'/'a-spec-bind.md';p.write_text('unchanged binding evidence\n');os.utime(p,(1200,1200))
(a/'timeline.json').write_text(json.dumps({'started':datetime.datetime.fromtimestamp(1000,datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}))
rows=[{'action':'a-spec','stage':'spec','outcome':'done','t':1300},{'action':'a-ts','stage':'test-spec','outcome':'done','t':1600}]
state={'improve_results':{'a-spec':{}}}
original=metrics.planning_window(a,state,rows,{1:1000})[0]
shutil.copytree(a,b,copy_function=shutil.copy)
copied=metrics.planning_window(b,state,rows,{1:1000})[0]
bp=b/'improve'/'a-spec-bind.md'
assert original['window']['seconds']==copied['window']['seconds']==600.0
assert original['improve']['seconds']==100.0 and original['producer_seconds']==500.0
assert copied['improve']['seconds'] is None and copied['producer_seconds'] is None
result={'status':'reproduced','purpose':'Same evidence bytes, different copy metadata; synthetic no-model observation','root':str(root),'sha256_equal':hashlib.sha256(p.read_bytes()).hexdigest()==hashlib.sha256(bp.read_bytes()).hexdigest(),'original':original,'copied_without_metadata':copied,'conclusion':'Window stays 600s; Improve/producer split changes from 100/500s to unknown after copy. Existing documented limitation, not a false passing verdict.'}
print(json.dumps(result,indent=2))
