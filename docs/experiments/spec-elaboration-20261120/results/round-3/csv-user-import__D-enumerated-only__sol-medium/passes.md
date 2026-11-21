## Pass 1 — Ground

Found no application source, user model, or deployment configuration in the working directory. Wrote U-1 through U-13 and C-1 through C-18 for first and later use, empty and malformed files, authorization, limits, duplicates, failure, operator controls, recovery, and rollback. Found no evidence for an existing CSV contract or runtime.

## Pass 2 — Presuppositions

Walked each first-pass use case and clause back to its preconditions. Added C-19 through C-41 for directory authority, discoverability of requirements, the submitted object, CSV grammar, identity, defaults, onboarding, and actionable diagnostics. Found no evidence of existing field, identity, or onboarding rules, so specified how available host behavior binds the feature and supplied a minimal fallback where needed.

## Pass 3 — Interactions

Added U-14 and U-15 plus C-42 through C-65 after comparing submission, connection loss, replay, duplicate creation, directory deletion, role changes, intake, onboarding, and terminal results. Specified the acceptance boundary, status transitions, timeout, retention, replay, and which side of a concurrent change controls creation. Found no other application surfaces or external integrations evidenced beyond user management and possible existing onboarding.

## Pass 4 — Runtime

Added C-66 through C-70. Used the browser's HTML file selection rule and specified secure production access, request-body fit, request timeout behavior, and execution readiness. Found no identified application host, account service, gateway, execution runtime, or deployment policy. Recorded the resulting unconfirmed limits in their clauses.

## Pass 5 — Preservation and invariants

Added C-71 through C-83. Checked ordinary creation, account management, sign-in, existing users, privilege assignment, browser session boundaries, untrusted input, operator access, and roster retention. Found no existing surface in the workspace to document by name, so preservation is tied to observable ordinary-path behavior where it exists.

## Pass 6 — Acceptance and recovery read-through

Added C-84 through C-97. Closed gaps around file-level diagnostics, empty selection, uncertain status, existing account states and quotas, operator retention, rollback and restoration, duplicate locations, and review of the selected file. Tightened existing clauses for blank files, logical row count, physical line numbering, permission revocation, and pending account visibility. Found no reason to add roster fields, an alternate delimiter, or account-update behavior.

## Pass 7 — Boundary consistency

Added U-16 and C-98 through C-103. Checked boundary times against terminal status, account scope against diagnostic visibility, and replay against onboarding. Fixed the timeout rule for an attempt already final and the distinction between incomplete transport and a lost reply after complete transfer. Added operator aggregate counts and a rule for a transfer reaching intake after its reference expires. Found no need for another timeout or separate account membership flow.

## Pass 8 — Authority and fallback read-through

Split the standalone account result into C-104. Made hidden-identity redaction consistent in create conflicts, concurrent outcomes, and operator categories. Checked the fallback against account defaults and found no basis for prescribing credentials, an additional profile field, or a new activation state.

## Pass 9 — Minimum and expiry read-through

Added C-105 to make the 1-record minimum explicit. Rechecked expired transfers, fresh submissions after identity release, pre-acceptance outage recovery, and diagnostic redaction. Found no separate minimum-file-size rule beyond the required header and data record.

## Pass 10 — Diagnostic ordering

Separated email syntax validation from checks that require an already valid identity. Made the admin-facing difference between a service failure and a processing timeout explicit. Found no additional failure class that needed a distinct admin outcome.

## Pass 11 — Completion check

Read the whole specification from U-1 through C-105. Traced each use case to observable behavior, checked the grammar and limit boundaries, enumerated statuses and diagnostic categories, and followed accepted attempts through concurrency, failure, expiry, and rollback. Checked that product decisions are marked as choices, that unresolved host limits are named where they apply, and that numbering and references resolve. Found no further behavior that needed to be added or changed. This was the stopping pass.
