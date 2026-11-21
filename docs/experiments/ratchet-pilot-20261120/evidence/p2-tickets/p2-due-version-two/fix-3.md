# Fix 3

## Fixed

The full gate passed 246 of 253 acceptance checks. The project and syntax checks passed, and a separate `npm test` run passed all 122 tests. No product changes were warranted by the seven failures. Each check exits during fixture setup because the checkout lacks the authentic 1.4.0 Git object `22f8405`.

- C-22 stops at `git archive` before comparing disabled-mode health, outbox, audit, and error responses with 1.4.0.
- C-67 stops at `git archive` before launching 1.4.0 on the file prepared and saved by the new release.
- C-68 stops at `git archive` before 1.4.0 can list and read the saved tickets.
- C-70 stops at `git archive` before 1.4.0 can allocate from the saved ticket sequence.
- C-124 stops at `git archive` before 1.4.0 can issue the cursor to reuse in disabled mode.
- C-233 stops at `git ls-tree` before comparing existing tests with their 1.4.0 sources. The local comparison against the incoming snapshot shows only the addition of `test/due.test.js`.
- U-11 stops at `git archive` before 1.4.0 can take ownership of the file, save further work, and hand it back for deadline recovery.

The exit is unsatisfied and continuation is blocked. The historical comparisons require the authentic 1.4.0 object in the checkout.

## Disputed

None. The checks match the specification, as recorded in `ratchet/referee-1.md`.

## Discoveries

- The seven checks share a fixture dependency outside the service | Observable: six focused checks receive Git exit 128 from `git archive`, and C-233 receives it from `git ls-tree`, all naming `22f8405` | Why: setup must retrieve the original release before making the historical assertions.
- The incoming snapshot cannot supply the rollback fixture | Observable: `git show 14feaa0:package.json` reports 1.4.0, and `git show 14feaa0:src/persistence.js` shows that it already writes file version 2 | Why: the genuine 1.4.0 rollback check requires the release that reads version 1 and predates the due-time changes.
- The gate summary counts failed use cases under “Other checks failing” | Observable: the gate prints one other failure and lists only the seven acceptance failures | Why: the summary counts every failing ID without the `C-` prefix, including `U-11`.
