# CRM remote document generation discovery

## Scope and evidence

This is a discovery-only record for the request in `README.md:3`: CRM review
must generate remote documents independently of a developer workstation. No
product, remote, credential, deployment, or callback action was performed.

The local source identifies the intended runtime aliases as
`crm-review-service` and `document-worker` (`src/app.py:1-2`). The historical
note says an earlier synthetic inventory used `tenant-blue` and both writers
were enabled (`docs/environment.md:3`), but it explicitly requires
revalidation. Current synthetic probe receipts at
`/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v2/cases/multi/tool-receipts/probes.jsonl`
conflict with that dated claim and are the current observation for this slice.

## Baseline and investigation method

The unchanged local fixture baseline passed; the exact command, output, and
coverage limit are retained in `BASELINE.txt`. It only checks the CRM alias and
does not prove a remote capability.

A compact investigation plan was necessary because the historical/current
environment observations conflict and the remote write/completion boundary has
independent unknown owners. Question: can an authorized remote runtime accept a
CRM review operation and durably complete a document without the workstation?
Permitted route: the documented read-only synthetic CLI, first resolving identity
then targeted inventory/schema/completion reads. Stop condition: record the
smallest prerequisite set and do not design implementation while authority or
completion ownership remains unknown. The target-free CRM inventory attempt was
rejected; after identity, the target-specific reads below succeeded.

## Current-system observations

- **CRM, current synthetic target `tenant-green`:** the discovery principal is
  `discovery-reader`; `crm-review-service` is configured read/write for
  `ReviewState`, but that behavior is unverified. Paginated inventory returned
  `LegacyCache` then `ReviewState`. `ReviewState` exposes `operation_id`,
  `status`, and `revision`; uniqueness, atomicity, and migration permission are
  unverified. `ReviewState` is therefore only an authority *candidate*, not a
  selected contract.
- **Documents, current synthetic target `folder-shared`:** the discovery
  principal may read metadata, while runtime principal `document-worker` has
  write denied. An existing `shared workflow-state.json` exposes
  `operation_id`, `document_id`, and `status`; conditional write is unverified,
  and its lock excludes other document projects and external writers. It is a
  possible reusable facility only after its authority and concurrency contract
  are confirmed.
- **Completion:** the document route describes acceptance as "queued, not
  completed" and says the runtime must not depend on a developer workstation.
  Its processor, recovery owner, and lost-acknowledgement behavior are unknown.
  A queue acknowledgement therefore cannot be reported as document creation.

## Conditional design and prerequisites

The evidence supports a conditional remote flow: CRM records/submits an
operation identity, a remote document processor performs the work, and a
durable read-back associates the operation with a `document_id` and completion
state. The asynchronous acceptance boundary is queued; completion requires the
processor's durable result and reconciliation. This preserves the stated
workstation-independence requirement without claiming an implementation or
inventing a queue, schema, or state store.

Before any dependent implementation or target-compatible test, resolve:

1. A target-specific authorized document writer (or an explicitly selected
   alternative runtime); current `document-worker` write access is denied.
2. The remote processor and recovery owner, including crash/retry,
   lost-acknowledgement, and acceptance-versus-completion semantics.
3. Idempotency and concurrency: `operation_id` uniqueness, CRM atomicity,
   document conditional writes, and treatment of external writers/projects.
4. Whether CRM schema changes are needed and, if so, authorized migration
   permission and a preserved-state/read-back plan.

When authority exists, test the real boundary with a target-compatible,
non-workstation flow: CRM review → queued operation receipt → remote processor
completion/read-back with `document_id`. Include denied writer, duplicate
operation, concurrent/external writer, retry/lost acknowledgement, and remote
restart cases. The current local baseline cannot cover those cases.

## Limits and handoff

All remote observations are synthetic receipts, not production behavior or
authorization. No network, credential inspection, live remote read/write,
consumer check, provisioning, deployment, or branch-return route was available;
the workspace is not a Git repository, so CI/deployment behavior is unknown.
The prerequisites gate only remote document generation; they do not alter the
local discovery conclusion or baseline.
