# Native setup recovery fixture

This diagnostic asks whether an existing ShipLoop test-stage loop can repair stale, explicitly authorized local setup while preserving its acceptance obligations. It adds no production phase, loop limit or prompt change.

The frozen preparation target was configured through the public CLI. The continuation target keeps that historical audit and configuration but lacks its required receipt. A successful run must notice current readiness, use the permitted setup command outside its tests, separately probe and read back the resulting configuration and receipt, and execute every required journey. The owner-gated grant must remain unchanged.

## Calibrate before using the oracle

From the repository root, with a new output directory:

    python3 -B test/fixtures/native-setup-pilot/recovery/operator/recovery_calibrate.py --corpus-root test/fixtures/native-setup-pilot/recovery/corpus-v1 --input-manifest test/fixtures/native-setup-pilot/recovery/input-manifest.json --output-dir /tmp/recovery-calibration-unique

The expected result is 17 passing checks, including ten negative controls, with zero model or network calls. The wrapper in test/native-setup-pilot.test.py runs this calibration in a temporary directory. The controls distinguish stale setup, a no-op Save, forged state, altered CLI, omitted consumers, unauthorized effects, completion before setup and weakened tests. A denied operation may append one documented denial event; it may not alter protected state.

## Continue a native slice

Use the retained native_slice.py with a clean, explicitly pinned harness and a complete built plugin. First run cases-ready.json from test-strategy through implement. Export the actual accepted test-strategy, plan, prepare and step-plan records with operator/recovery_seed_records.py. Pass both --case-catalog corpus-v1/cases-stale.json and --output-catalog to that exporter. Its output catalog forwards the exact accepted work item at the frozen seed's second input seam; copying catalog metadata into the navigator plan can otherwise inject unsupported fields.

Then start a separate test-seeded continuation with that accepted record export, normalized stale catalog and --seed-from the preparation output. Preserve the original frozen catalogs and both attempts. The historical corpus README and reference test describe calibration inputs: a native subject must author its own acceptance tests.

After the subject stops, run operator/recovery_oracle.py with --corpus-root, --input-manifest, --product-root, --target and a fresh --output-dir. It independently checks six dimensions and replays the authored suite against copied ready and stale targets. Ready must pass; stale must fail without setup in the suite. Preserve source and original target hashes before and after. The oracle is for a trusted local fixture, not an adversarial security boundary or a substitute for semantic review of each requirement.

## Interpret the result

An in-scope defect or authorized setup repair can stay in the current Until Loop. Replan through the native send-back callback when scope, criteria, prerequisites or recorded commands need revision. A missing external grant remains blocked until its owner acts. Never delete, skip or relax tests just to finish.

A passing slice establishes this synthetic recovery only. It stops after the item at system-test-author; system tests, release and deployed application acceptance remain outside it. No real credentials, Salesforce orgs or external services are used by this retained fixture.
