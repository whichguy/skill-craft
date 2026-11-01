# Offline ticket semantic probe

`ticket_semantics.py` compares the base suite, explicitly selected original tests, and two focused behavior probes against disposable ticket-source copies:

- A same-agent reassignment remains a no-op after the injected manual clock advances.
- A real assignment is already present in `DATA_FILE` before graceful cleanup begins.

The runner seeds one fault per probe in its copy. The clock fault refreshes `updated` only for an empty `ticket.assigned` action. The persistence fault skips the assignment save; graceful cleanup still saves the in-memory snapshot. The correct source and an optional alternative reference are controls.

## Inputs and command

Run from the monorepo root. Supply separate source directories for the clock and persistence cases, and name every test file explicitly. The runner does not discover or glob test files. Use a new output directory for each registered attempt. `--node` can pin the executable path; the resolved path and version, Python version, exact commands, working directories, and source identities are recorded.

For the current 17-file base catalog and retained six-test original suites, use this command shape and replace the source paths and output directory with the intended inputs:

```sh
python3 -B test/shiploop_e2e/probes/ticket_semantics.py \
  --node /path/to/node \
  --clock-source /path/to/clock-source \
  --clock-base-tests \
    test/api.test.js test/audit.test.js test/config.test.js test/errors.test.js \
    test/http.test.js test/ids.test.js test/notifier.test.js test/outbox.test.js \
    test/pagination.test.js test/persistence.test.js test/query.test.js test/router.test.js \
    test/service.test.js test/states.test.js test/store.test.js test/validate.test.js \
    test/worker.test.js \
  --clock-original-tests test/assignment.test.js test/system-assignment.test.js \
  --persistence-source /path/to/persistence-source \
  --persistence-base-tests \
    test/api.test.js test/audit.test.js test/config.test.js test/errors.test.js \
    test/http.test.js test/ids.test.js test/notifier.test.js test/outbox.test.js \
    test/pagination.test.js test/persistence.test.js test/query.test.js test/router.test.js \
    test/service.test.js test/states.test.js test/store.test.js test/validate.test.js \
    test/worker.test.js \
  --persistence-original-tests test/assignment-contract.test.js \
  --reference-source /path/to/alternative-reference \
  --expected-base-count 116 \
  --expected-clock-original-count 6 \
  --expected-persistence-original-count 6 \
  --clock-repetitions 3 \
  --output /path/to/new/evidence-directory
```

The run protocol with declared predictions is written before Node tests start. The runner refuses an existing output directory. It records one attempt for each declared condition; the three clock repetitions are calibration repetitions, not retries. There are no sleeps: the clock probe advances its manual clock by exactly one second.

## Reading results

Only a complete TAP report with the declared count, no skips or todo tests, consistent pass/fail totals, and a matching process exit code is classified as a valid `PASS` or `FAIL`. Setup errors, timeouts, missing or inconsistent TAP, count mismatches, source changes, and unexpected outcomes remain `UNKNOWN`/incomplete. They do not count as test detection. The original source identities must match before and after execution; each arm must report its own absolute working directory.

The results record each suite separately, including the base suite and original tests, along with runtime and output bytes. A failing behavioral probe only demonstrates that assertion against that specific fault and source copy. It does not establish a general gap across generated tests: other completed workflow suites may already cover the same behavior. This offline probe does not alter a live scorecard or acceptance floor, and does not qualify a product change. Model calls and live runs are zero.

## Narrow verification

```sh
python3 -B test/shiploop-e2e-ticket-semantics.test.py
```
