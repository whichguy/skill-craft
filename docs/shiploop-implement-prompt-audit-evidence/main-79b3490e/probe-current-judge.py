"""Probe the pinned judge and saved-verdict reuse; direct helpers, not live/CLI acceptance."""
from pathlib import Path
import argparse,io,json,subprocess,sys,tarfile,tempfile
from unittest.mock import patch
p=argparse.ArgumentParser();p.add_argument('--repo',default=str(Path(__file__).resolve().parents[3]));p.add_argument('--revision',default='79b3490e3c04ebcb2dc48d21ff0f98ae2c363e91');args=p.parse_args()
raw=subprocess.check_output(['git','-C',args.repo,'archive',args.revision,'skills/shiploop/scripts'])
with tempfile.TemporaryDirectory(prefix='shiploop-judge-main-') as tmp:
 with tarfile.open(fileobj=io.BytesIO(raw)) as tar:tar.extractall(tmp,filter='data')
 sys.path.insert(0,str(Path(tmp)/'skills/shiploop/scripts'))
 import shiploop_test_loop as t
 outputs={
  'original_masked_failure':'test_config.py::test_value[CASE-1] FAILED\n================ 1 failed in 0.01s ================\n',
  'mixed_pass_and_error':'test_config.py::test_value[CASE-1] PASSED\n================ 1 passed, 1 error in 0.01s ================\n',
  'passing_title_contains_FAILED':'test_config.py::test_FAILED_value[CASE-1] PASSED\n================ 1 passed in 0.01s ================\n'}
 cases=[]
 for name,output in outputs.items():
  for suite in ['focused','check']:
   row={'command':'wrapped-test','suite':suite,**({'ids':['CASE-1']} if suite=='focused' else {})}
   cases.append({'scenario':name,'row':row,'exit':0,'output':output,'verdict':t.judge(row,0,output)})
 root=Path(tmp)/'run';root.mkdir();row={'command':'wrapped-test','suite':'focused','ids':['CASE-1']}
 legacy={'schema':t.SCHEMA,'action':'A1','stage':'verify','work_item':'W1','passed':True,'commands':[row],'trees':['same-product-tree'],'runs':[dict(row,exit=0,status='passed',counts={'ran':1,'failed':1,'runners':['pytest']},stdout=outputs['original_masked_failure'],stderr='')]}
 t.store.write_record(root/t.check_only_path('A1'),legacy)
 with patch.object(t,'_tree',return_value='same-product-tree'):
  reused=t._reused(root,'A1','verify','W1',[row],root,{})
 replay={'boundary':'_reused with a saved pre-fix-shaped receipt; only product tree lookup stubbed as unchanged','receipt':legacy,'reused':reused is not None,'returned_status':reused[0][0]['status'] if reused else None}
 result={'revision':args.revision,'boundary':'direct committed helper calls, not CLI/live acceptance','cases':cases,'stale_receipt':replay}
 print(json.dumps(result,indent=2))
 assert [x['verdict']['status'] for x in cases]==['failed','failed','passed','passed','passed','passed']
 assert replay['reused'] and replay['returned_status']=='passed'
