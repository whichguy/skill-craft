# Intake Improve — review one

## Scope, authority, and sources

This is one complete actual Improve review cycle for the pending `intake` producer action `nav-3198ccc6204f4d208922cc7023893ea0`. Reviewed candidate: `<study>/new/run/notes/intake.md`; parent result: `<study>/new/run/inbox/nav-3198ccc6204f4d208922cc7023893ea0.md`. Rechecked `README.md`, `docs/platform.md`, `docs/api.md`, `host-observation.json`, `scripts/probe_environment.py`, the selected Improve/Until Loop binding, and the relevant maintained-requirements and interaction-design guidance. Read the sole reachable Git commit `ec3243d658e24304b306749bc361869154fc4660` in full. The immutable authority permits only this child evidence tree; it forbids product/run-note edits, commits, installs, deployments, and remote writes.

A fresh read-only independent reviewer inspected the same candidate and sources without being told a desired classification. Its observations were triaged against the current API/platform facts, rather than accepted automatically.

## Findings and disposition

| ID | Severity | Finding | Evidence / disposition |
| --- | --- | --- | --- |
| I-1 | material | The intake calls `clientOperationId` transient presentation state even though lost POST confirmation must be reconciled through that identity. A reload before confirmation could lose the only reconciliation key and enable a duplicate retry. | Accepted. The final accepted intake result must state that operation-ID retention/reload recovery is an unresolved design/research question under `client_persistent_storage: not_assessed`; it must not imply a durable mechanism. |
| I-2 | material | The intake notices incomplete response-schema information but does not explicitly carry status/transition vocabulary, error shapes, collection/pagination data, operation-lookup outcomes, and same-ID repeat-POST behavior as discovery questions. | Accepted. Carry these as bounded API-contract questions needed for UI state, accessible failure/retry behavior, and stale-response handling. |
| I-3 | trivial wording defect with a consequential correction | The intake says the API alone authorizes account scope, while the platform contract says the host controls authorization and account identity. | Accepted. Correct the model: host controls identity/authorization; API owns export/job state within that host-authorized scope. |
| I-4 | material | “Failure state with a recoverable action” is not established by the request or API contract. | Accepted. Keep a visible failure status as requested, but treat retry/recovery semantics as API-dependent and unresolved. |

The reviewer also confirmed that the candidate correctly distinguishes controlled fixture evidence from a deployed-host or consumer receipt.

## Authorized correction plan and application

Because the child contract forbids editing the parent intake note/result, no source or run-note rewrite was made. The authorized application is this review record plus a planned `final_result` in the actual parent completion evidence: it will preserve the producer outcome and authority while correcting the accepted intake summary/evidence references to carry I-1 through I-4. The immutable original note remains historical evidence of the first producer attempt; it will not be treated as the final accepted decision record after import.

## Validation and assessment

Actual checks and their limits are recorded in [checks-cycle-one.md](checks-cycle-one.md). Product source remains unchanged; the observed untracked `.shiploop-improve/` directory contains only allowed runtime/record material. The findings are material to later interaction and API planning, so this review is classified `non-trivial`. The substantive exit condition is not yet satisfied and a further review/correction-assessment iteration is authorized.
