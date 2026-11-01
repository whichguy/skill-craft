# Stage 5: one full qualified cycle

Stage 5 of [the closed-loop plan](../../shiploop-e2e-closed-loop-plan-2026-10-30.md), asked for by the owner on 2026-11-01
("B, c and full"; this is C). It follows the [stage 4 pilot](../closed-loop-pilot-20261101/README.md), which exercises the same
`cycle.py` path with a hand-built candidate.

## What it is

`iterate.py --qualify` as designed, once (`--iterations 1`):

1. **Select or explore.** `learning_records.select` now reads the cycle's cases (b3328b4), so the only admitted record on the
   ledger, LR-20261031-8d97e7 (found on the hosted `gym-membership-salesforce` case), is not this cycle's. With no record it can
   take, the loop explores: one `seat-reservations` run on the tip, reviewed and judged, whose material implementation findings open
   and admit records. If nothing is admitted the loop stops there ("no admitted learning record after exploring") and no cycle
   runs. That is a designed outcome, and it is what to return.
2. **Improve and check purpose.** An improver (Codex `gpt-6.1-sol`, the role default) applies exactly one record in one commit
   with a `Learning-Record:` trailer and a prediction; the script check and a fresh review confirm the change serves the record.
3. **Register and run.** A `promotion/5` epoch: the tip against the candidate, `seat-reservations` (the exposing case) and `csv-report`
   (a case of another style, kept unseen by the improver), a stated tolerance of 0.25 and 3 attempts per arm recorded as
   unmeasured, subject Codex `gpt-6.1-terra` at `xhigh` (Extra High, the owner's choice of 2026-11-01; the first launches ran at
   `high`), 12 subject runs.
4. **Review, decide, record.** Every attempt is reviewed and judged (Codex `gpt-6-astra` at `xhigh`, the role default), then
   `decide`. The prediction's verdict and the record's outcome go to the ledger and a journal entry to `LEARNINGS.md`, committed
   on the loop branch after any ShipLoop commit.

**Why these cases.** The first launch used `user-listing` and was refused: it declares a fixed port 3000
(`quality.refuse_ports`), `run.py` takes that port as a machine-wide lease and refuses to start while another harness
holds it, and another session's `user-listing` run held it. `battleship` and `checkers` declare 3000 too, and the
`ticket-*` cases 4180. At that time a cycle on such a case would also have failed its own parallel attempts, because
`launch_all` serialised same-platform attempts but not same-port ones; it now holds back an attempt whose port another
attempt of the epoch holds and uses the free slot for other work, so such a case can run with `PARALLEL` above 1 (another
session's run on the port still refuses a start). The default cycle uses two cases with no fixed port and no hosted
platform, of different styles: `seat-reservations` (a small HTTP service on a free port, the exposing case) and `csv-report` (a
command-line tool, kept unseen by the improver as the generality case). Both have run on Terra in other sessions' studies.
No Salesforce org, no shared lane, no fixed port.

**Why the roles were swapped.** The second launch used them the other way round (`csv-report` exposing). Its exploration ran
once, found one material item and the loop routed it to the owner (record LR-20261101-bea142, with the owner in the
ledger), so nothing was admitted for an improver and the loop stopped there, as designed; no cycle ran. The results of that
launch are in `run-02-results/` once landed. The third launch explores the other case. The record is on the ledger before it
starts, so the reviewer is told it is the owner's, and the generality case is the one that record's evidence names: if the
new exploration finds the same item again it adds to that record, which this cycle cannot select, and the loop stops
for the same stated reason. The swap changes which case is explored; no record was hidden, edited or admitted by hand.

## What passes

Whatever the loop honestly decides. The cycle passes if it ends with a decision, a prediction verdict and a journal entry, or if it
stops for a stated reason (nothing admitted after exploring, a candidate that crossed the evaluator boundary, a refused
registration, a rejected purpose). It is not a failure when the candidate does not promote: at a stated 0.25 tolerance and three
attempts, most honest candidates will not. A PROMOTE is not a goal and nothing here steers toward one.

## How to run (on the machine that holds Codex's login)

```sh
bash docs/experiments/closed-loop-cycle-20261101/run.sh BASE_SHA /path/to/new/output/folder
```

By default it explores `seat-reservations` and keeps `csv-report` unseen, the pair the stage 3 calibration kit also measures.
`EXPOSING_CASE` and `GENERALITY_CASE` change that for one launch, to any two cases with no fixed port and no hosted platform; for
example `EXPOSING_CASE=shared-expenses` explores a stateful Node service that another session added (47ed1804) and keeps
`csv-report` unseen. `EFFORT` (default `xhigh`) sets the subject's reasoning effort. The reviewer, judge and improver keep their
role defaults. The stage 3 calibration kit, which another session owns and runs, measures the cases at `high`, so its figure
does not transfer to a cycle at `xhigh`; the stated tolerance stays the basis.

Expect 3 to 5 hours: the exploration run and its review (about 40 minutes), the improver (up to 45 minutes) and the purpose
review, then 12 subject runs (8 to 25 minutes each, at most `PARALLEL` at once) and 12 sequential reviews and judgments (about 10
minutes each; `review_all` holds the epoch lock for each). The script adds one detached worktree under the output folder and
commits and pushes nothing. `iterate.py` itself creates a worktree and a branch `auto/shiploop-loop-<hex>` from that checkout;
the branch is in the owner's repository until someone deletes it.

Return `OUTPUT/results/`: `iterate-exit-status.txt`, `loop-stdout.txt`, `LOOP.md`, `branches.txt`, and per stage folder
(`cycle-1`, `explore-1`) its `cycle-result.json`, `epoch-verdict.json`, `epoch-registration.json`, `prediction.json`,
`purpose-*.json`, `exploration-result.json` and `epoch-status.json`, whichever exist. The runner also pushes the loop branch and,
for a candidate kept as a ref, that ref, each as a new branch named in the runner's instructions, so the learning commits and the
candidate reach the repository byte-exact. The raw run folders stay where they are.

## What this does not show

One cycle, one stated tolerance, one pair of cases. A DROP or UNDECIDED here says the comparison could not or would not promote
this candidate at this sample; a PROMOTE would say it passed once, not that the tolerance is right.
