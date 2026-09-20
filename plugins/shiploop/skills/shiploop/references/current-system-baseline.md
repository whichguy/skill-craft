# Recover the current system before planning changes

This is a discovery output within the existing lifecycle, not another stage or
an approved requirements generator. Keep the prior system, incoming change and
maintained product knowledge recoverable through ordinary notes and references.

## Establish or refresh

Read README first as the principal product overview, alongside applicable AGENTS
instructions. Follow relevant usage, architecture, API, operations and test links;
locate maintained specs and decisions. A README can be the existing contract home.
An absent `SHIPLOOP.md` or a first ShipLoop invocation does not make a system new.

For an existing implementation, follow the unchanged
[initial repository baseline](execution-planning.md#initial-repository-baseline)
before further verification or product edits. Record executed/skipped checks,
failures and access/setup gaps; the recovered spec does not replace that baseline.

Classify the starting point from evidence:

- **Existing with an adequate baseline:** reuse its relevant sections, checking
  scope, source identity/freshness, cross-cutting conditions and evidence limits.
- **Existing without an adequate baseline:** reconstruct the missing description
  from README, linked docs, relevant code/tests and authorized read-only system
  observations. Accepted requirements may define intent without establishing
  current behavior; preserve their authority while recovering the latter.
  Scattered README/code/test facts are recovery inputs, not automatically an
  adequate baseline. Synthesize them unless an existing document or linked set
  already supplies the scoped, source-bounded account consumers can reopen.
- **Stale, partial or conflicting baseline:** retain the earlier account and
  re-investigate affected sections. Missing access is a gap, not evidence that
  the feature or system is absent.
- **Genuinely new:** record the evidence and lack of prior implemented behavior;
  define new intent in the incoming spec without fabricating an as-is product.

For first recovery, produce a shallow overview of the known system: purpose,
actors/entrypoints, major capabilities and boundaries. Deepen the requested slice
and cross-cutting state, interface, failure and quality constraints. Record what
was not inspected. Do not make an exhaustive legacy rewrite a prerequisite unless
the user requested it; do not limit the overview to the new feature alone.

Retain a concise baseline in the run's discovery notes, for example
`notes/current-system-baseline.md`, or reference sufficient existing material at
a retrievable immutable revision. Include its selected locator in the discovery
result's `evidence_refs` and name its intended durable documentation home.
Research resolves material unknowns before dependent spec/planning work. A useful
partial account can be recorded while affected work remains unready.

## Evidence and authority

For each material behavior or constraint, use an existing ID or stable heading
and give its exact source section/symbol or response-receipt field. Record the
repository/content revision, or remote target/version/observation time, scope
and verification limits. A Git HEAD alone does not identify dirty working content;
retain relevant non-secret content snapshots/digests when no immutable source
version captures what was inspected.

Distinguish **documented promises**, **accepted requirements** with their decision
basis, **observed implementation**, **runtime-verified behavior**, **inference**,
and **unknown or conflicting claims**. These categories describe evidence, not
a new required record schema. README is central evidence for product promises;
tests/code show implementation; a runtime probe establishes only what it exercised.
Do not infer an SLA, policy, approval or complete coverage from those observations.

Preserve material disagreements instead of silently choosing the newest source
or blessing a bug. Resolve a consequential intent/implementation conflict through
the relevant evidence or user decision before dependent changes. Synthetic data
stays fixture evidence and cannot choose a production contract. Read-only discovery
does not authorize infrastructure setup, deployment, or remote writes.

Keep three logical records; reuse existing homes instead of copying full specs:

| Record | Meaning and lifetime |
| --- | --- |
| Prior baseline for this run | As-of documented/observed behavior, evidence and limits, captured before the change; a frozen note or retrievable immutable revision. |
| Incoming change spec | This request's delta, acceptance criteria and preserve/add/modify/retire decisions, with user-request/decision basis and baseline references. |
| Maintained product knowledge | Current cumulative accepted intent and separately labeled recovered observations, outside disposable run storage, revalidated by later requests. |

Once consumed, do not silently rewrite the prior baseline to match changed code.
Keep its original as-of account; record corrections/new evidence in an addendum
or new snapshot and update current consumer references through the active
protocol's correction route. A historical test pass or approval is not current
verification or authority.

## Remote-only systems

With no local source repository, identify a durable local project documentation
directory as the explicit non-Git/in-place `--repo` under the existing entry
policy. Keep the run directory separate. This local knowledge home does not
claim to be the remote code repository. Use an already selected project root
when suitable; obtain a missing location decision only when it cannot be inferred.
Do not invent a remote target, create Git solely for discovery, or silently bind
an unrelated account. README-equivalent operator/API docs can supply the overview;
record their absence when unavailable.

Keep service/account/tenant/environment, principal visibility, version/date and
safe receipt locators distinct from the local documentation root. Inspect relevant
readable interface contracts and authorized read responses; preserve filters,
pagination, denied access and unsampled surfaces. Tool enumeration does not prove
successful access, write permission or deployed behavior. A queued operation is
not completed, and a denied read does not prove that a feature is absent. Use
[platform discovery](platform-discovery.md#safe-observations-and-authority) when deeper remote behavior
matters. A local or empty documentation-directory test cannot establish remote
health; retain unavailable relevant checks as gaps, not successful N/A.

## Planning and review handoff

Research and spec reopen the selected baseline and its limits. Reconcile the
incoming request with accepted intent and observed behavior using
[requirements definition](requirements-definition.md). Record concrete before/after
behavior and preserve/add/modify/retire decisions; uncertainty about a consequential
existing behavior is a discovery prerequisite, not a license to guess.
The current user's explicit request supplies authority for its requested delta;
missing historical approval is not a reason to reconfirm that request. Record
reasonable in-scope design choices as decisions with rationale, not invented user
requirements. Gate only work dependent on a material unresolved gap; unrelated
planning may proceed under the existing stage and scope rules.

Test strategy, global planning and each affected step-plan carry selected baseline
sections, incoming-spec sections, check locators and revalidation conditions in
ordinary `evidence_refs` and work-item `context`. Demonstrate consumption through
the preservation decisions and corresponding checks. A link to this guide alone
does not identify the product baseline. Reopen the actual sources after a cold
restart; missing, stale or inaccessible material remains a visible gap.

Pass those same selected references into the actual Improve child's existing
contract before its first review. Review for lost conditions, observations promoted
to intent, scope/target drift and unsupported completeness. Follow the existing
child correction/incomplete route when material context was omitted; do not edit
runtime state or create a second review loop. The runtime preserves supplied
locator text; it does not prove that the model opened or understood the source.

## Retain across runs

During authorized documentation work, retain useful recovered knowledge in the
existing product documentation home. A small README or existing system/architecture
section may suffice; otherwise `docs/current-system.md` is a descriptive fallback.
Accepted requirements keep their existing home, with the existing
[`docs/requirements.md` fallback](project-knowledge.md#choose-one-authoritative-home).
Keep these roles distinct, even if both fit in one document. Link selected homes
from README and `SHIPLOOP.md`; do not duplicate the full contents in both indexes.

Plan this persistence work explicitly when discovery created only run notes,
including documentation-only changes where appropriate. Document/carry-forward,
product acceptance and handoff reconcile accepted deltas, observed behavior and
actual checks while retaining pending obligations. Verify durable links and
necessary knowledge from the returned project, without the old run directory or
discarded execution worktree. For non-Git projects use retained as-of copies or
receipts instead of assuming Git history exists. If durable retention is outside
scope or unavailable, report the remaining obligation rather than claim success.

For a new request, read and revalidate maintained knowledge and capture that run's
prior baseline; do not replay the old task or reuse its receipts as completion.
Keep original and superseding rationale retrievable. Interrupted requests resume
their existing run. No new state fields, importer, mandatory ID taxonomy, host
launcher or lifecycle stage is introduced.
