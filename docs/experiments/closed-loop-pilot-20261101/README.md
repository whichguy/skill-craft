# Stage 4 pilot: can the loop say no?

**The question.** If we give the loop a change that looks cheaper but is actually broken, does it refuse it? This is stage 4 of
[the closed-loop plan](../../shiploop-e2e-closed-loop-plan-2026-10-30.md). A good result is a refusal (DROP) or an honest
"can't tell" (UNDECIDED). A PROMOTE would mean the loop is broken.

## The setup

- **Control:** the commit that holds this kit.
- **Candidate:** the control with one fix taken out, the qualified missing-completion hook. `run.sh` removes it, so the
  candidate is faster (fewer tokens) but wrong.
- **Case:** `hello-hook-continuation`. Its check `checks/shiploop_hook_contract.py` fails any build without the hook, whatever
  the model does.
- **Prediction** (`prediction.json`, record `LR-20261101-1b4675` in `pilot-ledger.jsonl`): the candidate uses at least 25%
  fewer tokens, and accuracy does not drop. The 25% comes from the hook costing about 34% more tokens in an earlier run
  (07734b9).
- **Size:** 3 attempts per arm, Codex `gpt-6.1-terra` at `high`, and a tolerance of 0.25 that is a stated choice, not a
  measurement. Reviews are skipped, so the loop can only DROP or stay UNDECIDED.

## What counts as a pass

- **Expected: DROP.** The control passes the case's checks, the candidate fails the hook check, and the prediction is refuted.
- **Also fine: UNDECIDED.** It means this sample could not tell (for example, some attempts left no usable evidence).
- **A defect: PROMOTE.**

## How to run (on the machine that holds Codex's login)

```sh
bash docs/experiments/closed-loop-pilot-20261101/run.sh CONTROL_SHA /path/to/new/output/folder
```

`DRY_RUN=1` first builds both arms and shows their digests differ, with no model call. Then without it: about 6 subject runs of
the case, 8 to 10 minutes each, at most 3 at once (`PARALLEL=2` is gentler when other sessions are running subject runs). Nothing is committed or pushed by the script. It adds two detached worktrees under the output folder,
which the runner removes afterwards (`git worktree remove`). It never kills, signals or cleans up any process or folder it did
not start.

Return the folder `OUTPUT/results/`: `entry.md`, `cycle-result.json`, `epoch-verdict.json`, `epoch-status.json`,
`ledger.jsonl` (the pilot record with its `predicted`, `decided` and `verdict` rows), `candidate-vs-control.stat` and
`cycle-exit-status.txt` (0 PROMOTE, 3 DROP, 4 UNDECIDED, anything else: it did not decide). The raw run folders stay where they
are.

## What this does not show

One case, one planted defect, one tolerance. It shows that this loop rejects this regression at this sample size, not that it
rejects every regression. If the candidate has no successful attempt, the token effect cannot be judged, so the verdict
rests on the accuracy check alone.

## Runs

**Run 1 (2026-11-01, kit commit bba7561): UNDECIDED; four of six attempts were invalid evidence, from a defect in the
parallel launch.** Codex `gpt-6.1-terra` at `high`, 3 attempts per arm, 2 at a time (the runner saw three or more other
subject runs on the machine). `run-01/` holds the returned files byte for byte (the runner also pushed them at e5f0422
on `results/closed-loop-pilot-20261101`; the raw run folders are on the owner's Mac under
`~/e2e-runs/2026-11-01/closed-loop-pilot-01`). `epoch-status.json` ends with a traceback after its JSON: that was a
separate defect in `epoch.py status`, since fixed.

- Attempts: control-1 recorded; control-2 and control-3 `invalid_evidence`; candidate-1 and candidate-2
  `invalid_evidence`; candidate-3 recorded. `cycle.py` exited 4: "registered attempts have no sealed run receipt ...
  required quality evidence is unknown", so the decision is UNDECIDED and the pilot could not answer its question.
- Cause: an attempt sealed while a parallel sibling was still writing; the receipt binds each overlapping run's
  timeline, metrics and invocation files, so it read as changed the moment the sibling wrote again. Whichever attempt of
  an overlapping set ends last stays valid. Fixed by making a finishing attempt wait for its siblings before sealing.
- What the two valid attempts say, and no more: the control passed accuracy (1.0) and the candidate failed it (0.0), so
  the prediction's accuracy guard read broken and its verdict `refuted`; the token effect is unjudgeable because the
  candidate had no successful attempt (the control's processed tokens for its one success: 18,258,993). One attempt per
  arm is not a rate.
- The record's outcome in `run-01/cycle-result.json` is `admitted` (an undecided comparison). Its rows are in
  `run-01/ledger.jsonl` and are merged into the repository ledger together with the rerun's, so the record is not left
  reading admitted while the rerun is pending.
