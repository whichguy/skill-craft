#!/usr/bin/env python3
"""Offline calibration of the new fictional reader, never participant evidence."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
base=Path(__file__).resolve().parent.parent
root=base/'calibration'
shutil.copytree(base/'fixture',root)
def hashes():
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name!='receipts.jsonl'}
before=hashes(); observations=[]
def call(*args):
    p=subprocess.run([sys.executable,'-B',str(root/'adapter.py'),*args],text=True,capture_output=True)
    value=json.loads(p.stdout);observations.append({'args':args,'exit':p.returncode,'response':value})
    return p.returncode,value
_,cat=call('catalog');assert next(x for x in cat['sources'] if x['id']=='slack')['operations']==['fetch']
_,first=call('search','--source','directory','--query','Orion')
assert len(first['results'])==2 and first['nextCursor']
assert all(x['id']!='slack-orion-review-1842' for x in first['results'])
_,second=call('search','--source','directory','--query','Orion','--cursor',first['nextCursor'])
assert second['results'][0]['id']=='slack-orion-review-1842' and second['nextCursor'] is None
for source,rid in [('slack','slack-orion-analytics-lead'),('slack','slack-orion-review-1842'),('intranet','adr-042-orion-review-gateway'),('private-git','orion-review-gateway-src-app')]:
    code,value=call('fetch','--source',source,'--id',rid);assert code==0 and 'full' in value['record']
    rows=[json.loads(x) for x in (root/'receipts.jsonl').read_text().splitlines()];assert rows[-1]['response']==value
for args in [('search','--source','directory','--query','Orion retry'),('search','--source','slack','--query','Orion'),('search','--source','teams','--query','Orion'),('search','--source','directory','--query','Orion','--cursor','wrong')]:
    code,value=call(*args);assert code==0 and value['status']=='gap'
code,value=call('search','--source','public','--query','Orion');assert code==3 and value['status']=='rejected'
assert before==hashes()
(root/'preflight.json').write_text(json.dumps({'outcome':'PASS','inputs_unchanged':True,'observations':observations,'limits':'Calibration only; no participant or live connector proof.'},indent=2)+'\n')
print('PASS: 12 calibration calls, pagination/full response receipts/coverage gaps/rejection; unchanged inputs')
