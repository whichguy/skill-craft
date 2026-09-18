# Intake assessment — Archive Exports client

## Boundary and authority

The preserved request is to plan a client-only export-status web application for a community archive. It covers collection selection, export requests, queued/running/complete/failure presentation, completed-download access, keyboard and narrow-screen use, restrained asynchronous feedback with a reduced-motion alternative, and a justified preparation plan. It does not authorize product implementation, dependency installation, a commit, a deployment, a remote write, or a change outside this isolated fixture.

The repository is `<study>/new/product`, at `ec3243d658e24304b306749bc361869154fc4660` on `main`; the observed worktree was clean. It contains no `AGENTS.md`, `SHIPLOOP.md`, test harness, UI, build configuration, or maintained requirements document. `README.md` is the current product overview; `docs/platform.md` and `docs/api.md` are the only supplied target/API contracts. Their absence as a maintained requirements home is a planning gap to resolve before implementation, not permission to invent an accepted product contract.

## Verified local facts

- `README.md` names this as the Archive Exports client and directs readers to the platform/API documents.
- `docs/platform.md` states that the deployed artifact is a static embedded web surface. Only same-origin bundled files are allowed; `script-src` and `style-src` are `self`, inline assets and CDNs are prohibited, no server process or persistent WebSocket is available, same-origin HTTPS API requests are permitted, and hidden pages can suspend. On foreground the client must read authoritative state.
- `docs/api.md` specifies `GET /api/exports`, `POST /api/exports` with a caller-supplied `clientOperationId`, `GET /api/operations/:clientOperationId` for lost-confirmation reconciliation, and `GET /api/exports/:jobId` for the current state and a same-origin download path only after completion. The server owns job state. Clients poll while visible and reconcile on foreground; notifications are only invalidation hints. There is no subscription or draft-storage endpoint.
- `python3 scripts/probe_environment.py` returned the controlled target `archive-static-v1`, `script_src` and `style_src` of `self`, `server_runtime: false`, `websocket: false`, `draft_api: false`, and `client_persistent_storage: not_assessed`. This is controlled fixture evidence, not a deployed-host receipt.

## Initial boundary model

Actor/channel/state ownership: an archivist uses the embedded client; the client sends same-origin HTTPS requests to the existing API; the API alone authorizes account scope and owns durable export/job state. Client state is transient presentation data: current list snapshot/revision, selected collection, pending request identity, loading/error status, and user-visible feedback. A POST acceptance is not completion; a lost POST confirmation must be reconciled by operation identity before showing success. A completed download can be opened only from a current completed job response. Visibility and foreground are client lifecycle inputs that cause read/reconciliation, not proof of live subscription.

The client must plan for API errors, an unknown POST outcome, duplicate activation, stale/late responses, a failure state with a recoverable action, and foreground reconciliation. The platform contract resolves polling over WebSockets; it does not establish a polling interval, response schema details beyond the supplied endpoints, client storage suitability, or an executable test/preview route. Those are open research/preparation questions.

## UI/design starting premise

Read `<study>/capabilities/frontend-design/SKILL.md` (SHA-256 `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`). It calls for subject-specific visual decisions, a compact token system, one restrained signature element, visible keyboard focus, responsive layout, and reduced-motion behavior. The consequential component, interaction, and skin decisions remain pending research/specification; no visual direction has been represented as an accepted product requirement.

## Evidence and reproducibility

Observed command: `DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe_environment.py` from the product root; output included observation SHA-256 `4234ca2a0b1535bab72aa9388b97f8d6140d7363ac0215a30858c77c415d2699`.

Observed Git command: `git --no-optional-locks -c diff.autoRefreshIndex=false status --short --branch`; output was `## main`. The available history has the single fixture commit `ec3243d658e24304b306749bc361869154fc4660` (“Fixture: freeze accepted request and controlled target facts”).

Source digests at intake: `README.md` `baa01be7a8ef154e1ac2d5f5528ac616be05b599a523da7202bd9c640d4fe33e`; `docs/platform.md` `b8dfe6ff0a442cfe5a13947afe8bdc7d5bf4eb77aa66cd6d39fff1b0adba8007`; `docs/api.md` `862db25f3187bdf02a2d1da27bd041faca855e3ff4b3a235e153cda67dd37a27`; `host-observation.json` `4234ca2a0b1535bab72aa9388b97f8d6140d7363ac0215a30858c77c415d2699`; selected ShipLoop card `be8340413f5ad72792da14d5f6719a98a8cbebc89a8531ad139e2c5dbc52c269`; selected Improve card `8c12fd39d2b7baf792e3054b464a34e912ae10800613218689ec905017dc1ef8`.

## Open questions carried forward

1. Which dependency-free or locally bundled UI technology can satisfy the static CSP and embedding constraints without an unverified install or external asset?
2. What concrete polling cadence/backoff and visibility reconciliation behavior fit the API and target without misrepresenting freshness?
3. Which browser-capable local test route can verify keyboard, narrow viewport, focus/status announcements, and reduced motion once a client exists, and what remains untestable without a deployed host?
4. How should the maintained requirements document record the current explicit requirements and planning decisions while keeping agent design choices distinct from user-approved intent?
