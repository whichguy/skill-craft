# H-shiploop-spec-duty4-no-open against P-shiploop-spec, round-10, item by item (set N1)

## sonnet-high, judge claude-opus-5-5: 1 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
+ csv-user-import N-9 [edge] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec (R-3): two configured limits apply: MAX_BYTES (file size) and MAX_ROWS ... Over either → rejected, nothing created. ... No default number is specified.
    H-shiploop-spec-duty4-no-open (R-3): A file larger than **2,097,152 bytes** is rejected `TOO_LARGE`; a file with more than **5,000 data rows** is rejected `TOO_MANY_ROWS`.

## sonnet-high, judge gpt-6.2-astra: 2 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-20, +csv-user-import N-9 | 

## sol-medium, judge claude-opus-5-5: 2 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 1 the other way
+ grokbot-salesforce N-21 [edge] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: The first use (no history), an empty question, and an answer or question at the maximum accepted length.
    P-shiploop-spec (R-2 2a): The maximum accepted input is inclusive. A valid multibyte prompt within the limit retains its text. The exact production bound and counting unit are open.
    H-shiploop-spec-duty4-no-open (C4): missing, empty, or Unicode White_Space-only input shows “Enter a prompt.” ... At 16,384 bytes the send is allowed; from 16,385 bytes it is rejected
+ csv-user-import N-9 [edge] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec (R-2 A4): Enforce each limit on the authoritative boundary, reject the whole file with the applicable limit and permit a smaller replacement.
    H-shiploop-spec-duty4-no-open (TC-4): Default maximum 65,536 file bytes inclusive ... A file above the cap is rejected with the limit and zero creates.
- invoice-reminders N-8 [async] P-shiploop-spec: covered; H-shiploop-spec-duty4-no-open: partial
    item: The sending provider's rate limit and how a large batch is paced within it.
    P-shiploop-spec (Non-functional requirements): including simultaneous due work or backlog, respect verified platform limits. With a rate limit or quota exhaustion, defer eligible work while the policy permits, expose the delay/failure, and resume without duplicates.
    H-shiploop-spec-duty4-no-open (R-3 Recovery): Respect runtime and channel admission limits. Stop submitting when the boundary denies capacity and leave eligible work discoverable for a later permitted evaluation.

## sol-medium, judge gpt-6.2-astra: 2 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-20, +csv-user-import N-9 | 

