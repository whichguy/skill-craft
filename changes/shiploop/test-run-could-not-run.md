---
bump: minor
---
A ShipLoop test run that never reached a verdict about the product is no longer
counted as a product failure.

- A command that times out, cannot start, or is skipped because the invocation's
  budget ran out is recorded `disposition: could-not-run`. It still refuses the
  stage — nothing is accepted on unrun tests — but it does not spend one of the 7
  refused runs, so an environment problem can no longer rewrite a work item's
  step plan. A real failing check beside a timeout is still a failure.
- Fixed: a command that could not start (`OSError`) was recorded as `failed`.
  The `error` status was computed and then overwritten, so a spawn failure was
  indistinguishable from a failing test.
- At the 7-refused-run gate the packet now names the outcome the stage actually
  allows: `revise` back to the step plan at an INNER stage, and `replan` with
  corrective work items at the outer `system-test` and `release-verify`, which
  have no step plan to revise and where the navigator rejects `revise`.
- A timeout is reported as reaching no verdict rather than as a product failure,
  since it can mean a deadlock, a broken test, a suite too slow for the budget,
  or an external dependency.
- Because those attempts no longer reach the gate, the refusal names the routes
  out explicitly: a hang in the item's own code, test or fixture is run-fixable
  and is not a blocker, a wrong recorded command or budget takes the stage's
  remedy, and `blocked` is only for what the user, an access grant or an outside
  dependency must supply.

The per-invocation command timeout (600s) and budget (1800s) are unchanged.
