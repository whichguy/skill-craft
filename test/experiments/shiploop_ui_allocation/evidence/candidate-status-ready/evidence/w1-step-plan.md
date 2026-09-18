# W1 step plan — read-only export-status observation

## Scope and verified baseline

This is a **plan for the selected W1 producer only**. It makes no product edit,
test edit, deployment, account change, request creation, or other mutation.
The requested delta is an in-memory observer for the existing host-authorized,
account-scoped `GET /api/exports` status snapshot. It must not add an
export-request flow,
collection selector, operation reconciliation, download behavior, persistent
draft storage, or any other mutation. W2 remains the separately blocked
persistent-draft item.

The repository-owned baseline is `product/README.md`,
`product/docs/design.md#UI identity`, `product/docs/platform.md`, and
`product/docs/api.md`; the selected W1 schema is
`evidence/controlled-status-schema.md`. The product is a non-Git fixture
(`.git` is absent), so no revision is claimed and Git must not be initialized.
The current product content identities are recorded by the producer command
output: `app.js` is
`729f0db397fe3b0eaae3fadff9de10facd82b071fb7bbe00a95dcb9d9b5f8ac2`,
`index.html` is
`f52423358a46b6210774533586602fb75267deb631129ba9bf96293e68f88213`, and
`styles.css` is
`cd3106112e5ddff749af99d9e3de730274f7786ccde2a2c4e75c172753b646bf`.

`python3 product/scripts/probe_environment.py` succeeded; its unmodified raw
output is in [w1-probe-environment.raw.json](w1-probe-environment.raw.json).
It establishes only controlled fixture facts: static embedded target
`fieldnotes-embedded-v2`, same-origin script/style/API support, no server
runtime or WebSocket, unavailable client persistent storage, no draft API, and
no live-deployment evidence. `node --check app.js` passed. `node --test`
exited 0 but discovered zero tests; the exact output is in
[w1-baseline-checks.raw.txt](w1-baseline-checks.raw.txt). Therefore no
executable test result is reused as W1 coverage. The packet-named prior
test-strategy result
`run/results/nav-131af2d40bd94ea086f45d2b4d043a0b.md` is absent, and the
state labels its predecessors synthetic; this plan reassesses W1 rather than
relying on a claimed earlier review.

No environment-lifecycle note is created for this planning-only fixture: no
environment augmentation or remote delivery operation is in scope. A later
release-oriented stage must revisit the recorded target and authority; this
baseline is not a deployment or consumer receipt.

## Contract and design basis

**Preserve.** The current native account selector; list/detail/edit/save/cancel/
back journeys; focused element; textarea text and selection; reading position;
navy `#15324f`, amber `#c08722`, white-card, system-body, Georgia-display skin;
same-origin static assets; and the existing note-save behavior. Polling must
never call `renderList`, `renderRecord`, `setEditing`, `focus`, or write the
textarea. An account-selector change updates local note state and reloads the
account-scoped note list; an export poll must not imitate that note journey. The
permitted sources do not establish that the selector attributes, changes, or
invalidates the export host-authorization scope, so it must never be used as an
export-status account identity or authorization-generation signal.

**Proposed conditional UI.** If the missing owner inputs are supplied, a later
producer may implement a persistent, fixed-size export-status slot outside both
`#notes-view` and `#detail`, as the first child of the existing `main`, so it
remains available through the existing list/detail journey without replacing
either view. It reuses the Field Notes ledger treatment: a small uppercase field
label, a static amber rule/mark, and quiet navy/muted text. It shows a bounded
summary rather than a variable-length job list; opaque job IDs remain internal
keys. An initial snapshot or multiple simultaneous changes uses a neutral
aggregate and makes no chronology claim from response ordering. After the owner
documents input bounds, a supplied label is rendered only as a text node/
`textContent`, never as HTML; bounded visual/live copy keeps the state/count
visible. A dedicated short `role="status"`, `aria-live="polite"`,
`aria-atomic="true"` node announces a real change once. No animation or
transition is proposed.

**Proposed conditional reading-position invariant.** The status slot would use
a stable block size at each responsive breakpoint and bounded copy so status
changes do not grow the page. A future rendered-browser procedure would evaluate
the initial structural change and later status changes against page/detail scroll
position and geometry; no such procedure has run in this planning-only packet.

The available frontend-design guidance was read from
`<study>/capabilities/frontend-design/SKILL.md`
(SHA-256 `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`).
Its applicable proposed direction is to reuse the product’s established visual
identity and add no new visual boldness: status is a factual field-note margin
cue, not a toast, animation, or redesign. These are conditional planning details,
not current implementation or rendered-proof claims.

**Actor, channel, state, and recovery agreement.** The host-authorized export
service owns jobs and the monotonic revision within its authorization scope. The
browser can own only a non-persistent presentation snapshot and a request/timer
handle. The browser reads only `GET /api/exports` over existing same-origin
HTTPS; it does not transmit a collection ID, operation ID, job action, download
request, or account identity. There is no socket, background worker, durable
local cache, or documented host-account event.

**Authorization-attribution prerequisite.** The controlled schema says that the
endpoint is scoped by host authorization, while the existing selector updates
local note state and reloads notes. No permitted source establishes that this
selector attributes, changes, or invalidates the export host-authorization scope,
exposes a browser-visible attribution identity, or signals a host authorization
change. Consequently this plan must not claim that a selector
transition changes the export scope, bind a response to Alpha or Beta, or use
`switchAccount` as a stale-response generation. Before implementation, the
host/API owner must document a reviewable authorization-attribution and
invalidation contract, plus a controlled fixture. The owner chooses the
mechanism; it must establish when the browser may accept a snapshot as current
for host authorization and what invalidates its transient presentation state on
an actual host authorization change. This W1 plan selects no field, token,
event, transport, or account mapping. The local selector is never that authority
and remains unavailable for export account attribution. Until the owner supplies
the contract, W1 implementation is blocked rather than guessing an account
mapping. A future permitted UI may use only generic "Current authorized export
status" copy once that contract is validated; it must not display a
selector-account label.

Conditional on that prerequisite, the observer follows the owner-defined
acceptance and invalidation semantics for its transient status state; it does not
derive them from the local selector. Foreground or the next visible polling
deadline refetches authoritative status under those semantics. One named
30-second timer schedules subsequent reads only while
`document.visibilityState === "visible"`; hiding the document invalidates/aborts
an in-flight generation and stops its timer. There is no socket, background
worker, or durable local cache.

The current fixture response contract is `evidence/controlled-status-schema.md`,
not API prose alone: a response has an integer `revision` and a complete `jobs`
array whose records carry stable `id`, user-facing `label`, and one of the four
stated statuses. It deliberately lacks the authorization-attribution and
invalidation contract above, JavaScript-safe revision bounds, a maximum job
count, explicit per-snapshot ID uniqueness, and ID/label size rules. It cannot
satisfy TC-W1-00 or the complete
normalizer contract, and W1 must not extend it on its own. Only after the
host/API owner supplies the updated complete contract may a future normalizer
use its documented JavaScript-representable monotonic revision encoding, job-array
and field-size bounds, per-snapshot opaque-ID uniqueness, stated status enum, and
label format. Invalid, duplicate, or over-limit values are schema failures before
rendering; the normalizer must not infer fields or fallback behavior from unrelated POST,
operation, or download routes. An invalid response then follows the
retained-data/retry path below.

Conditional on the owner-defined authorization-attribution contract, each request
uses its own visible-generation `AbortController`. That contract, rather than the
local selector, governs when transient status state may be accepted or must be
invalidated. A documented host authorization invalidation, replacement request,
hidden page, or superseding generation aborts or makes an older callback
ineligible. A complete snapshot is accepted only when the owner contract permits
it and its revision and jobs validate against the owner-supplied complete
response contract before comparison or rendering. The documented revision rule
then distinguishes newer, equal, and stale valid snapshots; an invalid value is
a schema failure, not an ordering input. Compare stable job IDs and statuses to
form the announcement; a sole new job or state transition
gets a concise label-based message, multiple changes get a neutral aggregate,
and unchanged polls stay quiet. A valid `failed` job is a server-owned domain
state and must not be presented as a successful export.

If a JSON, schema (including a revision that cannot be safely compared, duplicate
ID, or value outside an owner-supplied limit), or network failure occurs, retain
the last successful snapshot only while the owner contract still permits it for
the current host authorization and show one concise retryable message such as
“Export status could not be refreshed. Retrying while this page is visible.” The
visible scheduler retries without a busy loop; aborts and superseded responses
are silent. A documented authorization invalidation clears the snapshot and does
not retain data across host contexts. Client messages
reveal no server payload, stack trace, or opaque identifier. There is no
existing debug control in the product; the implementation should add no
always-on diagnostic dump.

## Concrete downstream implementation plan

1. **Prerequisite evidence** — before changing product files or bootstrapping
   feature tests, obtain the host/API owner’s documented authorization-attribution
   and invalidation semantics, complete response contract, and a controlled
   fixture that exercises initial acceptance and an actual host authorization
   change. The owner chooses the mechanisms; update the selected schema/contract
   only through that owner-authorized process. This W1 planning run has no
   authority to invent or edit it.
2. **`product/index.html`** — after that prerequisite is met, add the fixed
   export-status composition and its separate polite announcer as the first
   `main` child, outside the list/detail containers. It has an explicit labelled
   relationship and stable child nodes so a refresh changes only summary text;
   it adds no buttons for starting exports, selectors, download links, hidden
   command form, or selector-account label.
3. **`product/styles.css`** — style that composition with existing navy, amber,
   mist, paper, line, and danger tokens. Keep its narrow-layout behavior inside
   the current responsive rules, reserve the explicit slot height at each
   breakpoint, preserve visible keyboard focus for existing controls, and add no
   animation. Error text uses the existing semantic error treatment without
   changing slot/page/detail geometry.
4. **`product/app.js`** — after the owner contract is present, add a small
   export observer isolated from the note list/detail/save state. Before mapping
   or rendering, it validates the owner-supplied complete response contract,
   including its safe revision representation, job/field limits, unique opaque
   IDs, status enum, and label format. It keeps only the transient
   authorization-validity state that owner contract permits, plus revision, jobs
   keyed by validated ID, visible generation, controller, timer, and
   last-announcement signature; renders only the new compact
   summary/announcement nodes through text nodes or `textContent` with the
   contract's bounded presentation rule; performs `GET /api/exports`; gates
   stale callbacks; and starts/stops the visible-only schedule plus
   foreground/hidden listeners. It does not use the existing account selector as
   an export scope key. Existing note POST behavior remains untouched and is not
   part of W1.
5. **`product/docs/design.md`** — after the owner contract is present, append a
   compact W1 UI/interaction note that records the preserved editor/list premise,
   read-only snapshot channel, owner-defined authorization-attribution/
   invalidation and visibility/revision/retry rules, static accessible status cue,
   and the planned test
   locator. It remains product documentation, while this run evidence remains
   disposable.
6. **`product/test/export-status.test.js`** — after the owner contract is present,
   create a dependency-free `node:test` fixture using a fake DOM, deterministic
   fetch queue, visibility events, timers, and abortable requests. It will load
   the actual application surface rather than adding a framework or making a
   live target claim. Add a separate local rendered-browser procedure/fixture
   for the real scroll-offset invariant; if no authorized browser surface is
   available at that later stage, retain that rendered verification as an
   explicit gap rather than substituting the fake DOM result.

## Planned executable cases and checks

| Case | Stimulus and oracle | Planned check |
| --- | --- | --- |
| TC-W1-00 | Before implementation or feature-test bootstrap, the owner supplies both the authorization-attribution/invalidation contract and the complete response contract, plus a controlled fixture for first acceptance and a real host authorization change. A selector-only change is proven not to be that authority; without both owner artifacts, W1 remains blocked and no product observer is added. | Contract/fixture review before code |
| TC-W1-01 | Initial visible load follows the owner-defined first-acceptance semantics; a valid revision-42 response with one queued job is accepted, rendered with generic current-authorized label/state, and does not invoke a mutation path. | `node --test test/export-status.test.js` |
| TC-W1-02 | A newer valid revision while the owner contract permits the current snapshot changes a stable job from queued to running/complete; display updates once and the separate polite announcement names the relevant visible label/state. | Same focused test |
| TC-W1-03 | The owner-defined authorization invalidation semantics make a pre-change callback ineligible after a real host authorization change; the next authoritative read follows the owner contract and cannot resurrect stale status. A local selector-only change does not establish or invalidate host authorization or permit account attribution. The existing note transition may change detail/editor state; W1 does not override it. | Same focused test |
| TC-W1-04 | Start a visible request, hide the document, then resolve that request despite abort; it cannot update summary/live announcement/revision or restart a timer. Advance fake time while hidden, then foreground: no hidden poll occurs and the new visible generation makes one authoritative refetch. | Same focused test |
| TC-W1-05 | While the owner contract permits the current snapshot, a fetch/parse/schema failure follows a successful snapshot; visible data remains, concise retryable error is shown, and the next visible timer uses `GET` again. Once the owner supplies the complete response contract, malformed or unrepresentable revisions, duplicate opaque IDs, and values outside its documented limits are rejected before ordering/diff/render. A documented authorization invalidation clears retained data. Abort/supersession is silent. | Same focused test |
| TC-W1-06 | Empty complete snapshot and a valid `failed` job render as factual states without a download/action control or false success claim. | Same focused test |
| TC-W1-07 | Markup exposes an accessible concise status channel and the status CSS reserves the same block size at every applicable breakpoint with no animation/transition dependency. After the owner supplies label bounds, hostile markup-like and boundary-length labels are rendered only through text nodes/`textContent`; the documented bounded presentation keeps state/count visible without executable DOM content. A real local browser fixture sets known page/detail scroll offsets, then triggers a new job, a state transition, and retryable error; both offsets and detail geometry remain unchanged. | static assertions plus an available-browser procedure that measures offsets; otherwise explicit rendered-check gap |
| TC-W1-08 | During editing while the owner contract permits the current snapshot, a successful status refresh or retryable fetch error changes only export-status nodes; textarea value, selection, active focus, editor mode, and list/detail state remain unchanged. | Same focused test plus rendered-browser procedure |
| TC-W1-09 | Once the owner supplies the job bound, a valid boundary response is reduced to the bounded summary rather than rendering an unbounded list; an over-limit response follows the TC-W1-05 schema-failure path. The fixed status slot and page/detail scroll offsets remain stable. | Same focused test plus rendered-browser procedure |

Harness lifecycle: only after TC-W1-00 verifies both owner artifacts and their
controlled fixture may each Node case construct an isolated DOM/fetch/clock
fixture. Its independent oracle is rendered text,
live-announcement text, absence of executable label markup, the owner-defined
bounded presentation, recorded fetch arguments, owner-contract acceptance and
invalidation outcomes, accepted documented revision values and rejected
duplicate/out-of-contract schemas, timer state, and preserved editor state;
teardown aborts outstanding requests, clears
timers/listeners, and restores globals. The scroll cases also
use an isolated local rendered-browser fixture with a known page and
`.detail-scroll` offset; its oracle records both offsets and detail geometry
before/after each status update, then tears down the fixture. It is stateless and
does not share a server, account, storage, or browser profile. The focused
command is the case file above; smoke remains `node --check app.js`; full local
suite after authoring is `node --test`. Existing baseline output has zero tests,
so these commands are **planned**, not passed W1 feature evidence.

## Dependency audit and disposition

- **Claim:** a person can observe current account-scoped export state in the
  existing Field Notes surface without disturbing notes or requesting an export.
- **Needs:** a documented read-only complete schema with a JavaScript-representable
  monotonic revision rule, job/field bounds, and per-snapshot unique opaque IDs;
  owner-defined host authorization-attribution and invalidation semantics;
  same-origin fetch; visible lifecycle; static accessible status surface; isolated
  local test harness. The current sources supply only the incomplete schema, fetch,
  lifecycle constraints, DOM/CSS, and Node 25.9.0; they do **not** supply the
  required complete schema or authorization-attribution contract. No persistent storage,
  server runtime, socket, collection selector, operation endpoint, or remote
  environment is needed once that owner contract exists.
- **Supply/Pull:** once the owner contract is supplied, the server owns job truth
  and defines how W1 may attribute and invalidate its transient snapshot; W1’s UI
  is the sole consumer. Note editing and W2 drafts do not consume or supply export
  status, so no dependency edge is added to W2. Foreground refetch repairs missed background
  changes without claiming push delivery.
- **Resolve:** hold W1 test-bootstrap and implementation until the host/API owner
  supplies the authorization-attribution/invalidation contract, complete
  revision/limits/unique-ID schema, and controlled fixture. The current plan can
  preserve the read-only UI/test design but cannot safely connect export snapshots
  to host authorization, validate response ordering and bounded data, or recover
  cross-context responses.
  Preserve the separate known gap that this controlled local fixture cannot
  verify a live account, deployment, or consumer endpoint. Keep W2 blocked
  because target facts explicitly report no client persistent storage and no
  draft API.

This plan uses ShipLoop’s embedded planning adaptation; no source-aware native
Backchain card was selected or invoked. The automatic Improve child, not this
plan, must independently challenge scope, state ownership, test adequacy, and
the live-target limitation before the parent can advance.
