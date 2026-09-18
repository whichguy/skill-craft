# Conditional test and verification strategy — Field Notes draft recovery and export notices

## Status and evidence boundary

This run-local strategy plans future verification; it creates no tests and proves no product behavior. It is based on the conditional specification in run/notes/spec.md, the research frontier in run/notes/research.md, accepted UI requirements in product/docs/design.md, and current platform/API facts in product/docs/platform.md and product/docs/api.md.

Current observations, retained in ../../evidence/test-strategy-*, are:

- The tracked product baseline is unchanged at 8f318f0adb98cb3a6e9c6419e57e48ef96ef2a8e; tracked-only status and tracked diff are clean. The full Git status contains the expected untracked .shiploop-improve package-bound runtime evidence from required review cycles, not a product-source change.
- node --check app.js passes, but it establishes JavaScript syntax only.
- Node v25.9.0 and its native node --test help route are available. The repository has no package manifest, test directory, registered test command, CI configuration, or existing behavioral test case.
- safaridriver is present on the host, but no authorized browser target, session, WebDriver configuration, test fixture, or repository browser suite exists. Presence of the executable is not a selected browser route.
- The fixture exposes no durable draft carrier or note contract (Q-R1/Q-R3), no real target access (Q-R4), and no behavioral-test route (Q-R5). These are blocked prerequisites, not N/A checks.

The accepted product requirements home is read-only for this experiment. This note cannot substitute for the normal repository-owned requirements/documentation update; the global plan must retain a named owner and destination for that work.

## Harness and execution decisions

| Route | Current fit and role | Exact command / selector | Status and revalidation |
| --- | --- | --- | --- |
| Existing static diagnostic | Retain the documented local syntax check as a fast guard only. | node --check app.js | **Executed once in this strategy; passed, syntax-only.** It does not select behavioral coverage. |
| Native Node local tests | Smallest currently available no-install candidate for deterministic state, request-order, and fake-response tests after implementation exposes a testable state/reconciliation seam. | Focused (planned): node --test --test-name-pattern='FN-TC-5' test/fieldnotes-state.test.mjs. Local smoke (planned): node --check app.js && node --test test/fieldnotes-state.test.mjs test/fieldnotes-async.test.mjs. | **Required but blocked.** node --test is available, but the named files, test registration, and source seam do not exist. Revalidate source/module shape and Node support after the first implementation plan. |
| Browser interaction/accessibility | Required for rendered list/detail/edit/save/cancel/back behavior, focus, reading position, async notice presentation, and keyboard/touch/narrow-layout observations. | **No authorized executable command exists yet.** A later owner must select an actual browser runner and target-specific command after confirming browser/session/target identity. | **Required but blocked by Q-R4/Q-R5.** safaridriver availability alone cannot establish a route or regression assertion. |
| Same-origin API integration | Required to prove the actual note contract, authorization, reload carrier behavior, and export responses at the real boundary. | **No authorized target URL, credentials, or invocation exists.** | **Required but blocked by Q-R1/Q-R3/Q-R4.** A local fake cannot discharge it. |
| System/journey verification | Required to combine account isolation, reload, async export reconciliation, and preserved UI behavior at the assembled authorized target. | **Full route unavailable.** It will combine the registered local suite with selected browser and same-origin integration commands. | **Required but blocked by Q-R1/Q-R3/Q-R4/Q-R5.** Do not call it N/A because the requested behavior crosses real UI and authorization boundaries. |

The eventual focused/smoke/full suite uses the same stable case selectors; smoke is a bounded subset and does not prove the full route. No remote or target command is inferred from the fixture. A later test-bootstrap producer must retain final commands, runner registration, and test files in the repository-owned test/documentation destination chosen with the normal requirements update.

## Case matrix

All cases are planned and unrun. T-* refers to the specification transition, FN-TC-* is the future stable behavioral check identifier, and FN-NFR-1 preserves the accepted UI/non-functional baseline independently of an async state transition. A fake validates client ordering logic only; it does not prove service authorization or the existence of a durable carrier.

| Case / requirement | Preconditions and stimulus | Independent expected outcome | Planned surface, fixture lifecycle, and boundary | Observation status |
| --- | --- | --- | --- | --- |
| **FN-TC-1 / T-1** pending versus confirmed | Isolated local fixture: effective account A, note N, confirmed text C. Edit to P without save. | Confirmed text/revision remains C; P is visibly pending and never labeled confirmed. | Native Node state test after a pure state seam. Setup fresh A/N/C objects; no shared mutable fixture; teardown discards objects. Browser follow-up confirms rendered label and focus. | Planned; local seam and browser route absent. |
| **FN-TC-2 / T-2** cancel | A/N/C plus pending P. Trigger cancel. | Pending P is replaced with C; no save/API mutation is issued. | Native Node state test with a request spy; fresh objects/spy per case; teardown asserts no residual request. Browser follow-up confirms preserved journey. | Planned; no test file. |
| **FN-TC-3 / T-3** current save confirmation and late-response guard | Contract-defined A/N/revision plus controllable future save response. Release a current success; separately switch identity/note before a held response releases. | Only an authorized current confirmation updates confirmed state. A late old response cannot replace current pending/confirmed UI. | Native Node async test with a controlled promise after Q-R3 defines response/conflict/idempotency behavior. Same-origin integration against the named target remains independently required. Teardown releases held work and clears fake state even on assertion failure. | Required but blocked by Q-R3/Q-R4; expected RED is appropriate after test authoring and before feature behavior exists. |
| **FN-TC-4 / T-4** failure and account race | A has P and a held or failing save; host changes to B before release. | A's failure/text/response is not visible under B; pending text is retained only for the effective identity as the future contract permits. | Native Node async fake with two isolated account namespaces; browser/integration follow-up observes real identity change. Never share the A/B fixture with another case. | Required but blocked by Q-R1/Q-R3/Q-R4/Q-R5. |
| **FN-TC-5 / T-5** reload recovery and isolation | Contract-defined carrier fixtures separately return (a) authorized A/N pending P, (b) authorized absence, and (c) carrier-read failure; then open B. | (a) restores P as pending, never confirmed; (b) shows confirmed content without a recovery claim; (c) shows Recovery Unavailable, not absence. B cannot read A's P. | Native Node fake-carrier test only after Q-R1/Q-R3 define a carrier interface; one fixture per outcome and fresh A/B namespaces. Actual same-origin/browser test must use an authorized isolated tenant and prove its own cleanup. | Required but blocked by Q-R1/Q-R3/Q-R4/Q-R5; primary expected-RED control after test authoring. |
| **FN-TC-6 / T-6** authoritative export difference | Current effective account/collection baseline is established; a fake or real GET /api/exports then returns unchanged and changed status/revision variants. | No notice on unchanged data; a relevant authoritative changed revision/status creates a truthful in-app notice without discarding pending P, focus, or reading position. A POST acknowledgement or hint alone does not count. | Native Node reconciliation test can use an explicit same-scope response fake; browser/API integration observes actual visible/foreground behavior. Setup includes account/collection/revision and teardown resets comparison state. | Local route blocked by missing test files; real check blocked by Q-R2a/Q-R4/Q-R5. |
| **FN-TC-7 / T-7** lifecycle, stale response, and cursor reset | Hold an A/collection response; change effective account or foreground lifecycle before release; establish B's fresh authoritative baseline. | Old A comparison cannot create B's notice. The UI re-reads current scope and preserves active edit/focus/reading position through the truthful loading/error state. | Native Node controlled-promise test for ordering, followed by browser/service journey check. Teardown releases held response and verifies no old scope remains in comparison fixture. | Required but blocked by Q-R2a/Q-R4/Q-R5. |
| **FN-NFR-1 / R-1** preserved native journey and UI baseline | At an authorized target, start on account A/note N with a recorded reading position and pending P; use keyboard and pointer/touch through selector, list, detail, edit, save, cancel, and back at the supported narrow layout, including one visible/foreground reconciliation. | The native controls and navy/amber/white/system/Georgia identity remain present; keyboard and touch controls work; focus, pending text, and reading position are not lost by the asynchronous refresh; save/cancel/back retain their accepted journey. | Browser-only regression assertion after a target/session and runner are selected. Setup records viewport, account/note, focus, and reading position; teardown removes only owned target data and verifies the next case starts clean. This case uses an observed rendered surface, not a screenshot-only claim. | Required but blocked by Q-R4/Q-R5; its target/runner command must be retained when selected. |

## Surface coverage and risk controls

| Surface | Disposition | Rationale and required evidence |
| --- | --- | --- |
| Unit/state | Required but blocked | Covers pending/confirmed separation, cancellation, recovery branch selection, and stale-result guards after a testable source seam and native Node test files exist. |
| Mock/fake collaborator | Required but blocked | Controlled promises and contract-shaped carrier/export fakes are needed to prove ordering and failure branches. They must be driven by Q-R1/Q-R3/Q-R2a contracts and cannot prove real authorization. |
| Same-origin API integration | Required but blocked | Must test actual current-account authorization, note semantics, durable carrier, export status/revision, and target build after a named owner/target makes them available. |
| Browser/end-to-end | Required but blocked | FN-NFR-1 is the stable preserved-journey/visual/accessibility case; FN-TC-1 through FN-TC-7 add rendered async/recovery observations. A target/session/registered route does not yet exist. |
| System/assembled target | Required but blocked | Cross-account reload plus export reconciliation crosses UI, host identity, carrier/API, and lifecycle boundaries. It cannot be replaced by local fakes. |
| Static syntax | Selected diagnostic | node --check app.js is a cheap local guard. It has no behavioral, accessibility, authorization, or target implication. |

Expected-RED controls are retained rather than weakened: after test bootstrap and contract decisions, FN-TC-4 and FN-TC-5 should fail against the pre-feature behavior because it lacks durable recovery and account-safe carrier behavior. The failure must be kept as evidence until a scoped implementation changes it for an independently stated oracle. No current missing test file or runner error is recorded as a behavioral RED.

## Fixture, authorization, and cleanup plan

- **Local fixtures:** each case creates its own A/B account identifiers, note IDs, confirmed/pending text, revision, collection, and controlled promise. No mutable fixture is shared. finally-style teardown releases held work, clears fake carrier/reconciliation state, and checks that a follow-up case starts empty.
- **Carrier/API fakes:** use only values allowed by the eventual named contract; distinguish authorized absence from read failure. A fake response is not authorization proof, and a fake carrier is not permission to select storage.
- **Real target fixtures:** require named owner, target/build identity, authorized two-account/isolated-tenant setup, account-switch/logout procedure, and cleanup/retention route for test drafts and export state. This experiment has none, so no remote test or cleanup was attempted.
- **Browser fixtures:** require the selected browser runner, target URL, effective-account session/role evidence, accessible-state assertions, and reproducible cleanup of target data. A manual browser flow may diagnose a failure but does not count as automated regression coverage.

## Owners, gates, and revalidation

| Need | Owner/boundary before the dependent test can run |
| --- | --- |
| Durable draft carrier, account scope, retention/clear behavior | Named host/target and API owner resolve Q-R1 with authorization evidence. |
| Note read/save/revision/conflict/idempotency semantics | Named note API owner resolves Q-R3. |
| Active export account/collection/cursor comparison | Product/spec owner resolves Q-R2a before FN-TC-6/FN-TC-7 implementation. |
| Browser and behavioral test route | Test owner establishes repository registration/test seam and selects an authorized browser runner for Q-R5. |
| Real integration/system target | Target owner supplies Q-R4 target/build/access and isolated test-data procedure. |
| Normal requirements/documentation destination | Product documentation owner updates the accepted repository-owned requirements home; this run-local strategy is evidence only. |

Revalidate this strategy if the target/platform probe changes, an API/carrier contract is supplied, source extraction changes the seam, Node/browser support changes, a test runner is registered, or a real target becomes available. Until then, the only executed result remains the syntax diagnostic; every planned behavioral, integration, browser, and system case is unrun or blocked as shown.
