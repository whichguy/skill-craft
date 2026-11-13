# Astra brief: a learning checkpoint after each inner-loop step? (2026-11-12)

You are reviewing a design question for ShipLoop (skill source `skills/shiploop/`, this checkout = origin/main
16563a016f74bd51644c36c123afc7a3c76e2411). Read-only. Use max effort. Verify every claim you make against the code.

## The owner's question (verbatim)

"After each task for inner loop, should we have a step to determine if there are any key learnings that would update
the overall pending step plan? The idea would be to elicit out any knowledge leaned and determine if there is a plan
that would be better to execute upon."

## What exists today (read these, do not trust this summary)

- `skills/shiploop/references/inner-loop.md`: per item, `step-plan`, `test-spec`, `validate-existing`, then
  `implement`, `test`, `document` once per step, then `carry-forward`. Send-back from test-spec through document
  returns the item to step-plan.
- `skills/shiploop/references/navigator.md` section "Each step's reflection": the `document` stage is each step's one
  place to reflect (records the knowledge home; routes new work: defect fixed now, work the plan lacks = send-back,
  work a later step holds = left to it, work outside the item = open item due at carry-forward).
- `skills/shiploop/references/carry-forward.md`: after each item, map observations to the future queue; may replace
  the whole future queue.
- Prior decision: commit 7bba525ed74ad436ddbbe526db029714fdec47cb (owner, 2026-10-28, "Go with C"): no separate
  knowledge stage after each step; reflection folded into document. Astra's review then:
  `docs/experiments/knowledge-stage-review-20261028/astra-review.md`.
- Send-back after a committed step: `docs/shiploop-review-after-tests-design-2026-10-27.md` around "A send-back after
  S1 is committed" and "After a send-back the redone plan counts steps afresh".

## Measured facts (this folder; scripts and outputs beside this brief)

300 distinct E2E runs (state.md newer than 2026-10-29, deduplicated by run_id; list in `runs.txt`; scripts
`agg.py`, `late.py`, `redo.py`; outputs `*.out`). E2E cases are small apps, so multi-step items are a minority.

- 283 work items; 90 had more than one step; 430 steps in final plans; 147 step boundaries (a later step remains).
- Step-plan versions per item: 1 for 214, 2 for 57, 3 for 12. 82 send-backs: implement 50, test-spec 17, test 10,
  validate-existing 3, system-test 2, document 2.
- 74 send-backs came before any step of the current plan was committed; 8 came after at least one step was committed
  ("late"; listed with their summaries in `late.out`).
- My reading of the 8 late ones (check it): about 6 are a later step's Proof that a planner could have caught without
  doing the earlier step (Proof not safe to repeat: a permission-set assignment reassigned on every run, 3 runs;
  shell quoting; a tool the run's guard denies, osascript, which the guard allowlist states from the start; a deploy
  wrapper with no test-run summary). One is a runtime defect needing diagnosis (gym S2). One unread (p0-terra rg).
  The repeat-safety wording A2a (211fe61b, 2026-11-01 14:28) landed after 4 of these runs.
- A late send-back re-runs implement, test and document for every carried-over step under the redone plan. Minutes
  from the send-back to the redo catching up with the done steps (`redo.out`): 2.9, 1.6, 3.4, 3.7, 14.6, 6.3, 9.8
  (one unmeasured); about 42 minutes over 7, items of 11 to 49 minutes.
- Item boundary: 10 carry-forwards had a later item; 4 of them replaced the queue.

## What I want from you

Part 1 (before reading Part 2): answer the owner's question independently. Should ShipLoop add a step (a model
action) after each inner-loop step, or each item, to elicit learnings and re-plan the pending steps? If not a step,
what should change, if anything? Weigh quality first, then tokens, then time (owner's priority). Name what evidence
would change your answer, and the cheapest experiment that would produce it.

Part 2: critique these candidates (mine), each for value, risk, and what it breaks:

- A. No new stage. `document`'s existing Reflect duty gains one question, asked only when a later step remains: do
  the later steps' Proofs, commands and paths still hold given what this step showed (and the run's environment and
  guard)? It records a one-line answer; "no" is a send-back that amends only later steps.
- B. Make a mid-item re-plan cheap: when a send-back's amended plan carries the committed steps over unchanged, the
  script keeps them done (their commits and receipts stand) and resumes at the first new or changed step, instead of
  re-running implement/test/document for each. The item's full regression still runs at its last step.
- C. Catch the dominant late class at plan time: step-plan checks for Proofs a later run cannot repeat or cannot run
  in this environment (generic, not stack-specific).

For B in particular: what does re-running carried-over steps currently protect (stale receipts, base commits, RED
checks, the per-step Improve review, the ledger), and is any of it lost if they are kept? Cite symbols.

Return: a verdict per part, the top risks with file/symbol citations, and anything in my measured facts you find
wrong (recount if you can).
