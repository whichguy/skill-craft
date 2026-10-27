"""Reproduce the recorded candidate-judge gap against committed source, without changing the repository."""
from pathlib import Path
import argparse,io,json,subprocess,sys,tarfile,tempfile
p=argparse.ArgumentParser();p.add_argument('--repo',default=str(Path(__file__).resolve().parents[2]));p.add_argument('--revision',default='e707b794de0a0bd802988ca68dac8e29ac0b3315');args=p.parse_args()
raw=subprocess.check_output(['git','-C',args.repo,'archive',args.revision,'skills/shiploop/scripts'])
with tempfile.TemporaryDirectory(prefix='shiploop-judge-audit-') as tmp:
 with tarfile.open(fileobj=io.BytesIO(raw)) as tar:tar.extractall(tmp,filter='data')
 sys.path.insert(0,str(Path(tmp)/'skills/shiploop/scripts'))
 import shiploop_test_loop as runner
 output='test_config.py::test_value[CASE-1] FAILED\n================ 1 failed in 0.01s ================\n'
 rows=[{'command':'wrapped-test','suite':'focused','ids':['CASE-1']},{'command':'wrapped-test','suite':'check'}]
 cases=[{'row':row,'exit':0,'verdict':runner.judge(row,0,output)} for row in rows]
 observed=runner.counts.outcomes(output,['CASE-1'])
 result={'revision':args.revision,'boundary':'direct calls to candidate judge; no CLI/live workflow','scenario':'runner reports a failed test but wrapper returns exit zero','output':output,'outcomes':observed,'cases':cases}
 print(json.dumps(result,indent=2))
 # This audit reproduces the defect; success does not mean the implementation is correct.
 assert observed['CASE-1']=='failed'
 assert all(x['verdict']['counts']['failed']==1 and x['verdict']['status']=='passed' for x in cases)
