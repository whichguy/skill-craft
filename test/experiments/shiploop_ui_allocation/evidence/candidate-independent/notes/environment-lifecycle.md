# Environment lifecycle — W1 remote export status

This note records planning evidence for the active W1 step-plan producer. It is
not a deployment receipt or a graph cursor.

- **Observed execution location:** the non-Git fixture at
  <study>/candidate-independent/product.
  Its baseline content identity and the successful node --check app.js
  observation are retained in
  ../../evidence/step-plan-nav-967cf4518b7f434da0320a6435948bf5.md.
- **Observed target contract:** controlled fixture target
  fieldnotes-embedded-v2; static same-origin asset delivery and HTTPS
  request/response are available. No deployed server runtime, WebSocket,
  persistent client storage, or draft API is available. The target may suspend
  while hidden, so the documented export API requires visible polling and
  foreground reconciliation after implementation.
- **Authority and remote boundary:** no remote deployment, account mutation, or
  API-fixture creation is authorized or available in this experiment. Local
  source checks do not verify a remote service or consumer.
- **Current blocker and earliest gate:** before W1 implementation/test authoring,
  the API/requirements owner must provide the authorized Field Notes
  collection-to-collectionId mapping and JSON/state/error fixture for all four
  export routes. Re-open the W1 step-plan against that source; do not invent it
  from note IDs or from an older storage observation.
- **Later verification route:** source/syntax and deterministic mocked local
  tests can run after the contract fixture is supplied. An authorized browser
  observation against the exact deployed candidate and account remains a later,
  separate consumer-verification obligation.
