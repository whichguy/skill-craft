# Native lifecycle and pending work

Read before launching background work. The host owns execution and completion;
this reference governs the parent conversation, not a new scheduler.

This lifecycle is shared by the helper-managed default and the selected
consumer-owned route. The latter adds its consumer-specific workspace, owner
record, recovery, acceptance, and cleanup contract in
[Consumer-owned workspace](consumer-owned-workspace.md); it does not use helper
receipts as native lifecycle evidence.


Keep a lightweight parent-owned record in the existing task state: task label,
native handle, assignment, last observed status/update, and result/report plus
next action when available. Track each invocation's actual worktree, inherited
baseline and retained-file/merge/removal state separately, even when labels
repeat. Native handles control execution; this record is
for coordination and recovery, not another scheduler. Refresh it from actual
native events/collection. Do not infer progress from elapsed time or file existence.

For consumer-owned work, the consumer's `host-owner.md` is that durable
parent-owned coordination record. Append launch intent before dispatch, then
handles, delegate and stop/collection evidence as known; only the parent writes
it. An interrupted launch remains possibly launched until native evidence resolves
ownership, so it blocks a replacement writer. Read the complete consumer route
before recovery; do not reinterpret a missing record as proof that no worker ran.

While the parent is only waiting, give a concise status about every two minutes
unless the harness is already providing equivalent visible progress. Summarize
all pending jobs together, what is known, and what is being awaited. Say that no
new detail is available when that is the truth; do not invent percentages or
interrupt useful worker execution to demand a progress report. The mandatory
before-launch and on-return notices apply independently of that interval;
blockers and user requests also deserve prompt updates.

Before entering a waiting-only state, select and use an available native status
mechanism. Completion-only notifications cannot provide periodic updates; do not
assume workers will finish before the next update is due.

- Use native wait/collection with an observation timeout around the requested
  cadence. On timeout, emit a visible combined status before collecting again;
  updating an internal record alone is not a user-facing notice. The timeout
  ends that observation wait, not the worker's execution.
- If periodic collection is unavailable but the host exposes a native
  current-session wakeup, schedule one parent status check with a real prompt
  and the requested cadence before becoming idle. At the wakeup, report observed
  pending state and schedule the next check only if jobs remain. Clear owned
  pending wakeups when the queue empties where supported. A wakeup is not worker
  completion and never substitutes for collecting actual results.
- If neither mechanism nor equivalent visible native progress is available,
  announce that periodic updates are unavailable before becoming idle. Continue
  native completion collection and launch/return notices; do not silently wait
  and later call an observed long silent interval unobserved.

Do not create external automations, custom timer scripts or one timer per worker. Timing is approximate and subject to host delivery. Do not
promise notifications after session exit or fabricate periodicity with busywork.
Respect a user request to change the cadence or stay quiet. Keep pending state
and unresolved handoffs available when the parent must recover its context.


## Waiting, cancellation and session lifetime

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
