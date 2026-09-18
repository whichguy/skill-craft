# Cold-dependent W1 independent assessment

Scope assessed: `evidence/step-plan-w1.md`,
`run/notes/environment-lifecycle.md`, and the selected W1 in
`evidence/initial-packet.txt`. This is a planning assessment only. The producer
is parked for Improve; no terminal Improve evidence or product implementation
was assessed.

| Criterion | Actual evidence | Grade |
| --- | --- | --- |
| C1 — recover original UI basis and design guidance | The step plan retrieves current `README`, design `#UI identity`, platform, API, code, DOM and guidance-card SHA. It carries selector/list/textarea/controls, focus/touch/narrow layout and navy/amber identity into the proposed delta and names check locators. | Pass |
| C2 — failed readiness has observation, owner and scoped correction route | The plan reruns the v2 probe, records no persistent client store/draft API and no authoritative subject/logout signal, and makes target/browser checks explicit gaps. It correctly says W1 implementation must wait. However, it assigns the needed environment augmentation only to an unspecified “owner” and puts it in prose as step 1; it does not allocate an explicit preparation producer/work item before the dependent W1. | Partial — material allocation gap |
| C3 — reopen contradiction without relaxing scope | It distinguishes historical v1 from current v2, rejects visible selector identity as proof of logout isolation, retains the account-isolation/reload requirement, and names two possible target-compatible contracts without choosing or inventing one. | Pass |

## Actionable finding

**P1 — missing owner/work item for the prerequisite.** The plan says a host-approved
durable-store or draft-API plus authoritative identity/logout contract is required,
but no plan item owns establishing or evidencing it. The existing `W1` is already
selected as “Implement reload-persistent account-scoped drafts”; therefore the
proposed “obtain contract and re-run probe” cannot be treated as a completed
preparation phase or simply folded into implementation. Allocate a preparation
producer before W1 (or keep W1 blocked with a named external owner and recovery
route until replanning creates that producer). Its done evidence should be the
selected target-compatible contract, identity/logout semantics, a current probe,
and readiness result. This follows the frozen environment policy’s requirement for
an explicit preparation producer before its consumer and its rule that a failed
prerequisite cannot become N/A.

**P2 — selected-item scope widens into export status.** The initial packet states
that W1 is “Implement reload-persistent account-scoped drafts”; its retained context
selects reload-persistent drafts. The step plan nevertheless proposes an
`ExportWatcher`, visible polling and export-notification tests in W1. That behavior
may belong to another planned item or must be reconciled with the selected item and
its prerequisites before implementation. It should not be silently added while the
draft prerequisite blocks W1.

## Fixture confounds (not source gaps)

- The synthetic predecessor’s source locator is not a verified baseline; the plan
  correctly re-observed current files and hashes.
- The fixture product lacks `.git`; absence of a revision limits baseline identity
  evidence but is not a producer defect.
- The controlled probe is not a live target/deployment receipt; the plan labels
  that limit accurately.

## Policy basis

- `frozen/shiploop/references/environment-lifecycle.md`, “Plan preparation before
  its first consumer”: setup needs an explicit producer before dependent feature
  work; failed prerequisites block dependents.
- `frozen/shiploop/references/requirements-definition.md`, “Initial-plan
  reconciliation”: each architecture/state obligation needs an owner, prerequisite
  or supplier, and check.
- `frozen/shiploop/references/behavioral-requirements.md`, “Review, evidence, and
  reuse”: preserve locators and revalidate gaps without claiming unrendered or
  unexecuted behavior.
