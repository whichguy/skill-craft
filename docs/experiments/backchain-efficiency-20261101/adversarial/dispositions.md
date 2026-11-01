# Dispositions of the 2026-11-01 adversarial review (codex:gpt-6.1-sol@medium)

Reviewed change: the packet `change.md` (238,145 bytes, SHA-256
`2e87ac74910aabdeab548d6779dee38be6ba562272a8ea6be652149acfc7a91c`), built at 07:16 from skill-craft
39af8ce04222fb49aa6d612e08b4dbabd73e5db3 plus the lean-prompt step then uncommitted (it landed as
090e37f5b222486c258e39c88a2d8e7557b939ef at 07:21). It diffs 17 source files against
e81fdb55d58bdb0bcc8c1643d93d5973709100e4 and leaves out the tests and the byte-for-byte validator move; the
evidence brief the reviewer had is `evidence.md` beside this file, and its findings are `findings.json` and
`findings.md`. Originals, with the review log, are under
`/Users/dadleet/src/backchain/results/backchain-efficiency-20261101/adversarial/`; the cohort protocol is
`/Users/dadleet/src/backchain/results/backchain-efficiency-20261101/cohort/PROTOCOL.md`.

Each code finding became a test in skill-craft `test/backchain-toolkit.test.py`, written from the reviewer's refutation
condition before its fix. The final test file run against 090e37f5 fails 16 times in 8 tests, each in the finding it
targets; after the fixes all 31 tests pass. `test_a_cycle_recorded_twice_in_one_callback_still_finishes` passes on
both: it guards against the first F1 fix's over-strict rule (one loop action per recorded cycle), which would have
refused a normal run that edits after `record` and records again in the same callback. Details and the fixing commit
are in `docs/backchain-efficiency-journal-2026-11.md`, Round 4.

| ID | Severity | Disposition | Test | Where |
|----|----------|-------------|------|-------|
| F1 | high | Fixed. `finish` accepts only this run's own terminal packet: it repeats the frozen contract's workspace, work, conditions, context and exit checks, names the run's receipt path and gate, counts no more actions than recorded cycles (an action with no record is a hand-written report) and carries the last cycle's report; a `complete` one shows every frozen exit check passing. A probe of a genuine run found every field equal. | `test_finish_refuses_a_receipt_that_is_not_this_runs`, `test_finish_refuses_a_callback_submitted_without_record`, `test_a_cycle_recorded_twice_in_one_callback_still_finishes` | `backchain.py` `receipt_problems` |
| F2 | high | Fixed. `verify` (the `backchain-evidence` exit check), `record` and `finish` recheck the digest of every frozen input (request, inherited draft, caller packet), the baseline, the contract and every resolved resource (Backchain card, prompts, command line, Until Loop card and runtime). | `test_verify_rejects_a_changed_binding` | `binding_problems` |
| F3 | high | Fixed. A caller's `edit_bounds` are enforced by `freeze`, `record` and `verify` against the inherited candidate, as `references/caller-contract.md` (repair/revise) states them; edge keys are `consumer<-supplier`, `null` for an `initial_state` input (now documented). Differs from the 2026-10-16 study's check in one respect: that check keyed edges per input object, this one per consumer/supplier pair, so another input on an existing provisional edge is a change of that edge, not a new edge. | `test_caller_edit_bounds_are_enforced` | `bound_errors`, `inherited_obligations` |
| F4 | high | Fixed. `record` refuses an assessment whose `candidate_identity` is not the sha256 of the candidate the cycle began with (freeze prints cycle 1's, each record prints the next and its handoff repeats it) or whose `checks` are empty. | `test_record_binds_the_assessment_to_the_candidate_it_reviewed` | `review_problems`, `reviewed_identity` |
| F5 | high | Fixed. With a caller packet, `finish --review FILE` is required; it checks the review's interface, action, stage and action ID against the packet, restores the caller's action identity and input identity, records the output digest, takes `coverage.structural_plan_status` from the check receipt and adds `review.convergence`; the result is `{plan, review, structure, status}`. A final review's planning gaps also prevent converged. | `test_a_source_aware_run_returns_plan_and_review` | `caller_review`, `command_finish` |
| F6 | medium | Measured, not changed. D1 is the owner's decision. The cohort reports the control arm's confirming-review yield (PROTOCOL.md secondary measure); a real material defect only a confirming review found goes to the owner. The reviewer's suggested extra arm (an independently contextualized confirming reviewer on candidate runs) is not run; the control's same-session confirming review is the in-distribution estimate, a stated limitation. | cohort | cohort PROTOCOL.md |
| F7 | high | Measured. D2's cohort is the experiment the finding asks for (control 0.6.6 against the exact combined candidate, all attempts kept). Added before the freeze: per-case reporting, a pooled block over the three cases where lean qualified less on 2026-10-16, and that pooled block as a block on a candidate win. | cohort | cohort PROTOCOL.md |
| F8 | medium | Fixed. The contract's authority is 0.6.6's scope again (no commit, push, merge or project execution, no broadened scope), plus "any other access is only what the request and the caller packet grant"; the blanket network, installation and contact ban is gone. | `test_the_contract_grants_only_the_callers_authority` | `AUTHORITY` |

Not defended (documented): a hand-edited `run.json` can change what the binding check compares against, and a
deliberately forged packet that copies every contract field and the last report would pass `receipt_problems`. The
2026-10-16 failures were hand-built bindings, not tampering; the checks target a normal run's mistakes.
