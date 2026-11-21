## On the starting project

Ran all 41 manifest commands on Node.js 26.12.1. They selected 53 tests, and the slowest command took 2.69 seconds.

### Existing clauses whose tests failed

none

### Other clauses whose tests passed

- C-8. The existing unknown-field validation already rejects `due` on all three write routes.
- C-11. Both the starting checkout and the extracted 1.4.0 reference produce the same off-mode status codes and bodies, including on files containing a `due` field.
- C-28. The 1.4.0 reader can read every ticket written by the starting checkout because that writer still uses version 1. U-5 additionally checks for saved deadlines before the rollback and fails on the baseline.
- C-33. The original checked-in test files are unchanged and their cases pass under `npm test`.

C-5 verifies the legacy startup error contract on the baseline. Its response-hours checks run when the service exposes the feature. All seven use cases fail on the baseline at the absent preparation, deadlines, overdue eligibility, or new `npm test` cases.

## Assumed

- `72d9828` is the local 1.4.0 reference when the plan's `ada051d` object is missing. The archive identifies itself as 1.4.0 and contains the pristine source and tests.
- A Node preload supplies deterministic wall time to `npm start` without importing the product's internal `manualClock`. For the default-port checks it records the requested port and lets the operating system bind port 0.
- The local POSIX runner honors directory and file permissions and a child-process file-size limit. These faults simulate a blocked save and an interrupted write without depending on a temporary file name.
- C-34 observes individual `node:test` cases from `npm test` and looks for evidence of due-time coverage in the added suite. The coverage evidence is a proxy for the substance of the added assertions.

## Discoveries

- Legacy production creation timestamps can include a nonzero UTC offset. Preparation should use that instant without rewriting the saved creation string. | Observable: A version-1 row created at `2025-09-01T01:15:00-07:00` starts successfully under 1.4.0 and has the same creation instant as `2025-09-01T08:15:00.000Z`. | Why: The legacy loader accepts the offset form even though HTTP-created tickets use UTC `Z` timestamps.
- A graceful 1.4.0 stop rewrites its version-1 data file even when clients make no ticket changes. | Observable: Start the old release on a file containing `due`, perform reads only, send SIGTERM, and inspect the file. | Why: The rollback read is successful, then the old shutdown save drops fields outside the old writer’s schema.
- A failed persistent create can affect live state in 1.4.0 even when its saved file is intact. | Observable: Block writes to `DATA_FILE`, POST a ticket, and compare a fresh listing with the retained file after the failed response. | Why: The baseline exposes the failed creation in memory while the data file still contains only the previous state.
- With positive response hours, the lower Node Date endpoint can be a creation instant. The earliest possible deadline for that creation is later than the endpoint. | Observable: Start the clock at the lower endpoint and create an urgent ticket. Its valid result is four hours later. | Why: Testing an assigned deadline exactly at the lower endpoint would require a duration outside the required positive-hours case.
