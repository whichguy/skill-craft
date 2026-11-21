# K-shiploop-spec-default-bounds against P-shiploop-spec over round-7, round-8, set X1 (22 items): items settled by one arm in every round and by the other in none (registered judge), with the second judge's states beside them

## sonnet-high: 3 settled by K-shiploop-spec-default-bounds in every round and by P-shiploop-spec in none; 2 of them the same under the second judge; 0 the other way
+ gym-waitlist N-10 [edge]  P-shiploop-spec: opus par/par, astra par/par;  K-shiploop-spec-default-bounds: opus cov/cov, astra cov/cov
    item: A cap on the waitlist itself, and what a person sees when even the waitlist is full.
    P-shiploop-spec round-7 (G-3): G-3 — waitlist length cap. Assumed none.
    P-shiploop-spec round-8 (G-4, NFR-10): Waitlist cap (per class, per member) unspecified. No bound is invented. ... Treated as unbounded in the spec
    K-shiploop-spec-default-bounds round-7 (J8): Class full, open, waitlist already has 10 entries | WAITLIST_FULL: "The waitlist for this class is full (10 of 10)."
    K-shiploop-spec-default-bounds round-8 (A-1; R-1): Waitlist capacity is **10 waiting entries per session** ... open-full, waitlist = 10 | `Waitlist full` disabled | `Class full · 10 on waitlist`
+ invoice-reminders N-19 [nonfunctional]  P-shiploop-spec: opus par/par, astra par/cov;  K-shiploop-spec-default-bounds: opus cov/cov, astra cov/cov
    item: A bound on sending volume or on how late a scheduled reminder may go out.
    P-shiploop-spec round-7 (N-1): How late after a step's moment a reminder may be sent is not stated by the request. No number is invented.
    P-shiploop-spec round-8 (R-9): So a customer never gets more than one reminder per invoice per run. ... There is no maximum lateness: a late reminder is still sent, with accurate wording.
    K-shiploop-spec-default-bounds round-7 (R-3 / A-4): Runs happen at least once every 60 minutes (A-4), so on a healthy system a due, eligible step is handed to the mail provider by the first run at or after its target, at most 60 minutes late.
    K-shiploop-spec-default-bounds round-8 (R-3): Maximum reminders ever sent for one invoice = number of offsets (A-6, A-8).
+ csv-user-import N-9 [edge]  P-shiploop-spec: opus par/par, astra par/par;  K-shiploop-spec-default-bounds: opus cov/cov, astra cov/cov
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec round-7 (R-2): size and row-count limits are configured values (`max_bytes`, `max_rows` ...); exceeding either rejects the whole file before any user is created (G-1: default values unresolved).
    P-shiploop-spec round-8 (R-2 / R-11): a configured maximum size in bytes and a configured maximum number of data rows... FILE_TOO_LARGE | size above the configured byte limit | TOO_MANY_ROWS
    K-shiploop-spec-default-bounds round-7 (R-2): 1,048,576 accepted, 1,048,577 rejected; 1,000 rows accepted, 1,001 rejected ... `file_too_large` 413, ... `too_many_rows` 422.
    K-shiploop-spec-default-bounds round-8 (A-5): file at most 2,097,152 bytes (2 MiB); at most 5,000 data rows ... `file_too_large` (HTTP 413) ... `too_many_rows`, 422, nothing created

## sol-medium: 3 settled by K-shiploop-spec-default-bounds in every round and by P-shiploop-spec in none; 2 of them the same under the second judge; 0 the other way
+ grokbot-salesforce N-21 [edge]  P-shiploop-spec: opus par/par, astra par/cov;  K-shiploop-spec-default-bounds: opus cov/cov, astra cov/cov
    item: The first use (no history), an empty question, and an answer or question at the maximum accepted length.
    P-shiploop-spec round-7 (C-05): Empty or whitespace-only text shows a validation cue and triggers no outbound call... Numeric limits remain open below.
    P-shiploop-spec round-8 (R-1.a; R-2.a): Blank, whitespace-only, or oversized input is rejected with an inline correction and zero provider requests. ... The confirmed prompt maximum is inclusive in the stated unit.
    K-shiploop-spec-default-bounds round-7 (R-1 Entry; R-2 Validate; R-2 Reply): Empty, whitespace-only, missing ... and over-limit input cause no outbound call. ... Accept 1 through 2,000 Unicode scalar values inclusive after trimming. Reject at 2,001
    K-shiploop-spec-default-bounds round-8 (C-05): reject missing/null, non-text, ill-formed Unicode, empty and whitespace-only input ... Boundary: 1 through 4,000 UTF-16 code units inclusive after trim
+ grokbot-salesforce N-25 [nonfunctional]  P-shiploop-spec: opus par/par, astra par/par;  K-shiploop-spec-default-bounds: opus cov/cov, astra cov/cov
    item: A latency target or bound for an answer, and truthful in-progress feedback in the interface while the async work runs.
    P-shiploop-spec round-7 (Non-functional requirements (latency and capacity)): Pending always reaches reply or actionable failure within the confirmed request deadline.
    P-shiploop-spec round-8 (R-2.c; Non-functional requirements): While waiting, show **Waiting for Grok** and disable duplicate sends in that view. ... No latency, availability or throughput SLA is specified for this development slice.
    K-shiploop-spec-default-bounds round-7 (R-2 Send; R-2 Recover): announces **Waiting for Grok**. ... The waiting cue does not assert provider receipt. ... The outbound wait is capped at 30 seconds after dispatch. The view stops waiting at 40 seconds from admission
    K-shiploop-spec-default-bounds round-8 (C-08): valid Send from an idle view shows the submitted question and an announced "Waiting for Grok…" status ... Boundary: one current attempt per mounted view, with no reply at or after 30,000 ms.
+ csv-user-import N-9 [edge]  P-shiploop-spec: opus par/par, astra par/par;  K-shiploop-spec-default-bounds: opus cov/cov, astra cov/cov
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec round-7 (A6): If either cap is exceeded, provide a file-limit error with zero writes. ... Each cap is inclusive.
    P-shiploop-spec round-8 (C5): An oversized or over-row-limit file receives a useful limit message and writes zero users.
    K-shiploop-spec-default-bounds round-7 (R-2): At most 262,144 file bytes (256 KiB) and 500 data records. ... exceeding a cap rejects the entire file before any user write. Show the failing category and the applicable limit
    K-shiploop-spec-default-bounds round-8 (R-2 Apply file limit / Apply record limit): Reject a file of 1,048,577 bytes or more and report the file-size limit. No users are created. ... Reject 1,001 or more data records with a row-limit error.

