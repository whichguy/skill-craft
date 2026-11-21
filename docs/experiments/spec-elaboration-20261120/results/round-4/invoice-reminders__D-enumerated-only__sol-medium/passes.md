## Pass 1 — The ground

Wrote the first specification from the incoming sentence. Walked first enablement, sending, repetition, payment, empty and large workloads, invalid inputs, access refusal, outages, observation, recovery, prior invoices, and rollback. The workspace supplied no invoice application, established workflow, production runtime, or reminder policy.

## Pass 2 — Preconditions

Expanded the first-pass clauses through account authority, invoice identity, the collectibility decision, current billing contact, email contents, the schedule, and the history a billing operator uses to investigate. Stopped at billing truth, approved sender identity, and mailbox delivery as inputs supplied by the eventual host and mail service. No invoice schema, role model, or schedule was available to inherit.

## Pass 3 — Interactions

Walked schedule against account settings, issuance, invoice changes, payment, recipient changes, outages, retries, callback ordering, overlapping workers, capacity, and rollback. Added an observable submission boundary, exact retry and expiry rules, and reconciliation of uncertain outcomes. There was no local manual-send, payments, or job interface to pair against directly.

## Pass 4 — Runtime rules

Specified the observable contract for an unattended scheduler and an external email service. The production scheduler, deployment host, and mail provider are unconfirmed. No provider-specific numeric limit or release rule could be verified from the workspace, so the applicable figures remain explicitly unconfirmed in their clauses. The 15-minute timing, three-attempt ceiling, and 60-second uncertainty threshold are product choices.

## Pass 5 — Preservation and invariants

Added separate preservation clauses for issuing invoices, invoice identity, settlement, and independent existing communications. Checked tenant isolation, recipient privacy, provider evidence, repeated processing, pause, and rollback for paths that could leak data, send twice, change an invoice, or lose the evidence needed after recovery. No working host application was present to verify existing behavior or host-specific roles.

## Pass 6 — Builder review

Read all 85 clauses from the start as an implementer. Found unresolved questions about history discovery and retention, denied or failed setting changes, retry readiness, restored records, and how the operator distinguishes a disabled release from a scheduler failure. Added observable rules for those cases. The request provided no release dashboard or history retention requirement to preserve.

## Pass 7 — Failure and lifecycle replay

Replayed handoff with pause, a crash, a late bounce, and a due-date change. Clarified the attempt counting boundary, cancellation and expiry precedence, and the closed set of current outcomes. Added completeness checks for message facts, release authority, and the first production enablement. Found no need to prescribe email wording, the settings surface, storage, or a vendor.

## Pass 8 — Scope and recovery audit

Cross-checked original and edited due dates, account and release boundaries, the status list, and old versus new window identity. Scoped retries to their own window and kept late evidence tied to the original attempt. Required historical billing evidence before reconstructing an expired window. No scheduler or mail provider was identified by these checks.

## Pass 9 — Temporal consistency

Checked readiness, attempt budgets, the meaning of a healthy empty account, and the outcome for a rejection that arrives after closure. Removed an unconditional retry statement and made exhaustion and health timing independently observable. No further numeric provider limits were available.

## Pass 10 — Convergence

Read the specification from the first use case through C-118. Traced empty and high-volume accounts, a first send for an existing invoice, late issuance, partial and full payment, a changed due date, a pause at handoff, overlapping runs, delayed rejection and bounce evidence, and activation after rollback. Checked independently observable outcomes, enumerated dimensions, numeric bounds, source labels, numbering, and cross-references. This pass found no missing behavior or ambiguity that required a change to the specification. The production runtime and provider-specific limits remain explicitly unconfirmed in the applicable clauses.
