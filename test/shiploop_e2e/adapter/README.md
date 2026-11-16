# The ShipLoop adapter for closed-loop

`facade.py` is the one program behind every command of the closed-loop adapter for ShipLoop's E2E harness (`adapter.json` is its manifest).
It drives the harness's own qualified loop (`iterate.py --qualify --iterations 1`) from a private clone of the repository and reads what the
loop wrote; it edits no scoring file, so the harness's scoring identity is unchanged. Plan and reasons:
`docs/closed-loop-phase2-plan-2026-11-15.md`; the build's rounds and findings: `docs/closed-loop-journal.md` (R7 and later).

## Files

| file | what it is |
| --- | --- |
| `adapter.json` | the manifest the owner ratifies: the commands, the four readiness claims, the pinned subject profile (Codex `gpt-6.1-terra` at `high`, tolerance 0.45 and 3 attempts stated, not measured, 2 attempts at once), the execution boundary |
| `facade.py` | the program (standard library only, Python 3.9 grammar); pinned by the manifest |
| `allowlist.json` | the cases a campaign may use, with the median minutes of a passing run as their cost; pinned by the manifest and checked against the base commit's `cases.json` |

## Running a campaign

```sh
python3 test/shiploop_e2e/adapter/facade.py setup --workspace "$X" --base "$RELEASED_COMMIT"        # once; the base is a release, 2.42.0 or later
python3 skills/closed-loop/scripts/closed_loop.py init --manifest test/shiploop_e2e/adapter/adapter.json --campaign "$C" \
    --workspace "$X" --cases hello --budget seconds=36000,runs=60 --quiet-window 1                    # the smoke campaign: one clean iteration
python3 skills/closed-loop/scripts/closed_loop.py ratify --campaign "$C" --yes-owner-approved          # the owner reads the boundary first
python3 skills/closed-loop/scripts/closed_loop.py readiness --manifest test/shiploop_e2e/adapter/adapter.json --campaign "$C" --workspace "$X" --require-start
python3 skills/closed-loop/scripts/closed_loop.py step --campaign "$C"                                   # repeat: start, poll, record
```

`readiness` is the first real compute: `cases.runs:hello` runs one real session (about 12 to 25 minutes), `improver.bounded` builds the plugin
and runs the quick tier on a clone (about 5 minutes), and `grading.scores` reads the stored run. `grading.sensitive` is not declared: no
whole-run measure has been shown to separate a known-bad run from a known-good one, so the certificate allows no quality claim.

The owner's decisions on the ledger's records reach the loop only through the facade (`CLOSED_LOOP_WORKSPACE="$X"`):

```sh
python3 test/shiploop_e2e/adapter/facade.py backlog                                                      # the material records that wait, as a table
python3 test/shiploop_e2e/adapter/facade.py decide --record LR-... --outcome accept|reject|defer|reopen --reason "the owner's words" [--reopen-when "..."]
```

## What it does, in one paragraph

X (the evaluator clone, at `$X`) is detached at a released base; its state lives beside it in `$X.facade/` (never inside X). The loop's tip is
X's ref `refs/closed-loop/tip`; every query reads Git objects at the published tip and writes nothing. A step runs in a detached worker (its
liveness is a file lock), one `iterate.py` invocation per requested case, each from the tip the one before left; a cycle ends the step. The
facts are read from the harness's JSON and Git (never its prose), the new tip is published in two phases, and baseline rows are captured from
both places they land (X's tracked file, each epoch's own) and X is restored. A failed or cancelled step publishes nothing and archives
what its worktrees held (`<out>/salvage/`), because a killed step's ledger rows can be staged and a plain diff misses them.

## Limits, said plainly

- A reviewer, judge or improver session left behind by a worker that died unobserved is in no lifecycle ledger and is not found; a cancel finds it.
- The harness's neighbour check sees only the folders beside a run (the runs-root variable is deliberately not set), not other sessions' runs.
- The tolerance and attempts rule (D1) and the loop's limits (D3) are open owner decisions; the manifest's values are stated, not measured.
- A killed `cases.runs` probe can leave a model session running: `python3 test/shiploop_e2e/lifecycle.py cleanup <run folder>` ends it.

## Tests

`test/shiploop-e2e-adapter.test.py` (queries, owner verbs, manifest), `test/shiploop-e2e-adapter-steps.test.py` (the step machinery on a stand-in
engine: process control, publication, kill windows, salvage, the model-free probes) and `test/shiploop-e2e-adapter-engine.test.py` (the real loop
with fake hosts, and the orchestrator driving a smoke campaign). All three are in the full tier only.
