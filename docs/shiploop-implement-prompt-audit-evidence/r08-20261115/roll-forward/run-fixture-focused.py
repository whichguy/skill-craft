import datetime, hashlib, json, os, pathlib, subprocess, sys, time
repo=pathlib.Path('/Users/dadleet/src/skill-craft-r08-20261115')
root=pathlib.Path(__file__).parent
phase=sys.argv[1]; out=root/phase; out.mkdir()
checks={'analysis': ['python3', 'test/shiploop-e2e-analysis.test.py', 'MetricsTest.test_a_verify_record_that_lists_its_request_counts_only_what_ran'], 'delta': ['python3', 'test/shiploop-e2e-delta.test.py', 'RegressionTest.test_matched_rows_preserve_plan_and_receipt_provenance', 'RegressionTest.test_reused_counted_receipts_are_observations_not_new_executions'], 'handoff': ['python3', 'test/shiploop-handoff.test.py', 'PrimaryGateTests.test_a_primary_outcome_needs_a_test_shiploop_saw_pass_in_a_case_for_its_requirement'], 'release-reporting': ['python3', 'test/shiploop-e2e-fidelity.test.py', 'ValidationTest.test_a_failed_or_unknown_release_verify_record_is_shown_with_passed_false_or_null', 'ValidationTest.test_the_release_verify_record_is_the_latest_by_created_at_then_by_number_never_by_file_name', 'ValidationTest.test_an_observed_block_with_no_where_is_no_release_verify_record']}
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
