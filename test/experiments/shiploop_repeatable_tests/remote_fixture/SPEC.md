# Remote test-authoring contract

Build a retained Apps Script server-side test suite using the supported CommonJS module contract in PLATFORM.md. This is a disposable, project-local test pilot. Do not connect to a remote service during authoring.

The product behavior to test is an integer-cent `totalCents(quantity,unitCents)` function: both arguments are nonnegative integers excluding booleans; reject invalid inputs; return their product. Implement this tiny fixture function in its own module and tests in `common-js/remote-repeatable-tests.gs`. Test independent exact results and errors.

Also test project-local ScriptProperties using names beginning with a unique suite-owned prefix. Support selecting stable test IDs, a useful smoke selection, full selection, and explicit reordered selection. Include stateful cases and controlled setup/assertion-failure injections, demonstrating cleanup and accurate failure reporting. Isolate normal full-suite cases from deliberate negative-control invocations. Preserve unrelated properties. The suite must report selected/executed IDs, pass/fail/blocked counts, and cleanup observations. Unknown IDs must be rejected explicitly.

Expose `runRepeatableTests(selection)` with selection as an object or a documented string/array form. Expose a read-only `inspectOwnedState()` for checking that no suite-owned property remains after a failed or interrupted invocation. Include a stable test-definition revision marker in results; external receipts will bind it to actual uploaded file hashes. Do not pretend a caller-supplied digest proves code identity.

Retain a local Node-based harness that can exercise logic and cleanup using a minimal ScriptProperties fake; label it as local simulation only. Retain exact remote commands and prerequisites. A local pass cannot establish remote execution. No mail, documents, triggers, account/config changes, new dependencies or remote creation.
