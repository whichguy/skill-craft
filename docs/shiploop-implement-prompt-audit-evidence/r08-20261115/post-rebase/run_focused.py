import ast
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

repo = Path('/Users/dadleet/src/skill-craft-r08-20261115')
evidence = Path(__file__).resolve().parent
def git(*args):
    return subprocess.check_output(['git', '-C', str(repo), *args])
def snapshot(label):
    files = git('ls-files', '-z').decode().split('\0')
    hashes = {p: hashlib.sha256((repo / p).read_bytes()).hexdigest() for p in files if p and (repo / p).is_file()}
    result = {'head': git('rev-parse', 'HEAD').decode().strip(),
              'status': git('status', '--porcelain=v1', '--untracked-files=all').decode(), 'hashes': hashes}
    (evidence / (label + '-source.json')).write_text(json.dumps(result, indent=2) + '\n')
    return result
loop = 'test/shiploop-test-loop.test.py'
counts = 'test/shiploop-test-counts.test.py'
tree = ast.parse((repo / loop).read_text())
tap = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'TapCountRouteTests')
tap_ids = ['TapCountRouteTests.' + node.name for node in tap.body if isinstance(node, ast.FunctionDef) and node.name.startswith('test_')]
assert len(tap_ids) == 9
r08_ids = ['TestLoopTests.' + name for name in [
    'test_stale_candidate_schema_reruns_on_the_same_tree',
    'test_current_candidate_schema_reuses_without_whole_answer',
    'test_stale_whole_answer_schema_reruns_stale_subordinate_receipts',
    'test_mixed_pytest_error_refuses_actual_step_proof',
    'test_stale_proof_schema_reruns_check_and_numbered_receipts',
    'test_current_proof_schema_reuses_check_then_numbered_receipt']]
commands = [
    ('tap-route', ['python3', loop, '-v', *tap_ids], 9),
    ('r08-counts-judge', ['python3', counts, '-v',
        'CountTests.test_pytest_summary_errors_fail_without_certifying_tests_ran',
        'JudgeTests.test_pytest_error_judgement_preserves_gate_precedence'], 2),
    ('r08-schema-proof', ['python3', loop, '-v', *r08_ids], 6)]
(evidence / 'commands.json').write_text(json.dumps([{'name': n, 'argv': c, 'shell': shlex.join(c), 'expected_methods': k} for n,c,k in commands], indent=2) + '\n')
(evidence / 'contract.json').write_text(json.dumps({'cwd': str(repo), 'deadline_seconds': 900, 'retry': 'none; stop on failure', 'source_edits_during_execution': False, 'expected_methods':17, 'generated_outputs':'ignored Python bytecode caches only; test fixtures use temporary directories'}, indent=2) + '\n')
pre = snapshot('pre')
results=[]
start=time.monotonic()
for name, cmd, expected in commands:
    t=time.monotonic()
    with (evidence / (name + '.log')).open('wb') as log:
        try:
            completed=subprocess.run(cmd, cwd=repo, stdout=log, stderr=subprocess.STDOUT, timeout=max(1,900-(t-start)), env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            code=completed.returncode
        except subprocess.TimeoutExpired:
            code='TIMEOUT'
    content=(evidence / (name + '.log')).read_text()
    passed=code == 0 and f'Ran {expected} tests in ' in content and content.rstrip().endswith('OK')
    results.append({'name':name,'command':shlex.join(cmd),'expected_methods':expected,'exit':code,'result':'PASS' if passed else 'FAIL' if isinstance(code,int) and code else 'INCOMPLETE','elapsed_seconds':round(time.monotonic()-t,3),'log':str(evidence / (name+'.log'))})
    (evidence / 'results.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps(results[-1]),flush=True)
    if not passed:
        break
post=snapshot('post')
stable=pre == post
report={'result':'PASS' if len(results)==3 and all(r['result']=='PASS' for r in results) and stable else 'INCOMPLETE', 'results':results, 'source_stable':stable, 'tracked_files_hashed':len(pre['hashes']), 'changed_hashes':[p for p in set(pre['hashes'])|set(post['hashes']) if pre['hashes'].get(p)!=post['hashes'].get(p)], 'elapsed_seconds':round(time.monotonic()-start,3)}
(evidence / 'handoff.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
