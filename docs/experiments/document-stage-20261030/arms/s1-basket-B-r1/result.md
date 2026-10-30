# ShipLoop navigator result

```shiploop-state
{
  "assumptions": [],
  "headline": "Basket's contracts are stated in src/basket.js, the README shows its use, and R-1, R-2 and AD-2 are recorded in the knowledge home.",
  "knowledge": {
    "architecture": "Added AD-2: Basket's constructor throws TypeError for every invalid limit, 0 and negatives included, departing from the Argument-errors convention because R-1 and the request say so; owner maintainer, revalidate when R-1 changes or a second class takes a size or range argument. AD-1 and the Structure and Conventions lines need no change.",
    "environment": "Added the focused command `node --test test/<concept>.test.js` with `--test-name-pattern=TC-<n>` to pick cases, run on test/basket.test.js; `npm test` and the harness line need no change.",
    "spec": "Added one line each inside R-1 (which invalid limits throw the TypeError; files and tests TC-1, TC-2) and R-2 (full means limit items, the RangeError leaves the basket unchanged, any item is accepted; TC-3, TC-4), both ending (W1/S1). R-3 needs no line: this step made no clause of it more precise."
  },
  "outcome": "done",
  "summary": "Comments only in src/basket.js, behaviour unchanged; README gained a module bullet and a Basket example that was run and matched. Known limit kept in the class docstring, not an open item: items and limit are public and unguarded, so direct writes can exceed limit (hardening them is unrequested). No test pins the 'count is items.length, not a counter' tombstone; a separate counter would still pass TC-3 and TC-4, so it rests on the S1 implement probe. new Basket(null) throws a TypeError from the destructuring, left out of the contract. No baseline work: nothing existing was recovered. Details in RUN/notes/document.md."
}
```
