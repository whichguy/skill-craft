## Fixed

None. Both reported failures stop at fixture setup before the preceding release can try to read the saved file. The current persistence code still writes the additive version 1 format.

## Disputed

- C-135 | the test expects: the gate environment supplies `RATCHET_PREVIOUS_RELEASE_DIR` pointing to an authentic pre-assignment checkout | the clause says: the previous release reads the saved version 1 file and serves its original ticket fields, audit history and outbox | the fixture variable is unset and the checkout is unavailable in the workspace, so the test aborts before it checks file compatibility.
- U-15 | the test expects: the gate environment supplies `RATCHET_PREVIOUS_RELEASE_DIR` pointing to the preceding executable | the clause says: an operator can roll back by running the preceding executable on the current version 1 data file, with a backup for assignment state | the executable is unavailable in the workspace, so the test never reaches the old release's read, edit or save.

## Discoveries

- Rollback verification requires an authentic pre-assignment executable supplied to the acceptance runner | Observable: Both focused commands fail at `startPreviousRelease` with the fixture variable unset, and the earliest local commit (`137198a`) already persists `assignee` | Why: The corrected fixture lookup replaced the missing Git revision, but the gate environment still lacks the executable needed to exercise rollback.
