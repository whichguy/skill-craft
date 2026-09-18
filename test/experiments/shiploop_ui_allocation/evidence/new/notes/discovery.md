# Discovery assessment — Archive Exports client

## Sources and current context

Read the repository README, platform/API contract, controlled host observation and probe script; inspected Git state/history/config/remotes, tracked files, manifests/test/build/CI inventory, hooks, and repository-local `SHIPLOOP.md`/requirements/.shiploop locations. No product `AGENTS.md`, knowledge index, maintained requirements home, prior run state, test harness, code, build configuration, or deployment configuration exists. The untracked `.shiploop-improve/` tree is the current run’s allowed child evidence and is not product implementation or a reusable project convention.

The current user request is the only accepted product-intent source. The supplied platform/API documents are verified local contracts for this controlled fixture; they are not deployment receipts. The selected frontend-design guidance remains applicable (digest `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`) and will inform later component, interaction, and skin decisions.

## Boundary findings

- **Runtime:** static embedded client; same-origin bundled assets only; no inline script/style, CDN, deployed server runtime, or persistent WebSocket. Same-origin HTTPS API requests are permitted.
- **Authority/state:** host owns identity/authorization; API owns durable export/job state; client will own presentation/pending intent only. Hidden-page suspension requires foreground reconciliation against API state.
- **API contract:** visible polling, operation-identity reconciliation after lost POST confirmation, and same-origin download only after a current complete response are established. Response vocabulary, pagination/collection details, error shapes, same-ID repeat semantics, and reload-safe operation-identity retention remain unresolved.
- **Development/test/delivery topology:** detailed in [environment-lifecycle.md](environment-lifecycle.md). No current build/test/delivery route exists; no remote access or consumer verification is available.

## Baseline and readiness

The actual environment probe and missing-suite classification are recorded in [discovery-baseline.md](../evidence/discovery-baseline.md). The repository has no existing client implementation to validate and no executable behavior suite. This is an explicit test-bootstrap prerequisite, not a passing baseline. Future feature implementation must not depend on the probe as evidence of UI/API behavior.

## Consequential research frontier

Research/specification must resolve or leave open, with a stated later owner:

1. Static technology/asset strategy that fits the target CSP and does not rely on runtime server, inline assets, or external CDN fonts/scripts.
2. API/data schema and semantics necessary for the request flow, including collection selection, statuses, error/retry eligibility, operation reconciliation, revisions, and completed-download transitions.
3. Client lifecycle and recovery policy for visible polling, foreground reconciliation, stale responses, duplicate activation, lost confirmation, and storage/reload constraints.
4. Test/preview surfaces: a repeatable local route for client logic and static assets; a browser route for keyboard, narrow layout, semantic feedback, and reduced motion; and the gap between local evidence and an authorized embedded-host/consumer observation.

## Planning implication

The later plan needs preparation before feature work: choose/verify the static build route, bootstrap tests, and make API fixture/contract gaps explicit. It must preserve the controlled-fixture/deployed-target distinction and route any delivery requirement through an owner-authorized release plan. No installation, provisioning, remote request, source edit, commit, deployment, or publish action occurred in discovery.
