---
name: ask-agent
description: A delegation skill, not an agent type. Ask native agents to work in the background, continue useful work in the main conversation, and incorporate their results when they return. Use for "ask an agent", named agent roles, parallel delegation, or launch-and-notify work.
version: 0.7.4
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: mixed
    capabilities:
      - ask-agent/consumer-owned-workspace/v1
---

# Ask agent

Delegate through this session's native agents. The bundled helper owns Git
workspace preparation and eligible cleanup; the native host owns execution and
return; the parent owns acceptance and integration. `ask-agent` selects this
skill, not an agent type. Do not implement another model launcher, SDK client,
subprocess harness, scheduler, or file watcher to simulate native delegation.

The helper-managed workspace route is the default for delegation. Historical
experimental cards are test fixtures, not alternative supported workflows. A
consumer-owned workspace is an explicit invoking-consumer contract, never an
automatic interpretation of an existing worktree, a speed request, or a request
for fresh context.

Default to a fresh background worker while the parent continues useful work.
An explicit request to wait takes precedence. Each invocation adds to the
initiating conversation's pending work; it does not replace earlier jobs.

A helper-managed request to change repository code includes bringing the verified
contribution back into the designated caller/integration checkout by default. The
parent performs that integration and validates the combined result before reporting
the overall request SUCCEEDED. A consumer-owned route instead has in-place parent
acceptance followed by its consumer's separately owned final caller delivery. A
successful worker return alone is not completion. If integration or final delivery
is blocked, report the overall blocker, worker outcome and retained locations
explicitly. An explicit review-only or return-without-integration request overrides
the helper-managed default; do not turn ordinary delegation into an unrequested
approval step. Follow the declared delivery mode and preserve caller dirty state.

## Select the route before preparing

This card declares `ask-agent/consumer-owned-workspace/v1`. Select exactly one
route before any helper preparation or native dispatch:

- **Helper-managed** is the default. It uses the existing helper-created
  snapshot, one of `patch`, `commits`, or `report-only`, and the procedures below.
- **Consumer-owned** requires an invoking consumer to explicitly set
  `workspace_route: consumer-owned` and `delivery_mode: in-place`, and to supply
  the complete workspace/ownership contract in
  [Consumer-owned workspace](references/consumer-owned-workspace.md). Its worker
  writes in the consumer's already-bound candidate; helper delivery modes do not
  apply.

An ordinary invocation that does not select consumer-owned uses the
helper-managed default. A consumer that explicitly requests consumer-owned but
lacks this card capability or any required contract field stays pending with its
available locators. Do not silently switch that incomplete consumer request to
the helper-managed route, shared writes, an inherited context, or a second
worktree.

The currently declared consumer binding is ShipLoop navigator-v3's whole-skill
Improve child. It supplies one fresh executor for the complete bound Improve
invocation; standalone Improve dispatch remains unchanged. This is a Codex native
pilot with evidence from bounded native fixtures. Earlier helper-managed host
evidence does not qualify this composition on Codex, Claude, Grok, or another
host.

Use the live native schema, not the model name or a presumed capital-`Task` API.
Read the matching route in [Host capabilities](references/host-capabilities.md).
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
model downgrades, or fixed depth/concurrency/output limits. Scope and write
ownership still apply. Some hosts filter child tools; disclose differences.
A delegated coding skill such as Improve retains normal coding-agent capability,
including deployment and other external operations already authorized for its
task. A fresh context does not revoke that authority or require renewed approval.
A worker may request an authorized parent-only operation through native
messaging when available, or use further native agents with the same workspace
and handoff constraints. It must collect its delegates before returning.

## Carry current learnings inline

Before either route launches a fresh worker, the invoking parent distills the
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

## Helper-managed default: prepare, launch, continue, collect

The six steps in this section apply only to the helper-managed default. They do
not apply to a selected consumer-owned workspace; use its complete route
reference instead.

1. **Prepare through the skill.** Read [Workspace operations](references/workspace-operations.md)
   and [Git integration](references/git-integration.md). Obtain the host-selected,
   absolute logical `SKILL.md` path, bind its helper, and run `identity --skill-card`
   before `prepare`. Record the returned logical and resolved card/helper paths,
   skill version, and both SHA-256 values with the pending job. This proves the
   selected card and executing helper are one package; it does not discover a skill
   from the task cwd, `PATH`, or a cache. Stop on identity failure; do not call
   `prepare`. Coordinate source writers, then call
   `prepare --source` with the actual caller checkout, including a linked worktree.
   The helper creates and verifies a new workspace carrying staged, unstaged,
   and non-ignored untracked inputs. The caller must not supply a worktree or
   reproduce the Git recipe. Do not begin independent caller edits until the
   snapshot returns. Keep the verified receipt and baseline in the pending job.
   Immediately before dispatch, record `inspect --phase prepared --receipt ...`
   for each receipt and stop if its inherited baseline has drifted. For a batch
   sharing the same snapshot, prepare each separate receipt while writers remain
   quiescent, verify every prepared state, then launch the batch.
   Non-Git or unsupported state is a concrete limitation, not permission to use
   an empty/default-branch checkout. An explicit ban on all filesystem writes
   also prohibits setup; an ordinary review permits isolated setup and reports.

   Orchestrated Git work requires this managed 0.6+ flow. The parent checks the
   selected helper's `capabilities --skill-card` response and `identity` before
   preparation; an older caller-worktree contract or an unsupported newer helper
   is not a fallback. Serial orchestration uses the same workspace helper while
   executing the bounded task in the main context instead of launching a worker.

   A coordinating Dispatcher or ShipLoop parent may perform this preparation
   before freezing its execution context. Continue that same attempt with the
   selected package identity and verified receipt it already recorded; compare
   the receipt's worktree with the frozen context workspace. Do not run a second
   fresh preparation when the parent grants native launch. This is continuation
   of this skill's preparation, not adoption of an arbitrary caller-created
   worktree. A different attempt requires a fresh receipt.

2. **Give a fresh worker a complete assignment.** Put the objective, relevant
   inputs, allowed actions, expected output, recorded package identity (logical
   card, resolved card/helper, version, and card/helper SHA-256 values), and the filled
   [delivery clause](references/git-integration.md#reusable-fresh-worker-launch-clause)
   directly in the native launch prompt. Do not create a prompt transport file.
   Choose `patch`, `commits`, or `report-only` before launch. Read
   [Result handoff](references/result-handoff.md) for the report and return
   contract. Omit resume handles and explicitly exclude inherited conversation
   history where supported; if only inherited forks exist, report the limitation.
   Normal host/project instructions may still load.

3. **Bind and verify the workspace.** Use native launch cwd when exposed;
   otherwise follow the host's explicit operation-directory recipe. Do not add
   another native-created worktree after the helper has prepared one. Require
   the worker to run `check-context --receipt ...` from its assigned operation
   directory before task work and to stop on failure. This checks real process
   cwd and Git root; reading a receipt or using `git -C` does not set shell cwd.
   Set directory scope on every subsequent command and absolute paths for file
   tools. Include the recorded package identity in the worker's self-contained
   return so the parent can prove which selected package created the workspace.
   Disclose operation-only binding; it is not native startup binding or
   operating-system isolation. Follow the target's project instructions.

4. **Launch and continue.** Immediately before every launch/retry/follow-up
   turn, publish its task label, assignment and current completed/pending state.
   A batch notice may name multiple tasks. Select native background mode where
   exposed; confirm launch before reporting RUNNING. Retain the native handle,
   receipt, delivery mode and route. Start independent workers within host
   capacity before collection. After launch confirmation, take useful parent
   action in a separate step; do not duplicate the delegated work or invent
   busywork. Handle new user input while other tasks remain pending.

5. **Receive native results.** Read [Native lifecycle](references/native-lifecycle.md)
   before waiting. Keep any required collection in the same live parent session.
   A headless process must not exit with required results uncollected. Use native
   notification or wait/join; distinguish them in reporting. A later resume is
   recovery, not automatic delivery. Immediately announce every return, including
   failures, before unrelated work or dispatch, and update the pending jobs.
   Fetch actual output if the notification provides only status. A worker's
   success label or an existing result file is not independent verification.

6. **Accept and preserve.** Read the returned handoff and required artifacts.
   Inspect the workspace with its declared delivery mode, verify and integrate
   the worker-only contribution: an ordinary code-change request authorizes this
   integration. If the caller explicitly requests code returned unmerged, or
   code integration is blocked, return the ready-to-use handoff and retain the
   worktree. Report-only work requires consumption of its results. Archive reports
   and call `close` only when
   the worker/delegates/consumers are stopped and acceptance is complete. The
   acceptance and close are per receipt; one worker's return or accepted result
   does not establish another worker's completion or acceptance. The
   helper retains work without valid acceptance. Keep blocked or cancelled work
   and give its next action. Use retained artifact paths after cleanup.
   Under a dependency dispatcher, settle the verified attempt and refill safe
   ready capacity before cleanup; retain this receipt as cleanup-pending until
   its owning helper confirms close. A cleanup refusal does not undo acceptance.

## Result and continuation by route

### Helper-managed default

Workers finish normally with their task label, assignment reminder,
SUCCEEDED/BLOCKED/FAILED, result or blocker, observed workspace, receipt,
delivery mode, selected-package identity (logical card, resolved card/helper,
version, card/helper SHA-256 values), context-check output or tool locator,
handoff/report paths, and next action/owner. They leave their
worktree intact. Return enough detail to be useful; put bulky evidence in reports.
Do not guess missing values or bury workspace and lifecycle information only in
a report the parent may not open.

Return the self-contained [caller handoff](references/result-handoff.md#caller-facing-handoff)
inline in both the worker return and the parent's final response. It names the
selected package identity, actual worktree and branch, outcome and checks, exact patch or ordered commit
SHAs, target checkout, integration state, and concrete integration/retention
directive. The caller must be able to review or integrate using that response
without opening a helper receipt, baseline JSON, or internal state directory.
Internal evidence may be linked separately; it is not the integration interface.

The parent's final result also includes, for each task: Task; Status; Result or
blocker; Native agent type; Role substitution; actual workspace; retained
references; integration/retention/removal state and next owner. Derive the type
from actual dispatch. Distinguish worker completion, verified success and
integration. End with collection notes: notification or join, rejected calls
and recovery, and any remaining pending work. Keep this complete after late
returns too; internal handles stay private when the host requires it.

Honor caller-supplied continuation instructions. Carry the exact continuation
and helper receipt in the worker's final native response without executing the
parent's continuation in the worker. When a timed return is explicitly requested,
use the separately available **prompt-timer** skill, resolved from the host's
selected skill context. Ordinary delegation does not require that skill or a
timer. Do not promise notification after the current parent session exits.

### Consumer-owned workspace

Use the in-place handoff in
[Consumer-owned workspace](references/consumer-owned-workspace.md). It carries
the consumer's binding, candidate and evidence instead of a helper receipt,
patch, commit range, or helper close outcome. The parent verifies the returned
edits and evidence, records acceptance, and then lets the consumer perform its
separate final-delivery continuation. The worker never executes that continuation
or consumer cleanup.
