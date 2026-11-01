# Stage 4b: can the loop say yes, with every attempt reviewed?

**The question.** Given a build that restores a fix we already know works, does the loop promote it when every attempt is reviewed
and judged? This is the mirror of [the stage 4 pilot](../closed-loop-pilot-20261101/README.md), which showed the loop refusing a
broken build with reviews switched off. It is part of [the closed-loop plan](../../shiploop-e2e-closed-loop-plan-2026-10-30.md).

**Why it exists.** The full stage 5 cycle has not been able to run past its first step. Two explorations (csv-report, then
seat-reservations) each stopped at the loop's designed stop, "no admitted learning record after exploring": the judge sent the
one material ShipLoop finding of each to the owner instead of admitting it, so no improver ran. Until a record is admitted, the
reviews of an epoch's attempts, a PROMOTE and the journal entry of a promoted cycle have never run live. This kit runs them
with a build whose answer is known, so a surprise is the loop's and not the change's.

## The setup

- **Candidate:** the commit that holds this kit. It has the qualified missing-completion hook.
- **Control:** the same commit with the hook taken out. `run.sh` removes it with the reverse of the delta that added it, from
  `779980629a81ce0e740f7c196e83e000dd582d99` (before the hook) to `7f25acff8dab239485f262249ec70773ba906aad` (with the hook).
  The stage 4 pilot used that build as its candidate.
- **Case:** `hello-hook-continuation`. Its check `checks/shiploop_hook_contract.py` fails any build without the hook. In the
  pilot's second run the build without it passed 0 of 3 and the build with it 3 of 3.
- **Prediction** (`prediction.json`, record `LR-20261101-58f651` in `restore-ledger.jsonl`): the share of attempts that pass
  accuracy on the case rises by at least a half. The case is therefore a capability case, so a rise in its quality can promote.
- **Size:** 3 attempts per arm, Codex `gpt-6.1-terra` at `high`, a stated tolerance of 0.25 that is a choice and not a
  measurement. **Reviews are on:** each of the 6 sealed attempts is reviewed and judged (Codex `gpt-6-astra` at `xhigh`, the
  roles' defaults), one after another.

## What counts as a pass

- **Expected: PROMOTE** (exit 0). The control fails the case's checks, the candidate passes them, the prediction is confirmed,
  the record reads `verified`, and all six attempts end `recorded` and then `reviewed`, none `invalid_evidence`.
- **Also informative: UNDECIDED** (exit 4) with a stated reason, for example a review that could not be used. It says what the
  loop needs before it can promote, and it is not a pass.
- **A finding, not a pass: DROP** (exit 3) or any `invalid_evidence`. The first would mean the candidate fell below an
  established requirement or a hard floor; read the reason before calling it a defect of either side.

## How to run (on the machine that holds Codex's login)

```sh
bash docs/experiments/closed-loop-restore-20261101/run.sh BASE_SHA /path/to/new/output/folder
```

`DRY_RUN=1` first builds both arms and shows their digests differ, with no model call. Then without it: 6 subject runs of the
case (8 to 10 minutes each, at most `PARALLEL` at once; `PARALLEL=2` is gentler when other sessions are running subject runs),
then 6 sequential reviews and judgments (10 to 15 minutes each). Expect about 2 hours. Nothing is committed or pushed by the
script. It adds two detached worktrees under the output folder, which the runner removes afterwards (`git worktree remove`). It
never kills, signals or cleans up any process or folder it did not start.

Return `OUTPUT/results/`: `entry.md`, `cycle-result.json`, `epoch-verdict.json`, `epoch-status.json`, `epoch-events.jsonl`,
`receipts/` (one file per reviewed attempt), `ledger.jsonl` (the kit's record with its rows, plus any record the reviews open),
`control-vs-candidate.stat` and `cycle-exit-status.txt` (0 PROMOTE, 3 DROP, 4 UNDECIDED, anything else: it did not decide). The raw
run folders stay where they are.

## What this does not show

One case, one known fix, one tolerance. It shows whether this loop promotes a build that restores a known fix when every
attempt is reviewed, not that it promotes a real improvement, and it does not run an improver or a purpose check. The reviews of
the attempts may open records of their own in the kit's ledger copy; those are real findings of real reviews, and landing them in
the repository's ledger is a separate decision.
