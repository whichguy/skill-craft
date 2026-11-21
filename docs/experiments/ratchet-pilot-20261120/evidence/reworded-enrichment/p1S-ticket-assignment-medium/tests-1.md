## Failing now
none — all 27 acceptance commands (C-1..C-22, U-1..U-5) pass on the product as it stands.

## Discoveries
- `node --test` (so `npm test`) also collects `acceptance/*.test.js` because it matches `**/*.test.js`; the acceptance files therefore run under `npm test` too, and a test that itself runs `npm test` would recurse | Observable: `npm test` output lists the acceptance tests | Why: C-22's acceptance test runs `npm test -- test/` to avoid the recursion; the specification may want `npm test` to say which folders it runs.
- A resolved or closed ticket keeps its assignee through transitions, and is still found by `assignee=<agent>` | Observable: assign, resolve, `GET /tickets?assignee=dana` still lists it | Why: not stated by any clause; tests do not assert it.
- Reassigning dana → omar → dana before delivery leaves only one pending notification for dana (outbox key per agent) | Observable: `GET /admin/outbox` | Why: plan note; the spec does not say whether the second dana assignment must notify again; not tested.
- Outbox events survive a restart with `DATA_FILE`, which is how the tests observe "pending, then delivered by the worker" without a clock hook | Observable: stop and restart with the same DATA_FILE and a worker interval | Why: needed to test C-11/C-12 black-box.
