# ShipLoop behavior capture and mock-DAG validation — 2026-09-17

The behavior recorder, deterministic Grok callback transport, real-navigator
replay, and protocol-aware smoke observer are implemented and validated.
This checkpoint made **zero live model calls** and did not modify production
ShipLoop. It supplements the earlier live game audit; it does not replace it.

## Executed checks

| Check | Result | Time |
| --- | --- | --- |
| `check_suite.py --suite mock` | 32 tests, no failures/errors/skips | 2.295 seconds |
| `check_suite.py --suite all` | 187 tests, no failures/errors/skips | 91.839 seconds |
| Default `dag_replay.py` | 10 cases, 383 recorded callback/control observations | 1.629 seconds across cases |
| Ruff and tracked-diff whitespace checks | Passed | — |
| Source and harness stability | Both unchanged during final checks | — |

The deliberately incorrect edge case passed by detecting its expected mismatch.
The full protocol-3 route exercised 34 stages and 68 producer/Improve callbacks.
Other cases covered two work items, duplicate/conflicting/stale callbacks,
malformed results, repeat, block/resume, pause/cold reload, and corrective work.
Mutation checks also rejected missing expected failures, incomplete mock output,
source drift, and reuse of cached navigator code after a package change.

The selected package hash was
`9a983ab4c32e5841f1cfe13b39908fd687ab56a520faac1808867d708f82080b`,
unchanged from this task's initial checkpoint. Concurrent production changes
already present at that checkpoint were preserved.

## Captured behavior and qualifications

Three real retained trials were exported without changing their result files:

| Trial | Recorded accepted history | Original outcome | Replay eligibility |
| --- | --- | --- | --- |
| Tic-tac-toe create | 35 entries, two work items | Passed | Protocol-2 routing fixture |
| Checkers create | 25 entries, one work item | Product failed | Protocol-2 routing fixture; failure retained |
| Tic-tac-toe guidance feature | 25 entries including preexisting history | Invalid trial | Rejected: preexisting run; isolation failed |

Fresh exports of both eligible cases byte-matched the checked-in fixtures.
Portable records preserve source hashes, process/settings facts, normalized DAG
history, native event counts, and original qualifications. They omit raw prompts,
commands, model prose, user paths, and product content. Future live trials write
`behavior.json` automatically, including explicit partial/unavailable outcomes.
An export failure leaves the original trial grade intact.

## Issues found and corrected

Review and mutation experiments tightened process eligibility, initial-history
attribution, accepted-result consistency, output overwrite refusal, mock terminal
validation, and source-cache binding. Missing process completion fields cannot
produce a derivable complete trace.

The current-protocol experiment exposed two legacy observer assumptions:

1. `planning-smoke` requested `plan-improve`, which does not exist as a separate
   protocol-3 stage. The selection now resolves to protocol-2 `plan-improve` or
   protocol-3 accepted `plan` after Improve, with the appropriate predecessor
   stages required. Requested and effective stage names are retained separately.
2. Callback auditing could credit protocol-3 producer `complete` before Improve
   finished. It now requires the matching successful `improve-complete` for each
   accepted protocol-3 action. Direct and supported Python-heredoc invocation
   shapes are covered; protocol-2 completion behavior is preserved.

The first combined check then rejected five host fixtures pinned to the previous
parser hash. All five fixed attribution expectations independently passed
unchanged against the new parser. Their bindings were updated with the previous
hash retained and a revalidation receipt recorded; no expectations were weakened.
The failed initial check remains in the external evidence directory.

## Reproduce and inspect

From the repository root:

```sh
python3 -B test/experiments/shiploop_e2e/check_suite.py --suite mock
python3 -B test/experiments/shiploop_e2e/check_suite.py --suite all
python3 -B test/experiments/shiploop_e2e/dag_replay.py \
  --output /tmp/shiploop-dag-replay-next
```

Use a new external replay directory. See
[MOCK-REPLAY.md — capture/replay commands and contracts](../test/experiments/shiploop_e2e/MOCK-REPLAY.md).

Retained local evidence root:
external/private retained artifact (not included in this repository).
The decisive receipts are `final-verification/validation.json`,
`final-verification/mock-final/result.json`,
`final-verification/all-final/result.json`, `replay/result.json`,
`replay/summary.json`, `export-validation.json`, and
`host-fixture-revalidation.json`. Each replay case also retains its state,
pre/post packets, expected/actual edges, and synthetic transport output.

## Evidence boundaries

Automatic live-trace derivation currently supports only complete, unambiguous
protocol-2 all-done histories with verified fresh scope and process completion.
Protocol-3 observations can be captured; their producer/Improve command sequence
is covered here with separately authored synthetic cases.

Mock reports always identify simulation and zero model calls. They do not prove
Grok prompt comprehension, actual standalone Improve execution, game behavior,
incremental feature quality, or hosted delivery. Existing CLI/runtime checks,
game oracles, live trials, and a later hosted campaign retain those responsibilities.
Live runs continue to use requested `xhigh` effort and a two-hour default cap.
