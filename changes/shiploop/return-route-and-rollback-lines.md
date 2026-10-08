---
bump: minor
---
Every isolated-run packet now states how the return will go, taken from `workspace.md` (replacing a generic sentence that was wrong for a clean start), the release-plan and release-check packets print tested rollback recipes for each return kind, and `review-return` reports the expected return once nothing is undecided, by the same rule `return` follows. The release-plan and release-check duties tell the model to write and verify the rollback against that route.
