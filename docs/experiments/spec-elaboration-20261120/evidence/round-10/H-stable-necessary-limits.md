# H-shiploop-spec-duty4-no-open against P-shiploop-spec over round-9, round-10, set N1 (6 items): items settled by one arm in every round and by the other in none (registered judge), with the second judge's states beside them

## sonnet-high: 1 settled by H-shiploop-spec-duty4-no-open in every round and by P-shiploop-spec in none; 0 of them the same under the second judge; 0 the other way
+ csv-user-import N-9 [edge]  P-shiploop-spec: opus par/par, astra cov/par;  H-shiploop-spec-duty4-no-open: opus cov/cov, astra cov/cov
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec round-9 (R-3 / G-5): at `IMPORT_MAX_BYTES` accepted, one byte over refused; at `IMPORT_MAX_ROWS` accepted, one row over refused.
    P-shiploop-spec round-10 (R-3): two configured limits apply: MAX_BYTES (file size) and MAX_ROWS ... Over either → rejected, nothing created. ... No default number is specified.
    H-shiploop-spec-duty4-no-open round-9 (R-3): content of 524,289 bytes or more → 413 `file_too_large`; 1,001 or more data rows → 422 `too_many_rows` carrying `limit` 1000 and `found`
    H-shiploop-spec-duty4-no-open round-10 (R-3): A file larger than **2,097,152 bytes** is rejected `TOO_LARGE`; a file with more than **5,000 data rows** is rejected `TOO_MANY_ROWS`.

## sol-medium: 1 settled by H-shiploop-spec-duty4-no-open in every round and by P-shiploop-spec in none; 1 of them the same under the second judge; 0 the other way
+ csv-user-import N-9 [edge]  P-shiploop-spec: opus par/par, astra par/par;  H-shiploop-spec-duty4-no-open: opus cov/cov, astra cov/cov
    item: A limit on file size or row count, and what happens to a file above it.
    P-shiploop-spec round-9 (R-2 File contract): Reject ... files above the published size or record limit. ... For each confirmed cap, the cap itself does not cause rejection and the first value above it does.
    P-shiploop-spec round-10 (R-2 A4): Enforce each limit on the authoritative boundary, reject the whole file with the applicable limit and permit a smaller replacement.
    H-shiploop-spec-duty4-no-open round-9 (R-2): Above that effective maximum, show the maximum and how to split or reduce the file. Reject before any creates ... The maximum is inclusive. Apply it to the file bytes before decoding
    H-shiploop-spec-duty4-no-open round-10 (TC-4): Default maximum 65,536 file bytes inclusive ... A file above the cap is rejected with the limit and zero creates.

