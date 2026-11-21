# H-shiploop-spec-duty4-no-open against P-shiploop-spec, round-10, item by item (set O1)

## sonnet-high, judge claude-opus-5-5: 1 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 1 the other way
+ invoice-reminders N-19 [nonfunctional] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: A bound on sending volume or on how late a scheduled reminder may go out.
    P-shiploop-spec (NFR-1, NFR-4, R-2 rule 2): Unresolved bound (G-4); no number is invented. ... At most one message per invoice per run.
    H-shiploop-spec-duty4-no-open (PD-4): A step may be sent only during its **grace window**: step date through step date + 2 days (3 runs)
- invoice-reminders N-10 [edge] P-shiploop-spec: covered; H-shiploop-spec-duty4-no-open: partial
    item: Time zone and sending hours: the customer's local time, business hours, weekends and holidays.
    P-shiploop-spec (A-3, R-2): sent at 09:00 in the business timezone ... Out of scope (bounded domain rules): ... weekend or holiday avoidance (a reminder due on a Saturday is sent on that Saturday).
    H-shiploop-spec-duty4-no-open (PD-3): One evaluation **run per calendar date**, at 09:00 in the account time zone (UTC if none set)

## sonnet-high, judge gpt-6.2-astra: 2 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 1 the other way
  +grokbot-salesforce N-25, +invoice-reminders N-19 | -invoice-reminders N-10

## sol-medium, judge claude-opus-5-5: 2 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
+ grokbot-salesforce N-25 [nonfunctional] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: A latency target or bound for an answer, and truthful in-progress feedback in the interface while the async work runs.
    P-shiploop-spec (NFR Bounded work): No latency percentile, load SLA or spend target was supplied.
    H-shiploop-spec-duty4-no-open (C7): when a valid send starts, show a screen-reader-announced Waiting for Grok state ... make the composer read-only and sending unavailable until the active attempt settles.
+ gym-waitlist N-10 [edge] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: A cap on the waitlist itself, and what a person sees when even the waitlist is full.
    P-shiploop-spec (Non-functional requirements, Performance and capacity): Queue length, throughput, latency, storage, concurrency and cost limits are unresolved. ... This specification adds no numeric SLA or waitlist cap.
    H-shiploop-spec-duty4-no-open (R-1 Bounds and prerequisites): No new roles, group enrollment, or per-customer or per-class queue cap is introduced.

## sol-medium, judge gpt-6.2-astra: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 1 the other way
   | -gym-waitlist N-19

