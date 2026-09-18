# Outer closure: coverage, quality, publication, handoff

Outer work begins only after every current DAG step is merged through the same
full inner loop. It is not a shortcut for patching code outside a step.
Read current `knowledge` as well as the approved environment/spec baselines.
Cross-step observations retain scope, provenance and revalidation guidance;
an old readiness observation is not proof of current external availability.
Reassess the research conclusions on which acceptance depends, including their
source/version and revalidation triggers. A new material research gap uses a
corrective research DAG step and its full Improve loop, with consumers ordered
after it; a conflicting frozen contract requires direction. Do not relabel an
unavailable source or failed probe as a trivial review. See
[Later research discoveries](../research-loop.md#later-discoveries).
Use [Deployment and handoff](../testing-and-documentation.md#deployment-and-handoff)
for the canonical whole-product test/documentation review; it is host guidance
within these stages, not a new result schema or automatic semantic proof.

## Coverage

Run the bound Review Coverage activity. The ledger must be complete, bound to
the correct plan, actually tracked, and clean in the repository. A prose claim,
foreign ledger, untracked file, or committed:no record is not closure. Use an
already explicit Review Coverage waiver only where its bound plan genuinely
permits one; do not author a waiver to escape review.

If coverage discovers a real product change, use replan with an action-bound
result that supplies plan_decision revise, plan_reason, plan, and complete DAG.
The revision adds a corrective pending step; completed work remains intact and
the new step receives the full implement/Improve/final-verify/post-inner loop.
Its review and carry-forward checkpoint consume current project knowledge;
the generic ShipLoop improvement journal remains a separate proposal list.

## Quality

Run the whole-product lint and integration/acceptance manifest through verify.
Map test acceptance entries to every exact `lifecycle.acceptance` string from
`context --section lifecycle`, not the prior step's `produces`.
This always occurs, whether lifecycle quality is true or false. When quality is
true, the completion result also includes a quality_review: the host's focused
review of integration risks and outcomes. The selection of an integration check
is implementation policy informed by the frozen contract—not an invented claim
that the user named a particular test. Select browser, service, and API views
from whole-product risk and surface, not as a mandatory ladder; compare each
case's expected result with actual evidence and environment/readiness identity.
A required unavailable, blocked, or unrun check remains unfinished, never `N/A`
or passed.

Reconcile the whole product's prompt-linked sequence flows, state invariants,
and transition cases, including cross-step failure/recovery behavior, using
[Traceability and review](../behavioral-requirements.md#traceability-and-review).
Passing isolated step tests does not establish whole-flow coverage. Link the
model and observed case evidence in handoff; retain honest scope/exclusions.

Quality failures remain unfinished. If quality learning requires another
corrective step, use the same action-bound replan path rather than editing
merged product code in the outer loop.

## Publication

Run publication only when lifecycle says outer-loop and the user authorized
the external effect. Before retrying, inspect existing delivery to avoid a
duplicate publish. Record artifact, entrypoint verification, and concrete
evidence in delivery.md. Local tests and a Git merge cannot prove a remote
deployment, URL, permission, or recipient state. If acceptance requires a real
deployment, its authorized deployment/readiness and dependent checks should
already have completed as DAG work before quality; outer publication adds only
final delivery-smoke evidence.

## Handoff

The handoff records checked acceptance, commands/evidence, known limitations,
delivery facts, and a prioritized summary of shiploop-improvements.md. Review
the generic proposal journal explicitly, supplying [] when no new proposal was
found. Do not apply these generic skill/script proposals during the delivery
run without separate authorization. Link the product README and concise
function/interface contracts, name actual tested environment/version and
passed/failed/blocked/not-run case outcomes, and keep run receipts/logs/session
state out of product documentation. The host must assess whether evidence and
documentation are semantically adequate; passing commands alone cannot do so.
