# Environment preparation and promotion

Use this policy when investigating a new or existing system, planning work, or
crossing a development, test, or delivery boundary. Discover the actual topology;
do not require a sandbox/dev/stage/prod ladder, new accounts, or a deployment for
local-only work. Environment labels do not prove isolation or permission.

For new Git-backed runs, the [workspace helper](workspace-lifecycle.md) captures
the current branch's tracked working content before stage work. Its execution
checkout is already prepared; do not schedule a duplicate worktree setup item
or return into the source branch after each INNER item. Remote sandbox/staging
preparation still belongs to its planned producer. The final guarded local
return belongs after whole-candidate validation; treat it as a release operation
if branch integration itself activates deployment.

## Discover before planning code

Read the repo README, applicable instructions, existing environment/design notes,
deployment configuration and relevant automation. Follow the repository knowledge
index and [cross-run policy](project-knowledge.md) for prior-run artifacts and
persistent decisions; verify current applicability instead of replaying the old
request. Establish:

- Where code is edited, built, installed for development, tested, and ultimately
  consumed. Distinguish a local branch/worktree from remote runtime/data isolation.
- The actual targets, environment roles, connections and non-secret identities;
  which areas exist and can be reused, and which need authorized preparation.
- How code/artifacts/configuration move between areas: source sync, build,
  deployment, promotion, or another documented operation. Inspect commit, push,
  merge and CI triggers: a local-looking operation may update a shared service.
- Required approvals/access, data boundaries, baseline checks, fixtures, version
  compatibility, migration order, rollback/recovery, and cleanup ownership.
  Development must not silently share production data, credentials or callbacks.

Use safe reads and the [early-access policy](research-loop.md#early-access-readiness)
to surface concrete setup/auth needs promptly. Investigation and planning do not
create a sandbox, copy production data, change credentials, or deploy. Do not
interpret missing safe isolation as permission to work directly in production.
For a new repo, establish the intended boundaries without inventing existing
infrastructure; for an existing repo, reuse verified conventions and bindings.

## Plan preparation before its first consumer

Record which prerequisites are already ready, need work, are unresolved, or are
genuinely unnecessary, with evidence and the earliest activity needing them.
Separate environment preparation from deploying the implemented candidate and
from final consumer activation. A release-only staging prerequisite need not
block independent local coding; isolation needed for coding must precede it.
These are planning decisions, not permission to execute inside `plan` or
`plan-improve`. Even authorized setup waits for its script-assigned work item.

In **navigator mode**, use the existing ordered `work_items` from `plan` or
`plan-improve`. Put an explicit preparation producer before every dependent
feature item when setup is needed. The producer traverses the same INNER graph:
its implementation is authorized setup, its tests are readiness/baseline checks,
and its documentation/Improve/carry-forward concern that setup, not invented
feature code. No new stage, preparation flag, counter, or second scheduler is
needed. Do not demand the producer's own output before allowing it to run.

For each applicable item, retain the target/role, authority, definition of ready,
definition of done, expected readiness observations, inputs, and evidence/note
locators in its plan and `context`. Preparation may include a worktree, a sandbox
binding, configuration, synthetic/sanitized fixtures, or a minimal migration;
select only what the task requires. Keep the original run/repo identity and
record alternate worktree/remote target locators rather than starting a new run.
Ask before creating billable/shared resources or changing scope/access when not
already authorized. Reconcile partial setup before retrying or cleaning up.

At `step-plan` and before implementing, recheck the applicable readiness evidence
and bindings. A plan or directory name is not proof that setup succeeded. A
failed current prerequisite blocks dependent work; it cannot become N/A. An
existing ready environment needs no make-work setup item. A late requirement
within the current item's scope may update its plan/checks; otherwise block for
replanning direction. `carry-forward` can reorder only future work, not jump
backward or silently change the active item.

In **managed/legacy modes**, retain the recorded lifecycle protocol: authorized
environment-only setup can use `preparation: outer-before`; dependency-scoped
setup uses a DAG preparation producer; no separate setup uses `none`. Final
publication follows the selected DAG or outer-loop route. See
[platform discovery](platform-discovery.md#bootstrap-validation-and-publication-are-different-obligations).
Do not copy those schema fields into a navigator result.

## Carry the route into final delivery

During initial planning, assign each required candidate deployment, migration,
approval and check to a responsible work item or outer stage. If system tests
need a staged candidate, plan an authorized non-final deployment/validation
producer after the feature work and before `system-test`; waiting until final
`release` would be too late. A multi-hop route is a set of real dependencies,
not a reason to bypass a prerequisite or invent a fixed number of environments.

`carry-forward` and affected standalone Improve handoffs reconcile new
environment/deployment needs with the existing plan. `release-plan` reads that
record, revalidates current targets and readiness, and plans only the remaining
authorized consumer update or promotion. Keep intermediate test deployments
distinct from final delivery.
Track the exact candidate being promoted and whether a rebuild, configuration
change or migration invalidates earlier checks. Retain each hop's approval,
preconditions, expected effect, checks, stop/rollback conditions and owner;
approval for a sandbox is not approval for production.

`release` performs only the authorized remaining operation(s), checking the
prerequisites at each hop. Stop on failure/unknown outcome, retain partial
receipts, and reconcile before retrying. `release-verify` checks the intended
final consumer, not just the sandbox or staging URL. `handoff` reports actual
environment/candidate status and any authorized cleanup or outstanding owner.
Never delete a shared environment merely because the run ended.

## Release operation ownership

Use the final-delivery route above and durable record below; this section adds
neither a stage nor a cursor. For consequential ordered work—schema, data,
service, configuration, or cutover—retain the actual execution owner, exact
candidate and target, predecessor/prerequisites, authority, expected before/after
state, observation method, and recovery limit. An operation can be **accepted**,
**running**, then **terminal**; its effect is **verified** only after the required
operation postcondition is observed. Final consumer behavior belongs to
`release-verify`, after `release` returns through its standalone Improve handoff.
A lost reply or
receipt requires reconciliation against documented provider job/key lookup and
parameter-binding semantics; a local ID alone does not provide idempotency.

Prefer an existing capable runner only when its durable record owns the required
operation order/dependencies, authority, current state, and reconciliation.
Otherwise, an unresolved execution-owner or readiness gap blocks affected
operations. Navigator retains graph routing, not a sub-operation cursor; the
environment note, work-item `context`, and `evidence_refs` retain plans and
receipts rather than a second scheduler.

Where concurrent releases matter, use target-enforced conditional mutation,
lease, or other documented exclusion; a local lock cannot exclude another owner.
Preserve compatibility by making additive changes before consumer migration and
defer destructive contraction until old consumers are absent. An irreversible
effect has only forward recovery unless actual rollback support is established.
A local-only scope can make external release work N/A, but candidate identity and
current local consumer evidence remain required. A stage-scoped Improve may assess
a plan/check and record its handoff; it cannot execute or replay a release effect.

## Durable record and responsibility

The packet always supplies the canonical run locator
`notes/environment-lifecycle.md`. Create this host-authored note when relevant
environment work exists; it can hold the record or point to an existing
repository environment/deployment document rather than duplicate it. It records
knowledge and pending requirements, never another graph cursor. No empty note is
needed for genuinely local work without environment requirements.

Keep facts, proposed actions, authorization, observed results and pending outer
work distinct. Inner actions read this note and append new promotion/setup needs
without duplicating resolved entries. Carry useful evidence locators in dependent
results and work-item `context` too, but the fixed packet locator survives even
when a later result omits references. Outer stages must check this note and its
relevant linked material; a missing expected record is a gap, not N/A. Do not
store secrets or mistake the script-supplied path for proof the note exists.

Keep stable topology, decisions and revalidation guidance in repository-owned
environment/deployment documentation and link it from `SHIPLOOP.md`. Run notes
retain detailed receipts and pending operations; they must not be the only home
of environment knowledge needed by a later feature's fresh run.

The script enforces accepted action identity, work-item order and graph routing.
The host identifies the necessary producers, performs authorized operations and
checks readiness. Ordered declarations do not independently prove remote setup,
isolation, approval, a successful promotion, or even that the host included every
needed prerequisite. This policy adds no automatic provisioning or deployment.

The distinctions are consistent with
[GitHub's environment protection boundaries](https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments)
and [AWS's artifact reuse and staging checks](https://docs.aws.amazon.com/prescriptive-guidance/latest/choosing-git-branch-approach/staging-environment.html).
Those are examples to investigate, not required tools, account topology, or a
mandate to adopt their specific pipelines.
