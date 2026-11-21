# H-shiploop-spec-duty4-no-open against P-shiploop-spec, round-9, item by item (set N1)

## sonnet-high, judge claude-opus-5-5: 1 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
+ csv-user-import N-9 [edge] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec (R-3 / G-5): at `IMPORT_MAX_BYTES` accepted, one byte over refused; at `IMPORT_MAX_ROWS` accepted, one row over refused.
    H-shiploop-spec-duty4-no-open (R-3): content of 524,289 bytes or more → 413 `file_too_large`; 1,001 or more data rows → 422 `too_many_rows` carrying `limit` 1000 and `found`

## sonnet-high, judge gpt-6.2-astra: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
   | 

## sol-medium, judge claude-opus-5-5: 3 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
+ grokbot-salesforce N-20 [edge] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: A conversation outgrowing the model's context window: what is trimmed or summarised, and at what size.
    P-shiploop-spec (R-2 B; R-3 A): Do not silently clip user input or retained context ... A context-limit rejection lets the user clear chat or shorten the draft
    H-shiploop-spec-duty4-no-open (R-2.A; Assumptions R-2.A): Default 8,192 UTF-8 bytes bounds one billable prompt ... and is well below the selected model's documented context capacity.
+ invoice-reminders N-1 [interaction] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: The schedule: how many reminders and at what offsets from the due date, including whether any are sent before it.
    P-shiploop-spec (R-1 Rules left open; R-2 Rules left open): Actual authority and activation path, scope of enablement, cadence and repeat count ... The product owner must confirm overdue versus pre-due coverage
    H-shiploop-spec-duty4-no-open (R-1 A2; R-3 D1): eligible starting at the beginning of the day after its due date ... The invoice is ineligible throughout the due date. / Use one automatic reminder milestone per organization and stable invoice identity
+ csv-user-import N-9 [edge] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec (R-2 File contract): Reject ... files above the published size or record limit. ... For each confirmed cap, the cap itself does not cause rejection and the first value above it does.
    H-shiploop-spec-duty4-no-open (R-2): Above that effective maximum, show the maximum and how to split or reduce the file. Reject before any creates ... The maximum is inclusive. Apply it to the file bytes before decoding

## sol-medium, judge gpt-6.2-astra: 4 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
  +grokbot-salesforce N-20, +invoice-reminders N-1, +invoice-reminders N-8, +csv-user-import N-9 | 

