# Cold-independent W1 independent assessment

Assessed before Improve correction. This assessment concerns the producer plan,
not any later Improve result or product execution.

## Assessed artifact identities

- `run/notes/w1-step-plan.md`: `c6fd2db8c0d3dc19347f3be88bb0c6c3e84b32227319d07ba8a221d4377ec814`
- `run/inbox/nav-bec327c2f88c48419ac498e62bd15d2f.md`: `5664255bd6d7b370ed7b7c6f62342c6d7d7d45944c510567cd10c70d23fe2461`
- `evidence/initial-packet.txt`: `4b8e3ca47b044f638508ede8e90b3760aec7df4deaaf2a882ea91cdaaeb85e27`

| Criterion | Actual evidence | Grade |
| --- | --- | --- |
| C1 | Current README, design, platform, API, source/DOM and frontend-design digest are reopened. The plan preserves components, interaction and navy/amber skin while describing the export-panel delta, focus, live status, narrow layout and reduced-motion behavior. | Pass |
| C2 | It identifies the missing authoritative `collectionId` source, rejects account/note/free-text guesses, and blocks mutation. The required source and recovery check are clear, but “obtain a repository-owned API or product-contract update” has no named owner or preparation producer before W1 implementation. | Partial — allocation gap |
| C3 | It uses same-origin request/response, no server/socket/CDN/inline assets, distinguishes service acceptance from browser display, handles lost confirmation with the documented operation lookup, and keeps reload loss honest. | Pass |

## Scope and API assessment

The selected item is W1, “Add remote export status using the existing API.” Its
`GET /api/exports`, `POST /api/exports`, operation lookup, and job-status use
matches the initial packet and `docs/api.md`. Persistent drafts remain in W2.
No scope-widening finding applies.

## Scope reconciliation addendum

The earlier “No scope-widening finding” conclusion was too categorical. The
source hierarchy is ambiguous:

- The actual product request in `product/README.md:3` asks for “notifications
  when a background export changes.” It does not expressly ask the user to
  create an export or download its artifact.
- The selected W1 title says “Add remote export status using the existing API.”
  Its seeded context expressly names `GET/POST /api/exports`, operation lookup,
  and job lookup. That makes those endpoints relevant to W1 investigation and
  permits the plan to identify their prerequisites; it does not clearly turn
  every available endpoint into a new required user journey.
- `docs/api.md` documents a capability, not accepted product intent. Existing
  implementation and an available API cannot override the request.

Therefore, the producer’s request-control, POST, lost-confirmation and download
design is **ambiguous rather than clearly unauthorized or clearly required**.
The plan should retain it as a proposed expansion requiring reconciliation with
the maintained request, or constrain W1 to observing existing background export
changes. This is not counted as a preregistered C1–C3 failure and does not alter
P1: the collection-ID supplier/owner gap remains material if request creation is
retained.

## Actionable finding

**P1 — allocate the collection-source prerequisite.** The plan correctly says
the `collectionId` source must be established before POSTing an export request,
but has no responsible work item or named external owner for that product/API
contract. Under frozen environment and initial-plan policies, allocate a
preparation producer before W1 with a concrete supplier, definition of done and
readiness check; otherwise leave W1 blocked with a named owner and correction
route. Do not infer the ID from account, note, or free text.

## Fixture confounds (not source gaps)

- The static product fixture lacks `.git`; hashes correctly substitute for a revision.
- The v2 probe and API contract are controlled fixture facts, not deployment evidence.
- Synthetic predecessor labels are not accepted as producer/Improve evidence.

## Policy basis

- `frozen/shiploop/references/environment-lifecycle.md`, “Plan preparation before
  its first consumer”: a needed precondition receives a producer before its consumer.
- `frozen/shiploop/references/requirements-definition.md`, “Initial-plan
  reconciliation”: map each architecture/state obligation to owner, supplier and check.
