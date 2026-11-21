## Pass 1 — The ground

Wrote the initial use cases and clauses for first use, batch creation, empty and limit cases, correction, access refusal, interruption, and operator controls and rollback. The workspace contained no application files or existing account documentation, so this pass found no product-specific field names, permission model, or platform limits to carry forward.

## Pass 2 — Preconditions

Expanded the upload and existing-account clauses into discoverability, schema, identity matching, CSV decoding and parsing, field validation, error location, and measurable limits. Followed those additions through the rules for optional cells, logical records, header mapping, and existing identity resolution. Found no reason to prescribe interface text, literal column names, or a fixed deployment ceiling.

## Pass 3 — Interactions

Walked submissions and retries against identity changes, ordinary account creation, concurrent imports, permission changes, maintenance, changed limits, disconnects, restarts, and downstream account setup. Added atomic creation, recoverable outcomes, replay rules, and the boundary between account creation and account setup. Found no interaction that requires a precedence rule for two nonoverlapping batches.

## Pass 4 — Runtime rules

Named the browser administration surface as an assumption and checked the HTML file-selection and filename rules. Added observable requirements for the hosting request-body cap, request deadline, execution deadline, and prerequisites for live intake. Found no identified server runtime, gateway, provider, or deployment settings from which to confirm numerical limits or provider-specific production rules.

## Pass 5 — Preservation and invariants

Added preservation of ordinary creation and existing-account access, destination and authority checks, privileged-field and credential restrictions, data visibility and retention boundaries, operational summaries, and safe rollback of pending work. Found no existing product-specific behavior beyond the ordinary account behavior the integration must preserve.

## Pass 6 — Build-through review

Read the full draft from file selection through rollback. Added missing-file handling, selection changes, incomplete transfer expiry, attempt ownership, deployment quotas, late setup, and recovery after rollback. Reworked observables that bundled schema guidance or operator permissions, made the file-byte boundary measurable, and corrected attribution for browser-dependent choices. Found no need for a prescribed interface layout, status label, or account identity format.

## Pass 7 — Boundary review

Cross-checked the use cases against parsing, limits, the intake cutoff, permissions, replay, and data expiry. Added oversized-file feedback before transfer, a rule for uploads still transferring during a pause, explicit empty-cell handling, clear failure reasons, and enforceable result expiry. Made the repeated-upload case explicit. Found no need to promise an exhaustive error list or prescribe the order in which simultaneous independent attempts complete.

## Pass 8 — Changes during submission

Read through every flow and observable again, focusing on which promises survive changes during an upload. Added recovery without the original response, the fate of unfinished transfers during rollback, and behavior when field mappings or validation policy change before creation. Found no reason to define a particular attempt-reference format or recovery screen.

## Pass 9 — Stopping pass

Reviewed the whole specification for usable observables, clauses with more than one behavior, unmarked choices, uncovered failure paths, and state without an end. Traced successful, refused, interrupted, replayed, and rolled-back attempts through their creation outcome and data expiry. Checked consecutive numbering, required fields, and clause references. This pass found no missing behavior or unresolved product decision that would change what a builder delivers. Hosting limits remain explicitly unconfirmed because the deployment was unspecified.
