# Conditional remote document delivery plan (draft)

## Verified starting facts

The requested outcome is CRM review generating a document through a remote runtime, without a developer workstation. `crm-review-service` resolves to `tenant-green`; `document-worker` and the discovery identity are denied document writes in `folder-shared`. `ReviewState` exists with `operation_id`, `status`, and `revision`, but its uniqueness, atomicity, and migration authority are unverified. The shared document-state facility has limited locking and unverified conditional writes. A document request returns `queued`, which is acceptance rather than completion; its processor, recovery owner, and lost-acknowledgement behavior are unknown. The existing one-test fixture baseline is local only and proves none of these boundaries.

Evidence: `SHIPLOOP.md`; `DISCOVERY.md#remote-document-generation-discovery`; `../tool-receipts/probes.jsonl`; `BASELINE.txt`; `src/app.py`; `docs/environment.md`. The earlier `tenant-blue` writer-enabled statement is stale and must not be used as availability evidence.

## Proposed boundary, pending owner approval and verification

CRM should durably create or advance an idempotent review operation. A remote document processor should consume it, durably publish a result, and a reconciler should project an independently readable result into CRM. Consumer states should distinguish `queued`, `processing`, `succeeded` (with `document_id`), and retryable failure. This is a design proposal, not an accepted or implemented contract.

## Ordered conditional work

1. **Establish authority and target compatibility.** The owning platform operator must identify an approved remote runtime principal and document-create permission in `folder-shared`; record target-scoped capability evidence. Revalidate current tenant/folder identities before any mutation. The document producer and its integration checks are blocked until this gate passes.
2. **Define durable contracts.** The CRM/data owner must decide and verify `ReviewState` uniqueness, idempotency, revision-conflict behavior, atomic transitions, retention, and migration authority. The document-system owner must name the queue/processor, retry/dead-letter and recovery owner, and lost-acknowledgement behavior. The CRM request writer, processor, and recovery path need this evidence.
3. **Define result and concurrency semantics.** Specify document-state conditional-write/read-back behavior despite external writers and limited locks; define correlation, receipt authority, `document_id`, failure reason, and actor/target authorization. The reconciler and consumer API/UI need this evidence; CRM writes alone cannot prove completion.
4. **Implement only after gates 1–3.** Add the smallest runtime-owned CRM operation producer, remote processor integration, reconciler, and consumer-result surface that conform to the approved contracts. Preserve the no-workstation requirement and make `queued` visibly non-terminal.
5. **Run target-compatible verification after implementation.** Cover one review/one document, duplicate and revision requests, denied/wrong-target identity, processor failure/retry and lost acknowledgement, concurrent/external writes, and CRM read-back that reports only verified completion. Record real target receipts separately from the local fixture test.
6. **Document and release conditionally.** Publish operator recovery, ownership, permissions, correlation, and rollback/correction routes only after the target evidence exists. Revalidate every earlier synthetic observation before release.

## Readiness and eligibility

Eligible now: owner/authority clarification, contract research, detailed test design, and this conditional plan. Ineligible: remote writes, migration, processor work, integration tests, release, and consumer completion claims. If any required owner or evidence cannot be obtained, retain the affected consumer as blocked and revise this draft; do not substitute a CRM record write or a local test for a completion receipt.
