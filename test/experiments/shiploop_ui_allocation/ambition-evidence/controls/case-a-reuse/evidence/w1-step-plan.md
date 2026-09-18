# W1 step plan — account-scoped export activity companion

## Scope, starting evidence, and limits

This plan covers W1 only: a read-only export-status companion for the existing
Field Notes page. It does not plan a new export request, a download, storage,
draft recovery, a server/socket, a new account selector, or a change to the
existing list/detail/edit/save/cancel/back journeys. W2 remains blocked on its
separate storage contract.

The controlled contract is the authority for this item:

- The only new request is `GET /api/exports?accountId=<selectedAccountId>`.
  It is allowed only while the document is visible and after foreground
  recovery. The host, rather than the selector, authorizes the account.
- A usable response contains the same `accountId`, a monotonic integer
  `revision`, and `jobs` with only `queued`, `running`, `complete`, or
  `failed` states. There is no percent, timestamp, elapsed time, delivery
  confirmation, download, operation reconciliation, notification, or storage
  data to display.
- A late generation, wrong echoed account, or older revision is ignored. An
  equal revision is a heartbeat and must not replay a success cue. Changing
  accounts clears the old activity snapshot before the next matching response.
  A `403` clears it and never leaves another account's snapshot current.
  Other retrieval or malformed-data failures retain only a valid same-account
  snapshot, visibly marked stale, with a read-only refresh action.

Relevant sources and revalidation points:

- `evidence/request.md:3-22` and
  `evidence/controlled-status-contract.md:3-25` define W1's current product
  scope and status semantics.
- `evidence/tooling-facts.md:3-35` records the self-only static target,
  available DOM/CSS/live-region/reduced-motion primitives, no package record,
  and the observed test commands.
- `product/index.html:15-89`, `product/app.js:4-14,143-174,288-312`, and
  `product/styles.css:4-20,147-179,369-420` are the existing account, request,
  focus/status, navy/amber, responsive, and reduced-motion foundations to
  preserve.
- The UI basis is the frozen ShipLoop behavioral contract,
  `package/shiploop/references/behavioral-requirements.md:86-261,263-330`, and
  the optional frozen `frontend-design` card at
  `<study>/capabilities/frontend-design/SKILL.md`
  (SHA-256 `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`).
  The card's useful guidance here is to let Field Notes' existing folio
  language and intentional hierarchy carry one distinctive detail, while
  keeping controls literal and failures directional.

The starting controlled checks were rerun before planning:

- `evidence/w1-probe-environment.txt`: `fieldnotes-embedded-v2`, self-only
  scripts/styles, no server runtime or WebSocket, and unavailable client
  persistent storage. This is fixture evidence, not a live deployment.
- `evidence/w1-node-check.txt`: `node --check product/app.js` exited 0 with no
  diagnostic output.
- `evidence/w1-node-test.txt`: `node --test` exited 0 but discovered 0 tests.
  That is missing coverage, not feature validation.

## Design decision: evolve the existing Field Notes primitives

The desired experience is a small, persistent **Export activity** folio just
inside `main`, before the mutually exclusive notes and detail sections. It is
always available in the notes-list, read-detail, and edit-detail states without
opening a new journey or taking focus from the editor. Its compact header gives
an at-a-glance, account-scoped status; an in-place list gives the retained
failure/context details when they exist; and one literal `Refresh status`
control re-reads the allowed endpoint. The visual signature is a restrained
amber "activity rule" beside the state summary, not a dashboard, timer, or
fictional progress meter.

| Alternative | Rough effort, conditional assumptions | Benefit and constraints | Decision / probe |
| --- | --- | --- | --- |
| Reuse unchanged status text (`quiet-message`/`save-status`) | XS–S, roughly 0.5–1 engineer-day assuming only a list-view line | Reuses every primitive, but cannot persist failure context, expose per-job hierarchy, remain useful in detail/edit, or make stale state actionable. | Rejected as insufficient for the requested companion. |
| Evolve the native DOM/CSS and `app.js` path | M, roughly 2–4 engineer-days assuming the supplied response shape remains stable and a small pure helper is testable with Node's built-in runner | Supports the full status/revision/account contract, accessible state hierarchy, current skin, CSP, narrow layout, and no new dependency. Maintenance stays in the one existing static artifact. | **Selected.** First implementation check is the existing Node route plus a controlled browser procedure when a target-compatible facility is available. |
| Upgrade to a package/framework status component (for example, a version-pinned Bootstrap/Material or Web Component candidate) | L+, at least 4–7 engineer-days only if an approved package, build, asset, CSP, and target path are established | Could provide prebuilt patterns, but no package/version/build record exists; it would add DOM ownership, loading, accessibility, licensing, and embedded-CSP risk without a demonstrated capability gap. | Do not select or install it. If a later request establishes a real gap, probe the built same-origin artifact under the deployed CSP and target lifecycle before reconsidering. |

The estimate is deliberately assumption-bound: no target polling budget, browser
harness, or live endpoint is supplied. A local preview would not prove either
the static target or remote service semantics.

## Three UI planning views

### Components and visible states

`product/index.html` will add one semantic `section` outside both
`#notes-view` and `#detail`, with a labelled heading, a stable summary/status
node, a real `Refresh status` button, and a jobs list. It will remain mounted as
the existing list/detail `hidden` flags change, so the companion appears in all
three existing user contexts: selecting a note, reading it, and editing it.
It does not replace either current live region or action bar.

`product/app.js` will render the following state hierarchy from the contract;
all job labels are assigned with `textContent`, never parsed as markup.

| Presentation state | Contract-backed visible content | Available action and cue |
| --- | --- | --- |
| Initial/refreshing, no snapshot | `Checking export activity` with component-local `aria-busy` | The stable refresh button is disabled in place while its one request is active. |
| Empty valid snapshot | `No export activity reported for this account` | Refresh remains available; no invented invitation to start an export. |
| Active valid snapshot | `Running` before `Queued`, then the named jobs and counts | A narrow amber activity rule may pulse only for a newly accepted visible change. |
| Failed valid snapshot | `Needs attention` and failed jobs appear ahead of active/complete jobs; each remains visible after the announcement | `Refresh status` checks the read model only. It never says retry, resend, download, or that a failed export was fixed. |
| Complete-only valid snapshot | The count of **reported jobs** is complete | The word `complete` reflects the supplied status only; it does not claim delivery, download, or user receipt. |
| Stale valid same-account snapshot | A persistent `Status may be stale` qualifier and a concise retrieval error sit with the last accepted jobs | Refresh is focus-preserving. Stale is used for network/non-403 HTTP/malformed-data retrieval failure only, never to keep another account's data. |
| `403` or no valid snapshot after failure | `Export activity cannot be read for this account` (or an equally literal malformed/unavailable message) and no old jobs | Refresh remains a GET-only recheck; the card does not present a stale cross-account result. |

Mixed job states use the same severity order—failed, then running, then queued,
then complete—while retaining every supplied job so a transient notice cannot
hide the next useful action. Each row has a visible status word; color supplements
that text and never carries the meaning alone. No state includes percent,
duration, time, accepted operation, download, or "success" language not supplied
by the GET response.

### Interaction model, ownership, and recovery

The page is an observer. The host owns the selected/authorized account; the
service owns export jobs and revisions; the client owns only an in-memory,
account-generation-scoped rendering cache. There is no outgoing domain command,
durable draft, subscription, background worker, or socket.

Add a small `exportActivity` branch to the existing page state, separate from
the notes' shared `requestGeneration`, with: current account generation,
accepted revision, last valid jobs/snapshot, stale/error marker,
`AbortController`, scheduled visible-page refresh handle, and a compact
announcement/change key. A dedicated generation avoids a list or detail request
accidentally invalidating export activity and vice versa.

Implement a single request/reconciliation path with these guards:

1. Capture `state.account` and increment the activity generation before
   `fetch('/api/exports?accountId=' + encodeURIComponent(account))`. Do not
   issue it when `document.visibilityState !== 'visible'`.
2. Validate the successful JSON shape, echoed account, integer revision, and
   every job/status before touching the UI. Accept it only if the controller is
   current, its generation still matches, and the captured and echoed account
   both equal the current account. Reject lower revisions. For an equal revision,
   retain the existing display and suppress an animation/live success cue. For a
   higher revision, replace the same-generation snapshot and compute a visible
   change key from job id/status/label differences; a revision bump with no
   visible difference updates the held revision quietly.
3. On account change, increment the activity generation, abort the active
   activity request, clear its scheduled work and all old snapshot/error/stale
   data, render the new account's initial state, then request only for the new
   account if visible. A `403` performs the same clear-for-current-account
   behavior before rendering the authorization error. This makes late Alpha data
   inert after a switch to Beta.
4. On a network, non-403 HTTP, JSON, or schema failure, keep the last valid
   snapshot only when it belongs to the current generation/account and mark it
   stale. If none exists, render an unavailable error without fabricated status.
   The recovery control calls the same read path and never changes a job.
5. Use one visible-page, non-overlapping `setTimeout` cadence (initial proposal:
   30 seconds after a request settles, subject to a service load/rate-limit
   recheck) rather than a background `setInterval`. On hidden, abort/clear the
   activity work; on `visibilitychange` back to visible, immediately reconcile.
   Manual refresh shares this path. This is the only planned connection
   lifecycle; no socket/reconnect semantics are implied.

Concrete late-read trace: Alpha's generation 7 requests revision 14. Before it
returns, the person selects Beta. The app increments to generation 8, clears the
folio, aborts Alpha, and starts Beta's request. If Alpha nevertheless resolves,
its generation/account checks discard it. A valid Beta revision 3 renders only
Beta jobs. A second Beta revision 3 heartbeat leaves the rows and live region
quiet; a later revision 4 with a job changing from `queued` to `running` updates
the row once and may show the bounded changed-state cue.

Automatic updates never call `focus()`, change the selected note, toggle
editing, reset the textarea, or move the reading position. The refresh button
is not replaced while it is disabled, so a person who activated it keeps focus;
the component's short polite live message announces a material update/error
rather than each poll. A collapsed/compact jobs detail remains at its current
open state during automatic refresh to avoid surprise layout expansion.

### Branding, skin, motion, and accessibility

`product/styles.css` will extend the existing token system and card geometry:
Georgia remains the restrained display face, the system font remains body/UI
text, navy remains the structural color, amber is the activity rule/focus cue,
and the existing danger token labels failure. The companion uses the current
white card, thin line, modest border radius, and narrow responsive stack. On
small screens, its summary and refresh action stack like the current action bar;
it does not introduce a second layout system.

Only a higher accepted revision with a visible queued/running/new/status change
gets one short amber rule/marker transition. That cue means “this displayed
snapshot changed,” not an export was delivered or successful. Under
`prefers-reduced-motion: reduce`, the transition/keyframe is removed and the
same change is conveyed through the static marker, updated text, and polite
status. Repeated equal heartbeats and foreground recovery do not replay it.

The markup will use a labelled `section`, semantic list, visible status words,
one component-local `role=status`/`aria-live="polite"` summary, `aria-busy` only
while reading, and the existing keyboard focus style. The plan's rendered check
will cover keyboard operation, focus preservation, contrast of each state,
screen-reader announcement restraint, and both motion preferences.

## Planned files and implementation order

| Target | W1 change |
| --- | --- |
| `product/index.html` | Add the persistent semantic companion before the existing notes/detail switch, with stable status, refresh, and jobs-list hooks. Preserve all existing ids and journeys. |
| `product/app.js` | Add the small activity reducer/validator and DOM controller; separate activity generations/controllers from note requests; wire account change, initial visible load, manual refresh, and `visibilitychange`; keep the read-only GET boundary and all stale/403/revision guards. Keep the testable response/reconciliation helpers in this existing file, exposing them only under Node's existing runtime guard so no browser framework/module system is introduced. |
| `product/styles.css` | Add companion variants, severity hierarchy, one bounded changed-state animation, responsive placement, and the reduced-motion override using current tokens and focus rules. |
| `product/test/export-activity.test.js` | Add Node built-in tests against the production-owned pure helpers in `app.js`; no Playwright, JSDOM, dependency, or separate harness. |
| `product/docs/design.md` | Record the W1 component/interaction/skin basis, all state/recovery rules, and the no-cross-account invariant. |
| `product/docs/api.md` | Add a clearly scoped W1 consumer note for the controlled account query, echoed account/revision, and read-only/stale semantics without broadening the service contract. |
| `product/README.md` | Update the local validation note once `node --test` has real activity cases; leave W2/draft claims unchanged. |

Implementation sequence: first add the pure validation/reconciliation seam and
its RED/green Node cases; then add the stable markup and controller; then skin
and reduced-motion behavior; then documentation and the focused checks. Keep the
existing `SHIPLOOP.md` index unchanged because it already points to `docs/design.md`
and `docs/api.md`.

## Verification plan and unresolved target checks

Use the existing runner, not a parallel test stack. `product/test/export-activity.test.js`
will make `node --test` cover at least:

1. valid matching-account snapshots and state-specific ordering/counts;
2. wrong echoed account, malformed payload, invalid revision, and invalid status
   rejection without mutation;
3. lower revision rejection and equal-revision heartbeat coalescing with no
   change cue;
4. account replacement/abort plus a late old-generation response that cannot
   render; and a `403` that clears rather than carries old data;
5. network/non-403/malformed retrieval failures that retain only a valid
   same-account snapshot marked stale and expose GET-only refresh;
6. visible-only scheduling, hidden cancellation, foreground reconciliation, and
   non-overlapping manual/automatic reads through injected/mocked fetch and
   visibility values; and
7. no derivation of percent, timestamp, delivery, download, or operation
   success from a job status.

Required local commands after implementation are:

```sh
python3 product/scripts/probe_environment.py
node --check product/app.js
(cd product && node --test)
```

The current static fixture has no deployed endpoint and no product browser
harness. Before any claim about rendered behavior, revalidate an authorized,
target-compatible browser route and use controlled responses to check the
companion in list/read/edit, account switching during a pending read, 403,
stale/manual refresh, keyboard focus, narrow layout, and reduced motion. That
future browser observation is distinct from the local Node checks and from any
deployment or remote-service claim.

## Handoff and revalidation conditions

The selected evolution remains appropriate only while the target stays static,
self-only, same-origin, and dependency-free; the controlled GET response keeps
the stated account/revision/job shape; and a 30-second visible-only polling
assumption is compatible with service policy. A changed target, rate limit,
status schema, browser facility, or package authorization requires reopening the
comparison before implementation. This producer has planned the work only; it
has not verified an oracle, remote endpoint, deployment, or consumer outcome.
