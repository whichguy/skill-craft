# G-shiploop-spec-duty4-bounds against P-shiploop-spec, round-9, item by item (set X2)

## sonnet-high, judge claude-opus-5-5: 4 covered by G-shiploop-spec-duty4-bounds and not by P-shiploop-spec; 5 the other way
+ grokbot-salesforce N-16 [unhappy] P-shiploop-spec: partial; G-shiploop-spec-duty4-bounds: covered
    item: A partial or truncated answer, and what the user sees when an answer never arrives.
    P-shiploop-spec (R-4): Callout timeout ... `TIMEOUT` | Grok did not answer in time | 2xx but no assistant text parseable | `BAD_RESPONSE`
    G-shiploop-spec-duty4-bounds (R-6): a reply cut off by the cap is shown with the visible note "Reply was cut off at the length limit" ... A reply arriving at 60 s or later is not shown (R-7 timeout).
+ gym-waitlist N-9 [unhappy] P-shiploop-spec: partial; G-shiploop-spec-duty4-bounds: covered
    item: Payment for a promoted booking: when it is taken and what happens when it fails.
    P-shiploop-spec (Service boundaries, G-2): Payments or credits: unresolved (G-2). If a booking has a cost, promotion must apply the same charging rule with a defined outcome on failure.
    G-shiploop-spec-duty4-bounds (R-4 open gaps (OG-5)): does promotion charge or consume credit? default: it behaves exactly as a booking made at that moment, so a failed charge means ineligible and skipped
+ gym-waitlist N-12 [edge] P-shiploop-spec: partial; G-shiploop-spec-duty4-bounds: covered
    item: Staff raising or lowering a class's capacity while a waitlist exists.
    P-shiploop-spec (R-4): capacity increased, where the app lets staff edit it (one seat per added unit, in queue order)
    G-shiploop-spec-duty4-bounds (R-3, Out of scope): Triggers: ... (b) staff raise capacity ... reducing a class's capacity below its booked count (existing behaviour, untouched).
+ csv-user-import N-21 [unhappy] P-shiploop-spec: partial; G-shiploop-spec-duty4-bounds: covered
    item: Hostile content in the file: a value that becomes a formula when the result is opened in a spreadsheet, or a field far longer than any column allows.
    P-shiploop-spec (R-4 / AC-9.3): `value_too_long` (a limit identical to single-create; the field is named) ... the echoed value is rendered as literal text, no script executes
    G-shiploop-spec-duty4-bounds (R-14): no CSV, XLSX or other export is produced by this feature, so spreadsheet-formula injection on output does not apply
- grokbot-salesforce N-12 [async] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: A retried or re-enqueued async job must not post the same reply twice (idempotency on the message or request).
    P-shiploop-spec (R-4.c): pressing Retry re-sends the same text, and on success shows exactly one user bubble and one bot bubble for it (no duplicate).
    G-shiploop-spec-duty4-bounds (Service boundary: xAI Grok): retry is user-initiated, duplicates are possible and accepted (no idempotency key; stated in the timeout message).
- invoice-reminders N-7 [async] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: The send failing: retry policy, a provider outage, and escalation to a person when it keeps failing.
    P-shiploop-spec (D-9): Transient provider failure: up to 3 attempts per step, one per tick; a definitive hard failure (invalid address) is not retried. ... settings page shows a count of invoices with a failed or unknown step
    G-shiploop-spec-duty4-bounds (R-6): Automatic retry count and backoff are open (G-3); interim: zero automatic retries ... Alerting on failures beyond History is out of scope (G-11).
- invoice-reminders N-11 [edge] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: Currency and amount formatting for the recipient.
    P-shiploop-spec (AC-4.6): 1234567.80 USD renders unambiguously with the currency code; zero-decimal currency (JPY 5000) renders without decimals.
    G-shiploop-spec-duty4-bounds (R-5): It states the invoice number, the outstanding balance with currency ... Out of scope: customer-editable templates, translations/locales
- invoice-reminders N-12 [unhappy] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: A bouncing or invalid recipient address, and an invoice with no contact at all.
    P-shiploop-spec (AC-4.4): Billing address empty or syntactically invalid at evaluation: no handoff ... at window end it resolves skipped: no-recipient. ... If the provider later reports a bounce, sent becomes bounced
    G-shiploop-spec-duty4-bounds (T-7 / D-6): invoice has no billing address | record NotSentNoRecipient ... completion of delivery to the mailbox is not observed (accepted-by-provider is the recorded success
- csv-user-import N-20 [preserve] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: Creating a single user by hand still works exactly as it does, and existing users are not modified.
    P-shiploop-spec (R-2 / R-5): Preserved: single-user creation behaviour is unchanged by this work. ... Existing users are never changed.
    G-shiploop-spec-duty4-bounds (R-4): existing users are never modified or overwritten.

## sonnet-high, judge gpt-6.2-astra: 5 covered by G-shiploop-spec-duty4-bounds and not by P-shiploop-spec; 6 the other way
  +grokbot-salesforce N-2, +grokbot-salesforce N-16, +gym-waitlist N-9, +csv-user-import N-4, +csv-user-import N-21 | -gym-waitlist N-8, -gym-waitlist N-14, -gym-waitlist N-15, -invoice-reminders N-11, -invoice-reminders N-12, -csv-user-import N-20

## sol-medium, judge claude-opus-5-5: 1 covered by G-shiploop-spec-duty4-bounds and not by P-shiploop-spec; 7 the other way
+ grokbot-salesforce N-11 [async] P-shiploop-spec: partial; G-shiploop-spec-duty4-bounds: covered
    item: How the interface learns the answer arrived: a platform event, change data capture, a polled status field, or Lightning Message Service — not an assumption that the call returns inline.
    P-shiploop-spec (AD-2; R-2 C): Use an imperative, non-cacheable Lightning-to-Apex request ... A browser timeout additionally ends the current UI operation when an invocation never returns.
    G-shiploop-spec-duty4-bounds (Service boundaries / R-3 State and data): UI Send is pending until Salesforce returns the result for that attempt ... There is no promised remote cancellation, durable queue, background completion, SSE, polling, or offline resumption
- gym-waitlist N-6 [async] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: Notification of a promotion: the channel, what it says, and what happens when sending fails.
    P-shiploop-spec (R-2): The default has one queue, no reserved categories, and no external notification. A member sees promotion in their own booking and waitlist surfaces under R-4.
    G-shiploop-spec-duty4-bounds (Service boundaries (Inapplicable), R-3.d): outbound notification delivery contract are outside this feature's scope. Existing booking notifications, if applicable, retain their established contract. ... A completed promotion appears on the existing booking surface upon authoritative refresh.
- gym-waitlist N-14 [data] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: The waitlist entry as a record with its join time and state, and whether a position is stored or derived.
    P-shiploop-spec (State and service contracts (Waitlist entry and position)): The booking authority owns minimal occurrence and member references, committed order, entry state and the promotion link where applicable. ... Ordinals are derived from active entries.
    G-shiploop-spec-duty4-bounds (R-3 State and data, Logical state inventory): Keep only existing identity/class references, acceptance order, and the disposition data necessary to reconcile the operation.
- invoice-reminders N-3 [interaction] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: absent
    item: A part-paid invoice: whether the reminder states the remaining balance rather than the original amount.
    P-shiploop-spec (R-2 A; C-1/C-4 walk): A partially paid invoice qualifies on its remaining balance if otherwise eligible ... one submission ... showing USD 60.00 ... A stale USD 100.00 notice fails the check.
    G-shiploop-spec-duty4-bounds (None): None
- invoice-reminders N-9 [edge] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: Invoices already overdue when the feature is switched on: the whole backlog of reminders does not go out at once.
    P-shiploop-spec (R-1 Rules left open): Proposed default is explicit activation per billing scope, with no historical catch-up on initial enablement until approved.
    G-shiploop-spec-duty4-bounds (T-2; R-1 Open gaps): For missed occurrences the approved policy permits recovering, resume unattended work ... late-work and catch-up behavior ... There is no basis for values or a catch-up default.
- invoice-reminders N-12 [unhappy] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: A bouncing or invalid recipient address, and an invoice with no contact at all.
    P-shiploop-spec (R-3 A; R-5 B): Missing, invalid, ambiguous or revoked destination ... yields no submission and a scoped reason. ... A post-acceptance bounce is recorded against that attempt with no automatic resend
    G-shiploop-spec-duty4-bounds (T-5; T-6): A missing, ambiguous, invalid or unauthorized destination or missing required content prevents handoff and leaves an actionable reason.
- csv-user-import N-4 [permission] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: An import must not create a user with more access than the importer has: roles named in the file are checked against the importer's own authority.
    P-shiploop-spec (R-3 Commit): Existing users retain their prior IDs, fields and privileges. The CSV cannot set privileges or credentials.
    G-shiploop-spec-duty4-bounds (R-2): CSV fields cannot select a target or bypass the assigned permissions of ordinary user creation.
- csv-user-import N-8 [unhappy] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: A row failing after side effects have already happened for earlier rows (invitations already sent).
    P-shiploop-spec (R-3 State and data): For definitive failure, the batch contributes no records or effects. An import never compensates by deleting an unrelated or pre-existing user.
    G-shiploop-spec-duty4-bounds (R-3): Open prerequisite for the product owner: determine ... any required invitations, activation, credentials, notifications or audit effects. Open feasibility prerequisite ...: verify whole-batch publication, including any mandatory provisioning effects

## sol-medium, judge gpt-6.2-astra: 2 covered by G-shiploop-spec-duty4-bounds and not by P-shiploop-spec; 7 the other way
  +grokbot-salesforce N-15, +gym-waitlist N-12 | -grokbot-salesforce N-12, -invoice-reminders N-3, -invoice-reminders N-9, -invoice-reminders N-12, -csv-user-import N-8, -csv-user-import N-12, -csv-user-import N-20

