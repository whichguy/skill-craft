# Field Notes browser acceptance harness

This is an opt-in, disposable real-browser harness for the ShipLoop UI consumer
pilot. It serves a supplied static product directory under a restrictive
same-origin CSP and supplies deterministic account/note API behavior in the same
local HTTP process. It does not edit the product, install packages, call a remote
service, or make deployment, native-app, or assistive-technology claims.

Run the preserved baseline journey:

```sh
PLAYWRIGHT_NODE_PATH=/path/to/playwright \
BROWSER_EXECUTABLE_PATH=/path/to/chrome \
node browser-tests.cjs --mode baseline --product ../baseline --output artifacts/baseline-run
```

Run the full feature acceptance suite against a frozen feature product copy:

```sh
PLAYWRIGHT_NODE_PATH=/path/to/playwright \
BROWSER_EXECUTABLE_PATH=/path/to/chrome \
node browser-tests.cjs --mode full --product ../feature --output artifacts/feature-run
```

`PLAYWRIGHT_MODULE_PATH` is accepted as an alias for `PLAYWRIGHT_NODE_PATH`.
The browser executable can also be overridden with
`BROWSER_EXECUTABLE_PATH`. `--headed` (or `BROWSER_HEADLESS=false`) runs a
visible browser where that environment supports one.

Pass `--baseline-report /path/to/report.json` to a feature run to compare its P1
labels, accepted design tokens, and typography against a prior green baseline P1
observation. The report identifies the product digest and files that were actually
servable static inputs; review metadata such as `.git`, `.until-loop`, and Markdown
documents are excluded. It separately digests the three harness source files.

Each output directory contains `report.json`, including the exact static-product
digest, browser version, case result, controlled service requests, and screenshot
paths. Screenshots are visual state evidence only. `--output` must name a new
directory; the harness rejects an existing path so a failure report is never
overwritten by a later retry.

`baseline` runs P1, the preserved list/detail/editor journey. `full` runs P1–P8
and X1, the preregistered delayed-save check that proves a newer draft survives a
late first-save response. The service double commits a POST atomically before it
can truncate every confirmation for that scoped operation until an explicit
operation lookup arrives, tracks scoped operation IDs, supports conflicts,
scripted out-of-order GET responses, and operation lookup failures.

Use `--case P2` (or a comma-separated list such as `--case P2,P7`) for a narrow
diagnostic run. It is useful for preserving an expected RED result before a
feature exists; that result is not a substitute for the full post-feature run.

For P8, the harness first probes whether a two-tab Chromium context produces a
real `hidden` document. If it does not, it records and uses a test-only synthetic
`visibilitychange` injection; the report explicitly labels that result as a
synthetic visibility exercise rather than a browser lifecycle claim. The harness
never simulates a screen reader or a native application.

P8 also uses Playwright's clock emulation to check one visible approximately
15-second polling opportunity, a 45-second hidden pause, and a visible resume
refresh. That report entry is explicitly clock-emulation evidence, not elapsed
wall-clock or operating-system background behavior.
