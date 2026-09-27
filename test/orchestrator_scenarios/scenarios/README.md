# Dispatcher scenarios (T1)

One JSON file per scenario, run by `test/plan-dispatcher-scenarios.test.js`
through `../harness.js`, each twice: normally and with the driver discarding
every response (context loss after every call). Both runs must end the same.

| Field | Meaning |
|---|---|
| `id`, `name` | Spec scenario ID (`C1`…) and a readable name |
| `graph` | `[[step, [deps...]], ...]` |
| `capacity` | Optional run capacity passed to `init` |
| `executor` | `native` (default) or `main-context` |
| `schedule` | Order the host finishes running tasks: `fifo` (default), `lifo`, or `{"seed": n}` |
| `outcomes` | Per step, the outcome of each attempt in order; the last repeats. `SUCCEEDED` (default), `FAILED`, `BLOCKED` (verified, retried), `BLOCKED:replan` (verified, replan), `FALSE_SUCCESS` (claims success, wrong value) |
| `faults` | `duplicate_report`, `stale_report`, `lose_launch_response`: lists of steps |
| `expect` | `{"complete": true}` or `{"complete": false, "replan": [...]}`, plus optional `accepted` and `min_refusals` |
