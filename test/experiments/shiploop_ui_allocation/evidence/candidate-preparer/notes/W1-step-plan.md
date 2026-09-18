# W1 step plan — static UI build and verification harness

**Action:** `nav-8178dc574a0a4c97ad44b4cdfa80a7a6` (`step-plan`)  
**Scope:** preparation for the static Archive Exports client and its local verification harness. This is a plan only; it does not implement the client, run a package install, invoke an API, deploy, commit, push, or bind/run Improve.

## Authority, baseline, and readiness

The active user request authorizes local Node/build tooling for this preparation item only. It prohibits a deployed server, remote request, installation, and deployment. The fixture is an archived non-Git directory: both the case root and `product/` lack Git metadata, so no Git initialization or Git-based baseline is planned.

The current product sources are the only verified contract inputs for this item:

- `product/README.md:1-5` defines the archivist-facing outcome and says that no UI, build, or harness exists.
- `product/docs/platform.md:1-4` requires a static embedded surface; deployed assets must be same-origin and CSP-compatible; it disallows a deployed Node/server runtime, inline script/style, external CDNs, and persistent WebSockets.
- `product/docs/api.md:1-2` defines the existing API and recovery boundaries: the service owns export state, POST acknowledgement can be lost after durable acceptance, reconciliation uses the client operation ID, polling happens while visible, and foreground reconciliation is required.
- `product/scripts/probe_environment.py:1-6` and `product/host-observation.json:1-14` currently identify `archive-static-v1`, `script-src/style-src: self`, no server/WebSocket, unassessed client persistence, and no draft API. They are controlled fixture observations, not a deployment receipt.

All earlier root-stage and `select-work` records are explicitly synthetic; they supply no executed research, baseline, test strategy, implementation, or Improve evidence. The current run-wide test-strategy pointer therefore required scoped reassessment. The revalidated local facts and source hashes are in `run/notes/W1-step-plan-checks.md`.

**Ready for W1 implementation:** the documented static target constraints, API contract, and locally available Node `v25.9.0`/npm `11.18.0`.  
**Not ready / not claimed:** an existing package runner, UI source, build output, tests, browser journey, target deployment, remote API access, or persistence across a browser crash. The absent harness is W1's owned output, so it does not block this preparation work. Later feature consumers must wait for W1's build and test commands to exist and pass.

The run has no record selecting source-aware-native Backchain resources. This step uses the selected ShipLoop package's embedded planning adaptation only; it does not invoke a standalone Backchain workflow or create a second review loop.

## Design basis and interaction agreements

This is a human-facing archivist work surface whose single job is to make an export's status intelligible from collection choice through recovery or download. I applied the selected `frontend-design` card at `<study>/capabilities/frontend-design/SKILL.md` (SHA-256 `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`). Its relevant direction is a deliberate, subject-specific visual identity, direct task language, native keyboard focus, responsive layout, useful async feedback, and a reduced-motion alternative.

The resulting preparation premise is an **archive transfer docket**, not a generic dashboard: a calm dark-teal work surface (`#17343B`), paper field (`#F2F0E8`), oxidized brass action (`#B66A2C`), verdigris completion (`#277B73`), slate queued/running (`#546B82`), and ink (`#162125`). Use the system `ui-sans-serif` family for readable task text and `ui-monospace` only for revisions/job IDs; do not introduce an external font or CDN. The signature is a vertical filing-slip status rail whose marks communicate actual stages rather than decoration. On narrow screens it becomes a labelled horizontal sequence. Motion is limited to a short status-transition cue; `prefers-reduced-motion` makes the state change immediate while retaining the same text and visual state.

The W1 shell may establish tokens, landmarks, focus styles, responsive layout, and an honest empty/preparation state, but it must not pretend that a collection was selected, a request was accepted, or a completed export exists. Feature consumers own the interactive views.

The future client contract that the scaffold and fixtures must make testable is:

1. The archivist initiates collection selection and export requests; the same-origin API is the authoritative state owner. Presentation state is transient: selected collection, the current `clientOperationId`, visible status/error/recovery notice, and latest observed revision. There is no justified browser-side durable draft store.
2. A feature client generates a `clientOperationId` before POSTing. A returned acknowledgement is only durable acceptance of the operation, not completion. If confirmation is lost, it queries `/api/operations/:clientOperationId` before any retry and never announces success merely from a timeout or animation.
3. The future client reads `GET /api/exports` while visible and reconciles on foreground. It does not open a WebSocket, treat notifications as authoritative state, or rely on a local Node server in the deployed artifact.
4. A complete job exposes a same-origin download path only after a current job-status read; failure remains visible with an actionable recovery choice. Colour, animation, and a transient toast never carry the only status information.
5. The crash boundary remains intentionally unresolved: if the server accepted a POST but the page crashes before the response is processed, client persistence is not assessed and the operation ID may be unavailable after restart. A later feature must refresh server state, must not automatically retry an unknown request, and must either verify a supported persistence route or describe a user-visible recovery path. W1 can provide a fake API fixture for this case; it cannot claim target recovery proof.

## Planned output and implementation microplan

The future W1 implementation stays at the preparation boundary and is ordered by actual prerequisites.

| Order | Planned carrier and responsibility | Need / supplier | Observable planned result and check |
| --- | --- | --- |
| 1 | `product/docs/ui-preparation.md` and a short `README.md` build/test entry | Current README, platform, API, probe observation, and this plan | Durable design basis, state/authority/recovery contract, command list, and limits. It distinguishes accepted fixture contracts from proposed UI choices and names remote/browser verification as unrun. |
| 2 | `product/package.json`, `product/scripts/build-static.mjs`, and `product/scripts/verify-static-output.mjs` | Node/npm observed locally; no installed package or framework exists | A zero-dependency, ESM-only local build route copies a declared source tree into a deterministic `dist/` artifact and validates it before replacement. It uses Node built-ins only (`node:fs`, `node:path`, `node:crypto`, `node:assert`, `node:test`); no `npm install`, `npm ci`, bundler, CDN, or deploy step. |
| 3 | `product/src/index.html`, `product/src/assets/app.css`, and `product/src/assets/app.js` | Static-CSP requirements and design basis | A same-origin external stylesheet/module entry point plus an honest archive-export shell. The source uses no inline script/style, external asset URL, server route, socket, or request. It supplies semantic landmarks, focus styling, narrow-layout rules, status-rail tokens, and a mount/contract seam for later feature modules without implementing collection selection or export actions. |
| 4 | `product/test/build-static.test.mjs`, `product/test/static-output.test.mjs`, and `product/test/helpers/temporary-project.mjs` | Node's built-in test runner and the planned builder | Isolated, stateless test fixtures exercise build output and policy failures. Each case creates its own OS temporary directory, derives an independent expected output/policy result, and removes it in `finally`; tests never call a network endpoint or leave mutable fixture data in the product directory. |
| 5 | Generated `product/dist/` plus README/documentation updates | Passing local build and tests | The output is a local static artifact only. Verification records its file manifest/content hashes and source-relative diagnostics. It is preparation evidence, never a deployed artifact, a live API check, or consumer proof. |

`build-static.mjs` should validate the complete candidate before replacing `dist/`, write into a temporary sibling directory, and leave the prior output intact if validation/copy fails. A failure reports a stable rule name and source-relative path (for example, `external-asset: src/index.html`) plus the original cause; it must not mask cleanup failure or dump source contents. No pre-existing debug control exists. The builder's normal diagnostic is bounded and non-sensitive; a future runtime debug facility is out of W1 scope unless a later feature has a demonstrated need.

The package scripts should be deliberately small:

- `npm run build` — generate and validate the static artifact.
- `npm run test` — run every `node --test` case under `test/`.
- `npm run test:smoke` — run the stable static-output/build subset using the same case selectors, not a duplicate implementation.
- `npm run verify` — clean build followed by the full test route.

No `lint` command is promised because no lint tool is installed or authorized. The static verifier is a policy/build check, not a mislabeled lint pass.

## Planned cases, fixtures, and suites

| Case | Setup and independent oracle | Planned command / suite | Teardown and limit |
| --- | --- | --- | --- |
| `W1-BUILD-01` valid static artifact | Copy the declared valid `src/` fixture to an isolated temp project; oracle asserts `dist/index.html` links only relative/same-origin external CSS/JS and every declared asset exists. | Focused: `npm run test -- --test-name-pattern=W1-BUILD-01`; smoke and full: `npm run test:smoke`, `npm run test`. | Delete isolated temp directory. It proves local artifact shape only. |
| `W1-BUILD-02` CSP/same-origin rejection is actionable | Per-case temp source introduces one inline script/style or external URL; oracle expects a nonzero build result naming the violated rule/path and unchanged previous `dist/`. | Focused selector; smoke and full suite registration. | Delete temp directory; no remote request. This distinguishes a validator that merely copies files from one that enforces target constraints. |
| `W1-BUILD-03` deterministic replacement/manifest | Two clean isolated builds from the same source; oracle compares the file manifest/content hashes and ensures stale output is absent after a successful replacement. | Focused and full suite. | Delete both temp directories. It does not prove a host deploy uses the artifact. |
| `W1-HARNESS-01` suite registration | A deliberately policy-invalid fixture must fail its direct assertion while valid fixtures pass, proving the runner sees both selected cases. | Full `npm run test`; smoke contains only W1 static-contract cases. | Stateless beyond each temp directory. A zero-selected test invocation is explicitly not a pass. |
| `AE-RECOVERY-01` through `AE-RECOVERY-05` (future consumers) | Fake API responses will later cover visible polling, foreground refresh, accepted-but-unconfirmed POST reconciliation by operation ID, complete-only same-origin download, failure/unknown recovery, and the crash-after-acceptance boundary. | Future feature test selectors only; not run or claimed by W1. | Fakes isolate local client logic. A real target/browser/API check remains required when the feature exists and access is authorized. |

The test harness has no mutable shared resource, so setup is per temporary project and teardown is explicit. Full-suite registration is part of the planned `node --test` glob; focused and smoke commands reuse those durable cases. Browser testing is considered but not selected for W1's own no-interaction scaffold: a browser is necessary later for rendered collection/export journeys, keyboard behavior, responsive observation, and target CSP/API behavior. No deployed target or feature exists here, so a source inspection or local static artifact cannot substitute for that later check.

## Dependency audit and downstream handoff

**Claim:** W1 produces a locally buildable, CSP-aware static client shell and a repeatable Node verification harness that later archive-export feature work can use.  
**Needs:** documented target/API contracts, same-origin asset policy, a local runner, a source/output layout, isolated fixtures, and a durable record of unverified target behavior.  
**Supplied now:** the source documents and controlled observation listed above; Node/npm availability; no existing UI/harness.  
**Supplied by W1 implementation:** the source layout, build scripts, local test runner, static-policy test fixtures, and artifact manifest.  
**Pulled by later consumers:** stable build/test commands, a CSP-safe entrypoint, design/state contracts, and fake transport seams. They do not need W1 to fabricate a live API, deployment, browser session, persistent storage, or completed export.  
**Unresolved / retained:** target-supported client persistence and real embedded-browser/API verification. Neither is a current prerequisite for building the static harness, but both remain mandatory considerations for the future interactive feature and final consumer verification.

The selected work item is correctly the preparation producer before feature consumers. It may produce its own missing output; it must not absorb the later collection-picker, export progress, or recovery feature implementation. The next owner is the packet's automatic Improve handoff, which must review this plan before any W1 implementation begins. No Improve activity has occurred in this producer result.

## Evidence and revalidation conditions

- Re-read `product/docs/platform.md`, `product/docs/api.md`, and rerun `python3 product/scripts/probe_environment.py` before implementing W1 or if the fixture contents/hash changes.
- Re-check local Node/npm availability before using the proposed built-in harness. Do not add a third-party package merely because a richer UI/test tool is available.
- Re-open this plan, `run/notes/W1-step-plan-checks.md`, and the product sources at the next W1 stage. The planned paths and commands are not evidence of authored files or passing tests.
- Reassess the planned browser/target verification when a feature has a rendered journey and an authorized target. Preserve the remote/deployment gap rather than treating local success as delivery evidence.
