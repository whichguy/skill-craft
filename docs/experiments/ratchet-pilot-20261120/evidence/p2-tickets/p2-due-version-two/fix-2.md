# Fix 2

## Fixed

The gate passed 246 of 253 acceptance checks, and `npm test` passed all 122 tests. This stage made no product changes. The seven remaining checks stop at a missing 1.4.0 baseline fixture. The current code cannot affect the Git commands that load it.

- C-22 stops while archiving `22f8405`, before comparing the disabled HTTP responses.
- C-67 stops while archiving `22f8405`, before starting 1.4.0 on the new release's data file.
- C-68 stops at the same archive, before 1.4.0 can page through or read the saved tickets.
- C-70 stops at the same archive, before 1.4.0 can allocate from the saved ticket sequence.
- C-124 stops while archiving `22f8405`, before 1.4.0 can issue a cursor for the new release to reuse.
- C-233 stops at `git ls-tree` on `22f8405`, before the historical source comparison. Every incoming test file matches the `14feaa0` snapshot, and `test/due.test.js` is the sole addition under `test/`.
- U-11 stops while archiving `22f8405`, before rollback and deadline recovery can be exercised with the original release.

Exit is unsatisfied and continuation is blocked. The seven checks require the authentic 1.4.0 Git object in the checkout.

## Disputed

None. The checks exercise the specified behavior and require the missing fixture to complete their comparisons.

## Discoveries

- The oldest available snapshot already contains due-time code despite its 1.4.0 package version | Observable: `git show 14feaa0:package.json` reports 1.4.0 and `git show 14feaa0:src/tickets/due.js` shows the implementation | Why: the snapshot can establish continuity of the incoming tests, while rollback requires the original release.
- The checkout has no configured Git remote and cannot resolve the historical fixture | Observable: `git remote -v` is empty, `git fsck --full --no-reflogs` reports no recoverable objects, and `git cat-file -t 22f8405` fails | Why: all seven historical checks depend on that object for setup.
