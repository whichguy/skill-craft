# Delivery authority readiness

Use this ordinary navigator guidance whenever discovery identifies a concrete
consumer, target or account, and operation that may affect an external boundary.
It applies whether or not the optional consumer-delivery declaration guard is
enabled. It adds no graph stage, result schema, parser, credential store, or
automatic deployment. A packet, policy file, login, or successful safe read
does not itself grant a write.

## Ask at the first concrete boundary

**The request is the grant when it names the target.** When the user's request
asks for the result to be delivered somewhere ("deploy it to my Salesforce
developer org", "publish it to my staging site"), that request authorizes this
run to make the non-destructive delivery of the project's own changes to that
target. At discovery, resolve the named target to exactly one concrete
target/account (for example the connected org behind the default alias) and
record the resolved grant in the discovery evidence: target, account ID, the
project's own changes only, no destructive changes to unrelated resources, this
run only. Do not ask the user to confirm it, do not plan a work item to record it,
and do not block on it later.

Ask only when the request does not settle it: the request names no delivery
target; discovery finds no matching target or more than one; the target is a
production or shared environment the request did not name; or the operation is
destructive beyond the project's own changes. Then ask once, at intake or
discovery, together with any other open question, and keep going: independent
work continues and only the dependent write waits. Never make recording an
approval a work item, and never stop mid-run to ask for authority the request
already gave.

When the request does not settle it: at discovery, after the consumer, target/account, and necessary operation are
concrete enough to name, check for an applicable explicit grant. If the
operation is necessary and no such grant is available, ask promptly; do not
defer the question solely because `release` is later in the graph.

Ask for the exact operation, target/account, environment, exclusions, and
expected effect. Also ask whether the user approves it for **this run only** or
as a **standing policy** for matching future work. Never assume that a reply or
one approval persists.

Silence, a login or access receipt, an old one-off approval/receipt, and an
agent-written policy are not grants. Do not test write permission by making the
change. An approved standing policy must itself be traceable to a user approval.

Independent work that is already authorized may continue in its assigned action.
Record the outstanding approval's owner and earliest gate, but do not perform
the necessary write or declare `release-plan` complete while that authority is
unresolved. Once the question is recorded, do not ask it again on every action:
discovery and other independent authorized work may continue, with the gap
blocking at the earliest dependent write or `release-plan`. A later browser or
access requirement does not erase this question.

After the user replies, recover the current action if needed, record the answer,
finish its assigned Improve work, and use the normal callback. The reply does
not create a new phase or itself complete discovery or planning.

## Reuse only a matching standing policy

Before reusing a user-approved standing policy, revalidate all of the following
against the current request and actual bindings:

- product and intended consumer;
- exact target and account/identity;
- operation and environment/access path;
- exclusions and user approval reference;
- current revocation or expiry state; and
- changed effects, including any broadened access, data exposure, or security
  impact.

The current request can narrow or override a standing policy: an explicit
source-only request wins over a policy that would otherwise allow a private
sync. An unchanged, still-valid policy needs no repeat approval for ordinary new
feature behavior within its approved scope. A mismatch, expired or revoked
policy, or changed effect outside that scope (including broader data, access, or
security impact) needs an actual user disposition before the operation. A
generated plan cannot repair or broaden a grant.

Retain an approved standing policy in an existing repository-owned `SHIPLOOP.md`,
`AGENTS.md`, or deployment/operations document and link it from the repository
knowledge index. Keep its user-approval reference, scope, exclusions, and
revalidation conditions there. Do not make a transient run note the only home of
a policy intended to persist.

## Record this run without a new ledger

Use the packet's existing canonical
[`notes/environment-lifecycle.md`](environment-lifecycle.md#durable-record-and-responsibility)
note for the current assessment. Record:

- whether the operation is necessary and the consumer/target/account/operation
  match inputs;
- actual sources read and current target, account, environment, and access
  binding evidence;
- the applicable grant, or the exact outstanding question, owner, and earliest
  gate; and
- required effect, identity, and consumer-behavior evidence, including any
  blocked verification.

Point the current result's existing `evidence_refs` at that note. It is a
host-authored assessment, not a new ledger or schema and not proof that the
grant, target, or observed behavior is authentic.

## Optional declaration-guard mapping

For a new run that explicitly opts into
[consumer delivery](consumer-delivery.md), map the same facts into its existing
fields: `necessity`/`basis`; `consumer`, `target`, `operation`, and `exclusions`;
`authority` (including a `repo-policy`'s user `approval_ref`); and required
effect, identity, and behavior obligations. Put the current-note locator in
ordinary `evidence_refs`.

The declaration guard checks field shape, consistency, and declared bindings;
it does not authenticate a policy, approval, source, remote effect, or browser
observation. It remains opt-in: do not enable it by default or retrofit it onto
an existing run.

## Reconcile scope and partial results

Before an Improve campaign converges, resolve contradictions such as a required
delivery in the specification but an optional update in the plan against the
original request and approved scope. Restore an accidental generated-plan
downgrade to the original requirement without asking for permission to correct
the plan. A genuine change to user-approved delivery scope needs an actual user
disposition. After correcting the contradiction, a downstream approval may
remain explicitly pending at its own gate without preventing this review's
convergence. Never erase the requirement to obtain a clean review.

If an authorized source synchronization succeeds but browser verification is
blocked (for example by login), retain the synchronization/effect and identity
evidence, mark consumer behavior blocked, and report the feature unverified.
Do not automatically repush or repeat the write merely to obtain a fresh
receipt. Restore appropriate access within scope and resume verification of the
same candidate; replan if the candidate, target, or authority changes.

For durable-context routing, also read
[project knowledge](project-knowledge.md) and
[environment lifecycle](environment-lifecycle.md).
