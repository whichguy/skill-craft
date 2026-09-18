# Corrected intake decisions for terminal import

This child record applies the accepted findings from [review-one.md](review-one.md) within the frozen no-product-edit authority. It is the source for the parent completion evidence’s revised `final_result`; it does not claim that the historical first-attempt intake note was rewritten.

## Corrected boundary

The embedded host controls authorization and account identity. The API owns durable export/job state and scopes its operations to the host-authorized account. The client owns only transient presentation state unless a later target-compatible decision establishes an allowed persistence mechanism.

## Required discovery questions

1. **Operation identity / reload recovery:** `clientOperationId` is required to reconcile a lost POST confirmation. Because the controlled target reports client persistent storage as `not_assessed` and exposes no draft API, discovery must establish whether a safe target-compatible retention/reload path exists. Until then, the client design may not claim reload-safe reconciliation or automatically retry an uncertain request with a new identity.
2. **API state and data contract:** discovery must resolve or retain a gap for status vocabulary and transitions, collections and any pagination/selection data, response/error shapes, `GET /api/operations/:clientOperationId` outcomes, `GET /api/exports/:jobId` unavailable/not-complete cases, and repeated POST behavior for the same operation identity. These facts determine UI state, accessibility wording, stale-response handling, and whether a retry action is valid.
3. **Failure presentation:** the request requires a visible failure state. The supplied facts do not establish that every failure is retryable; retry/recovery controls must be conditional on verified API semantics rather than asserted as an accepted behavior.

## Preserved facts and limits

Keep the controlled-fixture/deployed-host distinction, static self-only asset/CSP constraints, no server runtime, no WebSocket, same-origin HTTPS API capability, visible-only polling, and foreground authoritative-state reconciliation. No live endpoint, deployed artifact, browser behavior, API response fixture, target storage capability, or release authority was observed.

## Final-result effect

The parent terminal `final_result` should remain `outcome: "done"` and preserve the intake authority limits, but summarize these corrected boundaries and carry this decision record, review records, check evidence, and the original intake sources in `evidence_refs`. It must not state that a durable storage strategy, a retry policy, an API schema, or a deployment verification has been established.
