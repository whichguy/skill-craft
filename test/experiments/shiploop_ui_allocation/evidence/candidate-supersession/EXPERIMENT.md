# Supersession-routing diagnostic

This isolated control tests whether a cold inner-loop producer follows a
reviewed accepted replacement of a stale global planning order. It is not a
feature implementation, deployment, live integration, or a paired A/B result.

## Frozen setup

- `evidence/request.md` states the selected W2 local-bootstrap scope.
- `run/notes/global-plan.md` is the retained historical original with the
  obsolete W1 -> W2 integration -> W3 bootstrap order.
- `run/notes/global-plan-reviewed-replacement.md` is the reviewed current order:
  W1 retained requirements/design basis -> W2 local bootstrap -> W3 integration.
- `product/docs/requirements.md` and `product/docs/design.md` provide W1's
  actual retained source basis. The source-read-only control leaves the normal
  durable correction of the historical plan record pending with its named owner.
- `oracle/expected.json` is frozen before launch and withheld from the producer.

`evidence/seed_state.py` creates eight explicitly synthetic early-stage records
(intake through select-work), then an actual selected candidate ShipLoop
`step-plan` action for W2. The synthetic cursor is not a claim of prior producer
or Improve execution. The actual producer may write a W2 plan and existing
check output only; it must submit one current callback and stop before Improve.

## What would count as support

The result supports the allocation only if the actual W2 plan uses the reviewed
replacement as current, keeps the obsolete note as history, treats future W2
local setup as independent of W3's external contract, carries W3 and the
pending durable correction forward separately, and does not claim feature,
remote, or Improve completion. The hidden oracle assesses those semantic
properties after the producer returns.
