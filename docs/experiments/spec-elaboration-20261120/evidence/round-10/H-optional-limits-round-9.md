# H-shiploop-spec-duty4-no-open against P-shiploop-spec, round-9, item by item (set O1)

## sonnet-high, judge claude-opus-5-5: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 1 the other way
- invoice-reminders N-19 [nonfunctional] P-shiploop-spec: covered; H-shiploop-spec-duty4-no-open: partial
    item: A bound on sending volume or on how late a scheduled reminder may go out.
    P-shiploop-spec (D-5): A step (invoice × offset) may be sent on its step date or the one following calendar day (its window). At most one reminder per invoice per calendar day
    H-shiploop-spec-duty4-no-open (R-3): Result: at most one message per invoice per evaluation and, since offsets are unique, at most one per invoice per local date.

## sonnet-high, judge gpt-6.2-astra: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 1 the other way
   | -invoice-reminders N-10

## sol-medium, judge claude-opus-5-5: 2 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
+ grokbot-salesforce N-25 [nonfunctional] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: A latency target or bound for an answer, and truthful in-progress feedback in the interface while the async work runs.
    P-shiploop-spec (R-2 C; Non-functional requirements): Show the pending message and an accessible progress status as soon as a valid send starts ... No latency SLA, multi-user throughput target or spend figure was requested.
    H-shiploop-spec-duty4-no-open (R-2.B; R-2.D): locks the composer and Send for that view, and announces Waiting for Grok… until that attempt ends. ... Default wait deadline is 60 seconds from accepted send.
+ gym-waitlist N-10 [edge] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: A cap on the waitlist itself, and what a person sees when even the waitlist is full.
    P-shiploop-spec (R-1): The request supplies no waitlist size limit or per-member cap across classes. Product and platform owners must resolve any required cap before capacity-dependent work.
    H-shiploop-spec-duty4-no-open (R-1): There is no feature-specific numerical list cap.

## sol-medium, judge gpt-6.2-astra: 2 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-25, +gym-waitlist N-10 | 

