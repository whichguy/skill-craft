# Locator-only recovery trial

Registered before workers run. This is a bounded capability trial, not an A/B
comparison, reliability estimate or unattended model launcher.

The fixture specification requires `clean_lines(text)` to accept only strings,
use Python `splitlines()` and `strip()`, discard blank lines, and preserve order
and duplicates. A fixed oracle uses independently specified expected outputs;
the seed must fail and a reference must pass before worker launch.

The public CLI creates the run and traverses an explicitly synthetic prelude to
`implement`. Those declarations are navigation setup, not performed SDLC work.
Each worker starts with no preceding conversation and receives only a durable
locator path plus its one-action stop rule. It must obtain its task from `next`.
Workers may read the actual fixture and relevant run notes, but are not given
this file, calibration, reserved oracle or future-stage expectations.

1. A reads the locator, recovers `implement`, changes the fixture and records
   effects, then deliberately stops before the completion callback. The saved
   action must remain unchanged. This is an intentional interruption boundary,
   not a crash-injection claim.
2. B starts fresh from the same locator, recovers the same action, reconciles
   the existing work and evidence, completes that action once, and stops.
3. C starts fresh from the locator, recovers `test-refine`, completes its
   actual test-planning duty from the changed code and specification, and stops.
4. D starts fresh from the locator, recovers `test-author`, writes meaningful
   tests, completes that action once, and stops at the returned packet.

Reserved expectations: accepted history grows by exactly three real actions
(implement, test-refine, test-author); final cursor is `document`. The locator
never acquires a copied stage/action or becomes authoritative. Final source
passes the fixed oracle; authored tests pass and reject the seeded defect.
Responses, initial/interrupted/final state, source, notes and receipts are kept.
Any failure remains in the record even if a later repair succeeds.

Limits: same model family, one small local task, persistent local filesystem.
Fresh contexts are supplied by the experiment host. ShipLoop does not launch
models, clear context, enforce note retention or prove substantive work from
`done`. This trial does not establish cross-host or full-graph LLM reliability.
