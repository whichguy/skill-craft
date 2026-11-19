# Improve ShipLoop end to end

This procedure drives the single source harness under `$SOURCE/test/shiploop_e2e/`.
It authorizes ordinary preflight and local campaign work within the stated scope.

## Prerequisites and checkout binding

1. Resolve `$SOURCE` to a clean `skill-craft` Git checkout at current `origin/main`
   (from the current directory or supplied `checkout=PATH`). If the checkout is
   dirty or off `main`, create a campaign-owned checkout from `origin/main`.
2. Verify the local environment before spending model time:

   ```sh
   python3 -c 'import os, sys; assert sys.platform != "darwin" or hasattr(os, "waitid"), "macOS needs Python 3.13+"'
   git -C "$SOURCE" -c user.useConfigOnly=true var GIT_COMMITTER_IDENT
   ```

3. Choose fresh external directories outside `$SOURCE` for `$RUN`, `$ASSESSMENT`,
   and the persistent `$BASELINES` JSONL ledger. Never create `$RUN` or
   `$ASSESSMENT` before invoking the script: `run.py` enforces that `$RUN` is
   new and outside `$SOURCE`, creates a brand-new isolated product directory at
   `$RUN/work`, and sets `GIT_CEILING_DIRECTORIES=$RUN` so Git never walks up
   into an enclosing repository.
   - **Every ShipLoop invocation is an isolated test-case run in a new Git repo
     folder:** greenfield cases start in an empty `$RUN/work` where ShipLoop
     initializes its own fresh Git repository; brownfield cases (`ticket-import`,
     `ticket-assignment-tests`, `user-listing`) copy the pinned fixture into a
     new `$RUN/work` and initialize a fresh, independent Git repository (`git
     init` + base commit) there before ShipLoop starts. Never run ShipLoop inside
     `$SOURCE` or reuse an earlier run's product repo folder.
4. Read the full relevant Git commit messages and `test/shiploop_e2e/LEARNINGS.md`
   for the affected area before planning any ShipLoop change, so prior
   measurements, rejected approaches, and owner decisions carry forward.

### Standalone preflight

Verify source freshness and installed marketplace packages without starting a model:

```sh
python3 -B "$SOURCE/test/shiploop_e2e/run.py" \
  --preflight-only --case "$CASE" --source marketplace \
  --host codex --codex-auto-review --output "$PREFLIGHT"
```

## 1–2. Iterate and evaluate

Pick a local case whose oracle can fail meaningfully:
- Default first case: `ticket-import` (brownfield delivery with pristine
  regression tests and held-out acceptance) or `ticket-assignment-tests`
  (calibrated test-adequacy case).
- Cheap launch/delivery smoke only: `csv-report` (no held-out acceptance block;
  do not treat a `csv-report` pass as proof that test authoring improved).
- Incremental `follows` cases (such as `user-teams`): use explicit `epoch.py init`
  with a reviewed predecessor registration; guided `--qualify` refuses them
  early before invoking the improver.

For Codex campaigns, resolve the latest available Sol and Astra families from
the current official model catalog, using Sol `medium` for the subject and
fresh Astra `high` sessions for reviewer and judge. Leave the improver at the
harness default (`max`: Codex Sol `max`, or Claude Sonnet `max` via
`--improver-host claude`; do not pass `--improver-effort medium`).

Run the published build:

```sh
python3 -B "$SOURCE/test/shiploop_e2e/run.py" \
  --case "$CASE" --source marketplace \
  --host codex --model "$SOL" --effort medium --codex-auto-review \
  --output "$RUN" --baseline "$BASELINES"
```

The runner verifies clean source and installed package bytes before dispatch,
checks launch evidence again after the session ends, runs product and held-out
quality checks (requiring executed, non-skipped tests), and refreshes
`$RUN/review-export/` after held-out quality finishes.

## 3. Decide and record learnings

Reuse the retained run for independent review and judgment (retryable with a
new `--output`; each assessment uses its own `assessment_id` and writes
`$ASSESSMENT/assessment.json`):

```sh
python3 -B "$SOURCE/test/shiploop_e2e/iterate.py" \
  --case "$CASE" --review-run "$RUN" --output "$ASSESSMENT" \
  --host codex --model "$SOL" --effort medium --codex-auto-review \
  --reviewer-host codex --reviewer-model "$ASTRA" --reviewer-effort high \
  --judge-host codex --judge-model "$ASTRA" --judge-effort high \
  --improver-host codex --improver-model "$SOL"
```

After every run (including failed, blocked, or no-change passes):
- Check `nomenclature` in `$RUN/metrics.json` against
  `skills/shiploop/references/glossary.md` (S-16) and cite any retired or
  confused term beside the model action that followed.
- Inspect `$RUN/review-export/` (compact `review-export.json` and static
  `run-review.html`). Updating the shared Run Review page via
  `/skill-craft:shiploop-run-review` is optional.
- Retain a `test/shiploop_e2e/LEARNINGS.md` entry and compact
  `test/shiploop_e2e/evidence/` summary in the repository with exact source SHA,
  launch identity, commands, test counts (including skips), verdict, coverage
  gaps, token/turn scope limits, and exact ShipLoop changes (or `none`).

## 4–6. Plan, change ShipLoop, qualify, release, and repeat

Group admitted findings into one generic SDLC hypothesis per cycle. Keep
candidates isolated until qualified. If editing ShipLoop terminology, update
`skills/shiploop/references/glossary.md` in the same commit and run
`test/shiploop-retired-terms.test.py`.

Run a registered `promotion/5` comparison with either a matched A/A calibration
report (`--calibration FILE`, bound to driver, floors, and usable splits) or an
explicitly stated, unmeasured pair (`--attempts N --tolerance T`):

```sh
# Continuing from Step 3: invoke iterate.py from the learning worktree printed in
# $ASSESSMENT/assessment.json ("next_command"), because iterate.py resolves the repo
# root from its own script path. Or pass --review-run "$RUN" directly without Step 3.
python3 -B "$LEARNING_WORKTREE/test/shiploop_e2e/iterate.py" \
  --qualify --iterations 1 --case "$CASE" --record "$RECORD_ID" \
  --attempts 3 --tolerance 0.25 \
  --host codex --model "$SOL" --effort medium --codex-auto-review \
  --reviewer-host codex --reviewer-model "$ASTRA" --reviewer-effort high \
  --judge-host codex --judge-model "$ASTRA" --judge-effort high \
  --improver-host codex --improver-model "$SOL" \
  --output "$CYCLE"
```

Add `--generality-case "$SECOND_CASE"` (a case of a different style) when a
claim needs cross-style evidence. The qualification harness runs `quick_suite`
on the exact candidate diff before spending comparative runs, interleaves
control and candidate attempts, pins observed host CLI builds across arms,
marks Codex parent-thread-only token counts as lower bounds when subagents or
auto-review ran, and preserves the numeric verdict alongside review completion.

On `PROMOTE`:
1. Review the loop branch and merge the verified ShipLoop change + learning
   entry to `main` (ensuring `test/shiploop_e2e/LEARNINGS.md` sits at or after
   the ShipLoop commit so `scripts/release.py`'s preflight passes).
2. Run `scripts/release.py` and `scripts/release-push.py`, verify CI and a
   fresh marketplace install, then rerun the affected test case in a brand-new
   `$RUN` directory with a fresh, independent product Git repository folder.

On `DROP`, `UNDECIDED`, or `NO_CANDIDATE`: keep the tip unchanged, retain the
learning commit explaining why, and proceed to the next hypothesis.

## Retention hygiene

Keep raw run folders outside the checkout. Once a terminal attempt's compact
evidence and `LEARNINGS.md` entry are committed, use
`python3 -B "$SOURCE/test/shiploop_e2e/lifecycle.py" dispose "$RUN"` to remove
heavy subdirectories (`work/`, `home/`, `build/`, `quality/`) while keeping logs
and receipts. Never delete another session's runs, worktrees, or branches
without explicit owner authorization.
