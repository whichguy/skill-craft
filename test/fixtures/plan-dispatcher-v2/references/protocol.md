# Dispatcher CLI contract

Bind HELPER to the selected installed skill's absolute `scripts/dispatch.js`.
Pass JSON files, not shell-evaluated plan text:

```sh
node /absolute/skill/scripts/dispatch.js init /absolute/run init.json
node /absolute/skill/scripts/dispatch.js next /absolute/run
node /absolute/skill/scripts/dispatch.js claim /absolute/run claim.json
node /absolute/skill/scripts/dispatch.js start /absolute/run start.json
```

All successful operations emit JSON. Failure emits JSON on stderr and nonzero
exit; `ELOCKED` means another writer or an orphan lock, not permission to relaunch.
The internal state.js CLI exists for regression tests, not as a substitute for
this contract. Keep the package code fixed for a run; no schema-upgrade mechanism.

## Graph

An init request has `{owner, graph}`. Owner is a unique nonempty dispatcher ID.
Graph is `{version:1, steps:[...]}` with optional JSON `source` provenance:

```json
{
  "version": 1,
  "steps": [
    {"id":"B","deps":[],"contract":{"task":"Sum is implemented","ready":["Isolated repo and checks available"],"done":["Empty, positive and negative cases pass"]}},
    {"id":"C","deps":[],"contract":{"task":"Double is implemented","ready":["Isolated repo and checks available"],"done":["Zero, positive and negative cases pass"]}},
    {"id":"D","deps":["B","C"],"contract":{"task":"Both changes are integrated","ready":["Accepted B and C commits available"],"done":["Both commits are ancestors; combined checks pass; worktree clean"]}}
  ]
}
```

All steps are required; there are no optional/conditional nodes. IDs and dependency
references must be unique/valid, the graph nonempty and acyclic. ready may be empty;
task and done must be nonempty. Initial-world facts in ready require actual checks,
not just a declaration in the plan. Contracts and provenance are frozen with the
dependency graph. Plan changes require a new run after reconciling existing work.

From a Backchain checkout, `node harness/dispatcher-plan.js PLAN.json` emits the
graph without executing it. Export requires structural validity, exact
`completionStatus=complete` including goal_needs closure, and compatibility with
the execution graph validator. Reserved object-key IDs and whitespace-only
contracts fail at export rather than yielding a graph that init cannot use.
It maps `statement` to
task, direct non-null input suppliers to deps, input needs to ready, and produces
to done. This gate is structural; it does not prove semantic sufficiency or replace
readiness/acceptance evidence. Do not resolve the exporter relative to this package.
Exact repeated ready/done wording is listed once; distinct supplier dependencies
and every original input binding remain intact, even when their wording matches.
Generic graph provenance remains arbitrary JSON. A packet exposes input_bindings
only from an own array at source.inputs[step.id]; absent or non-array provenance
produces an empty list. Inherited object properties are never input bindings.

## Commands and inputs

| Operation | INPUT.json fields | Effect |
| --- | --- | --- |
| init | `{graph,owner}` | Exclusively create a new run; return next actions |
| next | No file | Read ready IDs, active attempts, accepted IDs and recovery actions |
| claim | `{owner,steps:["B","C"]}` | Reserve precisely these ready IDs atomically; return preparation packets |
| start | `{owner,attempt,context,executor?}` | Native path persists launch intent and returns launch; `main-context` executor atomically enters serial work and returns execute; exact replay reconciles |
| launched | `{owner,attempt,handle}` | Save actual nonempty native handle returned by the host |
| packet | `{attempt}` | Read frozen task/context and supplier evidence; never authorize another launch |
| report | Envelope below | Publish one immutable inbox receipt; state.json unchanged |
| receipt | `{attempt}` | Return the envelope and digest of its stored bytes |
| settle | `{owner,attempt,verification}` | Record independent accepted/rejected decision and return next actions |
| retry | `{owner,attempt,confirmed_stopped:true,reason}` | Retire nonaccepted attempt; next claim gets a fresh token |
| takeover | `{oldOwner,newOwner,confirmed_stopped:true,reason}` | Fence old dispatcher owner, retain workers/receipts |

Context is exactly:

```json
{
  "workspace": "/absolute/separate-worktree",
  "write_scope": ["src/sum.cjs"],
  "resources": ["database:isolated-fixture-1"],
  "ready_evidence": {"path":"/absolute/readiness-B.json","sha256":"64 hex digits"}
}
```

The workspace must exist and be disjoint from RUN and other active workspaces.
write_scope uses relative paths without `..`, absolute paths or a whole-workspace
`.` entry. It is cooperative scope, not filesystem access control. Use the same
resource key for any shared writable external target; undeclared conflicts cannot
be detected. Starting work atomically reserves workspace/resource identity.
Resources remain reserved while launching/running/rejected, and are released by
accepted settlement or confirmed-stopped retry. Preparing/claiming alone does not
reserve resources. Restrict claim count using actual available host capacity.

`executor`, when supplied to `start`, is exactly
`{"kind":"main-context","id":"nonempty stable caller identity"}`. It is a
durable per-attempt identity for explicitly serial main-context work, not a native
handle or completion claim. Its first start atomically records `running` with
`handle:null` and returns `action:"execute"`; the native path still starts with
`action:"launch"` and records its actual handle through `launched`. An attempt
has one execution identity: a native handle and executor cannot coexist. A changed
executor, serial start after native launch, or `launched` after serial entry fails
without changing state. The caller, such as ShipLoop, enforces serial capacity one;
the helper does not introduce another scheduler. The executor ID is a durable
caller attestation, not a host-authenticated conversation capability; after
recovery or takeover, the current dispatcher must explicitly attest it may resume.

Readiness evidence should record each checked condition and its observed basis.
The helper checks the bytes and binding; the dispatcher judges the facts. Preserve
immutable artifacts outside writable worker scopes. Returned packets carry direct
suppliers' result/verifier artifacts, contracts, identity, context and report call.
Read and hash-check supplier evidence, then prepare the right base commit in the
assigned worktree; the helper does not check out commits for you.

For Git tasks, the dispatcher must allocate sibling linked worktrees in an
external container outside all checkouts and Git metadata. Before creation,
canonicalize the candidate and every registered worktree root; reject equality
or containment in either direction, symlink redirection and foreign enclosing
repositories. Record the exact initiating checkout, branch and base as the return
target, even when it is a linked worktree; do not substitute `main` or the primary
checkout. These are caller-owned Git requirements, beyond the helper's existing
directory/resource overlap checks; automatic Git allocation and return enforcement
remain unimplemented.

Worker envelope:

```json
{"run_id":"run_...","step":"B","attempt":"attempt_...","status":"SUCCEEDED","evidence":{"path":"/absolute/result-B.json","sha256":"64 hex digits"}}
```

Status is SUCCEEDED, FAILED or BLOCKED. Result artifact records actual output,
commit/workspace identity where applicable, checks and exit codes, and limitations.
Native workers return both the envelope and artifact paths through native completion,
including if inbox publication failed. A main-context task writes the same result
and envelope itself; the parent may retry the exact report in either path.
The packet assigns concrete output files under `RUN/artifacts/ATTEMPT/` and
creates that directory at start. Workers may write only their own `result.json`
and `envelope.json` there; canonical state and other attempts remain dispatcher
owned. Write the result, compute its hash, and fill the actual status/digest in
`report_envelope`; its evidence path and identity are already concrete. Execute
the returned `report_argv`. The public helper rejects a different evidence path,
and its CLI rejects a different envelope input path. Packet recovery deterministically
returns the same output paths. Output-directory setup happens before launch intent;
a setup failure leaves the claim unlaunched and startable.

Parent verification (inside the settle request):

```json
{"receipt_sha256":"digest returned by receipt","passed":true,"reason":"Independent contract checks passed","evidence":{"path":"/absolute/verification-B.json","sha256":"64 hex digits"}}
```

Verifier evidence should include exact result/commit identity and independently
observed checks, plus the appropriate completion/stoppage observation. Before
settlement, native execution requires collecting the native task and confirming it
stopped; accepted settlement releases its workspace/resources. For a main-context
executor, `confirmed_stopped` means all task-owned commands finished, not that the
main conversation terminated. A receipt or saved identity alone does not establish
this. Independent verification is a separate checking phase with actual tests or
inspections; it need not run in a separate agent. This is a dispatcher precondition;
the helper cannot inspect native liveness or conversation state.
Only SUCCEEDED plus passed=true is accepted. Other combinations
reject and keep descendants blocked. Hashes do not establish test success. A fast
worker may report before the native handle is saved; settlement waits for that
handle without discarding the receipt. Exact report/settlement replay is inert;
changed/stale/cross-run records fail.

## Completion-driven dispatch

The main conversation handles each native completion notification or collected
result. Bind it to the current run/step/attempt and saved native handle; confirm
the worker stopped, collect/publish its exact receipt, independently verify its
done contract, and settle it. For an entered main-context attempt, `next` returns
`resume` before a report and `verify` after one: resume or check in the current
conversation without spawning, native collection, or native waiting. Because the
executor is an attestation, the current dispatcher confirms it is appropriate to
resume after recovery or takeover. A report alone never unlocks successors. Process
completion events through the sole dispatcher; workers do not select or launch
successors. No polling service or automatic cross-session callback is implied.

The public `settle` response already includes refreshed `ready`, `active`,
`accepted`, `complete`, and action data. `ready` is the full set of pending steps
whose direct dependencies are all accepted, not just the successors newly
unlocked by this event. Check actual readiness, external resource availability
and remaining native capacity, then claim the eligible subset and launch through
the ordinary start/launched protocol. The `claim` action's `steps` lists candidates;
construct a request containing only the selected subset rather than executing the
action unchanged. The helper has no host-capacity input or global slot enforcement.
Leave excess ready steps unclaimed. Include
claimed, launching and unresolved native work when accounting for capacity.

For `A -> B,C`, `B -> D,E`, and `C,D,E -> J`: accepting A offers B and C. Accepting
B can offer both D and E while C continues. If only one slot is free, launch D
and leave E ready. After D finishes, E remains offered even though it was unlocked
by the earlier B completion. J stays pending until C, D and E are all accepted.
There is no whole-wave barrier. Exact settlement replay cannot reoffer a claimed
or accepted node; claims still validate the selected IDs against current state.

Refresh on initialization/resume and after a confirmed-stopped retry too. Native
capacity or resource availability changes can justify another `next` without a
new graph acceptance. This is an event-driven caller decision, not a reason to
create scheduler timers or polling. A supported current-session status wakeup
may report observed pending work under Ask-Agent's waiting guidance; it does not
establish completion or unlock a step. Before waiting-only, select native timed
collection, equivalent visible native progress or a supported status wakeup;
respect the selected Ask-Agent guidance and user cadence/quiet preference. A
timed observation returns control for a visible combined status update, without
ending the worker. If periodic status is unavailable, disclose it before idle
and continue native completion collection. A rejected result blocks its descendants while other
independent ready work can continue. Retrying that task is a separate explicit
operation with a fresh attempt; dispatching its successors is not a retry.

When no step can launch, collect active native tasks if their results are needed;
otherwise report the concrete dependency, readiness, resource or recovery blocker.
An empty ready set does not establish completion: require `complete: true` and
the agreed integration/verification evidence. If a claim fails because the view
changed, rehydrate instead of launching from the stale action packet.

## Recovery and limits

`next` with no completed IDs is also the initial “where do I start?” command.
If a claim response is lost, use the saved active claim; do not claim it again.
If a native start response is lost, the saved intent is uncertain even if no launch
actually happened. Find the existing native task by full dispatch identity if
possible. Zero or multiple matches are not proof of safe relaunch. An entered
main-context start is already durably running and rehydrates as resume/verify, not
native reconciliation. Require actual native stopped/non-launch evidence before
retry; `confirmed_stopped` is only the caller's attestation, not a cancellation
mechanism. Handle retrieval after parent session loss depends on the host and has
not been established by local tests.

Lock acquisition fails immediately. Retry an identical receipt after the current
writer finishes, or return it for parent collection. Never clear a lock based on
elapsed time. After a process crash, first establish all old writers are stopped;
only then may an operator remove that run's known orphan `.dispatcher.lock`.
The helper intentionally has no automatic lock-clear command. Do not delete a run
as a recovery shortcut for possibly launched work.

State snapshots use atomic rename; inbox publication is immutable. Hydration
checks graph/state identity and accepted evidence. Keep original evidence bytes
available. Corruption/drift stops dispatch and requires investigation, not manually
editing a result to accepted. Interrupted init can leave an incomplete directory:
retain it, confirm no initializer is running, and use a different unused run path.

Scope: trusted local filesystem and one main dispatcher. Process-crash tests do
not establish power-loss or network-filesystem durability. Tokens fence stale
updates, not a worker's file writes. No malicious-process sandbox, automatic
service, model launcher, exactly-once effects or cross-session callback promise.
