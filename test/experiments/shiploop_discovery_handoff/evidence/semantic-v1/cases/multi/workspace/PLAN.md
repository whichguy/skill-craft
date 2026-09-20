# Conditional delivery outline — draft only

## Retained facts

- This is synthetic discovery, not an accepted design, implementation, or live-tenant proof. The current synthetic CRM target is `tenant-green` with runtime principal `crm-review-service`; the document target is `folder-shared`, where `document-worker` write access is denied.
- `ReviewState` is present with `operation_id`, `status`, and `revision`, but uniqueness, atomic/conditional updates, and schema-migration authority are unverified.
- `shared workflow-state.json` is document-project-local and cannot exclude external writers. Document acceptance is only “queued, not completed”; processor, recovery owner, and lost-acknowledgement handling are unknown.
- The retained local baseline passed only an alias-binding fixture. It is not evidence of remote authority, execution, persistence, completion, or consumer behavior.

Evidence: [SHIPLOOP.md](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v1/cases/multi/workspace/SHIPLOOP.md), [DISCOVERY.md](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v1/cases/multi/workspace/DISCOVERY.md), [BASELINE.txt](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v1/cases/multi/workspace/BASELINE.txt), [environment note](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v1/cases/multi/workspace/docs/environment.md), and [synthetic receipts](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v1/cases/multi/tool-receipts/probes.jsonl).

## Proposal, pending acceptance

Assess a CRM-owned operation record: a CRM review creates an operation ID/revision; a separately running document worker creates the document; a revision-aware completion writes document ID and terminal state; CRM reads that state. This is a candidate only, not accepted scope or specification.

## Ordered conditional work

1. **Authorize and identify the boundary.** An accountable owner must select the remote document target and grant the minimum unattended worker write permission. Revalidate principal, target, and permission at execution time.
2. **Define the operation contract.** Accept requirements for durable acceptance, pending/terminal states, retry, duplicate, stale-worker, and lost-acknowledgement behavior; name processor and recovery owners and the authoritative CRM read-back consumer.
3. **Prove CRM state semantics.** Establish `ReviewState` uniqueness, conditional-write/atomicity behavior, and migration permission. The operation/revision design cannot proceed without these facts.
4. **Establish delivery and consumer route.** Identify remote runtime, deployment/promote/rollback owner, configuration, and the exact CRM surface that reads a stable terminal state/document ID.
5. **Implement only after steps 1–4 are ready.** Change the selected CRM state model, worker, completion path, and consumer/read-back path; keep workstation independence and conditional completion as design constraints.
6. **Verify at the real boundary.** Use target-authorized checks for an operation through remote completion and CRM read-back, including duplicate/stale work and crash after acknowledgement before processing. Retain local checks separately. Document recovery and release evidence before acceptance.

## Eligibility and missing handoff

Eligible now: this conditional plan and owner-facing evidence/requirement requests. No implementation, integration, deployment, or consumer end-to-end work is eligible.

Consumers blocked on missing evidence: the document worker needs permission/target proof; the CRM review/read-back consumer needs state and concurrency semantics; processor/recovery operations need ownership and terminal-state rules; release and test consumers need runtime, delivery, and target-compatible verification routes.

No accepted requirements, product specification, test strategy, or Improve evidence was supplied to this cold sample. The packet’s predecessor labels are synthetic and are not carried forward as acceptance. Reopen all listed evidence before any later plan or execution; the dated `tenant-blue` note is historical only.
