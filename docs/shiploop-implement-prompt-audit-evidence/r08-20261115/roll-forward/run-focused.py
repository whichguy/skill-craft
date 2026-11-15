import datetime, hashlib, json, os, pathlib, subprocess, sys, time
repo=pathlib.Path('/Users/dadleet/src/skill-craft-r08-20261115')
root=pathlib.Path(__file__).parent
phase=sys.argv[1]; out=root/phase; out.mkdir()
checks={
 'counts':['python3','test/shiploop-test-counts.test.py','CountTests.test_pytest_summary_errors_fail_without_certifying_tests_ran','JudgeTests.test_pytest_error_judgement_preserves_gate_precedence'],
 'reuse':['python3','test/shiploop-test-loop.test.py',*[f'TestLoopTests.{x}' for x in ('test_stale_candidate_schema_reruns_on_the_same_tree','test_current_candidate_schema_reuses_without_whole_answer','test_stale_whole_answer_schema_reruns_stale_subordinate_receipts','test_mixed_pytest_error_refuses_actual_step_proof','test_stale_proof_schema_reruns_check_and_numbered_receipts','test_current_proof_schema_reuses_check_then_numbered_receipt')]],
 'fidelity':['python3','test/shiploop-e2e-fidelity.test.py','ValidationTest.test_current_v2_emitted_evidence_is_readable','ValidationTest.test_a_counted_row_that_ran_zero_tests_is_listed_not_passed','ValidationTest.test_a_record_of_another_schema_or_that_cannot_be_read_is_not_read_and_is_counted_apart'],
}
paths=['skills/shiploop/scripts/shiploop_test_counts.py','skills/shiploop/scripts/shiploop_test_loop.py','skills/shiploop/scripts/shiploop_check.py','test/shiploop_e2e/fidelity.py']
paths += subprocess.check_output(['git','-C',str(repo),'diff','--name-only'],text=True).splitlines()
def identity():
 return {'head':subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip(), 'status':subprocess.check_output(['git','-C',str(repo),'status','--short'],text=True),'sha256':{p:hashlib.sha256((repo/p).read_bytes()).hexdigest() for p in sorted(set(paths))}}
(out/'before.json').write_text(json.dumps(identity(),indent=2)+'\n')
results=[]; deadline=time.monotonic()+1200
for name,cmd in checks.items():
 started=datetime.datetime.now(datetime.timezone.utc).isoformat(); t=time.monotonic()
 with (out/f'{name}.stdout').open('wb') as stdout,(out/f'{name}.stderr').open('wb') as stderr:
  try:
   result=subprocess.run(cmd,cwd=repo,stdout=stdout,stderr=stderr,timeout=max(1,deadline-time.monotonic()),env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
   code=result.returncode; outcome='PASS' if code==0 else 'FAIL'
  except subprocess.TimeoutExpired: code=None;outcome='TIMEOUT'
 results.append(dict(name=name,command=cmd,cwd=str(repo),started=started,seconds=time.monotonic()-t,exit_code=code,outcome=outcome))
 (out/'outcomes.json').write_text(json.dumps(results,indent=2)+'\n')
 print(name,outcome,round(time.monotonic()-t,2),flush=True)
(out/'after.json').write_text(json.dumps(identity(),indent=2)+'\n')
