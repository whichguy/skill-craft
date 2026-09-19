# Compound Ask-Agent orchestration coverage

This increment starts from `f8d9c0d`. Its previous 93-suite qualification remains
evidence for that commit, not automatically for these changes. Baseline validation
before this increment passed all 10 lifecycle cases, 14 Git cases and 23
native-trace controls. Expanded-suite results are recorded separately below.

The useful next tests combine lifecycle boundaries rather than adding more
isolated happy paths:

| Scenario | Required invariant | Test layer |
| --- | --- | --- |
| A worktree is removed externally and recreated with the same path, branch and commit | An old cleanup request must preserve the replacement allocation, including when retiring a rejected worker | Real Git identity and cleanup |
| Serial execution is interrupted after Git creates its worktree but before adoption is recorded | A durable creation record must identify the pending workspace; recovery must reuse that clean allocation without an orphan or second execution grant | Composed allocation recovery |
| A is accepted but its worktree cannot yet be removed | C can consume A's archived output and integrated code; cleanup remains observable and cannot rerun A | Composed public lifecycle |
| A has a durable integration intent when its parent is interrupted | B cannot mutate the target until A is reconciled; B then needs fresh preparation and checks against the advanced target | Composed public lifecycle |
| Two individually valid changes combine incorrectly | Failed combined verification preserves the current target and blocks dependents; a replacement attempt can recover, while old-attempt work remains fenced | Composed code-producing lifecycle |
| Completion arrives before the parent records the launch handle | Preserve the early result, but refuse integration until the dispatcher has a recorded execution identity | Composed public lifecycle |
| Dispatcher ownership changes before a prepared worker completes | The previous dispatcher binding cannot mutate Git or settle the attempt | Composed public lifecycle |
| One worker has both successful and failed terminal collection records | The observer cannot choose the convenient success and ignore contradictory terminal evidence | Synthetic typed host trace |
| A recorded exit status is JSON `false` | It must not pass an integer exit-code-zero check | Synthetic typed host trace |
| B's native handle record points to A's handle source | Each step must retain its own exact handle-file identity | Native trace manifest |

The worktree-recreation and trace cases reproduced false acceptance on the
baseline. A rejected attempt also remained preparable after retry, appending new
preparation events for obsolete work. Tests must show those failures before the
repair and passing behavior afterward. Include positive controls for normal cleanup, legitimate pending
observations, and repeated identical completion collection so stricter admission
does not reject supported recovery.

The recreation oracle must show that the filesystem instance actually changed
while Git path/branch/commit values stayed the same, and that rejected cleanup
leaves the replacement registered. Interrupted integration must distinguish
inert replay of A's accepted completion from rejection of B's stale candidate.
Trace contradictions must fail in either order; pending then success and repeated
equivalent successful completion must remain valid.
Changing an already rejected completion to a positive result must fail before
integration even while that rejected attempt is still the current one. Checking
only that an attempt has not yet been retried is insufficient.

Bind each new parallel or serial workspace's filesystem instance when it is
adopted or allocated, before dispatch. Cleanup must compare the recorded root and
private Git-directory identities as well as Git identity. Old per-step records
without an instance binding must retain their worktrees for explicit
reconciliation rather than silently binding whichever directory exists during
cleanup. Legacy final-return runs keep their original lifecycle. This is a local
cooperative filesystem check, not a security guarantee against hostile mutation
or filesystem inode reuse.

The increment adds 15 regression cases: five lifecycle cases, two Git cases and
eight trace controls. All 117 selected tests passed:

| Check | Passed | Execution |
| --- | ---: | --- |
| Composed lifecycle | 15 | Full 14-case run, then the new prepared-before-takeover case separately |
| Real Git identity/integration/cleanup | 16 | Full focused suite |
| Native trace observer | 31 | Full focused suite, including an independent rerun |
| Existing chain compatibility | 33 | Full focused suite |
| Handoff/archive validation | 16 | Full focused suite |
| No-model-launch boundary | 6 | Full focused suite |

The final lifecycle test edit moved post-finish ownership assertions into the
separate pre-integration takeover case. Production stayed frozen across the
14-case run (455.571 seconds), the new case (8.267 seconds), and compatibility
checks. Independent targeted review found no remaining production must-fix;
plugin synchronization and diff checks passed. The full 93-suite inventory and
23-group packaging gate were not repeated for this increment.

Local logs and the production digest record are retained under
`/private/tmp/shiploop-chain-compound-20260919.y5bzxn`.

Run the existing suites directly; the full ShipLoop inventory already includes
them, so this increment must not duplicate suite registration:

```sh
python3 -B test/shiploop-chain-lifecycle.test.py
python3 -B test/shiploop-chain-git.test.py
python3 -B test/experiments/shiploop_chain/test_trace.py
python3 -B test/shiploop-chain.test.py
python3 -B test/shiploop-chain-handoff.test.py
python3 -B test/shiploop-no-model-launch.test.py
```

Use real Git repositories and explicitly synchronized deterministic worker
processes for local interleavings. Assert target/branch identity, committed code,
archive bytes, one acceptance, reservation/recovery state and worktree survival
or removal. Prose can vary; safety-relevant identities and state transitions
cannot. Synthetic trace controls test the observer, not native delivery.

## Separate live qualification

The highest-priority remaining live case is actual prompt-driven Ask-Agent
worktree preparation followed by bridge adoption, overlapping workers, verified
per-step return and cleanup. The current native pilot fixture creates worktrees
itself and cannot establish that first property.

Additional live cases should cover parent recovery after launch but before the
handle is persisted, and nested delegates or commands still active when a worker
returns. Require actual host lookup, collection and stoppage evidence; do not
invent a child-inventory schema or infer stoppage from a report file. Native
completion timing before the parent's launch-record call can be legitimate and
must not itself be classified as failure.

Shared MCP/database/deployment targets need a separate resource-contention test
with a harmless disposable backend: worktree isolation alone cannot establish
remote isolation. The current clean-target prerequisite should remain explicit;
generic Ask-Agent dirty-snapshot behavior is not a supported chain feature.

No live host is retried by this test increment. The prior Grok cancellation
clarification and native qualification remain unresolved.
