# H-shiploop-spec-duty4-no-open against P-shiploop-spec, round-10, item by item (set X3)

## sonnet-high, judge claude-opus-5-5: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 1 the other way
- csv-user-import N-18 [operator] P-shiploop-spec: covered; H-shiploop-spec-duty4-no-open: partial
    item: Cancelling an import that is running, and retrying only the rows that failed.
    P-shiploop-spec (Section 6 forbidden events, Section 1 out of scope): cancellation, expiry and restart are n/a: the operation is one synchronous request with no retained work / importing only the valid rows of a file with errors
    H-shiploop-spec-duty4-no-open (F-3): file or row problems → `rejected`, nothing created; screen Rejected; the admin fixes the file and starts F-1 again.

## sonnet-high, judge gpt-6.2-astra: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
   | 

## sol-medium, judge claude-opus-5-5: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 2 the other way
- gym-waitlist N-17 [operator] P-shiploop-spec: covered; H-shiploop-spec-duty4-no-open: absent
    item: Staff can see the waitlist, promote or remove someone by hand, and see who was promoted when.
    P-shiploop-spec (Scope; R-4 Open gaps; Owned event coverage): staff reordering ... excluded ... staff queue views are outside this change. ... Retain operational evidence of join, leave, promotion, closure
    H-shiploop-spec-duty4-no-open (None): None
- csv-user-import N-18 [operator] P-shiploop-spec: covered; H-shiploop-spec-duty4-no-open: partial
    item: Cancelling an import that is running, and retrying only the rows that failed.
    P-shiploop-spec (R-4 A4 / R-3 State and data): No post-submit cancel or promised unattended processing. ... Correct a failed batch and resubmit.
    H-shiploop-spec-duty4-no-open (TC-7): If a response was lost after commit, retry encounters the authoritative conflict and can create identities that did not commit. Closing the view does not promise cancellation or background completion.

## sol-medium, judge gpt-6.2-astra: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
   | 

