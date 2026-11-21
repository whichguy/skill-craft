## Pass 1 — Ground

Added activation, collection follow-up, payment, an empty cycle, backlog, invalid inputs, delivery trouble, pause, inspection and rollback. The workspace supplied no product code, existing billing contract, scheduler, hosting service or email provider. The request supplied no specific dates, amounts, cadence, channel or limits. Example amounts and dates in the spec illustrate the selected policies.

## Pass 2 — Prerequisites

Traced eligibility through issued and collectible invoice state, posted balances, due dates, billing day, recipient authority, and independent invoice identity. Traced activation through policy visibility and restart, then followed rejected destinations through correction. Recursion stopped at existing billing decisions about issuance, payment posting, and invoice ownership, plus ordinary facts about the passage of time. No evidence supported a required payment method, email wording, UI, or address hierarchy beyond the authoritative billing designation.

## Pass 3 — Interactions

Reviewed eligibility, activation, invoice edits, payment, recipient changes, overlapping evaluations, retry, late evidence, crash recovery and backlog progress against each other. Added the submission boundary, holds across restart, outcome reconciliation and fair progress. Found no required fixed processing order or email recall operation.

## Pass 4 — Runtime rules

The named external runtime boundary is Internet email, with conditional rules for SMTP submission and downstream delivery. Checked RFC 5321, RFC 6409 and RFC 6531 for the acceptance boundary, rejection classes, authorization, line-length limit, Unicode address requirements and timeouts. Added scheduler and live-sender readiness, capacity deferral, and nonproduction isolation. No application host, scheduler implementation, or mail provider was supplied. Their execution and response timeouts, rate limits, quotas, and provider approvals remain unconfirmed. A protocol’s minimum capability or recommended response time does not establish a specific deployment’s quota or timeout.

## Pass 5 — Preservation and invariants

Covered existing creation, editing, issuance, payment and manual sends where those capabilities exist. Added access boundaries, recipient isolation, intact financial records, failed stop confirmation, outage handling and rollback of uncertain attempts. No implemented invoice surface or legacy reminder history was available to inspect. No evidence called for migration of prior manual sends into automatic deduplication.

## Pass 6 — Build-through review

Re-read all use cases and clauses against the observable launch, failure, recovery and rollback paths. Added outcome reconciliation authority, bounce treatment, invoice reopening and replacement, local-date transitions, retry timing, production limits, and repeatable configuration actions. Split outcomes from their follow-on effects where one observable was doing two jobs. No request evidence fixed a time of day, provider-specific value, retry count, or email copy.

## Pass 7 — Boundaries and lifecycle

Rechecked the first activation, zero invoices, sender identity, recipient follow-through, the retry deadline after a provider delay, interrupted work before contact, cross-workspace evidence, restart, timezone changes, existing invoice access and eventual history expiry. Added the externally visible distinctions a builder could have missed. Found no support for a required invoice-link format, contact method, displayed history duration or additional operator-selected schedule.

## Pass 8 — Adverse timing and outcome review

Re-read the submission boundary from scheduler to provider, including deferrals without attempts, temporary failures inside one billing day, permanent failures beyond invalid destinations, asynchronous handoff and conflicting outcome evidence. Added explicit behavior for each. No external rule established a customer receipt deadline or a way to recall an asynchronous provider handoff.

## Pass 9 — Final closure review

Re-read the full specification from the use cases through the clauses. Traced each visible result to an actor, trigger and observable outcome. Checked first and repeated runs, no-work cycles, backlog completion, timing and settlement around submission, evidence across retries, permission boundaries, restored invoices, and rollback. Checked sequential numbering, required fields, source labels and references. This pass added no behavior and found no remaining material omission or ambiguity within the stated scope. The unresolved deployment figures are identified in their clauses. This was the stopping pass.
