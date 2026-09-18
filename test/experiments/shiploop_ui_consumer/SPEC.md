# Field Notes consumer pilot

## Accepted baseline
A local web product for field researchers reviewing two notes. Navy (#15324f), amber (#c08722), white cards and a pale blue-gray background. System body type with a restrained Georgia title; no external fonts/assets/framework and no runtime installation. The existing list/detail/editor, labels, semantic buttons, save/cancel/back behavior and mobile layout are accepted. UI state is in memory only. Deployable artifact is the static source, served with same-origin script/style CSP. This pilot is a local real-browser fixture with a controlled service double, not a hosted service.

## Components and stable test interface
- Account selector label Account, id account, options alpha/beta. Lists contain note buttons with data-note-id=a1/a2.
- Detail section id detail, title id note-title, saved content id confirmed-note, numeric revision id revision, labeled textarea id note-input.
- Buttons Back to notes (#back), Edit note (#edit), Save changes (#save), Cancel (#cancel).
- Feature buttons Refresh (#refresh), Retry save (#retry-save), Reapply my text (#reapply). Hide nonapplicable actions. Persistent status #save-status (role=status, aria-live=polite); export #export-status (role=status, aria-live=polite). Status changes must not steal focus.
- Keep DOM editor node stable while editing; a long scrollable detail/editor area supports a nonzero reading position. Ordinary keyboard semantics and touch-size controls.

## Service contract
fetch /api/accounts/{account}/notes lists [{id,title,note,revision,exportStatus,exportRevision}]; GET /api/accounts/{account}/notes/{id} returns one. Notes a1/a2 exist in both accounts with visibly distinct content. Initial note revision 10, exportRevision 1, exportStatus idle. Service response is authoritative; display revisions never regress. Resource revision and exportRevision are independent monotonic integers. Fetch may resolve out of order. Identity/session generation invalidates old callbacks even if a user switches alpha→beta→alpha.
POST /api/accounts/{account}/notes/{id} body {note,baseRevision,operationId}. Server commits/deduplicates atomically within account/note/id scope before confirming; success returns {record}. Conflict HTTP409 returns {record}. Same scoped operationId + same intent lookup/retry can return existing result; changed text/base is a new intent/ID. Record not-found/unknown is not false failure. GET /api/accounts/{account}/notes/{id}/operations/{operationId} returns {state:committed,record}, {state:unknown}, or fetch failure. On response loss, retain draft and pending identity; retry unchanged intent first looks up same identity then can replay unchanged POST if unknown. Editing while save pending creates newer draft which late success must not erase. Reapply after conflict uses returned current revision and NEW operationId with chosen local text. In-flight older intent resolution must not overwrite newer text.

## Async interactions and motion
Export processing is service-owned even while UI absent. Poll detail every 15 seconds only when visible; refresh on resume; incoming event `fieldnotes:update` (CustomEvent detail {account,noteId}) is an invalidation hint, not trusted record data. Repeated hints coalesce one pending refresh and one follow-up at most; hidden hints just mark dirty. Do not announce stale intermediate history on resume. Fetch failure is persistent, retryable (Refresh), and cannot erase dirty text. Account switch discards former account draft/pending view and cancels stale cue work.
A confirmed relevant export change updates text immediately and optionally cues the status area for about 180ms; it never owns save success or domain work. Newer export state cancels older cue. `prefers-reduced-motion: reduce` keeps truthful status with no nonessential motion. A failure/status requiring action stays visible. Use native Web Animations API, no instrumentation affecting domain logic. Real browser can observe getAnimations + finish/cancel/currentTime and DOM assertions.

## Design guidance
The recorded planning run read and applied an available frontend-design card; its identity and applied decisions are retained in DESIGN.md. The accepted baseline palette, components and journeys override wholesale redesign. Record card identity/digest as metadata, not a made-up Markdown anchor. No Bootstrap/Material migration: static CSP environment needs no new component framework for this delta.

## Independent acceptance cases
| Case | Controlled input / interruption | Required observation |
| --- | --- | --- |
| P1 Existing journeys | Repeat the declared list/detail/edit/save/cancel/back journey before and after the feature. | Existing labels, tokens, component behavior and applicable keyboard/touch navigation remain consistent. |
| P2 Update during editing | Place the caret in a dirty note, then receive a confirmed export-status change. | Status updates; text, selection, focus and reading position remain intact. |
| P3 Reversed responses | Apply revision 11 for the active document, then deliver an older request's revision 10 response. | Confirmed view does not regress and the old response does not overwrite the current draft. |
| P4 Conflict/reapply | Server rejects an edit against revision 10 and supplies revision 11; user explicitly chooses to reapply local text. | The outgoing new intent carries revision 11 and a new operation ID; local text remains the user's chosen value. |
| P5 Unknown save result | Commit succeeds, response is lost, user retries the same unchanged intent. | Lookup/retry uses the same scoped operation ID and produces the allowed single effect; no false rejection or success is inferred from the timeout. |
| P6 Identity change | Switch accounts before an old request completes. | No old account data, draft, cue or callback affects the replacement account. |
| P7 Motion interruption | A relevant state change starts a cue, then a newer state arrives; repeat with reduced motion. | Current status/actions remain truthful and usable; old visual work is canceled, focus stays intentional, and motion completion never owns processing. |
| P8 Resume and event burst | Hide/resume after duplicate or missed updates; include a fetch failure. | Reconcile current authority, avoid repeated stale success/announcement bursts, retain actionable error/retry and preserve drafts. |


Also verify newer draft typed during pending save survives late success; unknown lookup failure retains retry; actual hidden/visible lifecycle where browser supports it (otherwise label synthetic visibility injection); keyboard and touch-emulated baseline journey; no screen-reader claim from DOM semantics alone.

## Experiment boundaries
Baseline preparation is synthetic prior product context. Only current step-plan producer, actual Improve review/parent import and subsequent feature implementation will be claimed executed. Improve gets these same acceptance criteria, not a hidden oracle. Source/test/plan claims are separate from browser observations. Product feature implementation waits for actual planning review acceptance. No shared repository commits, remote writes or deployment.
