# document notes, W1/S1 (Basket)

Changed public behaviour (from src/basket.js, test/basket.test.js, the step plan and implement-S1): `new Basket({limit})`
validation, `add(item)`, the public `items` and `limit` properties. Each was run with scratch/observe.js; the README
example was run literally with scratch/readme-example.js (exit 0).

Documented where
- src/basket.js: contract docstrings on the class, constructor and add (inputs, returns, errors, test IDs); the two
  line-narrating comments were removed; one tombstone at `return this.items.length` (the drifting counter, AD-3).
  `grep -c '/**' src/basket.js` = 3 (criterion C3).
- README.md: module bullet, a `## Basket` example with expected results, the `items` caveat, links to spec.md and the tests.
- docs/shiploop/spec.md: one marked (W1/S1) line each in R-1, R-2, R-3 (additions only).
- docs/shiploop/architecture.md: AD-2 (TypeError for 0 and negatives, the departure from the Conventions) and AD-3 (count is items.length).
- docs/shiploop/environment.md: single-file and by-ID test commands, platform seen.

No documentation needed, and why
- Operator, deployment and diagnostics docs: the module has no logging, configuration, I/O or service, so there is nothing to turn on or operate.
- Error docs beyond the docstrings: both errors are thrown in-process with fixed messages, observed and recorded in the docstrings and spec.
- Baseline (recovered existing behaviour): none; src/basket.js is new, so there is no prior as-of baseline to keep apart.
- docs/shiploop/architecture.md Conventions and Structure: unchanged; Basket follows src/<concept>.js and test/<concept>.test.js, and its one
  departure is recorded as AD-2 rather than by editing the Convention.

Observed details worth keeping
- `new Basket(null)` is a TypeError too, but with the engine's destructuring message, not `limit must be a positive integer` (docstring says so).
- Pushing into `basket.items` directly exceeds `limit`; the next `add` then throws RangeError, because the check is `items.length >= limit`. Documented as a caveat in the class docstring and README; not changed (no requirement asks for encapsulation, and TC-1/TC-4 read `items.length`).
- Every example that can run here was run. None was left unverified.

Reruns after the last edit: `node --test test/basket.test.js` exit 0 (4 pass), `npm test` exit 0 (11 pass).
