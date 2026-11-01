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
with at most 10% false calls. Run 1's results are under `run-01/` and written up below, in this file, with the bring-the-owner
recommendation for decisions D1 and D3. They are not in `LEARNINGS.md`: a commit touching that file counts for the release
gate as an E2E round for every earlier ShipLoop commit, and this run measured no ShipLoop change.

## Result (2026-11-01, run 1)

**What ran.** Kit commit e346725d1f7e60e1f220a8216892d2ba1f126a0b, one plugin build (`df86014cfb87`, skill-craft 2.28.1 /
ShipLoop 1.27.0) in both arms, Codex `gpt-6.1-terra` at `high`, 4 + 4 attempts of `csv-report` and of `seat-reservations`, two at
a time, from 16:29Z to 19:04Z (155 minutes). All 16 attempts sealed with valid evidence and none was ever a lasting
`invalid_evidence`. Raw run folders stay on the Mac (`~/e2e-runs/2026-11-01/calibration-01`); `run-01/` holds the text results:
`calibration.json` (spread.py at 3 attempts per arm), `calibration-k2.json` and `calibration-k4.json` (the same eight
runs per case dealt for 2 and 4 attempts per arm), `attempts.jsonl` (one row per attempt), `paired.json`, `status.json`,
`registration-template.json`, `run.log` and `analyze_run.py` (how `attempts.jsonl` and `paired.json` were made).

**Quality.** 16 of 16 attempts passed the accuracy and fidelity floors, so no split of the same build's runs differed in
quality and the false-DROP risk read 0. Zero failures in 8 attempts of a case is also consistent with a true failure rate of
up to about 31% (95% upper bound; about 17% over all 16), so this is no proof that a failure cannot happen.

**Tokens (processed, all-attempt) of one build against itself.**

| case | runs | median | range | largest / smallest |
|---|---|---|---|---|
| `csv-report` | 8 | 28.1M | 17.7M to 44.1M | 2.5x |
| `seat-reservations` | 8 | 35.5M | 22.1M to 50.4M | 2.3x |

**False-decision rate.** Of the equal-quality ways to deal the case's eight runs into a "control" of 3 and a "candidate" of 3,
the share where the measure moved by more than the tolerance, so the promotion rule would have called a change that is not
there:

| measure | case | 0.25 | 0.30 | 0.35 | 0.40 | 0.45 | 0.50 |
|---|---|---|---|---|---|---|---|
| tokens | `csv-report` | 35.7% | 26.4% | 17.9% | 10.7% | 7.5% | 5.5% |
| tokens | `seat-reservations` | 27.7% | 20.0% | 13.0% | 8.4% | 5.9% | 4.1% |
| turns | `csv-report` | 14.1% | 6.1% | 2.5% | 0.9% | 0.0% | 0.0% |
| turns | `seat-reservations` | 6.1% | 2.9% | 0.7% | 0.2% | 0.0% | 0.0% |

The decision-D1 rule (the smallest tolerance with at most 10% false calls on every case) gives **0.45 for tokens at 3
attempts per arm** (`csv-report` 0.45, `seat-reservations` 0.40). At 4 attempts per arm it gives 0.4 (70 re-deals of the same
eight values per case, so a weaker figure); at 2 it gives none up to 0.50. For turns, 0.30 already holds at 3 attempts per arm
(6.1% and 2.9%).

**What it means.** The stated tolerance of 0.25 on tokens, used by the stage 5 kit, is inside the noise: one build compared
with itself would have been called a change in 35.7% of the
`csv-report` re-deals and 27.7% of the `seat-reservations`
re-deals. A cycle's efficiency verdict at 0.25 is mostly noise; its quality verdict (pass or fail first) is not affected. A change
has to move tokens by about 45% to be seen at 3 attempts per arm. Nothing was changed: the tolerance and attempt count of a
cycle are the owner's decision (D1 and D3). The options, in the order this run supports them: state the measured numbers
(`--tolerance 0.45 --attempts 3`, with this run as the evidence; the cycle records a stated basis as "stated, not measured",
which understates it); turns as the efficiency measure at 0.30; or 4 attempts per arm at 0.40.

**The measured route is already closed.** `iterate.py --qualify --calibration run-01/calibration.json` is refused on current
`main` ("the scoring files or case entries changed since the calibration: calibrate again"). The two calibrated cases' catalog
entries are unchanged; the cause is that the scoring digest covers the whole `checks/` folder (26 files at the kit commit, 27
now), and 47ed1804 added `checks/expense_service.py` for the unrelated `shared-expenses` case, so this calibration went stale
an hour and a half after it started (that commit is timestamped 18:03Z; the run began at 16:29Z). A digest limited to the calibrated cases' own checks would keep a calibration usable
while other cases are added; that changes what a calibration vouches for, so it is the owner's call and is not made here.

**Arm labels.** Both arms ran one build, so a difference between the "control" and "candidate" labels would be a harness
effect (launch order, or the label in the run's folder name). In the eight twin pairs the candidate-labelled run used more tokens
in 6 (one-sided sign test p = 0.1445; median +19.7%): 4 of 4 on
`csv-report` (+34.0%), 2 of 4 on `seat-reservations` (-7.8%). After the first five pairs it
was 5 of 5 (p = 0.03); it did not hold. This is no evidence of a label effect and cannot rule one out at 8 pairs; a same-build
run with the launch order reversed would settle it if a cycle ever ends near its threshold.

**Limits.** Two port-free cases, so not the brownfield style the first design chose; one build; `high`, not `xhigh`; eight runs
per case, so the 560 re-deals are not 560 samples (`csv-report` at 0.40 read 10.7%, just over the 10% line, so 0.45 itself is
uncertain); `spread.py` has no minimum sample. The machine was shared: the one-minute load average at launch ranged from 10.3 to
157.2 (median 59.6, 18 CPUs) and other sessions' runs overlapped these attempts without the epoch's own overlap record showing
them (LR-20261101-35ad6a is about that), so some of the spread may be load. The harness marked the timing evidence invalid on all 16
attempts (`timing_valid` false), so minutes are not evidence here; tokens and turns are (attribution valid, totals not lower
bounds). One status poll during the run read 9 of the 12 attempts then sealed as `invalid_evidence`; the next poll and the final
one read all as recorded. No file in any earlier run folder was newer than that run's end, so nothing of this run's analysis
touched them; the cause is not established.
