---
name: ask-agent
description: A delegation skill, not an agent type. Ask native agents to work in the background, continue useful work in the main conversation, and incorporate their results when they return. Use for "ask an agent", named agent roles, parallel delegation, or launch-and-notify work.
version: 0.3.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: prompt-only
---

# Ask agent

Common invocation: “Use the ask-agent skill to ask a reviewer to check
estimate.md. Meanwhile, complete the budget. Incorporate the review when it returns.”

Delegate the user's task through this session's native agents. Do not do the
delegated task yourself or create a script, subprocess launcher, nested harness
CLI, SDK runner, or recurring schedule.
The name `ask-agent` selects this skill; it is not a native worker type.

## Choose the available capability

Use the tools and agent roles actually exposed in this session; the model name
does not determine the tool interface. If native delegation is unavailable,
report that limitation without simulating an agent.

Use an explicitly named installed agent when available. For a descriptive role
such as reviewer or costing agent, use a suitable native role or a general-purpose
worker with that role in its task. Include any role substitution in the final
answer, even if it was already mentioned during dispatch. If the
user requires an exact agent that is unavailable, report it rather than substituting.
Inherit the host's model choice unless the user requests another supported model.

## Launch, continue, and handle completion

1. Give each worker its objective, relevant inputs, allowed actions and required
   output in a self-contained prompt. Start a fresh context, without resuming
   an old worker or copying unrelated conversation history. Explicitly select
   no inherited parent history wherever the native schema exposes that choice.
   If only inherited forks are available, report that fresh delegation is
   unavailable instead of dispatching one. Normal host/project instructions
   may still load; separate contexts do not isolate the filesystem.
   Give workers separate write ownership when needed. Workers may use further
   native delegation when useful and supported; carry the task's actual
   constraints forward and collect those results before reporting completion.
   For repository changes, read [Git integration](references/git-integration.md)
   before dispatch and pass its relevant contract to the worker. Identify the
   actual workspace, contribution, integration target and integrating owner.
   The parent owns integration and acceptance by default; it may delegate their
   execution. A completed worker does not imply its changes have been integrated.
2. Launch in the background by default, using native asynchronous agents and
   explicitly selecting background mode where exposed. Start independent workers
   within host capacity before collecting them. Retain each native handle and
   user-facing task label. Report RUNNING only after launch is confirmed.
   If the host cannot support background continuation, report that limitation;
   do not silently block and call it background work.
3. After native launch confirmation, continue the user's independent work in the
   main conversation before waiting. Keep parent work out of the worker-launch
   tool batch: receive the launch receipt first, then take a useful parent action.
   Do not duplicate the delegated work or invent busywork. Report useful parent
   results as they become ready; do not hold them for an unrelated worker.
   If no independent work remains, acknowledge the running task and let the host
   deliver its completion. Keep any required collection in the same live session.
   Handle new user input delivered to this parent while workers continue.
   Report the requested answer promptly and keep unrelated workers running.
   A queued message is not an answered request; the harness controls when
   queued or steering input reaches this conversation.
4. Include the compact handoff instructions below in each worker's task; do not
   assume a worker inherits this skill. Ask it to report its result and task status: SUCCEEDED if it achieved
   the requested outcome, BLOCKED if required input is missing, or FAILED if it
   encountered an error. A missing required value must not be guessed.
5. Treat native completion notifications as incoming results in this conversation.
   Incorporate the actual worker result when delivered; never predict it from the
   task prompt. A report path is a reference to read, not an already verified
   result. Use the compact handoff procedure before accepting a file-based result.
   If a notification provides only status, retrieve that worker's
   output with the native collection tool. Keep other unfinished tasks pending.
   Use a native blocking wait/join only when the next action needs the result,
   no independent work remains, or the caller needs the invocation kept open
   until collection. Do not exit a headless invocation with required results
   uncollected. Distinguish this explicit join from automatic notification.
   A wait may return early; continue native collection until required workers finish.
   Do not create timers, schedules, shell sleeps, no-ops, polling loops, or output-file
   watchers to wait. Follow the live tool schema and disclose rejected collection
   calls and recovery. If native notification/collection is unavailable, report it.
6. Return each completed task using these fields, in a table or compact list:
   Task; Status; Result or blocker; Native agent type; Role substitution.
   Derive the native type from the actual dispatch. For substitution, name the
   requested descriptive role mapped to that type, or say none. Keep these fields
   in the complete final response after late completion notifications too.
   Treat "worker finished" and "task succeeded" separately. Say all work succeeded
   only if every required task succeeded; otherwise identify the remaining work.
   End with Collection notes: how results arrived (notification or native join),
   any rejected collection request/recovery, and any still-running task.
   Successful task results do not erase collection errors. Keep this synthesis
   concise; link retained deliverables instead of reproducing detailed reports.
   For code changes, also state integration status and the next action/owner.

## Compact result handoff

Prefer compact handoffs without imposing fixed word, line, duration, concurrency
or delegation-depth limits. Let the task and the native harness determine how
much work, evidence and output are needed. Explicit user constraints still apply.

For substantial results, give the worker a unique absolute report path in a
temporary directory that both worker and parent can access. Authorize writing
only that report when the underlying task is otherwise read-only. Do not assume
a local path is shared across hosts, sandboxes or worktrees. If file handoff is
unavailable or writing is forbidden, disclose that boundary and use an available
native artifact or a concise inline result. Tiny answers may stay inline.

Tell the worker to put its findings and supporting evidence in the report.
Begin with a self-contained handoff summary: the assignment and requested
outcome, what was completed, status, key totals or blocker, artifact locations,
and the recommended next action and responsible owner. Include the relevant
current state, checks and unresolved decisions so the parent can reincorporate
the result without remembering the launch conversation. For repository work,
include the Git receipt described in the integration reference. Locate detailed
evidence with headings below the summary; do not copy conversation history.
Finish writing before returning. Prefer a concise final native response with
the task label and a brief assignment reminder, SUCCEEDED/BLOCKED/FAILED,
the outcome or blocker, the recommended next action and owner,
the report path (or explicitly no report), and whether the report is temporary.
When there is no report, include the state and artifact/revision references
needed for that next action inline; say integration is not applicable when so.
Return enough detail to make the result useful; keep bulky evidence in the
report by default instead of duplicating it in parent-directed messages.
Finish normally so the harness delivers this receipt; do not create a separate
notifier or delete the report.
If the required report cannot be written, report that handoff failure honestly.

After native completion or collection, check the assigned report is available.
Start with the summary, then read as much supporting evidence as the next
decision requires. Prefer selective reads and concise verification outputs to
avoid loading irrelevant detail; a full report read is appropriate when needed.
Use native follow-up for clarification when useful, and disclose any remaining
verification limit. Do not treat the worker's success label as verification.
Treat its next-action recommendation as a proposal: check it against current
instructions, workspace state and other contributions before acting. Preserve
pending actions and their artifact/revision references in the parent's existing
task record or retained handoff when they must survive context loss. Do not
delete the only record needed to finish integration or other outstanding work.
If a required report is missing, unreadable or inconsistent, report the collection
problem and use native
follow-up/collection where available; do not invent its contents or silently
replace it with a large inline dump. File existence is not a completion signal:
keep using native notifications/collection, never file polling.

The parent owns cleanup. Delete only its assigned temporary reports, after the
worker has stopped and all required use/verification is complete. Keep a report
needed for unresolved work, another consumer or recovery; disclose that retention.
Preserve durable deliverables and user files. A deleted temporary path is not a
usable final reference. Deleting a file does not remove text already read into
the conversation, so selective reading is essential.

An explicit request to wait overrides the background default: collect the required
results before the requested response, using native foreground or wait facilities.
Do not promise survival across session exit/restart or notifications outside the
current conversation. If the host cannot retain/retrieve work after returning
control, disclose that boundary rather than promising a later callback.
Keep internal handles private when the host requires it. On a cancellation
request or deadline, use native cancellation. Report CANCELLED only when the
current execution is confirmed stopped; otherwise report that stopping is
unconfirmed. Cancellation stops the current task; the host may retain the
worker context. Do not resume that context for a fresh delegation.

Host hints; follow the live schema when it differs:

- Claude Code: Agent with run_in_background=true when exposed; use native task
  completion notifications. Choose a type that creates a fresh task, not the
  native fork type that inherits parent history. Where agents always run in
  the background,
  omit unavailable mode arguments. In an interactive session retained between
  turns, return an ordinary interim response to hand control back. In headless
  mode, keep the invocation open through native notification/collection.
  Do not call ScheduleWakeup or another timer/no-op to manufacture a later turn.
- Grok: spawn_subagent with background=true; omit resume_from. In a headless
  invocation that requires the result, report useful parent work first, then call
  get_command_or_subagent_output with the pending task_ids and a positive timeout_ms
  before ending the parent response. An idle completion notice can enter history
  without a completed parent follow-up; forwarded child text is not parent collection.
  Incorporate the retrieved result and report that collection used a native join.
- Codex: native asynchronous spawn; choose no inherited history where exposed,
  such as fork_turns="none". Continue parent work before native wait/completion collection.
- OpenCode: native task with background=true where exposed. For a fresh worker,
  omit task_id entirely; it is a resume handle, not a task label. Never invent
  that handle; retain the ID returned by the actual native launch. Keep the
  parent session alive for completion. Native background availability and
  session lifetime depend on the installed host; report unsupported modes.
