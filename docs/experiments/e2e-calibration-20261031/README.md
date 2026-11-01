# Stage 3: the same-build calibration

Stage 3 of [the closed-loop plan](../../shiploop-e2e-closed-loop-plan-2026-10-30.md): measure how much one ShipLoop build
differs from itself, so a later comparison knows how big a change must be before it can promote or drop it. Nothing here
changes ShipLoop or the harness.

## What runs

| Case | Style | Attempts (both arms, one build) |
|---|---|---|
| `csv-report` | command-line tool | 8 (4 + 4) |
| `seat-reservations` | small HTTP service | 8 (4 + 4) |

These are the two cases of the [stage 5 cycle](../closed-loop-cycle-20261101/README.md), so the figure measures the noise
of the comparison it would replace. Subject: Codex `gpt-6.1-terra` at `high`, the cycle's subject. No reviews or
judgments. `E2E_CALIBRATION_PARALLEL` sets how many run at once (default 3; use 2 beside other sessions' runs). 16 runs of
8 to 25 minutes each: about 1½ to 2½ hours.

**Why not the first design (2026-11-01).** It ran `battleship`, `user-listing` and `ticket-assignment`. Each declares a
fixed port (`quality.refuse_ports`: 3000, 3000 and 4180), which `run.py` leases machine-wide and `cycle.launch_all`
does not serialise, so its own parallel attempts would have refused one another, and another session's run held port
3000 when the cycle's first launch tried it. `battleship` has also never run on Terra. The kit had not run, so no
evidence changed.

## How to run it

It needs the Codex CLI signed in to the owner's account, which the cloud containers do not have. On the owner's
computer, in a checkout of `main`:

```sh
bash docs/experiments/e2e-calibration-20261031/run.sh                          # freeze HEAD, run everything
E2E_CALIBRATION_DRY=1 bash docs/experiments/e2e-calibration-20261031/run.sh    # check the setup, launch nothing
```

The output folder is `~/e2e-runs/calibration-<UTC date>/` (`E2E_CALIBRATION_OUT` overrides it). It holds:
- `source/`, a detached worktree of the frozen commit, so the evaluator cannot change under the runs;
- `build/`, the one plugin build both arms run;
- `epoch/`, the registered epoch with every sealed attempt;
- `launch-logs/`, `status.json` and `calibration.json`.

Running the script again with the same output continues where it stopped. It never relaunches an attempt whose launch
was interrupted; seal one with `epoch.py reconcile` (the command is in the script's header) or leave it unknown.

## What comes back, and where it goes

`calibration.json` (spread.py) gives, per case, the successes and failure rate, the median and range of tokens, turns
and minutes, the false-decision rate at each tolerance from 5% to 50%, and the recommended tolerance at 3 attempts per arm
with at most 10% false calls. Commit it here as `calibration.json` with a LEARNINGS entry that states the tolerance, the
false-drop risk per case and battleship's time on Terra, and bring the owner a recommendation for decisions D1 and D3.
