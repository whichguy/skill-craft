# Plan Improve review 3 — local and browser proof-boundary audit

**Scope and independence.** This distinct self-review compared the plan’s
implementation and proof claims with the strategy’s explicit browser-only
FN-NFR-1 and browser follow-up requirements. No additional independent
reviewer was used.

**Finding — material plan correction.** The earlier P-5/P-8 wording could
make FN-NFR-1 look like a local test result even though the accepted strategy
defines it as a browser-only regression assertion. P-6 also said local checks
would preserve the rendered R-1/FN-NFR-1 baseline, and P-7 said local checks
would show rendered focus/input/reading-position survival. Those claims would
blur the plan’s declared local-versus-target proof boundary.

The corrected plan now:

- has P-5 register local FN-TC work while retaining the FN-NFR-1 target
  assertion and intended membership until P-3b provides a browser route;
- has P-8 execute only locally executable FN-TC checks and retain FN-NFR-1
  for P-3b/P-9;
- makes P-6 reserve rendered journey/focus/input/reading-position/visual
  confirmation for P-9; and
- makes P-7 reserve rendered asynchronous preservation evidence for P-9.

P-9 remains the explicit real target recipient for FN-TC-1 through FN-TC-7
and FN-NFR-1 receipts. Local fakes still support ordering/state checks only.

**Check record.** review-three-checks.stdout/stderr retains an initial
checker-only failure because it searched for a bold Markdown variant of the
strategy phrase. It did not change the plan. The corrected
review-three-checks-rerun.stdout verifies the actual browser-only strategy
phrase, P-5/P-8/P-6/P-7 boundaries, all T/FN identifiers, P-9 receipts,
empty tracked-only status, and syntax-only Node diagnostic.

**Limits retained.** This is still a conditional plan. Q-R1, Q-R3, Q-R2a,
Q-R4, Q-R5, and G-6 remain unresolved. No carrier/API/cursor, browser target,
real fixture, product change, durable documentation update, or deployment
occurred. The plan remains in embedded Backchain mode.

**Disposition.** Non-trivial allowed run-local correction. Two subsequent,
distinct trivial reviews are required before terminal Improve acceptance.
