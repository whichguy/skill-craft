# Independent review — cycle 2

Scope reviewed: the current W1 step plan, frozen controlled identity contract,
copied Field Notes baseline, producer boundary, and prior review records. This
was a fresh read-only review; it did not inspect the preregistered oracle or
edit the candidate.

## Material finding

The active-view reset in the candidate plan clears the held revision on account
change and lets a returning account accept an equal-revision response. That
contradicts the frozen contract's per-account comparison rule: an equal revision
is a no-change heartbeat, and a response is accepted only if newer than the
held revision for that account
([controlled-status-identity-contract.md - acceptance rule: equal heartbeat](<study>/candidate-status-complete/evidence/controlled-status-identity-contract.md:52)).
The prior independent review correctly exposed the empty-return issue
([reviewer-one.md - account-return finding: cleared display with held revision](<study>/candidate-status-complete/product/.shiploop-improve/nav-feb81a8fc7cd4f7fa1ecfdfb0887a90d/nav-b6aa8ba5f6ef4c66b878c853184790e3/reviews/reviewer-one.md:9)),
but the interim repair changed the authoritative heartbeat semantics. The plan
needs a conforming client-state lifecycle or a genuine external contract gap;
it cannot claim both behaviors as written.

## Other review areas

The plan otherwise keeps an aggregate-only UI and does not infer job-ID,
ordering, label, or JavaScript-safe-integer restrictions. It separates selector
context from host authorization, keeps W2 blocked, specifies accessible states
and observer-scoped GET-only testing, preserves existing UI premises, and does
not overclaim controlled-host evidence.

**Classification recommendation: non-trivial.** The per-account heartbeat
lifecycle is a material interaction/state-contract issue, so this cannot count
as a qualifying trivial review.
