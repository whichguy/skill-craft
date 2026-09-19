# UI platform-guidance experiment: bounded research and calibration

## Scope and decision boundary

This is a new, static browser fixture for Phase-0 calibration. It tests three
related practices without adding a package, changing ShipLoop, launching a
model, contacting an account, or creating a production artifact:

1. Keep the rendered result owned by the newest relevant async request.
2. Use semantic native controls and verify keyboard operation plus exposed status.
3. Test rendered behavior under controlled schedules rather than only DOM shape
   or implementation selectors.

The existing UI-consumer pilot already has a controlled service double,
reversed-response barriers, semantic controls and an explicit limitation on ARIA
claims. This smaller fixture does not duplicate that product scenario; it
isolates the calibration pattern for the candidate coding-guidance study.
[README.md - existing real-browser and barrier scope](/Users/dadleet/src/skill-craft/test/experiments/shiploop_ui_consumer/README.md:3)
[SPEC.md - existing stale-response and semantic-control contract](/Users/dadleet/src/skill-craft/test/experiments/shiploop_ui_consumer/SPEC.md:4)

The candidate is draft treatment material, not installed policy. Its State card
already requests authority, transitions, concurrency and recovery decisions, and
its Notifications card already asks for truthful accessible UI status.
[shiploop-coding-guidance-candidate-2026-09-18.md - State and Notifications cards](/Users/dadleet/src/skill-craft/docs/shiploop-coding-guidance-candidate-2026-09-18.md:55)

Likewise, the existing shared behavioral guidance already calls for a state
owner and checks for stale/concurrent/out-of-order changes when the boundary
makes them relevant. Its research-loop reference specifically proposes forcing
two asynchronous operations to finish in reverse order and checking rendered
state. This fixture supplies a compact executable instance of that existing
direction; it does not establish a wholly new ShipLoop requirement.
[behavioral-requirements.md - state ownership and out-of-order checks](/Users/dadleet/src/skill-craft/skills/shiploop/references/behavioral-requirements.md:110)
[research-loop.md - reversed-completion UI experiment](/Users/dadleet/src/skill-craft/skills/shiploop/references/research-loop.md:347)

## Primary sources and concrete source inspection

| Source and identity observed 2026-09-18 | What was inspected | Supports | Evidence against overgeneralizing |
| --- | --- | --- | --- |
| [React `useEffect` documentation](https://react.dev/reference/react/useEffect#fetching-data-with-effects), source at [`reactjs/react.dev` commit `b011783f`](https://github.com/reactjs/react.dev/blob/b011783fcc7a39da9eefd4274147a1444860a12b/src/content/reference/react/useEffect.md#L897-L927) | The documented `ignore` cleanup flag prevents a late fetch result from applying after the reactive input changes. | A response must be accepted only if it is still current; cancellation and generation checks are implementation choices. | The same document says direct effect fetching has server-rendering, waterfall and caching drawbacks. Do not turn this small client fixture into a mandate to fetch through a UI effect. |
| [Playwright best practices](https://playwright.dev/docs/best-practices), source at [`microsoft/playwright` commit `78ff4260`](https://github.com/microsoft/playwright/blob/78ff4260d79b924724bdcc4ccd89e463b8f43b0d/docs/src/best-practices-js.md#L12-L16) | Tests should exercise user-visible behavior and favor role/text/contract locators over CSS/XPath. | Browser oracle selectors can make semantics and visible outcomes part of the contract. | Playwright's locator advice does not itself establish accessibility conformance or that a browser suite catches every state defect. |
| [`radix-ui/primitives` roving-focus source at `f7ecd5ab`](https://github.com/radix-ui/primitives/blob/f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae/packages/react/roving-focus/src/roving-focus-group.tsx#L304-L383) | The component handles directional keys, modifier keys, orientation, focusability and focus order explicitly. | Keyboard behavior needs a concrete interaction contract when a composite widget requires it. | This complexity belongs to a roving-focus composite. A one-action search control should retain native `<button>` behavior rather than import a generic focus system. |
| [`testing-library/dom-testing-library` role query at `6049cc0b`](https://github.com/testing-library/dom-testing-library/blob/6049cc0bc7cf2201625c476c95fa6299d0e2fa8b/src/queries/role.ts) and its [README](https://github.com/testing-library/dom-testing-library/blob/6049cc0bc7cf2201625c476c95fa6299d0e2fa8b/README.md#L64-L120) | `getByRole` derives accessible roles/names and the project frames tests around DOM use rather than component instances. | Role/name queries are a useful behavior-facing test interface. | No library installation follows: this fixture uses its already available Playwright browser API, and role checks alone cannot prove assistive-technology usability. |

Commit identities came from read-only `git ls-remote` checks; Playwright's
observed HEAD was `78ff4260d79b924724bdcc4ccd89e463b8f43b0d`, DOM Testing
Library's was `6049cc0bc7cf2201625c476c95fa6299d0e2fa8b`, Radix's was
`f7ecd5ab16f5e1e820eb5786a1419a98a2d594ae`, and the React documentation
source's was `b011783fcc7a39da9eefd4274147a1444860a12b`.

The identity command was:

```sh
git ls-remote https://github.com/microsoft/playwright.git HEAD
git ls-remote https://github.com/testing-library/dom-testing-library.git HEAD
git ls-remote https://github.com/radix-ui/primitives.git HEAD
git ls-remote https://github.com/reactjs/react.dev.git HEAD
```

## Fixture and oracle contract

`fixture.html` has three selectable variants:

| Variant | Intent | Expected calibration outcome |
| --- | --- | --- |
| `reference` | A native button, labeled input, polite status region, and a current-request generation gate. | All behavior checks pass. |
| `stale` | Omits the generation gate, so a late older response overwrites the current one. | The reversal oracle fails; ordinary one-response and weak structural checks still pass. |
| `div-button` | Replaces the native button with a visually similar clickable `div`. | Pointer behavior passes; role/tab/Enter checks fail. |

The browser oracle creates a fresh browser context per case. It controls only
response timing through the fixture's local test seam, then asserts the public
DOM: accessible role/name, focus progression, keyboard activation, live status,
list contents, and the final visible result. It does not accept a passing
internal flag as evidence. The deliberately weak CSS/shape check is a negative
control: it is expected to pass for both the reference and the stale mutant.

This is independent behavior evidence for the fixture mechanism, not a
simulation of a remote server or a proof that any model follows guidance. The
study plan requires calibrated references/mutants before trials and warns that
completed calibration alone cannot establish model effectiveness.
[shiploop-coding-guidance-experiment-plan-2026-09-18.md - calibration requirement](/Users/dadleet/src/skill-craft/docs/shiploop-coding-guidance-experiment-plan-2026-09-18.md:258)
[shiploop-coding-guidance-experiment-plan-2026-09-18.md - UI readiness and evidence limit](/Users/dadleet/src/skill-craft/docs/shiploop-coding-guidance-experiment-plan-2026-09-18.md:325)

## Local execution

No dependency was installed. The observed toolchain was Node `v24.19.0`,
Playwright `1.62.1`, and Chrome for Testing `151.0.7922.47`. The runner requires
`BROWSER_EXECUTABLE_PATH` and resolves Playwright from `NODE_PATH`, so a different
environment must explicitly supply its already available equivalents.

The initial `chromium.launch({headless: true})` preflight failed because this
Playwright package's default headless-shell cache entry was absent. No download
or installation was attempted. Launching the already present Chrome for Testing
binary through `executablePath` passed, so the final command below is the
calibrated route.

```sh
cd /Users/dadleet/src/skill-craft/test/experiments/shiploop_platform_guidance_20260918/ui
NODE_PATH=/Users/dadleet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
BROWSER_EXECUTABLE_PATH='/Users/dadleet/.cache/puppeteer/chrome/mac_arm-151.0.7922.47/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing' \
/Users/dadleet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  browser-oracle.mjs --output results.json
```

The generated `results.json` is the execution receipt. Its expected failures are
calibration successes: the stale and `div` mutants must be rejected by the
respective strong oracles, while the weak check must fail to distinguish the
stale mutant.

## Calibration receipt

The recorded run started at `2026-09-19T00:10:02.921Z` and finished at
`2026-09-19T00:10:06.512Z`. It used fixture digest
`fd04a539addeb3ff77f69b42af1c671d4b5e697092eb7b16783afd6020a81c84` and
oracle digest `d2534c8ed15190e0ef435f06020b662faeba40ef3999eba2adf07bbcd17757ba`.
All nine outcomes matched their predeclared calibration expectation.

| Case | Expected → observed | What it demonstrates |
| --- | --- | --- |
| UI-R1 | pass → pass | The reference preserves `Current note` when an older response arrives later. |
| UI-R2 | fail → fail | The stale mutant visibly overwrote the newer result, so the reversal oracle rejects it. |
| UI-A1 | pass → pass | The reference has one named button, Tab reaches it, Enter activates it, and the resulting status/list are exposed. |
| UI-A2 | fail → fail | The clickable `div` exposes zero named buttons and Tab reaches no search control. |
| UI-O1/UI-O2/UI-O3 | pass → pass | Reference and both mutants can complete an ordinary single pointer search. |
| UI-W1/UI-W2 | pass → pass | The weak CSS/shape check accepts both reference and stale mutant, so it cannot establish freshness. |

This is a successful *calibration* receipt, not nine product-feature passes:
the two expected test failures are the intended mutant rejections.

## Guidance decisions

| Decision | Scope and rationale |
| --- | --- |
| **Adopt for this fixture family** | A UI phase-0 case must name an authoritative result/currentness key and exercise an explicit reversed-completion schedule. Without the schedule, `stale` remains plausible and ordinary tests pass. |
| **Pilot as a compact UI subprompt, not new global policy** | When a request changes a human-facing async interaction, prompt for (a) result authority/currentness or cancellation rule, (b) pending/error/current rendered states, and (c) a browser-visible response-order case plus keyboard/semantic checks for changed controls. This narrows the existing State/Notifications guidance rather than adding a framework rule. Evaluate it only through matched coding-agent trials. |
| **Defer a required real-browser gate** | This host can run Chromium, but a mandatory gate would exclude non-browser or unavailable-browser cases. The experiment plan already makes UI browser evidence conditional on case applicability. |
| **Reject library or pattern mandates** | Do not require React effects, Radix roving focus, DOM Testing Library, Playwright, request IDs, or cancellation universally. The evidence supports the behavioral contract; framework/library choices remain local and proportional. |

The result can support fixture readiness only after the generated receipt shows
the reference and all intended negative-control outcomes. It cannot support
adoption of the candidate guidance until the planned, isolated A/B coding-agent
trials run with frozen packets, access controls and grading.
