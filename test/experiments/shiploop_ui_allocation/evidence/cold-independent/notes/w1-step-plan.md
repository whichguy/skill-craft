# W1 step plan — remote export status

Action: `nav-bec327c2f88c48419ac498e62bd15d2f` (`step-plan`), owner `W1`.

This is a planning record only. No product source, test, deployment, account, or
remote service state was changed. The next ShipLoop action is the separately
bound Improve review; it has not run here.

## Scope and retained requirements

The maintained product requirement is the Field Notes extension in repository
`README.md:1-5`: preserve the existing list/detail/edit/save/cancel/back
journeys and navy/amber visual identity, keep pending local state distinct from
server-confirmed content, and do not assume the historical environment. The
repository knowledge index is `SHIPLOOP.md:1-5`.

W1 adds only account-authorized remote export status using the fixture APIs in
`docs/api.md:1-2`: list exports, start an export, reconcile a lost confirmation
by `clientOperationId`, and obtain a completed job's same-origin download path.
It must preserve the UI identity and stable textarea described by
`docs/design.md:1-5`; it does not implement persistent drafts. W2 remains
separate future work.

The durable state was read at `run/state.md:1-280`. Its earlier preparation,
test-strategy, plan, and select-work entries explicitly identify themselves as
synthetic fixture predecessors. The projected test-strategy result
`run/results/nav-8bb0f96f6f8a48dcb1693830b724b251.md` and prior Improve receipt
`run/improve/nav-76ae377e5608481196c2c088c874a742/receipt.md` were absent when
checked, so they are not reused as test or review evidence. There is no current
item test-decision source before this first W1 producer.

## Actual baseline observations

The repository contains only the static product files listed below; no
`AGENTS.md`, package manifest, test directory, test runner configuration, or
test source was discovered. `git -C product rev-parse --is-inside-work-tree`
exited 128 with `fatal: not a git repository`; therefore this controlled static
fixture has no current Git revision to use as a baseline.

| Observation | Actual command and result | Planning implication |
| --- | --- | --- |
| Target environment | `env DEVELOPER_DIR=/Library/Developer/CommandLineTools python3 -B scripts/probe_environment.py` printed `{"client_persistent_storage":"unavailable","draft_api":false,"observation_scope":"controlled fixture target facts; not a live deployment","observation_sha256":"40a3900ae08cf109734f411f62c8a89dbd5fae84c5f04d127ff000ea3038c878","script_src":["self"],"server_runtime":false,"style_src":["self"],"target":"fieldnotes-embedded-v2","websocket":false}`. | W1 may use same-origin HTTPS request/response only. It may not add draft storage, a server process, a WebSocket/subscription, inline code/style, external CDN assets, or a deployed-service claim. |
| Existing smoke route | `node --check app.js` exited 0 with no output. | This is a current source-syntax baseline only; it does not exercise API or browser behavior. |
| Available local runner | `node --version` printed `v25.9.0`; `node --test --help` exited 0 and lists `--test launch test runner on startup`. | Node's built-in runner is available for a future dependency-free focused suite, but no tests have yet been authored or run. |
| Target / delivery boundary | `docs/platform.md:1-4` says the deployed artifact is static, same-origin only, has no server runtime or persistent WebSocket, may suspend while hidden, and has no remote deployment access in this experiment. | Local source checks and a future local API fixture cannot prove a deployed target or real service behavior. |

Current input digests recorded from `shasum -a 256`:

| Input | SHA-256 |
| --- | --- |
| `product/README.md` | `4faae9b31e39d5da0967ce4e5482f96a5277f8c9bb5769a58dc7d9b5f602b604` |
| `product/SHIPLOOP.md` | `b570909d3f879ab80462a5fff2c313da77bc02f7f988654e31d6e8932e8918bf` |
| `product/docs/design.md` | `f3e6dce3dcab93d5d0b7fd294d9ab908c116e5416d7456b568ba01025e9699f9` |
| `product/docs/platform.md` | `b8dfe6ff0a442cfe5a13947afe8bdc7d5bf4eb77aa66cd6d39fff1b0adba8007` |
| `product/docs/api.md` | `862db25f3187bdf02a2d1da27bd041faca855e3ff4b3a235e153cda67dd37a27` |
| `product/scripts/probe_environment.py` | `c54f52e5bd7f8a5801dee4f336ed2fe4989ffdfd035c30340835d0883ff41ec4` |
| `product/host-observation.json` | `40a3900ae08cf109734f411f62c8a89dbd5fae84c5f04d127ff000ea3038c878` |
| `product/index.html` | `f52423358a46b6210774533586602fb75267deb631129ba9bf96293e68f88213` |
| `product/app.js` | `729f0db397fe3b0eaae3fadff9de10facd82b071fb7bbe00a95dcb9d9b5f8ac2` |
| `product/styles.css` | `cd3106112e5ddff749af99d9e3de730274f7786ccde2a2c4e75c172753b646bf` |
| Selected frontend-design guidance | `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd` |
| Selected ShipLoop card | `be8340413f5ad72792da14d5f6719a98a8cbebc89a8531ad139e2c5dbc52c269` |

## Design basis and interaction agreement

The applicable design baseline is the existing Field Notes reading surface:
the native account selector, note list, stable textarea and controls remain
where they are; navy `#15324f`, amber `#c08722`, white cards, system body text,
Georgia headings, keyboard focus, touch behavior, narrow layout, reading
position, and draft text are preserved (`docs/design.md:2-5`,
`index.html:21-82`, `styles.css:4-19`, `styles.css:369-420`).

The selected design guidance is
`<study>/capabilities/frontend-design/SKILL.md`
(SHA-256 above). Its applied direction is a restrained, subject-grounded
“dispatch slip” export panel in the existing notes view: one compact white
record with the existing amber rule and a Georgia status heading, rather than a
generic dashboard or new visual system. The panel's single job is to let the
current account see what is happening to a collection export and download it
only when the service reports completion. Plain, consistent UI copy will name
the actual action and recovery, such as “Request export,” “Checking export
status,” and “Export could not be confirmed. Check status before trying again.”

Components: retain `#account`, `#note-list`, `#detail`, textarea, and the
existing action bar; add one account-scoped export panel with a status summary,
an accessible `role=status` live region, an explicitly named request/check
control, and a download link that is absent until an authoritative complete
response supplies a validated same-origin path. Do not reuse the note save
status as a second, ambiguous export channel.

Interaction and state ownership: the person initiates a request; the host owns
account authorization; the service independently owns export jobs; the browser
owns only presentation state, the active `clientOperationId`, abort handles,
generation/timer state, and the currently rendered snapshot. The request path
is browser `POST /api/exports` → durable server acceptance/response → browser
status display. A lost confirmation is not success: while the page still has
the same in-memory operation identity, reconcile it through
`GET /api/operations/:clientOperationId`; unresolved results remain visibly
unconfirmed. `GET /api/exports` provides a foreground/account-change snapshot;
`GET /api/exports/:jobId` refreshes a known job while the page is visible. The
app must stop timers while hidden, reconcile on `visibilitychange` when visible,
and treat any future notification only as an invalidation cue followed by a
GET—there is no subscription to add.

On account switch or superseding load, abort the old request, advance a
generation/token, clear account-specific presentation state, and ignore old
callbacks before they can render. On a page crash or reload after server
acceptance but before the browser processes its response, there is no permitted
persistent browser store for the operation ID. The UI must never claim success
from that lost in-memory state; after reload it can display only statuses
actually returned by `GET /api/exports`. This is a recovery boundary, not an
excuse to add draft or operation persistence.

Skin and motion: reuse the existing tokens, card edge, focus treatment,
`aria-live` status, and narrow-layout flex rules. A status change can use a
brief amber accent only if it conveys a real state transition; under
`prefers-reduced-motion` it is static and the text remains the complete cue.
The visible status must persist long enough to give recovery direction rather
than being a transient toast. No new font, framework, CDN, inline code/style,
or animation library is needed.

## Dependency audit and unresolved prerequisite

**Claim.** The UI can request and truthfully display an authorized collection
export's current state without changing existing note-editing behavior or
depending on draft persistence.

**Needs / supply.** `docs/api.md:2` supplies the API routes, server-owned job
state, durable acceptance boundary, same-origin download rule, visible polling,
and foreground reconciliation. `docs/platform.md:1-4` supplies the static
same-origin runtime and the no-WebSocket/no-deployment boundary. Existing
`app.js:4-14`, `app.js:37-43`, `app.js:125-141`, and `app.js:288-310` supply
local state, a UUID-capable operation helper, response error handling, and an
account-switch abort pattern. The account selector itself only supplies
`alpha`/`beta` values (`index.html:21-27`); it is not documented as a collection
identifier.

**Unresolved.** `POST /api/exports` requires `collectionId`, but none of the
current authoritative sources defines a collection model, maps an account or
note to a collection, or specifies the collection ID carried by
`GET /api/exports`. The same short API prose does not define the list-item,
operation-reconciliation, or job-response shape needed to identify a job,
interpret status/terminal states and revisions, or locate the completed download
path. Equating account name, selected note ID, or a free-text input with
`collectionId` would invent a service contract and could target the wrong export;
inventing JSON fields from the word “status” would do the same for display,
polling, and a fake test fixture. Implementation must first obtain and record
the authoritative collection-selection/data-source and response contracts with
their account-scope behavior. This does not prevent this step-plan producer from
completing; it blocks the future API-integration behavior that depends on those
contracts. A fake “valid collection” or response cannot stand in for a source
or make the request flow implemented, testable against the product contract, or
passed.

**Pull / safety.** The downstream browser needs a stable collection choice to
form the POST, a job ID or a reconciled operation result to poll, and a
same-origin completed path before presenting a download. The server remains
the only owner of job state. No separate persistence, service, subscription,
or draft producer supplies this need. W2 is not a supplier or consumer for W1.

### Pre-code criterion and prerequisite matrix

The synthetic predecessors supplied no accepted `T-` catalog or exact
`produces` strings. The following **plan-local** trace IDs make this W1 plan's
criteria and test dependencies explicit; they do not create new accepted
product requirements, report implementation, or replace the README/API
contract. Every listed case is planned and unrun. A later source that resolves
the collection model must be reconciled with this matrix before test authoring.

| Trace / exact planned produces | Requirement and prerequisite basis | Planned case / intended observation |
| --- | --- | --- |
| `T-W1-00` — “A repository-owned, account-scoped source names the authorized `collectionId` and the list/operation/job response fields needed for stable job identity, status/terminal state, revision, completed download path, and empty/unauthorized behavior; otherwise each affected API behavior remains explicitly blocked.” | `docs/api.md:2` requires `collectionId` and names high-level routes, while `docs/platform.md:2` says the host owns account identity; neither current source supplies the collection mapping or response shapes. | `EXP-000` read-only integration-contract gate; inspect the future source and reject inferred account/note/free-text mappings or fabricated JSON fields. It gates the API-dependent observations below. Purely local preservation/storage checks remain separately planned and unrun because no test harness exists; they are not made green by this gate. |
| `T-W1-01` — “The current account displays only a current `GET /api/exports` snapshot with truthful empty/error state and no invented collection identity.” | Preserve the Field Notes UI and use the existing same-origin API only. | `EXP-001` list/empty/error display. |
| `T-W1-02` — “A validated collection request uses one `clientOperationId`; ambiguous confirmation is reconciled with that same ID and never displayed as success while unresolved.” | `docs/api.md:2` defines durable acceptance before confirmation and the operations recovery route. | `EXP-002` accepted request and `EXP-003` lost confirmation. |
| `T-W1-03` — “A known export is polled only while visible, refreshed on foreground, and exposes a download path only when the server reports complete and the path is same-origin.” | `docs/api.md:2` plus the static host's hidden-page boundary. | `EXP-004` visible polling/foreground reconciliation and `EXP-005` completion link. |
| `T-W1-04` — “Account changes and stale callbacks cannot render an old account's export state; reload cannot recover an in-memory operation ID or claim an ambiguous POST succeeded.” | Account identity remains host-owned; current v2 storage is unavailable and no draft endpoint exists. | `EXP-005` stale/account isolation and `EXP-006` unavailable storage/reload boundary. |
| `T-W1-05` — “Export-status work preserves the existing note list/detail/edit/save/cancel/back journeys, textarea state, focus/touch/narrow layout, and navy/amber identity.” | `README.md:3` and `docs/design.md:3`. | `EXP-007` preserved note journey plus an authorized future browser accessibility smoke. |

## Bounded implementation plan

1. **Resolve the collection and response contract before API integration.**
   Obtain a repository-owned API or product-contract update that states where a
   current authorized `collectionId` comes from, its relationship to the
   selected account, and its empty/unauthorized case. It must also define the
   list, operation-reconciliation, and job-response fields used for collection
   and job identity, status/revision interpretation, terminal/failed behavior,
   and the completed same-origin download path. Keep the explicit unresolved
   result if that source cannot be provided; do not add a guessed mapping,
   guessed JSON field, or new server endpoint. If an API change is needed, it
   is outside this static-client step and needs separately authorized work.
   Record this as `EXP-000` before authoring or running a fake API fixture: a
   fake may mirror an already-authoritative contract for diagnosis, but may not
   supply or validate the contract itself. A later layout-only/local change
   would still need its own preservation evidence and cannot be called remote
   export-status coverage without the API contract.

2. **Add the export surface without disturbing the note surface.** In
   `index.html`, place the dispatch-slip panel in the notes view beside the
   account-scoped list rather than inside the note editor. It receives stable
   IDs for the status live region, request/check control, and conditional
   download link. Preserve current focus paths: the account selector still
   moves to its account's list; a completed/download state must not steal focus;
   keyboard and touch can activate the export control; account changes return
   the user to an empty/loading export panel for the new account.

3. **Add isolated export lifecycle logic in `app.js` (or a same-origin helper
   only after browser-module compatibility is verified).** Reuse `operationId`,
   `responseJson`, `AbortController`, and generation checks rather than adding a
   framework. Introduce only state necessary for the export list, known job,
   pending client operation, controller(s), visibility-aware timer, and a
   monotonically advancing generation. Keep testable request/normalization and
   status-transition functions separated from DOM writes; preserve causal error
   context internally without showing response bodies or a duplicate stack to
   the user. If a bounded existing debug control is found during implementation,
   use it for redacted operation ID/phase/status changes; none is presently
   documented.

4. **Implement the service transition rules.** On account entry/foreground,
   fetch `GET /api/exports` and render only the current generation/account.
   On a validated collection selection, create one `clientOperationId`, POST
   `{collectionId, clientOperationId}`, and show truthful pending/accepted
   state. If the POST response is missing or ambiguous, query
   `/api/operations/:clientOperationId` using that same in-memory ID; do not
   manufacture a second operation or call it successful until it resolves.
   Poll a known incomplete job only while visible, stop when complete/failed or
   hidden, and restart from a fresh snapshot on foreground. Validate a completed
   download path against the same origin before enabling the link. A controlled
   retry/recovery control must keep the uncertain outcome visible; it must not
   overwrite it with a success message.

5. **Handle failure and identity boundaries.** Treat invalid/missing collection
   data, HTTP/JSON failure, ambiguous confirmation, missing job ID, stale
   callback, account change, hidden page, and failed/noncomplete job as distinct
   states. Abort and invalidate old work on account change; never render Alpha
   status under Beta. Do not retain a client operation ID across reload. Preserve
   the existing textarea's working text, edit mode, save/cancel/back behavior,
   and note API flow while the export panel updates.

6. **Document only confirmed behavior after implementation.** Update the
   maintained README/design/API contract narrowly with the collection source,
   in-page status/recovery behavior, polling/foreground boundary, download
   availability, and the intentional lack of draft persistence. Do not claim a
   deployed integration, browser notification, or persistent draft recovery
   based on a fixture or local test.

## Planned checks and test lifecycle

No behavior suite existed at this baseline. At the test-author step, add the
smallest dependency-free Node built-in suite (proposed
`tests/export-status.test.js` plus a testable seam in the static app) rather
than installing a framework. Each case creates its own fake fetch responses,
visibility state, timer scheduler, account, and DOM/view adapter. Its teardown
aborts outstanding controllers, clears timers, and asserts no timer or response
can update another case; the next run repeats the same focused selector.

| Planned case | Stimulus and independent oracle | Setup / teardown / route |
| --- | --- | --- |
| `EXP-000` integration-contract gate | A repository-owned source must define the current authorized `collectionId`; collection/job identity; list, operation, and job response fields; status/revision/terminal meaning; completed download path; and empty/unauthorized behavior. Missing facts block only the corresponding API-dependent assertion; account name, note ID, free text, and fabricated JSON fields are rejected as invented mappings. | Read-only source reconciliation with `T-W1-00`; no fake API response, product edit, or executable remote-API coverage is claimed while the source is absent. |
| `EXP-001` list and empty/error display | After the list-response portion of `EXP-000` is supplied, a fake `GET /api/exports` response that mirrors it determines exactly the rendered status/empty/error text; no response body is treated as success. | Fresh account/view and contract-shaped fake fetch; teardown clears controller. `node --test tests/export-status.test.js --test-name-pattern='EXP-001'`. |
| `EXP-002` request and accepted job | After `EXP-000` supplies collection and POST-response fields, a request contains that authoritative `collectionId` and one generated `clientOperationId`; pending UI is disabled and the returned `jobId` is the only job later polled. | Fresh fixture that mirrors the already-resolved source; teardown aborts and clears timer. Focused Node selector, then suite membership. |
| `EXP-003` lost confirmation | After `EXP-000` supplies the operation-response shape, a rejected/ambiguous POST is followed by `GET /api/operations/:clientOperationId` with the same ID. A still-unresolved result remains unconfirmed and offers recovery, never success. | Contract-shaped fake response sequence; teardown asserts no duplicate POST. |
| `EXP-004` visible polling and foreground reconciliation | After `EXP-000` supplies job identity/status/terminal semantics, a known incomplete job is polled only while visible. Hidden state clears the timer; visible re-entry first refreshes the list and then current job state. | Contract-shaped fake clock/visibility events; teardown asserts no residual scheduled work. |
| `EXP-005` stale/account isolation and completion link | After `EXP-000` supplies list/job identity and completed-path fields, a late Alpha callback after switching to Beta is ignored. Only a complete job with an allowed same-origin path exposes a download link. | Separate account fixtures and deferred promises; teardown aborts both stale paths. |
| `EXP-006` unavailable storage boundary | The v2 probe remains unavailable/false; export logic performs no `localStorage`, draft API, server-process, or subscription action. A reload has no retained client operation ID and cannot claim the ambiguous POST succeeded. | Read the controlled probe and exercise a fresh controller; no shared persistent fixture. |
| `EXP-007` preserved note journey | Beginning or resolving export status does not change the textarea's value/read-only state, note save controls, back behavior, or account switch rules. | Fake note DOM plus export responses; teardown restores the fresh view. |

Planned commands after tests exist:

```sh
env DEVELOPER_DIR=/Library/Developer/CommandLineTools python3 -B scripts/probe_environment.py
node --check app.js
node --test tests/export-status.test.js
node --test
```

The first two commands have run only on the pre-change baseline above. The last
two are planned checks, not results; `node --test` currently has zero selected
tests and is not behavior coverage. `EXP-000` is a prerequisite disposition,
not a green test: while its authoritative collection and response contracts are
absent, the list/request/reconciliation/polling/download assertions remain
planned and unrun. The storage and preserved-note cases are also unrun because
the baseline has no test harness; that is a separate missing-coverage fact, not
proof that `EXP-000` blocks every local assertion. A browser/manual accessibility smoke is
also planned only if an authorized same-origin fixture can supply the API and
the resolved collection mapping: verify keyboard focus, live status text,
pending/failed/complete/recovery states, narrow layout, hidden→visible
reconciliation, and account switch while a response is delayed. It would prove
only that controlled fixture, not a deployment.

## Explicit unavailable boundary

The current controlled target is `fieldnotes-embedded-v2` with
`client_persistent_storage: unavailable` and `draft_api: false`; its observation
hash equals the current `host-observation.json` hash above. This is current
fixture evidence, distinct from the historical v1 storage statement in
`docs/design.md:4-5` and distinct from a real deployment. W1's remote export
status flow uses the documented API and may proceed after the collection-ID
contract is supplied. Persistent account-scoped draft recovery remains W2 and
is neither implemented nor represented as available here.

## Progress snapshot at this producer boundary

- Done: seven preparation stages are only the durable synthetic fixture entries;
  no actual predecessor producer or Improve cycle was used as evidence.
- Current: W1 `step-plan`, action `nav-bec327c2f88c48419ac498e62bd15d2f`.
- Pending: W1 test-spec through carry-forward remain script-owned future stages;
  W2 remains queued and out of scope.
- Blocked: navigator state remains active, but future W1 implementation is
  blocked on the missing authoritative `collectionId` source. No target/deployment
  or real API invocation was attempted.
