# K-shiploop-spec-default-bounds against P-shiploop-spec, round-7, item by item (set X1)

## sonnet-high, judge claude-opus-5-5: 4 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
+ grokbot-salesforce N-8 [platform] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: Governor limits that bind this design are named with their numbers: callout timeout ceiling, callouts per transaction, heap, CPU time.
    P-shiploop-spec (NFR-2): One callout per send (limit 100 per transaction, not approached). Callout wait time is excluded from the 5-second long-running-request limit
    K-shiploop-spec-default-bounds (R-12): per-callout timeout 1 ms–120,000 ms (default 10 s), cumulative 120 s per transaction, 100 callouts per transaction ... synchronous heap 6 MB, CPU 10,000 ms
+ gym-waitlist N-10 [edge] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A cap on the waitlist itself, and what a person sees when even the waitlist is full.
    P-shiploop-spec (G-3): G-3 — waitlist length cap. Assumed none.
    K-shiploop-spec-default-bounds (J8): Class full, open, waitlist already has 10 entries | WAITLIST_FULL: "The waitlist for this class is full (10 of 10)."
+ invoice-reminders N-19 [nonfunctional] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A bound on sending volume or on how late a scheduled reminder may go out.
    P-shiploop-spec (N-1): How late after a step's moment a reminder may be sent is not stated by the request. No number is invented.
    K-shiploop-spec-default-bounds (R-3 / A-4): Runs happen at least once every 60 minutes (A-4), so on a healthy system a due, eligible step is handed to the mail provider by the first run at or after its target, at most 60 minutes late.
+ csv-user-import N-9 [edge] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec (R-2): size and row-count limits are configured values (`max_bytes`, `max_rows` ...); exceeding either rejects the whole file before any user is created (G-1: default values unresolved).
    K-shiploop-spec-default-bounds (R-2): 1,048,576 accepted, 1,048,577 rejected; 1,000 rows accepted, 1,001 rejected ... `file_too_large` 413, ... `too_many_rows` 422.

## sonnet-high, judge gpt-6.2-astra: 4 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-8, +gym-waitlist N-10, +invoice-reminders N-19, +csv-user-import N-9 | 

## sol-medium, judge claude-opus-5-5: 7 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
+ grokbot-salesforce N-13 [async] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: Queue depth or concurrent-job limits, and what happens to a request that cannot be enqueued.
    P-shiploop-spec (R-3 Open gap): The integration owner must establish the supported attempt deadline and overload behavior on the chosen model and target runtime before live readiness.
    K-shiploop-spec-default-bounds (AD-2; Service contracts): Salesforce also documents up to 20 concurrent external callouts for Developer Edition. ... Excess capacity follows R-2 unavailable feedback or the view deadline.
+ grokbot-salesforce N-20 [edge] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A conversation outgrowing the model's context window: what is trimmed or summarised, and at what size.
    P-shiploop-spec (C-04): If the context exceeds the confirmed budget, decline the send before dispatch and offer Clear conversation to start fresh.
    K-shiploop-spec-default-bounds (R-3 Follow up; AD-3): Zero through four completed pairs can precede the new prompt. On the fifth success the oldest pair leaves the window.
+ grokbot-salesforce N-21 [edge] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: The first use (no history), an empty question, and an answer or question at the maximum accepted length.
    P-shiploop-spec (C-05): Empty or whitespace-only text shows a validation cue and triggers no outbound call... Numeric limits remain open below.
    K-shiploop-spec-default-bounds (R-1 Entry; R-2 Validate; R-2 Reply): Empty, whitespace-only, missing ... and over-limit input cause no outbound call. ... Accept 1 through 2,000 Unicode scalar values inclusive after trimming. Reject at 2,001
+ grokbot-salesforce N-25 [nonfunctional] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A latency target or bound for an answer, and truthful in-progress feedback in the interface while the async work runs.
    P-shiploop-spec (Non-functional requirements (latency and capacity)): Pending always reaches reply or actionable failure within the confirmed request deadline.
    K-shiploop-spec-default-bounds (R-2 Send; R-2 Recover): announces **Waiting for Grok**. ... The waiting cue does not assert provider receipt. ... The outbound wait is capped at 30 seconds after dispatch. The view stops waiting at 40 seconds from admission
+ gym-waitlist N-10 [edge] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A cap on the waitlist itself, and what a person sees when even the waitlist is full.
    P-shiploop-spec (NFR Workload, latency and runtime ceilings): concurrent demand on a popular class, cross-class throughput, queue and retention capacity, execution time, and cost limits are unresolved.
    K-shiploop-spec-default-bounds (R-1.C): with 20 active entries, a new distinct entrant sees Waitlist full and the queue is unchanged.
+ gym-waitlist N-19 [nonfunctional] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A bound on how soon a promotion follows a cancellation.
    P-shiploop-spec (NFR Workload, latency and runtime ceilings): Allocation completion and freshness budgets ... are unresolved. ... No numeric target or platform capability is established here.
    K-shiploop-spec-default-bounds (R-3.A; R-3 State and data): if the allocation cannot be determined or committed, the attempted seat-changing operation does not commit a partial result ... One failed allocation leaves the release and queue in their prior state.
+ csv-user-import N-9 [edge] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec (A6): If either cap is exceeded, provide a file-limit error with zero writes. ... Each cap is inclusive.
    K-shiploop-spec-default-bounds (R-2): At most 262,144 file bytes (256 KiB) and 500 data records. ... exceeding a cap rejects the entire file before any user write. Show the failing category and the applicable limit

## sol-medium, judge gpt-6.2-astra: 8 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-20, +grokbot-salesforce N-21, +grokbot-salesforce N-25, +gym-waitlist N-10, +gym-waitlist N-11, +gym-waitlist N-19, +invoice-reminders N-10, +csv-user-import N-9 | 

