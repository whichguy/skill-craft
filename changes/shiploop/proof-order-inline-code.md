---
bump: patch
---
Step-plan's proof-order refusal also reads the test files named inside a Proof's inline code (`node -e`, `python3 -c`): a Proof
whose code runs a test the item base lacks and no earlier step declares is refused with rule A's words, as the same path in
the command's own words already was. Such a Proof cannot pass at its implement's done, because the test stage writes the test
afterwards. Absolute and home paths, URLs (a local server's port included) and scratch scripts inside the code are not read
as repository files; a quoted command string's relative test path is.
