# Improvements from the DeepSeek-flash runs (2026-10-26) — plan, awaiting the owner's go

Consumer: the owner deciding what to build next, then the session that builds it. The evidence comes from two runs, both
on `claude --backend ollama` (`deepseek-v4.1-flash:1017-cloud`) at 2.16.0 / ShipLoop 1.15.0:
- hello (`~/e2e-runs/20261026/pilot-ollama-dsflash-993a9d-hello`);
- battleship (`~/e2e-runs/20261026/ds-flash-978478-battleship`, 222.4 min, PASS, no overlap).

Both are journaled in `test/shiploop_e2e/LEARNINGS.md`. Items are ranked by measured gain on ShipLoop's code
production, generic for any project.

## Ranked

| # | change | measured cost today | kind | ceremony |
|---|---|---|---|---|
| 1 | step-plan refuses a step Proof that cannot run at implement | about 24 of 222 min (11%) in battleship, one send-back | ShipLoop engine | change note, fail-first test, release |
| 2 | the run record measures the 2.15.0 gates | a misread journal (hello's deferral); one scratch script | E2E harness | quick tier, no release |
| 3 | result templates state each bounded field's limit | 8 refusals in hello, 9 in battleship; about 1-2 min a run | ShipLoop templates | change note, release with 1 |

### 1. Step-plan refuses an unmeetable step Proof (highest gain)

- **Seen.** W1's step plan gave S1 the Proof `node --test test/game.test.js`, with the paths `lib/game.js` only. The
  test file is written by the `test` stage, which comes after implement, and is absent on the item's base. Implement
  could not meet "after the last edit, each step's Proof exited 0", so it sent the plan back.
  - That cost one implement attempt plus a second step-plan, test-spec and validate-existing: about 24 minutes.
  - The same class, unreachable criteria causing send-backs, was a measured cost in run 5.
- **Change.** At step-plan `complete`, refuse a step whose Proof names a repository path with three properties: it is
  absent on the item's base, it is outside this step's and earlier steps' `paths`, and it is not created by the Proof
  itself.
  - The refusal names the path and the stage that writes it. It asks for a Proof that runs on this step's files alone,
    as the step-plan done-when already requires.
  - It reuses the base-tree lookup that already refuses `E13 … server.js does not exist on the item's lint base`.
  - Path detection is generic: command tokens that look like repository-relative files. There is no stack rule
    (the owner's generic-fix rule).
- **Proof.** A fail-first CLI test through the real `complete`:
  - W1's plan shape is refused;
  - a Proof on the step's own path is accepted;
  - a path an earlier step writes is accepted.
- **Risk.** Some file-looking tokens are not paths, such as a URL or a glob. Refuse only when the token resolves as a
  repository path that is absent on the base, so an ambiguous token is let through.

### 2. The run record measures the 2.15.0 gates (harness)

- **Seen.** I read hello's gates from Sonnet's empty lists and wrote "nothing deferred", which was wrong. I also built a
  scratch analyser (`gates.py`) to see pass sizes and refusals. Counting phrases in the event stream gave false hits,
  because the model reads ShipLoop's source and docs.
- **Change.** `metrics.json` and the scorecard gain a `gates` block, read from the run's own records, never the stream:
  - Improve: reviews, passes, the most passes in one review, the longest run of 1-10-line passes, and convergence
    refusals (`RUN/trace.jsonl`);
  - restatement: the unverified list per due stage (`results/*.md`), and restatement refusals.
  - The run report prints one line for it, and the e2e status card shows it.
- **Proof.** A hermetic test on a fixture run with one deferral and one restatement refusal; the counts are exact.

### 3. Result templates state each bounded field's limit

- **Seen.** `test_layers[].reason`, `targets[].target` and `targets[].base_state_route` have limits of 160, 60 and 240
  in `shiploop_test_layers.FIELD_LIMITS`. The packet's template shows `"<why this status; …>"` with no limit, so the
  model learns it only from a refusal. `base_state_route` took four tries in hello (483, 302, 276, 255 characters).
- **Change.** Each bounded placeholder carries its limit from the same constant, for example `"<why this status; at most
  160 characters>"`. The other producer limits (criteria 1,200, a work item's context 2,500, a headline 100) get the
  same treatment where a template prints the field. It is one source, so the text and the check cannot drift.
- **Proof.** A packet test that every placeholder of a bounded field names the limit `FIELD_LIMITS` holds.

## Not doing, with the reason

- **The improve-skill skip** (6 of 22 Improve stages). The packet already says to run the improve skill at every
  Improve stage. When the model skips it, it does the review, `improve-pass` refuses once, the model calls the skill,
  and the work is kept. The cost is one refused call a stage, so a change would not pay (KISS, and scale ceremony to measured
  gain).
- **Live evidence for the convergence gate.** A hermetic test already drives it through the real `improve-pass`
  (`test_three_small_passes_make_a_non_trivial_pass_name_its_later_stage_defect_or_end_the_review`). Live evidence
  needs a model that loops. Haiku is closed out, so record it when a run produces it, rather than spend a run looking
  for one.
- **`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` on the Ollama route.** The owner said "Not now" (2026-10-26). The open
  `api.anthropic.com` connection stays noted in the battleship entry.

## Order

1, then 3 (same release, both ShipLoop text or engine), then 2 (harness, any time). One release after 1 and 3, then one
DeepSeek battleship run (the default since 2026-10-26) to measure 1's gain: no send-back for an unmeetable Proof, and
fewer length refusals.

## Related evidence: Improve's value by stage, seven runs (2026-10-26)

"Effective" means a review with at least one non-trivial pass that changed lines. The earlier column comes from
`docs/shiploop-improve-schedule-proposal-2026-10-25.md` and counts the stricter "reviews with a DEFECT".

| stage | runs 3, 4, 5b | DeepSeek hello | DeepSeek battleship | Sonnet hello | Sonnet battleship |
|---|---|---|---|---|---|
| spec | 1/3 | 1/1 | 1/1 | 1/1 | 1/1 |
| test-strategy | 2/3 | 1/1 | 1/1 | 1/1 | 1/1 |
| plan | 3/3 | 1/1 | 1/1 | 0/1 | 1/1 |
| carry-forward | 2/2 | 1/1 | 0/1 | 1/1 | 1/1 |
| step-plan | 4/10 | 0/1 | 2/2 | 0/1 | 1/1 |
| test-spec | 1/9 | 0/1 | 2/2 (one only confirmed scope) | 0/1 | 0/1 |
| implement (per step) | 5/22 | 0/2 | 4/12 (3 real code fixes) | 0/1 | 3/3 |
| system-test-author | 1/3 | 1/1 | 1/1 | 0/1 | 0/1 |
| release-plan | 0/1 | 1/1 | 1/1 | 0/1 | 0/1 |

- **No stage is useless everywhere.** Spec, test-strategy, plan and carry-forward found something almost every time.
- **Test-spec found almost nothing.** It had 2 real catches in 14 reviews.
- **Implement is uneven.** 11 of 40 reviews found something; none did on hello, a one-line program.
- **Release-plan and system-test-author depend on the model.** Their reviews found something only on DeepSeek, where
  they fix that model's own longer plans. In DeepSeek hello, 4 of 14 non-trivial passes repaired an error an earlier
  pass of the same review had introduced.
- This supports the 2026-10-25 proposal's P3 (narrow re-reviews) and P4 (reuse an unchanged step's review). It is the
  owner's decision, so nothing is built.
