# Backchain internal convergence correction — 2026-09-18

The earlier source-aware integration let the caller decide when to revise based on material findings. The user's clarified requirement is unconditional repeated evaluation **inside Backchain** until two consecutive distinct reviews find only trivial or no changes. This correction supersedes that earlier ownership and stopping decision; it does not reinterpret the earlier audit pilot as convergence evidence.

## Implementation plan and delivered contract

1. Keep the existing generator, dependency-review, elaborator, source audit, and bounded revise prompts as single-pass building blocks. Add a portable convergence-review prompt and companion report in Backchain; leave canonical plan JSON unchanged.
2. Make the normal native Backchain skill own whole-plan review, authorized repair, pass history, material reset, and the two-consecutive-pass condition. Repeat even when the initial candidate has no known material defect. Default to six assessment passes as a resource ceiling; exhaustion means incomplete, never convergence.
3. Revisit original request/source clauses, all outcome and verification sinks, the technical category index, relevant detailed cards, and forward effects on producers/consumers/new branches every pass. Preserve protected work and source identities. Unknown impact or unresolved planning gaps cannot qualify. Accurately modeled future execution prerequisites remain separately incomplete.
4. Keep an explicit diagnostic audit read-only and one-pass. Whole draft/revise calls own the loop. Direct checkout harness commands remain candidate/structural primitives; the skill must perform its semantic reviews after using them.
5. Have ShipLoop call one whole native draft or bounded revise operation and retain the returned convergence assessment in existing notes. ShipLoop and Improve do not manage Backchain's qualifying count; Improve retains its broader independent review. Missing selected convergence capability stays incomplete. No new ShipLoop lifecycle state, external runtime dependency, or script scheduler is introduced.

## Verification scope

Package tests cover materialized prompt availability, placeholder rendering, parity, and runnable behavioral eval inventory. ShipLoop tests check actual emitted action-packet routing and generated plugin parity. These checks alone do not establish that a model conducts adequate semantic reviews.

Bounded native trials and Backchain's required local-change gate are recorded in the Backchain experiment report, `docs/experiments/internal-convergence-2026-09-18.md`. The trial report distinguishes actual returned behavior from internal reasoning that cannot be observed independently. Neither planning convergence nor structural validation proves execution, successful experiments, or deployment.

Local ShipLoop validation passed: 21 navigator-v3 tests, 8 reference-routing tests, 4 Backchain-guidance tests, 14 standalone-Improve tests, and 27 marketplace-package tests (74 total), plus generated ShipLoop plugin parity and diff checks. This is focused validation, not a claim that the entire skill-craft suite ran locally.
