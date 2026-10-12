# Coordinator contract

In Parallel uses the internal Agent Harness adapter to compose the selected Ask
Agent compact task interface with the selected Plan Dispatcher. Its scripts do
not start agents. Only the coordinator uses them to initialize and advance the recorded run; the host launches workers
and supplies their actual terminal results.

## Bind the run

For Python composition, see the [script API contract](script-api.md). The CLI
and callable coordinator entry point share validation and mutation locking.

Use Python 3, Node.js for the selected Plan Dispatcher, and an existing Git
checkout. This implementation supports Git sources only. Select the actual
absolute cards loaded by the current host. The run directory must be a new
absolute path outside the source checkout and all three selected skill package
roots. Keep request, result, and verification files in a retained location
outside those protected trees.

The request option is a path to a regular JSON object file. It is not inline
JSON. `init` also pins the selected package contents and creates a new run; it
does not resume or adopt another workflow's state.

`init` is new-run-only: it cannot take over an existing run or rewrite its
selected package pins. If setup is interrupted before Dispatcher initialization,
inspect the retained partial setup, then initialize into a different new run
directory. Do not treat partial setup as a resumable run.

```sh
python3 /selected/in-parallel/scripts/harness.py init \
  --run /absolute/external/new-run \
  --request /absolute/external/request.json \
  --ask-agent-card /selected/ask-agent/SKILL.md \
  --dispatcher-card /selected/plan-dispatcher/SKILL.md
```

The request object has these fields:

| Field | Contract |
| --- | --- |
| `objective` | Nonempty goal for the whole batch. |
| `source` | Absolute path to an existing Git checkout. |
| `workspace` | Required `current` or `worktree`, chosen from the user's request and Ask Agent's route. |
| `mode` | Required `edit`, `report-only`, or `ephemeral`. Ephemeral requires a worktree. |
| `tasks` | Required nonempty list of independent tasks, each with unique `id`, nonempty `objective`, frozen nonempty `expected_result`, and `write_set`. |
| `capacity` | Optional positive integer limiting concurrent worker reservations, defaulting to `min(5, task count)`. It does not limit total tasks or lifetime worker contexts; unconfirmed launches consume capacity. Current-workspace edit is forced to capacity one; a warning is recorded when the requested value differs. |
| `integration` | Optional `apply` or `return-only`, default `apply`. Current-workspace edit requires `apply`. |
| `checks` | Optional list of nonempty argv arrays; required for edit with `integration: apply`. Checks run in the source checkout without shell evaluation. |
| `writers_quiescent` | Must be `true` when preparing a worktree snapshot. This is a coordinator attestation, not a lock. |
| `exclusive_writer` | Must be `true` for current-workspace edit. This is an attestation that the coordinator excludes other writers. |
| `current_learnings` | Optional string with relevant current findings; it carries context, not authority. |
| `authorization` | Optional string recording applicable authorization already present; it cannot create new authority. |

Each task has exactly the fields `id`, `objective`, `expected_result`, and
`write_set`. Use unique IDs and disjoint, repository-relative exact file paths
or directory prefixes; globs and traversal are rejected. `report-only` requires
an empty write set. Edit and ephemeral tasks require a nonempty write set. A
dependent graph is outside this adapter: do not convert dependencies into a
parallel batch.

## Follow the recorded lifecycle

The adapter calls the selected Dispatcher and prepares each eligible Ask Agent
compact packet. The run graph records
`source.agent_harness: {"schema":"agent-harness/v1","ask_agent_interface":"compact"}`.
Treat the returned assignments and exact task scopes as binding. For a
worktree, all workers are prepared from the same captured source snapshot; the
snapshot includes the parent's staged and unstaged changes and repository-root
`.gitignore` and `.claspignore`. A worktree edit defaults to Ask Agent commit
delivery. The parent is never committed automatically. Separate worktrees
separate files, but are not operating-system sandboxes.

The lifecycle is:

1. `dispatch --run ABS` claims and prepares tasks and returns compact native
   assignments. Start each returned assignment once through the live native
   host interface. When multiple independent assignments are ready, use the
   host's asynchronous launch behavior and launch the batch before waiting
   for results. Record the effective native launch state; do not invent a
   background flag that the live schema does not expose. The coordinator,
   not the helper, starts the worker.
2. After each native launch returns, record its actual host handle with
   `launched --run ABS --attempt ID --handle NATIVE_ID`. A task label is not a
   handle. If launch success is uncertain, inspect the host's actual native
   inventory; do not launch again based on elapsed time, a notification, or a
   saved file.
3. After the host confirms terminal completion and the coordinator has the
   actual result, save a result JSON file and call
   `collect --run ABS --attempt ID --result RESULT.json`. The file must attest
   `native_terminal: true` and the matching `native_handle`. It must include
   `status` (`SUCCEEDED`, `BLOCKED`, or `FAILED`), a meaningful `summary`, and
   one `criteria` entry for each frozen expected-result string. Each criterion
   records that exact `criterion`, a concrete `check`, what was `observed`, and
   a `level` of `confirmed`, `inspected`, `failed`, `not_run`, or
   `unconfirmable`. Optional result `evidence` entries are `{path, sha256}`
   pairs for absolute regular files whose bytes match the hash. The native
   lifecycle fields are coordinator attestations; the script does not
   authenticate the host.
4. Independently inspect or rerun the expected-result checks. Save a separate
   verification JSON object with boolean `passed`, a substantive `reason`, and
   a nonempty `evidence` list of absolute regular `{path, sha256}` files. Then
   call `accept --run ABS --attempt ID --verification VERIFICATION.json`.
   Acceptance is distinct from collection; a passing acceptance requires a
   successful worker result and every criterion confirmed or inspected.
5. Refill the queue: after accepting or rejecting a collected terminal result,
   call `dispatch --run ABS` again. It returns only newly granted assignments
   within capacity; each needs a fresh native worker. Continue until every
   required task is accepted. `NO_NEW_LAUNCH` is not completion: inspect
   `status` for active, pending, verification, and retry actions, and reconcile
   uncertain native launches without duplicating them. Failure or rejection
   does not remove that task from the required set.
6. Call `finish --run ABS` only when the Dispatcher reports every required
   worker accepted and no active reservation. It records the final delivery
   outcome. Edit/apply validates and delivers accepted worker changes while
   preserving the source HEAD and index, then runs the required combined
   checks. A failed integration or check remains a failure with retained
   evidence; do not report whole-run success. After a successful worktree
   edit/apply delivery is saved and combined checks pass, close each integrated
   worktree using the selected Ask Agent helper. Cleanup follows combined
   delivery, not the worker's return or task acceptance alone.

All commands except `init` require the same absolute run directory:

```sh
python3 /selected/in-parallel/scripts/harness.py dispatch --run /absolute/external/new-run
python3 /selected/in-parallel/scripts/harness.py launched --run /absolute/external/new-run --attempt ATTEMPT --handle NATIVE_ID
python3 /selected/in-parallel/scripts/harness.py collect --run /absolute/external/new-run --attempt ATTEMPT --result /absolute/external/result.json
python3 /selected/in-parallel/scripts/harness.py accept --run /absolute/external/new-run --attempt ATTEMPT --verification /absolute/external/verification.json
python3 /selected/in-parallel/scripts/harness.py retry --run /absolute/external/new-run --attempt ATTEMPT --reason "What changed after reviewing the rejected result" --confirmed-stopped
python3 /selected/in-parallel/scripts/harness.py finish --run /absolute/external/new-run
python3 /selected/in-parallel/scripts/harness.py status --run /absolute/external/new-run
```

### Interrupted operations and rejected attempts

Resume an interrupted operation with the same saved input artifacts. `dispatch`
reuses a saved prepared task if Dispatcher start was interrupted; if preparation
stopped before that artifact was saved, leave the attempt blocked for inspection
instead of preparing it again. `collect` can finish publishing the same saved
result after an interruption, but refuses a duplicate after the result was
already reported. `accept` reuses an identical saved verification proof if
settlement was interrupted. `finish` reuses its immutable delivery result after
an interrupted aggregate write and never applies the delivery a second time.

Use `retry` only for a collected, known-terminal attempt rejected by
verification when Dispatcher exposes its retry action. `--confirmed-stopped`
is the coordinator's confirmation of actual native stop; it does not discover
or prove stop state. The reason must say what changed after reviewing the
rejected work. An unknown or still-running launch is never retryable. A
current-workspace edit also cannot retry in place: inspect the edits already
made, then initialize a fresh run only after reviewing the remaining work and
the new baseline.

`status` is a read-only view of recorded Dispatcher progress, actions, and
delivery outcome. It does not query whether a native worker is still
running, stopped, or complete. Do not use it to restart a worker, adopt an
existing Plan Dispatcher or ShipLoop run, or infer native freshness. If the
host result or stop state is unknown, reconcile it through native host tools
and retain the uncertainty until resolved. If the wrapper cannot express the
required next Dispatcher action, stop and report the evidence; do not bypass
this adapter with a guessed direct mutation.

Unexpected tracked or nonignored files or changes created by host hooks are
scope violations too. Ordinary ignored caches remain governed by Ask Agent's
existing ignore rules; do not broaden ignores to hide a failed return.
Do not delete or hide those files after a worker returns to make verification
pass. Retain the rejected attempt and identify the exact writer from evidence.
Retry only after the cause has been corrected within the authorized setup; a
second launch with the same active writer does not fix the failure. Do not
silently disable user hooks or change persistent host configuration.

### Cleanup after integration

For worktree edit/apply, `finish` uses the saved successful delivery, native
terminal attestations and accepted inspection fingerprints to call the selected
Ask Agent `close` helper. All workers and any delegates must have stopped.
Preserve referenced evidence outside the removable worktree first. Each close
rechecks the worker state and removes only its receipt-bound worktree. Branches,
commits, contribution patches and run evidence remain recoverable.

Read each cleanup status: exit zero alone does not establish removal. A refused
close reports `CLEANUP_PENDING` and exits 2, with `delivery_success: true`
preserving the successful integration result and per-worker cleanup evidence.
Integration is not rolled back or repeated. An interrupted finish reuses its
saved delivery and the helper's existing close outcome instead of applying code
again. Do not delete a worktree directly to bypass a cleanup guard.

Failed or unmerged contributions and edit/return-only worktrees stay intact.
Report-only and ephemeral runs have no integration event and are not covered
by automatic post-integration cleanup. Ephemeral work permits scoped scratch
changes and returns findings only. Current and consumer-owned workspaces are
never removed by this cleanup path. Historical pinned runs retain their
original policy; this change is not an instruction to sweep old worktrees.

## Existing pinned runs

The public skill is `in-parallel`; internal `agent-harness/v1` run and delivery
schemas and the Dispatcher `source.agent_harness` profile remain unchanged.
This naming consolidation does not migrate a saved run. A run pins absolute
package paths and file hashes: use its original retained packages and inspect
its evidence, rather than redirecting it to the new skill or rewriting its pins.
