# Outer closure: coverage, quality, publication, handoff

Outer work begins only after every current DAG step is merged through the same
full inner loop. It is not a shortcut for patching code outside a step.

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

## Quality

Run the whole-product lint and integration/acceptance manifest through verify.
Map test acceptance entries to every exact `lifecycle.acceptance` string from
`context --section lifecycle`, not the prior step's `produces`.
This always occurs, whether lifecycle quality is true or false. When quality is
true, the completion result also includes a quality_review: the host's focused
review of integration risks and outcomes. The selection of an integration check
is implementation policy informed by the frozen contract—not an invented claim
that the user named a particular test.

Quality failures remain unfinished. If quality learning requires another
corrective step, use the same action-bound replan path rather than editing
merged product code in the outer loop.

## Publication

Run publication only when lifecycle says outer-loop and the user authorized
the external effect. Before retrying, inspect existing delivery to avoid a
duplicate publish. Record artifact, entrypoint verification, and concrete
evidence in delivery.md. Local tests and a Git merge cannot prove a remote
deployment, URL, permission, or recipient state.

## Handoff

The handoff records checked acceptance, commands/evidence, known limitations,
delivery facts, and a prioritized summary of shiploop-improvements.md. Review
the generic proposal journal explicitly, supplying [] when no new proposal was
found. Do not apply these generic skill/script proposals during the delivery
run without separate authorization.
