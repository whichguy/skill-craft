# K-shiploop-spec-default-bounds against P-shiploop-spec, round-8, item by item (set X3)

## sonnet-high, judge claude-opus-5-5: 0 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 1 the other way
- csv-user-import N-18 [operator] P-shiploop-spec: covered; K-shiploop-spec-default-bounds: partial
    item: Cancelling an import that is running, and retrying only the rows that failed.
    P-shiploop-spec (Transition ledger / A-4): cancellation: n/a, because the operation has no user cancel and a client disconnect does not stop a commit already begun ... the file can be fixed and re-uploaded once.
    K-shiploop-spec-default-bounds (A-3): No partial state to explain or repair; a fixed file can be re-uploaded whole.

## sonnet-high, judge gpt-6.2-astra: 0 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
   | 

## sol-medium, judge claude-opus-5-5: 1 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
+ gym-waitlist N-17 [operator] P-shiploop-spec: partial; K-shiploop-spec-default-bounds: covered
    item: Staff can see the waitlist, promote or remove someone by hand, and see who was promoted when.
    P-shiploop-spec (Scope and basis / R-6.A3): The waitlist adds no staff workflow ... Authorized operations staff can retrieve app-owned outcomes for join, withdrawal, closure, promotion ...
    K-shiploop-spec-default-bounds (R-2 Domain rules; R-4.c; R-4 UI premises): There are no manual queue overrides ... Authorized operators can retrieve correlated outcomes for join, leave, promotion ... No new ... roster ... or queue-management screen.

## sol-medium, judge gpt-6.2-astra: 0 covered by K-shiploop-spec-default-bounds and not by P-shiploop-spec; 0 the other way
   | 

