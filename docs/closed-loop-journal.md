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
- **Tier and release (2026-11-15).** Quick tier on the merged tree (`2512e16c85c83d573ed98a60b0d85565f1b7f893`, pinned
  `--changed-from 20ec94e273fa88266c2b18a7b22cbb8a066ba6e0`): 23 suites, PASS, 282.1 s wall at `--jobs 8`; the closed-loop suite
  inside it: 165 tests OK in 155.8 s (the slowest suites were shiploop-navigator-contract 282.0 s and shiploop-keepalive 175.7 s).
  The same suite on the release tree: 165 tests OK in 194.1 s with other work on the machine. So one suite's wall time was 126.0,
  155.8 and 194.1 s on one machine within the hour: the 115.0 estimate is low, the rule of `76693288` stands (a CI receipt above
  120 s on Linux forces the split-or-exception decision), and a split is the likely answer if it does. Release cut with
  `scripts/release.py` in a clean detached worktree: `1562e8a99fe2b1cc930d48b57176f8549db0def8` (`release: skill-craft 2.41.1,
  closed-loop 0.1.0`, tree `4a4123185c8f66a82627bb37efe3409824086e19`), checked with `scripts/check-release-boundary.py` and the
  closed-loop suite on the release tree, and published with `scripts/release-push.py` (expected base
  `20ec94e273fa88266c2b18a7b22cbb8a066ba6e0`, the four release checks) as one push of the feature range and the release commit, so
  no pending note ever sat on main. Evidence: `docs/experiments/closed-loop-review-20261115/quick-tier-merged.txt`, `release-2.41.1.txt`.
- **Open (unknown).** No further review is planned before 0.1.0; every max review so far has said "not ready", with narrowing
  findings (Sol: six P1, then three), and the fixes of this round are verified by tests and mutation checks, not by a reviewer.
  Nothing has driven the card with a model operator on a real subject. An active file-system monitor daemon was not exercised. The
  vendored runtime's null-tree behaviour is unchanged (guarded on this side by the written-tree requirement).

### R6. Phase 2 plan (the ShipLoop adapter) and two Sol reviews of it (2026-11-15)

- **Question.** After the release, what is the cheapest safe route from `closed-loop` 0.1.0 to a real campaign on ShipLoop's E2E harness,
  and what must be true before any real run is spent? The first plan (R0) had assumed one batched harness change (decision 6: a new
  scoring identity and a re-baseline) and a two-operator drill. Plan: `docs/closed-loop-phase2-plan-2026-11-15.md`.
- **What reading the harness showed** (cited in the plan's section 1): the harness already has a qualified loop and a durable epoch
  controller; a loop can continue from a positioned checkout without an engine edit, because the improver cannot touch the scoring files and
  the loop's commits are outside the identity; the October calibration no longer matches the scoring files; 14 material ShipLoop records are
  unresolved and three of them name no case, which blocks every scope; and baseline rows, model processes and staged ledger rows each
  escape a naive facade.
- **Reviews.** Codex `gpt-6.1-sol` at max, read-only, one attempt, no fallback (`docs/experiments/closed-loop-phase2-review-20261115/`).
  Round 1 (13 minutes, draft 1): "not ready for real compute", nine findings, each checked against the code and folded into version 2.
  Round 2 (15 minutes, version 2): "not ready", seven findings (a smoke the orchestrator stops after one iteration; model processes that
  survive a kill; staged ledger additions a plain diff misses; a relabelled PROMOTE that fails validation; incomplete baseline semantics;
  publication replay and import roots; unbounded coverage claims), checked and folded into version 3. Version 3 has not been reviewed
  again; its gate G1 puts a review of the facade's contract, with code and tests in front of the reviewer, before any compute.
- **Decisions made in the session (routine; AGENTS.md, Decisions), with reasons.**
  1. *Keep the facade-only route.* Two reviews attacked the continuation claim and neither broke it; a harness edit would cost a new
     identity and fresh baselines while other sessions commit to the harness daily; each trigger that would justify one is measurable.
  2. *No real compute before model-free tests (G1).* Both reviews found contract mismatches that only code and tests expose.
  3. *The smoke is one iteration at a quiet window of 1,* because the orchestrator stops `blocked` once only owner-gated records remain.
  4. *No third plan review.* The remaining findings are implementation details that G1 reviews against code; a third round of a plan
     returns less than the first two did.
- **Measurements.** Reviews: 792 s and 882 s (their run records). Plan: 416 lines. No code, test or skill file changed.
- **Open (unknown).** The plan's section 8; your decisions on the five records of its appendix A and on section 6.

### R7. Phase 2 build, first round: the facade's step machinery, the fact derivations, and a real-engine check (2026-11-15)

- **Question.** Can the plan's step contract (plan 3.2 to 3.5) be built so that every fact the orchestrator needs is read from what the
  harness writes, and shown against the real loop and not only against the facade's idea of it? Owner decision before this round:
  "Approve, start W1" (the plan's picks, route facade-only, no harness edit; the five record decisions of appendix A stay the owner's).
- **What was built** (`test/shiploop_e2e/adapter/facade.py`, 1,450 lines, stdlib only, Python 3.9 grammar): the step verbs `step start|poll|cancel`
  and `cleanup`, a detached worker whose liveness is an OS file lock, write-ahead step records, hygiene of the evaluator clone with
  baseline capture from both destinations, a process snapshot taken before a cancel signals anything, kill salvage, two-phase tip
  publication with replay, and the derivations of plan 3.4 (cases, review and judge, discoveries by ledger diff, candidate, acceptance, tier
  receipts, cleanup receipt, consumed).
- **Tests.** 32 step tests on a stand-in engine (`test/fixtures/closed-loop-adapter/fake_iterate.py`: the loop's observable contract, with
  knobs), and 2 tests that run the **real** `iterate.py --qualify` through the facade with one fake `codex` answering every role
  (`fake_codex.py`; a research subagent built the recipe). The orchestrator's own `validate_facts` checks every iteration a test receives.
- **Decisions made in the session (routine; AGENTS.md, Decisions), with reasons.**
  1. *A failed or cancelled step publishes no tip.* The engine's INTERRUPTED path commits a deferred record before it re-raises (commit
     ba51c3f4e74ea8731ac03959675d6e47b5d91c37), so publishing after a failure would move the loop on to other records and hide a repeated
     failure; the orchestrator's own rule (three identical failures stop the campaign) is the owner's stop-and-report rule, so the redo
     stays visible. The interrupted ledger is in the archive.
  2. *A cycle ends the step* (not only a promotion, as plan 3.3 said), because the iteration object carries one candidate.
  3. *Timing validity is not evidence validity.* Plan 3.4 sent "attribution or timing not true" to `invalid`; promotion needs timing only for
     minutes, and the October calibration's sixteen timing-invalid attempts still served the token claim (commit
     3423e21801165d86c21e1d9e59d5c55d130bff66). Only an attribution that is false is reported as invalid.
  4. *`cleanup` also stops a live step's worker*, because a launch whose handle was lost can be ended only there (the orchestrator calls
     `cleanup` for such a launch and has no recorded step to cancel).
  5. *The runs-root variable is removed from the engine's environment, never set* (commit 8493c5b9fc3b4fa6bac67588521e90912ff71592).
  6. *The strict outcome is the harness's own function, run in the bridge process* (not re-stated), so it cannot drift; a rename fails loudly.
- **Second part of the round: the probes, the owner verbs, the manifest, a dress rehearsal.** `probe` proves four claims (`cases.runs:hello` by one
  real run in a clone, `grading.scores` by two identical scorecards of the stored run, `improver.bounded` by a build, the quick tier and a caught
  planted edit, `grading.calibrated:PROFILE` by a calibration report for that driver); `grading.sensitive` and `improver.invocable` are not
  declared. `backlog` and `decide` are the only way the owner's decisions reach the ledger the loop reads. With fake hosts the real
  `closed_loop.py` ran init, ratify, readiness (all four probes at the states the plan promised, start rule holding), steps until it recorded an
  iteration it accepted, cleanup and the certificate, and nothing in the verbs' JSON had to change. Two more decisions: (7) the manifest's profile
  is Codex `gpt-6.1-terra` at `high`, tolerance 0.45 and 3 attempts stated (D1 stays the owner's) and 2 attempts at once (the one measured
  cycle pilot, commit 3301eae58c75e3afdc5e738656308d56df7467ee, ran PARALLEL=2 with 3 attempts per arm at effort xhigh); (8) a probe works in a clone under the
  state folder, never in X.
- **Open (unknown).** Orphaned model sessions after a worker that died unobserved (a reviewer, judge or improver session is in a session of its
  own and is in no lifecycle ledger; a cancel snapshots them, a SIGKILL of the worker alone does not); the owner-decision path (an `owner`
  accept must reach the tip's ledger: the `decide` verb of W3); D1 and D3 (the tolerance-and-attempts rule and the loop limits) are open
  owner decisions that plan section 6 does not list.

### R8. Gate G1: Sol's max review of the built facade, and the round it forced (2026-11-15)

- **Question.** Plan gate G1 puts a max review of the facade's contract, with code and tests in front of the reviewer, before any real compute. Is the
  facade, as built (commit 441b9edb4f6fbb990d1401c56538ac8bad0c49f3), ready for the first real compute?
- **Review.** Codex `gpt-6.1-sol` at max, one attempt, no fallback, `workspace-write`, in a neutral clone; 974 seconds; verdict **not ready**, eleven
  findings (ten verified bugs, one likely) and four judgements (`docs/experiments/closed-loop-phase2-review-20261115/g1-sol-answer.txt`, brief and
  witnesses beside it). It found no false QUIET from ordinary completed artifacts, confirmed the six decisions of R7, and found the derivations of the
  loop's own paths sound. I checked each finding against the code before accepting it; all eleven held, and two of them (the cancel and cleanup race
  against a booting worker, and the evaluator finding that keeps an iteration from being quiet) I had already found myself minutes earlier.
- **What changed (each with a regression test).** (1, 3) cancel and cleanup rewrite a step's record only while holding the step's lock, and a worker
  that is only finishing is waited for, never stopped; (2) a kill's outcome (a group that survived, one that could not be signalled or verified, sessions
  below the worker that survived) is part of what a cleanup proves, so a cleanup with a survivor is not verified; (4, 5) one workspace admission lock
  covers `step start` and `decide`, and an unsettled step (running, starting, or prepared, with or without a live worker) blocks both; (6) a start replay of
  a step that has since failed or been cancelled answers `running`, the orchestrator's only other accepted word being `done`; (7) the last judge assessment of
  an exploration (`review-judge-retry-N`) and the last review event per epoch attempt are the assessments that count; (8) a case's `needs`, `platform` and
  `base` from the harness catalog travel as the case's `requires`, so the orchestrator gates a browser case (a test had pinned the empty list); (9) a
  calibration probe needs sealed attempts and compared splits, not only a matching digest; (10) a worker's start-up failure is a durable failed step, a
  poll respawns a worker at most three times, and an unavailable `ps` is an error; (11) a group whose leader is gone is not signalled when its record is
  older than twelve hours. Test fixes: an ancestry check that compared a helper's empty stdout, the certificate the rehearsal never read, the poll storm's
  swallowed thread errors. Added: two real-orchestrator controls on stand-in evidence and an empty ledger (quiet and comparable evidence converges a scope
  in two iterations; evidence that misses its floors never does), which the real-engine suite cannot give because fake hosts leave fidelity unobserved.
- **Decisions made in the session (routine; AGENTS.md, Decisions), with reasons.** (9) Evaluator findings (records with `target: harness`) are not
  `discoveries` of a subject iteration: the adapter contract says they never block a subject certificate, and a recurring one would otherwise keep the
  quiet window from closing. (10) An unsettled step blocks a new step and an owner decision until a poll or a cleanup settles it, even when its worker is
  dead: the evaluator clone, its worktrees and the tip are that step's until then. (11) The planted-edit half of `improver.bounded` stays what it is, a test of
  `boundary.candidate_path`; it would not notice enforcement removed from `iterate.improve` or `cycle._qualify_impl`, and the README says so.
- **Not fixed, said plainly.** Reviewer, judge and improver sessions of a worker that died unobserved are in no ledger (a cancel finds them); real
  kill and recovery trials need durable ownership for them; a recycled group number with an absent leader is now bounded by an age, not excluded.
  The probes' positive controls still run on fake hosts. The review ran on the snapshot before the fixes; the fixes themselves have not been reviewed again
  (one more round of review returns less than the first, but a reviewer reading these diffs is the way to learn whether they introduced a defect).

### R9. Sol's verification review of the G1 fixes, and the round it forced (2026-11-15)

- **Question.** Did the fixes of R8 (commit fc5b3d5e, on main as a9d40c30) close the eleven findings without opening new defects, so that the readiness
  probes and a one-iteration smoke campaign can run?
- **Review.** Codex `gpt-6.1-sol` at max, one attempt, no fallback, `workspace-write`, a neutral clone of main; 872 seconds; verdict **not ready**
  (`docs/experiments/closed-loop-phase2-review-20261115/g1b-sol-*`). Of the eleven: five FIXED, six PARTLY. Seven new or remaining defects, each marked
  verified bug with the reviewer's own witness. I checked each against the code before accepting it; all seven held. It found no lock-order cycle.
- **What the review showed about the first fixes.** The rule of R8 (whoever is not the live worker rewrites a step's record only under the step's lock)
  was applied to cancel and cleanup but not to every writer: the poll published a finished step outside the lock, a respawn checked its grace outside the
  lock, and a start read the tip before it checked for unsettled steps. A lock obtained at once was taken as proof that the worker's group was gone, though a
  worker killed alone frees its lock while its engine still runs in the group, so cleanup reported verified with a live process left. `kill_step` collected
  the sessions below a group before deciding whether the group was provably the worker's, and signalled them even when it was not.
- **What changed (each with a deterministic regression test, and each test mutation-checked: breaking the fix makes it fail, 9 of 9).** One owner for
  every rewrite and publication: `advance` publishes, respawns and settles only under the step's lock, after a reload, and re-checks the boot grace there;
  cancel and cleanup publish a step that finished rather than discard it (`finish_publication`). `end_leftovers`: after the lock is held, a kill of whatever a
  dead worker left in its group, and any kill result counts toward the verdict whatever state the record reached. `group_verdict` decides ownership before
  anything is collected or signalled; the age rule reads the epoch time stored in the worker's identity (`at`), not ps's local-time text, and an identity with
  no time proves no ownership of a leaderless group. `step_start` reads the tip after the unsettled check. `epoch_evidence` counts an attempt as reviewed the way
  `epoch.state` does (its last reviewed receipt with its seal intact) and takes the last decision; a parity test on the real engine's epoch compares the two.
  The calibration probe needs a positive whole number of attempts and a recommendation that `spread.recommend` gives from the report's own rates.
- **A fault of the test apparatus, found while measuring.** On the final tree the real-engine suite failed 3 of 5 ("the engine exited 1 on hello"): the real
  loop's `iterate.record_learnings` runs `git commit` with the caller's git identity, the suite's throwaway home had none, and git's fallback guess
  (`user@hostname`) is refused when the hostname has no dot. This Mac's hostname had become a dotless identifier that day (`git var GIT_COMMITTER_IDENT` in an
  empty home: "unable to auto-detect email address (got 'user@<identifier>.(none)')"); the same suite had passed on a9d40c30 earlier the same day. The suite's
  home now carries its own identity: 5 of 5 OK in 96.8 s. Not a facade defect: in real use the engine runs with the owner's home, which has an identity.
- **Decisions made in the session (routine; AGENTS.md, Decisions), with reasons.** (12) Cancel and cleanup publish a `prepared` step: it finished, and
  throwing its result away would make the next step redo it. (13) Re-state the epoch's review rule in the facade (with the parity test) instead of calling
  `epoch.state`, which needs a fully frozen epoch the stand-in engine does not build. (14) The age rule uses the recorded epoch time, so a time-zone change or a
  DST fold cannot move it.
- **Open (unknown).** These fixes are not reviewed yet; R8's were not either and the review found siblings of them, which is the reason for another round.
  The residual gaps the reviewer named remain stated: reviewer, judge and improver sessions of a worker that died unobserved are in no ledger; recent group
  ownership is shown by the record's age, not proven.

### R10. A failure that was not the code, Sol's third verification, and a replan (2026-11-15)

- **Question.** Did round R9's changes cause the real-engine suite's three failures, and what does the verification of R9 (review round 5) say about
  readiness for the first real compute?
- **Experiment: the git identity, controlled** (`docs/experiments/closed-loop-phase2-review-20261115/identity-failure-evidence.txt`). A clone of
  4e36b3ad486b30fce972e697096fcfa158c29e3d with only the suite home's git identity removed fails the same three tests (59.0 s) and passes the other two;
  with the identity, 5 of 5 (96.8 s). Each failed engine log ends in `iterate.record_learnings` at `git commit` (the harness's git helper drops git's
  stderr, so the log names the command, not the reason). Replaying each failed loop's staged learnings, taken from the facade's salvage archive, with the
  same message and home: refused without an identity, committed with one, 3 of 3 each way. Cause: `~/.gitconfig` names no email, so git guesses one from
  the hostname; the Mac has no fixed hostname, and at 20:44:57 macOS took a dotless one from the home router's reverse-DNS answer (`configd`, IPMonitor),
  which git refuses. **Firm.** Not a facade defect.
- **Measured reach.** On this machine in this state six loop-related E2E suites pass (725 tests), and the adapter's queries and steps suites passed after the
  change: only the real-engine suite relied on the guess (fixed in 4e36b3ad). Real runs do not pass: the loop's learnings commits (`iterate.record_learnings`,
  the cycle's) and the improver's commits (`iterate.improve` hands it `~/.gitconfig` as `GIT_CONFIG_GLOBAL`) use the owner's identity; subject, judge and
  reviewer sessions get throwaway ones (`hosts._isolated_env`). The readiness probes never reach those commits (`probe_cases_runs` runs `run.py` alone; that
  probe test passed with no identity), so readiness would have passed and the first real step failed after its subject run. **Firm.**
- **A second, separate cause: Linux CI** (`docs/experiments/closed-loop-phase2-review-20261115/linux-ci-failure-evidence.txt`). GitHub's full runs on
  a9d40c30 and on 4e36b3ad failed the same three tests, and neither failure message lists an archive (the macOS identity failure always left one staged
  path), so the loop ended earlier. In a Debian container already on the machine (offline, non-root, node lent from a local image) the same three fail and
  the same two pass; every engine log ends `OSError: [Errno 7] Argument list too long: 'codex'` where the reviewer is launched. The Codex host passes its
  prompt as one argument, the reviewer prompt is 174,858 bytes (the 164,262-byte E2E spec is in it), and Linux caps one argument at 128 KiB (macOS caps the
  whole command line at 1 MiB). So the suite has never passed on CI, the harness's reviewer cannot launch on Linux at all, and the identity fix (mine in
  4e36b3ad and the same four lines another session added in fd314f5c9329cdfbe5811d045d0ed472a1068a27) does not touch it. I had not read CI's result after
  the a9d40c30 push. **Firm.**
- **Review, round 5.** Codex `gpt-6.1-sol` at max on 4e36b3ad, one attempt, no fallback, a neutral clone; 645 s; verdict **not ready**
  (`docs/experiments/closed-loop-phase2-review-20261115/g1c-sol-*`). Of R9's seven: four FIXED, three PARTLY. Six verified bugs, each checked against the code
  before acceptance; all held. (1) A repeated cleanup answers from its own call only: once a step is terminal, `end_leftovers` returns nothing, so a second
  cleanup over an unverified group says verified (a regression of R9's change to `cmd_cleanup`). (2) A cancel or cleanup that publishes a prepared step
  returns the worker's clean cleanup facts whatever the kill found, and the cancel answers `done` where `closed_loop.py`'s `cmd_cancel` requires `cancelled`
  (R9 decision 12 broke the consumer's contract). (3) A write failure after the tip ref moved records the step `failed`. (4) The facade's re-stated epoch rule
  omits the harness's `sealed_run` check and reads a torn event line as "nothing expected". (5) `stop_group` escalates to SIGKILL without re-checking that the
  group is still the worker's. (6) The calibration probe does not bind the report's case set to its scoring cases. Test gaps: the mutation driver exits 0 when
  mutants survive and counts any non-zero exit as caught; the simultaneous-start barrier precedes the shared read; an older cleanup test never calls
  `cmd_cleanup`; the parity assertion has no corrupted control. Its other answers: no duplicate engine run or publication on any `advance` path.
- **What rounds 3 to 5 show together.** 11, 7 and 6 verified defects. They come from four kinds of code: (a) re-statements of a harness rule (epoch reviews:
  rounds 4 and 5); (b) more than one actor that may rewrite or publish a step (poll, cancel, cleanup: rounds 3 to 5); (c) receipts computed from one call's
  view instead of the stored evidence (R9's fix made round 5's regression); (d) signals to process groups whose ownership is inferred (rounds 3 to 5).
  Patching each finding where it is reported adds a path, and the next round finds its sibling. **Interim.**

### Replan after round 5 (proposed 2026-11-15; waits on the owner)

Recommended (B): remove the four kinds of code, then verify once.

1. **The host (the owner's).** Configure a git identity on this machine (`git config --global user.email` and `user.name`, the identity every earlier
   commit carries), or give it a fixed hostname (`sudo scutil --set HostName`). Every real loop, and every commit on this machine that names no email,
   fails until then.
2. **Main's CI (urgent: every full run, so every release, fails on this suite).** Recommended: the harness hands each host its prompt on stdin (`codex
   exec` reads it there when no prompt argument is given; the Codex host already writes the prompt file), a generic E2E apparatus fix with no change to
   what any model reads. Interim alternative: the engine suite skips its three reviewer-reaching tests off macOS, naming the measured limit. Either way it
   is coordinated with the session repairing CI fixtures, which attributed the GitHub failure to the identity.
3. **Facade, routine.**
   1. An identity precondition: `step start` and the readiness answer refuse, naming the fix, when the engine's environment has no configured identity
      (`git -c user.useConfigOnly=true var GIT_COMMITTER_IDENT` and `GIT_AUTHOR_IDENT` in X with the engine's environment, and again with the improver's
      `GIT_CONFIG_GLOBAL`). Configured, not guessed: a campaign runs for hours and the guess changed with the network tonight. The negative test is
      deterministic on any host through `user.useConfigOnly`.
   2. One publisher: only `poll` publishes a prepared step; `cancel` and `cleanup` settle it cancelled and answer `cancelled`, as `cmd_cancel` requires.
      This reverses R9 decision 12 (publish on cancel) for the consumer's contract and removes finding 2.
   3. Receipts from stored evidence: a step's kill problems stay in its record until a later check shows them resolved; a cleanup of a terminal step with
      open problems checks the group again on a fresh process table and answers from that. Finding 1.
   4. Ownership re-checked before every escalation: `stop_group` runs `group_verdict` again after each wait and before SIGKILL, and stops when it is not
      `ok`. Finding 5.
   5. The harness owns its epoch rule: the facade asks `epoch.state` through the bridge instead of re-stating it, the stand-in engine writes its epochs with
      the harness's own epoch functions, and an unreadable ledger is invalid, not empty. Finding 4 and the parity assertion's blind spot.
   6. Publication reconciled with the ref: a worker that fails after the ref moved records `published` when the ref holds the prepared result. Finding 3.
   7. Calibration stays unmeasured for the smoke; the coverage binding (finding 6) comes before any calibrated claim.
   8. Tests: the mutation driver fails when a mutant survives and counts only a failing assertion of the named test; the barrier sits after both
      snapshots; the cleanup tests call `cmd_cleanup`.
4. **One verification** of that diff only (Sol at max), asking whether the four kinds are gone. The owner sets the bar: "ready with documented limits"
   when only judgements on rare paths remain, or "ready".
5. **The owner's decisions, then compute.** The records, the boundary hash, the budget, D1 and D3; then readiness and the one-iteration smoke on `hello`.

Alternatives. (A) Fix the six where they were reported and review again: the trend says a sixth round finds their siblings. (C) After steps 1 and 2 and items
3.1, 3.2 and 3.4 only, an attended smoke with the rest as documented limits: the reviewer would not start without truthful repeated cleanup, coherent
publication recovery, authoritative epoch validation and safe escalation, and C leaves two of the four open.

Outside the adapter (for the owner, or the session that owns the harness): `iterate.py` could refuse to start without a configured identity, and its git
helper could keep git's stderr in the error. Both would have turned tonight's diagnosis into one line.

### R11. Plan B, step 2: the prompt on stdin, landed by another session (2026-11-16)

- **Decision.** The owner chose replan B ("Yes, plan B", 2026-11-16). Step 1 (this machine's git identity) stays the owner's: nothing in it was changed.
- **What happened.** I built and verified a fix (Codex's command opens its prompt file as its own stdin and then becomes Codex, so no launcher
  changes) and committed it locally. Before pushing I found that another session had pushed its own fix for the same failure to main an hour
  earlier: ec2eae6978419034454580b7b96fe20e47a3d5d9, "send complete Codex helper prompts through buffered stdin" (`Host.prepare` returns the prompt
  bytes, `run_agent` feeds them through a scoped temporary file; the reviewer, judge and improver opt in; subject and resume launches, the purpose
  check, the fan-out study and the other hosts keep their argument). It touched the same five files. I dropped my unpushed commit
  (29d47f09ec0bf3c6b744be52709891c587440653, never on main) rather than push an alternative over another session's validated work; its patch is kept
  outside the repository only as a reference.
- **Checks of main's fix, made independently here.** The real-engine adapter suite on ec2eae69 in the offline Linux container: 5 of 5 OK in 56.9 s
  (3 of 5 failed before it). The real Codex CLI reads a `-` prompt from stdin: one session (codex-cli 0.169.0, `gpt-6.1-sol` at low) exited 0 in
  4.8 s and replied `STDIN-OK`, the prompt in no argument. **Firm.**
- **What stays open.** The paths main's fix leaves on the command line carry short prompts today; a large purpose-check prompt (it includes a diff)
  could still meet the Linux limit. Nothing runs them on Linux now. Recorded, not changed.

### R12. Plan B, step 3: the facade removes the four kinds of code (2026-11-16)

- **Question.** Can the defects of rounds 3 to 5 be ended by removing the kinds of code they came from, rather than patching each?
- **Changes, by kind** (`test/shiploop_e2e/adapter/facade.py` unless named).
  - *Re-stated harness rules.* `epoch_evidence` asks the harness: a new bridge operation, `epoch_facts`, runs `epoch.state` and `epoch.events` in X's
    harness and returns the last decision, each attempt's status, and the receipt of each attempt `epoch.state` calls reviewed. `epoch_reviewed`, the
    re-statement, is deleted. An epoch folder that exists but cannot be read (a torn row, a changed registration) is reported invalid; an attempt the
    harness calls `invalid_evidence` is reported invalid; a cycle that made no epoch has none. The stand-in engine now writes its epochs with the harness's
    own `epoch.initialise`, `launch_intent`, `record_run`, `append` and `digest`, so the facade reads them exactly as it reads a real one.
  - *Several publishers.* Only the step's worker, or a poll finishing what a dead worker prepared, publishes. `cancel` and `cleanup` settle a finished
    but unpublished step `cancelled` (reversing R9 decision 12), so a cancel answers `cancelled`, as `closed_loop.py`'s `cmd_cancel` requires, and no
    published fact can contradict what a kill found.
  - *Receipts from one call's view.* `cleanup` answers from the stored kill evidence; an open problem in it is checked again on a fresh process table,
    and resolved only by a check that finds the group gone or stopped.
  - *Signals on inferred ownership.* `stop_group` decides ownership again before SIGKILL; a group that emptied during the grace counts as stopped, and a
    group number now leading another session's group is not signalled.
  - Beyond the four: `identity_problem` refuses `step start`, and answers the `cases.runs` probe `declared` before its model session, when the engine's
    environment has no configured git identity (`git -c user.useConfigOnly=true var`), for the loop's commits and for the improver's view (only
    `$HOME/.gitconfig`); a worker never settles a step `failed` once its publication is prepared, so a write that fails after the ref moved is reconciled
    by the next poll; the calibration probe requires the cases it measured to be the cases its scoring digest covers.
- **Tests** (`test/shiploop-e2e-adapter-steps.test.py` unless named). ReplanTests (identity refusal for a step, for the improver's view, and for the
  probe before its run; a repeated cleanup that keeps an unresolved problem until a fresh check resolves it; no SIGKILL to a group recycled during the
  grace; a write failing after the ref moved, finished by a poll). The cancel and cleanup of a finished step now answer `cancelled` and publish nothing;
  the last-decision, torn-ledger and changed-sealed-evidence tests run through the stand-in's real epochs; a misbound calibration report is refused; the
  simultaneous-start test reads before its barrier (so it fails without the admission lock in every schedule); the older kill-blocker test also calls
  `cmd_cleanup`. The suite's home now carries a git identity, and the bare homes of the identity tests set `EMAIL`, so git could guess an identity on
  any host and only `user.useConfigOnly` refuses it. The engine suite's parity assertion compares the facade's facts with `epoch.state` on the real
  epoch and adds a changed-sealed-run control.
- **Results.** Queries suite 29 OK (23.7 s); steps suite 78 OK (427.9 s; nine new tests); real-engine suite 5 OK (104.3 s), with the facade's
  facts compared with `epoch.state` on the real epoch and a changed-sealed-run control. Mutation check (`g1d-mutations.py` in a throwaway clone):
  15 of 15 caught, each by a failing assertion of its named test (78.8 s), removing `user.useConfigOnly` included (caught because the bare homes set
  `EMAIL`). The real-engine suite on this tree in the offline Linux container: 5 of 5 (52.7 s). Boundary hash
  1c1eb78b7fe966841b006af44017a173280813a19b62951f608329c3b59fb270 (its ratification is the owner's). **Firm** for what the tests cover.
- **Open (unknown).** Whether removing the kinds ends the sibling pattern is what the verification of this diff measures. *Answered in R13: partly.*

### R13. Plan B, step 4: the one verification (2026-11-16)

- **Review.** Codex `gpt-6.1-sol` at max on c154c44fee46a6c5c852ce158e818d3237d3f121 (the diff from 4e36b3ad), one attempt, no fallback, a neutral clone;
  704 s; verdict **not ready** (`docs/experiments/closed-loop-phase2-review-20261115/g1e-sol-*`). Of round 5's six: FIXED, the SIGKILL re-check and the
  calibration binding; PARTLY, the other four. It found no competing publication or duplicate engine run on any path, and no wrong dependency on the
  stdin commit. I checked each claim against the code and the witnesses; all held.
- **Blocking, in the reviewer's words "would require before starting".**
  1. *Detached survivors forgotten.* A repeated cleanup re-checks a stored kill with `kill_step`, which answers `gone` with no survivors once the worker's
     group has emptied, so survivors recorded below it (processes in sessions of their own) are dropped, and only their PIDs were stored, not their
     start times.
  2. *Terminal transitions against a moved ref.* A prepared record whose ref already moved (a write failed after `update-ref`) is settled `cancelled`,
     "not published", by `cancel` and `cleanup`, while the tip holds its result; and a cancel that finds a step already published answers `done`,
     which `cmd_cancel` refuses (the campaign's step stays running until its next poll).
  3. *Unfinished epoch evidence accepted.* An absent epoch with a cycle result that needs one (DROP), or an accepted epoch with no decision yet, counts as
     zero expected assessments, so review and judge can read complete.
  4. *Identity checked in the wrong context.* The check runs in X, but the loop commits in a linked worktree (an `includeIf gitdir:<X>/.git` identity
     passed and failed there), and the improver's view kept the real HOME (a `~/` include passed and vanished in the isolated home); it also refuses a
     Claude improver whose identity is in XDG, although that host keeps the caller's environment.
- **Not blocking the attended smoke, by its account.** No judge placeholder for an incomplete epoch assessment (older than this diff); the Claude refusal.
  Test limits: the simultaneous-start barrier's 2-second wait can still let a delayed second thread pass without the lock; the engine parity compares
  counts, not receipt identities; the mutation driver would count an unrelated setUp assertion as caught. Judgements: a recent leaderless group's
  ownership is still inferred; unrecorded sessions of a worker that died unobserved are still not found.
- **What it shows.** The four kinds were reduced, not removed: the publisher kind kept terminal transitions that ignore the ref, the receipt kind kept
  a re-check that answers from one view, and the identity check is itself a re-statement (of where and how the engine commits). The defects are now in
  rarer paths (a process that survives SIGKILL, a disk that fills between two writes, an identity configured by path, an epoch stopped before its
  decision) than round 3's. **Interim.** Rounds 3 to 6: 11, 7, 6, then 4 blocking.
- **Next.** The owner's decision (plan B step 5): fix the four and then run the attended smoke without another round; fix them and verify once more; or
  run the attended smoke now with all of them as documented limits.

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
| F15 | A plan that names a skill's claims must use the skill's own vocabulary and ladders: three of the first draft's six claims did not exist (`improvement.callable`, `calibration`, `baseline`); check names against `CLAIM_LADDERS` | firm | `docs/closed-loop-phase2-plan-2026-11-15.md` appendix B; `references/readiness.md` |
| F16 | Walk the planned scenario through the certificate's checks and the navigation before promising its outcome: draft 1's smoke could never converge (records that name no case block every scope) and version 2's two-iteration smoke could never run (the orchestrator stops `blocked` after one) | firm | `check_c1`, `analyze`, `plan_next`; the Phase 2 review folder |
| F17 | A facade that kills a step's process group does not reach the model: the harness starts host processes in their own sessions. Use the engine's own cleanup per run folder, and reject `unverified` and `protected` results that its CLI reports with exit 0 | firm | `hosts.run_agent`, `lifecycle.cleanup`; the Phase 2 plan row 15 |
| F18 | Archive everything a step produced before any cleanup: a killed step's ledger rows can be staged, so copy the whole worktree and bundle its branch, not a diff | firm that the window exists, not shown for real kills | `round1-sol-kill-witness.json`; the Phase 2 plan row 13 |
| F19 | A derivation tested only against the facade's own idea of the harness's files can pass while the real loop differs: run the real `iterate.py --qualify` with one fake host program for every role (14 to 64 seconds) and read the real artifacts, the real strict-outcome function and the real baseline predicate | firm | `test/shiploop-e2e-adapter-engine.test.py` (2 tests); the facts it printed |
| F20 | A wait on a kill window must wait for content, not for a file name: while `git worktree add` fills a worktree its index is empty and every file looks staged; and the last side effect a fake produces must be the one the test waits for | firm (one instance) | `ProcessTests.hung` in `test/shiploop-e2e-adapter-steps.test.py` |
| F21 | A step's liveness is a file lock its worker holds: the OS frees it however the worker ends, so no pid reuse or stale file can fake a live worker, and a worker killed alone is found dead by the next poll | firm | `ProcessTests.test_a_worker_killed_alone_...` |
| F22 | Timing-invalid evidence still serves a token claim: only an attribution that is false makes a run's evidence invalid for it | firm (code and one calibration) | commit 3423e21801165d86c21e1d9e59d5c55d130bff66; `promotion._strict_comparable` |
| F23 | A cancel must snapshot what runs below the worker before it signals anything: the harness starts model sessions in sessions of their own, found through parent links only while their parents live; a group kill and the lifecycle ledger together still miss a reviewer, judge or improver session | firm for the cancel path, a stated gap after an unobserved death | `ProcessTests.test_cancel_also_ends_the_sessions_below_the_worker_...` |
| F24 | A probe's positive control can be wrong in the reader and right in the check: `grading.scores` parsed `scorecard.py --json` as a list when it prints `{"scorecard", "cards": [...]}`, which only a real run folder through the real scorecard showed; and a negative control must make the CHECK fail, not feed it bad input: a harness copy whose boundary rule accepts every path leaves `improver.bounded` declared while its build and tier parts pass | firm | `RealEngineTests.test_the_runs_and_scores_probes_...`; `RiggedBoundaryTests` |
| F25 | Whoever is not the worker rewrites a step's record only while holding the step's lock: the worker's saves overwrite the whole file, so a canceller or cleanup that kills the worker the record names and then saves a stale copy loses a worker that was still booting (no identity yet) and can overwrite a publication that finished meanwhile | firm | Sol's witness `g1-sol-witness-parent-races.json`; `BootWindowTests`, `ReviewFindingsTests` |
| F26 | A per-step lock cannot make two steps with different keys exclusive, and a step whose worker died is still the evaluator clone's owner: admission and every hand move of the tip (`decide`) take one workspace lock and refuse while any step is unsettled | firm | `ReviewFindingsTests.test_two_steps_started_at_the_same_moment_...`, `..._a_decision_is_refused_...` |
| F27 | A cleanup receipt is a claim about what is left running, so a kill's outcome (survived, protected, unverified, surviving sessions) is part of it; the lifecycle ledger alone sees only recorded run resources and said verified over zero folders | firm | `kill_problems`; `ReviewFindingsTests.test_a_kill_that_left_something_running_...` |
| F28 | "The first file found" is not the final assessment: a judge that is invalid is judged again in a folder of its own (`review-judge-retry-N`), and an epoch review that ended incomplete may be redone: read the last one per attempt | firm | `final_verdict`, `epoch_evidence`; `ReviewFindingsTests` |
| F29 | Authority travels with the catalog: the facade dropped a case's `needs`, so the orchestrator's owner-only rule never fired for the browser case, and the test that pinned the empty list protected the defect; assert the refusal from the real orchestrator | firm | `CasesTests.test_the_orchestrator_gates_the_browser_case_...` |
| F30 | A calibration document with no observations passes the harness's loader (it checks the digest and the recommendation): a probe must ask for sealed attempts and compared splits | firm | `ProbeTests.test_the_calibrated_claim_...` (three new negatives) |
| F31 | A reply's vocabulary belongs to its consumer: `step start` accepts `running` or `done`, so an idempotent replay of a finished step must not answer `failed` (the orchestrator counts it as a start failure, and three stop the campaign) | firm | `ReviewFindingsTests.test_the_replay_of_a_start_...` |
| F32 | A failure before the exception handler is a step that stays `starting`: a poll then begins a new worker each time (389 identical failures in the reviewer's logs); make start-up failures durable, bound respawns, and turn an unavailable `ps` into an error | firm | `ReviewFindingsTests.test_a_worker_that_cannot_read_the_process_table_...` |
| F33 | A lock obtained at once proves nothing about the worker's group: a worker killed alone frees its lock while its engine still runs there, so every path that settles a dead step stops the group first | firm | `SecondReviewTests.test_cleanup_stops_what_a_worker_that_died_alone_...`, `..._a_cancel_stops_...`; reviewer witness `g1b-sol-witness-results.json` |
| F34 | An ownership rule fixed for the writers a review named still fails for the ones it did not: list every writer and every publisher of the state and apply the rule to each (the poll's publication, the respawn's grace check and the start's tip read were the siblings) | firm | `SecondReviewTests`; journal R8 against R9 |
| F35 | Decide ownership before collecting anything below a process group, and take a record's age from an epoch time stored with it, not from `ps`'s local-time text (a time-zone change turned 16 hours into 8) | firm | `group_verdict`; `PureTests.test_a_group_whose_leader_is_gone_...` |
| F36 | Where the facade re-states a harness rule, mirror it exactly and keep a parity test against the harness's own function on real data: the facade took the first epoch decision and ignored receipt seals, while `epoch.state` takes the last and demotes a broken seal | firm | `epoch_reviewed`; the real-engine parity assertion |
| F37 | A recommendation must follow from the report's own measurements: recompute it with the harness's function (`spread.recommend`); a zero attempt count had turned the sample check into 0 >= 0 | firm | `ProbeTests` (two new negatives) |
| F38 | A test named for a guarantee must fail when the guarantee is removed: break each fix on purpose and run its test (9 of 9 caught here; in R8 the simultaneous-start and the kill tests could not have failed for some mutants) | firm as a method; the 9 of 9 is qualified by F45 (2026-11-15: the driver counted any non-zero exit) | `docs/experiments/closed-loop-phase2-review-20261115/g1b-mutations.py` and `g1b-mutations.txt` |
| F39 | A throwaway home must carry every piece of global configuration the code under test relies on: git's fallback identity depends on the hostname, so a suite that passed earlier in the day failed once the hostname lost its dot | firm | `setUpModule` in `test/shiploop-e2e-adapter-engine.test.py`; R9 |
| F40 | On a Mac with no fixed hostname, git's guessed identity follows the network: the hostname came from the router's reverse-DNS answer and lost its dot mid-session, and every commit that relied on the guess failed. Configure an identity; never depend on the guess | firm | `identity-failure-evidence.txt` (timeline, mechanism, controlled experiment, exact replays) |
| F41 | Readiness must exercise every environment dependency of the loop's own steps, not only the subject's: the probes ran a case (whose sessions use a throwaway identity) but never the learnings or improver commits, so readiness would pass and the first step fail after its subject run | firm | `identity-failure-evidence.txt` section 4; the probe test passed with no identity |
| F42 | An error that names the command but not the reason costs a replay: the harness's git helper drops git's stderr, so the engine log showed `git commit` failing, not why | firm | `identity-failure-evidence.txt` section 3 |
| F43 | Fixes made where a review points add paths, and the next round finds their siblings (11, 7, 6 verified defects in rounds 3 to 5). The defects come from four kinds of code: re-stated harness rules, several writers or publishers of one step, receipts from one call's view, signals to groups whose ownership is inferred. Remove the kind, not the instance | interim | R8 to R10; `g1c-sol-answer.txt` |
| F44 | A decision that changes what a reply means must be checked against the consumer's code: publishing on cancel answered `done`, which `closed_loop.py`'s `cmd_cancel` refuses | firm | `g1c-sol-answer.txt` change 2; `cmd_cancel` |
| F45 | A mutation check is evidence only if its driver fails when a mutant survives and counts only the named test's failing assertion; R9's driver did neither, so its 9 of 9 is weaker than it read | firm | `g1b-mutations.py`; `g1c-sol-answer.txt` |
| F46 | The same symptom on two machines can have two causes: compare the failure's details (CI's messages listed no staged path, the Mac's always one) and reproduce on the CI's operating system before attributing | firm | `linux-ci-failure-evidence.txt`; R10 |
| F47 | A prompt passed as one command-line argument fails on Linux above 128 KiB; the harness's reviewer prompt is 175 KB because it carries the whole E2E spec, so its reviewer cannot launch on Linux, and macOS's 1 MiB limit is about six times away and shrinks as the spec grows. Hand prompts over on stdin | firm | `linux-ci-failure-evidence.txt` sections 2 and 3 |
| F48 | Read CI's result after every push, not only its start: the engine suite failed CI from its first push (a9d40c30) and was noticed two pushes later | firm | CI runs 43801628143 and 43811121318 |
