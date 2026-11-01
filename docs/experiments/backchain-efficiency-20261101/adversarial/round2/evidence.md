# Evidence the fix commit rests on

All results are script-run tests or direct probes; no model run has used the fixed commands yet (a six-run live pilot
with gpt-6-astra medium is the next step, then a 60-run cohort).

## Fail-first and after

The final `test/backchain-toolkit.test.py` (31 tests) run against the code before the fix (090e37f5) fails 16 times
in 8 tests; after the fix all 31 pass (29.7 s, Python 3.15 on macOS; the scripts parse as Python 3.9).
- F1, 3 failures: `test_finish_refuses_a_receipt_that_is_not_this_runs` (a receipt file `{"status": "complete"}`,
  and a genuine complete receipt copied from another run, each make finish exit 0 "converged" before the fix; after,
  exit 1 and an incomplete result whose next action names the receipt; the genuine receipt converges);
  `test_finish_refuses_a_callback_submitted_without_record` (a hand-written report submitted to Until Loop's
  done_argv, then one recorded trivial cycle completes the loop; before, finish converged; after, it reports "the
  receipt counts 2 action(s) where 1 cycle(s) are recorded").
- F2, 6 failures: `test_verify_rejects_a_changed_binding`, a source-aware run with a copied Until Loop card; after
  one recorded cycle, appending a newline to each of input/request.md, input/caller.json, loop/baseline.json,
  loop/contract.json, the Until Loop card and the runtime script left verify at exit 0 before the fix; after, exit
  1 naming the changed file; restoring the byte content restores exit 0.
- F3, 4 failures: `test_caller_edit_bounds_are_enforced`, bounds {provisional S2, provisional edge S2<-S1, S1
  protected, the one initial fact protected, no new steps or edges}: changing protected S1's statement, adding a
  step S3, adding an input to S2 from initial_state (key S2<-null), and dropping the protected fact were all
  accepted by freeze before; after, each is refused naming the bound. Removing one of S2's two inputs from S1
  (within the bounds) is accepted before and after.
- F4, 1 failure: `test_record_binds_the_assessment_to_the_candidate_it_reviewed` fails first on the new assertion
  that freeze prints "Cycle 1's candidate_identity: <sha256>". With that assertion removed, its three subtests fail
  on 090e37f5: assessments with candidate_identity null, a stale all-zero sha256, and an empty checks list were
  recorded as cycles 1, 2 and 3. After, each is refused and nothing is recorded; a correct one records, and record
  prints and its report handoff carries the next cycle's identity.
- F5, 1 failure: `test_a_source_aware_run_returns_plan_and_review`: before, finish on a caller-packet run exited 0
  with {plan, convergence}; after, it exits 3 without --review, and with a review object whose interface, action,
  stage and action_id match the packet it writes {plan, review, structure, status} with review.convergence (terminal
  status complete), review.candidate.output_sha256 equal to the plan file's sha256, and
  review.coverage.structural_plan_status "valid" beside the review's own source_review_status.
- F8, 1 failure: `test_the_contract_grants_only_the_callers_authority` (authority keeps commit, push, merge,
  project execution and broadened scope; names no network, contact or installation ban).
- A guard that passes before and after: `test_a_cycle_recorded_twice_in_one_callback_still_finishes` (the model
  records, edits, records again and submits the second report in the same callback; finish converges). It exists
  because the first version of the F1 fix required exactly one Until Loop action per recorded cycle, which would
  have refused that normal run.
- The 23 earlier toolkit tests pass unchanged, among them: a fresh run converging on its first trivial review; a
  changed plan never classified trivial; `--passes one` and `--passes converge`; record refusing lost goal_needs,
  an orphan step, a malformed assessment and an unresolved-but-satisfied report; inherited edges staying while
  generated ones may be removed; verify catching a late edit and a changed record; finish reporting a blocked stop
  honestly and refusing an active loop.

Other suites: the quick tier for the changed paths (17 suites, incl. ShipLoop's navigator contract, dry run and
planning handoff) passed in 322.5 s before the one-action correction; after it, the toolkit,
`BackchainGateDocumentsTest` (9) and `shiploop-navigator-dry-run` (36), the two ShipLoop suites that read the
edited Backchain docs, pass. backchain-graph 12, backchain-chunks 49, shiploop-backchain-check 10,
marketplace-package 31 and until-loop-vendor 10 pass.

## The runtime's terminal packet (probe of a genuine run)

A real run (prepare, freeze, start, record, verify_script, done_argv) ended `complete`. Its receipt file equals the
packet done_argv printed. workspace, work, context, exit_checks, receipt, conditions {exit, repeat} all equal the
frozen contract's; last_report equals the cycle's report.json; progress was {action_number 1, trivial_streak 1,
required_trivial_reviews 1}; last_check_results held both frozen checks with passed true. In the runtime's code a
terminal packet's action_number is the number of the callback that ended the run (callbacks are numbered from 1),
a satisfied report needs a fresh verify run, a report may carry check_repairs only with an unsatisfied exit, and a
repaired check changes the stored exit_checks.

## Callers

ShipLoop writes no edit_bounds (it uses the caller contract only for its read-only audit resource and lists it
among a whole-skill call's resources). The 2026-10-16 study (36 runs) is the only prior use of edit bounds: its
own checker keyed edges per input object; this one keys them per consumer<-supplier pair.

## Decisions the reviewer may contest

- Not defended: a hand-edited run.json changes what the binding check compares against; a forged packet that
  copies every contract field and the last report passes the receipt check. The 2026-10-16 failures were mistakes
  in hand-built bindings (12 of 14 disqualified runs), not tampering.
- finish puts the run's own problems before a model-written next_action.
- A final review's planning gaps also prevent "converged" for a caller-packet run.
