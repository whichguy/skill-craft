# Referee rulings

| Dispute | Ruling | Reason |
| --- | --- | --- |
| C-135 | test corrected | The Observable calls for the previous service to read tickets, history and outbox from a copy of the saved version 1 file. The test now launches a supplied previous-release checkout via `RATCHET_PREVIOUS_RELEASE_DIR` and keeps the endpoint assertions. The absent Git revision `22f8405` was a fixture lookup. |
| C-184 | test corrected | The Observable requires the original tests to pass as written. The test checks their file digests against the local base and verifies that their cases pass in `npm test`. The baseline excludes `test/assignment.test.js`, which is assignment coverage already present in the local base. |
| C-185 | test corrected | The Observable requires `npm test` to discover assignment coverage alongside the original suite. The test finds new `node:test` files under `test/` using the frozen file list, checks the specified coverage areas and verifies that the original and new cases appear in the same run. |
| C-186 | test corrected | The Observable concerns a free port and a disabled worker for queued-state assertions, with an exception for delivery. The test inspects the assignment coverage discovered from `test/` and checks the shared `withService` defaults of port `0` and worker interval `0`. |
| U-15 | test corrected | The flow requires the preceding executable. The test checks the backup and pending notices, runs the supplied previous release on a copy and explicitly edits a ticket to trigger a save. It checks that the save drops the assignee and that the backup retains it. |
| U-16 | test corrected | The flow requires one `npm test` run on Node.js 22 or later with no dependencies. The test confirms that unchanged original cases and new assignment cases passed in the same run using their reported names. |

## Verification

`npm test` passed all 125 tests. The acceptance commands for C-184, C-185, C-186 and U-16 passed. The command entries in `ratchet/acceptance.json` still apply.

The local base, `137198a`, already contains the assignment route and persists assignees. The pre-assignment executable is absent from this checkout. C-135 and U-15 reached the missing-fixture assertion after preparing the saved file. Both also rejected the assignment-enabled checkout when it was supplied as the fixture. End-to-end rollback verification requires `RATCHET_PREVIOUS_RELEASE_DIR` to point to an authentic checkout of the preceding release containing `src/server.js`.
