# Readiness recovery corpus

Provider-free ShipLoop case copied from frozen source `c233c18acec66237534680695e8e5648a82f9511`.
The only product-code change expected is `offline_summary.py`; `readiness_cli.py` and
`contract.txt` remain byte-identical. Durable tests are owned by the test stage.

`state-ready/` was made by invoking the copied public CLI `setup sandbox` against a
copy of `state-pristine/` at the recorded timestamp in `source_identity.json`.
`state-stale/` is a copy of that real result with `sandbox-receipt.json` removed;
its configured sandbox record and original successful setup audit are retained. The
fixture documentation calls that evidence historical. A fresh probe is required.

`cases-ready.json` and `cases-stale.json` have the same case ID, task, fixture,
obligations, seed records, and expected paths. They differ only in
`seed_state.from`. Use the ready catalog for the first native slice and the stale
catalog for the resumed test slice. The test suite observes its supplied target and
never configures it. The workflow may use the explicitly authorized public setup
command before running the suite.

Run the fixed subject suite from the copied product fixture with
`python3 -B -m unittest -v test_acceptance`. The independent oracle and no-model
calibration live under `oracle/` and `operator/recovery_calibrate.py`; they inspect
the external target because case checks do not inherit `NATIVE_SETUP_TARGET`.
