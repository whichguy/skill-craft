# Referee rulings

| Dispute | Ruling | Reason |
| --- | --- | --- |
| C-135 | test stands | The Observable requires the previous release to open a copy of the saved version 1 file and serve the original ticket fields, audit history and outbox through its original endpoints. The test stops the assignment release, copies its saved file and makes those requests against the previous release. `RATCHET_PREVIOUS_RELEASE_DIR` tells the test where to find that executable. |
| U-15 | test stands | The flow requires an operator to keep a backup, check pending assignment notices and run the preceding executable on the version 1 file. The test performs those steps and triggers a save with a ticket edit to verify that the preceding writer drops the assignee and that the backup preserves it. |

Both acceptance commands stopped at fixture setup because `RATCHET_PREVIOUS_RELEASE_DIR` was unset. The earliest local commit already includes assignment, and no pre-assignment executable was found in the workspace. Compatibility and rollback remain unverified.
