# release-check: re-cut draft (worker D)

## 1. Goal (R1)

Confirm the release candidate is ready without releasing it: run the planned deploy's dry run and each post-release
confirm command once, and record every readiness check with its output in this result's `summary` and
`evidence_refs`.

## 2. Duty

1. Name the release plan you check: the latest done release-plan and system-test-author records after the last
   accepted replan. Put their action, result and plan locators in `evidence_refs`. A missing plan is not guessed:
   recover it, or report `repeat` (or `replan` for missing product work).
2. Check, against the current target, and record each in `summary` with its evidence in `evidence_refs`: the
   candidate identity, that its evidence is current, the target and its prerequisites, the required approvals,
   rollback readiness, the execution owner's readiness, and any concurrency condition the target enforces.
3. Run the dry-run form of the planned deploy (for example `sf project deploy validate`) once. Save its output in
   RUN/notes/<action>-release-check.md and put that path in `evidence_refs`.
4. Run each post-release confirm command from FEATURE/release-plan.md once against the current target. Save its
   "not there yet" output in the same file. A confirm command whose output cannot tell the result present from absent is
   fixed now in FEATURE/release-plan.md and run again.
5. Isolated run only: run the packet's plan-return command, then decide every undecided path with its review-return
   command. This is a dry run of the return; the decisions are kept for the return at release. Compare the expected
   return that review-return prints with the rollback in FEATURE/release-plan.md. When they differ, correct the
   rollback there and run plan-return again.
6. Keep stale or failed evidence in `evidence_refs` as it is. Do not replay or promote anything to get a fresh
   observation. A material change to code, tests, fixtures, configuration or target invalidates the observations it
   affects: rerun those through the planned route, and reuse the rest only with their identity and relevance stated.
7. External release N/A does not waive the local candidate checks in items 2 to 4. Record a justified N/A in
   `summary` with what you assessed.

## 3. Checked by

Nothing beyond the exit conditions and the shared mechanical checks.

## 4. Guides to keep

- Release operation guidance (environment-lifecycle.md#release-operation-ownership): items 2 and 6.
- Delivery completion guidance (consumer-delivery.md#where-completion-is-enforced): item 7.
- OUTER test-planning handshake (repeatable-test-suites.md#outer-test-planning-handshake): item 1.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| Verify final release-candidate readiness without performing the release. | Goal |
| Check candidate identity, current evidence, target/prerequisite status, approvals, rollback readiness, pre-release validation. | Item 2 (pre-release validation is items 3 and 4) |
| Preserve stale or failed evidence; do not replay or promote to get a new observation. | Item 6 |
| Check execution-owner readiness and target-enforced concurrency conditions. | Item 2 |
| External release N/A does not waive current local candidate checks. | Item 7 |
| Run the dry-run deploy and each post-release confirm command once, against current target state; record both outputs. | Items 3 and 4 |
| A confirm command that cannot tell present from absent is fixed here, before the real deploy. | Item 4 |
| Isolated run: run plan-return and review-return now as a dry run of the return. | Item 5 |
| plan-return may commit leftover product files to the run branch. | CUT: workspace-lifecycle.md#inner-assembly-and-final-return step 1 states it, and plan-return prints what it committed |
| The decisions you record are kept for the plan made at release. | Item 5 |
| Compare the expected return review-return reports with the rollback in release-plan.md; correct it when they differ; then run plan-return again. | Item 5 |
| Consideration "Deploy: Dry-run the deploy; do not release." | Goal and item 3 |
| OUTER handshake: current plans are the latest done system-test-author and release-plan records after the last accepted replan. | Item 1 |
| OUTER handshake: earlier records are history; pending, repeat and blocked results are not plan authority. | Item 1 ("latest done ... after the last accepted replan") |
| OUTER handshake: retain action, result and plan locators in this result. | Item 1 |
| OUTER handshake: the owning stage creates the plan; a later stage names and revalidates it. | Items 1 and 2 |
| OUTER handshake: recover a missing plan or report incomplete/corrective; never guess commands, drop coverage, or deploy to make a check available. | Item 1 (guessing); dropping coverage and deploying: CUT for this stage, since it deploys nothing and drops no case; repeatable-test-suites.md#outer-test-planning-handshake keeps both |
| OUTER handshake: a plan is not execution evidence. | Items 3 and 4 (the runs are the evidence) |
| OUTER handshake: a material change invalidates affected observations; rerun; reuse others with identity and relevance shown. | Item 6 |
| STAGE_RULES | Shared section (worker B) |

## 6. Size

- Today: duty 1,211 + considerations 35 + OUTER handshake 916 = 2,162 characters.
- Draft: goal, duty and Checked by 2,338 characters with headings.
