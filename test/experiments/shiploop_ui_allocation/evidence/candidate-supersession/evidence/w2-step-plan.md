# W2 step plan — local static client and Node test bootstrap

## Scope and current authority

This is a plan only.  The current source-read-only diagnostic writes this
evidence and does not modify the product.  In a later authorized implementation
checkout, W2 will establish the smallest dependency-free local source/test
carrier for the retained Archive Register shell.  It will not implement export
behavior, call an API, add a package or framework, use a remote system, or make
a deployment claim.

The reviewed replacement at
`run/notes/global-plan-reviewed-replacement.md` is the current operational
order: W1 retained requirements/design basis, then W2 local bootstrap, then W3
integration contract.  The historical
`run/notes/global-plan.md` stays intact for audit.  W3 remains the later
supplier for API/target-owner decisions about collection/status/error shapes,
operation/retry/persistence, assets or packaging, target verification, and
consumer authority; none is a W2 bootstrap prerequisite.

The retained W1 basis is:

- `product/docs/requirements.md#Existing UI baseline` and
  `#Current W1 basis for this diagnostic`;
- `product/docs/design.md` component, interaction, and skin layers;
- `product/docs/platform.md` static-target constraints; and
- `product/docs/api.md` for the distinct W3 boundary.

## Revalidated starting point

The copied product has `index.html`, `styles.css`, and `app.js`, no package
manifest, and no test files.  The existing classic self-hosted script has one
local interaction: clicking `#inspect` changes the polite `#status` message.
It has no API call, incoming event, connection, durable state, or background
work.  The static target accepts same-origin external scripts and styles but no
server runtime, package installation, CDN asset, inline script/style, or
persistent socket.  Node is therefore a local authoring/test route only.

Baseline checks ran in `product/`:

| Command | Observed result | Raw output |
| --- | --- | --- |
| `node --check app.js` | exit 0; no stdout or stderr | `evidence/w2-baseline-node-check.stdout-stderr.txt` |
| `node --test` | exit 0; 0 tests, 0 pass, 0 fail | `evidence/w2-baseline-node-test.stdout-stderr.txt` |

The packet-named run-wide test-strategy result
`run/results/nav-9ba6f173d9a24ec5bd8ff3d2216e74f2.md` and prior Improve receipt
`run/improve/nav-00c18bd5c7384b29ac0f2552a4d56b7a/receipt.md` are absent.  Their
synthetic state labels therefore provide no reusable harness or passing-test
evidence.  The observed baseline commands above are the current W2 starting
evidence.

## Future authorized W2 implementation

1. Update `product/app.js` only enough to make the retained shell bootstrap
   testable without a dependency.  Define a small
   `bootstrapArchiveRegister(document)` initializer that locates
   `#status` and `#inspect`, attaches the existing click behavior, and
   preserves the existing status text.  Run it automatically only in the
   browser document; expose that initializer to Node through a guarded
   CommonJS export so requiring the file does not need a DOM, a build step, or
   a package manifest.
2. Give a missing required shell selector an immediate, concise bootstrap error
   that names the missing selector.  This is a local diagnostic boundary, not a
   new UI state or feature.  There is no existing debug control to extend, so
   W2 adds no logger or diagnostics framework.  Each test owns a fresh fake
   document/elements; no teardown or persistent cleanup is required.
3. Add `product/test/app.test.js` using only `node:test` and
   `node:assert/strict`.  Its fake document/elements will provide a meaningful
   Node oracle for:
   - loading the guarded module without a browser global;
   - wiring the retained inspect click to the exact retained status message; and
   - rejecting a missing required shell element with the planned diagnostic.
4. Update `product/README.md` in that later authorized checkout to replace the
   current zero-test statement with the focused and full Node commands below,
   explicitly limiting their meaning to local bootstrap verification.  It must
   not describe them as API, target, deployment, or consumer verification.

The retained `product/index.html` and `product/styles.css` are preservation
references, not W2 redesign targets.  The implementation must keep the concise
record-status message, native inspect control, keyboard-visible focus, narrow
layout, graphite/catalog-blue/paper/green/rust visual premise, serif ledger
heading, and reduced-motion rule.  W2 is static: the only transient state is
the status element's text after an explicit click.  There is no accepted-work
acknowledgment, remote operation, queue, connection, or durable mutation, so an
acknowledged-before-processing crash/recovery case is not applicable.

## Test route and completion conditions

The intended transition is from the observed `node --test` zero-test baseline
to Node discovering `test/app.test.js` and reporting its authored cases.  In
the later authorized checkout, run from `product/`:

```sh
node --check app.js
node --test test/app.test.js
node --test
```

The focused test isolates the bootstrap contract; the full command confirms
Node discovery uses the same local suite.  Passing results establish only the
local static carrier and test harness.  A browser/consumer session, deployed
target, API contract, package/asset route, retry/persistence behavior, and
remote failure handling remain unverified W3-or-later work, not N/A evidence.

## Dependency, correction, and handoff

W2 needs only the retained static shell, Node route, and supplied requirements
and design basis; all are present.  Its future output is the local
`app.js`/test/README carrier and repeatable Node commands.  W3 consumes no
unresolved W2 external contract: W3 independently owns the integration and
target contract before behavior or remote work.

The source-read-only diagnostic cannot correct the stale durable plan pointer.
Carry this pending correction to the **delivery-plan owner** with destination
**the repository-owned planning index** and source
`run/notes/global-plan-reviewed-replacement.md`; the frozen sources do not
identify that index's exact product path, so the owner must resolve it rather
than guess or alter the retained historical note.  This does not block the
future authorized W2 source/test bootstrap.

The next protocol action is the script-returned Improve handoff.  This producer
does not bind, run, or import Improve.
