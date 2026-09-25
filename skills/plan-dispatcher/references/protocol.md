# Dispatcher CLI contract

Bind HELPER to the selected installed skill's absolute `scripts/dispatch.js`.
Pass JSON files, not shell-evaluated plan text:

```sh
node /absolute/skill/scripts/dispatch.js capabilities
node /absolute/skill/scripts/dispatch.js init /absolute/run init.json
node /absolute/skill/scripts/dispatch.js next /absolute/run
node /absolute/skill/scripts/dispatch.js claim /absolute/run claim.json
node /absolute/skill/scripts/dispatch.js start /absolute/run start.json
node /absolute/skill/scripts/dispatch.js check-context /absolute/run context-check.json
```

All successful operations emit JSON. Failure emits JSON on stderr and nonzero
exit; `ELOCKED` means another writer or an orphan lock, not permission to relaunch.
The internal state.js CLI exists for regression tests, not as a substitute for
this contract. Keep the package code fixed for a run; no schema-upgrade mechanism.
Every successful RUN-scoped response includes an `instruction`; a `next` response
also includes the authoritative current `actions`. For a dispatcher-scoped
response, the dispatcher executes its instruction, then its exact `next_argv`,
instead of deriving graph navigation from this reference or the graph itself. A
task-facing `report` response ends the bounded task phase and is returned to the
dispatcher, which then uses its exact `next_argv` for the next phase. This
reference defines fields, boundaries, and recovery semantics; it is not another
scheduler.
`capabilities` is package discovery rather than a RUN operation.

For a fresh native launch, the parent passes the complete returned worker packet
unchanged beside a compact Current learnings block with a Markdown heading and
short labeled bullets from the current conversation, stating explicitly when none
are relevant. It retains the effective assignment and
launch identity in the existing parent record or retained handoff, durably outside
the worker workspace. Where the host supports it, the fresh native context has no
inherited history. Launch, status, collection, and
waiting instructions are parent-only; the already-started worker receives its
bounded task role, scope-authorized facilities, checks, handoff and exact report
return ownership.

## Categorical progress

The parent obtains fresh status with the returned exact `next_argv`, which calls
`dispatch.js next RUN`, at its normal continuation boundary after the current
instruction. `next` returns `progress` along with the existing `actions`. Parent
responses from `init`, `claim`, `start`, `launched`, `settle`, `retry` and `takeover`
also include `progress`, so launch notices can use script facts directly.
`report` and `receipt` retain their bounded receipt shape. A worker hands its
report response and `next_argv` back; only the parent performs the refresh.

Internally, `state.inspect(RUN)` uses `snapshotFromState` and its single
`progressFromState` projection. It classifies the validated state, the same
current receipt observations used by the active-attempt snapshot, and applicable
planning-context issues. The projection is read-only and is not persisted as a
second state authority.

Every required graph task appears exactly once, in graph order within its group:

| Group | Script criterion |
| --- | --- |
| `completed` | The current task is accepted by settlement |
| `active` | Claimed, launching or running, without a current report or a start-blocking planning issue |
| `awaiting_verification` | A matching current report is published; acceptance and any required native confirmation remain outstanding |
| `pending` | Unstarted work, including dependency-ready tasks and tasks awaiting dependency acceptance |
| `blocked` | A dependency is rejected/blocked, or required planning material prevents unstarted/claimed work from starting |
| `failed` | The current attempt was rejected by settlement; its reservation can still require reconciliation and retry |

Each row includes `step`, the graph's `task` description, observed `state`, a
`reason`, and `unmet_dependencies`. Current attempts include `attempt`.
`awaiting_verification` includes the worker's `reported_status`, which is a claim,
not proof of completion. `pending` includes `dependency_ready`; that boolean
checks dependency acceptance only, not host capacity, resource safety or external
readiness. Blocked dependency rows identify `blocked_dependencies`. Applicable
planning issues appear in `planning_issues`, filtered by each issue's
`required_for` scope. The internal contract-free state primitive uses a null
task description; the public facade requires graph task contracts.

`counts` provides all six group lengths, `total`, and `remaining`. The sum of
group lengths equals `total`; `remaining` equals `total - completed` and includes
active, awaiting-verification, pending, blocked and failed work. Whole-run
`complete` continues to mean that every required task is accepted. Disconnected
tasks count too. A retry removes the obsolete rejected attempt from the current
projection but preserves its durable evidence.

Planning-input loss does not imply a worker stopped: running and returned work
stays active/awaiting verification with the relevant issues attached. Previously
accepted work stays completed. Native liveness, host capacity and unrecorded
external blockers are not inferred. The parent may supplement the script facts
with explicit native observations, identifying them as such. Never cache this
projection by state revision alone: a new inbox receipt can change it without
changing the durable snapshot revision.

The counts and `complete` refer to this dispatcher graph. A containing workflow
can still have work after the graph is accepted; its owner determines completion.

Use `progress` for truthful status, and `actions` for execution. The reporting LM
chooses natural wording and useful formatting; it must not reclassify these
tasks, invent omitted work, or treat a group as authorization to run it.

## User-facing status presentation

The parent dispatcher owns user-facing status; workers return bounded task
handoffs and exact report responses instead of overall-run updates. At every
native-agent boundary, publish a meaningful, evidence-grounded Markdown update.
Choose the structure and detail that fit the event; do not follow a fixed template
or mechanically dump packet fields. Explain what happened, what has been
accomplished, and the immediate next work or remaining condition, with significant
findings, blockers, or required user action. For each affected task, give a
natural account of its assignment, accepted or completed work, and any active,
pending, or blocked condition that determines the next work; choose useful
wording and layout rather than mechanically copying field names.

Before a native call, identify the task assignment and call the update launch
intent until the host confirms it. On a native return, identify the reported
outcome and say it is not acceptance. Distinguish launch intent, a worker-reported
result, a verified outcome, and whole-run completion; only call a run complete
when the script reports it, and only describe task work as accepted or completed
after parent acceptance. Do not invent unreported work, future steps, percentages,
or an ETA. Preserve meaningful task assignments, pending dependencies, and any
gap between a worker result and parent acceptance. Keep protocol IDs and callbacks
internal unless they explain a problem. The parent incorporates worker results
without duplicate overall updates, and presentation never changes control flow:
continue only the current authorized action or honor the returned stop or handoff.
A worker report or handoff returns control to the parent; it does not end the run.
If a dispatcher-scoped response stops, describe prerequisites for future work
without starting a wait or retry.

Cadence, native UI, or notification does not replace either required boundary
update. Required launch/return notices and exact internal handoffs remain exact.

## Ask-Agent compatibility and managed Git preflight

Every Ask-Agent delegation selects a compatible package before execution. Bind
the selected absolute card and helper, then run:

```sh
python3 /absolute/ask-agent/scripts/ask_agent_workspace.py capabilities \
  --skill-card /absolute/ask-agent/SKILL.md
```

Accept only a declared JSON capability response with this schema and the full
current capability set (all five names):

```json
{
  "schema": "shiploop-chain-ask-agent-managed-worktree/v1",
  "version": "verified selected card version",
  "capabilities": [
    "helper-managed-worktree",
    "prepared-inspection",
    "returned-commit-delivery",
    "fingerprint-bound-close",
    "ignored-output-report"
  ]
}
```

The capability set is the gate, not a version number: `version` is recorded
with the declaration but no numeric floor applies. Do not treat a frontmatter
version, a version number, or prose in a skill card/reference as
compatibility. A missing schema or any missing capability blocks delegation. After this gate, use the existing
`identity --skill-card` contract unchanged and retain its selected-card/helper
identity with the same capability declaration. Every Git task workspace,
including an explicitly serial `main-context` task, must then be prepared by
the selected managed-worktree helper before the dispatcher freezes its generic
context. Do not adopt a caller-prepared worktree or allocate a serial Git
workspace as a fallback. Non-Git tasks use the same compatible selected package
but retain the ordinary four-field context contract without managed workspace
preparation.

## Run state authority

Each RUN has one mutable dispatcher snapshot, `plan-dispatcher-state.json`,
created by `init`. A RUN that contains the retired Plan Dispatcher 0.1.0
`state.json` is refused ("dispatcher run uses retired state.json (Plan
Dispatcher 0.1.0); not supported") before any read or write; start a new run
instead. A state file that is not a regular non-symlink file also fails; no
operation chooses, copies, links, renames, or mirrors a second state authority.
The separate `inbox/` directory contains immutable report receipts, not another mutable state.
Graph-only runs use state version 1. An init with `planning_context` creates
state version 2 and retains its immutable reference; v1 runs are never upgraded
or retrofitted with planning inputs.

## Graph

An init request has `{owner, graph, planning_context?}`. Owner is a unique
nonempty dispatcher ID.
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

From a Backchain checkout, `node scripts/export-execution-graph.js PLAN.json` emits the
graph without executing it. Export requires structural validity, exact
`completionStatus=complete` including goal_needs closure, and compatibility with
the execution graph validator. Reserved object-key IDs and whitespace-only
contracts fail at export rather than yielding a graph that init cannot use.
It maps `statement` to
task, direct non-null input suppliers to deps, input needs to ready, and produces
to done. A produce with a Backchain `confirm` entry carries its method in the done
string: `<produce>. Confirm by: <by>` for execution, the same plus
` (inspection is sufficient)` for inspection, or
`<produce>. Confirm by: unconfirmable here — <by>`. A produce without one is
exported unchanged. Workers treat every done item as an exit criterion and use
its `Confirm by:` method when present (see [exit criteria](#exit-criteria)). This gate is structural; it does not prove semantic sufficiency or replace
readiness/acceptance evidence. Do not resolve the exporter relative to this package.
Exact repeated ready/done wording is listed once; distinct supplier dependencies
and every original input binding remain intact, even when their wording matches.
Generic graph provenance remains arbitrary JSON. A packet exposes input_bindings
only from an own array at source.inputs[step.id]; absent or non-array provenance
produces an empty list. Inherited object properties are never input bindings.

## Immutable planning context

Before a caller creates a planning-context run, it queries the selected package:

```json
{"capabilities":{"planning_context":"shiploop-planning-artifacts/v1","graph_validation":"execution-graph/v1"}}
```

Before a caller persists an immutable graph binding, use
`node /absolute/dispatch.js validate-graph INPUT.json` with `{graph}`. This
read-only operation uses the same graph and required task/ready/done validation
as `init`, returning `{ok:true,graph_sha256}` for the canonical validated graph.
It takes no RUN, creates no state, and returns no `next_argv`. Invalid
dependencies, cycles, or contracts fail before the caller binds anything.
This does not validate planning-reference availability or authorize execution;
`init` still repeats validation and checks any supplied planning context.
Callers requiring preflight must check `graph_validation` on their selected
package. Existing bound runs can continue with their original package.

The optional init field is an immutable wire reference:

```json
{
  "path":"/absolute/run/chains/implement-1/planning-artifacts.json",
  "sha256":"64 lowercase hex digits",
  "source":{"run_id":"run-1","action_id":"implement-1"}
}
```

Its target must be a regular non-symlink JSON file with schema
`shiploop-planning-artifacts/v1`. The manifest identifies the same source
run/action, its immutable graph reference, a shared `briefing` reference, and
artifact entries with `required_for` set to `[]`, explicit graph IDs, or `["*"]`.
The briefing must also be a shared required artifact. Artifact metadata such as
roles, producers, references, origin, and source_reference is retained for the
worker as supporting planning reference material. It cannot alter graph
navigation, replace a step's task/ready/done contract, or carry a repackaged
original user prompt.

Before creating the run directory, init validates the wire-reference digest,
manifest source, frozen graph digest and canonical graph equality. The manifest
graph must be a versioned `{version:1,steps}` graph that passes the normal graph
validator; an unversioned `{steps}` graph is refused. Init also checks every required artifact and refuses required
unresolved or reference-only material. It performs no run-directory mutation on
failure.

Use the read-only context check before allocating a workspace, integrating a
target, or asking a worker to begin fresh work:

```json
{"step":"B"}
```

or:

```json
{"attempt":"attempt_..."}
```

It returns `ok`, `issues`, and `planning_context` without throwing for a missing
or drifted planning input. Each issue carries `required_for`, so a caller can see
the affected graph IDs. A context-bound `next` also includes the exact
`planning_context`, `planning_context_check`, and `planning_blocked_steps`.
`ready` remains dependency-derived; it is not a launch grant.

## Commands and inputs

| Operation | INPUT.json fields | Effect |
| --- | --- | --- |
| capabilities | No RUN or file | Report selected-package context support |
| validate-graph | No RUN; file contains `{graph}` | Validate graph and step contracts without creating a run; return canonical graph digest |
| init | `{graph,owner,planning_context?}` | Exclusively create a new run; return next actions |
| next | No file | Read exhaustive categorical progress, ready IDs, active attempts, accepted IDs and recovery actions |
| claim | `{owner,steps:["B","C"]}` | Reserve precisely these ready IDs atomically; return preparation packets, which never launch by themselves |
| start | `{owner,attempt,context,executor?}` | Native path persists launch intent and returns launch; `main-context` executor atomically enters serial work and returns execute; exact replay reconciles |
| launched | `{owner,attempt,handle}` | Save actual nonempty native handle returned by the host |
| packet | `{attempt}` | Read frozen task/context, supplier evidence and any `prior_attempts`; never authorize another launch, execution, acceptance, or successor selection |
| check-context | `{step}` or `{attempt}` | Read context availability for one current graph step; never mutates state or authorizes launch/acceptance |
| report | Envelope below | Publish one immutable inbox receipt; dispatcher state unchanged |
| receipt | `{attempt}` | Return the envelope and digest of its stored bytes; never infer completion or acceptance |
| settle | `{owner,attempt,verification}` | Record independent accepted/rejected decision and return next actions |
| retry | `{owner,attempt,confirmed_stopped:true,reason}` | Retire nonaccepted attempt; next claim gets a fresh token whose packet lists it in `prior_attempts` |
| takeover | `{oldOwner,newOwner,confirmed_stopped:true,reason}` | Fence old dispatcher owner, retain workers/receipts |

Every successful operation scoped to a RUN includes `next_argv`, exactly
`[node-executable, selected-helper-absolute-path, "next", absolute-run-path]`,
and a nonempty `instruction`. For a dispatcher-scoped response, the dispatcher
carries out its instruction, then uses that exact argv to read current actions.
The next response, rather than this reference, decides whether the current task is claim,
preparation, launch, collection, verification, recovery, or completion. A
worker's `report` response is task-facing only: it ends the bounded task phase and
orders the worker to return that exact response, including its `next_argv`, to the
parent. The worker never follows the argv, dispatches successors, acknowledges the
receipt, updates parent state, performs dispatcher acceptance verification of the
receipt, or settles. Those duties appear only in the parent's subsequent `next`
action. The same boundary applies to bounded
main-context task execution: the task returns the report response and the
dispatcher loop follows graph navigation.

For a context-bound packet, `planning_context` is the exact init reference,
`planning_brief` is the manifest's `{path,sha256}` briefing reference, and
`reference_material` is the full list of shared and step-applicable artifact
entries. The packet's task and definition-of-ready/done fields remain the sole
execution assignment. Workers verify each reference hash, use the planning brief
for key planning reference statements, then read applicable material before that
assignment work. Missing material produces a BLOCKED report; it never authorizes
a guessed substitute. Workers use applicable planning facts and constraints within
the task/ready/done contract. If those facts conflict with it, they preserve the
discrepancy and evidence and report it to the parent before affected work; they do
not change the graph. Context-bound packets deliberately omit `graph.source.goal`;
graph-only packets carry it as their goal.

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
reserve resources. Restrict claim count using actual available execution capacity;
the caller preserves serial capacity one for main-context work.

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

For every Git task, including a `main-context` task, the dispatcher is the
selected Ask-Agent package's parent. After the read-only planning-context check,
it binds the selected helper, validates the declared capability response above,
uses the unchanged identity binding, prepares from the actual initiating checkout,
and records `inspect --phase prepared` before `start`. Keep the capability
declaration, selected package binding, identity and exact preparation receipt in
the parent pending-job record and durable preparation evidence. Standalone
Dispatcher uses its readiness artifact, bound by path and digest. When ShipLoop
is the parent, preserve the caller's immutable `ready_evidence`: its existing
attempt-bound preparation/allocation records and enriched launch packet carry the
helper evidence. This adds no fields to `context` and no dispatcher receipt state
machine. The parent and selected helper validate receipt meaning and workspace
match. Recover those values from the same durable carrier; missing or mismatched
evidence blocks launch.
Only then freeze the helper's exact returned worktree as `context.workspace`. The
first `action:"launch"` may call the native tool directly only with that same
capability declaration, package binding, identity, receipt, workspace and complete
assignment. A bounded native or main-context task receives the receipt in that
assignment, never reruns preparation or creates a worktree, and runs the selected
helper's `check-context --receipt` before task work. Its observed command cwd and
Git root must both match `context.workspace`; a mismatched or unavailable check is
BLOCKED. An unavailable or incompatible capability blocks Git preparation rather
than permitting caller-prepared or serially allocated Git worktrees. Non-Git work
uses the same compatible selected package but keeps the ordinary
context/readiness contract without managed workspace preparation.

Once a task packet is delivered, the native worker is already started in its
assigned workspace. It uses available tools, skills, permissions, and execution
facilities within assigned authorization, does not repeat preparation or allocate
a worktree, runs the required context check, and returns its report response to
the parent. It does not receive parent launch, status, collection, or waiting
directions. A non-Git native task uses its assigned generic workspace and write
scope without managed workspace preparation.

For a same Git attempt recovered or delivery-retried, retain and inspect the same
declared capability response, identity, and preparation receipt; do not run full
prepare again or create a worktree after dispatcher `start`. A dispatcher `retry`
creates a new attempt, so its later Git preparation needs a fresh capability gate,
identity and receipt. Record the exact initiating checkout, branch and base as the
return target, even when it is a linked worktree; do not substitute `main` or the
primary checkout. The selected helper's Git requirements govern worktree creation
and return enforcement.

Worker envelope:

```json
{"run_id":"run_...","step":"B","attempt":"attempt_...","status":"SUCCEEDED","evidence":{"path":"/absolute/result-B.json","sha256":"64 hex digits"}}
```

Status is SUCCEEDED, FAILED or BLOCKED. Result artifact records actual output,
commit/workspace identity where applicable, checks and exit codes, and limitations.
It includes a `criteria` array with one entry per definition_of_done item,
`{criterion, check, observed, level}`: the item text, the check or inspection
used, the observed output from the final pass, and a level of `confirmed`,
`inspected`, `failed`, `not_run` or `unconfirmable`. It also includes
`discrepancies` and `recommendations` arrays, empty when there are none. The
helper does not parse the artifact; the parent reads `criteria` during
verification.
Its self-contained handoff summary preserves material discoveries, corrected
assumptions, decisions and concise rationale, checks actually performed,
unresolved questions, and implications for the assigned result; it states when
there are no material new findings and identifies supporting result files. A
task/ready/done discrepancy includes its evidence and is reported to the parent
without changing the graph.
Native workers return both the envelope and artifact paths through native completion,
including if inbox publication failed. They also return the actual `report`
response and its `next_argv` to the parent, without following graph navigation or
performing parent collection, dispatcher acceptance verification of its receipt,
or settlement. A main-context task
writes the same result and envelope itself; that report handoff ends its bounded
task phase in the same conversation. The dispatcher then follows its next action
to begin its distinct parent verification phase, and the parent may retry the exact report in
either path.
The packet assigns concrete output files under `RUN/artifacts/ATTEMPT/` and
creates that directory at start. Workers may write only their own `result.json`
and `envelope.json` there; canonical state and other attempts remain dispatcher
owned. Write the result, compute its hash, and fill the actual status/digest in
`report_envelope`; its evidence path and identity are already concrete. Execute
the returned `report_argv`. The public helper rejects a different evidence path,
and its CLI rejects a different envelope input path. Packet recovery deterministically
returns the same output paths. Output-directory setup happens before launch intent;
a setup failure leaves the claim unlaunched and startable.

### Exit criteria

Every packet tells the worker, native or main-context, that its
definition_of_done items are its exit criteria. The task is finished only when
each item is confirmed as far as the environment allows:

1. Before editing, record for each item the command or inspection that confirms
   it and what counts as a pass, using the item's `Confirm by:` method when it has
   one. Existing tests, check scripts, golden or fixture files, and thresholds
   belong to the checks and change only when an item says so.
2. Confirm with what is already present. Never download, install, or fetch a
   tool, runtime, or dependency to confirm an item; record the best available
   evidence and recommend what would confirm it.
3. Stay within the task. A check whose satisfaction would make the result do or
   claim something the task does not ask for stays failing, and the discrepancy
   is reported.
4. After the last edit to any file, rerun every check in one pass; only that pass
   counts. A failing check changes the work, not the check.
5. Stop on exactly one: every item confirmed or inspected, or reported
   `unconfirmable` when its definition_of_done text already says `Confirm by:
   unconfirmable here`, and none failed → SUCCEEDED; an item proven unachievable
   → BLOCKED; the same check still failing after 3 genuine fix attempts → FAILED.
   An item is proven unachievable only when (a) it contradicts another item, the
   task, or a protected file, shown by a check after all compatible work is done
   and with the existing behavior kept at the conflict point; (b) confirming it
   needs a tool, runtime, access, or authority that is absent, for an item the
   plan did not already mark `Confirm by: unconfirmable here`; or (c) satisfying
   it would exceed the task.

Missing input still means BLOCKED; never guess. The worker reports actual checks
and output artifact or commit identity, with the per-item `criteria` receipt
above.

Parent verification applies to every result, Git or not. The parent checks the
returned per-item receipt against each definition_of_done item and independently
reruns or inspects each item's confirmation. It rejects when a confirmable item
failed or was not confirmed, naming the items in the settlement reason. An item
reported `inspected` or `unconfirmable` whose `Confirm by:` required execution
means the step contract cannot be met here: treat it as BLOCKED for planning,
not as accepted. A BLOCKED result with a proven-unachievable item goes back to
planning (plan revision, or a replan in a new run), not to a blind retry.

### Parent verification and settlement

Parent verification (inside the settle request):

```json
{"receipt_sha256":"digest returned by receipt","passed":true,"reason":"Independent contract checks passed","evidence":{"path":"/absolute/verification-B.json","sha256":"64 hex digits"}}
```

Verifier evidence should include exact result/commit identity and independently
observed checks, plus the appropriate completion/stoppage observation. Before
settlement, native execution requires collecting the native task and confirming it
stopped; accepted settlement releases its workspace/resources. For a main-context
executor, record that all task-owned commands finished in the verifier evidence;
the main conversation remains active. `settle` has no `confirmed_stopped` field.
A receipt or saved identity alone does not establish
this. Independent verification is a separate checking phase with actual tests or
inspections; it need not run in a separate agent. This is a dispatcher precondition;
the helper cannot inspect native liveness or conversation state.
The parent reads the returned summary, its declared supporting files, and the
evidence needed for the current decision. Before releasing the workspace, preserve
relevant findings, open questions, and surviving evidence locators in the existing
parent handoff. If the enclosing workflow archives results, use those archived
locations after import. Evaluate a worker recommendation against the current action
and contract before submitting the verification facts and following the returned
continuation.
Only SUCCEEDED plus passed=true is accepted. Other combinations
reject and keep descendants blocked. Hashes do not establish test success. A fast
worker may report before the native handle is saved; settlement waits for that
handle without discarding the receipt. Exact report/settlement replay is inert;
changed/stale/cross-run records fail.

Planning-input availability gates only a fresh `start` and a newly passing
settlement. A changed manifest, graph, briefing, or step-required artifact is
visible on `next` and blocks those transitions without changing their state.
It never gates `next`, `packet`, `report`, `receipt`, `retry`, `takeover`, native
handle recording, or a negative settlement. Keep an already-running attempt on
its original context; use the existing replan/review boundary for new planning.

## Completion-driven dispatch

This section explains the meanings of script-returned actions and fallback
boundaries. It does not authorize a caller to construct a schedule independently
of the current response's `instruction`, `actions`, and `next_argv`.

The main conversation handles each native completion notification or collected
result. Bind it to the current run/step/attempt and saved native handle; confirm
the worker stopped, collect/publish its exact dispatcher receipt, independently
verify its done contract, and settle it. For a managed Git result, inspect the
returned contribution through its retained preparation receipt and declared delivery
mode, complete the integration or report-consumption path, and verify it before
that exact dispatcher settlement. Follow the settlement's `next` response and
refill safe ready capacity. ShipLoop's existing completion/cleanup callback alone
decides whether its accepted or superseded managed workspace is closed or retained;
the dispatcher does not invent receipt retirement or close authority. For an entered main-context attempt, `next` returns
`resume` before a report and `verify` after one: resume or check in the current
conversation without spawning, native collection, or native waiting. Because the
executor is an attestation, the current dispatcher confirms it is appropriate to
resume after recovery or takeover. A report alone never unlocks successors. Process
completion events through the sole dispatcher; workers do not select or launch
successors. No polling service or automatic cross-session callback is implied.

The public `settle` response already includes refreshed `ready`, `active`,
`accepted`, `complete`, and action data. It identifies the settled step directly
as `step`, with the existing detailed `attempt` record and `outcome`; exact replay
returns the same identity. Use that identity, not arrival order or the first
active task. Reports and receipts identify their step and attempt in `envelope`.
`ready` is the full set of pending steps
whose direct dependencies are all accepted, not just the successors newly
unlocked by this event. Check actual readiness, external resource availability
and remaining execution capacity, including caller-enforced serial capacity one
for main-context work, then claim and launch as many eligible candidates as safely
fit through the ordinary start/launched protocol. Fill every safe available slot
on initialization/resume and after each returned event; do not arbitrarily choose
a smaller eligible subset. The `claim` action's `steps` lists candidates, so
construct a request containing only that eligible subset rather than executing
the action unchanged. The helper has no host-capacity input or global slot
enforcement: the caller owns this dispatch obligation. Count claimed, launching
and unresolved work against capacity. Leave only excess or concretely blocked
ready steps unclaimed, identifying the capacity limit or blocker for each.

Start eligible existing claims and fill safe available capacity before blocking
on native collection, verification or reconciliation. `next.actions` places
`collect`, `verify` and `reconcile` after starts, serial resumes and claims so a
native observation cannot impose a wait before a ready launch. Process already
available returns promptly. If an observation cannot
resolve immediately, retain that attempt's reservation and continue unrelated
safe work. After each action follow the exact `next_argv` for current instructions;
the earlier action list is not authority for a later launch. Individual launch
and return notifications do not require serial task execution.

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
Retry a fixable failure only; a proven-unachievable item goes back to planning.

A fresh attempt's packet carries `prior_attempts`, the step's earlier attempts
oldest first, each `{attempt, status, reason, result, verification}`. `status` is
the reported receipt status (SUCCEEDED, FAILED or BLOCKED), or `NOT_REPORTED`
when the attempt was retried without a receipt. `reason` is the settlement
rejection reason when the attempt was settled, otherwise the retry reason.
`result` is the receipt's `{path, sha256}` result evidence and `verification` is
the parent's settlement `{path, sha256}` evidence; each is `null` when absent.
This is a read-only projection of existing dispatcher state and inbox receipts:
it adds no state fields and does not change retry or settlement semantics. A
first attempt's packet has no `prior_attempts` key. When the key is present, the
worker verifies those hashes, reads the results and reasons first, and
addresses the named failing items. Name the failing items in a rejecting
settlement reason so the next attempt can act on them.

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

For a managed Git attempt, recovery retains the same declared capability response,
selected package binding, identity, preparation receipt and frozen workspace.
Re-inspect or reconcile that receipt; do not rerun preparation or create another
worktree after `start`. A replacement attempt needs a fresh capability gate,
identity and preparation receipt before it can start. ShipLoop's superseded
workspace retention and finish decision remain within its existing lifecycle.

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
