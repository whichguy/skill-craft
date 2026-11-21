## Pass 1 — the ground

Wrote the first specification with nine use cases covering enablement, receipt, ineligible and empty accounts, monitoring, recovery, existing invoices, rollback and large portfolios. The workspace contains no application source or project runtime declaration. The request supplies no exact scheduling, channel or limit values.

## Pass 2 — what each sentence takes for granted

Expanded the ground clauses with account permissions, invoice identity, qualifying states, collection holds, balance and data requirements, schedule boundaries, recipient and message contents, settings validation, eligibility diagnostics and global controls. Existing invoice state names and authorization APIs were unavailable. The specification uses business states and leaves their mapping to any host application open.

## Pass 3 — where the parts meet

Added commit ordering, stale input replacement, retries, due-date edits, reopened invoices, simultaneous evaluation, duplicate and late results, ambiguous handoffs, bounces, outages and the invoice history needed to see those effects. The interaction review found no separate recipient action, manual resend path or external payment integration in the requested feature.

## Pass 4 — the runtime’s own rules

Checked Internet email behavior against the SMTP and Internet Message Format RFCs. Added mailbox and line bounds, acceptance and refusal semantics, service capacity, message-size failure, retry restrictions and production readiness. The outbound service plan, execution host and scheduler were unidentified. Their applicable figures and deployment prerequisites are marked unconfirmed instead of being assigned to an invented platform.

## Pass 5 — what must not change and what must never happen

Specified preservation of existing creation, issuance, edits, payments, adjustments, closure, delivery and access behavior where those operations exist. Added cross-account and message isolation, nonproduction isolation, rollback continuity, retention and permanent deletion rules. No concrete pre-existing UI, API or workflows were available to name.

## Pass 6 — builder read-through

Added use cases for payment, edits, delivery failure and startup. Clarified acceptance versus receipt, healthy evaluation and stall times, concurrent setting changes, interruption at handoff, opportunity status after later or ambiguous results, and history when a date is removed. Checked source attribution for chosen behavior. No evidence established a delivery-time guarantee or a concrete host limit.

## Pass 7 — boundary and observability review

Resolved status precedence, results after window close, exact timeout ties, calendar rollover, live account ownership and unavailable reads. Clarified internationalized addresses, authorized senders, what a verified bounce can establish and the boundary of global diagnostics. Found no basis to require SMTPUTF8 support or a particular provider, and no requested invoice delivery order.

## Pass 8 — interruption and retention review

Defined the external start boundary, clarified when a due-date edit can revive an expired window, preserved the original window in attempt history and separated transport wait from the unknown-outcome deadline. Made authoritative result handling deterministic and accounted for the required Internet email origination date. Found no reason to retain a raw message or its address in reminder history.

## Pass 9 — acceptance examples and preserved constraints

Made the normal timing bound observable as a started attempt, clarified scheduler health during pending delivery, resolved a third attempt’s late temporary rejection and preserved any existing account-, invoice- or address-level restriction on billing email. Found no separate commitment to a fixed handoff order or a bounded inbox delivery time.

## Pass 10 — rollback and unattended operation

Specified what happens when the operator cannot confirm a stop before rollback. Made unattended operation observable at actual handoff and aligned earlier-opportunity eligibility with preservation of its terminal history. Found no additional state that needs restoration after rollback.

## Pass 11 — completion review

Read the specification from the first use case through the final clause. Checked each flow against its prerequisites and failure paths, then checked clock boundaries, simultaneous changes, retries, late evidence, permission boundaries, existing invoices and rollback. Verified consecutive numbering and required fields. This full pass found no additional behavior a builder would have needed to decide, so it added nothing to the specification. Host- and provider-specific limits remain explicitly unconfirmed.
