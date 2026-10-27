---
Execute: ask
Status: draft for the owner; nothing launched; replaces R2 pairs 3 to 8 of docs/shiploop-effort-by-stage-experiment-plan-2026-10-24.md
Opened: 2026-10-25
Consumer: the owner, who reads it to approve or strike rung S0 before any slice is launched
Source: owner decision 2026-10-25 ("go with this" after the pair-1 finding); journal docs/type1-fast-models-sdlc-journal-2026-10-24.md sections 18 and 19
---

# E-EFF2: does lower effort on Improve pass 2 and later pay, tested on slices

Question: in a ShipLoop inner loop, does lowering reasoning effort on Improve passes 2 and later cut tokens and time
without changing what Improve delivers? Control against treatment, nothing else varied. One host, Grok 4.7.

## 0. Why this replaces the full-run test

- **Pair 1 of E-EFF1 (full `hello` runs) could not see the lever.** Mechanical stages plus Improve pass 2 and later were 22% of
  run seconds in both arms (treatment 899 of 4,031 s, control 1,301 of 5,837 s). The other 78% runs the same settings in both arms
  and differed by 31% between them (3,132 s against 4,536 s; 258 against 391 model calls). That is run-to-run noise larger than the
  lever's whole ceiling. Output and reasoning tokens are about 0.5% of all tokens; the rest is context re-read per call.
- **A slice removes the shared part.** `test/shiploop_e2e/slice.py` runs one work item through the inner loop on a seeded fixture,
  including the Improve child after the implement step, and stops before release. Measured on the 80 Grok 4.7 medium slices of
  the plan-sizing batch (`/Users/dadleet/e2e-runs/e6-r1-20261024`, session spans from `sessions.jsonl`): 442 to 2,132 s per slice,
  median 609 to 1,267 s by case set, against 4,000 to 5,800 s for a full hello run. In those 80 slices 55 had an Improve child that
  reached pass 2 or later (passes per child: 1 pass 25, 2 passes 45, 3 passes 9, 4 passes 1).
- **What a slice cannot test:** the seven outer mechanical stages (prepare, system-test, product-acceptance, release-check, release,
  release-verify, operations). A slice stops before them (`no_overshoot`). Their ceiling is about 13% of stage seconds on Claude
  (E-EFF1 plan section 0), so they are deferred, not tested here.

## 1. Rungs

**S0, measure the ceiling (7 control slices, no treatment).** Run the seven cases of `test/shiploop_e2e/step_cases.json` once each at
Grok 4.7 medium with the existing `--effort-schedule control.json` (restarts at class changes, as in R1), two at a time. Report per case:
seconds, tokens, how many Improve passes ran, and the share of slice seconds and tokens in class I2 (`run_totals.py classes`).
Estimated 1 to 1.5 h, taken from the 80 measured slices; not yet measured on these cases. **Stop rule: the owner reads the I2 share
and decides whether S1 is worth running; no threshold is set in advance.**

**S1, the blocked pair (only on the owner's go after S0).** The same cases, control and treatment (`treatment.json`: I2 low, rest medium),
one trial per arm, two at a time; arm order per case alternates by a seeded draw recorded in a frozen manifest, as in E-EFF1. The judge
rule needs 8 scenarios and only 7 cases exist, so S1 needs an eighth case (a fixture and a `step_cases.json` row), or two trials per case
with the clustering stated. 16 slices at about 17 min each, two at a time: about 2.5 h. Nothing in `skills/` changes.

## 2. Readouts

1. **Quality, script-scored first:** the slice verdicts (`process`, `inner_loop`, `assembled`, `checks`, `no_overshoot`) and, on the
   three `node-seeded-*` cases, whether the seeded defect is fixed (`seeded_defects.py`). A second judge only if the scripts tie.
2. **Tokens, then seconds**, as run totals of the slice, with the class I2 figures beside them. Because the shared part is now small, the
   I2 figures are close to the totals.
3. **Refusals attributed** by `run_totals.py refusals` (restart-induced "write this pass's review" refusals are excluded from the
   refusal gate, as in the E-EFF1 plan section 10.5).
4. A slice whose Improve child never reaches pass 2 in either arm is reported and not counted for or against.

Decision rule unchanged: a material quality difference first; then significantly fewer tokens; then less time; a tie keeps the control.

## 3. Unknowns

| # | Unknown | How it is resolved |
| --- | --- | --- |
| V1 | Do the seven `node-*` slices reach pass 2 as often as the chess slices did (55 of 80)? | S0 count |
| V2 | Does the effort schedule fire on a real Grok slice? It was shown on full runs (R1) and tested on slices only with a fake host | S0 includes one treatment slice on `node-add-function` as a smoke |
| V3 | Pass 2 happens only if pass 1 changed the tree, so the two arms can diverge before the lever applies | Reported per case; a fork at the end of pass 1 is the remedy if it is common |
| V4 | The Grok account is shared; the E2E session waits for it | S0 starts only after E-EFF1 pair 2 ends and the E2E session has had its window |

## 4. What happens to E-EFF1

R2 stops after pair 2 (seat-reservations). Pairs 1 and 2 are kept as full-run evidence: class shares and a noise level on two scenarios.
Two scenarios cannot decide (the judge needs 8), so R2 is reported as partial and not as a result. The frozen manifest stays as written.
