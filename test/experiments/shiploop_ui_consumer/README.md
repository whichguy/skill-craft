# Incremental UI consumer pilot

This opt-in browser experiment checks an existing list/detail/editor while adding
async export status and safe note reconciliation. It accompanies ShipLoop's
component, interaction and branding guidance. It is a local static product with
a controlled service double, not a hosted backend or native application.

The fixed contract is in `SPEC.md`. `baseline/` retains the corrected prior UI;
`feature/` contains the incremental implementation. The harness uses actual
Chromium rendering and input, independent service request/effect assertions,
explicit response-order barriers, and normal/reduced-motion observations.

## Run

Supply an already available Playwright module and Chromium executable through
`PLAYWRIGHT_NODE_PATH` and `BROWSER_EXECUTABLE_PATH`. The harness does not install
dependencies. From this directory, use new output directories for each run:

```sh
node harness/browser-tests.cjs --mode baseline --product baseline \
  --output /tmp/field-notes-baseline-run
node harness/browser-tests.cjs --mode full --product feature \
  --baseline-report /tmp/field-notes-baseline-run/report.json \
  --output /tmp/field-notes-feature-run
```

Focused checks select case IDs, for example `--case P3,P6`. A smoke selection is
`--case P1,P2,P5`; `--mode full` is the complete consumer suite. These checks are
not part of the repository's hermetic aggregate because they require a real
browser. Each case uses isolated mutable service state and a fresh browser
context, with cleanup even when assertions fail. Output directories are never
overwritten; nonzero exit means failure or missing prerequisites.

## Evidence boundaries

P1 checks preserved journeys, labels, tokens and type before and after the
feature. P2–P8 cover dirty editors, reversed responses, conflict reapply,
ambiguous saves, identity changes, interrupted motion, and resume/recovery.
X1 covers a newer draft typed while an earlier save is pending. Reports record
the served-source and harness digests, browser version, case results, service
requests and observations. Screenshots establish visual states only.

Where the browser cannot generate a real hidden/visible transition, the harness
labels its visibility injection as synthetic. Clock-controlled polling checks
are labeled separately. ARIA checks do not establish screen-reader usability;
this fixture does not establish native suspension, remote delivery or deployment.

Browser reruns do not execute an LLM or Improve. The accompanying results report
separately records the actual planning producer, selected Improve child and
once-only parent import from the original bounded pilot. Earlier navigation was
explicitly synthetic; it was not a full ShipLoop delivery run.

The [results report](../../../docs/shiploop-ui-consumer-results-2026-09-17.md)
records the original observations. `evidence/manifest.json` binds content-only result copies and their original
digests. Machine-local roots are tokenized; screenshots and full runtime logs
remain outside the package. Run the commands above to generate current evidence.
