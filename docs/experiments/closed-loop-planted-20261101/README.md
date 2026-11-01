# Stage 5b: a full cycle on a planted fault

**The question.** Can the whole loop run live, from the first exploration to the journal entry: find a defect, admit it, have the
improver fix it, check the fix, run a full epoch with every attempt reviewed, and decide? Three explorations of ordinary cases
(csv-report, seat-reservations, user-listing) each stopped at "no admitted learning record after exploring", because the
judge sent every material ShipLoop finding to the owner (disposition investigate). The stage 4b restore pilot showed what happens when
the defect is plain and mechanical: the reviews of a build without the qualified missing-completion hook routed an
implementation-eligible finding every time. So this run gives the loop that plain defect and nothing else. See
[the closed-loop plan](../../shiploop-e2e-closed-loop-plan-2026-10-30.md), "How this program concludes".

**What this is and is not.** It is an instrument test. The "fault" is a revert of a fix we already have, made by `run.sh` in a throwaway
checkout, so no product decision is involved and nothing it produces is a change to ShipLoop. It tests whether the machinery works,
not whether the improver is clever: the improver can read the git history and see what is missing, and may simply restore it. The
loop branch it produces has the revert as an ancestor, so **it must never be merged**; its journal entry, ledger rows and evidence are
landed by copying them.

## The setup

- **Checkout:** the commit that holds this kit, plus one local commit `run.sh` makes that reverses the hook's source and tests
  (`git diff 779980629a81ce0e740f7c196e83e000dd582d99 7f25acff8dab239485f262249ec70773ba906aad`, minus `changes/`). Its message says
  what it is. The reviewer and the improver read the last commit messages, so the loop is not blind to it; the defect itself is found
  by the case's own check, which fails any build without the hook.
- **Cases:** `hello-hook-continuation` (exposing: its check `checks/shiploop_hook_contract.py` fails a build without the hook) and
  `csv-report` (of another style, kept unseen by the improver). Neither declares a fixed port or needs a hosted platform.
- **Size and setting:** 3 attempts per arm, Codex `gpt-6.1-terra` at `xhigh` (the owner's setting of 2026-11-01), a stated tolerance of
  0.25 recorded as unmeasured, three subject runs at once, every attempt reviewed and judged (Codex `gpt-6-astra` at `xhigh`), each
  incomplete review assessed again up to three times. The improver is Codex `gpt-6.1-sol`, the role default.
- **Selection:** a record is taken only if it is admitted, material (a sighting that is material makes a record material; the seeded
  value `high` counts), found on the exposing case or seeded, and not seen on the unseen case. If the reviewer links its finding to an
  existing record (`same_as`), that record is the one taken.

## What counts as a pass

- **Expected: a complete cycle.** The exploration admits a record, the improver commits one change with a prediction, the purpose check
  passes, the epoch registers, all twelve attempts are `recorded` and then `reviewed`, and the cycle ends with a decision, a
  prediction verdict and a journal entry. PROMOTE is the likely decision if the improver restores the hook, but a DROP or an
  UNDECIDED with a stated reason is also a complete answer: it says the machinery decided, not that the improver was right.
- **Also informative: the designed stop** "no admitted learning record after exploring". It would mean the reviews did not
  admit the planted defect even when it is plain, and the report says what the ledger shows.
- **A finding, not a pass:** an attempt that reads `invalid_evidence`, a review still incomplete after three assessments, a crash in
  the improver or purpose-check stage, or a refusal at registration. Read the reason before blaming either side.

## How to run (on the machine that holds Codex's login)

```sh
bash docs/experiments/closed-loop-planted-20261101/run.sh BASE_SHA /path/to/new/output/folder
```

`DRY_RUN=1` first makes the planted commit and prints its diffstat, with no model call. Then without it: the exploration (about 10 to 25
minutes with its review and judgment), then, if a record is admitted, the improver (up to 45 minutes), the purpose check, twelve subject
runs and twelve reviews (about 10 minutes each, one after another). Expect 3 to 6 hours. Nothing is pushed; the script adds one detached
worktree under the output folder, and `iterate.py` makes its own worktree and a branch `auto/shiploop-loop-<hex>` that the runner pushes
to a `results/...` branch for the evidence and never merges.

Return `OUTPUT/results/`: `iterate-exit-status.txt`, `loop-stdout.txt`, `LOOP.md`, `branches.txt`, `planted-fault.stat`,
`planted-commit.txt`, and per stage folder (`explore-1`, `cycle-1`) `listing.txt`, `cycle-result.json`, `epoch-verdict.json`,
`epoch-registration.json`, `prediction.json`, `purpose-*.json`, `exploration-result.json`, `epoch-status.json`, `epoch-events.jsonl` and
`receipts/`, whichever exist.

## What this does not show

One planted defect that the improver can undo from history, one case pair, one tolerance that the stage 3 result says is too small for
efficiency (quality decides first here, so the decision does not depend on it). A PROMOTE says the loop's machinery can promote a plain
fix it found itself; it does not say the loop finds or fixes real, subtle problems, and it must not be read as an improvement to ShipLoop.
