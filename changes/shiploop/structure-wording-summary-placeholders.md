---
bump: minor
---
Every stage's result template now says what its `summary` is for, so a summary records what only that result holds
instead of restating the request, the spec or the files written.
- The generic placeholder reads `<decisions, defaults, open questions and owners only this result records; no
  restatement>`. Intake asks for one clause per request sentence, cited S<n>; plan, test-spec and verify carry what their
  duties used to list (the duty text moved into the template, printed once). ShipLoop refuses a summary still equal to a
  placeholder.
- Intake duty 1 covers each request sentence in one clause cited S<n> instead of copying it. Spec criteria give positive,
  failure and boundary lines only where each adds something, otherwise `n/a: <reason>`. Test-spec states a value every
  case shares once. A step's `task` cites IDs rather than their text; check commands are safe to repeat locally;
  scaffolding folds into the first step that uses it. Step-plan duty 9 opens with the record's status and covers only the
  topics the item touches. Test-strategy: the host's tool listing is the probe that a host tool exists, and IDs use
  characters legal in the runner's test names (`TC_1` where a hyphen is not). Prepare starts each runner in its no-op form,
  not the suite.
- `--delivery-contract` is added only when the request or the host asks for it.
