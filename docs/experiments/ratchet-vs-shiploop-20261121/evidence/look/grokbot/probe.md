# Try a review's findings on every build of the request

`/Users/dadleet/e2e-runs/d20261122-360a9f/look/grokbot/unmatched.json` lists shortfalls a reviewer reported for one product built from the request `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/request.md`, each with
the reviewer's steps. Three products built from that request by different builders are in `/Users/dadleet/e2e-runs/d20261122-360a9f/deep/grokbot/products` under code
names: `pae93f0`, `p8e1ce4`, `pe77982`. The reviewer saw the one named `pae93f0`. Their internals differ; carry the steps out through
each product's own interface (adapt a port, a file name, a start command or page markup, never what is being
tested). Where a step needs the page, drive it with Playwright from a Node script: `const { chromium } = require('/Users/dadleet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')` and `chromium.launch({ executablePath: '/Users/dadleet/Library/Caches/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-mac-arm64/chrome-headless-shell' })`.

For each shortfall and each product, run the steps yourself and record `present` (the product falls short as
described), `absent` (it behaves as the reviewer says it should), `not-applicable` or `could-not-run`, with what you
observed. Copy each product once to your own work folder `/Users/dadleet/e2e-runs/d20261122-360a9f/look/grokbot/probe-work/<code>` and run everything there, on free ports
you pick and data files inside your work folder. Stop every process you start, by its process id; never stop
processes by name. Edit nothing outside `/Users/dadleet/e2e-runs/d20261122-360a9f/look/grokbot/probe-work`.

Write `/Users/dadleet/e2e-runs/d20261122-360a9f/look/grokbot/probed.json` as one JSON object and nothing else:

```json
{"probed": [{"n": 1, "results": {"<code>": {"result": "present", "observed": "..."}}}]}
```

Reply with, a product, the count present.
