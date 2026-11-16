# Astra max review of the closed-loop Phase 1 build (2026-11-15)

**Question.** Is the first build of the generic `closed-loop` skill (plan: `docs/closed-loop-plan-2026-11-15.md`, Phase 1) safe to
ship, and where can its convergence certificate be wrong?

**Subject.** Commit `ff9cb35d46316f6ce70f92c0e418c0fad53f0e3c` on branch `feat/closed-loop-p1-ce82cb`: `skills/closed-loop/` (the
orchestrator `scripts/closed_loop.py`, 1,219 lines; card, five references, three prompts), `test/closed-loop.test.py` (63 tests) and
the fake subject `test/fixtures/closed-loop-fake/adapter.py`.

**Reviewer and conditions.** Codex `gpt-6-astra` at max effort, a fresh child with the owner's effort override, one attempt, no
fallback (`astra-run.json`); read-only on tracked files (it ran the suite and temporary-directory probes; `git status` was clean
before and after). The brief is `astra-brief.txt`; the full answer is `astra-answer.txt`.

**Result.** *Not ready to ship.* 10 findings (8 P1, 2 P2), each reproduced or traced by the reviewer. At that commit all 63 tests
passed in 122.5 s (`test-run-at-ff9cb35d.json`), so the suite itself encoded several of the defects: C1 expected a `verified`
record without evidence to pass; the "queries never write" test compared file names, not contents; the fake had one dimension and
always returned well-formed reports. Status: **firm** (reproduced; evidence files below).

## Findings, fixes and the tests that now hold them

| # | Finding (reviewer's priority) | Evidence | Fix in the hardening commit | Regression tests (`test/closed-loop.test.py`) |
| --- | --- | --- | --- | --- |
| 1 | P1. Malformed evidence converges: `--quiet-window -1`, `"ran": "false"`, empty identities, a missing case | `probes-certificate.json` (`negative_k`, `false_strings`), `probes-additional.json` (`negative_k_invalid_review`, `missing_identity`) | `validate_facts` (types, exact case set, finite consumption, non-empty identity) before evidence is recorded; a malformed report is a failed step; `validate_state` on every load; K at least 1 | `EvidenceTests.test_validate_facts_...`, `test_a_malformed_report_from_an_adapter_is_a_failed_step_...`; `StateTests.test_deeply_malformed_state_...`, `test_init_never_reinitialises_...` |
| 2 | P1. The quiet window does not establish the named scope; S1 converged with zero S1 iterations | `probes-certificate.json` (`missing_scope_case_in_last_quiet`, `widen_no_new_scope_runs`) | exact scope-case coverage per iteration; `window` bound to the active scope; contract checks carry `--expect-scope` and `--expect-identity` | `EvidenceTests.test_widening_starts_with_no_quiet_history_...`, `test_a_contract_for_another_campaign_identity_...`; `UntilLoopTests.test_a_contract_frozen_at_one_scope_...` |
| 3 | P1. The real Until Loop accepts a stale satisfied report after the campaign changes outside the subject workspace | `probe-runtime-stale-satisfaction.json` | the contract's workspace is the campaign folder (a Git repo holding only campaign state); the runtime's state, contract and receipts live in the sibling `<campaign>.work` so recovery cannot rewrite what the fingerprint watches | `UntilLoopTests.test_a_state_change_made_through_the_sanctioned_verbs_...` (the reviewer's scenario), `test_a_change_to_the_campaign_after_the_verify_run_is_refused` |
| 4 | P1. `verified` needs no evidence; C5 reads only the last cleanup; readiness limits vanish | `probes-certificate.json` (`verified_without_evidence`, `unclean_earlier_run`) | evidence required for every resolved status; unknown statuses fail closed; C5 covers every iteration; `cleanup` and `cancel` verbs; readiness is recorded and its allowed claims travel into the certificate and report | `CertificateTests.test_a_record_resolves_only_with_a_known_status_...`; `EvidenceTests.test_an_earlier_unclean_run_...`, `test_a_cancelled_step_...`; `CertificateTests.test_the_certificate_carries_...` |
| 5 | P1. A hunt's findings are ignored; coverage tracks single values only; the report claims convergence early or keeps a stale stop | `probes-additional.json` (`unhandled_hunt_then_stale_stop`, `missing_combinations`) | a hunt closes with a disposition for every blind spot and only a reasoned rejection converges; declared `combinations`; campaign status is `in progress` until a stop, and a converged stop is re-checked every time it is read | `EvidenceTests.test_a_hunt_result_needs_...`, `test_a_blind_spot_handed_to_the_owner_...`, `test_only_a_rejected_blind_spot_...`, `test_declared_combinations_...`, `test_a_converged_scope_is_not_a_converged_campaign_...` |
| 6 | P1. `init` then `step` runs a hosted case with no ratification, no readiness and no owner approval | `probes-certificate.json` (`no_ratification_no_readiness_owner_only_case`) | every start needs the ratified boundary hash, a recorded readiness for it that shows the start rule, and every selected case released (`--approve-case`); the card asks before a `needs_owner` task is done | `GateTests` (five tests) |
| 7 | P1. The quota is bookkeeping: an empty budget, failed-step cost discarded, no accounting for probes or tasks, no timeout, missing stops | `probes-certificate.json` (`failed_step_cost`) | a mandatory budget; failed-step, probe and task consumption charged; `execution.timeout_seconds` (default 3600) with the failed call's wall time charged; a start that fails three times with one error stops (its key is kept so a retry cannot launch a second run); stops for three iterations without progress and for a metric regression; `reopen` for the owner | `QuotaTests` (seven tests), `ResumeTests.test_three_iterations_without_progress_...`, `test_a_metric_regression_...` |
| 8 | P1. Campaign ids repeat within a second, concurrent `init` both succeed, journal appends can duplicate, deep state corruption escapes as a traceback | `probes-certificate.json` (`same_second_campaign_key_collision`) | a random campaign id; the existence check inside the lock; the journal idempotent on the step key; a malformed-state JSON error and a catch-all in `main` | `IsolationTests`, `StateTests.test_concurrent_initialisations_...`, `ResumeTests.test_a_crash_before_the_journal_...` |
| 9 | P2. The readiness contract reruns effectful probes inside exit checks | review text | removed: readiness is a gate that records its result; there is one contract kind | `ContractTests.test_there_is_no_readiness_contract_...` |
| 10 | P2. The card's shell binding fails under zsh and with spaces; the definer's wrapper is not what `adapter-check` reads | review text | `loop()` and `until_loop()` functions with quoted paths; the definer writes a bare `adapter.proposed.json` and `adapter-check --proposal` validates the wrapper (slots, evidence, no grader among the candidate paths) | `CardTests.test_the_card_binds_its_scripts_as_functions_...` (bash and zsh, a space in the path), `ProposalTests` |

## Round 2: Astra's second max review of the hardened build (2026-11-15)

**Subject.** `498a98b172c25b9e6733ec8a332c2500691fc2e8` (the hardening) merged with published main as
`163f21f2e9724ff61611f71a3311bc360ed25a41` (no source change). Same conditions as round 1: Codex `gpt-6-astra` at max, read-only, one
attempt, no fallback, 11 minutes (`round2-run.json`); `git status` was identical before and after. Files: `round2-brief.txt`,
`round2-answer.txt`, `round2-evidence.json` (the reviewer's reproductions).

**Result.** *Not ready to ship.* Of the ten round-1 findings the reviewer judged four FIXED and six PARTLY fixed, and reported eight
new or remaining issues (six P1, two P2) and two instruction bugs. It also found the ordinary runtime path improved: read-only
queries and receipt recovery changed no campaign content, `campaign.lock` caused no fingerprint churn, `.git` writes stayed excluded,
and gate zero disables the first-pass shortcut. Status: **firm** (reproduced by the reviewer), except where a row says judgement.

| # | Round-2 finding | Disposition | Tests |
| --- | --- | --- | --- |
| 1 | P1. The real runtime still accepts stale satisfaction: (a) `.git/info/exclude` hides `campaign.json`; (b) a Git error records `tree: null` and the runtime then skips freshness; (c) an in-scope unknown added after the checks but before the fingerprint; (d) a changed pinned adapter outside both workspaces | (a) fixed: `init` writes a folder `.gitignore` of `!*` (it outranks `.git/info/exclude` and the user's global excludes) and every check and `contract` run `git check-ignore` and `git add -A -n`, exiting 2 on an ignore rule or a Git failure. (b) fixed on this side: the checks cannot pass on a folder Git cannot read; the vendored runtime's null-tree behaviour is `improve`'s validated copy and was not changed. (c) and (d) not fixable by the script: disclosed in the card and `references/until-loop.md` (one session at a time; verify and report back to back) | `FingerprintTests` |
| 2 | P1. A material record with `"cases": "A1"` leaves its scope; a persisted review `valid: "false"` still converges | fixed: record `cases` and `target` are validated when fetched; saved iterations are validated with the same rules as fresh evidence and their `quiet` flag is recomputed on every load | `EvidenceTests.test_a_record_with_a_malformed_cases_...`, `test_a_persisted_review_flag_...`, `test_a_persisted_quiet_flag_...` |
| 3 | P1. A running step does not block completion; a converged campaign stop survives a new open task | fixed: C5 fails while a step is running or a launch's outcome is unknown; a converged stop is stale while a step runs or a task is open | `EvidenceTests.test_a_running_step_...`, `test_work_added_after_a_converged_stop_...`, `test_a_start_that_failed_may_have_launched_...` |
| 4 | P1. Readiness claims outlive their evidence: a state without evidence is accepted; quality claims survive a changed evaluator; a later failing readiness leaves the certificate converged | fixed: a proven claim needs evidence; claims are recorded with their evidence and the scoring identity and are withdrawn when it changes; the latest readiness must show the start rule (check C7) and gates the next start | `ReadinessTests` (three new) |
| 5 | P1. The quota is bypassable: completion at exhaustion; polling continues under a spent budget; repeated readiness; a failing probe forgets earlier probes' cost | partly fixed, partly judgement: the budget is checked before every probe and the cost of finished probes is kept when one fails; a failing poll is bounded (three, or one once the budget is used). *Judgement, not changed:* a contract can complete on the step that used the last of the budget, because the budget is checked between steps (the repository's own rule calls budgets post-hoc); the report states scope converged and campaign incomplete, and the card says so | `QuotaTests` (four new), `test_an_exhausted_budget_...` now asserts both statuses |
| 6 | P1. `cleanup` runs the adapter's cleanup with no ratification | fixed: cleanup needs the ratified boundary and is not run for an empty set | `GateTests.test_cleanup_is_an_adapter_command_...` |
| 7 | P2. Crash replay recomputes the launch base from the live build and marks the original receipt invalid (a regression of mine: the live-base change of the hardening commit) | fixed: a launch intent (base, scope, cases) is saved before the adapter is called and a replay reuses it; an unknown outcome is accounted for until cleanup covers it | `ResumeTests` (three new, one kills the orchestrator mid-call) |
| 8 | P2. Proposal validation overpromises: root and absolute paths, `[null]` evidence, empty `found` slots, no link to the manifest | fixed: paths must be relative and stay inside the root, evidence is non-blank text, found and proposed slots need a typed non-empty value, and the proposal is reconciled with the manifest (evaluation class, the owner-gate list, a `needs_owner` entry for a hosted capability). Not handled: aliases through symlinks | `ProposalTests` (three new) |
| - | Instruction bugs: the action table says to repeat every `start` and `poll`; readiness pending ratification is routed to the definer | fixed in the card (a finished step means verify first; "not run" before ratification is expected) | `CardTests` |
| - | Tests conceal two failures (the quota test checked after an extra stop step; crash recovery never polled the recovered handle); the initialisation existence check was not in the mutation list | fixed: both tests rewritten, a deterministic lock-holding form of the concurrent-init test, and the mutation added | see above |

## Round 3: Sol's first max review (2026-11-15), the first after the owner moved deep reviews from Astra to Sol

**Subject.** `56e02efb798b18fc949866639214b37abffd3998` (source parent `b80ccb36d5f5992e473d63c640eebe152079c16e`, the round-2
fixes, merged with published main). Codex `gpt-6.1-sol` at max, read-only, one attempt, no fallback, 13 minutes (`round3-sol-run.json`);
`git status` was identical before and after. Files: `round3-sol-brief.txt`, `round3-sol-answer.txt`, and the reviewer's reproductions
(`round3-sol-evidence.json`, `-additional.json`, `-git-filter.json`, `-readiness-workspace.json`, `-index.json`). The brief asked for
the *class* of defect (every piece of campaign state against the certificate, the quota and the gates), a literal run of the card, and
the runtime; the quick tier ran beside it: 23 suites, PASS, 301.4 s.

**Result.** *Not ready to ship*: six P1 findings and one P2, all reproduced. It also found the literal operator drill (adapter-check
through stop and report, two scopes, receipt recovery) **succeeded**, the sibling-receipt arrangement sound, gate zero effective, the
disclosed limits honest, and it disagreed with Astra on one point (a scope that converges on the last authorized step is not invalid;
my docs contradicted that in two places, now fixed). Four of the six P1 findings are things Astra's two rounds had not found.

| # | Round-3 finding | Disposition | Tests |
| --- | --- | --- | --- |
| 1 | P1. Git can hide campaign changes without ignoring files: an `assume-unchanged` or `skip-worktree` flag on a staged state file, or a `.gitattributes` clean filter that returns constant content; every guard passes and the runtime completes over an incomplete certificate | fixed by changing the kind of guard: instead of looking for each cause, `fingerprint_problem` does what the runtime does (copies the real index, `git add -A`) and compares the staged blob of each state file with the file's own bytes; any mismatch or Git failure makes the check exit 2 and `contract` refuse. Closes the class (ignore rules, flags, filters, file-system monitors, a different repository) | `FingerprintTests` (real flags and a real filter) |
| 2 | P1. Fresh verification completes over an open owner-held task (the certificate omitted tasks that `next` still returned) | fixed: an open task is backlog (check C1), so no certificate converges while one is open | `EvidenceTests.test_an_open_task_...` |
| 3 | P1. A cached converged stop is revalidated against part of the state: a later deferred hunt, or spending the budget, leaves `next` and `report` saying converged | fixed: one predicate (`completion_problems`: the certificate, unrejected blind spots, the budget) decides a converged stop when it is made and each time it is read | `EvidenceTests.test_a_converged_stop_is_stale_after_...` |
| 4 | P1. Readiness evidence survives failure or belongs to another workspace: a refresh that raises keeps the old pass; `--workspace OTHER` records proofs from elsewhere; a saved readiness with `start_ok: "false"`, no claims or invented claims is accepted | fixed: a refresh records a not-passing result before it probes; `--workspace` must be the campaign's own; the recorded readiness is re-derived from its claims on every load (and runs require a ratification of this boundary) | `ReadinessTests` (four new) |
| 5 | P1. A cleanup receipt survives a retried launch killed before its exception handler; P2: a cancellation answered `running` is accepted | fixed: the receipt is voided and saved before every launch attempt, retries included; a cancellation must be acknowledged `cancelled` | `ResumeTests.test_a_kill_during_a_retried_launch_...`, `EvidenceTests.test_a_cancellation_...` |
| 6 | P1. Responsive polling is unbounded (twelve `running` polls took 1.07 s against a 0.2 s budget and cost nothing recorded), and a probe refused for missing evidence loses its reported cost | fixed: a step in flight spends the `seconds` budget as it runs; a running step is not polled once the budget is used; `execution.step_timeout_seconds` bounds any step; a refused probe's cost is collected first | `QuotaTests` (four new) |
| - | Sweep and judgement items: resolving an unknown is an unevidenced attestation; `adapter-check --proposal` compares only the proposal's own lists; adapter environment filtering missing from the mutation list; the card and references still said exhaustion makes the *scope* incomplete | fixed: `unknown resolve` needs `--evidence` (quoted in the report); a candidate may not overlap the manifest or its pinned files, and the card says what the check cannot know; the environment mutation added; the wording says the *campaign* ends incomplete | `CertificateTests`, `ProposalTests`, `CardTests` |
| - | Test gaps: the no-evidence test began from a null readiness; the cleanup mutation exercised a caught failure, not a killed retry; the fake lacked persistent running replies and refused cancellations | fixed: transition tests, a killed-retry test, a `cancel_refuse` knob (persistent running was `poll_delay`) | see above |

What stayed as a limit, now stated more precisely: a writer that changes the campaign between the last check and the runtime's own
fingerprint; the subject or a pinned adapter changed between the verify run and the report; the vendored runtime's null-tree
behaviour (the checks now refuse to pass whenever the folder is not provably visible to it).

**Mutation check of round 5.** 21 safeguards (`mutations-round5-batch1.txt`, `-batch2.txt`). Batch 1 (19 runs): 18 caught and one survivor, the pre-probe save of the readiness refresh marker (removing it changed nothing, because the caught-failure path saves the same state). Batch 2 re-ran it against a new test that kills the process mid-probe and added the git timeout and the temporary-file guard: 3 of 3. Every safeguard is held by at least one test that fails without it; that shows the tests are not vacuous, not that the safeguards are complete.

## Round 4: Sol's second max review, a verification of the round-3 fixes (2026-11-15)

**Subject.** `76693288f650fb183f7f8e960531beee931a5d7d`: the round-3 fixes (`aceb1d03a390daf51c80325e1f2465d354cfdb5b`) merged with
published main (`0f09e78e1d8e1db9899b1430916f6329820ba894`) plus a one-line catalog estimate; the reviewed skill, fixture and tests are
identical to `0f09e78e`. Codex `gpt-6.1-sol` at max, one attempt, no fallback (`round4-sol-run.json`); the reviewer wrote nothing in the
checkout. Files: `round4-sol-brief.txt`, `round4-sol-answer.txt`, `round4-sol-index.json` (where its reproductions are), and
`round4-sol-literal-card.json` (the card run from an empty directory). The brief asked, in order: re-run the reviewer's own
reproductions against the fixed code; look for regressions and false stops the fixes introduced; look for any remaining path to false
completion; run the card literally once more.

**Result.** *Not ready to ship.* Of the ten earlier reproductions nine were fixed and one was not (index flags: the guard compared the
staged bytes with the files' bytes *as they were*, so a flag set after the check still hid a later change). Two paths to false
completion remained (that guard; a cancellation that erased the seconds a step had spent), and the fixes had introduced one P1
regression and four P2 defects, all reproduced; one more item was a judgement. The literal operator drill passed. 157 tests passed in
122.3 s at that commit. Six of the eight findings (1 to 6 below) are defects of the previous round's own changes (a guard that
did not hold, the step charge at cancel and at a failed poll, the readiness re-derivation, the line-ending refusal, a stranded run
after an upgrade), and the round-3 text claimed the resolution of an unknown was quoted in the report when it was not (finding 7): the
reason to review fixes and not only features. Status: **firm**.

| # | Round-4 finding | Disposition | Tests |
| --- | --- | --- | --- |
| 1 | P1. Snapshot equality does not prove the fingerprint will hold a later change: an `assume-unchanged` or `skip-worktree` flag set after staging, a static clean filter that returns a saved copy of the current bytes, and an unmerged entry in a path the runtime excludes (`git write-tree` fails, the runtime records no fingerprint and skips freshness) each pass every check, and the runtime then completes | fixed by changing what is checked from today's content to what the next change needs: no index entry is flagged or unmerged (`git ls-files -v`: any tag other than `H`), no Git filter applies to a state file (`git check-attr filter`), `core.fsmonitor` is not a hook command (the built-in values are accepted), and the runtime's own procedure (`git add -A` into a copy of the index, then `git write-tree`) must succeed and stage what `git add` makes of each state file. The comparison uses `git hash-object` *with* filters, so ordinary line-ending conversion is not refused | `FingerprintTests` (six new, three replaced) |
| 2 | P1. Cancelling a running step erased the seconds it had spent: 0.403 s used of a 0.3 s budget became 0 after `cancel`; after cleanup and `reopen` with the same budget the campaign converged | fixed: ending a step (finished, failed or cancelled) charges at least the wall time since it started | `QuotaTests.test_cancelling_a_step_keeps_the_seconds_it_ran_so_a_reopen_cannot_launder_them` |
| 3 | P1. A readiness that proved both sensitivity and calibration made its own campaign unreadable: the saved file sorts claim keys, the re-derivation on load listed the allowed claims in another order, and the list comparison called the state malformed (`status` and a new readiness both exited 2). A regression of the round-3 re-derivation | fixed: one canonical (sorted) derivation order | `ReadinessTests.test_a_readiness_with_sensitivity_and_calibration_proven_survives_a_reload` |
| 4 | P2. A failed poll while a step ran was charged twice (about 0.114 s of the step's own wall time plus 0.106 s of the failed call exhausted a 0.2 s budget) | fixed: the failed call's time is not added while a running step already accounts for it | `QuotaTests.test_a_failed_call_while_a_step_runs_is_not_charged_twice` |
| 5 | P2. Ordinary `core.autocrlf=true` normalisation made every check and `contract` exit 2 with Git clean and the state unchanged | fixed with finding 1 (hash with filters); line-ending conversion is not a hiding mechanism | `FingerprintTests.test_crlf_normalisation_is_not_a_hiding_mechanism_and_is_not_refused` |
| 6 | P2. A run started by the parent revision lacks `started_epoch`, so after an upgrade `status`, `cancel` and `cleanup` reject it | decision, no code: a campaign belongs to the script version that created it (its identity includes the script's hash) and there are no migrations, because the repository keeps one supported version; the parent revision was never released (this is the first release), so no installed campaign can predate it. The adapter schema says to finish or abandon a campaign, including a running step, before updating the skill. Rejected: reading the step's `started` timestamp, a shim for a version nobody has | `CardTests` (the sentence is pinned) |
| 7 | P2. `contract --out` into a missing directory printed a traceback; neither report quoted what resolved an unknown | fixed: a file-system error is a JSON error; both reports list the unresolved unknowns and quote the evidence that answered each resolved one | `StateTests.test_a_file_system_error_is_a_json_error_not_a_traceback`, `CertificateTests` |
| 8 | Judgement. A hunt finding handed to a task, then investigated, then followed by a clean hunt, blocks forever (including after `reopen`), which follows the stated policy | fixed within the policy: a later hunt supersedes an earlier finding only by naming the same blind spot (same text, case and spacing aside) with `rejected` and a reason; a clean hunt does not clear what an earlier one found | `EvidenceTests.test_a_later_hunt_supersedes_a_finding_only_by_naming_it_and_rejecting_it_with_a_reason` |

What the reviewer confirmed sound: staging, committing, global excludes, split indexes and a different `TMPDIR` pass the Git guard;
readiness before ratification stays usable; the literal card drill (two scopes, receipt recovery, the owner-gated stop) passes. What
stays a limit: an active native file-system monitor daemon could not be exercised (the guard refuses a hook command, not a daemon that
misreports); a writer between the last check and the runtime's own fingerprint; the subject or a pinned adapter changed between the
verify run and the report; the vendored runtime's null-tree behaviour (now guarded on this side by the `write-tree` requirement).

**Mutation check of round 6.** 23 safeguards, 22 caught on the first pass and the one miss closed by a sharper test; see "Mutation check of the new tests", below.

## Judgement items and what stayed as it was

- *Boolean fields cannot prove an adapter ran anything.* True, and unfixable by a script. It is now stated in the card, the
  convergence reference and the adapter schema; `execution.pin` (new) puts the adapter program and every grader or check file under
  the ratified boundary hash so an unratified change is refused. The ratification, the pins and the readiness probes are the trust.
- *"Do not chase 500 lines."* Followed in spirit: the readiness contract is gone and the generic task machinery stayed small, but
  strict validation made the script larger (about 1,650 lines). Validation, durable step recovery, cumulative scopes, cleanup
  accounting, quotas and the checks stayed, as the reviewer advised.
- *Quota overshoot.* The budget is checked before each step, so one step can overshoot it (as with `--max-budget-usd`). Said so in
  the card and the schema; not changed.
- *Subject changes between the verify run and the report.* The runtime fingerprints the campaign folder, not the subject. The
  checks catch the change as stale on their next run; the card says to verify and report back to back.
- *Python 3.9 floor.* The script and the tests' fake parse under `ast.parse(feature_version=(3, 9))` (a test); no 3.9 interpreter
  was available to run them.

## Mutation check of the new tests

`mutation_check.py` (not kept: it edits the script in place and restores it) broke each safeguard once, ran the test classes that
should notice, and restored the file. **Run 1** broke 28 safeguards (`mutations-run1.json`): 27 were caught. The survivor was the
report's own stale-stop rewrite: the test reached it only through a fresh `step`, which records a new stop, so the rewrite never
mattered. A test that calls `report` directly now holds it. **Run 2** (`mutations-run2.json`) re-ran that survivor and three
safeguards added after run 1 (the report surviving a broken adapter, a step starting from the live build, an outside change to the
subject being recorded): all four caught. So 31 distinct safeguards are each held by at least one test that fails without it. That
is evidence the tests are not vacuous; it is not evidence the safeguards are complete.

**Rounds 3 and 4** (`mutations-round3-batch1.txt` to `-batch3.txt`): 29 further safeguards, the fixes from my own read-through and
from round 2. Batch 1 (24 runs): 22 genuine kills, one vacuous "kill" (my mutation of the C7 readiness check had a syntax error) and
one survivor (the first of two overlapping Git guards: a missing `.git` trips both, so the test passed with either removed). Batch 2
re-ran those two with a corrected mutation and a stub-`git` test of the first guard, and added one safeguard (a new start failure
voids an earlier cleanup): 3 of 3. Batch 3 re-ran the four round-3 safeguards (record `cases` validated, a promotion must change the
build, a build change needs a promotion, a timeout kills the process group) for a clean log: 4 of 4. Every safeguard is held by at
least one test that fails without it. Still not evidence that the safeguards are complete.

**Round 6** (`mutations-round6-batch1.txt`, `-batch2.txt`): 23 safeguards, the ones round 6 added or rewrote: the index flag check (removed outright, then once per tag: `assume-unchanged`, `skip-worktree`, unmerged), the filter check, the monitor-hook check and its built-in values, the written-tree requirement, line-ending conversion, three failure paths of the Git guard, the content comparison, the Git timeout and the temporary-file guard; the sorted readiness order; the charge for a step that ends; the skip of a double charge; hunt supersession and the clean-hunt rule; the file-system error catch; and the two report sections. Batch 1 (23 runs, 130 s): 22 caught and one missed. Ignoring the unmerged tag changed nothing, because the test that planted an unmerged entry (in a path the runtime excludes) asserted only the word "unmerged", which the `git write-tree` guard's message also contains: the test passed with either guard removed. Batch 2 re-ran it after the assertion named the index guard's own word ("flagged"): caught. Every safeguard is now held by at least one test that fails without it; still evidence that the tests are not vacuous, not that the safeguards are complete.

## Files

`astra-brief.txt`, `astra-answer.txt`, `astra-run.json` (model, effort, no fallback), `test-run-at-ff9cb35d.json`,
`probes-certificate.json`, `probes-additional.json`, `probe-runtime-stale-satisfaction.json`, `mutations-run1.json`,
`mutations-run2.json`; round 2: `round2-brief.txt`, `round2-answer.txt`, `round2-run.json`, `round2-evidence.json`; rounds 3 and 4:
`mutations-round3-batch1.txt`, `-batch2.txt`, `-batch3.txt`; round 3 (Sol): `round3-sol-*`; round 5 mutations: `mutations-round5-batch1.txt`, `-batch2.txt`; round 4 (Sol): `round4-sol-*`; round 6 mutations: `mutations-round6-batch1.txt`, `-batch2.txt`.
