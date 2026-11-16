# Does Backchain provide any value at all? A design and evidence review (2026-11-15)

Owner question, 2026-11-15: "Deeply inspect the design and intent of backchain, and really help to identify if,
honestly, it provides any value at all (or if the construct and premise itself is too rudimentary and the models
already have it handled)."

No new planning attempts ran for this review. It reads the released design, re-reads the 2026-11-15 value study's
evidence ([../backchain-value-20261115/](../backchain-value-20261115/)), compiles the whole recorded history, and adds
an independent review by another model family. The findings and the decision record are journal Round 15 in
[../../backchain-efficiency-journal-2026-11.md](../../backchain-efficiency-journal-2026-11.md).

## Method

1. **Design read** of `skills/backchain` at origin/main 477542e047f8dcbadcfc4b5767d956c85017631c: the card, the seven
   prompts, the references, the three scripts, and ShipLoop's two Backchain references.
2. **Re-analysis of the value study's grades**, per criterion: [criterion_breakdown.py](criterion_breakdown.py) writes
   [criterion-breakdown.json](criterion-breakdown.json) from `evidence/grades.json` (both Opus passes, 60 attempts).
3. **Backchain's own check on the one invalid no-skill plan**:
   [invalid-no-skill-plan-check.json](invalid-no-skill-plan-check.json) (`backchain.py check` on a packaged copy of
   `independent-inspection-scopes--none--sonnet` from `evidence/plans.json`).
4. **Design inventory**: [design_inventory.py](design_inventory.py) writes [design-inventory.json](design-inventory.json),
   the instruction bytes each arm read and the script split.
5. **The caller contract's rules on both arms**: [preservation_check.py](preservation_check.py) writes
   [preservation-check.json](preservation-check.json), comparing all 30 final plans of the five inherited-plan cases
   with their inherited plans under the rules of `references/convergence.md` and `references/caller-contract.md`.
   It reads the inherited plans from the cohort's case file in the private harness (`BACKCHAIN_COHORT_CASES`).
6. **History**: a read-only research agent (Claude Sonnet) compiled every recorded measurement and catch from the
   private harness and skill-craft history; the main session checked the claims the verdict rests on and corrected
   three readings. [history-report.md](history-report.md).
7. **Independent review**: Sol 6.1 (gpt-6.1-sol) at max effort, read-only, on a neutral export of public files only
   (origin/main's `skills/backchain`, the value study folder, the efficiency journal, ShipLoop's two Backchain references
   and Plan Dispatcher's card; local account paths replaced by `~`). Brief: [sol-brief.md](sol-brief.md); the review
   verbatim: [sol-review.md](sol-review.md). The brief carried the owner's question and no conclusion of the main
   session's.

## Files

| File | What it holds |
|---|---|
| [criterion-breakdown.json](criterion-breakdown.json) | universal criteria: mean points (0-2) per arm and model; case-specific criteria: 204 paired differences, 190 tied, 7 better, 7 worse |
| [invalid-no-skill-plan-check.json](invalid-no-skill-plan-check.json) | the receipt: invariant 7 fails twice (two `from: null` needs not listed word for word in `initial_state`) |
| [design-inventory.json](design-inventory.json) | 5,544 bytes of instructions for the no-skill arm against 90,960-172,539 for a fresh Backchain run (16-31×); script lines |
| [preservation-check.json](preservation-check.json) | 0 of 15 Backchain and 0 of 15 no-skill plans break the inherited-plan rules; no-skill plans add 31 `initial_state` facts, none closing an inherited undeclared need |
| [history-report.md](history-report.md) | the recorded evidence, July to November 2026, with verification notes |
| [sol-brief.md](sol-brief.md), [sol-review.md](sol-review.md) | the independent review's brief and its text |
