---
name: plan-dispatcher
description: >-
  Use when executing or resuming an agreed dependency graph with one main
  dispatcher and parallel native workers: claim ready steps, preserve launch
  state, collect result evidence, verify outcomes, and identify successors.
  Planning belongs to Backchain or the caller; this skill executes the plan.
version: 0.3.0
author: Backchain
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
  hermes:
    category: software-development
    tags:
      - dependency-dag
      - execution
      - native-agents
    related_skills:
      - backchain
      - ask-agent
---

# Plan dispatcher

The main conversation is the sole dispatcher. Native workers perform bounded
tasks and report evidence; only the dispatcher accepts results and schedules
successors. Use the available ask-agent skill for fresh native contexts. An
explicitly serial caller may instead execute one task in its current main context
through the durable `main-context` identity described below; the caller enforces
capacity one. If neither path is available, report that boundary; do not
substitute a model subprocess.
Every Ask-Agent delegation selects a compatible package before execution. Bind
its selected absolute `SKILL.md` and helper, run `capabilities --skill-card ABS`,
and accept only its declared `shiploop-chain-ask-agent-managed-worktree/v1`
schema with the full current capability set: `helper-managed-worktree`,
`prepared-inspection`, `returned-commit-delivery`, `fingerprint-bound-close`
and `ignored-output-report`. The capability set is the gate, not a version
number; do not infer compatibility from a version, frontmatter or prose. Then use the existing `identity --skill-card ABS` binding and
preserve that selected-card/helper identity. For every Git task, use that selected
managed-worktree helper before freezing dispatcher context. Non-Git delegation
uses the same compatible selected package but retains its generic context without
managed workspace preparation. The dispatcher is Ask-Agent's parent for Git
preparation, integration ordering and acceptance; it may delegate integration
execution.

Every run-scoped helper response includes an `instruction`. A `next` response's
`actions` are the graph-navigation authority. For dispatcher-scoped responses,
the dispatcher executes that prompt and the returned exact `next_argv`; do not
derive successors, recovery work, or a parallel schedule from the graph or this
document. The task-facing `report` response instead ends the bounded task phase:
the task returns it, including its `next_argv`, to the dispatcher, which then
uses that argv for the next phase. This skill explains the response fields and
fallbacks, but it is not another scheduler.

For a fresh native `launch`, the parent assembles the complete returned worker
packet unchanged beside a compact **Current learnings** block with a Markdown
heading and short labeled bullets from the current conversation. State explicitly
when no learnings are relevant. Keep essential
facts and rationale inline, with evidence locators for detail; the block cannot
broaden the frozen task contract. Retain the effective assignment and launch
identity in the existing parent record or retained handoff, durably outside the
worker workspace, before recording the confirmed native handle. Parent launch,
status, collection, and waiting directions stay in parent
responses. The already-started worker receives its bounded task role, workspace,
scope-authorized facilities, checks, handoff, and report-return obligations.

For user-facing status, use the returned `progress` rather than reconstructing
task categories from conversation history. `next` computes it from the current
durable state and observed receipts; initialization, claim, start, launch
confirmation, settlement, retry and takeover also return it. The parent refreshes
it through the existing `next_argv` at the normal continuation boundary, after
executing the current instruction. A worker returns its exact report response
to the parent; it does not run the refresh itself.

`progress` accounts for every required task exactly once in `completed`, `active`,
`awaiting_verification`, `pending`, `blocked`, or `failed`, with a task description,
state, reason and unmet dependencies. `counts.remaining` includes all five
non-completed groups. `pending` includes tasks waiting on dependencies as well as
dependency-ready work; its `dependency_ready` flag never authorizes a launch.
`active` includes claimed and unconfirmed launching work, so read the row's state
instead of assuming the worker is running. A receipt remains awaiting verification
until settlement accepts it. `actions` still determines what the parent may do
next. These internal categories are facts to explain, not a required display
template. See [the status projection contract](references/protocol.md#categorical-progress)
for classification and observation limits.

At every native-agent boundary, status is mandatory. Write meaningful status
changes in clear, thoughtfully formatted Markdown, choosing the structure and
detail that fit the facts instead of following a fixed template or mechanically
dumping packet fields. Explain what happened, what has been accomplished, and
the immediate next work or remaining condition; emphasize significant findings,
blockers, or required user action. Ground the update in returned facts and
observed evidence. For each affected task, include a natural account of its
assignment, accepted or completed work, and any active, pending, or blocked
condition that determines the next work; choose useful wording and layout rather
than mechanically copying field names. Preserve pending dependencies and any gap between a worker result and
parent acceptance. Do not invent unreported work, future steps, percentages, or
an ETA.

Immediately before every native-agent call that starts or continues work,
including an initial launch, retry, or follow-up turn, identify the assignment and
say that it is launch intent until the native tool confirms it. On every native
return, including failed, blocked, or cancelled work, promptly describe the
reported outcome and state that it is not acceptance. A worker report remains a
claim about task work and checks until the parent independently accepts it; only
then may task work be described as accepted or completed. Describe whole-run
completion only when the script reports it. The parent dispatcher incorporates
worker results without duplicate overall updates, keeps protocol IDs and callbacks
internal unless they explain a problem, and preserves the required exact
launch/return notices and handoffs. Cadence, a native UI, or notification does not
replace either boundary update. Reporting does not change control flow: follow the
current authorized action or returned stop/handoff. A worker report or handoff
returns control to the parent; it does not end the run. If a dispatcher-scoped
response stops, describe prerequisites for future work without starting a wait or
retry.

Bind `scripts/dispatch.js` to the absolute directory containing this loaded
SKILL.md, not the current project, PATH or another installation. Requires Node.js
18+ and a trusted local filesystem. The complete package is copyable; it needs
no author checkout. Read [the CLI contract](references/protocol.md) when starting
or recovering a run. Every helper call reloads durable state.

When ShipLoop supplies an immutable planning-artifact manifest, first call
`capabilities` on this selected package before creating any chain-side artifact
or dispatcher run. Only pass `planning_context:{path,sha256,source}` when it
advertises `shiploop-planning-artifacts/v1`. The manifest preserves planning
reference material beside the reviewed graph; the step task/ready/done contract
remains the sole execution assignment. It does not select successors, create a
queue, change worker authority, or transport the original user prompt.
Workers use applicable planning facts and constraints to carry out that assigned
task. If a fact conflicts with task, ready, or done, preserve the discrepancy and
its evidence and report it to the parent before affected work; do not change the
graph.

Before saving a new immutable caller binding, require capability
`graph_validation: execution-graph/v1` and call `validate-graph INPUT.json`
with `{graph}`. It takes no run path and validates through the same graph and
contract checks as init, without writing state. A rejected graph can therefore
be corrected before a binding exists. This preflight does not check planning
files or replace init's current-input checks; existing bound runs retain their
selected package for recovery.

## Execute

1. Use an agreed graph with per-step task, ready and done contracts. When the
   input is Backchain JSON, use its checkout exporter if available; otherwise
   preserve the caller's explicit dependency and contract information in the
   documented format. Never discard unresolved needs to make a graph executable.
   Choose one absolute run directory shared by all workers, outside their
   workspaces, and a unique dispatcher owner. For a context-bound run, initialize
   with the exact immutable `planning_context` reference after capability
   preflight; init verifies required material before creating the run. Initialize
   once; resume with `next`.
2. Follow the current script response exactly: execute its `instruction`, then
   its exact `next_argv`, and obey the resulting current actions. The script owns
   graph navigation. `next` returns dependency-ready IDs and recovery actions.
   Check external readiness facts, including initial-world inputs, available
   execution capacity (including caller-enforced serial capacity one for
   main-context work), and shared resources, before claiming returned candidates.
   Fill every safe available slot from the returned candidates on the first
   response and every refresh; do not arbitrarily select fewer eligible tasks.
   Count claimed, launching and unresolved work against capacity. These facts
   may defer candidates; identify each concrete blocker or capacity limit, and
   never add or infer another successor ID. A claim
   reserves work but does not mean an agent exists. For a context-bound run,
   inspect `planning_context_check` and `planning_blocked_steps`; `ready` remains
   a dependency view, not permission to start a step with unavailable planning
   material.
3. Prepare a separate workspace per concurrent worker and an immutable readiness
   artifact describing the facts actually checked. Before allocating the workspace
   or integrating a target, run this dispatcher's `check-context` for the exact
   step or attempt. For every Git task, including an explicitly serial
   `main-context` task, the dispatcher is the selected Ask-Agent package's
   parent. Its required order is selected package binding,
   `capabilities --skill-card ABS` compatibility gate, unchanged
   `identity --skill-card ABS` binding, helper `prepare`,
   `inspect --phase prepared`, then dispatcher `start`: bind the selected helper,
   coordinate source writers, prepare from the actual initiating checkout, and
   retain the returned receipt, worktree and baseline. Record the declared
   capability response, selected package binding, identity, and exact preparation
   receipt in durable preparation evidence and the parent pending-job record:
   standalone Dispatcher uses its readiness artifact; ShipLoop uses its existing
   attempt-bound preparation/allocation records and enriched launch packet while
   preserving the caller's immutable `ready_evidence`. Do not add helper receipt
   fields to generic `context` or a dispatcher receipt state machine. Only a
   successful prepared inspection lets the dispatcher freeze that exact returned
   worktree as `context.workspace` and pass the context to `start`. Do not create
   another worktree or rerun preparation after `start`. Name the integrating
   owner, worker base, contribution scope, synchronization policy, exact
   initiating checkout/branch and revision as the return target in the readiness
   evidence and worker handoff. Carry required uncommitted inputs explicitly; a
   worktree from HEAD does not contain them. An unavailable or incompatible helper
   capability blocks Git preparation: do not adopt a caller-prepared worktree or
   allocate a serial Git workspace. Non-Git work retains the existing generic
   workspace and readiness-evidence contract while using the already selected
   compatible Ask-Agent package; it does not invoke managed workspace preparation.
   Native start input is
   `{owner,attempt,context}`; only its first
   `action: launch` response authorizes native launch with the complete
   returned packet. A serial caller instead supplies
   `executor:{kind:"main-context",id:"stable-id"}` in that same atomic start
   request. Its first response is `action: execute`, records no native handle,
   and records the caller's main-context execution attestation for the bounded
   task. The helper cannot authenticate a live conversation, so a recovery or
   takeover dispatcher must explicitly confirm it may resume that identity. A
   `reconcile` response never authorizes a new launch or a second execution.
   A `packet` or `check-context` response is read-only: it never authorizes a
   launch, acceptance, or successor selection; return to its exact `next_argv`.
4. Launch a fresh context with no inherited history where the native tool permits
   it. Default to the broadest general-purpose native worker unless the user
   requested an available named worker; express a descriptive role in its task.
   Where the host supports it, retain the parent's available tools, skills,
   permissions and execution facilities within the assigned authorization. Do
   not add arbitrary tool restrictions, read-only modes or model downgrades;
   disclose material host filtering instead. Workers must stay within their
   relative write scope and cannot select graph successors. Further native
   delegation must preserve the assigned capacity, ownership and isolation
   constraints; workers collect their own delegates before completion. An
   explicit task constraint may prohibit it. These are parent launch
   instructions, not worker-packet instructions. The parent launches the complete
   returned worker packet unchanged beside a compact Current learnings block with
   a Markdown heading and short labeled bullets, states explicitly when none are
   relevant, and retains the effective assignment
   and launch identity in its existing parent record or retained handoff, durably
   outside the worker workspace. Immediately before every
   native-agent call that starts or continues work, including a retry or
   follow-up turn, publish the mandatory user-facing status above. That status
   is launch intent only, not confirmation. Record the confirmed native handle
   with `launched`, announce the assignment and the parent's next action, and
   retain a parent-owned pending-job entry with the label, handle, last observed
   status and returned report/result when available. For every managed Git native
   attempt, the first `action: launch` permits a direct native launch only with
   the same declared capability response, selected package binding, identity,
   preparation receipt, frozen `context.workspace`, and complete assignment
   recorded before `start`. The bounded worker is not an Ask-Agent parent: it
   must not rerun full preparation or create a worktree. Before task work it runs the selected helper's
   `check-context --receipt` from its assigned operation directory and records
   the observed command cwd and Git root; both must match `context.workspace` or
   it reports BLOCKED. Continue useful parent work.
   The worker is already inside the bounded task: it uses the assigned workspace,
   write scope, and available facilities within authorization, while retaining
   applicable task constraints and report-return ownership. Parent status,
   launch, collection, and waiting directions are not copied into that packet.
   A non-Git native task uses its assigned generic workspace and write scope
   without managed workspace preparation.
   A native notification or join collects an actual result. While only waiting,
   update that record only from native events or collection; a native observation
   timeout is not completion. Before becoming waiting-only, select native timed
   collection, equivalent visible native progress, or a supported current-session
   status wakeup under the selected Ask-Agent guidance and user cadence/quiet
   preference. On an observation timeout, give a combined visible pending-job
   update before collecting again; the worker keeps running. If no periodic
   mechanism is available, disclose that before becoming idle and continue native
   completion collection. A wakeup is never a completion substitute. Do not create
   custom timers, external recurring tasks or output-file polling.
   For `action: execute`, do the bounded task in the current main conversation
   instead. For a Git task, use the same capability-gated, helper-prepared frozen
   workspace and receipt that the parent recorded before `start`; do not repeat
   package binding, capability/identity checks, preparation, or worktree
   allocation. From its assigned operation directory, run the selected helper's
   `check-context --receipt` before task work. Do not call ask-agent to launch a
   native worker, wait for a native handle or fabricate one. The report handoff ends that bounded task phase:
   return the actual report response, including its `next_argv`, to the dispatcher
   phase in the same conversation. As the task, do not execute that argv, navigate
   the graph, perform dispatcher acceptance verification of the receipt, or settle.
   The same conversation then has a distinct parent verification phase; execution
   success is not acceptance. The dispatcher's next response begins that phase.
   Preserve the returned executor identity on recovery and
   attest it remains appropriate before resuming; `next` returns `resume` while
   task work remains and `verify` after its receipt exists. Context packets include the
   exact manifest ref, its planning brief, and shared/step-required reference
   material. The graph step contract remains the execution assignment; workers
   hash-check and use the brief's key planning reference statements and material
   before task work. They use applicable planning facts within that contract and
   report an evidence-backed task/ready/done discrepancy to the parent without
   changing the graph. An unavailable required input is BLOCKED, never guessed.
   Every packet makes the definition_of_done items the worker's exit criteria:
   record each item's confirming check and pass condition before editing (using
   its `Confirm by:` method when present), never install or fetch a tool to
   confirm one, stay within the task, rerun every check in one pass after the
   last edit, and stop on SUCCEEDED (all confirmed or inspected, or reported
   `unconfirmable` when the item already says `Confirm by: unconfirmable here`,
   none failed), BLOCKED (an item proven unachievable) or FAILED (the same check
   still failing after 3 genuine fix attempts). See [exit criteria](references/protocol.md#exit-criteria).
5. A worker writes its result/envelope at the packet's concrete `outputs` paths,
   publishes a `report` using the returned argv, and returns the actual receipt
   response, including its `next_argv`, with those paths plus SUCCEEDED, FAILED or
   BLOCKED and a brief assignment reminder and next action/owner. That return ends
   the bounded task phase. The worker never follows `next_argv`, dispatches
   successors, acknowledges the receipt, updates parent pending state, performs
   dispatcher acceptance verification of the receipt, or settles; the dispatcher
   gets its own next response for those duties. This
   continuation ownership also applies to a bounded main-context task: its task
   execution returns the report response to the dispatcher loop, which alone
   follows graph navigation.
   The result artifact includes a `criteria` array, one
   `{criterion, check, observed, level}` entry per definition_of_done item with
   the observed output from the final pass and a level of `confirmed`,
   `inspected`, `failed`, `not_run` or `unconfirmable`, plus `discrepancies` and
   `recommendations`.
   Substantial results begin with a self-contained handoff summary;
   repository results include the Git receipt, exact contribution/target
   revisions and integration state. Preserve material discoveries, corrected
   assumptions, decisions and concise rationale, checks actually performed,
   unresolved questions, and implications for the assigned result; state when
   there are no material new findings. Keep essential meaning in the summary and
   identify supporting result files. The report writes only its inbox receipt.
   The dispatcher's post-report `next` action owns the next phase. On every
   native return, immediately publish the mandatory user-facing status above,
   then acknowledge the task label and reported outcome, update the pending-job
   entry and state that the return is not verification or acceptance.
   Read the returned summary, its declared supporting files, and the evidence
   needed for the current decision. Preserve relevant findings, open questions,
   and surviving evidence locators in the existing parent handoff before releasing
   the workspace. If the enclosing workflow archives results, use those archived
   locations after import. Evaluate the worker's
   recommendation against the current action and contract before submitting
   verification facts and following the returned continuation.
   For every result, Git or not, check the per-item `criteria` receipt against
   each definition_of_done item and independently rerun or inspect each item's
   confirmation. Reject when a confirmable item failed or was not confirmed,
   naming the items in the settlement reason. An item reported `inspected` or
   `unconfirmable` whose `Confirm by:` required execution means the step
   contract cannot be met here: treat it as BLOCKED for planning, not as
   accepted. A BLOCKED result with a proven-unachievable item goes back to
   planning (plan revision or replan), not to a blind retry.
   For a main-context report handoff, it records that all task-owned commands
   finished at the bounded task-phase boundary in the current conversation. It
   reads the assigned handoff and independently checks the task's done contract,
   relevant tests/artifacts and actual commit identity. For a Git result, inspect
   the returned contribution through the same Ask-Agent preparation receipt and
   declared delivery mode, complete the declared integration or report-consumption
   path, and independently verify it before `settle`ing the exact dispatcher receipt. A
   passing settlement rechecks the
   relevant planning inputs; report, receipt, retry, takeover, packet inspection,
   and negative settlement remain available when a later input check fails. Native execution requires verifying
   the worker stopped before settlement releases resources, including delegates.
   For a main-context execution, record that all task-owned commands have finished
   in the verifier evidence; the main conversation remains active. Independent
   verification is a distinct checking phase with actual tests or inspections;
   it need not use a separate agent. Only accepted results unlock successors. Before integrating, recheck the target
   revision and reassess changed targets; serialize updates to that target and
   verify the combined behavior. Worker completion alone does not prove
   integration. After that accepted settlement, follow `next` and refill safe
   ready capacity. When ShipLoop owns the managed helper lifecycle, its existing
   completion/cleanup callback alone decides whether an accepted or superseded
   workspace is closed or retained. The dispatcher does not invent a receipt
   retirement or close authority.
6. After every dispatcher-scoped authorized action, settlement, retry, takeover,
   or recovery observation, the parent executes the returned `instruction`, then
   follows the exact `next_argv` and obeys its current actions. After a task report
   handoff, the parent uses that exact `next_argv` to receive the next dispatcher
   action; it does not treat the task-facing report instruction as parent work. It may offer
   multiple successors and still-ready work deferred earlier. Check readiness
   and resources, then claim and start as many returned eligible IDs as safely
   fit current execution capacity, including caller-enforced serial capacity one
   for main-context work. Start eligible existing claims too. Fill available
   slots before blocking on collection, verification or reconciliation; an
   unresolved observation keeps its reservation but does not block unrelated
   safe work. Leave only capacity-limited or concretely blocked work pending,
   identifying each deferral. Do not wait for an entire wave or reschedule
   accepted work. No ready IDs is not completion while
   work is active, blocked or unresolved.
   See [completion-driven dispatch](references/protocol.md#completion-driven-dispatch).
   A dependent step receives accepted supplier evidence.
   If it needs integrated code, depend on an explicit merge-and-verify step and
   use that accepted commit as its base. Completion in an isolated branch does
   not put the code into another worktree.
7. Finish only when the script's current `next` response reports `complete:true`
   and the required integration/verification outcomes have evidence. Report
   integration status and next action/owner;
   retain handoffs needed for unresolved work or recovery. Report failed or unresolved work honestly. Execution
   does not extend authorization for publication, deployment or external effects.

## Recover

Use the current response's `instruction` and `next_argv` to rehydrate; do not
reconstruct navigation from conversation memory. `packet` only rehydrates the
bounded task and is not a launch, acceptance, or scheduling authority.
An unsent claimed attempt can start. A saved intent without a confirmed handle
must be reconciled through native inventory and the full dispatch identity before
any retry. Hosts without reliable lookup leave that outcome unknown. An attempt
with `executor.kind:"main-context"` is already entered: resume it in the current
main conversation, or verify its saved receipt, without spawning or waiting on a
native worker.

Retry only after confirming the old worker stopped and inspecting its effects;
the helper creates a fresh attempt on the next claim and rejects stale reports.
The fresh attempt's packet carries `prior_attempts`, the step's earlier attempts
oldest first as `{attempt, status, reason, result, verification}`, read from
existing state; the worker reads them first and addresses the named failing
items. A first attempt's packet has no `prior_attempts`.
A recovered managed Git attempt retains the same declared capability response,
selected package binding, identity and preparation receipt: inspect or reconcile
that preparation rather than rerunning it or creating another worktree. A fresh
retry attempt needs a fresh capability gate, identity, and preparation receipt
before its `start`. A ShipLoop-superseded helper workspace remains in ShipLoop's
existing retained/finish lifecycle; the dispatcher has no separate retirement
authority.
Takeover requires confirming the old dispatcher stopped; keep active worker
handles and use a new, never-reused owner ID. The helper does not verify these
attestations or cancel native work. Orphan locks are never stolen by age; see
[recovery details](references/protocol.md#recovery-and-limits).

For a busy receipt write, preserve the exact envelope and return its paths to
the parent for publication retry. Do not rerun the task. Saying “I'm done” alone
does not call this skill, accept work or wake a lost parent conversation.

See [host evidence](references/host-matrix.md) before claiming portable native
recovery. Saved state does not establish survival or notifications across sessions.
