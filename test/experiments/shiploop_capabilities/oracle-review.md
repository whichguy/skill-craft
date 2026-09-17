# Capability experiment: independent oracle (`capability-oracle-r2`)

## Freeze record

This r2 follow-up oracle treats `fixtures/SPEC.md` as the authority. It was
revised after the completed study exposed a malformed-reference defect, while
keeping expected outcomes declared here rather than derived from a candidate
app, candidate tests, or a candidate's cached state. Historical study inputs
remain frozen at their recorded bytes.

The fixture is deliberately a small loopback Checkers RPC exercise.  These
checks do not claim to validate a complete game, a browser UI, an MCP server,
or any hosted Google Apps Script or Salesforce environment.

## Observable API assumed by the grader

Scored checks use a new loopback server and the public HTTP routes. The grader
may use the fixture's Store constructor only to bootstrap an isolated server
from specification-owned state. A separately reported direct-Store compatibility
diagnostic is unscored and cannot replace a public HTTP result.

The fixture adapter must make these public operations available to the grader:

```python
GET /api/state                              # JSON mapping: board, turn, version
POST /api/move + JSON request + Bearer token # JSON mapping and real HTTP status
```

The grader parses the actual status and JSON body; it must not translate an
incorrect outcome into a correct one. The grader starts a fresh public server
over the same workspace to observe persistence after errors and restarts.

## Frozen independent cases

All request maps contain `actor`, `from`, `to`, `expectedVersion`, and a
nonempty `idempotencyKey`.

| ID | Stimulus | Expected observation |
| --- | --- | --- |
| P1 | Red token: red `b2 -> c3`, version 1, key `r1` | 200; no replay; `c3` is red, `b2` empty, turn black, version 2. |
| P2 | Repeat P1 exactly | 200; replay true; version remains 2 and state is unchanged. |
| P3 | Black token: black `g7 -> f6`, version 2, key `b1` | 200; turn red; version 3. |
| A1 | Red token, body actor black, at black's turn | 403 `actor_mismatch`; state unchanged. |
| A2 | Known actor token with no configured write scope | 403; state unchanged. |
| V1 | After P1, black's legal move with expected version 1 | 409 `version_mismatch`; state unchanged. |
| V2 | P1 key reused with different request fields | 409 `idempotency_conflict`; state unchanged. |
| I1 | Red `b2 -> b3`, version 1 | 422; state unchanged. |
| I2 | Red `z9 -> a1`, version 1 | 400; state unchanged. |
| N1 | Red `z9 -> a1`, version 1, with no authorization header | 400 `invalid_coordinate`; request normalization precedes authorization and state is unchanged. |
| I3 | Red `b2 -> d2`, version 1 | 422; state unchanged. |
| C1 | Read a state, complete P1, then read again | The second read is version 2 and contains `c3`; it cannot return the primed version-1 state. |
| R1 | Complete P1; build a new Store over the same workspace | The new store observes P1's version-2 state. |
| J1 | JSON object with `actor` as an array or object | 400 `invalid_actor`; a fresh public reader observes unchanged persistence. |
| J2 | JSON list, string, or `null` as the entire request body | 400 `invalid_json`; a fresh public reader observes unchanged persistence. |

Each negative result must preserve the immediately preceding persistent state,
observed through a newly started public reader so a primed cache cannot mask a
write. The oracle records only the statuses and error names explicitly specified
above; it does not assign a category to an arbitrary process or transport
failure.
The oracle deliberately does not infer draw, game-over, remote-opponent,
matchmaking, spectator, or full-UI behavior.

### Retained calibration case

I3 retains the illegal-geometry calibration case. Both endpoints are
syntactically valid playable coordinates, but the move has illegal geometry, so
the result must be 422 and leave state unchanged. It does not replace I1 or I2.
It gives the declared illegal-geometry defect a relevant observable check;
`b2 -> b3` is rejected earlier as an unplayable square and therefore cannot
exercise that defect.

## Held-out grading

`INNER` is graded with the complete public HTTP set above against the final
candidate. A candidate that only passes its own worker tests does not pass this
oracle.

The oracle preflight must prove that the correct r2 reference passes every
applicable frozen case through loopback HTTP. It must also prove that selected
known defect variants fail their relevant cases: duplicate/P2, stale/V1,
cache/C1, wrong-actor/A1, and invalid-move/I3. This detects a vacuous oracle.
If a "correct" reference shares the implementation under evaluation, it is only a
calibration subject; the specification-derived cases remain the source of the
expected results.

### Calibration source and receipt requirements

Evidence-grade calibration requires exactly the five declared families supplied
as distinct source files outside the reference: actor impersonation, duplicate
idempotency, stale version, cache invalidation, and illegal geometry. The
grader rejects missing or unknown families, source-path aliases, duplicate source
hashes, and a mutant whose hash equals the reference. It records each actual
source kind and SHA-256 hash. Running the reference's runtime defect selector
without separately supplied sources remains an explicitly diagnostic exercise;
it is useful for local debugging but is never a passing evidence-grade
calibration.

Before execution, every score receipt binds the current public SPEC and
`fixture_setup.py` hashes plus the applicable reference or candidate hash,
mutant hashes, and worker test-tree hash. It records selected oracle checks,
expected and selected defect families, and whether the oracle workspace was
retained or cleaned as a temporary directory. In-process HTTP checks and worker
test subprocesses clear an inherited authoritative-receipt path unless that
individual grader run explicitly configures one.

## Test-expansion grading

For `TEST`, run the worker's `test*.py` suite unchanged once against the fixed
reference and once per independently selected defect variant.  The suite earns
credit only when it has zero false failures on the fixed reference and detects
distinct defect families. If the fixed reference fails, the result is explicitly
`invalid_reference`; mutant results are not scored. A setup failure, an import
error, or a test that depends on a grader-only path is neither a valid detection
nor a passing test.

The score records the detected family names separately from raw test count.
The five planned families are actor impersonation, duplicate idempotency,
stale version, cache invalidation, and illegal geometry. A full valid score
requires exactly those five independently supplied sources. A partial set is
reported as `incomplete_mutant_set`; unknown families, aliases, duplicate source
hashes, or reference-equal sources are reported as `invalid_mutant_set`. Neither
result runs arbitrary mutant variants or passes the worker suite.
