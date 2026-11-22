# Audit one product against a request

You are auditing a product a builder delivered for a customer's request. Your audit will be compared with audits
of other deliveries of the same request, each made with these same instructions, so be exact and observe before
you assert.

- The request: `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/request.md`
- The files the builder started from: `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/base/`
- The inventory, the items to check: `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/inventory.md` (stated requirements S-n, and conditions the request
  leaves unsaid U-n, each with a probe and the outcomes that would be acceptable)
- The product: `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/products/pe77982`. Its builders' specification is `ratchet/spec.md` inside it; other working notes of theirs may sit beside it.

## Rules

1. Work only in your own copy: copy the product to `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/work/pe77982-share3` first and run everything there. Change no other
   folder. Never edit the original.
2. Use a free port you pick yourself and data files inside your work folder. Stop every process you start, by its
   process id, before you finish; never stop processes by name.
3. `observed` is true only when you ran something and saw the result. Reading the code is `observed: false`.
4. Judge the product against the request and the inventory, not against your taste. Any outcome the inventory
   lists as acceptable is acceptable. A choice the request leaves open is not a defect unless it loses data,
   misleads a user or breaks something that worked.
5. Size is not quality. Do not credit a product for the length of its documents or the number of its tests, and
   do not hold either against it: only what they do counts.

## Part 1: behaviour. Do this before you open the product's tests or its builders' specification.

Start the product and try every inventory item for real, with the item's probe (adapt a port, a file name or a
start command, never what is being tested). Record the command you ran and what came back.

For each stated item, `built`: `yes`, `partly`, `no` (missing) or `wrong` (present and incorrect).

For each unstated item, `behaviour` (what the product does there, as observed) and `handling`: `sound`,
`acceptable`, `poor` (works against the user or loses something), `unhandled` (crashes, hangs, corrupts, or the
product has no behaviour there) or `not-applicable`.

Then up to 12 probes of your own choosing beyond the inventory, aimed at ordinary use and at the edges of
what was asked. List every one in `explored` with what came back, including those that found nothing. A defect
needs an exact reproduction another person can run on a fresh copy of any build of this request: the commands in
terms of the product's interface (HTTP requests, commands, function calls), what comes back, what should have.
`severity`: `high` loses data, gives a wrong result on an ordinary use, or breaks what worked before; `medium` is
wrong on an unusual but plausible use; `low` otherwise.

Do not change a Part 1 grade because of anything you read in Part 2 or Part 3.

## Part 2: tests

Run the product's own tests and record the command and its result. Then, for each stated and unstated item,
`test`: `strong` when a test in the suite would fail if this item broke (name it in `test_name`), `weak` when a
test touches it but would not notice most breakages, `none`.

For these stated items the claim must be proved: S-5, S-31, S-33, S-67, S-72, S-88. For each one, break that behaviour in your copy with the
smallest edit to the product's code that makes the item's probe fail, run the suite, record in `proved` whether it
`fails` (name the failing test) or `passes`, then undo the edit and confirm the suite is back to its first result.
`could-not-break` if the item is not built.

## Part 3: specification and documents

- For each stated item, `spec`: does the builders' specification state it: `stated`, `absent`, `contradicted`, or
  `none` when the product has no specification.
- For each unstated item, `spec`: `open` (marked for the customer to decide), `decided-marked` (decided and marked
  as the builder's own choice or assumption), `decided-unmarked` (decided in an ordinary requirement line),
  `silent`, or `none`.
- For each unstated item, `told`: would a customer who reads the documents delivered with the product (README, API
  or operations documents, a changelog or delivery note; not the builders' specification or working notes) find
  an accurate account of what the product does there: `yes` (say where in `told_where`) or `no`.
- `extras`: things built that the request did not ask for, each `value`, `neutral` or `liability`, with why.
- `spec_notes`: where the specification contradicts the request, decides something without saying so, or pins a
  choice a correct product need not share. `none` if there is no specification.
- `tests_notes`: tests that cover several behaviours at once; tests tied to internals (file names, private
  functions, timing); tests that would fail on another correct build of this request.
- `maintainer`: what the next person would find hardest to change safely, in two or three sentences.

Write your audit to `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/audits/pe77982.share3.json` as one JSON object and nothing else in the file:

```json
{"code": "pe77982",
 "ran": {"tests_command": "...", "tests_result": "...", "started_with": "..."},
 "stated": [{"id": "S-1", "built": "yes", "observed": true, "evidence": "command and what came back", "spec": "stated", "test": "strong", "test_name": "...", "proved": "fails|passes|could-not-break|not-asked", "proved_by": "the edit, and the test that failed"}],
 "unstated": [{"id": "U-1", "behaviour": "...", "handling": "sound", "observed": true, "evidence": "...", "spec": "silent", "told": "no", "told_where": "", "test": "none"}],
 "explored": [{"probe": "...", "came_back": "...", "finding": "none|defect"}],
 "defects": [{"title": "...", "severity": "medium", "repro": "...", "observed": "...", "expected": "...", "basis": "stated|unstated|other", "item": "S-3 or U-2 or empty"}],
 "extras": [{"what": "...", "where": "...", "worth": "neutral", "why": "..."}],
 "spec_notes": "...", "tests_notes": "...", "maintainer": "..."}
```

Every inventory item must appear once. When the file is written and every process you started is stopped, reply
with three lines only: the tests' result, the count of stated items not `yes`, the count of defects.


## Your share of this audit

This inventory is long, so the audit of this product is shared between 3 auditors who work separately, each
with these same instructions. Your share is these items and no others: U-1, U-2, U-3, U-5, U-6, U-7, U-8, U-9, U-11, U-13, U-14, U-15, U-16, U-17, U-20, U-21, U-22, U-23, U-25, U-26, U-27, U-29, U-30, U-31, U-32, U-33, U-34, U-35, U-36, U-37, U-38, U-39, U-40, U-41, U-42, U-43, U-44, U-45, U-46, U-49, U-50, U-54, U-57, U-58, U-60.

- Do Parts 1, 2 and 3 for your items only. The `stated` and `unstated` arrays of your file hold your items only,
  each once. This replaces "every inventory item must appear once".
- In Part 2, the items of yours whose test must be proved by breaking the behaviour: none.
- You also make the probes of your own choosing and write `extras`, `spec_notes`, `tests_notes` and `maintainer`.
- Where an item needs the page in a browser, drive it for real with Playwright from a Node script:
  `const { chromium } = require('/Users/dadleet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')` and `chromium.launch({ executablePath: '/Users/dadleet/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell' })`
  (headless). Close every browser you open.
