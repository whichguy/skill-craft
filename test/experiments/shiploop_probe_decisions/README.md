# Decision-driven probe experiments

Test-only component study of whether an explicit decision cue improves the
current ShipLoop navigator-v3 research producer. It reuses the existing frozen
generalized-discovery runner, bounded workspace gateway, receipts, input checks,
and blind collector. It is not an installed skill dependency or production loop.

The [first measured study](../../../docs/shiploop-probe-decisions-results-2026-09-18.md)
retained the production baseline: eight workers completed and four blind
comparisons tied. Historical evidence is under `evidence/2026-09-18/`.

The [preregistered plan](../../../docs/shiploop-probe-decisions-plan-2026-09-18.md)
defines the candidate, four experiments, independent rubric, hard regression
vetoes, replication rule, and bounds. The source directory contains a historical
snapshot of the compared producer prompts; those files are experimental inputs,
not another production source of truth. A later comparison must deliberately
regenerate and freeze its own prompts and plan.

## Experiments

1. Reuse a sufficient receipt while revalidating a changed effective binding.
2. Follow the active runtime; distinguish preview success from committed writing.
3. Evaluate applicable native/skill reuse and an unrelated advertised capability.
4. Distinguish metadata access, target-data denial, and an indeterminate result.

`fixtures.materialize(family, root, mutant=False)` creates one synthetic workspace.
`fixtures.calibrate(root)` exercises reference and altered states. The coordinator
keeps required/forbidden findings outside worker workspaces. Calibration proves
the fixtures discriminate, not that a model selects the right experiment.

## Reproduce

Use a new absolute study directory outside product source and historical evidence.
Initialization and preparation are local, no-model operations; `run` explicitly
launches fresh Codex CLI sessions using the CLI default model. The gateway needs
macOS `sandbox-exec`. No installer or persistent connector is used.

```sh
python3 -B test/experiments/shiploop_probe_decisions/study.py initialize \
  --study /absolute/new-study \
  --candidate /absolute/candidate-prompt.md \
  --plan /absolute/preregistered-plan.md
python3 -B /absolute/new-study/frozen/study.py prepare --study /absolute/new-study
python3 -B /absolute/new-study/frozen/study.py preflight --study /absolute/new-study
python3 -B /absolute/new-study/frozen/study.py run --study /absolute/new-study \
  --arms trial-01,trial-02,trial-03,trial-04,trial-05,trial-06,trial-07,trial-08 \
  --parallel 3
python3 -B /absolute/new-study/frozen/study.py collect --study /absolute/new-study \
  --family f1
```

Collect each family separately. Initialization freezes private per-family tasks,
required/forbidden findings, and calibrated reference observations. Collection
combines that hash-bound packet, the frozen rubric, and the compact blind bundle
in `blind/fN-r0/ready-to-evaluate.md`. Give that file to a fresh independent judge;
withhold the variant mapping and guide differences. Preserve all judgments,
including incomplete ones. Complete transport
and a nonempty report do not establish semantic success. Never run the historical
generic oracle against this different corpus; use its own calibrated fixture
observations and the preregistered semantic rubric.

If the initial evidence meets the plan's conditions for replication, `prepare
--families fN --repetition 1` creates a fresh pair with reversed order. At most
twelve workers can be prepared/launched. Do not retry failed arm IDs, adjust the
candidate after results, or refill the original study allowance.

## Verification and limits

Run the local `test_fixtures.py` and `test_study.py` checks without model calls.
They cover reference/altered observations, write preservation, paired inputs,
source mutation refusal, and exclusion of failed contexts from valid comparison.
The live worker run and independent semantic review are separate evidence.

Fixtures use local source code and modeled service responses. No fixture proves
real account permission, MCP installation, service availability, deployment,
or full ShipLoop/Improve traversal. Time is subprocess wall time; CLI usage is
retained when available, and character-based token estimates must be labeled.
The runner enforces per-worker bounds; combined native-helper accounting remains
the coordinator's responsibility.
