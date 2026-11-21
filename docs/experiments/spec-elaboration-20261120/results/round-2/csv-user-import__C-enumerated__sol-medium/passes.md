## Pass 1 — the ground

Wrote the initial use cases and clauses for submission, repeats, empty and bounded input, rejection, failure, onboarding, operation, rollback, and concurrent creation. Found no product source, runtime manifest, deployed-service reference, or product-specific instructions in the workspace.

## Pass 2 — what the request takes for granted

Followed upload, CSV, admin, user, creation, and outcome into the prerequisites each introduced. Added the submission scope, CSV grammar and schema, identity and row validation, error reporting, atomic rejection, account defaults, onboarding, and result contract. Found no evidence for product-specific fields, roles, identity rules, or activation defaults. The specification uses ordinary directory semantics where they exist and states a baseline email contract.

## Pass 3 — the people who run it

Added rollout readiness, availability, settings and numeric ranges, operator authority, targeted stop, attempt lookup and filtering, diagnosis, control history, remediation, and rollback checks. Reviewed how to confirm activation and how existing records survive introduction and rollback. Found no established operator controls or immutable release-rollback system to describe.

## Pass 4 — where the parts meet

Walked submission, transfer, pending state, terminal outcome, directory state, authorization, settings, rollback, and onboarding against each other. Added attempt references, retry and replay boundaries, a commit deadline, stop and disable races, current authority and identity checks, reconciliation after a lost reply, and post-commit recovery. Found no need to order disjoint imports or to make activation delivery part of account commit.

## Pass 5 — the runtime's own rules

Verified the HTML browser rules for selected files, local paths, and picker type hints. Added environment-facing requirements for payload capacity, timeout recovery, runtime quota refusal, secure transport, and production readiness. Found no identified backend, hosting service, identity provider, or delivery service. Their platform-specific limits and prerequisites are explicitly unconfirmed where relevant.

## Pass 6 — what must stay true and what must never happen

Checked ordinary create, management permissions, editing, access lifecycle, and onboarding. Added direct submission parity, scope and result privacy, safe treatment of uploaded values, source-data lifetime, no side effects before commit, and protection against replayed onboarding or remediation of a replacement account. Found no evidence of additional existing user-management surfaces that need a named compatibility clause.

## Pass 7 — first builder read

Re-read use cases and clauses in order. Fixed the repeat rule for identities later released, split fallback identity matching from syntax, clarified byte accounting and deadlines, and added recovery when the caller loses the reference before seeing it. Closed gaps around unavailable and expired lookups, configuration changes on enabled deployments, rollback races, commit-time diagnostics, canceled selection, and visibility of a whole-batch commit. Found no need to choose polling, response codes, diagnostic wording, or an implementation technology.

## Pass 8 — second builder read

Compared the lifecycle rules against access checks, logging, validation precedence, and rollback. Closed gaps for duplicate start delivery, oversized uploads refused before full transfer, deleted directories, syntax locations, interrupted rollback, cleanup verification, and competing terminal decisions. Fixed cancellation language so disable leaves earlier rejections and failures intact, and scoped repeat-onboarding protection to accounts whose identities remain reserved. Found no need to introduce a second account lifecycle or an import-specific invitation policy.

## Pass 9 — inherited rules and remaining user decisions

Traced each inherited directory rule to the observable decision it makes for import. Added a fallback for identity reservation, distinguished domain syntax from creation policy, and specified precedence when commit sees multiple possible refusals. Added pre-enable readiness inspection and let admins distinguish a pending transfer from pending processing. Found no host-specific rule documentation or limits that could replace the explicitly unconfirmed values.

## Pass 10 — visibility and retention boundaries

Checked every view of import data, including direct calls, browser screens, operator records, and support records. Closed the gap for uploaded contents appearing in support logs, made the end of control-history access explicit, and defined operator authority across deployments. Found no additional raw-file access needed for corrections, remediation, or rollback.

## Pass 11 — complete builder read, no substantive additions

Read from U-1 through C-136. Checked the ordinary and refused flows for each actor, CSV record boundaries, every numeric limit and clock boundary, result visibility, duplicate and late delivery, commit versus cancellation, inherited account rules, operator recovery, and the end of retained access. Checked that every use case has a corresponding clause and that headings, labels, numbering, and references are consistent. This pass found nothing that required adding or changing a behavior.
