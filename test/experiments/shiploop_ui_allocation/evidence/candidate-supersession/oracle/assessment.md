# Independent post-producer assessment

This assessment was made after the producer returned. `oracle/expected.json`
was frozen before the producer launch and was withheld from that producer.

| Preregistered criterion | Assessment | Evidence |
| --- | --- | --- |
| The reviewed replacement is current and the original remains history. | Pass | `evidence/w2-step-plan.md` identifies the W1 -> W2 -> W3 order as current and preserves the original for audit. `run/notes/global-plan-reviewed-replacement.md` declares its precedence. |
| W2 remains the local static/bootstrap and Node-harness item. | Pass | The plan limits W2 to a future dependency-free local carrier/harness and does not return it to the original integration-first order. |
| W3 is retained but does not block W2. | Pass | W3's API/target decisions stay separately named and are expressly not a W2 bootstrap prerequisite. |
| Current step-plan authority and the pending stale-record correction are distinct from future W2 authority. | Pass | The plan names the delivery-plan owner, repository-owned planning-index destination, and reviewed-replacement locator while retaining later authorized W2 setup. |
| The static UI baseline is preserved without an invented delivery claim. | Pass | The plan preserves the existing shell/design sources and excludes feature/API/package/remote/deployment/Improve completion claims. |

## State and evidence boundary

The eight earlier stages are explicitly synthetic. The distinct W2 callback is
persisted and structurally valid, but its Improve child remains unbound and the
parent step remains pending. The plan is therefore evidence of one actual
producer callback, not proof of an accepted parent step, Improve completion,
feature implementation, deployment, or consumer behavior. Both frozen-input
checks report zero mismatches; `evidence/observed-state-after-producer.json`
correctly leaves `semantic_verification` false.

## Residual limitation

The fixture has no independently authenticated transport log for the producer
actor. The persisted state and returned packet demonstrate the callback
transition, but not actor identity. `accepted_producer_count` in the structural
reader counts the eight synthetic predecessors and can be misread; future
fixtures should rename it to `synthetic_predecessor_count` or add an explicit
`actual_producer_callback_count: 1` field.
