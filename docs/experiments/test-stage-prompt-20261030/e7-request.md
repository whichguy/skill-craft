# E7-F by the request: the tests check everything the request says; the mutant gap is outside it

2026-10-30. Status: **firm** for this case, this implementation and this model (32 samples, a deterministic scorer);
**exploratory** beyond them. Consumer: the owner's D6 decision (docs/shiploop-test-stage-prompt-design-2026-10-30.md §9).

## Question

E7 and E7-F scored tests by mutants of the product code (`evaluators/e7_tests.py`). That takes the code as the truth: a
test that agrees with a wrong implementation kills every mutant, and a check the code added that the request never asked
for counts as a gap. The owner's aim is to test the product code against what was asked. So: do the tests E7-F's
arms A, D and C wrote fail on versions of the fixed implementation that break the request?

## Method

`evaluators/e7_request.py` (commit in this branch). Ten variants of the recorded implementation (E7-K2 A/6, tree
`a45625d3`), each changing one line to break one sentence of the `tickets-assign` prompt:

| Variant | Request sentence it breaks |
|---|---|
| limit-65, limit-63 | an agent is a non-empty name of at most 64 characters |
| empty-name | an agent is a non-empty name |
| no-unassign | `{"assignee": null}` unassigns it |
| resolved-assignable, in-progress-refused | only open and in-progress tickets can be assigned or unassigned |
| same-agent-changes | assigning a ticket to the agent it already has changes nothing |
| not-notified, requester-notified | the agent a ticket is assigned to is notified |
| no-null-assignee | every ticket shows its `assignee` (null when unassigned) |

Each carries a witness over the HTTP API. `e7_request.py verify`: all ten pass on the recorded implementation and fail on
their variant, so none is an equivalent change. A sample's whole suite (`node --test`) runs once per variant on a copy of
its worktree; a variant is killed when the suite fails twice running (no flaky kill; none occurred). The same runs with
`test/` restored to the seed commit give the tests that existed before the test stage.

## Result (e7-request-results.json; `e7_request_export.py` prints it)

| Arm | n | Request score | Earlier tests alone | Mutant score (e7_tests.py) |
|---|---:|---:|---:|---:|
| A | 8 | 1.000 | 0 of 10 killed | 0.604 |
| D | 8 | 1.000 | 0 of 10 killed | 0.625 |
| C | 8 | 1.000 | 0 of 10 killed | 0.583 |
| T (D6) | 8 | 1.000 | 0 of 10 killed | 1.000 |

1. **Every one of the 32 runs kills all ten request-breaking variants.** Against the request, the test stage is complete
   in every arm, including T: D6 raised the mutant score from 0.604 to 1.000 (exact p 0.0001, design §7f) and the request
   score did not move. The measure is saturated, so it cannot rank the arms.
2. **It is not insensitive.** The tests that existed before the test stage kill none of the ten (0.0), so the scale runs
   from 0.0 to 1.0.
3. **The API-level 64-character boundary is tested in 32 of 32 runs** (limit-63 and limit-65 are killed everywhere).
4. **All 57 target survivors of the mutant score sit on two lines of `src/persistence.js`:** 144 (45, the `||` clauses
   of the stored-record check) and 145 (12, the 64-character bound there). That is load-time validation of a
   hand-edited data file. The request does not mention it; implement added it by following the file's pattern for the
   other fields. So the mutant score's gap is not a request gap.
5. **The case's own hidden check catches 3 of the 10** (limit-65, no-unassign, no-null-assignee). The tests are far
   more thorough than the check the harness uses as its oracle.

## What this settles, and what it does not

- **Settled for this case:** the arms differ in how many code-introduced internals their tests pin, not in whether the
  request is tested. The mutant score's apparent differences (0.58 to 0.63) were never differences in coverage of what
  was asked.
- **For D6:** D6 feeds back exactly those load-time survivors. On this case a gain would raise the mutant score without
  raising request coverage, which is already complete. Whether tests of the code's own validation are worth the extra
  refusals is a separate call from the one this experiment measures.
- **Not settled:** ten variants I wrote after reading the recorded implementation and the request, each a whole-clause
  break, and A/1 was scored before the other 23 (the set was not changed after it). Subtler breaks (a name padded with
  spaces, a reassignment A to B to A, an unassign of a closed ticket) are not in the set, and a set built to separate
  the arms might. One case, one implementation, one model.
- **Arm T (D6)** was scored on 2026-10-30 after the other session finished its 8 runs (they ran the scorer; this export
  adds the row). Its tests pin the load-time guard the request never mentions, which is where the mutant gain comes from.

## Decision

2026-10-30, owner: **skip D6** (answering "Skip D6 and keep ShipLoop's test stage as it is?" with "Yes, skip D6"). The stage
mutation check keeps its catalog and its spread sampling, and nothing in ShipLoop changes. Why: the request measure above
shows the tests already cover everything the request says, and the survivors D6 would feed back are outside it. Arm T's
samples (E7-F/T/1..8) were a different session's runs; they finished with 1.000 on the mutant score and 1.000 on the
request score, the same as A, D and C.

## Evidence

e7-request-results.json (32 samples, arms A, D, C and T, and the ten variants' `verify` rows); per-sample `request-score.json` under
~/e2e-runs/e7-20261030/E7-F/{A,D,C}/<n>/; the scorer test `test_e7_request_variants_change_one_line_once_and_the_scorer_restores_the_file`.
