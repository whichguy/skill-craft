---
bump: minor
---
A ShipLoop test run that never reached a verdict about the product is no longer
counted as a product failure.

- A command that times out, cannot start (the process could not be spawned; a
  command the shell cannot find or execute exits 126 or 127 and is still a
  failure), or is skipped because the invocation's
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
  and is not a blocker, a recorded command that is wrong or too slow to fit the
  run's budget takes the stage's remedy, and `blocked` is only for what the user,
  an access grant or an outside dependency must supply. A skipped command is
  named as such: it never started because the commands before it used the run's
  budget, and they run in the same order every time, so a retry skips it again.
- That remedy is accepted. At `test-green`, `regression` and `static-checks` the
  navigator used to require a stopped Until Loop packet for `revise`, which a
  `could-not-run` attempt never produces, so the route the refusal named was
  refused (and at `static-checks`, `blocked` too). ShipLoop's own record now
  supports it: when its latest test run for the action is `could-not-run` (and,
  at `static-checks`, where it was never opened, after 7 refused runs too),
  `revise` (and `blocked` at `static-checks`) is accepted without a new loop
  packet; `replan` with corrective work items at the outer stages and `revise`
  at the other INNER stages were already accepted. An ordinary `done` still needs
  a complete loop packet, and a later failed run closes the route again.
- The outer-stage rerun packet says which stage recorded its commands
  (`system-test-author`, `release-plan`) instead of the step plan, and the
  `test-red` text no longer asks for the item's own code to be fixed. The
  `end-of-work review` gate, which is not a graph stage and has no remedy outcome,
  no longer says that a failing run ends in `blocked`.
- Keepalive's stuck release (14 continuations without an accepted result) keeps
  its value, which is no longer paired with the 7-run cap for a command that
  cannot run; its comment says so and its notice names the outcomes above.

Known limits, kept on purpose: a timed-out command's partial output is not read,
so a suite that prints failures and then hangs is `could-not-run`; and at the
`end-of-work review` gate, which reruns every item's recorded commands for the
Improve import, a recorded command that cannot run has no remedy outcome.

The per-invocation command timeout (600s) and budget (1800s) are unchanged.
