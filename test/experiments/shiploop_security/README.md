# ShipLoop security pilot harness, prospective V6

This opt-in apparatus builds a new private harness from the exact frozen V5 retry source. It needs Python 3, Git, and Node. It does not copy the old schedule, registration, prepared checkout state, candidate package, observations, results, or credentials. It does not start subjects. Keep the materialized tree and the private probes outside any subject checkout.

Run the no-model qualification with the **evidence directory** of the completed retry and an existing private report directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 test/experiments/shiploop_security/qualify.py \
  --frozen "$FROZEN_RETRY_EVIDENCE" --reports "$REPORTS"
```

This creates a fresh report and a temporary materialization. It checks the 73 earlier reference dispositions and 21 new controls, then retains calibration, synthetic grade and old-format rejection records. The synthetic records use real Git worktrees and the native exporter but contain no model responses. Run the standalone scope/materializer tests with `python3 -m unittest discover -s test/experiments/shiploop_security`.

For an operator who already has approval for a **separate** study, `materialize.py --frozen "$FROZEN_RETRY_EVIDENCE" --output "$NEW_PRIVATE_ROOT"` builds the private harness without running calibration or dispatch. Use a new directory whose parent exists. It checks the exact source path inventory, bytes, and modes before applying `v6.patch`; the zero-context hunks are checked against those pinned bytes. The output includes the prospective schedule generator, native operator, dispatcher, grader, and decision program.

Before any subject starts, prepare fresh public seed records at `operator/prepared-v3` using the materialized runner's `prepare` subcommand, generate `schedule.json` with `preflight/make_schedule.py`, and freeze the study as `shiploop-security-pilot/v2`. Keep the existing cohort and arm fields, update their paths and hashes, and register the new corpus with modes and the materialized `scope_evidence.py`, `logger_failure.cjs`, `analysis/grade.py`, and `analysis/decision.py` alongside the existing required sources. The dispatcher checks the registration digest and all listed identities before admitting a subject. Preserve the two scope receipts and both exported trees until independent grading is complete. The grader and decision program reject V1 inputs; never relabel old rows as V2.

The actual initial snapshot is taken after the native checkout and first render, before the first subject starts. Both endpoints use the native exporter's selection. Existing regular-file modes are compared in full; directory and symlink modes are outside this measurement. Mode drift between fixture and checkout is reported separately. Scope reports show root `SHIPLOOP.md` as changed documentation when applicable, and reject new links, skipped paths below a link, unrelated paths, and executable-bit increases. The diagnostic checks exercise the ordinary successful call and a separate throwing logger with independent synthetic credential, request, message, and cause markers; the retained report records booleans, and raw logger-error markers stay in transient captures. The outer probes test warm export, authorized update, then immediate same-process export, alongside foreign and denied operations. These checks calibrate the apparatus for the named cases. They do not measure a prompt improvement or provide a general security or isolation guarantee.

## Opt-in V7 apparatus

V7 starts with the same pinned 329-file V5 allowlist and unchanged V6 recipe, then applies the reviewed source delta and private probes. It seals the final path, byte and mode inventory in `assembled.json`. The completion source hashes identify the bytes that informed the port; those historical files are never imported by the assembled runner. Supply `--verify-completion-source` with the prior completion root to check those source hashes read-only.

Use canonical absolute paths for all inputs and outputs, with no `..` components or symlink aliases. Before running qualification, create a private report parent owned by you outside the source checkout and every frozen root. Pass that existing directory to `--reports`. No models are called by either command:

```sh
python3 -B test/experiments/shiploop_security/materialize_v7.py \
  --frozen "$FROZEN_RETRY_EVIDENCE" --output "$V7_APPARATUS"
python3 -B test/experiments/shiploop_security/qualify_v7.py \
  --frozen "$FROZEN_RETRY_EVIDENCE" --reports "$OWNED_REPORTS"
```

Qualification retains separate reference, unit control, inert pipeline and legacy admission logs. V6's 94 dispositions must survive, alongside the added V7 references. Inert controls exercise real Git export/restore and the actual V7 grade, decision and mask commands. Ordinary CI runs the single `security-harness` suite via `python3 -B test/experiments/shiploop_security/run_tests.py`. The runner discovers the local tests, needs Python, Git and Node, and works without any archives, credentials or network.

For a separate authorized smoke, use a clean, pinned checkout and its separately built plugin. Set `V7_APPARATUS`, `HARNESS`, `PLUGIN` (the build's `plugins/skill-craft` directory) and `CODEX_BIN` to absolute paths, and set `HARNESS_HEAD` to the full commit SHA. Keep the same runtime environment through preparation, dispatch and grading.

```sh
python3 -B "$V7_APPARATUS/operator/runner.py" prepare \
  --case secret-exposure --corpus "$V7_APPARATUS/corpus" \
  --harness-root "$HARNESS" --expected-head "$HARNESS_HEAD"
python3 -B "$V7_APPARATUS/preflight/make_schedule.py" draft \
  --purpose smoke --harness-root "$HARNESS" --expected-head "$HARNESS_HEAD" \
  --plugin-dir "$PLUGIN" --codex-bin "$CODEX_BIN" --host-seconds 900 --cohort-seconds 1320
```

The draft is one noncomparative Sol 6.1/medium sample with explicit launch controls and a registered Astra/high judgment role. After the exact draft is reviewed and authorized, pass its printed digest and the retained owner authorization to `preflight/make_schedule.py freeze --draft-sha256 … --authorization …`. Run `coordination/dispatch.py --check-only` with the apparatus and harness arguments before any separately authorized `--authorize-live` launch. Do not reuse a partially dispatched apparatus. The inner endpoint stays at the target's accepted carry-forward; grading requires its completed Improve receipt and refuses accepted work past that endpoint.

The public checks run in an isolated replay of the retained export and its Git context. The private runtime probes use a separate Git-free tree. A missing or altered context, unsafe export, or failed lifecycle verification makes the observation incomplete. Once owned processes have ended, normal cleanup and recovery remove the trial's `home/.codex/auth.json` symlink and record its status without inspecting the target. An absent link is fine; an unexpected entry or parent makes cleanup incomplete. Recovery still cannot verify a forced observation. The history scanner's synthetic committed/deleted markers qualify only the declared reachable-blob scan. Live historical disclosure remains unmeasured, and usage totals are complete only when all admitted launches and both parent streams agree. A native boundary stop can leave usage incomplete. An independently authorized optional `v7/collector_smoke.py` runs one naturally ending parent turn in its own directory when collector verification needs that evidence; it uses the same link cleanup and does not resume or extend the subject run.

Run `analysis/grade.py --evidence "$V7_APPARATUS" --output "$NEW_GRADE_DIR"` for retained dispatch evidence, then `analysis/decision.py "$NEW_GRADE_DIR/observations.json" --evidence "$V7_APPARATUS"`. A valid smoke returns `SMOKE_NONCOMPARATIVE`; it can never promote a candidate. `judgment/build.py --evidence "$V7_APPARATUS" --grades "$NEW_GRADE_DIR" --output "$NEW_MASKED_DIR"` publishes one owner-only report tree with masked checks and separate private provenance. Keep grade, masked and optional collector outputs fresh and outside apparatus inputs.
