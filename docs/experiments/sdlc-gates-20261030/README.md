# SDLC gates, 2026-10-30: evidence for docs/shiploop-sdlc-gates-proposal-2026-10-30.md

The owner approved the proposal as recommended on 2026-10-30 ("Recommend and proceed"). This folder holds the tooling
for its two side experiments. Results are recorded in test/shiploop_e2e/LEARNINGS.md once they exist.

## SG1: proof order at step-plan (replay, no model)

`sg1_proof_order.py` replays a candidate step-plan check on saved runs and changes nothing. It flags a step whose
Proof names either of these:
- **rule A:** a test-class path that does not exist yet, which only a test stage could write later;
- **rule B:** a path that only a later step of the same plan declares in its `paths`.

"Does not exist yet" is read from the step's base commit in the run's iteration ledger (`git` mode) when the worktree
survives. Otherwise it is inferred from the plan's `absent` expectations (`inferred` mode).

```sh
python3 -I docs/experiments/sdlc-gates-20261030/sg1_proof_order.py skills/shiploop/scripts --self-test
python3 -I docs/experiments/sdlc-gates-20261030/sg1_proof_order.py skills/shiploop/scripts            # ~/e2e-runs/2026*/*
python3 -I docs/experiments/sdlc-gates-20261030/sg1_proof_order.py skills/shiploop/scripts 'DIR/2026*/*'
```

Each step plan prints one JSON row: its flags, and the item's implement outcomes after that plan. A last line gives
the totals.

The bar, set before any replay (proposal §5):
- DeepSeek W1 of 2026-10-26 is flagged. Its Proof ran `test/game.test.js`, which only the later test stage writes
  (LEARNINGS.md:3652).
- Grok chess 5b's S3 is flagged if its Proof names a path only S4 declares, and reported either way.
- No step whose Proof passed at `implement` is flagged.

If the bar is met, D6 adds the refusal at step-plan. Today the same mistake is caught only at `implement`'s step-proof
gate, after a whole Until Loop (skills/shiploop/scripts/shiploop_navigator.py:4699).

**Status, 2026-10-30:**
- The self-test passes (7 cases).
- A smoke replay over test/fixtures/fidelity read 12 runs and 16 step plans with no error. It judged none, because
  those fixtures keep 80-character summaries and no step Proofs. Nothing in this repository records a live step's
  Proof.
- The verdict therefore needs the owner's full saved runs (`~/e2e-runs`), which this container does not have.

## SG2: review recall, inline against fresh (seeded-defect step slices)

SG2 is declared in **PR #27**, kept apart from this folder's PR because it moves the harness's digests:
- the evaluator digest moves, because experiment.py is a top-level harness file;
- the qualification snapshot moves, because evaluators/ is part of it.

Merge it between epochs. It adds `SG2-K1` to `SG2-K4` to test/shiploop_e2e/experiments.json, one per seeded-defect step
case: `node-seeded-case-compare`, `node-seeded-numeric-sort`, `node-seeded-empty-guard`, `node-seeded-early-validation`.

- **Arms.** A is release 1.23.2 (`4e9cf843`) inline. B is the same commit with `delegation: ask-agent`, so the review
  runs in one fresh worker (experiment.py passes an arm's `delegation` to slice.py). Both arms were repinned on
  2026-10-30 from release 1.23.1 (`d98451fb`): 1.23.2 changes three skill files, among them the document loop's scope
  in `shiploop_loops.py`, and the skill has not changed since that release.
- **Shape.** Each slice runs from step-plan to carry-forward, 4 samples per arm.
- **Scoring.** `evaluators/sg2_recall.py` scores 1 when the defect is absent from the final tree. Beside it, it counts
  the Improve fix commits, which tell a review's fix from a defect that was never written.
- **Bar.** B is promoted on a catch-rate gain beyond the A/A spread, unless its minutes per sample exceed 1.5 times
  A's (read from each sample's metrics.json).
- **Limit.** Delegation also moves `implement` to a fresh worker, so the comparison is "everything in one context"
  against "fresh workers", not the review alone. The fix-commit count shows which arm's catches came from review.

Run it on a Codex Terra 6.1 xhigh host with hooks on, the current default subject:

```sh
python3 test/shiploop_e2e/experiment.py verify SG2-K1          # each case's probe tells naive from fixed (no model)
python3 test/shiploop_e2e/experiment.py queue SG2-K1 SG2-K2 SG2-K3 SG2-K4 --arms A,B --jobs 4
python3 test/shiploop_e2e/experiment.py score SG2-K1           # then each K
python3 test/shiploop_e2e/experiment.py decide SG2-K1 A B      # then each K
```

Start with a 2-case smoke (`run SG2-K1 --arm A --sample 1`, and the same for B) to measure minutes per slice before the
full queue.

**Status, 2026-10-30:** declared in PR #27 and verified with no model; not run. This container has no Codex CLI, and the
`--host claude` route (DeepSeek flash on Ollama) is at its monthly limit.

## Track A: the SDLC probes (a reader, no model)

`test/shiploop_e2e/probes/sdlc_probes.py OUT [OUT ...]` prints the probes for finished runs' output folders. It sits
below the harness's top level, so it is in neither the evaluator digest nor the qualification snapshot, and run.py never
calls it. It reads `<out>/work`, or the delivery bundle after `lifecycle.py dispose`.

| Probe | What it reports | Status |
|---|---|---|
| P1 | Suppression comments added to code or tests | built |
| P2 | A later step or item editing a test an earlier one created, with the assertion lines removed and added | built |
| P3 | Read from the run's own metrics.json: `commits.other` (counters.history) and the fidelity block's `model_commits` and `script_owned` edits | already measured by the harness; the reader reports it |
| P4 | An earlier item's test IDs missing from a later item's full regression | not built: it needs every item's IDs mapped across the verify records |
| P5 | Dependencies a manifest gained: `package.json`, `requirements*.txt`, `pyproject.toml`, `go.mod`, and an Apps Script project's `appsscript.json` (libraries and enabled advanced services). A repository with none of these is reported as not measured, never as none. | built |
| P6 | Known credential formats, reporting the format and path but never the value | built |
| P7 | Swallowed errors in product code | built |

Run it over the owner's saved runs for base rates. A probe that fires on a live run is the evidence the gate rule asks
for (proposal §4).
