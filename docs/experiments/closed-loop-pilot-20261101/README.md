# Stage 4 pilot: can the loop say no?

Stage 4 of [the closed-loop plan](../../shiploop-e2e-closed-loop-plan-2026-10-30.md), and the 10-29 plan's P5 ("a known-bad
candidate with one cheap regression case; its first success criterion is rejection or an honest undecided result, never a
forced promotion"). Built 2026-11-01 on the owner's instruction to run the known-bad pilot and one full cycle.

## What it is

A faster-but-incorrect candidate, by construction and not by instruction.

- **Control:** the commit that holds this kit.
- **Candidate:** the control without the qualified missing-completion hook. `run.sh` applies the reverse of the source delta
  between `779980629a81ce0e740f7c196e83e000dd582d99` (the control of 07734b9f's pair) and
  `7f25acff8dab239485f262249ec70773ba906aad` (its candidate), leaving out the change note a release already consumed.
- **Case:** `hello-hook-continuation`. Its own harness check, `checks/shiploop_hook_contract.py`, runs the selected package's
  real Until Loop runtime and keepalive decisions, so a build without the hook fails it whatever the model does. In the live
  pair behind 07734b9 the pre-hook control failed it ("returned allow/no-progress three times ... and stopped that probe",
  accuracy 3 of 4 checks).
- **No-model evidence that the candidate lacks the hook** (17cbbd9b with the reverse applied, the hook's tests left as they
  are): `shiploop-keepalive` 11 failing tests, `shiploop-loops` 13, `shiploop-actual-improve-cli` 1.
- **Prediction** (`prediction.json`, record `LR-20261101-1b4675` in `pilot-ledger.jsonl`): tokens down by at least 0.25 on the
  case, guarded by accuracy not down. The 0.25 is what the pair behind 07734b9 suggests the hook cost (+34.2% tokens), so it is
  a claim a careless simplification would make.
- **Basis:** a stated, unmeasured tolerance of 0.25 and 3 attempts per arm, Codex `gpt-6.1-terra` at `high`, as the owner chose
  on 2026-10-31. Reviews are skipped, so the cycle can only DROP or stay UNDECIDED; it cannot promote.

## What passes

Not PROMOTE. The expected result is DROP: the control passes the case's checks, the candidate fails the contract check, quality
is read before cost, the accuracy guard is broken, the prediction reads refuted and the record reads `refuted`. An UNDECIDED
result is honest and also passes (the plant did not bite, or attempts were unknown); it is recorded as such and says the
measurement could not see this defect at this sample. A PROMOTE would be a defect in the loop.

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

One case, one planted defect, one stated tolerance: it shows that this loop rejects this regression at this sample, not how
often the tolerance misleads or that the loop rejects every regression. The prediction's token effect cannot be judged when
the candidate has no successful attempt (cost per success is undefined), so the verdict rests on the guard.
