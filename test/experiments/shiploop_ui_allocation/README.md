# ShipLoop UI allocation study apparatus

This directory holds the inputs, evidence reader and local browser capability control for the bounded study described in [the report](../../../docs/shiploop-ui-planning-allocation-2026-09-18.md). The report distinguishes each observed outcome from unexecuted work.

## Case inputs and limits

The retained [input record](fixtures/inputs.json) contains the original requests,
platform/API/design facts, probe source, predeclared semantic criteria and source
hashes. Existing UI code is the byte-matching sibling consumer pilot baseline;
the external frontend-design card is identified by digest, not redistributed.

The study uses a constrained static Field Notes fixture: `docs/design.md` preserves the account selector, note list, textarea, controls, keyboard/touch/narrow-layout behavior, and visual identity; `docs/platform.md` permits bundled same-origin assets and HTTPS APIs but no deployed server or WebSocket; `docs/api.md` defines the export-status API. `scripts/probe_environment.py` is a controlled current-host fact, not a deployed-host receipt.

Cold dependent and cold independent cases are deliberately seeded only through `step-plan`. Their prior producer and Improve records are synthetic navigation fixtures. Later producer and reviewer evaluations may be semantic and real, but those cold predecessors cannot establish that early planning or actual Improve happened.

The later controls test preparation ownership, headless scope, and read-only
status with progressively clarified contracts, and recovery from a superseded
global-plan note. Their [input records](fixtures/controls.json) retain the
predeclared requests and expectations. They are diagnostic cases, not
paired statistical evidence or replacements for earlier failures. The original
status control retains its missing host-authorization bridge; supplying that
contract in a new case does not prove a deployed account boundary.

The cold fixture context deliberately retains its original malformed heading fragments and product-root-relative document locators as a controlled confound. Do not repair those strings while comparing baseline and candidate cases.

## Published evidence

The [case summary](evidence/summary.json), [independent assessments](evidence/assessments)
and [manifest](evidence/manifest.json) retain bounded content copies of actual
case state, producer results, review receipts and plan notes. Machine-specific
roots are tokenized. The manifest records original and published SHA-256 values
separately; these copies are **not resumable runs or direct reader inputs**.
Raw transient work remains in the original isolated study. Transcript whitespace
and intentional Markdown line breaks are preserved; whitespace lint applies to
authored code and documentation, excluding these content copies. In-place plan edits
during Improve are described by the retained reviews; an original producer
result alone does not preserve every earlier byte of its referenced plan.

## Structural evidence reader

`evidence.py` reads a persisted `run/state.md` against the explicitly selected ShipLoop package. It executes that trusted local package's store and navigator validator; it is not a sandbox for untrusted packages. The reader itself does not mutate run state. It checks state shape and imported terminal-packet identities, separates synthetic predecessors from imported Improve records, and reports callback content as reported evidence only.

```sh
DEVELOPER_DIR=/Library/Developer/CommandLineTools \
python3 -B test/experiments/shiploop_ui_allocation/evidence.py \
  /absolute/path/to/case --package /absolute/path/to/selected/shiploop
```

`accepted_stage_record_count` counts ledger rows, including synthetic
predecessors; it is not a count of actual earlier producer executions.

It reports `structurally_valid` and `semantic_verification: false`, and returns exit status 2 for structurally invalid/missing evidence. Exit 0 can describe an active or synthetic-only case; it does not prove semantic judgment, product behavior, browser results, deployment, or remote environment.

## Browser capability control

`browser-capability-probe.cjs` is an opt-in loopback Chromium control. It requires an already installed Playwright module and browser executable; it never installs either and makes no remote request. Set both paths explicitly and use a new output directory:

```sh
PLAYWRIGHT_NODE_PATH=/absolute/path/to/node_modules/playwright \
BROWSER_EXECUTABLE_PATH=/absolute/path/to/chromium \
node test/experiments/shiploop_ui_allocation/browser-capability-probe.cjs \
  /absolute/path/to/new-browser-evidence
```

The fresh directory receives `report.json` and `constrained-host.png`. The three expected groups are `bundled-assets-and-inline-rejection`, `ordinary-origin-storage-reload`, and `renders-but-persistence-blocked`. They show controlled loopback CSP/sandbox behavior only, not a native host or deployment capability.

Run a syntax check without launching a browser:

```sh
node --check test/experiments/shiploop_ui_allocation/browser-capability-probe.cjs
```
