## Pass 1 — The ground

Added U-1–U-8 and C-1–C-14 for first and repeated imports, empty and invalid input, capacity, access refusals, interruption, maintenance, and rollback. The workspace contains no product source, account model, deployment configuration, or product instructions that establish inherited behavior or numeric limits.

## Pass 2 — Prerequisites

Added C-15–C-36 for discoverability, directory context, authority, submission guidance, CSV parsing and schema, ordinary account provisioning, result identity and visibility, retention, and the maintenance signal. Found no supplied account schema, address rules, tenancy model, or role names. Used ordinary provisioning as the observable reference wherever the product controls those facts.

## Pass 3 — Interactions

Added C-37–C-54 after comparing upload delivery, actor and directory context, concurrent import and single-user provisioning, status retrieval, account or policy changes, service failures, and maintenance controls. Identified explicit outcomes for overlap, late delivery, lost responses, and restarts. Profile and onboarding behavior remain the responsibility of normal provisioning, as the workspace gives no separate integration contract.

## Pass 4 — Runtime rules

Added C-55–C-60 for ingress body size, incomplete transport, request lifetime, production authentication, atomic write capacity, and required provisioning inputs. No hosting runtime, ingress, backing store, or production configuration is supplied. Their numeric ceilings remain unconfirmed in the affected clauses. Found no identified external platform with a publication or approval rule to specify.

## Pass 5 — Existing behavior and invariants

Added C-61–C-72 for single-user provisioning, normal management of imported users, preservation of existing accounts, atomic visibility, onboarding, confidentiality, retention, and mutation safeguards. Found no existing audit, import, invitation, or account lifecycle documentation that establishes exact host-specific behavior. Kept those properties tied to ordinary provisioning or marked them unconfirmed where applicable.

## Pass 6 — Builder review

Revisited the full draft and added C-73–C-91. Split CSV quoting into its separately observable rules. Defined diagnostic line numbers, admission versus validation failures, activity fields, empty files, limit measurement, reference scoping and expiry, sign-out, and the first deployment and rollback boundaries. Corrected source labels for choices and separated maintenance from status access. Found no evidence of a second file schema, another input path, or a specific runtime to name.

## Pass 7 — Outcomes from the caller's side

Added U-9 and C-92–C-98 for overlapping groups, maintenance authorization, unreadable results, unaccepted input cleanup, receipt confirmation, outcome retention through rollback, and the access-refusal boundary. Rechecked which facts could be observed through the product and replaced parser-only examples with submission results. Found no additional CSV schema or output format required by recovery.

## Pass 8 — Admission and recovery cross-check

Added C-99 for a complete upload that reaches an unavailable intake service. Clarified that a retry of an interrupted transfer can be the first eligible delivery for a reference, distinguished protected-reference refusals from an authorized submitter's replay after expiry, and checked that the two product ceilings can be satisfied together. Found no additional terminal state needed to represent an unaccepted upload.

## Pass 9 — Control and maintenance boundaries

Added C-100 to distinguish selecting a file from explicitly submitting it. Added C-101 to keep an unavailable pending count from being mistaken for a completed drain. Reviewed the upload and maintenance controls against in-flight work and found no additional control needed to finish or recover an accepted attempt.

## Pass 10 — Full stopping pass

Read U-1–U-9 and C-1–C-101 from the start as a builder. Traced selection, admission, validation, commit, result retrieval, expiry, and maintenance in order, then checked overlapping submissions, authority changes, unavailable dependencies, and rollback against those same boundaries. Checked observability, separately stated choices, enumerated members, inclusive limits, and unconfirmed host constraints. Verified the requested form and gapless numbering. This pass found no behavior to add or correct and left the specification unchanged.
