# S7: does a "nearest wrong rule" clause make generated tests catch more stated conditions? (predeclared 2026-10-31)

Owner, 2026-10-31: "Run S7". It was proposed in docs/experiments/prompt-template-review-20261031/README.md §5a, after
the per-run condition test found that 74 of 448 stated conditions survived the runs' own suites.

## Question

Arms A and B both write the tests for an already-built product. Arm B is also told: give each stated condition a case
whose input makes the stated rule and its nearest wrong rule disagree. Do arm B's tests kill more of the 74 verified
survivor variants?

## Deviation from §5a, decided before any run

§5a proposed re-running ShipLoop's test-spec and test stages "for every work item" on each run's fixed product. That
is not run, for two reasons:
- The ten archived items have 2 to 4 steps each, about 29 steps. The current inner loop runs implement, test,
  document and an Improve review per step, so forty fixed-product item loops would cost roughly 10-20 hours.
- That route needs per-step implementation trees that the archived runs do not expose cleanly.

S7 runs instead as a frozen-input test-authoring A/B, the instrument class of the condition-review pilot (488ffbd9).
It measures the clause's effect on what a model writes from the same requirements. It does not measure ShipLoop's
gates, the step structure or the route. A positive result is a candidate for a live E2E check through ShipLoop, not an
adoption.

## Arms (the only difference is one sentence)

The common frame (`s7.py`, `FRAME`) gives:
- the run's frozen changed requirement texts (`../prompt-template-review-20261031/conditions/<run>.requirements.json`);
- the repository's suite command;
- this task: design positive, failure and boundary cases from the requirement text (never from the code), write them
  as tests with the case ID in the test name, run the suite until it passes, and change no product code.

Arm B adds this sentence, worded as in §5a with "criterion" read as "requirement":

> For each condition a requirement states, give a case whose input makes the stated rule and its nearest wrong rule
> disagree, such as an input out of the required order, a half-way value, both sides of a range edge, each member of
> an enumerated class, or each axis of a symmetric rule.

## Corpus

The five runs of the condition test.

| Run | Survivors | Suite command used for scoring |
|---|---|---|
| codex-r2-user-listing | 4 | `npm test` |
| claude-csv-report | 17 | `python3 -m unittest` |
| bf-ds-ticket-assignment | 15 | `npm test` |
| grok-web-battleship | 21 | `node --test` |
| v2170-ds-battleship | 17 | `node --test` |

Each session starts from the run's archived final product. That run's own tests are removed: every path ShipLoop
classifies as a test that the run added, plus v2170's run-written `browser-check/` and `system-check/` harnesses. A
test file the run changed is restored to its baseline version. Tests the product already had before the run stay.

## Model and samples

- Codex host as the E2E harness runs it: `hosts.CodexHost`, a throwaway HOME and CODEX_HOME that link only
  auth.json, full access in a scratch copy.
- Model and effort: `gpt-6.1-terra`, effort `high`.
- 4 samples per arm per run: 40 sessions. Arms interleave within each run (A1 B1 A2 B2 ...).
- No retries. A session that fails to finish is recorded as failed.

## Measures (all by script)

- **Primary.** Kill share of the run's verified survivor variants, pooled over runs (survivors killed ÷ survivors
  tried). For each variant: apply `patches/<id>.patch` to the session's final tree, run the scoring suite, and score
  a nonzero exit as a kill.
- **Regression.** Kill share of 10 killed variants per run, drawn with seed 31107 before any session ran (50 in all).
- **Validity.** A session counts only if its suite passes twice on the unmutated tree and it changed no product file.
  An invalid session is reported and left out, not rerun.
- **Cost.** Tokens from the Codex stream, and wall minutes.

## Decision rule (fixed now)

**B is a candidate for a live ShipLoop check if all of these hold:**
- B's pooled survivor kill share is at least A's plus 15 points;
- a one-sided permutation test, permuting arm labels within each run (10,000 draws, seed 31107), gives p < 0.05 on
  the pooled difference;
- B's regression kill share is no more than 2 points below A's;
- B's mean tokens are at most 25% above A's.

Otherwise B is not adopted, and the result is recorded as it falls. Nothing is adopted from S7 alone.

## Known limits

- One model and effort.
- The task frame is not ShipLoop's packet.
- The requirements are the run's final spec text.
- The scoring suite is whatever the session wrote.
- The survivors were defined against the original run's tests, so arm A may already kill some of them. The comparison
  is A against B on the same variants, not against the original run.
