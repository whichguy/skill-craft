# Step-plan parallelism census (2026-11-14)

Question: how much parallelism do the recorded step plans' `deps` expose, before any parallel mechanism is designed?
Offline and read-only: no model call, no ShipLoop command. Script: `census.py` (stdlib). Evidence:
`evidence/census.json` (one row per plan + aggregates), `evidence/summary.txt` (the printed summary).

## Method
- Roots: all 19 `/Users/dadleet/e2e-runs*` folders. Every `results/*.md` (hidden `.shiploop-runs/` included) whose
  `shiploop-state` block has `stage: step-plan` and a `result.steps` list; one row per action id (as in
  `docs/experiments/concern-scope-20261114/concern_scope.py`, re-implemented). Of an action's copies, the one whose trace
  yields the most step windows is used; no action's copies differ in their steps (0 of 928).
- Request family = `state.md` `prompt` without a leading `$skill-craft:shiploop `, hashed. Run date = `timeline.json`
  `started`.

## Definitions
- n = steps. Level of a step = 1 + max level of its deps (1 if none). L = max level (longest chain, in steps).
  W = the most steps sharing one level. Independent pair = two steps with no dependency path either way.
- Class: single-step (n = 1); chain (every step after the first has deps exactly [its predecessor]); all-independent
  (n > 1, no deps at all); ordered-non-chain (no independent pair, not a pure chain, e.g. S3 deps [S1, S2]); mixed (at
  least one independent pair otherwise); unknown (a step lacks a `deps` list). Shape figures use plans with `deps` on
  every step.
- Write-set overlap of a pair: some path of one equals, or is a directory prefix of, a path of the other, after
  stripping `./` and a trailing `/`; a glob is cut to its fixed directory prefix (a top-level glob overlaps all).
  Pairs where either step has no `paths` are counted apart.
- Step iteration (trace.jsonl): window k starts at the first `implement` packet for the work item printed after the
  plan's acceptance (the `complete` exit 0 whose `accepted` lists this step-plan action), or after window k-1 ended;
  it ends at the next `complete` exit 0 whose `accepted` lists (`document`, item): the step's implement, test, document
  and its Improve review, including any send-backs. Window k is step k (list order is execution order). Windows stop
  at a re-plan (another step-plan packet for the item). A plan is timed only if it has one window per step.
- Cross-check: `iterations/<item>.json` maps each step to its commit and `commits/<implement action>.txt` maps an
  implement action to its commit; 459 of 459 checkable steps have their implement packet inside window k.
- T = sum of step durations; C = longest dependency chain weighted by duration; ideal saving = 1 - C/T. This assumes
  unlimited concurrent workers and that a step's duration would not change if run concurrently (assumption).

## Population
928 step plans (935 copies), 787 work items, 750 runs, 75 families; runs dated 2026-10-03 to 2026-11-14.
`deps` on every step: 922; on none (legacy): 6; on some: 0. No dep names a later or unknown step.

## Headline (denominators named)
- Classes (928 plans): single-step 600, chain 218, mixed 90, ordered-non-chain 12, all-independent 2, unknown 6.
- Plans with at least one independent pair (L < n): 92 of 922 (10.0%); 92 of 322 with n >= 2 (28.6%).
  Pairs: 351 independent of 1,620 step pairs. L = 1 in 602 plans, 2 in 176, 3 in 84, 4+ in 60. W = 1 in 830 plans,
  2 in 64, 3 in 23, 4+ in 5.
- Level bound S = n/L, ASSUMING equal step durations: per-plan median 1.00, mean 1.06, max 3.75 (922 plans);
  pooled sum n / sum L = 1.10. Family-weighted (each of 73 families once): mean S 1.04; independent-pair share 7.1%;
  14 of 73 families have any plan with an independent pair.
- Write sets, same-level pairs (203, in 92 plans): overlap 90, disjoint 86, no paths 27; overlap is 51% of the 176
  pairs with paths. All independent pairs (351): overlap 192, disjoint 122, no paths 37 (61% of 314). 45 plans have at
  least one disjoint same-level pair.
- Durations: 323 of 922 plans timed (311 runs), only 75 of them with n >= 2 (22 mixed). Not timed: 243 no
  trace.jsonl (runs dated 2026-10-03 to 10-25), 155 plan action absent from the trace though state.md accepts it
  (seeded runs; a hand check found 157 of 160 such rows with no trace row at all), 49 fewer windows than steps (run
  stopped mid-plan or was re-planned). Step iteration: median 154 s, p25 116 s, p75 212 s, max 1,866 s (476 steps).
  Time-weighted saving over all 323 timed plans: 1 - 92,522/104,645 = 11.6%; over the 75 with n >= 2:
  1 - 46,224/58,347 = 20.8%. Per plan (n >= 2): median 0, p75 0.27, max 0.55; 21 of 323 plans have saving > 0.
  Family-weighted mean saving (56 timed families): 1.6%; family time-weighted: 1.7%.
- Concentration: the saving and most mixed plans come from few families (ticket-service extensions, Battleship,
  chess); see `aggregate.per_family.families` in the evidence.

## Anecdotes (Q5, read by hand; anecdotal, not a rate)
- Missing dep? `nav-82034028…` (Node chess, 13 steps) S3 deps [S1] but its task says "Preserve the S2 contract
  comments." The only plan of 928 whose task names an earlier step outside its ancestors (regex `\bS\d+\b`).
- Shared file, no order: `nav-722842cf…` (Apex chess) S2 to S5 each deps [S1] only, all edit `SLChessEngine.cls` and
  `scripts/w1-proof.apex`, and S4 says "Append asserts and keep earlier asserts" (an order on a shared file).
- Shared file, no order: `nav-00eb8a10…` (Battleship) S2 (PORT handling) and S3 (POST /api/fire) both deps [S1],
  both edit `server.js` and `scripts/w2-proof.js`.
- Independence that looks honest: `nav-00307834…` (ticket assignment) S2 endpoint, S3 filter, S4 CLI each deps [S1],
  disjoint files; `nav-7ae53d2f…` (hello) S1 `hello.py`, S2 `.gitignore`, no deps.
- Forced chain? 21 chains (n >= 3) have disjoint paths between neighbours; the four read (Salesforce engine ->
  controller -> LWC -> tab/app) each consume the previous step's output, so none looked forced.

## Limits
- Durations exist for few multi-step plans (75), so time figures rest on a small, concentrated set.
- The ideal saving ignores merge cost, shared-file conflicts, worker limits and changes in per-step time.
- Paths are the plan's declared `paths`, not the files actually changed.
- Families hash the exact text, so near-identical E2E variants count as separate families.

## Rerun
`python3 -I docs/experiments/parallel-plan-execution-20261114/census/census.py [ROOT ...]` (default: every
`/Users/dadleet/e2e-runs*`; about 1 to 3 minutes). Output is sorted and repeatable for the same run folders.
