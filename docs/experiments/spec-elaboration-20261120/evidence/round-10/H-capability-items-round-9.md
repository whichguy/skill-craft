# H-shiploop-spec-duty4-no-open against P-shiploop-spec, round-9, item by item (set X3)

## sonnet-high, judge claude-opus-5-5: 3 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
+ gym-waitlist N-17 [operator] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: Staff can see the waitlist, promote or remove someone by hand, and see who was promoted when.
    P-shiploop-spec (PD-9, G-6, NFR-6): Staff roster views, manual reordering and staff removal are out of scope.
    H-shiploop-spec-duty4-no-open (A-10): Staff get no waitlist view and no manual promotion in this change.
+ invoice-reminders N-17 [operator] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: Turning it off globally and per customer, previewing or dry-running it, and resending by hand.
    P-shiploop-spec (R-1): Disabling stops new sends immediately for ticks that start after the save
    H-shiploop-spec-duty4-no-open (D-10): No per-invoice or per-customer pause ... the only stop controls are the global `enabled` switch, `dry-run` mode, and the invoice leaving the unpaid state.
+ csv-user-import N-18 [operator] P-shiploop-spec: partial; H-shiploop-spec-duty4-no-open: covered
    item: Cancelling an import that is running, and retrying only the rows that failed.
    P-shiploop-spec (A-4 / NFR-2): a corrected file can be re-uploaded whole ... no durable import record or resume is provided (A-8) because the all-or-nothing rule makes a resume unnecessary.
    H-shiploop-spec-duty4-no-open (R-12): cancelling an in-flight import (cancelling the page request would not undo a server effect)

## sonnet-high, judge gpt-6.2-astra: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
   | 

## sol-medium, judge claude-opus-5-5: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 1 the other way
- csv-user-import N-18 [operator] P-shiploop-spec: covered; H-shiploop-spec-duty4-no-open: partial
    item: Cancelling an import that is running, and retrying only the rows that failed.
    P-shiploop-spec (R-4 Lifecycle boundaries; R-4 Recovery): Cancellation after submission, deletion of completed imports from the UI, and account migrations are inapplicable to this create-only flow. ... A rejected file can be corrected and sent as a fresh submission.
    H-shiploop-spec-duty4-no-open (R-4, R-3): Leaving the view drops the local draft and result and does not undo writes or promise cancellation ... Authorized resubmission resolves each supplied identity against current directory state

## sol-medium, judge gpt-6.2-astra: 0 covered by H-shiploop-spec-duty4-no-open and not by P-shiploop-spec; 0 the other way
   | 

