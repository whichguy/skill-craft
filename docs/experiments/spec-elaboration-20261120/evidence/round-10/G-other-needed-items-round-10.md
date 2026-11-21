# G-shiploop-spec-duty4-bounds against P-shiploop-spec, round-10, item by item (set X2)

## sonnet-high, judge claude-opus-5-5: 2 covered by G-shiploop-spec-duty4-bounds and not by P-shiploop-spec; 3 the other way
+ grokbot-salesforce N-11 [async] P-shiploop-spec: partial; G-shiploop-spec-duty4-bounds: covered
    item: How the interface learns the answer arrived: a platform event, change data capture, a polled status field, or Lightning Message Service — not an assumption that the call returns inline.
    P-shiploop-spec (R-13): Unknowns (OG-10): whether Lightning's server-call transport tolerates a callout running up to 120 s from an LWC imperative call without its own timeout
    G-shiploop-spec-duty4-bounds (AD-6): The component calls an `@AuraEnabled` (non-cacheable) method imperatively; one send is one callout ... The method returns a structured result (success flag, reply, finish reason, stable error code, safe message)
+ grokbot-salesforce N-16 [unhappy] P-shiploop-spec: partial; G-shiploop-spec-duty4-bounds: covered
    item: A partial or truncated answer, and what the user sees when an answer never arrives.
    P-shiploop-spec (R-6): `BAD_RESPONSE` (HTTP 200 but body unparsable or the reply text empty) ... A timeout is an unknown outcome: the provider may have processed the request; the message says so for `UNREACHABLE`.
    G-shiploop-spec-duty4-bounds (R-2, R-7): reply reaching the configured max output tokens (D-3) is shown with the notice "Reply was cut off at the length limit" ... at the timeout bound (D-4 elapsed) the user sees `TIMEOUT`, the pending state ends
- gym-waitlist N-6 [async] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: Notification of a promotion: the channel, what it says, and what happens when sending fails.
    P-shiploop-spec (R-6, PD-8): the member is informed they are now booked, class name and start. At minimum the in-app status changes ... notification delivery failure never reverses the promotion ... the failure is logged
    G-shiploop-spec-duty4-bounds (R-7): Outbound notification of promotion and removal uses an existing channel if one exists (AD-7, G-4). ... a failed notification send never reverses a promotion; it is logged (R-12).
- invoice-reminders N-15 [data] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: What the reminder contains: invoice reference, amount, due date and a way to pay, and whether that link expires.
    P-shiploop-spec (R-3): Body ... contains in order: a greeting line, `Invoice: <number>`, `Amount due: USD <balance>`, `Due date: <Month D, YYYY>` ... Out of scope: payment link or instructions (G-6; none in the default message)
    G-shiploop-spec-duty4-bounds (R-3): It states: business name, invoice number, outstanding balance with currency, due date (`YYYY-MM-DD`) ... If the host exposes a payment link for the invoice it is included, otherwise the message omits it.
- csv-user-import N-21 [unhappy] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: Hostile content in the file: a value that becomes a formula when the result is opened in a spreadsheet, or a field far longer than any column allows.
    P-shiploop-spec (NFR-3, PD-5, R-8): Neutralising values that begin with =, +, - or @ when a later feature exports users to CSV is that feature's duty / name 1–100 characters / The body never contains the contents of a cell.
    G-shiploop-spec-duty4-bounds (R-3): formula-injection neutralization (values are stored verbatim after trim; any later CSV export owns that risk)

## sonnet-high, judge gpt-6.2-astra: 2 covered by G-shiploop-spec-duty4-bounds and not by P-shiploop-spec; 7 the other way
  +grokbot-salesforce N-16, +invoice-reminders N-5 | -grokbot-salesforce N-2, -grokbot-salesforce N-3, -grokbot-salesforce N-18, -gym-waitlist N-6, -gym-waitlist N-14, -gym-waitlist N-21, -csv-user-import N-5

## sol-medium, judge claude-opus-5-5: 1 covered by G-shiploop-spec-duty4-bounds and not by P-shiploop-spec; 7 the other way
+ csv-user-import N-8 [unhappy] P-shiploop-spec: partial; G-shiploop-spec-duty4-bounds: covered
    item: A row failing after side effects have already happened for earlier rows (invitations already sent).
    P-shiploop-spec (R-3 A4 / R-3 Open gap): An authoritative abort after some rows have been staged leaves zero visible or durable users ... If normal creation has irreversible effects or the boundary cannot meet atomicity, reconcile the product policy
    G-shiploop-spec-duty4-bounds (R-3 Partial outcomes; R-2 Interpret): Keep earlier confirmed creations, even if a later row fails. ... Assert that a syntax error late in a file prevents earlier valid rows from producing writes.
- grokbot-salesforce N-10 [platform] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: The remote endpoint must be registered (Remote Site Setting or the Named Credential's host) or the callout is refused.
    P-shiploop-spec (AD-2): A modern Named Credential points to the approved inference endpoint and an External Credential with Custom authentication and a named principal provides the bearer header
    G-shiploop-spec-duty4-bounds (AD-2): one foreground HTTPS callout ... to the xAI Responses API at `https://api.x.ai/v1/responses`. ... Link it to a Named Credential
- gym-waitlist N-1 [interaction] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: What happens when a spot opens: automatic promotion, or an offer the person must accept within a stated window.
    P-shiploop-spec (R-2 State and domain defaults): The proposed Join action states that the member will be booked automatically if a seat opens while they are still eligible. The default adds no claim window, new consent mechanism
    G-shiploop-spec-duty4-bounds (R-2 Open gaps; TC-13): whether the member must actively claim or may agree to automatic booking. ... If the chosen model reserves a place for a claim, a finite claim deadline is required ... The value ... open.
- gym-waitlist N-5 [async] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: Promotion is triggered by a cancellation that happens outside the person's session, so it is background work with a stated trigger and timeliness.
    P-shiploop-spec (R-2 Allocate in order; R-2 State and domain defaults): An accepted cancellation of a confirmed place or an authorized increase in bookable capacity gives each available seat to the earliest eligible active waiter ... even when their app was closed during the change. ... makes a valid opening and its allocations one coherent outcome.
    G-shiploop-spec-duty4-bounds (F-2 T-3; R-2 State, authority and recovery): T-3 Existing authority makes capacity bookable. ... If processing continues after the initiating response, the app owns recovery without depending on the member keeping the view open.
- gym-waitlist N-6 [async] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: Notification of a promotion: the channel, what it says, and what happens when sending fails.
    P-shiploop-spec (Scope; R-2 State and domain defaults; R-4 Read and recover status): outbound messages are excluded from this change. Members see their own outcome in the booking app. ... The default adds no ... notification channel
    G-shiploop-spec-duty4-bounds (TC-5; R-2 Open gaps): The affected member can see their actual outcome in the app. ... External notification channels ... are outside the specified delta.
- gym-waitlist N-12 [edge] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: Staff raising or lowering a class's capacity while a waitlist exists.
    P-shiploop-spec (R-2 Allocate in order; R-2 State and domain defaults): an authorized increase in bookable capacity gives each available seat to the earliest eligible active waiter ... Capacity decreases use the existing capacity policy and do not by themselves trigger a promotion.
    G-shiploop-spec-duty4-bounds (F-2 T-3; R-2 Open gaps): T-3 Existing authority makes capacity bookable. ... Discovery must establish which existing events actually reopen capacity
- invoice-reminders N-3 [interaction] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: absent
    item: A part-paid invoice: whether the reminder states the remaining balance rather than the original amount.
    P-shiploop-spec (R-2): A partially paid invoice qualifies for its remaining balance.
    G-shiploop-spec-duty4-bounds (None): None
- csv-user-import N-12 [async] P-shiploop-spec: covered; G-shiploop-spec-duty4-bounds: partial
    item: A large file is processed in the background, and how the admin learns it finished.
    P-shiploop-spec (R-4 A4 / R-4 A2): No post-submit cancel or promised unattended processing. ... On timeout or disconnect after submission, show Outcome unknown and offer Check result when reachable.
    G-shiploop-spec-duty4-bounds (R-4 Recover; R-4 State): Default The feature offers no saved results page or guaranteed processing after the initiating interaction ends. ... Any runtime need to accept durable work for processing outside the view requires a separately evidenced execution and recovery contract

## sol-medium, judge gpt-6.2-astra: 1 covered by G-shiploop-spec-duty4-bounds and not by P-shiploop-spec; 8 the other way
  +invoice-reminders N-12 | -grokbot-salesforce N-5, -grokbot-salesforce N-10, -grokbot-salesforce N-11, -gym-waitlist N-1, -gym-waitlist N-5, -gym-waitlist N-8, -gym-waitlist N-12, -invoice-reminders N-3

