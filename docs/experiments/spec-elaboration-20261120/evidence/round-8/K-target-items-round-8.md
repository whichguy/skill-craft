# K-shiploop-spec-default-bounds against P-shiploop-spec, round-8, item by item (set X1)

## sonnet-high, judge claude-opus-5-5: 4 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 2 the other way
+ grokbot-salesforce N-14 [unhappy] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: The model API refusing (4xx), failing (5xx) and timing out each have a distinct, stated user-visible outcome.
    P-shiploop-spec (R-5): Any other non-2xx status (400, 404, 3xx, 5xx) | `upstream_error` | "Grok is temporarily unavailable. Try again."
    K-shiploop-spec-default-bounds (R-5): Request rejected | other HTTP 4xx except 429 | BAD_REQUEST ... Upstream failure | HTTP 5xx | UPSTREAM ... Timeout | no response within the configured timeout (60 s default) | TIMEOUT
+ gym-waitlist N-10 [edge] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A cap on the waitlist itself, and what a person sees when even the waitlist is full.
    P-shiploop-spec (G-4, NFR-10): Waitlist cap (per class, per member) unspecified. No bound is invented. ... Treated as unbounded in the spec
    K-shiploop-spec-default-bounds (A-1; R-1): Waitlist capacity is **10 waiting entries per session** ... open-full, waitlist = 10 | `Waitlist full` disabled | `Class full · 10 on waitlist`
+ invoice-reminders N-19 [nonfunctional] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A bound on sending volume or on how late a scheduled reminder may go out.
    P-shiploop-spec (R-9): So a customer never gets more than one reminder per invoice per run. ... There is no maximum lateness: a late reminder is still sent, with accurate wording.
    K-shiploop-spec-default-bounds (R-3): Maximum reminders ever sent for one invoice = number of offsets (A-6, A-8).
+ csv-user-import N-9 [edge] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec (R-2 / R-11): a configured maximum size in bytes and a configured maximum number of data rows... FILE_TOO_LARGE | size above the configured byte limit | TOO_MANY_ROWS
    K-shiploop-spec-default-bounds (A-5): file at most 2,097,152 bytes (2 MiB); at most 5,000 data rows ... `file_too_large` (HTTP 413) ... `too_many_rows`, 422, nothing created
- invoice-reminders N-10 [edge] P-shiploop-spec: covered; K-shiploop-spec-default-bounds: partial
    item: Time zone and sending hours: the customer's local time, business hours, weekends and holidays.
    P-shiploop-spec (A-2, A-10): sent at **09:00** account-local time ... Offsets are plain calendar days: no business-day or holiday calendar.
    K-shiploop-spec-default-bounds (A-5): Reminder time: 09:00 in the account's time zone (UTC when the account has none).
- csv-user-import N-13 [async] P-shiploop-spec: covered; K-shiploop-spec-default-bounds: partial
    item: The new users' invitation or welcome mail: whether hundreds go out at once, and the pacing if so.
    P-shiploop-spec (A-3): Import sends no email and sets no password.
    K-shiploop-spec-default-bounds (R-12.3): Importing the 5,000 users of FX-17a sends 5,000 onboarding messages and not more or fewer, **if** single creation sends one

## sonnet-high, judge gpt-6.2-astra: 4 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 2 the other way
  +grokbot-salesforce N-14, +grokbot-salesforce N-26, +gym-waitlist N-10, +csv-user-import N-9 | -gym-waitlist N-11, -csv-user-import N-13

## sol-medium, judge claude-opus-5-5: 5 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 1 the other way
+ grokbot-salesforce N-21 [edge] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: The first use (no history), an empty question, and an answer or question at the maximum accepted length.
    P-shiploop-spec (R-1.a; R-2.a): Blank, whitespace-only, or oversized input is rejected with an inline correction and zero provider requests. ... The confirmed prompt maximum is inclusive in the stated unit.
    K-shiploop-spec-default-bounds (C-05): reject missing/null, non-text, ill-formed Unicode, empty and whitespace-only input ... Boundary: 1 through 4,000 UTF-16 code units inclusive after trim
+ grokbot-salesforce N-25 [nonfunctional] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A latency target or bound for an answer, and truthful in-progress feedback in the interface while the async work runs.
    P-shiploop-spec (R-2.c; Non-functional requirements): While waiting, show **Waiting for Grok** and disable duplicate sends in that view. ... No latency, availability or throughput SLA is specified for this development slice.
    K-shiploop-spec-default-bounds (C-08): valid Send from an idle view shows the submitted question and an announced "Waiting for Grok…" status ... Boundary: one current attempt per mounted view, with no reply at or after 30,000 ms.
+ invoice-reminders N-1 [interaction] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: The schedule: how many reminders and at what offsets from the due date, including whether any are sent before it.
    P-shiploop-spec (R-1): A reminder slot is one occurrence in the billing scope's approved recurring policy. Eligibility requires ... a reached due instant
    K-shiploop-spec-default-bounds (R-2(b), R-2(a)): Ordinals 1, 2 and 3 open at 09:00 UTC respectively 1, 7 and 14 UTC calendar days after the authoritative due date. ... An invoice due today or in the future is excluded.
+ csv-user-import N-7 [unhappy] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: File encoding and shape: a byte-order mark, line endings, quoted fields containing commas or newlines.
    P-shiploop-spec (R-2 Proposed file contract): with an optional UTF-8 BOM, LF or CRLF record endings, and a final newline allowed. ... Quoted fields are parsed as fields, including commas within quotes and doubled quotes as a literal quote.
    K-shiploop-spec-default-bounds (R-2 Parse file and schema): valid UTF-8 CSV with an optional initial UTF-8 BOM, LF or CRLF line endings, and optional final line ending... Support quoted fields, commas and line breaks inside quotes, and doubled quotes
+ csv-user-import N-9 [edge] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec (C5): An oversized or over-row-limit file receives a useful limit message and writes zero users.
    K-shiploop-spec-default-bounds (R-2 Apply file limit / Apply record limit): Reject a file of 1,048,577 bytes or more and report the file-size limit. No users are created. ... Reject 1,001 or more data records with a row-limit error.
- grokbot-salesforce N-14 [unhappy] P-shiploop-spec: covered; K-shiploop-spec-default-bounds: partial
    item: The model API refusing (4xx), failing (5xx) and timing out each have a distinct, stated user-visible outcome.
    P-shiploop-spec (R-2.c; Verification evidence): Distinguish unavailable setup/access, rate limiting, and timeout/service or unusable-response failure. For timeout or disconnect say the answer could not be confirmed.
    K-shiploop-spec-default-bounds (C-04): Timeout, no transport, upstream 5xx or platform invocation failure without a known more specific classification | "No reply received. Send again."

## sol-medium, judge gpt-6.2-astra: 5 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-20, +grokbot-salesforce N-25, +invoice-reminders N-1, +csv-user-import N-7, +csv-user-import N-9 | 

