# document, W1/S1 notes

- src/basket.js: comments only; behaviour untouched. Class, constructor and add now state their contract (constraint and error, return, unchanged-on-failure, the unguarded public `items`/`limit`). Two restating comments ("check the limit", "if the basket is full throw") deleted. Two one-line tombstones: TypeError for 0 and negatives (R-1, TC-2, AD-2) and the count is items.length, not a counter. No test pins the second tombstone (a separate counter would pass TC-3 and TC-4); it rests on the S1 implement probe (RUN/scratch/probe-count.js).
- test/basket.test.js: no docstring added. It is a test file; each test title states the behaviour and its TC ID, and the sibling test files carry no header either.
- README.md changed: module bullet plus a short Basket section. Its example was run (RUN/scratch/readme-example.js against WORKTREE); output matched the comments: 1, 2, RangeError "basket is full (limit 2)", TypeError "limit must be a positive integer".
- Not documented because not intended behaviour: `new Basket(null)` also throws a TypeError, but from the destructuring, with the engine's message, not the limit message. Observed, left out of the contract.
- Baseline (step 5): not applicable. The step adds a new module; no existing behaviour was recovered, so no as-of baseline or accepted delta to keep apart.
- Stale mentions: none listed; grep for "count" and the Basket names in README and docs found nothing stale.
- Lint: the repo has no linter configured; `node --check src/basket.js` passes. `grep -c '/\*\*' src/basket.js` is 3 (criterion C3).
- Reruns after the last edit: `node --test test/basket.test.js` 4 of 4 pass; `npm test` 11 of 11 pass, exit 0.
- spec.md R-3 given no line: it concerns the whole suite, and this step made no clause of it more precise.
