# K-shiploop-spec-default-bounds against P-shiploop-spec, round-8, item by item (nonfunctional items) (set X1)

## sonnet-high, judge claude-opus-5-5: 1 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
+ invoice-reminders N-19 [nonfunctional] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A bound on sending volume or on how late a scheduled reminder may go out.
    P-shiploop-spec (R-9): So a customer never gets more than one reminder per invoice per run. ... There is no maximum lateness: a late reminder is still sent, with accurate wording.
    K-shiploop-spec-default-bounds (R-3): Maximum reminders ever sent for one invoice = number of offsets (A-6, A-8).

## sonnet-high, judge gpt-6.2-astra: 1 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-26 | 

## sol-medium, judge claude-opus-5-5: 1 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
+ grokbot-salesforce N-25 [nonfunctional] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A latency target or bound for an answer, and truthful in-progress feedback in the interface while the async work runs.
    P-shiploop-spec (R-2.c; Non-functional requirements): While waiting, show **Waiting for Grok** and disable duplicate sends in that view. ... No latency, availability or throughput SLA is specified for this development slice.
    K-shiploop-spec-default-bounds (C-08): valid Send from an idle view shows the submitted question and an announced "Waiting for Grok…" status ... Boundary: one current attempt per mounted view, with no reply at or after 30,000 ms.

## sol-medium, judge gpt-6.2-astra: 1 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-25 | 

