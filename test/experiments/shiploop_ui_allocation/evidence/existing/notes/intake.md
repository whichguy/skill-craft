# Intake — Field Notes recoverable drafts and export-change notice

## Run and authority boundary

- This is the initialized navigator-v3 run `nav-ba797d421eb24ce8b9c19baeee54d59c` against the explicit isolated fixture at `<study>/existing/product`.
- The observed baseline is clean on `main` at `8f318f0adb98cb3a6e9c6419e57e48ef96ef2a8e`; its only reachable fixture commit is recorded in `../evidence/intake-git-history.txt`.
- This planning experiment permits local read-only probes and run-local evidence only. It does not authorize product edits, commits, installations, network services, deployment, or a replacement `init`/`drive` run.

## Accepted user outcome and preserved conditions

- Add recoverable drafts across reloads and a notice when a background export changes.
- Preserve the accepted list, detail, edit, save, cancel, and back journeys; native account selector; focus/keyboard/touch behavior; narrow layout; reading position; draft text; navy `#15324f`, amber `#c08722`, white cards, system body, and Georgia display type. Local pending text remains separate from the confirmed server note. Source: `product/docs/design.md` lines 1-5.
- A logout/account transition must make a prior account's drafts unreadable to the next account. This is a user requirement, not currently verified product behavior.

## Observed consumer, target, and current product facts

- The consumer is a static embedded Field Notes web surface. The target permits same-origin HTTPS APIs, but no deployed server runtime, external assets, inline script/style, or WebSockets. Hidden pages may suspend and must reconcile authoritative state on foreground. The experiment has no remote deployment access. Source: `product/docs/platform.md` lines 1-4.
- The controlled current observation identifies `fieldnotes-embedded-v2`, `client_persistent_storage: unavailable`, and `draft_api: false`; it is explicitly not a live-deployment receipt. Source: `product/host-observation.json` lines 1-14; command source: `product/scripts/probe_environment.py`.
- Export state is server-owned. The documented usable path is visible-page polling plus foreground reconciliation; notifications are invalidation hints. There is no documented subscription or draft-storage endpoint. Source: `product/docs/api.md` lines 1-2.
- The existing client has account switching, list/detail loading, in-memory editing, and save/cancel/back behavior. It has no observed draft persistence or export-status UI. This is an implementation observation from the frozen source snapshot, not an accepted requirement.

## Design guidance applied

- The current packet explicitly selected `<study>/capabilities/frontend-design/SKILL.md` as a non-binding planning input (SHA-256 `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`); it does not create product authority. The user request and repository-owned accepted UI/design record control. Any later draft/export-status treatment must state what changed in plain user language, retain visible focus and responsive behavior, and avoid a visual redesign or decorative motion.

## Open questions for discovery and research

1. Reload recovery is not currently compatible with the observed target because both client persistence and a draft API are unavailable. Research must evaluate an account-scoped server draft API versus a target storage-capability change, including logout erasure/isolation and available authorization.
2. The export contract supports polling and foreground reconciliation but not persistent subscriptions. Research must define an observable, non-WebSocket change-detection plan and distinguish an in-app notice from an operating-system notification.
3. The request depends on existing note read/save routes used by `app.js`, while the repository-owned API document only specifies export endpoints. Discovery must retain that contract gap rather than inventing note API guarantees.
4. No current-run evidence records the README-provided `node --check app.js` smoke command or `python3 scripts/probe_environment.py` observation as having run. The selected ShipLoop initial-baseline guidance makes them discovery candidates; they remain unrun intake evidence rather than a product-defined gate.

## Evidence inventory

- Source hashes: `../evidence/intake-source-sha256.txt`.
- Product Git identity/status/history: `../evidence/intake-head.txt`, `../evidence/intake-git-status.txt`, and `../evidence/intake-git-history.txt`.
- Selected ShipLoop CLI binding check: `../evidence/shiploop-help-argv.json`, `../evidence/shiploop-help.stdout`, and `../evidence/shiploop-help.stderr`.
