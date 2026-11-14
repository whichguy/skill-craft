# One-command stage close-out (registered 2026-11-14, before any sample)

Owner, 2026-11-14:
- asked "Is there any efficiency gain to be made without losing key functionality?";
- on this proposal: "Yes, use codex sol medium instead or terra. Use simple test cases to verify".

Standing rule the same day: change nothing unless it is materially different from current functionality.

Status: **registered; samples not yet run.**

## Why: the measured cost of closing a stage

Measured on retained E2E runs since `check` shipped (d9667b483b8a7c8835f8f5f1396e036f5ff8fc5e, 2026-10-29), with the
scripts in `analysis/`. Each script takes a file that lists its inputs, one path per line:

```sh
find ~/e2e-runs* -name trace.jsonl -not -path '*/seed/*' > traces.txt
find ~/e2e-runs* -maxdepth 6 -name events.jsonl -newermt 2026-10-30 -not -path '*/worktree/*' -not -path '*/.shiploop-runs/*' > events.txt
```

- **Turn time** (`turns.py`, 414 Codex runs with Until Loops): each command's model thinking plus run time. The total
  was 257,364 s, about 10.4 minutes a run:
  - work 29%;
  - `complete` 21%;
  - `check` 16%;
  - loop bookkeeping about 16% (start 4.8%, done reports 7.4% plus 2.8% written as Python, next 0.7%).
- **Close-out** (`closeout.py`): 2,483 sequences from a `check` yes to the next `complete`.
  - The usual sequence is `check` yes, then one loop `done` report, then `complete` (1,470 of 2,483).
  - From the end of the check's yes to the end of the accepted `complete`: median 10.3 s, 90th percentile 33.5 s,
    38,013 s in all. That is about 92 s a run, 15% of model and tool time.
  - `complete` after a matching check yes runs in a median 0.4 s, because it reuses the yes (`eff.py`, 290 traced
    runs). So the gap is model turns, not script work.
- **Refusals** (`refusals2.py`, `resolved.py`, 290 traced runs):
  - 85% of 2,461 accepted inner finishes ran `check` first;
  - 504 `check` refusals landed inside the loop;
  - 27 `complete` refusals (1.1%) landed after it, and all 26 actions behind them were accepted later (median 9 s,
    max 38 s).

## Candidate (T)

`shiploop_loops._RESULT_HEAD`, the result line of every inner stage's Until Loop block, changes:

- **Before (B):** when the receipt says complete, keep it in evidence_refs and run the callback.
- **After (T):** write the result first. For outcome done, close with one shell command whose parts each run only if
  the one before succeeded:
  1. the callback with `check` in place of `complete`;
  2. the loop's `done_argv` with the satisfied report on stdin;
  3. the callback.

  A refused check stops the command before the report. Send-back and blocked keep their route.

No script changes. The Until Loop, the gates and `complete`'s receipt check are unchanged. Hooks still see the whole
command line, so no command is hidden in a runtime subprocess.

## Arms, runner, cases

- **B:** `--ref 3474addc6a2a40c0a13313c3409841831252fe12` (main, shiploop 1.34.2).
- **T:** `--ref` the commit that adds this registration and the candidate.
- **Runner:** `test/shiploop_e2e/stage_suite/stages.py live --host codex --model gpt-6.1-sol --effort medium`. Fresh
  sessions, 3 samples per case per arm, 3 at once.
- **Cases** (simple fixtures, one per inner stage that has a live scenario, plus one send-back control):

  | Case | Fixture | Expected outcome |
  | --- | --- | --- |
  | `validate-existing/broken-works-small-fix` | node-base | done |
  | `step-plan/ui-backend-control` | node-base | done |
  | `implement/ui-apply-saved-design` | web-choice | done |
  | `document/ui-verification-truth` | web-choice | done |
  | `validate-existing/wrong-check` | node-base | send-back (control: the done-only close-out must not change it) |

## Measures (script only, from each sample's `events.jsonl`, `timeline.jsonl` and run `trace.jsonl`)

- **M1, quality (decides first):** the stage suite's own sample `pass` (process, accepted, oracle and every id caught
  or held), per case and pooled.
- **M2, close-out turns:** for an accepted done sample, the number of host tool calls after the call that ran the last
  `check` yes, up to and including the call that ran the accepted `complete`. A trace row is matched to the tool call
  whose start-to-finish window holds its time. B is expected at 2 (the report, then `complete`); a fused T close is 0.
- **M3, close-out seconds:** for an accepted done sample, the time from the last `check` yes to the accepted
  `complete` (trace times).
- **M4, total tool calls and seconds:** from the session's start to the accepted `complete`.

## Predictions and decisions

- **Predictions:**
  - M1: T equals B on every case;
  - M2: B median 2, T median 0;
  - M3: B median at least 5 s, T median under 2 s;
  - the control: send-back in every sample of both arms that B passes.
- **Adopt T only if** all of these hold:
  - M1 for T is at least B's pass count, pooled and on the send-back control;
  - T's M2 median is 0;
  - T's M3 median is at least 5 s below B's.
- **If T loses on M1**, diagnose the failing samples before anything else. A loss caused by the close-out wording
  rejects T.
- **If T's M2 median is 1 or more** (the model does not fuse), T is not adopted. One wording revision may be registered
  here and rerun on T alone.

Retry policy: a sample that ends for an apparatus reason (host crash, harness timeout, authentication) is rerun once
under a new number and reported. Failures the model causes count.

No rescoring after the data. A better reading is its own line.

## Results

Not yet run.
