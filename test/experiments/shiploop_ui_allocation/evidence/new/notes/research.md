# Research — Archive Exports client

## Evidence boundary

This research re-read the accepted discovery correction, the local README/platform/API contracts, controlled host observation, source digests, Git history, selected design guidance, and the local runtime inventory. The source/probe evidence establishes fixture constraints and local development capabilities only. It does not establish a deployed target, live API response, browser result, consumer session, or delivery action.

## Decisions supported for planning

1. **Client shape:** plan a dependency-free static HTML, CSS, and external ES-module JavaScript client. Keep assets same-origin and external; do not select a framework, package installation, server runtime, WebSocket, inline code, or CDN asset.
2. **Invocation and recovery:** plan native browser request/response calls from an external module. `GET /api/exports` supplies current authorized status/revisions; `POST /api/exports` uses `collectionId` and `clientOperationId`; a lost confirmation reconciles through `GET /api/operations/:clientOperationId`; current job state/download eligibility comes from `GET /api/exports/:jobId`. Poll only while visible and reconcile on foreground; notifications only invalidate views.
3. **Authority:** the host controls account identity/authorization; the API owns durable export/job state; the client retains only transient presentation and pending intent. The fixture has no remote deployment authority. A consumer-session binding was not supplied or revalidated, so consumer validation is unperformed and unverified.
4. **Unknown API details:** do not invent status enums, error vocabulary, repeat-POST behavior, retries, pagination, collection shape, download-error behavior, or client persistence. The first implementation-preparation step must bind an approved local API contract fixture or owner decision for those details. Until then, an unacknowledged request must not be represented as success.
5. **Visual premise:** use an archive-ledger system: graphite `#17212B`, catalog blue `#294C67`, paper gray `#E2E8E5`, circulation green `#3A765C`, and signal rust `#A84638`; restrained serif collection titles, quiet sans controls, and monospace job metadata. A vertical accession strip anchors each export row’s state/date. Keep keyboard focus visible, use accessible status text, adapt hierarchy for narrow screens, and suppress state motion for reduced-motion preference. This is a planning decision, not a rendered or user-tested interface.
6. **Verification:** native Node v25.9.0 can later run deterministic state/adapter tests through `node:test`; a loopback-only Python static server can support local manual browser checks. No product-local Playwright, Vite, React, jsdom, or package manifest was found, so none is selected. Local preview cannot prove the embedded target or consumer behavior.
7. **Delivery and consumer observation:** they are necessary later lanes for the requested usable client but remain blocked on a real target and owner-authorized operation. No access request is appropriate yet because no target/account alias or concrete operation was supplied.

## Actor → channel → state → outcome

An authorized archivist selects a collection and requests an export through the static client. The client sends same-origin request/response calls to the API. The API durably accepts an operation before confirmation and owns job state. If confirmation is lost, the client reconciles the same operation ID. While visible, the client reads current state; after background suspension it rereads authoritative state. A completed download action appears only when a current complete response supplies a same-origin path. The host controls identity and may suspend the page.

## Evidence locators and revalidation

- Product request and missing baseline: `<study>/new/product/README.md`, `<study>/new/run/evidence/discovery-baseline.md`
- Target/API contract: `<study>/new/product/docs/platform.md`, `<study>/new/product/docs/api.md`, `<study>/new/run/evidence/discovery-probe-stdout.json`
- Local runtime inventory: `<study>/new/run/evidence/research-runtime-inventory-stdout.json`
- Design premise: `<study>/capabilities/frontend-design/SKILL.md`
- Corrected delivery/consumer boundary: `<study>/new/product/.shiploop-improve/nav-2148a17cdff14eef8c90236660d96142/nav-70d0ab5e215b4977a1131b00914b8baa/reviews/discovery-corrected-decision.md`

Revalidate the API fixture before adapter/test authoring, target policy before build choice, and real target/account/consumer authority before any delivery or consumer claim. No product source, dependency, target, consumer session, or deployment was changed.
