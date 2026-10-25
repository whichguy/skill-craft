**I would adopt P1 and P2 with corrections, retain P6, replace P3 with conditional reuse, and reject P4 as the default schedule. P5 is worth piloting, with survivor triage at the test stage and a final audit at end of work.**

I inspected the current working tree at `9bcc95d9`, including its uncommitted changes, and the cited run artifacts. The audit confirmed 56 reviews and 118 passes. No files were changed.

The main evidential problem is equating “made no edit” with “could not find anything.” These records establish intervention frequency and historical review cost. They do not establish the quality outcome if those reviews disappear. There are also several concrete corrections below.

**P1 — Change: keep the measurement fix, but measure the actual reviewed and accepted results.**

The underlying problem is real. Run 5b’s test-spec review added assertions while its pass record reported `changed: false`. However, the reviewer edited the **original inbox file**, then intended to supply `--final-result` at parent return. Hashing only `<action>-final-result.md` could miss the editing pass and attribute the change to a later pass. [Run 5b test-spec review:8–15](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/worktree/.shiploop-improve/test-spec-4fb41465/reviews/review-1.md:8)

There is another correction: current `metrics.improve_reviews` does **not** inherit edit counts from `passes.md`. It reads review files, reports no edit count, and calculates elapsed time as last-note minus first-note time. Consequently, a one-pass review reports zero seconds there. P1 needs an explicit metrics implementation, including correct first-pass timing. [metrics.py — improve_reviews](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/test/shiploop_e2e/metrics.py:955)

My replacement rule:

> At bind and after each pass, record the content identity of the candidate result being reviewed, including edits to the original inbox result or its replacement. Record `tree_changed`, `result_changed`, and `edited` separately. Compare against the preceding pass, using the frozen producer result as the initial baseline. At import, separately record whether the accepted result differs from that producer result. Missing evidence is “unknown,” not “unchanged.”

Compare parsed result content so copying an unchanged result to a new filename does not manufacture an edit. Keep pass activity distinct from the net accepted change: an edit later reverted is activity, but not a delivered improvement.

This can remain telemetry-only. Do not change stopping behavior merely because `edited` becomes true. The current contract stops after one **trivial** pass, which may include polish; “one unedited pass” is an approximation. [navigator — Improve exit contract](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:8135)

Expected benefit is highly believable. Cost remains small, though it is more than one hash when multiple result paths are supported.

**P2 — Change: require valid transitions, not merely a computed final state. This answers advisor question 1.**

This is the strongest proposed direction, but its causal explanation needs correction.

Run 5b **already executed and recorded a replay of the illegal promotion sequence**. Its check explicitly says it used `apply_simple`, with “no legality generator.” That function’s docstring says “No legality”; it removes the source piece and overwrites the destination. I reproduced its acceptance of `b2b4 b7b5 b4b5` without writing anything. [Recorded replay](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/worktree/.shiploop-improve/test-strategy-edacefd5/reviews/checks.md:3), [replay helper — apply_simple](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/run/scratch/oracle_replay.py:50)

Moreover, the test-strategy review added TC_28 and endorsed that illegal sequence. This is evidence of a **review-introduced invalid oracle**, not simply an example nobody replayed. [Test-strategy review — added case and claimed check](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/worktree/.shiploop-improve/test-strategy-edacefd5/reviews/review-1.md:7)

I would use:

> For each new or changed expected result derived from a sequence, validate the stated start conditions and every transition under the relevant specification rules, then recompute the result. Include examples introduced by this review. Record the case ID, method or command, decisive intermediate states, computed result, and evidence location. A helper that merely applies requested state changes does not establish that the sequence is permitted. Reuse prior evidence only when its inputs, relevant rules, and method remain applicable; otherwise leave the claim unresolved.

This changes the task from making an example executable to establishing its validity. “Record the replay” alone does not accomplish that.

Additional safeguards:

- A small explicit derivation can suffice; do not require building a second product implementation for every example.
- An existing reference evaluator must implement the relevant rules. The product being tested must not be the sole authority for its expected result.
- Reuse unchanged evidence across spec, strategy, plan, step-plan, and test-spec. Otherwise “every expected value” creates repeated computation across five stages.
- Keep detail in evidence files and a compact obligation in the shared duty text. My stronger wording costs more than the proposal’s approximately 200 characters.

The potential saving is plausible, but **the specific avoided send-back is n=1**, and the proposed wording has not demonstrated that saving.

**P3 — Change: narrow repeated reviews rather than eliminate them. This answers advisor question 3.**

The four historical no-edit re-reviews check out: **344 seconds total**, or 1.91 minutes per run. But “five first-item reviews” is inaccurate. Two were run 3’s initial reviews of **W2 and W3**, under the older schedule. The comparison mixes scheduling versions. [Run 3 W2 packet](/Users/dadleet/e2e-runs/20261019/chess-sf-full-05fe25b/.shiploop-runs/work-20261019-190637-c96f77/run/packets/nav-32eb55651db34644a2321f25d6aa1445.md:73), [W3 packet](/Users/dadleet/e2e-runs/20261019/chess-sf-full-05fe25b/.shiploop-runs/work-20261019-190637-c96f77/run/packets/nav-0ecb93d748ba4622862dbab327232653.md:73)

Yes, a revised test-spec review can catch something its preceding step-plan review cannot: **the test-spec author introduces the oracle, RED/GREEN definitions, and procedure after the plan was reviewed**. A correct revised plan can therefore yield an incorrect new expected value or weakened failure condition. Script completion checks the loop receipt; it does not independently compute these proposed oracles. [stage_spec — test-spec contract](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_stage_spec.py:371)

My replacement rule:

> After a send-back, review the revised test specification’s changed cases, affected dependent cases, and preservation of previously accepted requirements. Omit this review only when the script establishes that a previously reviewed case contract and its relevant premises are unchanged. If no prior reviewed version exists, retain the review.

This will not recover all 5.7 minutes claimed; changed premises deliberately remain reviewable.

There is also an implementation ambiguity. Current selection means “first work item **or any item with a prior send-back**.” Removing the second clause still re-reviews W1 after every send-back. “Only W1’s initial test-spec” requires a different predicate. Scheduling and state validation must agree. [navigator — selection](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:488), [required review receipts](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:1615)

**P4 — Drop as the default rule; retain it only as a hypothesis to measure. This answers advisor question 2.**

The retrospective counts hold: 22 implementation reviews, five defect-bearing reviews, and 953 seconds of proposed skips. The evidence is substantially narrower than “three runs” suggests:

| Run | Implementation reviews | Defect-bearing reviews | Proposed skips | Logged time skipped |
|---|---:|---:|---:|---:|
| 3 | 4 | 1 | 2 | 149 s |
| 4 | 4 | 1 | 0 | 0 s |
| 5b | 14 | 3 | 10 | 804 s |

**Every observed later-step review comes from run 5b.** Runs 3 and 4 used S1-of-1 implementation packets. Thus the evidence for skipping later steps is **n=1 run**, with several observations further involving unchanged reissued steps. [Run 3 single-step packet](/Users/dadleet/e2e-runs/20261019/chess-sf-full-05fe25b/.shiploop-runs/work-20261019-190637-c96f77/run/packets/nav-aa400925f76140ab8bc2e12bb457512a.md:14), [run 5b S2-of-6 packet](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/run/packets/nav-341ebb441cbe4a1b8a7764e97247cada.md:14)

The rule also has concrete generic failure cases:

- S1 changes configuration; S2 implements the public interface. **Neither receives review.**
- A revised plan repeats unchanged S1 and repairs S2. The rule reviews the repeated work and skips the repair.
- A later step adds authorization, persistence behavior, asynchronous coordination, or an integration boundary. Ordinal position says little about its risk.
- Configuration and metadata can determine execution or access. The existing classifier includes `.github/**` as configuration and permission definitions as metadata; neither classification establishes low risk. [Path classification catalog](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/references/path-classes.json:12)

Two implementation details further weaken the proposed measurement:

1. **Lint scope is cumulative from the item base, not the step base.** It can include source changed by earlier steps. Use the existing step-entry snapshot for actual step changes. [navigator — step-entry snapshot](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:4081)
2. The ask-agent route builds all steps in one implementation action. It needs an explicit rule; the inline first-step predicate does not generalize automatically. [navigator — route distinction](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:3518)

My near-term replacement is conservative:

> Retain review for each changed implementation action. Reuse a completed review only when the actual candidate, applicable contract, and verification evidence are unchanged from that reviewed candidate. Missing snapshots or uncertain external-state changes require review. Step number and path class alone do not waive it.

For a better prospective trigger, measure **verification gaps**: criteria marked `confirm: inspected`, unverified layers, and source-search-only evidence. These directly identify missing executable checks and already have structured representations. They are useful reasons to retain or intensify review, although their absence does not prove a step safe to skip. [test_layers — confirmation modes](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_test_layers.py:144)

Ten further reviews should be a reassessment point, not a safety threshold. Record “would skip” while retaining reviews, including another domain and different step decomposition.

**P5 — Change: triage survivors during testing, then audit unresolved dispositions at end of work. This answers advisor question 4.**

The premise is sound: concrete survivors deserve attention. The current gate normally refuses only when mutants ran and **none** were killed; mixed remote/local execution has an additional exception. Partial survival therefore passes without individual explanations. [mutation — acceptance rule](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_mutation.py:397)

But “add the test that kills it, or record why it cannot be killed” is too permissive about explanations and too broad about what deserves a test.

For example, run 3’s cited record contains three survivors in tool-generated tracking configuration, alongside the engine survivor. A blanket instruction could waste effort testing non-product artifacts. [Run 3 mutation inventory](/Users/dadleet/e2e-runs/20261019/chess-sf-full-05fe25b/.shiploop-runs/work-20261019-190637-c96f77/run/tests/nav-da24c1ff79c24782961596998710a40a-mutation1.md:15)

Survival can also reflect equivalence under the contract rather than weak assertions. Mutation tooling explicitly documents this limitation. [Stryker — equivalent mutants](https://stryker-mutator.io/docs/mutation-testing-elements/equivalent-mutants/)

I would use:

> For each current in-scope surviving mutant, identify its candidate version, mutation, and affected requirement. Either add a behavioral test that passes on the unmutated candidate and fails on that mutant, or give specific evidence that the mutation is equivalent under the contract, outside product scope, or not exercised by this runner. Unavailable verification remains unresolved. Do not weaken the oracle or change required behavior to improve the mutation count.

And at end of work:

> Reconcile outstanding survivor dispositions against the final candidate. Recheck dispositions invalidated by later edits, and verify that claimed kills have execution evidence.

**The test stage should refuse an unexplained in-scope survivor**, through an explicit disposition requirement, rather than demand a 100% kill rate. Pilot this requirement because its net cost has not been measured. It can use the existing test-stage correction cycle instead of adding another unconditional Improve child.

End-of-work review is a backstop, not the sole owner: run 3 demonstrates that a run may never reach it. Its current import reruns recorded test commands after changes, but does not itself establish that a previously surviving mutant is now killed. Targeted mutant reruns remain necessary. [navigator — end-review verification](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:4479)

**Do not remove weak-assertion review from test-spec.** The mutation sample is at most eight mutations of selected changed lines. It cannot establish that an oracle is correct, cover unselected faults, or replace checks on remote-only behavior. Planning-oracle review and mutation analysis serve different purposes.

**P6 — Keep, but correct the count and stop treating 4.6 minutes as an established value estimate.**

There are **ten edited spec passes**, not the table’s nine:

- Run 3: five.
- Run 4: two.
- Run 5b: three.

The omitted run 3 pass says an ambiguous position reference would cause a correct engine to fail. Under the proposal’s definitions, that is a DEFECT correction. A defensible classification is **2 DEFECT / 7 STRENGTHEN / 1 POLISH**, while separately identifying that this extra defect repaired wording introduced earlier during Improve. [Run 3 spec pass log](/Users/dadleet/e2e-runs/20261019/chess-sf-full-05fe25b/.shiploop-runs/work-20261019-190637-c96f77/run/improve/nav-61033d5e23f146cd96aafecbc4d005dc/passes.md:7), [omitted correction](/Users/dadleet/e2e-runs/20261019/chess-sf-full-05fe25b/.shiploop-runs/work-20261019-190637-c96f77/worktree/.shiploop-improve/spec-c4d005dc/reviews/review-5.md:7)

The 36.8-minute total is correct. Dividing it by eight does not isolate the marginal cost or value of strengthening: it includes whole reviews, confirmation passes, and some self-created rework.

My wording:

> Retain spec review. Prioritize incorrect oracles, missing observable behavior, contradictions, and requirements that later stages could falsely satisfy. Report corrections to producer defects separately from repairs of review-introduced defects. Reuse valid evidence for unchanged requirements.

For quality-first delivery, strengthening an upstream oracle can readily justify several minutes. These runs support retaining that capability; they do not price each strengthening pass or prove all seven were equally valuable.

**For advisor question 5, the guarantees at risk are specific.**

P3 removes scrutiny of a newly generated test contract after its premises changed. P4 removes the current pre-test review of later implementation changes. Removing weak-assertion hunting under P5 removes an upstream check that sampled mutation testing cannot replace. An end review does not restore those earlier checkpoints, especially for runs that stop before reaching it.

There is also a small contradictory instruction worth correcting independently: the current planning handoff still mentions “two existing qualifying reviews,” despite the one-trivial-pass contract. That is a plausible source of extra work, though I have not established that it caused any measured delay. [navigator — planning handoff wording](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:7410)

**What I would add to the next experiment**

A focused review of **new, unevidenced planning premises on later items** is more promising than first-step-only implementation review. Run 5b’s W2 send-back concerned a runtime exception assumption that invalidated both the proof and test oracle; its initial plan had not received the first-item review. This is an **n=1 candidate**, not justification for reviewing every later plan indiscriminately. [W2 send-back evidence](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/run/results/nav-c7fbd0e2b91c447eac563bf5c6e429c3.md:12)

A proposed trigger is:

> Before implementation, review a newly introduced or changed oracle, execution procedure, or runtime-dependent prerequisite when no applicable validation evidence is recorded. Limit the review to that premise and its dependents.

For measurement, reuse existing pass records and add only what resolves the decision:

- Bind-to-import elapsed time, including first-pass and verification costs; token usage where available, otherwise “unknown.”
- Actual step diff and normalized result deltas, separating initial reviews, revisions, and unchanged reissues.
- Unique defects corrected, defects introduced by review, downstream regressions, and strengthened oracles—not just edited passes.
- Prospective “would skip” decisions while reviews still run. Looking only for later discoveries in skipped steps misses defects that every later stage also overlooks.
- Run version, route, stop rule, and domain, so unlike schedules are not pooled as independent confirmation.

P3 and P4 together identify approximately **21.6 minutes of historical review work across all three runs**, about 9% of their Improve time. That is a gross retrospective saving. Corrected measurement and a prospective quality comparison are needed before calling it a production gain.