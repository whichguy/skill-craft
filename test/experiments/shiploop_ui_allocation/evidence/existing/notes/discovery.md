# Discovery — Field Notes recoverable drafts and export-change notice

## Sources and status

| Source | Status and use |
| --- | --- |
| `product/README.md` and `product/SHIPLOOP.md` | Repository-owned request overview, smoke command, and index; current. |
| `product/docs/design.md` | Accepted UI identity and preserved interaction conditions; current accepted baseline. |
| `product/docs/platform.md` and `product/host-observation.json` | Controlled target constraints; current local observation is not live deployment evidence. |
| `product/docs/api.md` | Existing export contract; current fixture contract, not a deployed service receipt. |
| `product/app.js`, `index.html`, and `styles.css` | Current client behavior/components; observed implementation only. |
| `run/notes/intake.md` | Accepted current-request boundary and retained capability questions. |
| `run/notes/environment-lifecycle.md` | Current topology, access, delivery, and revalidation record. |

## Baseline and repository observations

- **Baseline smoke:** `node --check app.js` in `product/` exited `0` on the initial tracked content. It is a JavaScript syntax check only; it does not exercise the DOM, note API, draft recovery, account isolation, exports, or a browser. Raw argv/output: `../../evidence/discovery-baseline-smoke-argv.json`, `../../evidence/discovery-baseline-smoke.stdout`, and `../../evidence/discovery-baseline-smoke.stderr`.
- **Environment probe:** `python3 -B scripts/probe_environment.py` exited `0` and reproduced the controlled v2 observation. Raw argv/output: `../../evidence/discovery-environment-probe-argv.json`, `../../evidence/discovery-environment-probe.stdout`, and `../../evidence/discovery-environment-probe.stderr`.
- **Unrun coverage:** the bounded test-artifact scan found no test runner/full suite. The documented smoke is the only current executable route found. This is missing behavioral coverage, not a passing full suite or an N/A test disposition.
- **Content identity:** every initial tracked product source hash remained `OK` after the baseline. Product tracked status/diff remained clean; only run-owned `.shiploop-improve/` is untracked. Evidence: `../../evidence/discovery-post-baseline-source-hash.txt`, `../../evidence/discovery-post-baseline-git-status.txt`, and `../../evidence/discovery-post-baseline-tracked-diff.txt`.

## Current flow and boundary assessment

- The human consumer uses the account selector, list, detail, edit, save, cancel, and back controls. `app.js` holds selected record/editing state in memory, uses abort controllers/generation checks around list/detail/save requests, and restores the confirmed note on cancel. It currently has no observed draft persistence or export-status UI. Flow locators: `../../evidence/discovery-client-flow-locators.txt`.
- The static embedded target allows same-origin request/response and requires bundled self-only assets. Its host owns account identity; hidden pages may suspend, so the documented export behavior is visible polling plus foreground reconciliation. WebSocket/subscription and local persistence are unavailable. Contract locators: `../../evidence/discovery-contract-locators.txt`.
- Export service state is authoritative and revisioned. A client notification is only an invalidation/display cue after an authoritative read; acceptance, completion, and display are different facts. No current source supports a persistent background receiver, OS notification, or draft store.
- The fixture's note endpoints are inferred from client source, while the repository-owned API contract documents exports only. Treat note save/revision/conflict semantics as unresolved until an authorized contract source is supplied.

## Applicable requirement and quality screen

- **Preserve:** existing journeys, component identity, keyboard/touch/focus, narrow layout/reading position, and navy/amber/white/system/Georgia skin from `docs/design.md`.
- **Add:** recoverable account-safe pending drafts; export-change user feedback; strict separation of local pending text from confirmed server content. These derive from the current user request and remain unimplemented.
- **Security/privacy:** applicable because a previous account's drafts must be unreadable after identity change. Required scope/clearing and server authorization rules are unknown, so this is a planning/research gap rather than a verified control.
- **Durability/recovery:** applicable because reload survival is requested. Current target has no verified carrier, so an augmentation is required before implementation can satisfy it.
- **Compatibility/operability:** applicable because the deployed artifact must stay static/CSP-compatible and the UI must recover after foregrounding. No latency, polling interval, retention period, or OS-notification policy was supplied; do not invent one.
- **Accessibility/usability:** applicable through preserved focus/keyboard/touch and truthful async status; browser-level evidence is not yet available.

## Discovery decision and research frontier

This discovery is sufficient to begin bounded research without implementation. The frontiers are: (1) the smallest authorized storage/identity contract that makes drafts recoverable and prevents cross-account reads; (2) the observable export revision/reconciliation flow that produces a truthful in-app notice under visible/foreground lifecycle; (3) the missing note read/save contract needed for conflict and pending-versus-confirmed behavior; and (4) a practical test route for the static client. No remote system was probed or provisioned, and no external access request is yet appropriate because the actual target/owner has not been identified in this experiment.
