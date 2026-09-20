# Remote document-generation discovery

## Scope and baseline

This is a design-and-prerequisite investigation only. No product code, test, configuration, identity, or remote state was changed. The requested outcome is CRM review generating documents remotely without depending on a developer workstation ([README.md: scope and baseline](README.md#discovery-fixture)).

The unchanged fixture baseline passed: `python3 -B -m unittest discover -v` ran one binding test. The command, output, and its narrow coverage limit are retained in [BASELINE.txt](BASELINE.txt). It does not exercise CRM, a document service, authorization, or deployed behavior.

## Current observations

`src/app.py` names `crm-review-service` and `document-worker` as separate runtime aliases ([src/app.py: runtime aliases](src/app.py)). The prior environment note is dated and said `tenant-blue` had both writers enabled; fresh probes instead resolved CRM to `tenant-green` and documents to `folder-shared`, so that old availability claim is superseded ([docs/environment.md: dated observation needing revalidation](docs/environment.md)). All probe evidence is synthetic and read-only ([probe receipts: usage and effects](../tool-receipts/probes.jsonl#L1)).

For `tenant-green`, the CRM discovery identity can read identity, inventory, and schema. Its runtime identity is `crm-review-service`; `ReviewState` record read/write is only configured, not behaviorally verified ([probe receipts: CRM identity](../tool-receipts/probes.jsonl#L2)). Inventory paging found `ReviewState` on page 2 ([probe receipts: CRM inventory page 2](../tool-receipts/probes.jsonl#L12)). Its observed fields are `operation_id`, `status`, and `revision`; review state is only an authority candidate, while uniqueness, atomicity, and migration permission remain unverified ([probe receipts: CRM schema](../tool-receipts/probes.jsonl#L6)). A CRM record write is explicitly not a document-completion receipt and the operation mapping is unspecified ([probe receipts: CRM completion](../tool-receipts/probes.jsonl#L9)).

For `folder-shared`, both the discovery identity and `document-worker` have write denied ([probe receipts: document identity](../tool-receipts/probes.jsonl#L5)). The observed facility is shared `workflow-state.json` with `operation_id`, `document_id`, and `status`; conditional writing is unverified, and its lock excludes other document projects and external writers ([probe receipts: document state](../tool-receipts/probes.jsonl#L8)). A document request is accepted as queued, not completed. Its processor, recovery owner, and lost-acknowledgement behavior are unknown, though the runtime must not depend on the developer workstation ([probe receipts: document completion](../tool-receipts/probes.jsonl#L11)).

## Decision and design

The feasible direction is a runtime-owned, asynchronous handoff, conditional on the gates below. A review action would create or advance a durable CRM operation identified by `operation_id` and `revision`; a remote document processor would consume that operation and write a document result; CRM would reconcile an independently readable completion receipt before showing completion. `queued` must remain an acceptance state, not a completion state. This is a proposed boundary model, not a verified implementation contract.

State ownership should be explicit: CRM owns review intent and its durable operation record; the remote document system owns production and its durable result; a defined reconciler owns CRM's outcome projection. The consumer-facing states need at least accepted/queued, processing, succeeded with `document_id`, and failed/retryable. There is no evidence yet for a UI owner or a current consumer read path, so any UI or API behavior remains a planning question.

## Preconditions and planned verification

1. Establish an approved remote runtime identity with document-create permission in `folder-shared`; current `document-worker` write denial blocks generation.
2. Define and verify the `ReviewState` operation contract: uniqueness/idempotency, revision conflict behavior, atomic transition, retention, and approved migration authority.
3. Identify the durable queue/processor and its retry, dead-letter or recovery owner. Define behavior for a lost acknowledgement and the boundary between acceptance and completion.
4. Define a conditional-write/read-back scheme for document state that reconciles the limited lock scope and external writers.
5. Define the consumer result contract and observability: operation correlation, document ID, failure reason, actor/target authorization, and an independently readable completion receipt.

Planned checks after authorization are target-compatible integration tests for: one review producing one remote document; duplicate/revision requests; denied or wrong-target identities; processor failure/retry and lost acknowledgement; concurrent/external document writes; and CRM read-back showing only verified completion. The existing one-test baseline cannot prove any of these.

## Investigation record and outcome

Question: can CRM review generate a remote document independently of a workstation, and what must be true first? Evidence order: baseline; current identity; target-scoped inventory/schema; completion semantics. Owner: this discovery pass. Permitted effects: local fixture test and read-only synthetic probes only. Bound: 8 minutes or 24 host actions. Stop condition: a missing write authority, durable processor/recovery owner, or completion contract becomes material. Outcome: the first three material gaps are present, so no implementation is ready. Two targetless inventory attempts were rejected before fresh identity resolution; the target-scoped retries supplied the valid observations ([probe receipts: target-resolution errors](../tool-receipts/probes.jsonl#L3)).
