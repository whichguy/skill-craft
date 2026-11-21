## Fixed

None. C-135 and U-15 each stop during fixture setup, before the preceding executable opens the saved data file. Rollback compatibility remains unverified.

## Disputed

none

## Discoveries

- The rollback checks require an authentic pre-assignment checkout supplied through `RATCHET_PREVIOUS_RELEASE_DIR` | Observable: Both focused checks abort with the fixture variable unset, and `git show 137198a:src/app.js` shows that the earliest local commit already registers the assignment endpoint | Why: The acceptance runner needs the preceding executable to verify that its original endpoints can read the saved file and that its writer drops the assignee on save.
