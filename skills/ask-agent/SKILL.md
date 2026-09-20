---
name: ask-agent
description: A delegation skill, not an agent type. Ask native agents to work in the background, continue useful work in the main conversation, and incorporate their results when they return. Use for "ask an agent", named agent roles, parallel delegation, or launch-and-notify work.
version: 0.6.1
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: mixed
---

# Ask agent

Delegate through this session's native agents. The bundled helper owns Git
workspace preparation and eligible cleanup; the native host owns execution and
return; the parent owns acceptance and integration. `ask-agent` selects this
skill, not an agent type. Do not implement another model launcher, SDK client,
subprocess harness, scheduler, or file watcher to simulate native delegation.

Default to a fresh background worker while the parent continues useful work.
An explicit request to wait takes precedence. Each invocation adds to the
initiating conversation's pending work; it does not replace earlier jobs.

A request to change repository code includes bringing the verified contribution
back into the designated caller/integration checkout by default. The parent
performs that integration and validates the combined result before reporting the
overall request SUCCEEDED. A successful worker return alone is not completion.
If integration is blocked, report the overall blocker, worker outcome and retained
locations explicitly. An explicit review-only or return-without-integration request
overrides this default; do not turn ordinary delegation into an unrequested
approval step. Follow the declared delivery mode and preserve caller dirty state.

## Select the route before preparing

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

Inherit tools, skills, permissions and execution facilities where the host
supports it. Do not independently add tool restrictions, read-only modes,
model downgrades, or fixed depth/concurrency/output limits. Scope and write
ownership still apply. Some hosts filter child tools; disclose differences.
A worker may request an authorized parent-only operation through native
messaging when available, or use further native agents with the same workspace
and handoff constraints. It must collect its delegates before returning.

## Prepare, launch, continue, collect

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

## Result and continuation contract

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
