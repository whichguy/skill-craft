# Try a review's findings on every build of the request

`/Users/dadleet/e2e-runs/d20261122-360a9f/look/expenses/unmatched.json` lists shortfalls a reviewer reported for one product built from the request `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/expenses/request.md`, each with
the reviewer's steps. Three products built from that request by different builders are in `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/expenses/products` under code
names: `p8284f5`, `p720d2a`, `p23566f`. The reviewer saw the one named `p8284f5`. Their internals differ; carry the steps out through
each product's own interface (adapt a port, a file name, a start command or page markup, never what is being
tested).

For each shortfall and each product, run the steps yourself and record `present` (the product falls short as
described), `absent` (it behaves as the reviewer says it should), `not-applicable` or `could-not-run`, with what you
observed. Copy each product once to your own work folder `/Users/dadleet/e2e-runs/d20261122-360a9f/look/expenses/probe-work/<code>` and run everything there, on free ports
you pick and data files inside your work folder. Stop every process you start, by its process id; never stop
processes by name. Edit nothing outside `/Users/dadleet/e2e-runs/d20261122-360a9f/look/expenses/probe-work`.

Write `/Users/dadleet/e2e-runs/d20261122-360a9f/look/expenses/probed.json` as one JSON object and nothing else:

```json
{"probed": [{"n": 1, "results": {"<code>": {"result": "present", "observed": "..."}}}]}
```

Reply with, a product, the count present.
