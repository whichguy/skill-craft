# One-command stage close-out (registered 2026-11-14, before any sample)

Owner, 2026-11-14:
- asked "Is there any efficiency gain to be made without losing key functionality?";
- on this proposal: "Yes, use codex sol medium instead or terra. Use simple test cases to verify".

Standing rule the same day: change nothing unless it is materially different from current functionality.

Status: **run 2026-11-14. The registered conditions for adoption are met; whether to adopt is the owner's decision, and
the limits under "Decision" apply.**

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

## Results (2026-11-14)

Run: Codex gpt-6.1-sol at medium, `stages.py live`, 3 samples per case per arm, 2 at once per arm. B was built from
`3474addc6a2a40c0a13313c3409841831252fe12` and T from `db725d10e31f869442f8ba0ec3b0401c4886b165`. Both arms ran at the
same time and another session's Codex run was alive on the machine, so seconds are not a clean wall-time measure.
Counts of calls are not affected by load. Results roots: `~/e2e-runs-sp/20261114/closeout-B` and `closeout-T`.
Evidence: `evidence/` (`scores.json` holds every sample's measures, `scores.txt` the printed table,
`closeout-commands.txt` each done sample's close-out calls, `live-B.txt` and `live-T.txt` the runner's tables).
Scorer: `analysis/closeout_score.py`, which reads each sample's `stage-result.json`, `trace.jsonl`, `events.jsonl` and
`timeline.jsonl`; no model judges anything.

### M1, quality: the suite's own pass (every id caught or held)

| Case | B | T |
| --- | --- | --- |
| `document/ui-verification-truth` | 3 of 3 | 2 of 3 |
| `implement/ui-apply-saved-design` | 2 of 3 | 2 of 3 |
| `step-plan/ui-backend-control` | 3 of 3 | 3 of 3 |
| `validate-existing/broken-works-small-fix` | 3 of 3 | 3 of 3 |
| `validate-existing/wrong-check` (control, send-back) | 2 of 3 | 3 of 3 |
| **pooled** | **13 of 15** | **13 of 15** |

All four misses were read from `stage-result.json` and the sample's calls. None is in the close-out, and every stage
was accepted with its intended outcome:
- B implement 1 and T implement 3: control C2 (`changed_only`). The model changed `docs/shiploop/environment.md`,
  the same file in both arms, during implement.
- T document 2: control C2. The model renamed test titles in `test/board-state.test.mjs` in the work phase (call 14).
- B wrong-check 3: plant P1. The outcome was send-back, but one of P1's checks on the corrected check was not met.

### M2 and M3 as registered (window matching)

| | B | T |
| --- | --- | --- |
| done samples that ran `check` | 4 of 12 (the other 8 went from the work to the loop report and `complete`) | 12 of 12 |
| M2 median, calls after the last `check` yes | 2 (n 4) | 0 (n 11) |
| closed in one call (M2 0) | 0 | 8 |
| M3 median seconds, last `check` yes to accepted `complete` | 10.3 (n 4) | 0.7 (n 12) |

Every registered condition holds: T's M1 is not below B's, pooled (13 and 13) or on the send-back control (3 and 2);
T's M2 median is 0; T's M3 median is 9.6 s below B's. The populations differ: B's M2 and M3 exist only for the 4
samples that ran `check` at all.

### The scorer's own defect, and a second matching (added after the first scoring, as its own line)

The registered matching attaches a trace row to the call whose window, widened by 0.5 s, holds its time. Adjacent
calls then overlap, and a zero-duration call (a file write) directly before a command can take its row. T step-plan 2
read M2 = 1 where its fused command had run the last `check` and `complete` in one call. The registered fields are kept
exactly as run (the first and the final `scores.json` agree on every one). A second matching reads the command text of
each call: `shiploop check`, the loop's `done` and `shiploop complete` are recognised where they are run, the trace
rows are walked against them in order, and a sample whose rows and recognised commands disagree is marked
`unmatched`. Three samples are unmatchable (B implement 3, T document 2, T step-plan 3): the model ran the commands
inside a Python script that calls them with `subprocess`.

Read by text, over the done samples that matched (B 11, T 10):
- T closed in one call in 8 of 10. Two ran `check && done` and then `complete` on its own (document 3, step-plan 1).
- The close-out span, from the first close-out command of the final attempt to the accepted `complete`:

  | | B | T |
  | --- | --- | --- |
  | calls | 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 4 (median 3) | 1 in 6, 2 in 2, 3, 4 (median 1) |
  | seconds, median | 10.5 | 3.6 |

  The span flatters T by a reordering: T writes the result and the report before the span, and B sometimes writes the
  result inside it. The whole-sample line below is the fair total.
- Send-back control (3 samples each): B closes in 3 calls, T in 1, 2 and 2.

### M4, whole samples (reported; not in the decision rule)

| | B | T |
| --- | --- | --- |
| mean calls, mean seconds | 14.0, 93.2 | 13.4, 93.6 |
| median calls, median seconds | 13.5, 90.8 | 15.5, 96.8 |

Per case, median calls and seconds: document 18 and 144 against 16 and 145; implement 17 and 111 against 17 and 97;
step-plan 14 and 91 against 17.5 and 110; broken-works-small-fix 11 and 56 against 8 and 53; wrong-check 10 and 50
against 8 and 46. Samples of one arm on one case differ by 5 to 30 s (B step-plan 89 to 96, T step-plan 99 to 120, B
document 134 to 151), several times the 7 s the span says T saves, so 15 samples an arm cannot resolve it either way.
The mean differences are -0.6 calls (standard error 1.8, 14 samples each; the two samples whose accepted `complete`
ran inside a Python wrapper have no call count) and +0.4 s (standard error 14.9, 15 each). The calls are compatible
with the mechanism's two fewer calls and with no effect; the seconds could not show a 7 s change.

### Hazards seen

- **Duplicate checks.** 3 of 12 T done samples (document 3, step-plan 2, step-plan 3) passed `check` on its own and
  again in the closing command. B had none (its extra checks were a refusal and its yes). A repeated `check` runs every
  gate again: only `complete` takes a recorded yes (`shiploop_check.matching_yes`, read in the navigator's complete
  path). On the test stage, where a check is the base run, the candidate run and the mutation check (median 5.1 s, 90th
  percentile 17.4 s over 679 retained checks), a repeat costs about one more such run. In retained history a passing
  check followed by another check is rare: 159 pairs in 290 runs, 104 s of script time in all (0.1% of inner-stage
  time; `analysis/dupcheck.py`).
- **Stages not covered.** The stage suite has no live scenario for the test or carry-forward stage, so this round says
  nothing about the stage where a repeated check is dearest.
- **Python wrappers.** 3 of 30 samples (1 B, 2 T) ran their close-out commands inside a Python script with
  `subprocess`. That is the model's choice in either arm.
- **Order.** The loop report is written before the check's answer exists, so its evidence cannot cite that answer. A
  refused check never reaches the report (the chain stops).

### Decision

The registered conditions are "adopt only if", which are necessary and not sufficient. What this round shows: with the
closing command, a done stage closes in 1 call instead of 3 (medians), the pass counts are equal (13 and 13) and the
send-back control is undisturbed. What it does not show: a saving in whole-stage time (means 93.2 and 93.6 s), which
rests on the mechanism and on the retained runs' median from a check yes to `complete` (8.8 s by trace times over
2,078 closes, 10.3 s by host event times over 2,483; `analysis/eff.py`, `analysis/closeout.py`), not on a measured
whole-stage difference. T was not adopted or rejected by this round.

Open (owner): whether about 1 call in 3 at the close, roughly 7 s a stage on Sol at medium and about 10 s on the
retained Terra runs, is material enough under the rule of 2026-11-14 (change only what is materially different). If it
is, the round still lacks the test and carry-forward stages: two full deliveries on each arm (csv-report and
shared-expenses, the earlier smoke deliveries) would cover them and would serve as the release round.

## Round 2: whole deliveries (registered 2026-11-14, before any run)

Owner, 2026-11-14, answering "do you want that minute?": "Yes". Round 1 could not reach the test and carry-forward
stages, where a repeated `check` costs most. This round runs two whole deliveries per arm. If it is clean, T ships as a
patch release; the owner's standing rule on releases (AGENTS.md, 2026-10-28) lets a release go out once the preflight and
CI pass.

### Arms, runner, cases

- **B:** a detached worktree at `3474addc6a2a40c0a13313c3409841831252fe12` (ShipLoop 1.34.2).
- **T:** this branch's worktree at launch; each run's `result.json` records its `local_head`. The candidate code is
  `db725d10e31f869442f8ba0ec3b0401c4886b165`; the commits after it change only documents, the scorer and the journal.
- **Runner:** `test/shiploop_e2e/run.py --host codex --model gpt-6.1-sol --effort medium --source checkout`, each arm from
  its own checkout, default planning review, no turn or spend limit, `--timeout 5400` (a background task needs one).
  Baseline rows go to a file of this experiment, not to the committed `baselines.jsonl`.
- **Cases:** `csv-report` (style cli-files, 5 checks, one step) and `shared-expenses` (style stateful-service, 6 checks,
  two steps in the earlier smoke delivery). Neither leases a port. One run of each case per arm: 4 runs.
- **Lanes (2 at a time, one B and one T in each):** lane X runs csv-report B and then shared-expenses T; lane Y runs
  shared-expenses B and then csv-report T. The two shared-expenses runs overlap for only part of their time, to keep two
  models from choosing the same port at once. An apparatus failure (host crash, authentication, a port collision that is
  not the model's choice) is rerun once under a new output name and reported; a failure the model causes counts.

### Measures (script only, from each run's `trace.jsonl`, `events.jsonl`, `timeline.jsonl`, `metrics.json`, `result.json`)

- **W1, delivery:** `result.json` `pass` (invoked, plugin, process, ShipLoop done, committed, every case check).
- **W2, close-out by stage type:** for each inner action accepted with outcome done (step-plan, test-spec,
  validate-existing, implement, test, document, carry-forward), the close-out calls and seconds read by command text as in
  round 1 (the span from the first close-out command of the final attempt to the accepted `complete`), and whether it
  closed in one call. Reported per stage type and pooled. The window matching is not used; a stage whose commands ran
  inside a Python wrapper is counted as unmatched.
- **W3, repeated checks:** done stages with two or more passing `check` rows for one action, and the script seconds of the
  second and later ones (`ms` of the trace rows), by stage type.
- **W4, whole run:** host tool calls, the metrics' `turns`, tokens and minutes. Reported, not in a rule.
- **W5, refusals:** `check` and `complete` refusals per run by stage, and any refusal that names the loop.

### Predictions and decisions

- **Predictions:** all four deliveries pass; T's pooled median close-out is 1 or 2 calls against B's 3; no T test stage
  closes more slowly than B's by more than one repeated `check`; no loop-named refusal in T beyond B's.
- **Release T only if** all of these hold:
  1. both T deliveries pass W1;
  2. no T failure is caused by the close-out chain. Any T run that fails or stalls is read from its trace first. A loop
     left active, a refusal that repeats because of the chain, or a half-submitted report rejects T;
  3. T's pooled median close-out calls over done stages is below B's;
  4. T's median close-out seconds on the test stage is no more than B's plus 5 s (the cost of about one repeated check
     at the test stage's retained median, 5.1 s).
- **If a condition fails,** T is not released. The failing run's trace is read before any change, and a revised wording is
  registered here before a rerun.
- **A B failure** is baseline noise unless the trace shows ShipLoop at fault; it is reported, not rerun, unless the
  registered retry policy applies.

With 2 runs an arm this round is a coverage and safety check, not an estimate of whole-run time: a difference in minutes
is not read from it.
