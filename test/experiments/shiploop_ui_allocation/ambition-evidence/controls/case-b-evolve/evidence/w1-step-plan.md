# W1 step plan — Field Notes export activity explorer

## Scope, authority, and revalidated starting point

This is a plan for W1 only. It adds an account-scoped, read-only export-status
explorer to the existing note-detail journey. It does not add an export request,
download, draft persistence, storage, socket, server process, account selector,
framework migration, package, deployment, or W2 work.

The controlling product input for this delta is
`evidence/controlled-status-contract.md`: while the document is visible (and
again after it returns to the foreground), the client may only request
`GET /api/exports?accountId=<selectedAccountId>`. The host owns authorization
of the existing account selector; a received `accountId` is still checked before
the UI accepts it. The response's `revision` and current job statuses are the
only authoritative activity facts. No timestamp, progress percentage, history,
delivery result, retry, or new server action will be displayed or inferred.

Preserve the existing native selector, note list/detail/editor, focus behavior,
in-memory editing, navy/amber skin, and narrow layout recorded in
`product/docs/design.md#UI identity` and implemented in
`product/index.html`, `product/app.js`, and `product/styles.css`. The older
README/API descriptions of drafts and broader endpoints are retained as older
product context; they do not authorize W1 to use them. The current controlled
request and status contract are the W1 source for the GET-only delta.

The frozen-input check passed before planning. The current fixture probe reports
`fieldnotes-embedded-v2`, self-only scripts/styles, no server runtime, no
WebSocket, and unavailable client persistent storage in
`evidence/w1-probe-environment.raw.json`. `node --check app.js` passed
(`evidence/w1-node-check.raw.txt` is empty), while `node --test` found zero
tests (`evidence/w1-node-test.raw.txt`). That is an existing coverage gap, not
a passing behavioral baseline.

The product has no repository-local skill package or test configuration beyond
the supplied Node commands. Reuse the static fixture probe and built-in
`node --test` route; do not create a second UI/test harness. The planning design
guidance used here is the frozen `frontend-design` card at
`<study>/capabilities/frontend-design/SKILL.md`
(SHA-256 `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`),
as guidance only, not a runtime dependency or target-capability claim.

## Design basis — three UI views

### Components

Add the explorer only inside the existing note-detail surface, adjacent to the
current detail header so it is available without creating a new route or
selection journey.

| Component | Responsibility and visible states | Contract |
| --- | --- | --- |
| `export-activity-summary` | Compact, always-identifiable status control: loading, no reported jobs, current job-count summary, stale snapshot, or unavailable state. | A native button with `aria-expanded` and `aria-controls`; it exposes only the existing selected account's accepted snapshot. Its label never claims timing, progress, delivery, or a retry. |
| `export-activity-panel` | In-place expanded view with a heading, current job rows (`label` and exact `queued`/`running`/`complete`/`failed` status), persistent data-quality/error text, and a read-only `Refresh activity` control. | A disclosure panel, not a route, modal, export picker, or job selector. Generated labels use `textContent`, as the existing list renderer does, and the panel is removed from the tab order when closed. |
| `activity-announcer` | Announces a user-initiated loading change or a newly accepted authoritative update without moving focus. | A concise polite live region for normal changes and a persistent readable error region for failed/stale data. Equal revisions never replay an update/completion cue. |
| Activity state/reconciler | Owns request lifecycle, current account generation, accepted revision, snapshot, stale/error state, expanded state, and foreground-needed flag. | It is local, in-memory presentation state. The service owns jobs/revisions; the host owns account authorization. It has no mutation, storage, operation, or delivery authority. |

Target implementation files are `product/index.html` (static container and
accessible relationships), `product/app.js` (state, GET/reconciliation,
event listeners, and focused DOM updates), and `product/styles.css` (scoped
layout, states, and motion). If the existing `node:test` route needs a
browser-neutral seam, add only a small source-owned activity reducer/helper and
`product/test/export-activity.test.js`; it must be shared by the application,
not a fake DOM/design harness. Later documentation belongs in
`product/docs/design.md`; `product/docs/api.md` is not broadened or normalized
by this GET-only plan.

### Interaction model and state agreement

The concrete trace is: the person opens a note -> the compact activity summary
requests a visible, selected-account snapshot -> the GET response is validated
against the captured account/generation/revision -> only an accepted snapshot
updates the summary/panel -> a person may expand the same in-place panel or use
the read-only refresh control. A `visibilitychange` return to visible follows
the same reconciliation path. There is no subscription, background processing,
acknowledgment, retry, or delivery confirmation.

`app.js` already uses an account value, request generation, and
`AbortController`s for note work. W1 should use the same local pattern, with a
separate activity controller and account-generation value so activity refreshes
never call `renderRecord`, `showList`, `setEditing`, or reset the textarea.

* On account change, increment the activity generation, abort its active
  request, clear the prior account's snapshot before any new response, collapse
  the panel, and wait for a matching response. The old account's jobs must never
  appear under the replacement account.
* Start a GET only when `document.visibilityState === "visible"`; when hidden,
  abort/ignore an outstanding activity request and mark a foreground refresh as
  needed. On the next visible event, run one reconciliation GET. The initial
  visible load and the explicit `Refresh activity` control use that same method.
  W1 does not invent a polling interval; a future visible-poll cadence needs a
  separately recorded product decision.
* Capture account, generation, and controller at request start. Ignore an
  aborted, superseded, hidden, mismatched-account, malformed, `403`, or older
  revision response. Validate that `revision` is an integer and each job has an
  id, label, and one of the four contract statuses before rendering any of it.
* A higher revision replaces only the activity snapshot and creates one concise
  `Export activity updated` cue. An equal revision may clear a stale condition
  but neither re-renders a completion cue nor starts a motion sequence. A lower
  revision is rejected and leaves the accepted display intact.
* A non-abort network/validation/authorization failure keeps a same-account
  accepted snapshot visibly stale with an always-available read-only refresh.
  Without an accepted snapshot, show a persistent unavailable/error state plus
  that control. A `failed` job is an authoritative job state, not a request
  failure and not a retry affordance.
* An asynchronous activity update does not focus, scroll, replace, or select
  the note/editor. Opening is an explicit user action; closing returns focus to
  the summary control when needed and restores the pre-open detail-scroll
  position. Preserve the editor's active focus, selection range, dirty text,
  selected note, and reader position across refreshes. The existing explicit
  account-switch journey may still change notes; W1 activity code must not add
  another loss path.

Keyboard behavior uses the native summary button (Enter/Space), `Escape` and a
visible close/return-to-note control for the expanded panel, predictable tab
order, and existing amber `:focus-visible` treatment. Do not use a focus trap.
Normal refreshes use an unobtrusive polite announcement; errors remain visible
instead of disappearing in a toast and do not steal focus.

### Branding, skin, and motion

Keep the existing Field Notes identity: navy `#15324f`/deep navy, amber
`#c08722`, white cards, muted utility text, Georgia display headings, and the
system body face from `product/styles.css`. The explorer's distinctive but
truthful signature is a compact **field ledger**: a quiet summary shelf and
expanded current-status rows marked by an amber rule. It is deliberately a
current snapshot, not a timeline or a fabricated activity history. Status
hierarchy comes from label, exact status word, and semantic error/freshness copy
rather than color alone.

At the existing `42rem` breakpoint, the summary controls and job rows stack,
actions wrap, and labels retain usable line length without horizontal overflow.
Use explorer-scoped CSS custom properties/classes rather than a new global
design system or shared motion-token layer. For people without reduced-motion
preference, a brief CSS opacity/transform disclosure and one real
higher-revision emphasis can connect compact and expanded views. Under
`prefers-reduced-motion: reduce`, render the final disclosure/state immediately
and retain the textual update/error cue; never substitute an animation for
semantic status.

No existing debug control was observed in the fixture. Do not add logging
machinery for W1. If an existing debug hook appears before implementation, it
may record bounded account-generation/revision/outcome facts without labels or
whole snapshots; user-facing errors stay actionable and do not expose raw
response/error details.

## Consequential UI decision

| Approach | Current evidence and benefit | Cost/tradeoff | Decision |
| --- | --- | --- | --- |
| Evolve plain DOM/CSS | Controlled primitives already include DOM composition, same-origin CSS, live regions, and reduced-motion media queries. It preserves the fixture's direct DOM ownership, self-only CSP, current visual language, and no-package footprint. | Requires careful semantic hide/show, scroll restoration, and targeted rendering. CSS continuity is modest rather than browser-snapshot magic. | **Safe W1 path.** Build the disclosure and truthful status states with existing primitives first. |
| Native View Transitions | Could make a supported compact-to-expanded change feel more continuous while keeping the DOM/CSS fallback. | `document.startViewTransition` is only a candidate: the intended embedded target has not established availability, lifecycle, accessibility, reduced-motion, focus/scroll, or fallback behavior. | **Conditional progressive enhancement only.** It cannot be the W1 baseline or remove the DOM/CSS path. |
| Framework/package candidate (for example Bootstrap or a Material implementation) | A future package might offer components, but no candidate, version, lockfile, license record, or build/runtime support is present. | It would introduce package, asset/module, CSP, framework-DOM-ownership, maintenance, and visual-identity risk without a demonstrated gap. | **Defer.** Do not install, select, or plan a migration in W1. |

The CSS/DOM implementation is a medium, bounded change: roughly the three
existing UI source files, the existing test route's first focused case(s), and
the design note, assuming the contract remains GET-only and no target-specific
browser incompatibility appears. A View Transitions enhancement adds a separate
target observation and fallback validation; a package migration is materially
larger and outside W1. These are relative, assumption-bound estimates rather
than schedule or target-performance claims.

Before enabling the native candidate, use the existing product/environment and
browser verification path on an authorized instance of the intended embedded
target, not local Chrome/Playwright alone. The bounded probe must: verify the
API's actual availability; exercise expand/collapse and a higher-revision update;
confirm the self-only CSP and static artifact still load; compare focus,
selection, scroll, live-region, error/stale, and reduced-motion outcomes with
the CSS fallback; and force the unavailable/rejected branch. It may guard the
candidate with `typeof document.startViewTransition === "function"`, but the
fallback remains authoritative. Current access provides no target browser or
deployment route, so this probe is planned and unresolved, not executed.

## Tests, documentation, and integration plan

The future `test-spec`/`test-author` work should put the following cases through
the existing Node route and the smallest available browser surface. The Node
route is appropriate for a small shared response/revision reducer; rendered
focus, CSS, accessibility, and target-native behavior require a browser check.
No test should claim a deployed target is covered until that authorized target
is actually exercised.

| Case | Preconditions and stimulus | Expected independent outcome | Planned route |
| --- | --- | --- | --- |
| `W1-ACT-01` | Matching visible-account response with each supported job status. | Compact aggregate and expanded rows contain only returned labels/statuses; empty data is a truthful empty state. | `node --test` for reducer/validation plus browser render check. |
| `W1-ACT-02` | Account switches or a newer request supersedes an older in-flight response. | Prior-account/superseded response cannot render; prior snapshot is cleared for the replacement account. | Focused Node state case; browser flow when available. |
| `W1-ACT-03` | Mismatch, malformed payload, `403`, lower revision, or network failure after a valid same-account snapshot. | Accepted snapshot remains; stale/error copy and read-only refresh persist; no fabricated recovery action appears. | Focused Node case and browser error-state observation. |
| `W1-ACT-04` | Equal revision, then a higher revision while the detail/editor is active. | Equal heartbeat emits no update/completion cue; higher revision updates once without changing note selection, text, focus, or scroll. | Focused Node case plus browser interaction check. |
| `W1-ACT-05` | Page hides during/after refresh, then returns visible. | No hidden fetch/result wins; foreground reconciliation uses GET and follows the same guards. | Browser lifecycle check on an available compatible surface. |
| `W1-ACT-06` | Keyboard expand/close and reduced-motion preference. | Correct `aria-expanded`, keyboard/focus return, persistent errors, responsive layout, and immediate reduced-motion equivalent. | Browser accessibility/reduced-motion procedure; native candidate remains unverified without target access. |

The future test bootstrap, if needed, owns its setup and teardown: deterministic
mock GET responses, aborted-controller cleanup, restored visibility/motion
overrides, and no persistent data. It must register cases under `node --test`
so zero discovery cannot be reported as green. Keep `python3
scripts/probe_environment.py`, `node --check app.js`, focused `node --test`,
and the full `node --test` route as separate evidence; the current full route is
only a zero-test baseline. A target browser check is a distinct, currently
unavailable validation obligation, not replaced by source inspection or a local
fixture.

At the later documentation stage, update `product/docs/design.md` with this
explorer's component, interaction, and skin contracts; its GET-only authority;
the conditional native decision; and the real test/target limits. Do not create
a competing requirements document, invent a local skill, or rewrite W2 draft
requirements. Integration remains within the static same-origin page: no
deployment, package installation, configuration change, remote write, or
server/API expansion is part of W1.

## Handoff locators and revalidation conditions

* Controlled requirements: `evidence/request.md` and
  `evidence/controlled-status-contract.md`.
* Product baseline/identity: `product/SHIPLOOP.md`,
  `product/docs/design.md#UI identity`, `product/docs/platform.md`,
  `product/index.html`, `product/app.js`, and `product/styles.css`.
* Environment/test evidence: `evidence/w1-probe-environment.raw.json`,
  `evidence/w1-node-check.raw.txt`, and `evidence/w1-node-test.raw.txt`.
* Package guidance: selected ShipLoop
  `references/behavioral-requirements.md#actors-channels-and-state-ownership`,
  `#ui-specific-planning`, and `#allocate-ui-decisions-to-their-planning-owner`;
  `references/repeatable-test-suites.md#select-or-revalidate-the-harness`; and
  `references/testing-and-documentation.md#test-cases`.

Revalidate this plan if the selected account/GET schema, target CSP/embedding,
browser capability, test route, or documentation authority changes. The normal
next action is ShipLoop's bound Improve handoff for this producer result; no
Improve cycle has been run by this plan.
