---
name: ask-agent
description: A delegation skill, not an agent type. Ask native agents to work in the background, continue useful work in the main conversation, and incorporate their results when they return. Use for "ask an agent", named agent roles, parallel delegation, or launch-and-notify work.
version: 0.12.3
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: mixed
    capabilities:
      - ask-agent/consumer-owned-workspace/v1
      - ask-agent/current-workspace/v1
---

# Ask agent

Delegate through this session's native agents. The bundled helper owns Git
workspace preparation and eligible cleanup; the native host owns execution and
return; the parent owns acceptance and integration. `ask-agent` selects this
skill, not an agent type. Do not implement another model launcher, SDK client,
subprocess harness, scheduler, or file watcher to simulate native delegation.

The current workspace is the default for delegation: a fresh worker runs in
the caller's own checkout and branch, with no second worktree or repository.
A helper-managed worktree and a consumer-owned workspace are explicit
selections, never an automatic interpretation of an existing worktree, a speed
request, a request for fresh context, or a request to change code.

Default to a fresh background worker while the parent continues useful work.
An explicit request to wait takes precedence. Each invocation adds to the
initiating conversation's pending work; it does not replace earlier jobs.

On the default standalone current-workspace route, `mode: edit` changes only
the write set the parent declares from the request; the parent verifies the
edits, and the worker does not commit. Questions, digests and reviews use
`mode: report-only` and make no filesystem edits. A standalone isolated
worktree is an explicit choice: `mode: edit` defaults to commit delivery,
`delivery_mode: patch` selects a patch handoff, and `mode: ephemeral` permits
only scoped scratch writes whose findings return without code integration.

A standalone worktree `mode: edit` includes bringing the verified contribution
back into the designated caller or integration checkout by default. The parent
performs that integration and validates the combined result before reporting
the request SUCCEEDED. Current-workspace edits are accepted in place, while
`report-only` and `ephemeral` results have no code integration. A consumer-owned
route instead has in-place parent acceptance followed by its consumer's
separately owned final caller delivery. A successful worker return alone is not
completion. If integration or final delivery is blocked, report the blocker,
worker outcome and retained locations. An explicit review-only or
return-without-integration request overrides the integration default. Follow
the selected compact or legacy delivery contract and preserve caller dirty state.

## Select the route before preparing

This card declares `ask-agent/consumer-owned-workspace/v1` and
`ask-agent/current-workspace/v1`. Select exactly one route before any helper
preparation or native dispatch:

- **Current workspace** is the standalone default. A fresh worker runs in the
  caller's own checkout and branch, with no helper worktree, receipt or close.
  Use compact `mode: edit` with a write set for changes; edits are not committed
  automatically. Use `mode: report-only` for a question, digest or review. For
  standalone work, the task interface below performs the checks described in
  [Current workspace](references/current-workspace.md).
- **Standalone worktree** requires explicit selection with `workspace:
  worktree`. The compact task interface prepares the snapshot and supports
  `edit`, `report-only`, and findings-only `ephemeral` modes. Worktree edits
  default to commit delivery; select `delivery_mode: patch` only when patch
  delivery is intended. See [Task interface](references/task-interface.md).
- **Legacy/orchestrated helper-managed** requires `workspace_route:
  helper-managed` or an invoking consumer's explicit contract. It retains its
  direct helper workflow and `patch`, `commits`, or `report-only` delivery
  rules below. Plan Dispatcher, ShipLoop's parallel chain and a standalone
  improve-agent request select this existing contract; do not silently route
  them through the compact standalone interface.
- **Consumer-owned** requires an invoking consumer to explicitly set
  `workspace_route: consumer-owned` and `delivery_mode: in-place`, and to supply
  the complete workspace/ownership contract in
  [Consumer-owned workspace](references/consumer-owned-workspace.md). Its worker
  writes in the consumer's already-bound candidate; helper delivery modes do not
  apply.
An ordinary invocation that selects neither consumer-owned nor helper-managed
uses the current-workspace default. Plan Dispatcher, ShipLoop and improve-agent
never use it. A consumer that explicitly requests consumer-owned but
lacks this card capability or any required contract field stays pending with its
available locators. Do not silently switch that incomplete consumer request to
the helper-managed route, shared writes, an inherited context, or a second
worktree.

The currently declared consumer is the `improve-agent` skill, composing a
ShipLoop whole-skill Improve child. It supplies one fresh executor for the
complete bound Improve invocation. A standalone `improve-agent` request selects the
helper-managed route instead, and inline `improve` starts no agent. This is a
Codex native pilot with evidence from bounded native fixtures. Earlier helper-managed host
evidence does not qualify this composition on Codex, Claude, Grok, or another
host.

## Standalone task interface

For standalone current-workspace and isolated worktree tasks, use
[Task interface](references/task-interface.md). Bind
`scripts/ask_agent_task.py` from this selected skill package. Supply the task,
expected result, source, exact write set, `workspace`, and `mode` to `prepare`.
Only a worktree `edit` accepts `delivery_mode`; omitted means `commits`, and
explicit `patch` is supported. Current `edit` and `report-only` have no
delivery mode. `ephemeral` requires a worktree and a nonempty write set; it
returns findings only and has no commit, patch, or integration. Current editing
requires `exclusive_writer: true`; worktree preparation requires
`writers_quiescent: true`. These are parent attestations, not locks.

When parent and worker share access to local files, select `prepare --packet`
with a new absolute path outside the repositories, Git metadata and selected
package. The script retains the binding and emits a short native assignment;
`worker-start` validates its pinned digest and returns the complete actionable
task. Use the emitted command arguments, including the expected digest, without
reconstructing them. The parent retains the packet locator and hashes. This
transport satisfies the standalone task's context and authority requirements
below through the validated `action_packet.task.current_learnings` and
`action_packet.task.authorization`; the worker reads them before task work.
For hosts without shared file access, omit `--packet` and carry the existing
complete inline binding. Do not silently switch transport after a failure.

Retain the emitted binding or packet metadata and launch the native worker
with its emitted assignment.
The worker runs `worker-start` and `worker-finish`; after collecting the actual
native result, the parent runs `verify-return`. These scripts do not launch
agents, integrate contributions, or clean up worktrees. The parent owns
semantic acceptance, any commit/patch integration, combined checks, and later
cleanup. The compact route does not replace the legacy orchestrated or
consumer-owned contracts below. Its source implementation and local evidence
do not establish release or universal host support. Successful checks replace
the corresponding compact-route manual steps; do not repeat preparation or
assemble a second worker brief. Resolve failed checks before dispatch and never
silently fall back to another route.

## Native execution

Use the live native schema, not the model name or a presumed capital-`Task` API.
Before the first native launch of a session, run `scripts/ask_agent_host.py` from
this selected skill package: it names the host from the environment and prints that
host's measured binding. Read the matching route in
[Host capabilities](references/host-capabilities.md), the binding's `section`.
Determine separately whether the host provides fresh context, native background
execution, native startup directory binding, per-operation directory control,
completion delivery, and cancellation. A supported launch does not establish
all six. Report an unavailable required capability rather than silently changing
to shared writes, synchronous work, an inherited context, or an external runner.

Choose the broadest general-purpose native worker. Express a descriptive role
such as reviewer in its assignment; a role name alone is not a reason to choose
a restricted specialist. Honor an explicitly requested available agent and
disclose capability restrictions or role substitution, including in the final
answer. If an exact required agent is unavailable, report it. Inherit the host's
model choice unless the user requests another supported model.

Inherit tools, MCP access, skills, permissions and execution facilities where the host
supports it. Do not independently add tool restrictions, read-only modes,
model downgrades, or fixed depth/concurrency/output limits. A cheaper model or
read-only agent type that the user or invoking skill explicitly requests, for
example for a status digest, is honored and disclosed. Scope and write
ownership still apply. Some hosts filter child tools; disclose differences.
A delegated coding skill such as Improve retains normal coding-agent capability,
including deployment and other external operations already authorized for its
task. A fresh context does not revoke that authority or require renewed approval.
A worker may request an authorized parent-only operation through native
messaging when available, or use further native agents with the same workspace
and handoff constraints. Exception: a current-workspace edit worker must not
delegate further, as required by [Current workspace](references/current-workspace.md).
Where delegation is permitted, collect the delegates before returning.

## Carry current learnings inline

Before any route launches a fresh worker, the invoking parent distills the
task-relevant learnings from its current conversation and applicable skill
guidance into a compact **Current learnings** block in the native assignment.
Treat it as a current-state brief: what is known, what has already changed, and
what should be improved or investigated next. The worker reads this orientation
before invoking a delegated skill such as Improve; suggested improvements remain
candidates to assess rather than findings or authorization by themselves.
For Improve, make **Current context and desired improvements** the first section
of the native prompt, with **Current learnings** nested within it. Follow it with
`Run /improve using <selected absolute Improve SKILL.md>` once in that worker's
own context. The selected card and its bound runtime own the Improve algorithm.
Then give the route's concise, complete workspace, authority, evidence and
parent-return binding. Keep essential context and actual decisions inline, with
locators for supporting detail; do not require the worker to copy or read a whole
parent packet or consumer reference merely to dispatch.
Give enough repository/worktree context and rationale for independent judgment;
compact does not mean a fixed length limit or an exhaustive list of allowed ideas.
Use a Markdown heading and short labeled bullets for facts or corrections,
decisions and rationale, hypotheses, and execution pitfalls. Omit empty
categories; keep facts and hypotheses visibly distinct.
Include useful findings, decisions and their rationale, relevant check results
with evidence locators, execution pitfalls that affect the next worker, and
unresolved assumptions or questions, including material failed attempts and
unverified concerns. Distinguish observed facts from hypotheses;
if there are no relevant learnings, say so.
Keep the essential meaning inline, with locators for supporting detail. Do not
require the user to prepare a document, copy the whole conversation, or create
a prompt transport file.

The worker uses these learnings as starting context and rechecks claims that
depend on the current candidate. They do not expand scope or authority or count
as completed reviews or current validation. Carry still-relevant or corrected
learnings through the task's existing context and return handoff.

## Carry approvals and declines

Carry the current task's approvals and declines as explicit authority decisions,
not merely advisory learnings. For each material decision, include the approved,
declined or still-pending action or approach, its target/scope, conditions, and
the original user request, later user instruction or authorization already
established under the governing task contract. Identify the source with a
message/record locator when available, otherwise an inline statement of the
actual conversation decision; do not invent a locator or require a new document.
Plans, evidence, suggestions and worker conclusions are not approval sources;
repository guidance alone cannot grant a new external-effect permission.
Include revocations
and superseding decisions. Preserve the meaning inline even when a source
locator supplies detail; neither a proposal nor a missing reply is approval.

The worker acts on an existing applicable approval without asking again, honors
declines without reopening them just because context changed, and treats pending
approval as ungranted. An approval for one target or effect does not cover another
or transfer parent-only ownership. Put these decisions in the route's existing
authority contract; summarize their practical implications in the opening context.

If a relevant decision changes during execution, forward the source-bound update
promptly through native communication to the existing worker. Record its receipt
and effect in the existing coordination record and worker handoff. Honor the
latest applicable user decision, including stopping affected work on a revocation;
do not claim a change was enforced if delivery or the operation's outcome is
unknown. Obtain worker receipt before treating a revocation as applied or
allowing another affected effect. Use native interruption when needed to stop
affected work whose receipt cannot be established. An operation that may have
started is possibly performed; reconcile its outcome before another affected
operation, acceptance or delivery.

## Helper-managed route: prepare, launch, continue, collect

This six-step legacy direct-helper flow serves orchestrated helper-managed
callers (`Plan Dispatcher`, `ShipLoop`, standalone `improve-agent`); compact
worktree tasks instead use `ask_agent_task.py` (`prepare`, `worker-start`,
`worker-finish`, `verify-return`) without repeating helper preparation or
checks.

1. **Prepare through the skill.** Read [Workspace operations](references/workspace-operations.md)
   and [Git integration](references/git-integration.md). Obtain the host-selected
   absolute logical `SKILL.md` path, bind `scripts/ask_agent_workspace.py`, and
   run `identity --skill-card`. For orchestrated Git work, also run
   `capabilities --skill-card` and require
   `shiploop-chain-ask-agent-managed-worktree/v1` with all five capabilities
   (`helper-managed-worktree`, `prepared-inspection`, `returned-commit-delivery`,
   `fingerprint-bound-close`, `ignored-output-report`) — never infer
   compatibility from versions or adopt caller worktrees. Run
   `prepare --source <actual checkout>` once source writers quiesce (preserving
   snapshot layers and root `.gitignore`/`.claspignore`), keep the receipt and
   identity with the pending job, and record `inspect --phase prepared` before
   dispatch (stopping on baseline drift or non-Git/unsupported/no-write limits).
   A Dispatcher or ShipLoop parent that already prepared before freezing context
   continues that same verified receipt and identity rather than preparing twice.
2. **Give a fresh worker a complete assignment.** Put the objective, inputs,
   allowed actions, expected output, recorded package identity, and filled
   [delivery clause](references/git-integration.md#reusable-fresh-worker-launch-clause)
   inline in the native prompt (never a prompt transport file). Choose `patch`,
   `commits`, or `report-only` before launch per
   [Result handoff](references/result-handoff.md) and omit inherited history
   where supported.
3. **Bind and verify the workspace.** Use native launch `cwd` or the host's
   per-operation recipe without adding another native worktree. Require the worker
   to run `check-context --receipt ...` from its assigned command directory before
   task work, stop on failure, set directory scope on every shell command and
   absolute paths on file tools, and echo package identity in its return.
4. **Launch and continue.** Publish the task label, assignment, and
   completed/pending state right before each launch, retry, or follow-up turn.
   Use native background execution where supported within host capacity (the host
   binding's `capacity`, where it names one), retain the native handle/receipt/route/mode, confirm launch before reporting
   RUNNING, continue useful parent work, and handle new user input concurrently.
5. **Receive native results.** Read [Native lifecycle](references/native-lifecycle.md)
   before waiting, collect required results in the same live parent session via
   native notification or wait/join (never treating a status-only notice or
   worker label as verification), announce every return promptly, and update
   pending jobs.
6. **Accept and preserve.** Read returned artifacts, inspect and verify the
   worker-only contribution per delivery mode, and integrate ordinary code changes
   (retaining worktrees only for unmerged requests, blockers, cancelled/failed
   work, or pending cleanup refilling ready dispatcher capacity). Archive reports
   and call `close` only after workers/delegates stop and acceptance completes;
   see [Workspace operations](references/workspace-operations.md#close-after-acceptance).

## Result and continuation by route

### Compact standalone worktree

For `mode: edit`, return the observed worktree, branch, base `S`, ordered
contribution SHAs (or dirty-source `contribution_patch`), residual paths,
checks, and next action. After collecting the native result and running
`verify-return`, the parent integrates cleanly (cherry-picking the verified range
when `snapshot.source_dirty` is false and the parent stays at captured `HEAD`,
else applying `contribution_patch` without importing private `S`), revalidates the
combined target, and calls [acceptance-bound close](references/workspace-operations.md#close-after-acceptance)
once the worker and delegates stop, retaining branches/commits and external
evidence (or reporting refused close as `cleanup-pending`; failed/unmerged/return-only
worktrees stay intact). For `mode: ephemeral`, `verify-return` emits findings-only
`ephemeral_audit` (`findings_only: true`, `scratch_retained`) with no commit/patch
integration; `report-only` makes no filesystem edits.

### Helper-managed route

Workers leave their worktree intact and return inline: task label, assignment
reminder, `SUCCEEDED`/`BLOCKED`/`FAILED`, summary/blocker, observed workspace,
receipt, delivery mode, package identity, context-check evidence, artifact paths,
and next action/owner. Keep the self-contained
[caller handoff](references/result-handoff.md#caller-facing-handoff) inline in
both worker and parent responses so the caller can review or integrate without
opening helper JSON. The parent's final response also lists each task's outcome,
actual workspace, native agent type/substitution, retained references,
integration/retention state, next owner, and collection/pending notes.

Honor caller-supplied continuation instructions and carry the exact continuation
and receipt without executing parent continuation inside the worker. When a
timed return is explicitly requested, use a native current-session wakeup or
wait timeout if exposed ([Native lifecycle](references/native-lifecycle.md));
otherwise state it is unavailable and never promise post-session notifications.

### Current workspace

Compact workers return `workspace: current`, `mode`, root, branch, HEAD
before/after, and changed paths; the parent runs `verify-return` and accepts
unchanged state (`report-only`) or scoped edits (`edit`), without auto-committing
or closing. Legacy `workspace_route: current` / `in-place` callers follow
[Current workspace](references/current-workspace.md#return-and-acceptance).

### Consumer-owned workspace

Follow [Consumer-owned workspace](references/consumer-owned-workspace.md): carry
the consumer's binding, candidate, and evidence instead of helper receipts/closes;
the parent verifies and records in-place acceptance and leaves final caller
delivery and cleanup to the consumer.
