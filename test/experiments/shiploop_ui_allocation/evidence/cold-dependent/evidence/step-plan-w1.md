# W1 step plan — reload-persistent account-scoped drafts

**Producer scope:** planning evidence only. No product code, tests, target configuration, identity integration, deployment, or external API call was changed or attempted.

## Contract and current evidence

The direct request is to add reload-recoverable drafts and background-export change notification while preserving the existing Field Notes journeys and visual system; it also requires local pending text to remain separate from confirmed server content and to be unreadable by the next account after logout. The repository-owned sources are:

- [`product/README.md:3-5`](../product/README.md) for the current request and existing smoke command.
- [`product/docs/design.md#UI identity`](../product/docs/design.md) for preserved selector/list/textarea/controls, focus, touch, narrow-layout, and navy/amber premises; [`#Previous environment assumption`](../product/docs/design.md) is historical only.
- [`product/docs/platform.md:1-4`](../product/docs/platform.md) for the static same-origin target, CSP, no server runtime/WebSocket, host-owned identity, foreground behavior, and no deployment access.
- [`product/docs/api.md:1-2`](../product/docs/api.md) for the export revision polling contract and the absence of a draft-storage endpoint.
- [`product/app.js:4-14`](../product/app.js), [`app.js:143-211`](../product/app.js), [`app.js:233-294`](../product/app.js), and [`product/index.html:42-82`](../product/index.html) for the existing state, fetch cancellation/generation behavior, save/account-switch journey, and live status surface.

The planning design guidance used is `<study>/capabilities/frontend-design/SKILL.md`, SHA-256 `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`; it reinforces keeping the established Field Notes identity and using direct, actionable copy. The selected ShipLoop card is `<study>/frozen/shiploop/SKILL.md`, SHA-256 `be8340413f5ad72792da14d5f6719a98a8cbebc89a8531ad139e2c5dbc52c269`.

### Revalidated baseline

All observations below are current local-fixture evidence, not deployment or consumer evidence.

| Check | Observation | Limit |
| --- | --- | --- |
| `DEVELOPER_DIR=/Library/Developer/CommandLineTools python3 -B product/scripts/probe_environment.py` | `target=fieldnotes-embedded-v2`, `client_persistent_storage=unavailable`, `draft_api=false`, `server_runtime=false`, `websocket=false`, `script_src=[self]`, `style_src=[self]`, observation SHA-256 `40a3900ae08cf109734f411f62c8a89dbd5fae84c5f04d127ff000ea3038c878` | The script reads a controlled fixture, not a live target. |
| `node --check product/app.js` | Exit 0. | Syntax smoke only. |
| Native Node harness probe on Node `v25.9.0` | One self-contained `node:test` availability check passed. | It was not a product behavior test. |
| Current-source boundary check | `localStorage`, `sessionStorage`, `indexedDB`, and `caches.open` were absent; `/api/exports` was also absent. | This proves only the current source has no draft-persistence or export-notification implementation. |
| Repository identity | `git -C product rev-parse HEAD` reported `fatal: not a git repository`; no Git revision was established. | The synthetic seed's source-commit field is not used as a verified baseline. |

Current content identities: `app.js` `729f0db397fe3b0eaae3fadff9de10facd82b071fb7bbe00a95dcb9d9b5f8ac2`; `index.html` `f52423358a46b6210774533586602fb75267deb631129ba9bf96293e68f88213`; `styles.css` `cd3106112e5ddff749af99d9e3de730274f7786ccde2a2c4e75c172753b646bf`; `docs/design.md` `f3e6dce3dcab93d5d0b7fd294d9ab908c116e5416d7456b568ba01025e9699f9`; `docs/platform.md` `b8dfe6ff0a442cfe5a13947afe8bdc7d5bf4eb77aa66cd6d39fff1b0adba8007`; `docs/api.md` `862db25f3187bdf02a2d1da27bd041faca855e3ff4b3a235e153cda67dd37a27`; `scripts/probe_environment.py` `c54f52e5bd7f8a5801dee4f336ed2fe4989ffdfd035c30340835d0883ff41ec4`; and `host-observation.json` `40a3900ae08cf109734f411f62c8a89dbd5fae84c5f04d127ff000ea3038c878`.

No executable product test suite or package manifest is present in the current product file set. The synthetic predecessor's `test-strategy` result file and predecessor Improve receipt are absent, so this plan makes the test decision afresh instead of treating those labels as test evidence.

## Readiness boundary and disposition

Reload persistence cannot be truthfully implemented for the current controlled target: neither a client-persistent store nor a same-origin draft API is available. In addition, the current fixture exposes an account selector but no authenticated subject identifier or logout/identity-change notification contract. Namespacing a browser key with the visible `alpha`/`beta` selector value alone would not prove the logout privacy requirement.

The required pre-implementation environment augmentation is therefore one of the following host-approved, target-compatible contracts:

1. a client-persistent storage capability that is available in the embedded target, keyed by an authoritative account/subject identity and paired with a host identity-change/logout signal; or
2. a same-origin draft API that enforces the authenticated account scope, has an explicit draft read/write/delete and recovery contract, and supplies the identity-change/logout behavior needed to clear in-memory state.

The chosen contract must establish its account-scope, retention/clear-on-logout, unavailable/failure behavior, and safe recheck route. It must be re-probed with `scripts/probe_environment.py` or a revised target probe before baseline/implementation. No server process, external CDN, WebSocket, or deployment is proposed. This is an unresolved prerequisite for W1 implementation, not a completed feature or a reason to modify the current target.

`GET /api/exports` is an existing source contract for visible polling and foreground reconciliation, but it is not a live endpoint observation in this fixture. The notification portion can use that poll/reconcile model only after the normal same-origin API route is available; it cannot use a persistent subscription.

## Proposed implementation once readiness is evidenced

### Files and interfaces

1. Add a small same-origin draft adapter module, proposed as `product/drafts.js`, with a narrow `read`, `write`, and `remove` interface whose inputs include authoritative subject/account identity, note ID, text, and base revision. Its storage backend is selected only from the evidenced contract above. It must not silently fall back to page-memory while displaying a recovered-draft claim.
2. Update `product/app.js` to make the adapter an explicit dependency and retain the current abort-controller/generation guards. Add draft state separate from `state.record`: a local pending draft is rendered only after the current account, selected note, and request generation still match. The confirmed note continues to come solely from the note API response.
3. Update `product/index.html` only to add concise, dedicated, polite status text for draft recovery and export-status changes if the existing `#save-status` would conflate independent events. Keep the selector, note list, stable textarea, and save/cancel/back controls.
4. Update `product/styles.css` only with existing navy/amber/white tokens and the current focus/narrow-layout rules. Use static text and an `aria-live="polite"` cue rather than decorative motion; reduced-motion behavior is therefore unchanged.
5. Add `product/test/drafts.test.mjs` and any minimal test-only fixture helpers using Node's built-in test runner. Do not add a framework, package dependency, remote service, or external asset.
6. During the later documentation stage, create the narrowly scoped maintained requirements home `product/docs/requirements.md` if no current document is selected as that home, then link it from `product/SHIPLOOP.md`. It must distinguish the accepted request, the chosen environment contract, and the still-unverified target behavior from implementation observations.

### Interaction, state, and recovery agreement

- On edit input, schedule a scoped draft write only when the current identity, account, note ID, and edit generation still match. A successful local write acknowledges recoverability; a failed write keeps the textarea text in the live page but reports that reload recovery is unavailable.
- On opening a note, first obtain the confirmed record, then read a matching local draft. Render the local draft as working text without replacing `state.record.note` or the confirmed-note panel. On reload, read the same scoped record only after the authoritative identity is available.
- On cancel, remove the scoped pending draft, restore `state.record.note`, preserve the current focus behavior, and report the discard. On a confirmed save, remove the scoped pending draft only after the save response is valid for the same identity/account/note/generation; a failed save retains working text and its draft.
- On account change or host logout/identity change, abort note/save/draft/export work, increment the generation, clear selected in-memory text before the next account is rendered, and then load only the next account's scoped data. No asynchronous completion from the former identity may update the UI.
- If a durable store acknowledges a write and the page crashes before in-memory acknowledgment processing, reload reads the canonical scoped record rather than relying on the lost volatile acknowledgment. The eventual test suite must exercise this write-then-reinitialize recovery case.
- Add an `ExportWatcher` scoped to the current authorized account/collection. Poll `GET /api/exports` only while visible, reconcile on `visibilitychange` foreground, compare monotonic revisions, and issue a concise status notice on a change. It must not overwrite the editor or local draft. A failed/aborted poll reports a bounded actionable status and must not claim freshness.

### Failure, privacy, and diagnostics obligations

- Treat unavailable storage, an unavailable draft API, unknown identity, storage quota/security errors, and stale/aborted responses as distinct outcomes. Preserve the original low-level cause internally where one exists; show only concise non-sensitive action text to the user.
- Do not log draft content, whole state, credentials, or account payloads. There is no existing debug control, so this work does not introduce a global debug switch.
- Keep the existing same-origin CSP and no-server/no-WebSocket boundaries. A local test double proves adapter behavior only; it never establishes that the chosen embedded target supports the required storage or account lifecycle.

## Test plan and check placement

The first later implementation action must re-run the probe and `node --check app.js` against then-current hashes. Because there is no existing executable product suite, test bootstrap is an explicit prerequisite rather than a green baseline.

| Layer | Planned isolated case and independent oracle | Command / boundary |
| --- | --- | --- |
| Adapter/unit | Fake scoped store: write Alpha/note A, recreate the app/adapter, and read the same text. A separate Beta subject or a post-logout subject receives no Alpha text. | `node --test test/drafts.test.mjs` from `product`; fresh store per test. |
| Editor integration | Confirmed record and pending draft stay separate; cancel removes draft; a valid confirmed save removes it; failed save retains it. Stale write/save completions after account switch cannot alter the new account UI. | Native Node DOM/fetch fixture with deferred promises; no shared fixtures. |
| Crash/recovery | Simulate durable write acknowledgement followed by reinitialization before client-side acknowledgement handling; the new instance reads the canonical scoped value. | Native Node test with a deterministic fake durable backend. |
| Export updates | A visible poll/foreground reconcile with a higher revision surfaces a notice; hidden state does not poll; API failure does not overwrite the draft or claim freshness. | Native Node fake fetch/timer fixture. |
| Static/regression | Same-origin assets/CSP remain self-only; `node --check app.js` passes; focused cases and full available `node --test` suite run. | `node --check app.js`; `node --test`; source/CSP assertions. |
| Target/consumer | In a later authorized real embedded target: edit, reload, verify same-account recovery; log out/change identity, verify no prior-account draft is readable; cause an export revision change and observe the notification while editing. | Controlled browser/manual route after the host contract and target access are supplied. |

The current controlled fixture cannot run the final browser/target cases, and no remote access, deployment, or write authority was provided. Those are explicit verification gaps, not N/A results.

## Dependency order and downstream gate

1. Obtain an authorized, documented persistence plus host identity/logout contract and re-run its controlled probe.
2. Bootstrap the isolated native test harness and capture the original missing-suite condition separately from its later test outcome.
3. Implement the adapter, account/generation guards, draft status, and export watcher without changing the retained journey or visual system.
4. Execute focused, full available local, and authorized target/browser checks; retain the target capability and consumer observations separately.
5. Update maintained requirements and the knowledge index with the final selected contract, evidence, and any remaining target/deployment gap.

This producer is complete as a bounded plan. The next implementation-oriented action must remain blocked until step 1 has real readiness evidence.
