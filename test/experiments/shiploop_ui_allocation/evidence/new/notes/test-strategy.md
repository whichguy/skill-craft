# Archive Exports test and verification strategy

## Status, baseline, and selection basis

This is a run-local strategy for the specification candidate at `run/notes/spec.md`; all commands below are **planned unless explicitly identified as observed**. The product has no client source, package manifest, test directory, runner configuration, build configuration, or existing behavior suite. The observed `node --test` baseline reports zero tests/suites/passes/failures (`run/evidence/test-strategy-node-test-baseline-stdout.txt`), so it is evidence of missing coverage, not a green suite.

Current local capability observations:

| Capability | Observation | Strategy decision |
| --- | --- | --- |
| Node | `v25.9.0`; `node --test` runs and reports zero selected tests | **Selected** for future dependency-free pure-state/API-adapter/static-constraint tests, using Node’s built-in runner. |
| npm | `11.18.0`, but no product manifest or dependency lock exists | **Not selected**; no installation or package-script assumption is needed for `.mjs` tests. |
| Python static preview | `python3 -m http.server --help` confirms a local static directory server | **Selected for local visual/manual inspection only** after a static artifact exists; it does not prove target compatibility or API behavior. |
| Safari driver | executable path observed, but no configured browser automation, app, target, or authorized session exists | **Not selected** as an automated regression runner. It may be reconsidered only after the actual browser surface and authorized route exist. |
| Playwright | no executable found; no product-local installation | **Required browser-automation option remains unavailable**, not silently replaced with an install. |
| Real embedded target / consumer | no deployment access, target identity, consumer session, or remote test framework supplied | **Required but blocked** for R-09 / AC-09. |

The controlled fixture facts remain current: static same-origin assets, self-only script/style, no server runtime or WebSocket, host-owned identity, visible polling/foreground reconciliation, and `client_persistent_storage: not_assessed` (`run/evidence/test-strategy-probe-stdout.txt`). The run also still lacks the normal durable requirements home because product edits are prohibited. These are readiness conditions, not passing results.

## Selected local harness and planned layout

The smallest sufficient local harness is Node’s built-in `node:test` plus `node:assert/strict`, with no third-party dependency. The planned static source/test layout is deliberately small:

```text
web/index.html
web/assets/app.mjs
web/assets/export-state.mjs
web/assets/export-api-client.mjs
web/assets/styles.css
test/export-state.test.mjs
test/export-api-client.test.mjs
test/static-constraints.test.mjs
```

This is a planned preparation shape, not an implemented layout. Pure state and request/reconciliation mapping must stay importable without browser globals so the built-in runner can test them. DOM rendering, browser lifecycle, and visual design require complementary browser/manual observation; a local fake cannot prove the target or authorized API.

### Planned suite entry points

Run from the product root after the named test files exist and are registered by Node discovery:

| Level | Exact planned command | Membership and purpose |
| --- | --- | --- |
| Focused state diagnosis | `node --test test/export-state.test.mjs` | T-01 through T-06: selection, pending/confirmation, lost confirmation, revision ordering, complete-only action, lifecycle reconciliation. |
| Focused request mapping | `node --test test/export-api-client.test.mjs` | T-02, T-03, T-05: POST/operation lookup/job read construction and response-to-state mapping against a deterministic fake. |
| Focused static constraint check | `node --test test/static-constraints.test.mjs` | T-07: planned static artifact has no inline/external source assumptions and follows the selected asset layout. |
| Smoke subset | `node --test test/export-state.test.mjs test/export-api-client.test.mjs test/static-constraints.test.mjs` | One representative assertion for every local functional/constraint category; it is a bounded subset. |
| Full local suite | `node --test` | Every discovered durable local test. A zero-selected result is a failure of suite registration/coverage, not a pass. |

Expected-RED control: after test bootstrap but before the matching client behavior is implemented, author T-03 and T-04 against the accepted lost-confirmation and revision invariants, run their focused command, retain the expected failure against unchanged source, then implement only the required behavior and rerun. No expected-RED test has been authored or run in this planning experiment.

## Case mapping, fixtures, and boundaries

| Test ID | Requirement/case | Layer and planned selector | Fixture lifecycle and oracle | Boundary/status |
| --- | --- | --- | --- | --- |
| T-01 | R-01 / AC-01 selection | Unit — `test/export-state.test.mjs` | Stateless frozen collection/status object; select one ID; assert local selection changes with no request effect. Teardown: none. | Selected local. |
| T-02 | R-02 / AC-02 confirmed request | Unit + adapter fake — state and API-client files | Per-test fake `fetch` records `collectionId`/operation ID and returns documented confirmed data; assert pending wording precedes authoritative status. Teardown: fake discarded. | Selected local; fake does not prove API. |
| T-03 | R-02 / AC-03 lost confirmation | Unit + adapter fake — state and API-client files | Fake loses POST confirmation, then supplies operation lookup result; assert no success before reconciliation. Separate fixture for unavailable operation ID after reload; assert visible unresolved state. Teardown: fake discarded. | Selected local; full reload persistence semantics remain blocked on owner/fixture decision. |
| T-04 | R-03 / AC-04 revision ordering | Unit — `test/export-state.test.mjs` | Frozen response pair with newer then older monotonic revisions; assert the view never regresses. Teardown: none. | Selected local. |
| T-05 | R-04 / AC-05 job state/download | Unit + adapter fake — state and API-client files | One fixture each for queued/running/complete/failure; assert only complete exposes the supplied same-origin path. Teardown: fake discarded. | Selected local; real download/authorization remains target/API validation. |
| T-06 | R-05 / AC-06 visibility/foreground | Unit — `test/export-state.test.mjs` | Explicit visible/hidden/foreground events with a fake refresh call; assert hidden does not require polling and foreground requests current state. Teardown: event fake discarded. | Selected local. |
| T-07 | R-08 / AC-08 static constraints | Static-source inspection — `test/static-constraints.test.mjs` | Read only the planned static files and assert the selected artifact does not rely on inline scripts/styles, CDN URLs, WebSocket creation, or a server runtime. Teardown: none. | Selected local after files exist; target CSP still required separately. |
| T-08 | R-06, R-07 / AC-07 | Local browser/manual procedure | Serve the planned `web/` directory, use keyboard-only navigation, a documented narrow representative viewport, and reduced-motion preference; inspect focus, labels, order, action state, and ledger hierarchy. Teardown: stop local preview. | Required but blocked until static UI and approved local example data exist; not automated coverage. |
| T-09 | R-02–R-05 / AC-02–AC-06 | Real API/embedded target integration | Owner-approved non-production account/collection, unique operation ID, documented cleanup/retention rule, target/revision identity, and response evidence. | Required but blocked: API details, access, and target route are absent. |
| T-10 | R-09 / AC-09 | Authorized consumer end-to-end journey | Authorized consumer session on the actual embedded target, known deployed artifact identity, selected collection, request/reconcile/status/open observations, and owner-approved cleanup. | Required but blocked: no target/session/deployment authority. |

The local unit and fake-based adapter tests are stateless or per-test isolated and can run in any order. No shared server, account, collection, port, persistent storage, or remote state is selected. T-09 and T-10 must not reuse a mutable account/collection until the owner provides isolation and cleanup; a local mock, preview, or smoke result cannot substitute for either.

## Browser and target procedures

When the static artifact exists, the planned local visual procedure is:

```sh
python3 -m http.server 4173 --bind 127.0.0.1 --directory web
```

Then inspect `http://127.0.0.1:4173/` in a local browser with a documented example-data fixture. Record the browser/version, viewport, reduced-motion setting, artifact digest, exact keyboard sequence, visible result, and the fact that this is a local static preview. The preview can support T-08 only; it cannot exercise the same-origin production API contract, embedded host identity, deployment CSP, or an authorized consumer journey.

T-09 needs an owner-approved API fixture or non-production embedded target after the unresolved collection/status/error/operation/repeat-POST/retry/persistence semantics are resolved. T-10 needs the actual target and consumer authorization. No remote-resident test framework, invocation interface, or result-retrieval route has been observed, so no remote command is invented.

## Non-functional and risk coverage

| Concern | Decision | Planned check / revalidation |
| --- | --- | --- |
| Keyboard, narrow layout, reduced motion, visual hierarchy | Selected | T-08 local browser/manual review after UI exists; then re-run at actual target for T-10. Choose representative viewport and browser from available environment at execution time. |
| CSP/static deployment fit | Selected | T-07 local source check plus actual target CSP/artifact observation within T-09/T-10. |
| Recovery/correctness | Selected | T-03, T-04, T-05, T-06; API contract change or selected persistence strategy triggers revision. |
| Security rendering | Required local follow-up | Add a textual-rendering case using API-provided strings containing markup-like content once view/rendering implementation is selected; retain target authorization as API/host-owned and blocked for real-boundary verification. |
| Fuzzing | Not applicable now | No parser, serializer, or untrusted-input transformation with a meaningful oracle is selected. Reassess if a parser/schema/format converter is introduced. |
| Dependency maintenance | Not applicable now | No product dependency is selected. Reassess if a dependency is deliberately added. |
| Performance/load | Required but blocked | No workload, latency, polling cadence, cache policy, or target budget exists. Owner/target information is required before a meaningful performance case can be selected. |

## Readiness and carry-forward

Before implementation/tests can start, the plan must include: (1) an authorized product documentation update for the durable requirements home; (2) API-owner or approved-fixture decisions for the unresolved contract semantics and a permitted operation-ID recovery strategy; (3) a same-origin font/asset source and static entry layout; (4) source/test bootstrap within the later authorized product-edit scope; and (5) owner-authorized target/consumer access for T-09/T-10.

This strategy is the run-wide test-decision source for later planning. It is intentionally not a test result, browser session, target readiness receipt, or authorization grant.
