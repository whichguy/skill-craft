# Re-run what the audits disagree on, and try each reported defect on every product

Several products were built from one request (`/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/request.md`) by different builders and audited one at a
time. The products are in `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/products/` under code names: `pae93f0`, `p8e1ce4`, `pe77982`. Their internals differ; a probe or a
reproduction is given in terms of the product's interface and may need the obvious adaptation (a different port,
file name or start command), never a change of what is being tested.

`/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/defects-reported.json` holds two lists.

**`recheck`**: inventory items (`/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/inventory.md`) on which the audits gave the products different grades.
For each, run the item's probe on every product yourself, the same steps and inputs for each, and grade what you
see: a stated item `yes`, `partly`, `no` or `wrong`; an unstated item `sound`, `acceptable`, `poor`, `unhandled`
or `not-applicable`, where any outcome the inventory lists as acceptable is acceptable. Your grade replaces the
audits' for these items, so do not copy theirs: run it.

**`defects`**: defects auditors reported, each for one product (`from`), with a reproduction.

1. Merge entries that describe the same defect (the same behaviour, whichever product it was reported for).
2. For each merged defect, run the reproduction on every product, the product it was reported for included, and
   record `present` (the defect shows), `absent` (the product behaves as `expected`), `not-applicable` (the product
   has no such feature) or `could-not-run`. Keep the highest severity among merged entries, and lower it only if
   what you observe is plainly less than the auditor claimed (say so in `note`).

Rules: copy each product once to your own work folder `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/work/probe/<code>` and run everything there. Use free ports you
pick yourself and data files inside your work folder. Stop every process you start, by its process id; never stop
processes by name. Edit nothing outside `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/work/probe`. Every result needs what you observed.

Write `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/defects-probed.json` as one JSON object and nothing else:

```json
{"rechecks": [{"id": "U-3", "results": {"<code>": {"grade": "acceptable", "observed": "..."}}}],
 "defects": [{"id": "D-1", "title": "...", "severity": "high|medium|low", "merged_from": ["<code>#<n>"],
               "repro": "...", "expected": "...", "note": "",
               "results": {"<code>": {"result": "present", "observed": "..."}}}]}
```

Reply with the count of rechecked items, the count of merged defects and, a product, how many are present.
