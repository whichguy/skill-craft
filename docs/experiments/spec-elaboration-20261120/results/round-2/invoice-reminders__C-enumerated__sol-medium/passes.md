## Pass 1 — the ground

Wrote the baseline for activation, receipt, repeat use, empty and busy accounts, missing data, delivery failure and refused access. The workspace contains no product files or runtime definition. The incoming sentence supplies no exact schedule, channel, scale or retry values.

## Pass 2 — prerequisites

Resolved which account owns the policy, how an invoice is identified, which collection states and balances count, where the destination and due date come from, and how an email leads back to the invoice. Chose a finite cadence and explicit clock. Found no basis for a new payment flow, contact directory or channel beyond email.

## Pass 3 — operations

Added enablement and readiness checks, effective policy inspection, configuration refusal, account pause, invoice suppression, legacy invoice coverage, individual and service-level diagnosis, mistaken-send containment, and release rollback and restoration. Found no reliable way for these controls to recall an email already released.

## Pass 4 — interactions

Walked policy and controls against due-date changes, each eligibility check, dispatch, retry and result handling. Walked run interruption and replay against each opportunity outcome. Added prospective scheduling, slot identity, expiry, retry and uncertain-delivery handling, result correlation, and dispatch precedence. Ordinary invoice access does not take part in scheduling or consume an opportunity.

## Pass 5 — runtime rules

Named the assumed runtime roles: the authoritative billing application, scheduled execution and outbound email delivery. Specified the effects of background execution, invocation cutoffs, quotas, retry delays, timeouts, asynchronous delivery, sender readiness and nonproduction recipient restrictions. Found no supplied hosting platform or email provider. Their hard scheduling, duration, quota, timeout and production onboarding details are marked unconfirmed instead of assuming a vendor.

## Pass 6 — preservation and prohibitions

Specified preservation of invoice lifecycle, billing balances and existing communications where present. Closed access gaps across roles and entry points, constrained links to existing invoice access rules, and checked invoice identity reuse, deleted invoices and currency integrity. No repository evidence establishes a named legacy endpoint, schema or role name.

## Pass 7 — builder's read

Read the spec in order and traced before-due, at-due and expired opportunities through activation, edits and retry. Made schedule boundaries strict at effective changes, distinguished transient inability to evaluate from confirmed exclusion, covered late results after a control reversal and made evaluation health measurable. Added history lifetime, concurrent control order and explicit dispatch gates. Kept the file to the requested headings and fields.

## Pass 8 — scenario replay

Replayed paid, reopened, backdated and legacy invoices against the schedule. Replayed service interruption, rollback, test delivery, quota delays and bounces against history. Added unsuppressed defaults, safe preconfiguration, missing invoice identity, account removal, delayed retry closure and a fallback for providers that cannot prove nonacceptance. Added use cases for invoice changes during dispatch, interruption recovery and test delivery. Found no requirement for a separate payment feature or synchronous delivery receipt.

## Pass 9 — boundaries and clause audit

Checked that the non-choice clauses express obligations a product needs to fulfill the request or a named use case. Made the retry requirement actionable, clarified activation readiness by environment and distinguished uncertain release counts from confirmed outcomes. Added prospective ownership transfer and historical privacy for billing systems that support transfers. Found no further vendor facts in the workspace.

## Pass 10 — empty-state and health review

Compared readiness, health and due-work states for empty, stopped and unconfigured installations. Added an idle evaluation heartbeat so a healthy quiet account cannot look like a scheduler failure. Found no new customer-facing behavior needed for an empty account.

## Pass 11 — terminal states and first installation

Read across the use cases and clauses again. Clarified that expiration closes only still-pending work rather than overwriting a recorded disposition. Set the first-installation default of the service stop independently of the restored state. Found no missing terminal outcome or unmatched operator control.

## Pass 12 — stopping pass

Reviewed the whole specification against the request and traced each use case through its gates, timing boundaries, failure outcomes, operator controls and recovery. Checked the listed status and reason values, numeric bounds, authorization across scopes, and the difference between confirmed platform facts and open runtime selections. Verified consecutive identifiers, required fields and valid cross-references. This pass found no additional behavior to specify and added no clauses.
