# closed-loop journal

The living record of the `closed-loop` skill: each round's question, test cases, models and effort, conditions and result; each
harness or test change with its commit, reason and effect on earlier results; each finding with its status and citations. Entries
are edited, never deleted: a claim that stops holding is marked superseded with the date and the reason. Statuses: **firm**
(reproduced or measured), **interim** (one observation), **exploratory** (a reading, not tested), **superseded**.

Plan: `docs/closed-loop-plan-2026-11-15.md`. Skill: `skills/closed-loop/`. Tests: `test/closed-loop.test.py`,
`test/fixtures/closed-loop-fake/adapter.py`.

## Rounds

### R0. The plan (2026-11-15)

- **Question.** How can ShipLoop's E2E loop (run, inspect, find improvements with higher-reasoning advisors, repeat) become a generic
  skill whose subject-specific parts are discovered or defined, with an Until Loop, iteration, and escalation to a wider case set?
- **Conditions.** Plan written against the repository, the Until Loop runtime (`skills/improve/runtime/until-loop`, 0.10.1) and the
  ShipLoop E2E harness (`test/shiploop_e2e/`). Reviewer: Codex `gpt-6-astra` at max effort, read-only.
- **Result.** Astra's review changed the convergence rule (a script-owned window with `required_trivial_reviews: 0`, because a failed
  frozen check zeroes the native streak), the counters, the state model and the identity rules. Evidence:
  `docs/experiments/closed-loop-plan-review-20261115/`. Plan commit `b0285785374570c88f534480cf361778030018ac` (it cites the earlier
  ShipLoop-only plan, `e0b13db06647f92082ea650a2de86ce50e4fc20c`, which it supersedes). Status: **firm** for the Until Loop facts
  (read from the runtime and tested), **interim** for the design.
- **Owner decision, 2026-11-15.** After reading the plan: "I don't know if you need to use existing records or not. You can build
  another schema if you think that would be more opportune. I want to make progress and not worry about the past." The skill
  therefore has its own schema (`closed-loop-campaign/1`) and Phase 1 proceeded on the plan's recommended working choices. The
  earlier preference to reuse existing records is superseded by this decision.

### R1. Phase 1 build and Astra's max review of it (2026-11-15)

- **Build.** Commit `ff9cb35d46316f6ce70f92c0e418c0fad53f0e3c` (branch `feat/closed-loop-p1-ce82cb`): the orchestrator (1,219
  lines), card, references, prompts, 63 tests on a fake subject and the real Until Loop runtime; quick tier green.
- **Question.** Is it safe to ship; where can the certificate be wrong?
- **Conditions.** Astra max, read-only, one attempt; the reviewer ran the suite (63 of 63 in 122.5 s) and temporary-directory probes.
- **Result.** *Not ready to ship*: ten findings, all reproduced or traced. Status: **firm**. Table of findings, fixes and the tests
  that hold them: `docs/experiments/closed-loop-review-20261115/README.md`.
- **Finding about the first build's own suite (firm).** A suite that passes is no evidence when it encodes the defect: C1 expected a
  `verified` record without evidence to pass, the query-write test compared names not contents, the fake never returned a malformed
  report. Every regression test was therefore written against the reviewer's reproduction, and the fake subject gained knobs that
  make evidence malformed, hang, crash, regress or change identity.
- **Harness changes (hardening commit).** The fake adapter gained `catalog`, `defects`, `omit_cases`, `extra_cases`,
  `iteration_overrides`, `case_overrides`, `regress`, `fail_poll`, `hang`, `crash`, `probe_consumed`, `cleanup_unverified`, and a
  `cleanup` verb that returns a receipt. Effect on R1's numbers: none (R1 measured the pre-hardening suite).

### R2. Hardening (2026-11-15)

- **Decisions made in the session (routine; AGENTS.md, Decisions), with reasons.**
  1. *The contract's workspace is the campaign folder*, a Git repo that holds only campaign state, with the runtime's state,
     contract and receipts in the sibling `<campaign>.work`. Rejected: moving the campaign inside the subject workspace, because
     recovery rewrites the receipt and would invalidate the verify run it guards (the reviewer's note); keeping the subject
     workspace, because the checks read the campaign's evidence, which then changes outside the fingerprint (the reviewer's
     reproduction). Cost: a subject change between verify and report is not in the fingerprint; the checks catch it as stale on their
     next run, and the card says to verify and report back to back.
  2. *No readiness contract.* Exit checks only read recorded evidence; readiness is a gate that records its result.
  3. *Every start is gated* on the ratified boundary hash, a recorded readiness for that hash that shows the start rule, and every
     selected case released by the owner.
  4. *A budget is mandatory;* failures, probes and tasks are charged; every adapter call has a timeout (default 3600 s).
  5. *`execution.pin`* puts the adapter program and graders under the ratified hash. It guards against an unratified change; it does
     not make the adapter honest.
  6. *`adapter-check --proposal`* validates a definer proposal (slots, evidence, no grader among the candidate paths), because the
     prompt said a grader in the candidate set "is refused" and no script refused it.
  7. *A step starts from the live build,* not the build the campaign last recorded, so a subject edited while the owner reviewed the
     boundary is adopted (and logged) instead of making the first report look like a base mismatch.
  8. *A stop is recorded even when the adapter can no longer be queried;* the report then says its certificate is unavailable.
- **Measurements.** Suite 63 to 110 tests, 58 s on this machine (R1: 122.5 s for 63): the catalog is fetched once per command and most tests
  use the three claims the start rule needs. Lint: ruff (E, W, F, B plus PLW1510, RUF059, RUF012, FURB167; E501 ignored as the
  repository does) clean. Grammar: `ast.parse(feature_version=(3, 9))` passes for the script and the fake (a test); no 3.9
  interpreter was available to run them. The card's shell binding runs under bash and zsh with a space in the path (a test).
- **Mutation check (firm).** 31 distinct safeguards broken one at a time; each is caught by at least one test, after one test was
  added for the single survivor of run 1 (the report's own stale-stop rewrite). Results: `mutations-run1.json`,
  `mutations-run2.json` in the review folder. This shows the tests are not vacuous, not that the safeguards are complete.
- **Open (unknown), as of the hardening commit; R3 below answers the first part.** A second Astra max review of the hardened code, the
  quick tier, and CI on main. Nothing has driven the card with a model operator on a real subject; the ShipLoop adapter (Phase 2) is the first
  real subject and waits on owner decisions (the harness's continuation seam is a new scoring identity, which AGENTS.md reserves
  for the owner).

### R3. Astra's second max review, and the round it forced (2026-11-15)

- **Question.** Did the hardening fix the ten findings, and did the fixes open new paths to false completion?
- **Conditions.** Codex `gpt-6-astra` at max, read-only, one attempt, 11 minutes, on `163f21f2e9724ff61611f71a3311bc360ed25a41`
  (the hardening merged with published main). Brief, answer, run record and the reviewer's reproduction bundle:
  `docs/experiments/closed-loop-review-20261115/round2-*`. The quick tier ran beside it on the same commit: 23 suites, PASS, 260.7 s.
- **Result.** *Not ready to ship.* Four of the ten round-1 findings FIXED, six PARTLY; eight new or remaining issues (six P1, two P2),
  two instruction bugs, one missing mutation. Status: **firm**. Finding-by-finding dispositions and tests: the review folder's README,
  "Round 2". The pattern across rounds: the first review found what the code did wrong; the second found what the *fixes* did not
  cover (a running step, an unknown launch, readiness that outlives its evaluator, a Git ignore rule that blinds the fingerprint) and
  one regression of mine (the live-base change broke crash replay).
- **Provenance of two fixes.** The process-group kill at a timeout was found by me after reading a progress line of the reviewer
  ("checking timeout cleanup"), not from its answer: `subprocess.run`'s timeout kills only the direct child, so a grandchild holding the
  output pipe kept the call, and the campaign lock, alive past it (test and mutation in `AdapterProcessTests`). The record-shape,
  build-consistency, lock-wait and cleanup-invalidation fixes came from my own read-through of the code.
- **Decisions made in the session (routine; AGENTS.md, Decisions), with reasons.**
  1. *`init` writes a `.gitignore` of `!*` into the campaign folder, and every check and `contract` run `git check-ignore` and `git
     add -A -n` first.* Rejected: patching the vendored Until Loop to fail closed on a null tree or an ignored file, because
     `improve` ships it validated and the vendor test pins it; the orchestrator can instead refuse to pass a check on a folder the
     fingerprint cannot see.
  2. *A launch intent is saved before the adapter is called.* It carries the base, so a replay does not recompute it from a build the
     run already changed, and it is also the record that a launch of unknown outcome exists, which check C5 refuses until cleanup.
  3. *Completion on the step that used the last of the budget is kept, and documented.* The budget is checked between steps, so the
     iteration that spends the last of it can also converge the scope; the contract may then complete and the campaign reads
     incomplete (budget used). The reviewer counted this as a quota failure; I did not change it because the repository's own rule
     calls budgets post-hoc and the scope certificate is a true statement about the evidence. The report states both statuses.
  4. *A concurrent writer between the last check and the runtime's fingerprint, and a changed adapter between the verify run and the
     report, are disclosed, not fixed.* No orchestrator-side change can close them: the checks are separate processes and the
     runtime fingerprints after they exit. The card says one session per campaign and verify-then-report back to back.
  5. *Quality claims are bound to the scoring identity they were proven under,* and a later failing readiness withholds the
     certificate (check C7) and the next start; a changed evaluator does not by itself block a start.
- **Owner direction, mid-round (2026-11-15).** "maybe we should switch from astra max to sol max for advisors going forward." Recorded
  in memory; the review above was already running and finished on Astra. Later reviews use Sol 6.1 at max. Whether Sol at max finds
  what Astra at max found is not yet measured.
- **Measurements.** Suite 110 to 140 tests (about 100 s); every new safeguard mutation-checked: see the README, "Mutation check", for
  the counts and the three that needed a better test (a vacuous kill from a bad mutation, a guard that overlapped another, and the
  existence check inside the lock). Lint and the 3.9 grammar check as before.
- **Open (unknown).** A third review, on Sol at max, of the round-3 fixes; nothing has driven the card with a model operator on a real
  subject; the vendored runtime still records a null tree on a Git error and then skips freshness (disclosed; guarded on this side).

### R4. Sol's first max review, and the round it forced (2026-11-15)

- **Question.** After two Astra rounds, does the hardened build still have paths to false completion, and is the class closed or only
  the instances? The brief asked for the class: every piece of state in campaign.json against the certificate, the quota and the gates.
- **Conditions.** Codex `gpt-6.1-sol` at max, read-only, one attempt, 13 minutes, on `56e02efb798b18fc949866639214b37abffd3998`;
  the quick tier beside it (23 suites, PASS, 301.4 s). Brief, answer, run record and reproductions:
  `docs/experiments/closed-loop-review-20261115/round3-sol-*`.
- **Result.** *Not ready to ship*: six P1 and one P2, all reproduced, four of them new to Astra's two rounds; the literal operator
  drill passed. Status: **firm**. Dispositions and tests: the review folder's README, "Round 3". Whether Sol at max matches Astra at
  max is still unmeasured, but on this code it found things the Astra rounds had not (open tasks, killed retries, wrong-workspace
  readiness, responsive polling), which is the one data point so far.
- **What the class sweep showed.** The recurring mistake across rounds 2 and 3 was local patches to a conjunction: the certificate,
  the cached stop, the report and the gates each recomputed "converged" from a different subset of state. Round 4's main change is
  structural: one predicate for a converged campaign (`completion_problems`) used wherever a stop is made or read, tasks inside the
  certificate (C1), and the recorded readiness re-derived on every load.
- **Decisions made in the session (routine; AGENTS.md, Decisions), with reasons.**
  1. *Prove visibility by content, not by hunting causes.* **Superseded 2026-11-15 by R5:** a comparison of today's bytes cannot see a
     later change, so the cause-by-cause guards rejected here are in the guard after all, beside the runtime's own procedure. Reject: more guards for `assume-unchanged`, `skip-worktree` and filters one
     by one (the review had already found two new causes after the ignore-rule guard). Instead `fingerprint_problem` runs the
     runtime's own procedure on a copy and compares each state file's staged blob with its bytes; anything that makes them differ,
     whatever the cause, fails the check.
  2. *A step in flight spends the `seconds` budget as it runs, and a running step is not polled once the budget is used.* This
     replaces the round-3 rule that polled a step to collect its result after exhaustion (a poll that kept answering `running` could
     continue without bound and charged nothing). A step also ends the campaign past `execution.step_timeout_seconds` (default 21600).
     The price: a step the budget outlasts mid-run is stopped for the owner, who can cancel it or reopen with a larger budget.
  3. *Completion at the final authorized step stays valid for the scope certificate* (Sol agreed; the docs contradicted it in two
     places and now say "the campaign ends incomplete"), but the *campaign* status needs the budget unspent at every read.
  4. *Resolving an unknown needs evidence,* a refreshing readiness withdraws the old result first, and a cleanup receipt is voided
     before every launch attempt: each was a place where an attestation or a receipt could outlive what it vouched for.
- **Measurements.** Suite 142 to 157 tests (114 s). 21 further safeguards mutation-checked, all caught after one test was added for the single
  survivor of the first batch (a kill-mid-probe test of the refresh marker); logs in the review folder. Lint and the 3.9 grammar check as before.
- **Open (unknown).** **Superseded 2026-11-15 by R5** (a fourth review was run and found three P1 defects). A fourth review is not planned: each round has found fewer and narrower defects, the class sweep is now
  structural, and the remaining limits are disclosed. Nothing has driven the card with a model operator on a real subject, and the
  vendored runtime's null-tree behaviour is unchanged (guarded on this side).

### R5. Sol's second max review, a verification of the fixes, and the round it forced (2026-11-15)

- **Question.** Do the R4 fixes hold, did they introduce regressions or false stops, and is any path to false completion left? R4 had
  planned no fourth review; one was run before shipping because R4 had changed the Git guard, the accounting and the certificate at
  the same time, which is where a fix is most likely to break a neighbour.
- **Conditions.** Codex `gpt-6.1-sol` at max, one attempt, no fallback, read-only, on `76693288f650fb183f7f8e960531beee931a5d7d`
  (the R4 fixes `aceb1d03a390daf51c80325e1f2465d354cfdb5b` merged with published main, plus the catalog estimate of `76693288`). Brief,
  answer, run record, reproductions index and the literal card drill: `docs/experiments/closed-loop-review-20261115/round4-sol-*`.
- **Result.** *Not ready to ship*: of ten earlier reproductions nine fixed and one not (index flags), two paths to false completion
  (a guard that compared today's bytes, and a cancel that erased spent seconds), one P1 regression (a saved readiness made its own
  campaign unreadable), four P2 defects and one judgement item. The literal operator drill passed. Status: **firm**. Dispositions and
  tests: the review folder's README, "Round 4". Six of the eight findings (the guard that did not hold, the step charge at cancel and at a failed poll, the readiness
  re-derivation, the line-ending refusal, a stranded run after an upgrade) were defects of my own R4 change, and R4's text claimed that
  a resolved unknown was quoted in the report when it was not, so reviewing the fixes paid; this is the second data point that Sol at max finds what Astra's rounds did not (the first was R4's four new P1 findings).
- **Decisions made in the session (routine; AGENTS.md, Decisions), with reasons.**
  1. *Guard what the next change needs, not today's content.* The index flags, Git filters and a file-system monitor hook are refused
     outright, the runtime's own procedure must finish with a written tree, and the staged blob is compared with `git hash-object`
     *with* filters so line-ending conversion is not refused. This reverses R4 decision 1: a snapshot comparison passes while a flag or a
     static filter is in place and then hides the next change. Cost: a rare false stop (a campaign folder mid-merge is refused even for
     a state file, where the runtime's `git add -A` would have resolved the conflict; checked in a scratch repository on 2026-11-15);
     the message names the command that clears each cause.
  2. *Ending a step charges at least the wall time it ran, and a failed call while a step runs is not charged again.* The R4 rule
     made a running step spend `seconds` as it runs; its terminal transitions then forgot it (cancel) or doubled it (a failed poll).
  3. *No migration for a campaign from an earlier revision.* The repository keeps one supported version and the parent revision was
     never released; the docs say to finish or abandon a campaign before updating the skill. Rejected: reading a running step's
     `started` timestamp, a shim for a version nobody has.
  4. *A later hunt supersedes an earlier finding only by naming it and rejecting it with a reason.* Keeps the policy (a finding is
     never silently dropped) and gives it an end.
  5. *A test that passes with either of two guards removed proves neither.* The mutation check found the unmerged-entry test doing
     this (both guards' messages contain "unmerged"); the assertion now names the index guard's own word.
- **Measurements.** Suite 157 to 165 tests, 126.0 s in the full run (114.4 s alone for 157 tests at `76693288`; the estimate in
  `test/suite_durations.json` stays 115.0 and the decision rule written in that commit stands: a CI receipt above 120 s on Linux
  forces the split-or-exception decision). 23 safeguards mutation-checked: 22 caught on the first pass, the one miss closed by the
  sharper assertion (README, "Mutation check of the new tests"). Lint and the 3.9 grammar check clean.
- **Open (unknown).** No further review is planned before 0.1.0; every max review so far has said "not ready", with narrowing
  findings (Sol: six P1, then three), and the fixes of this round are verified by tests and mutation checks, not by a reviewer.
  Nothing has driven the card with a model operator on a real subject. An active file-system monitor daemon was not exercised. The
  vendored runtime's null-tree behaviour is unchanged (guarded on this side by the written-tree requirement).

## Findings

| # | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F1 | A script-owned quiet window needs `required_trivial_reviews: 0`: a failed frozen check sets the native streak to zero, so two counters make convergence take three passes instead of two | firm | `test/closed-loop.test.py` `UntilLoopTests`; `until-loop-exit-checks-0-8-0` memory; runtime `until_loop_ephemeral.py` |
| F2 | The Until Loop's freshness check binds to a workspace's Git tree: bind it to the folder that holds every fact the checks read, not to the subject | firm | `probe-runtime-stale-satisfaction.json`; `UntilLoopTests.test_a_state_change_made_through_the_sanctioned_verbs_...` |
| F3 | A certificate is only as strong as the validation of what it reads: types, exact case set, identities and finite amounts are checked before evidence counts | firm | `EvidenceTests`; mutation run 1 |
| F4 | Marginal coverage misses interactions: a catalog of AX, BY, AY leaves AY unselected unless the pair is a declared combination | firm | `EvidenceTests.test_declared_combinations_...`, `..._without_declared_combinations_...` |
| F5 | The script cannot prove an adapter reported truthfully; the ratified boundary, the pinned files and the readiness probes are the trust | firm (a limit, stated in the card) | `references/convergence.md`, `references/adapter-schema.md` |
| F6 | The budget is checked between steps, so one step can overshoot it; hung and failed calls are charged | firm | `QuotaTests` |
| F7 | The Until Loop's fingerprint is `git add -A` into a private index: an ignore rule hides a file from it and a Git error makes it unavailable, after which the runtime skips freshness. A folder `.gitignore` of `!*` outranks every other ignore source, and the checks refuse to pass when Git cannot see the folder | firm | `FingerprintTests`; `round2-evidence.json` |
| F8 | A launch the campaign does not know the outcome of (a crash or a timeout after the adapter may have started it) must be written down before the call and counted as unclean until cleanup covers it; a replay must reuse the recorded base | firm | `ResumeTests`, `EvidenceTests`; the live-base regression I introduced and the reviewer found |
| F9 | A claim readiness proves is about an evaluator: it must carry its evidence and the scoring identity, and lapse when the identity changes | firm | `ReadinessTests` |
| F10 | `subprocess.run`'s timeout kills only the direct child: run the adapter in its own session and kill the process group, or a grandchild holding the pipe keeps the call alive | firm | `AdapterProcessTests` |
| F11 | A guard that proves today's content cannot prove a later change will show: refuse whatever can freeze or rewrite what the fingerprint holds (index flags, filters, monitor hooks) and require the runtime's own procedure to finish, not a snapshot that matches | firm | `FingerprintTests`; `round4-sol-answer.txt`; `mutations-round6-batch1.txt` |
| F12 | A step that ends must not erase what it spent, and what a running step already accounts for must not be charged again: charge at least the wall time since start at every terminal transition | firm | `QuotaTests`; `round4-sol-answer.txt` |
| F13 | A re-derivation compared by list order breaks when the saved file sorts its keys: derive in one canonical order, and test the reload of the richest state (every optional claim proven) | firm | `ReadinessTests`; `round4-sol-answer.txt` |
| F14 | A test whose assertion two guards both satisfy proves neither; assert the guard's own words. A mutation check finds this, a green suite does not | firm (one instance) | `mutations-round6-batch1.txt`, `-batch2.txt` |
