---
bump: patch
---
The audit harness follows ShipLoop's 8-stage inner loop (step-plan, test-spec, validate-existing, implement, test,
document, verify, carry-forward; 24 stages in all). The DAG replay oracle states the new stage lists and edges by
hand, parks every accepted implement step for Improve under both planning-review options, and walks 24 stages with
33 callbacks (28 in a `none` run, 44 with two work items). The old repeat-at-step-plan scenario became a repeat at the
test-strategy checkpoint, and a new revise scenario checks that test refuses repeat and sends the item back to its
step plan. Live lifecycle evidence no longer asks for a callback for a stage ShipLoop recorded by script
(validate-existing with every expectation matched, a left-out test or document), and `complete --check-only` is not
credited as a callback. `red-check` is a recognised ShipLoop verb; the behaviour capture's closed stage list is
the new one, and its outcome list accepts `revise`.
