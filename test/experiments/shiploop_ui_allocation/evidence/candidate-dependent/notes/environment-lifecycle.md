# W1 environment lifecycle assessment

## Scope and observed target

This note covers only W1, reload-persistent account-scoped drafts, in the
controlled fixture. It is not a deployment receipt or a live-host observation.

- Repository: <study>/candidate-dependent/product
- Target observed by product/scripts/probe_environment.py:
  fieldnotes-embedded-v2
- Current target facts: client_persistent_storage is unavailable, draft_api is
  false, server_runtime is false, websocket is false, and script-src/style-src
  accept only same-origin assets.
- Product documentation says the embedded host controls authorization and account
  identity. The current account selector is a UI control, not evidence that a
  durable client namespace is an authenticated account boundary.
- There is no remote deployment access in this experiment. No external write,
  credential operation, package install, or target mutation was attempted.

## Readiness and blocked dependency

The requested recovery outcome needs a durable carrier that survives reload and
enforces the account boundary. The current target supplies neither a durable
client store nor a draft API. The historical fieldnotes-embedded-v1 observation
in product/docs/design.md is explicitly historical and is not a supplier for
fieldnotes-embedded-v2.

No planned preparation item or named capability owner exists in this one-item
run. The missing supplier is therefore the target/platform owner, or a user
instruction that names an authorized supplier and permits a corrected plan.
This W1 producer cannot create that capability.

Definition of ready before W1 can leave its blocked boundary:

1. The supplier publishes a current target-compatible contract for either a
   durable client-store interface or an authoritative draft API, including
   account/identity scoping, retention, error behavior, and its allowed static
   embedded invocation path.
2. A rerun of product/scripts/probe_environment.py reports that contract for
   the same target, rather than relying on fieldnotes-embedded-v1.
3. The selected solution permits a real same-account reload check and a
   cross-account/logout isolation check. A local preview or a UI-only key
   prefix does not satisfy either condition.
4. The step is resumed or replanned through the ShipLoop route after the new
   supplier evidence is recorded.

The earliest dependent activity is the remaining W1 test/implementation path.
The planned target-browser check is required but currently blocked; source
inspection and the controlled probe do not substitute for it.

## Delivery and recovery boundary

This producer is planning-only and does not need delivery authority. If a later
supplier requires a deployment, target configuration, account binding, or
service write, that operation needs its own concrete authority and target
assessment before it runs. Preserve this note and the W1 plan as the recovery
locator; do not create a replacement run or infer capability from a local
browser preview.
