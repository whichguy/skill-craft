# M-shiploop-spec-members against P-shiploop-spec, round-8, item by item (set X3)

## sonnet-high, judge claude-opus-5-5: 0 covered by M-shiploop-spec-members and not by P-shiploop-spec; 1 the other way
- csv-user-import N-18 [operator] P-shiploop-spec: covered; M-shiploop-spec-members: partial
    item: Cancelling an import that is running, and retrying only the rows that failed.
    P-shiploop-spec (Transition ledger / A-4): cancellation: n/a, because the operation has no user cancel and a client disconnect does not stop a commit already begun ... the file can be fixed and re-uploaded once.
    M-shiploop-spec-members (R-5): Recovery: nothing to repair after failure; the admin fixes the file and re-uploads.

## sonnet-high, judge gpt-6.2-astra: 0 covered by M-shiploop-spec-members and not by P-shiploop-spec; 0 the other way
   | 

## sol-medium, judge claude-opus-5-5: 0 covered by M-shiploop-spec-members and not by P-shiploop-spec; 0 the other way

## sol-medium, judge gpt-6.2-astra: 1 covered by M-shiploop-spec-members and not by P-shiploop-spec; 0 the other way
  +csv-user-import N-18 | 

