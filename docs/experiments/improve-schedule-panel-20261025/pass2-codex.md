### 1. Hold

- My recommendations remain: correct P1 and P2; make P3 conditional; reject P4 as the default schedule; pilot P5 with early survivor disposition and a final audit; retain P6.
- A review making no edits does not establish that removing it preserves quality.
- P2 must validate permitted transitions. The escaped sequence was already computed using a helper that explicitly omitted legality checks.

I rechecked the repository at **`49aebb77`**, which has advanced since pass 1, and read Kimi’s saved answer and relevant run artifacts. No files were changed. Opus and Grok supplied execution-error records, not substantive peer advice.

### 2. Augment / revise

#### REJECT Kimi:

**Claim:** P1 must change `unchanged_first_pass` to prevent result-only edits from prematurely ending current ShipLoop reviews.

**Why:** The cited comment is misleading, but the executable conditions do not support that diagnosis:

- ShipLoop sets `IMPROVE_TRIVIAL_REVIEWS = 1`.
- The runtime’s unchanged-first-pass shortcut itself requires a **trivial** classification.
- The runtime emits `unchanged_first_pass` only when that shortcut bypasses the required streak. With the current requirement of one, a qualifying trivial pass already meets the ordinary gate.

See [shiploop_navigator.py — current review requirement](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:8101) and [until_loop_ephemeral.py — shortcut and completion conditions](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:1050).

The cited run-5b result-only review took two passes because its first pass reported **non-trivial / unsatisfied**, despite an unchanged tree. Its review explicitly explains that classification. This demonstrates the existing semantic gate working, not a tree-change requirement. [Run-5b test-spec review — classification](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/worktree/.shiploop-improve/test-spec-4fb41465/reviews/review-1.md:8)

Correct the stale comment. Do not add a mandatory confirming pass after every result edit: the current contract deliberately permits trivial polish on the terminating pass. Changing the definition of `unchanged_first_pass` alone would not enforce Kimi’s proposed behavior under the current one-pass requirement.

#### REVISE (own):

**From:** P1 can remain telemetry-only, with no associated behavioral correction identified.

**To:** Keep P1’s measurement change separate, but add a companion correction for **preserving and validating result-only check evidence**.

**Why:** Following Kimi’s concern about tree-only decisions exposed a different concrete problem. `_improve_pass` unconditionally replaces `checks.md` with a producer-check summary whenever the Git tree is unchanged. It does not consider edits to the reviewed inbox result. The result-only review inspected above currently has only that generic summary in `checks.md`, including “producer checks: none recorded.” [shiploop_navigator.py — checks replacement](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:8472), [run-5b checks.md](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/worktree/.shiploop-improve/test-spec-4fb41465/reviews/checks.md:1)

Replacement rule:

> Preserve authored check evidence. Reuse producer evidence only for claims unaffected by the reviewed result’s changes. When a result changes, record the applicable validation of that result and bind the evidence to its content identity. An unchanged Git tree does not establish that the reviewed result is unchanged.

This matters especially for P2: a recorded replay must survive the review callback. It does **not** require product tests where no product exists, nor another review merely because bytes changed. The companion correction has behavioral implications and should be measured separately from P1’s telemetry.

#### ADOPT Kimi:

**Claim:** P3’s conditional version needs a fresh savings calculation; unchanged reviews are not evidence of unchanged review inputs.

**Why:** I compared the accepted test-case rows before and after both run-5b send-backs:

| Revised test specification | Case changed | Fields changed | Re-review time |
|---|---|---|---:|
| W1 | `TC_28_promoFromStart` | `oracle`, `green` | 204 s |
| W2 | `TC_19_controllerMates` | `oracle`, `red`, `green` | 30 s |

The revised contracts are visible in [W1’s promotion case](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/run/results/nav-5d572b10a63a4b298be31c17856264e1.md:196) and [W2’s controller case](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/run/results/nav-eec267e83e644c7b9674b9c129e3f507.md:21). Their pass logs record [204 seconds](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/run/improve/nav-5d572b10a63a4b298be31c17856264e1/passes.md:7) and [30 seconds](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/run/improve/nav-eec267e83e644c7b9674b9c129e3f507/passes.md:7).

Both reviews remain under Kimi’s unchanged-row condition and my stricter prior-reviewed-contract condition. Therefore **234 seconds of P3’s historical 344-second saving disappear immediately** under either conditional proposal.

I retain my additional requirement that relevant premises remain unchanged. Identical case text can become invalid when its referenced setup, runtime assumption, or requirement changes. Also, `_sent_back_results.spec_before` identifies a previously **accepted** specification; it does not establish that it was previously reviewed. [shiploop_navigator.py — previous-result lookup](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:717)

#### ADOPT Kimi:

**Claim:** P2 needs a direct behavior measure and an explicit way to report that validation was not performed.

**Why:** Counting avoided send-backs alone cannot distinguish prompt compliance from a run that happened to contain no problematic sequence. Add this to my replacement wording:

> For each new or changed derived oracle, record whether its validation evidence is new, reused, or unresolved. Cite the evidence and identify which transition rules the method checks. If validation was not performed, record `NOT-REPLAYED: <reason>`; this does not satisfy the validation obligation.

Measure these statuses against the number of eligible oracles, and audit the evidence—not merely the presence of a replay claim.

The qualification matters: run 5b already recorded a successful scripted replay while explicitly acknowledging “no legality generator.” A “recorded replay” counter alone would score that failed method as success. [Run-5b replay evidence](/Users/dadleet/e2e-runs/20261024/chess-sf-full-12a23d/.shiploop-runs/work-20261025-020942-4061a0/worktree/.shiploop-improve/test-strategy-edacefd5/reviews/checks.md:3)

#### REJECT Kimi:

**Claim:** P4 becomes suitable for adoption by retaining first-step-only review while narrowing exclusions to documentation and dotfiles.

**Why:** This repairs one exclusion problem but leaves the unsupported scheduling assumption intact. A plan whose first step prepares files and whose second step introduces the behavior still skips the behavior’s review. A repair confined to S2 remains skipped after an unchanged S1 is reissued.

Dot-prefixed paths also provide no generic safety boundary. The repository’s classifier explicitly includes `.github/**` and `.forceignore` among configuration paths; excluding such paths cannot establish that execution or deployment behavior is unaffected. [path-classes.json — configuration patterns](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/references/path-classes.json:21)

There is also a source-reading correction: the peer’s cited `item_scope.changed_paths` measures changes since the **item** base, not the step base. Step-specific measurement must use the separately captured step-entry snapshot. [shiploop_item_scope.py — item diff](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_item_scope.py:148), [shiploop_navigator.py — step-entry snapshot](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:4081)

Retain P4 as a prospective “would skip” experiment while reviews still execute. The first-pass finding that all observed later-step reviews came from run 5b makes the later-step exclusion **n=1 run**, despite the pooled three-run headline.

#### REVISE (own):

**From:** Pilot survivor-disposition refusal through the existing test-stage correction cycle.

**To:** Pilot an explicit disposition check, but require a cheap retry when only the explanation changes. Do not implement it simply by adding another refusal after expensive test execution.

**Why:** Kimi’s cost concern is valid, although refusal does not inherently require restarting the whole item. The current test completion path invokes the base check, candidate commands, and mutation check. A naive missing-explanation refusal could repeat that work unnecessarily. [shiploop_navigator.py — test completion gates](/Users/dadleet/src/skill-craft/.claude/worktrees/run5-checks-9bec02/skills/shiploop/scripts/shiploop_navigator.py:4279)

Refined rule:

> Before accepting an item, require an evidence-backed disposition for each applicable surviving mutant. If only disposition text changes, recheck the disposition against the same candidate and mutation record without rerunning valid executions. Changes to code, tests, commands, or relevant setup invalidate affected evidence. Skipped mutation checks remain explicitly unverified; they create no fictional survivors.

Equivalent mutants remain admissible with evidence; this is not a 100% kill-rate requirement. Keep the end-of-work reconciliation as a backstop. Until the retry behavior exists and its cost is measured, Kimi’s survivor-count-and-record-pointer is a useful interim addition, but it does not itself resolve survivors.