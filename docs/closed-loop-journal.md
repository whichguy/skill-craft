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
- **Open (unknown).** A second Astra max review of the hardened code, the quick tier, and CI on main come next and are recorded below
  when they exist. Nothing has driven the card with a model operator on a real subject; the ShipLoop adapter (Phase 2) is the first
  real subject and waits on owner decisions (the harness's continuation seam is a new scoring identity, which AGENTS.md reserves
  for the owner).

## Findings

| # | Finding | Status | Evidence |
| --- | --- | --- | --- |
| F1 | A script-owned quiet window needs `required_trivial_reviews: 0`: a failed frozen check sets the native streak to zero, so two counters make convergence take three passes instead of two | firm | `test/closed-loop.test.py` `UntilLoopTests`; `until-loop-exit-checks-0-8-0` memory; runtime `until_loop_ephemeral.py` |
| F2 | The Until Loop's freshness check binds to a workspace's Git tree: bind it to the folder that holds every fact the checks read, not to the subject | firm | `probe-runtime-stale-satisfaction.json`; `UntilLoopTests.test_a_state_change_made_through_the_sanctioned_verbs_...` |
| F3 | A certificate is only as strong as the validation of what it reads: types, exact case set, identities and finite amounts are checked before evidence counts | firm | `EvidenceTests`; mutation run 1 |
| F4 | Marginal coverage misses interactions: a catalog of AX, BY, AY leaves AY unselected unless the pair is a declared combination | firm | `EvidenceTests.test_declared_combinations_...`, `..._without_declared_combinations_...` |
| F5 | The script cannot prove an adapter reported truthfully; the ratified boundary, the pinned files and the readiness probes are the trust | firm (a limit, stated in the card) | `references/convergence.md`, `references/adapter-schema.md` |
| F6 | The budget is checked between steps, so one step can overshoot it; hung and failed calls are charged | firm | `QuotaTests` |
