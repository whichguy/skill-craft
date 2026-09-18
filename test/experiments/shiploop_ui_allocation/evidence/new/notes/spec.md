# Archive Exports specification candidate

## Status and authority

This is the current **run-local specification candidate** for the isolated planning experiment. It records the requested delta and planning checks; it is not a repository-owned requirements home. The controlled product has neither `docs/requirements.md` nor `SHIPLOOP.md` (`run/evidence/spec-requirements-home-stdout.txt`), but `EXPERIMENT.md` forbids source-checkout edits. Creating or linking the normal durable requirements home is therefore a required later, authorized preparation task rather than an action taken in this run.

| Source | Status | Use in this candidate |
| --- | --- | --- |
| `REQUEST.md` | current user requirement | Defines the archive export client, its outcomes, accessibility, async feedback, visual identity, and preparation planning scope. |
| `product/README.md` | fixture overview | Confirms no UI, build, or harness exists and points to the controlled target/API facts. |
| `product/docs/platform.md` and `host-observation.json` | controlled fixture contract | Bounds the deployed artifact: static, same-origin assets, no inline/CDN source, no server runtime or WebSocket, host-owned identity, visible polling and foreground reconciliation. |
| `product/docs/api.md` | fixture API contract | Bounds the API lifecycle and server authority; it is not a deployed-service observation. |
| `run/notes/research.md` | run-local research decision | Supplies the dependency-free client proposal, evidence boundaries, and archive-ledger design direction. |
| `frontend-design/SKILL.md` (`sha256: 1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`) | selected design guidance | Requires a deliberate archive-specific identity, useful copy, visible keyboard focus, narrow-screen usability, and restrained motion. |

The source fixtures were rechecked at product HEAD `ec3243d658e24304b306749bc361869154fc4660`; source and probe evidence is retained under `run/evidence/spec-*`. No product source, target, API instance, account, or consumer session was changed or observed.

## Requirement delta

All identifiers below are candidates to be placed in the later authorized repository-owned requirements home. “Accepted” means supported by the current request or the documented fixture contract; “design decision” means an in-scope choice made for planning, not a claim that it has been implemented or independently approved.

| ID | Kind and basis | Requirement / decision | Planned evidence |
| --- | --- | --- | --- |
| R-01 | Accepted — user request, API fixture | An archivist can see the current authorized collection/export view and choose one collection before requesting an export. The client does not create collection data or authority. | Fixture-driven client test and later target-compatible browser check. |
| R-02 | Accepted — user request, API fixture | An explicit user request sends `collectionId` and a client operation ID to `POST /api/exports`. The interface may show a request-in-flight state, but must not report durable success until the API supplies a confirmed or reconciled authoritative result. | Controlled request/response cases, including lost confirmation. |
| R-03 | Accepted — user request, API fixture | The client presents the API-owned queued, running, complete, and failure outcomes with concise, action-oriented feedback. A newer accepted revision must not be replaced with an older view. | State/revision transition cases and manual browser review. |
| R-04 | Accepted — user request, API fixture | A completed export may be opened only when `GET /api/exports/:jobId` reports `complete` and supplies its same-origin download path. Queued, running, unknown, and failed jobs do not expose a fabricated download affordance. | Completion/failure boundary cases. |
| R-05 | Accepted — platform/API fixture | While visible, the client polls the documented request/response API; on foreground it re-reads authoritative state. It does not depend on a WebSocket or treat notifications as authoritative updates. | Lifecycle cases using controlled visibility/foreground events. |
| R-06 | Accepted — user request and design guidance | Collection choice, request, status, recovery guidance, and completed-export action are usable by keyboard with a visible focus treatment. A narrow layout preserves order, labels, status, and usable action targets. Any motion is minimal and respects reduced-motion preference. | Keyboard walkthrough, narrow viewport review, and reduced-motion observation; the representative viewport is to be selected in test strategy rather than invented here. |
| R-07 | Design decision — user-requested visual identity, selected design guidance | Use an archive-ledger identity: graphite `#17212B`, catalog blue `#294C67`, paper-gray `#E2E8E5`, circulation green `#3A765C`, and rust `#A84638`; quiet sans controls with a restrained serif collection/status treatment and monospace metadata; an accession-strip/ledger line communicates the real export lifecycle. The strip must encode state or chronology, not be decoration. | Design review against the component/interaction model; same-origin bundled font source remains unresolved. |
| R-08 | Accepted — controlled platform contract | The deployed client is a static same-origin artifact: scripts, styles, fonts, and images are bundled same-origin; no inline script/style, external CDN, deployed server runtime, or persistent WebSocket is required. | Static artifact/CSP inspection and target-compatible deployment check when access exists. |
| R-09 | Accepted evidence boundary — experiment scope | Local fixture, Node, and preview checks can establish only their stated local behavior. Delivery and an authorized consumer operation are necessary later work, but no deployed target, live API, or consumer-session behavior is claimed now. | Owner-authorized target and consumer validation later. |

## Components, actors, and state ownership

| Actor/component | Channel | Owns / does not own |
| --- | --- | --- |
| Archivist | keyboard/pointer interaction with embedded client | Chooses a collection and explicitly initiates an export; does not grant account identity or invent a server result. |
| Embedded host | embedding and authorization context | Owns account identity and authorization; its hidden-page behavior can suspend client work. |
| Static client | same-origin browser request/response and local display state | Owns selected collection, transient request/reconciliation state, latest received revision, focus and visual feedback; it is not the durable job authority. |
| API service | same-origin HTTPS endpoints | Owns authorized collections, export jobs, durable operation acceptance, job status, revision, and complete-only download path. |
| Browser lifecycle | visible/hidden and foreground events | Signals when polling may run and when the client must reconcile; it does not provide authoritative export state. |

The planned surface has four components: a collection selector, an export request control with concise pending/recovery message, an export-status ledger, and a complete-only download action. Supporting elements are a contextual status summary and inline failure/recovery guidance. Native semantic controls are preferred for selection and request actions; no custom widget is required to create a visual identity.

## Interaction and recovery model

1. On visible entry or foreground, the client gets the current export view and records the highest accepted API revision for display.
2. The archivist selects a listed collection. This changes only local selection state.
3. An explicit request creates a client operation ID and sends the documented POST. The UI says that the request is being recorded, not that the export is complete.
4. A confirmed response associates the returned job with the current display, then normal visible polling/foreground reconciliation reads current server state.
5. If confirmation is lost or ambiguous, the client must not announce success. It reconciles through `GET /api/operations/:clientOperationId` only while an operation ID is available; how that ID survives a full reload is unresolved because persistent storage is `not_assessed`.
6. The ledger renders queued/running/complete/failure from current authoritative data. Only complete has an enabled open-export affordance; failure names the failed outcome and provides no invented retry behavior.
7. When the page is hidden, polling may pause. On foreground it re-reads authoritative state instead of assuming an in-memory status is current. Notification inputs, if later available, are invalidation hints only.

### Relevant state transitions and invariants

| Transition | Before → after | Invariant / recovery |
| --- | --- | --- |
| Choose collection | current view → selected collection | No API mutation occurs. |
| Submit export | selected collection → request in flight | One user action maps to one client operation ID; no success claim before confirmed/reconciled API evidence. |
| Confirmation lost | request in flight → reconciliation pending | Look up the known ID; unresolved is visible as unresolved, never coerced to success. |
| API revision advances | prior view → newer current view | Do not regress the accepted displayed revision. |
| Job completes | queued/running → complete with download path | Enable open-export only from API’s complete response and same-origin path. |
| Job fails | queued/running → failure | Retain failure feedback; repeat-POST/error semantics are not guessed. |
| Foreground | possibly stale local view → reconciled view | Read authoritative API data before presenting current status. |

## Acceptance cases and planned checks

| Case | Input / condition | Expected observable result | Verification boundary |
| --- | --- | --- | --- |
| AC-01 | Authorized GET returns collections and mixed export states | A collection can be chosen and the ledger communicates each returned state. | Local fixture/unit or controlled browser case; later target check. |
| AC-02 | Archivist requests a selected collection and POST confirms | The UI acknowledges recorded work, follows the returned job, and does not label it complete until the complete status arrives. | Controlled API lifecycle case. |
| AC-03 | POST confirmation is lost | The UI avoids success language and reconciles the known operation ID; if the ID is unavailable after reload, it reports the recovery limitation rather than fabricating a result. | Failure/recovery fixture case. |
| AC-04 | API returns a newer revision after a prior view | The newer state is shown and a later stale response cannot replace it. | Deterministic reducer/client-state case. |
| AC-05 | Current job is queued, running, complete, then failed in distinct cases | Feedback changes meaningfully; only complete exposes the supplied download path. | State boundary fixture case. |
| AC-06 | Page becomes hidden then foregrounded | Polling is not required while hidden; foreground triggers an authoritative refresh. | Controlled lifecycle case. |
| AC-07 | Keyboard-only navigation, narrow representative viewport, reduced-motion preference | All essential controls/actions remain reachable and understandable; focus is visible; layout retains useful order; nonessential animation is suppressed. | Manual browser accessibility/design review. |
| AC-08 | Produced static artifact is inspected | No inline or external/CDN scripts/styles/fonts are needed; no WebSocket/server-runtime dependency appears. | Artifact/CSP check on the real target when available. |
| AC-09 | Owner-authorized embedded target and consumer session become available | The actual embedded surface can perform the documented flow for the authorized user without crossing the fixture evidence boundary. | Later authorized consumer validation; currently blocked. |

## Non-functional assessment

- **Target compatibility and security:** R-08 is a hard constraint from the controlled fixture. Same-origin source, static deployment, host-owned identity, and no WebSocket are requirements; local preview is insufficient proof of the deployed target.
- **Accessibility and responsiveness:** R-06 has observable keyboard, focus, narrow-layout, and reduced-motion checks. Exact viewport and assistive-browser matrix are currently unselected and belong in the test strategy.
- **Correctness/recovery:** revision ordering, complete-only download access, lost-confirmation reconciliation, and foreground refresh are correctness conditions. Missing API error, duplicate/operation, collection, and retry semantics remain open rather than receiving invented behavior.
- **Visual quality:** R-07 is reviewed for a specific community-archive ledger identity, disciplined hierarchy, plain action copy, and a useful state-bearing accession strip. The later implementation must use a proven bundled same-origin font source or a system fallback; it cannot assume a CDN font.
- **Performance, scale, and availability:** no measured workload, latency, polling cadence, cache policy, or target performance budget was supplied. No numeric goal is asserted; any later choice needs source or owner basis.
- **Delivery/consumer:** this experiment has no deployment authority or authorized consumer session. That unresolved external boundary does not make the client requirement optional.

## Open prerequisites before implementation or prepare

1. An authorized product documentation edit must establish and link the durable requirements home (`docs/requirements.md` unless an existing home is selected). This run must not make that source change.
2. The API owner or an approved local fixture must define collection shape, status/error vocabulary, operation lookup outcomes, duplicate/repeat POST behavior, retry policy, and an allowed operation-ID persistence strategy.
3. The source/rights and same-origin packaging route for the visual type treatment must be chosen; system fallback is the safe unselected default, not evidence of the intended font.
4. A target-compatible entry/asset packaging route and repeatable local test route must be selected after the contract decisions; no framework, dependency, or harness is selected by this candidate.
5. An owner-authorized embedded target and consumer session must be supplied for delivery and consumer validation.

## Planning mode

The current navigator v3 run uses the selected ShipLoop **embedded Backchain adaptation** for dependency reasoning. No run note selects `source-aware-native`, and no standalone Backchain invocation is claimed. This candidate carries the applicable requirement, acceptance, design, state, and prerequisite locators forward to the test-strategy and plan stages.
