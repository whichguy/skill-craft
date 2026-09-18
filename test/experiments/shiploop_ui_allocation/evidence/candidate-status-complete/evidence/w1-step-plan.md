# W1 step plan — read-only account-scoped export status

This is a planning-only W1 artifact. It plans one status observer; it does not
implement product code, tests, documentation, Git work, host changes, or a
deployment. The current request supersedes the older reload-draft proposal only
for this scoped observer: W2 remains blocked.

## Design basis and preserved locators

~~~mermaid
flowchart LR
  A[Visible page and selected account] --> B[Capture account and generation]
  B --> C[GET exports with encoded account query]
  C --> D[Host independently authorizes query]
  D --> E{Current generation, matching account, accepted revision}
  E -->|accept| F[Update standalone status surface]
  E -->|reject or failure| G[Clear unsafe status and show recovery]
~~~

- The native selector, list/detail/editor, focus, reading position, draft text,
  navy/amber palette, and no-framework premise are preserved from
  [design.md - UI identity: existing interaction and visual contract](<study>/candidate-status-complete/product/docs/design.md:2).
  The existing code already keeps note-list requests separate from detail/edit
  state and focuses the editor only on explicit edit; the observer must stay
  outside those paths
  ([app.js - list and detail request lifecycle: existing UI rendering](<study>/candidate-status-complete/product/app.js:143),
  [app.js - editor focus and cancellation: dirty draft behavior](<study>/candidate-status-complete/product/app.js:213),
  [app.js - account switch: privacy-preserving note-view transition](<study>/candidate-status-complete/product/app.js:288)).
- W1’s sole new read is
  [controlled-status-identity-contract.md - request contract: encoded account query](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:11).
  It is a controlled fixture contract, not a production-host, deployment, or
  account-switch claim
  ([controlled-status-identity-contract.md - scope: controlled input only](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:3)).
- The static, same-origin, CSP-constrained surface permits HTTPS request/response,
  may suspend while hidden, and provides neither a server runtime nor a socket
  ([platform.md - deployment boundary: supported client capabilities](<study>/candidate-status-complete/product/docs/platform.md:2)).
  The current controlled observation also says persistent client storage and a
  draft API are unavailable
  ([host-observation.json - controlled target facts: storage and draft limits](<study>/candidate-status-complete/product/host-observation.json:11)).
- Applied UI guidance: the available
  [frontend-design SKILL.md - restrained, accessible existing-identity design](<study>/capabilities/frontend-design/SKILL.md:41),
  SHA-256
  1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd,
  recorded in
  [frozen-input-manifest.json - frontend-design identity: frozen digest](<study>/candidate-status-complete/evidence/frozen-input-manifest.json:81).
  It supports a narrow, deliberate addition rather than a redesign, as required
  by [behavioral-requirements.md - UI-specific planning: components, interaction, and skin](<study>/candidate-2/shiploop/references/behavioral-requirements.md:184).

## Planned implementation delta

**Files and components.** A later implementation changes only
product/app.js, product/index.html, and product/styles.css. Add a standalone
account-scoped #export-status surface outside the list/detail render paths so it
persists while either existing view is open. It contains a compact visible
aggregate count by documented status (never an individual-job list), and a retry
control that repeats the same read; add a separate polite announcement node that is
populated only for a meaningful accepted change. It must not reuse #list-message or #save-status,
which belong to existing note operations
([index.html - current live regions: list and save messages](<study>/candidate-status-complete/product/index.html:31)).

The fixed composition has four explicit visible states: initial loading (no
accepted snapshot yet), accepted empty, accepted non-empty, and persistent
retryable error. A current-account network or parse failure after an accepted
snapshot retains that **same-account** last-known summary with an error/retry
message; authorization failure, identity mismatch, or account replacement
clears it before a response can be rendered. Retry is a visible, named native
button; it is disabled only while that one read is pending and never moves focus.
The summary is a separate visible label from the polite announcer, so polling
does not repeatedly announce unchanged content. Fixed aggregate counts and copy
fit the reserved narrow-layout height; job IDs and labels are neither rendered
nor used as client identity keys, so W1 adds no inferred uniqueness, ordering,
or text-length rule to the supplied response contract.

The surface is informational: it has no export-request action, collection
selector, operation reconciliation, job details, download, pagination,
subscription, persistence, server, socket, or framework migration. Its only
new interaction is a retry of the documented GET. No product documentation is
changed in this W1 producer; the fixture contract remains run-local evidence,
not a repository claim of a live integration.

**Interaction and state.** Keep observer state separate from
state.requestGeneration, which currently guards list/detail requests
([app.js - shared request generation: existing request invalidation](<study>/candidate-status-complete/product/app.js:4)).
The observer owns a status generation, its own AbortController, one
visible-only timer, current rendered account/snapshot, and one exact
held-revision token for that active view. The held token exists only while its
view snapshot is active; clearing that view clears its comparison state. The
host remains sole owner of authorization and job state; the client owns only
transient presentation state. This follows the
required separation of request context, authorization, and consumer state
([behavioral-requirements.md - state ownership: authority and lifetime](<study>/candidate-2/shiploop/references/behavioral-requirements.md:110)).

For every initial, retry, visible poll, or foreground refresh:

1. Capture selectedAccountId = elements.account.value and the current observer
   generation, then request exactly GET /api/exports?accountId=<encodeURIComponent(selectedAccountId)>
   with Accept: application/json.
2. The selector supplies request context only. The host independently compares
   the query with its authoritative authorizedAccountId; the client sends no
   credential, does not treat DOM state as authorization, and does not claim a
   host account switch
   ([controlled-status-identity-contract.md - authorization boundary: 403 for nonmatching query](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:19)).
3. Normalize only the fields W1 consumes before rendering: response `accountId`
   exactly equals the captured nonempty account text; `revision` is preserved as an exact valid
   JSON-integer token and ordered by a local arbitrary-precision decimal
   comparison (not `Number`, `Number.isSafeInteger`, or an added range rule);
   and every consumed job `status` is one documented enum value. A
   number-preserving JSON decoder, or an equally precise small decoder for this
   controlled response shape, is a W1 client implementation choice and requires
   no new host capability. W1 aggregates statuses only: it neither renders nor
   keys state by job IDs or labels, and therefore does not reject otherwise
   contract-valid duplicate IDs, long labels, or opaque label text. Reject only
   malformed JSON, a non-integer revision token, or a missing/invalid consumed
   contract field as a recoverable read error; no HTML insertion or server
   payload output is permitted.
4. Accept a normalized 200 response only if the captured generation is still
   current, its accountId exactly equals the captured request account, and its
   revision is newer than the held revision for that contiguous active account
   view. Equal remains a no-change heartbeat whenever a revision is held; lower
   is stale; revisions are never compared across accounts. Account replacement
   clears both the visible snapshot and that view's held revision. Because there
   is then no comparison-state value, the first matching response after a return
   establishes a fresh current view without an announcement; it does not
   reclassify an equal held revision as newer.
   ([controlled-status-identity-contract.md - acceptance rule: generation, identity, and revision guards](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:52)).
5. On account change, abort/invalidate the old observer request, increment its
   generation, clear the status snapshot and active-view held revision before
   the existing note-view transition, and only let a matching response for the
   new account render. A late old-account callback is discarded silently.
   ([controlled-status-identity-contract.md - account replacement: clear old snapshot](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:59)).

**Failures, recovery, and visible lifecycle.** A 403
account_not_authorized, response-account mismatch, malformed consumed contract
field, or network failure never renders the response and keeps the visible surface in a
concise persistent retryable error state. Only an already accepted snapshot for
the *same current account and generation* may remain visible beneath that error;
account replacement, 403, or identity mismatch clears it. The surface never
shows opaque IDs, labels, or server payload. It neither treats a selector change as
authorized nor exposes an old account’s jobs under the new account
([controlled-status-identity-contract.md - failure privacy: no prior-account jobs or payload leaks](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:59)).

Read only while document.visibilityState is visible; abort/stop the timer when
hidden, keep at most one observer request active, and refetch the then-current
selector account on foreground. A newer revision for the active account view
updates the visible surface; only a meaningful aggregate-status-count difference
receives a polite announcement. A first matching response for a newly cleared
active view establishes the compact summary without a success cue; an equal
held revision, lower revision, stale generation, failed response, or resumed-old
response does not replay a success cue. Errors remain visible until a later retry/accepted
snapshot; no auto-focus, toast-only recovery, or motion can confirm the
underlying export state. This preserves the contract’s visible-only recovery
boundary and accessible persistent feedback
([controlled-status-identity-contract.md - lifecycle and UX: visible reads, foreground recovery, status feedback](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:65)).

**Focus, draft, and skin.** Same-account refreshes may update only the new
status nodes. They must not call renderList, showList, showDetail, renderRecord,
setEditing, or focus/scroll APIs; therefore the existing textarea value,
selection, keyboard/touch focus, reading position, and dirty draft remain
untouched. Account replacement retains the existing privacy transition rather
than inventing draft persistence. The status panel uses the existing navy/amber
variables, white-card density, Georgia/system type split, and existing focus
ring
([styles.css - visual tokens and focus treatment: established skin](<study>/candidate-status-complete/product/styles.css:4)).
Any pending/change transition is restrained and disabled under the existing
reduced-motion rule
([styles.css - reduced-motion media rule: motion fallback](<study>/candidate-status-complete/product/styles.css:414)).

## Planned focused checks

No test is created in this producer. The prior projected test-strategy result is
absent and synthetic state is not evidence of coverage; node --test currently
discovers zero tests. The planned smallest harness is a local native Node test
with a fresh fake DOM/fetch/visibility fixture per case and deterministic
authorizedAccountId setup. It adds no dependency or remote operation. The
future focused command is node --test test/status-observer.test.js; the future
full local route is node --test. Each case restores globals, timers,
controllers, and fixture account identity in teardown. A zero-selected run is
not a pass
([repeatable-test-suites.md - harness selection: explicit runner and lifecycle](<study>/candidate-2/shiploop/references/repeatable-test-suites.md:9)).

- **ST-1 accepted and empty reads:** assert the exact encoded GET, matching
  controlled host account, matching response account, and first/higher
  same-account revision render only the status surface. Cover initial loading,
  accepted empty jobs, accepted non-empty jobs, and the separate persistent
  visible aggregate-summary/polite-announcer semantics. Assert that W1 shows
  aggregate enum counts only, never individual IDs or labels.
- **ST-2 authorization and identity failures:** fixture 403, mismatched response
  account, malformed JSON, a non-integer revision token, missing/invalid status,
  and network failure; assert no response payload leak, persistent recovery, and
  no note/editor mutation. Separately supply duplicate IDs and long or hostile
  label text with valid aggregate statuses and assert that the accepted aggregate
  is rendered without exposing those unused fields or inventing a rejection.
- **ST-3 ordering:** switch alpha to beta while alpha is in flight; ensure the
  old callback cannot render. Switch alpha to beta to alpha with the same valid
  alpha revision value: the cleared alpha surface remains blank until the first
  current authorized alpha response establishes its new active view without an
  announcement. Within one active account view, check equal heartbeat/no change,
  lower-revision rejection, and higher-revision acceptance. Assert that no alpha
  snapshot renders while beta is selected. Include a contract-valid integer beyond JavaScript
  safe-number range to prove exact ordering without a hidden range restriction.
- **ST-4 lifecycle and preservation:** hidden state issues no poll; foreground
  refetches once for the current selector. With a focused, dirty editor and
  selected text/scroll, a same-account status refresh preserves value, selection,
  focus, and reading position; meaningful higher changes announce politely and
  reduced-motion does not require animation. Exercise retry: its accessible
  named button performs exactly one new status GET, disables only during its
  pending request, and restores the visible error/snapshot rule on failure.
- **ST-5 observer-only negative effects:** assert status initialization, polling,
  foreground recovery, and retry issue only the documented GET and never invoke
  an export mutation, collection/operation/download route, storage, socket,
  server, or framework addition. Existing note-save POST behavior remains an
  unaffected baseline and is not an observer failure.

The current local baseline is recorded verbatim in
[w1-probe-environment.raw.txt - controlled target observation: no storage or live deployment](<study>/candidate-status-complete/evidence/w1-probe-environment.raw.txt),
[w1-node-check.raw.txt - syntax baseline: exit 0](<study>/candidate-status-complete/evidence/w1-node-check.raw.txt), and
[w1-node-test.raw.txt - test baseline: 0 tests and 0 passes](<study>/candidate-status-complete/evidence/w1-node-test.raw.txt).
They establish syntax and fixture facts only, not implementation coverage,
rendered accessibility, live authorization, deployment, or consumer delivery.

## W2 and controlled-host limits

W2 (persistent account-scoped drafts) stays blocked. Its missing suppliers are
client persistence or a draft API; both are expressly absent from the controlled
host observation. W1 must neither add storage nor provide a workaround that
turns temporary editor state into persistent drafts
([controlled-status-identity-contract.md - W2 boundary: no storage or draft route](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:81)).

The product directory is non-Git (product/.git was absent), so this producer
has no repository revision, commit, merge, or rollback evidence. The permitted
probe describes a controlled fixture and there is no remote deployment access;
neither a local harness nor this plan can prove a real host authorization bridge,
account switch, deployed artifact, or live status change. These limits remain
open for any later owner with authorized target access.
