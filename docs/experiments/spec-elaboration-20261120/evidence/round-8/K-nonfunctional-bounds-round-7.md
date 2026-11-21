# K-shiploop-spec-default-bounds against P-shiploop-spec, round-7, item by item (nonfunctional items) (set X1)

## sonnet-high, judge claude-opus-5-5: 1 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
+ invoice-reminders N-19 [nonfunctional] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A bound on sending volume or on how late a scheduled reminder may go out.
    P-shiploop-spec (N-1): How late after a step's moment a reminder may be sent is not stated by the request. No number is invented.
    K-shiploop-spec-default-bounds (R-3 / A-4): Runs happen at least once every 60 minutes (A-4), so on a healthy system a due, eligible step is handed to the mail provider by the first run at or after its target, at most 60 minutes late.

## sonnet-high, judge gpt-6.2-astra: 1 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
  +invoice-reminders N-19 | 

## sol-medium, judge claude-opus-5-5: 2 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
+ grokbot-salesforce N-25 [nonfunctional] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A latency target or bound for an answer, and truthful in-progress feedback in the interface while the async work runs.
    P-shiploop-spec (Non-functional requirements (latency and capacity)): Pending always reaches reply or actionable failure within the confirmed request deadline.
    K-shiploop-spec-default-bounds (R-2 Send; R-2 Recover): announces **Waiting for Grok**. ... The waiting cue does not assert provider receipt. ... The outbound wait is capped at 30 seconds after dispatch. The view stops waiting at 40 seconds from admission
+ gym-waitlist N-19 [nonfunctional] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A bound on how soon a promotion follows a cancellation.
    P-shiploop-spec (NFR Workload, latency and runtime ceilings): Allocation completion and freshness budgets ... are unresolved. ... No numeric target or platform capability is established here.
    K-shiploop-spec-default-bounds (R-3.A; R-3 State and data): if the allocation cannot be determined or committed, the attempted seat-changing operation does not commit a partial result ... One failed allocation leaves the release and queue in their prior state.

## sol-medium, judge gpt-6.2-astra: 2 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-25, +gym-waitlist N-19 | 

