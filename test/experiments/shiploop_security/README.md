# ShipLoop security pilot harness, prospective V6

This opt-in apparatus builds a new private harness from the exact frozen V5 retry source. It needs Python 3, Git, and Node. It does not copy the old schedule, registration, prepared checkout state, candidate package, observations, results, or credentials. It does not start subjects. Keep the materialized tree and the private probes outside any subject checkout.

Run the no-model qualification with the **evidence directory** of the completed retry and an existing private report directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 test/experiments/shiploop_security/qualify.py \
  --frozen "$FROZEN_RETRY_EVIDENCE" --reports "$REPORTS"
```

This creates a fresh report and a temporary materialization. It checks the 73 earlier reference dispositions and 15 new controls, then retains calibration, synthetic grade and old-format rejection records. The synthetic records use real Git worktrees and the native exporter but contain no model responses. Run the standalone scope/materializer tests with `python3 -m unittest discover -s test/experiments/shiploop_security`.

For an operator who already has approval for a **separate** study, `materialize.py --frozen "$FROZEN_RETRY_EVIDENCE" --output "$NEW_PRIVATE_ROOT"` builds the private harness without running calibration or dispatch. Use a new directory whose parent exists. It checks the exact source path inventory, bytes, and modes before applying `v6.patch`; the zero-context hunks are checked against those pinned bytes. The output includes the prospective schedule generator, native operator, dispatcher, grader, and decision program.

Before any subject starts, prepare fresh public seed records at `operator/prepared-v3` using the materialized runner's `prepare` subcommand, generate `schedule.json` with `preflight/make_schedule.py`, and freeze the study as `shiploop-security-pilot/v2`. Keep the existing cohort and arm fields, update their paths and hashes, and register the new corpus with modes and the materialized `scope_evidence.py`, `logger_failure.cjs`, `analysis/grade.py`, and `analysis/decision.py` alongside the existing required sources. The dispatcher checks the registration digest and all listed identities before admitting a subject. Preserve the two scope receipts and both exported trees until independent grading is complete. The grader and decision program reject V1 inputs; never relabel old rows as V2.

The actual initial snapshot is taken after the native checkout and first render, before the first subject starts. Both endpoints use the native exporter's selection. Existing regular-file modes are compared in full; directory and symlink modes are outside this measurement. Mode drift between fixture and checkout is reported separately. Scope reports show root `SHIPLOOP.md` as changed documentation when applicable, and reject new links, skipped paths below a link, unrelated paths, and executable-bit increases. The diagnostic checks exercise the ordinary successful call and a separate throwing logger with synthetic message/cause markers; the retained report records booleans, and raw logger-error markers stay in transient captures. The outer probes test warm export, authorized update, then immediate same-process export, alongside foreign and denied operations. These checks calibrate the apparatus for the named cases. They do not measure a prompt improvement or provide a general security or isolation guarantee.
