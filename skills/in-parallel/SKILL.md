---
name: in-parallel
description: >-
  Use for "in parallel" or when one goal should be divided among independent
  native agents and returned as one verified aggregate. One coordinator owns
  decomposition, progress, acceptance, and optional Git delivery.
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: mixed
---

# In Parallel

Turn one user prompt into independent native-agent work and one aggregate
result. The coordinator reasons about decomposition and synthesis; the bundled
Agent Harness scripts compose the selected Ask Agent compact task interface
with Plan Dispatcher. Ask Agent remains independently usable. Plan Dispatcher
is the only durable execution-state authority; this skill adds no model
launcher or second scheduler.

## Select inspection or a new batch

For a status-only request about existing work, use its owning workflow's
read-only interface in the current context and return the findings directly.
Do not initialize a batch or create a coordinator for that inspection.
Recorded status is not live native status: query the owning host's inventory
when actual agent activity is asked for.

Existing Dispatcher and ShipLoop runs retain their owner. Their dependency
graphs may be inspected for context, but must not be adopted, reconstructed,
restarted, merged, or replaced by this skill. Dependent work belongs to the
workflow that owns its sequence.

A new batch currently requires an existing Git workspace and the selected Ask
Agent and Plan Dispatcher packages. If a dependency or host capability is
missing, report the gap; do not create a repository, guess an ambient package,
or silently substitute a provider or workflow.

## Initiating context: pass one goal to one coordinator

Read [host guidance](references/hosts.md) to choose a supported route. Start
**one fresh coordinator** with this selected skill's absolute `SKILL.md` path,
the user's prompt, repository locator, relevant current learnings, constraints,
and existing approvals or declines. Carry requested worker concurrency, provider/model,
workspace, return behavior, and checks. Do not require the user or initiating
context to author task JSON; the coordinator writes the request.

Tell the recipient: **You are the sole coordinator. Run In Parallel in this
context; do not create another coordinator.** If already assigned that role,
perform it here instead of delegating it again. Do not prepare a separate Ask
Agent worktree for the coordinator. The initiating conversation retains one
coordinator handle, continues useful independent work, and relays the evidenced
aggregate; it does not separately dispatch the leaf workers.

## Coordinator: decompose, execute, and verify

Read [the coordinator contract](references/contract.md) and the selected route
in [host guidance](references/hosts.md). Bind the absolute Ask Agent and Plan
Dispatcher cards actually selected by the host. Their contracts own worker
workspace and return rules and durable task state. Use
[examples and component boundaries](references/usage.md) when useful.

Inspect the target before choosing independent assignments. For implementation,
use disjoint deliverables and write scopes. For analysis, choose distinct
questions or perspectives whose findings can be assessed separately; review
does not authorize edits. Give each assignment a concrete expected result. Map every requested outcome to
one or more task IDs before launch and review that coverage against the original
goal. Preserve the full task list: a worker cap never truncates the work queue.

Interpret “use at most N agents” as at most N concurrent **workers**, excluding
the one coordinator. Set request `capacity` from that explicit positive integer.
Otherwise the helper defaults to at most five workers, or fewer when there are
fewer tasks. A seven-action goal with capacity three still has seven tasks and
seven fresh worker contexts over its lifetime. Do not pool or resume a completed
worker for a new action. A known lower host limit may reduce concurrency; state
that limit instead of silently raising the user's cap. Use the smallest useful
set of independent assignments that covers the full goal.
Worktrees do not make overlapping deliverables independent: keep overlapping
edits with one writer or the workflow owning their dependency sequence.

Preserve the explicit workspace choice. Without one, Ask Agent defaults to the
current workspace: report-only readers may run in parallel, but edits require
one exclusive writer and capacity one. If parallel editing is required and
isolation has not been selected, ask whether to use worktrees while continuing
read-only scoping. Do not silently create worktrees or imply shared writers are
isolated. Select edit/apply, edit/return-only, report-only, or worktree ephemeral
before launch; follow the linked contract for preservation, checks, and errors.
For report-only tasks, carry no-write inspection constraints into each worker
brief as well as coordinator checks. Avoid incidental source artifacts, such as
Python import caches (use `python -B` or disable bytecode writes), and retain
verification output outside the source workspace. A clean Git status alone
does not prove that ignored files stayed unchanged.

Use this selected package's `scripts/harness.py` for the recorded lifecycle.
The coordinator alone launches task workers through live native host tools,
records actual handles, collects terminal results, independently verifies them,
and records acceptance. Collect any descendants that the host permits workers
to start before the final handoff. The helper prepares and records; it never
launches a model. A saved result does not prove native completion, and collection
does not imply acceptance.

Announce each ready batch once. Where supported, issue asynchronous native
launch calls together before waiting; do not interleave inspection or report
writing between launches. Keep worker prompts exactly as prepared and record
returned handles promptly. Consolidate routine progress; return promptly for
a real blocker. An uncertain launch requires native inventory reconciliation,
never a duplicate launch based on elapsed time or a saved file. `status`
reports recorded Dispatcher state only, not a live host check or restart.

Consume the planned backlog as a finite, generator-style queue: `dispatch`
returns only the next items that fit available slots. Each item gets one fresh
native agent execution; workers never pull another item or become a reusable
pool. Plan the full backlog before starting, rather than adding discovered work
to a running batch. Dispatcher retains the backlog and attempts across calls;
do not introduce a separate in-memory queue or scheduler.

Drain the entire queue through the same Dispatcher run. After a native worker
returns, collect, verify, and accept or reject its result, then call `dispatch`
again to fill available slots while other workers continue. Do not wait for an
entire batch to finish before refilling a free slot. Launch only newly
returned assignments; never replay an earlier launch list. Pending tasks,
unconfirmed launches, verification, and retry actions remain visible in status.
`NO_NEW_LAUNCH` means no slot or eligible action is available now, not that the
goal is complete. Keep monitoring owned workers and following the recorded next
actions. If unresolved work cannot advance, return an explicit incomplete
outcome with the remaining task IDs; never silently drop them or start a new
batch to bypass the blocker. Call `finish` only after all required tasks are
accepted, not merely when the first wave returns or no worker is currently active.

## Return one aggregate

After actual native collection and independent verification, answer the
original prompt with a synthesis of findings or combined changes. Remove
duplicate findings, retain meaningful worker/evidence attribution, and identify
disagreements, assumptions, and unresolved questions. Resolve disagreements
from evidence where possible; agent vote counts do not establish correctness.

Reconcile the aggregate against the original outcome-to-task mapping: include
every planned task exactly once using its accepted current attempt, and check
any requested combined totals or artifacts independently. An omitted requirement
keeps the overall goal incomplete even if every task in an incomplete plan passed.

Include each assignment's accepted, rejected, blocked, or incomplete outcome;
the combined delivery/check result; remaining work; and evidence and retained
worktree locations. Partial findings may be useful, but missing or failed
required work keeps the batch incomplete. Report successful code delivery only
after required acceptance, integration, and combined checks pass. Do not hide
coordinator failures or replace evidence with worker claims.

After successful worktree edit/apply delivery and combined checks, `finish`
closes each integrated worker worktree through the selected Ask Agent helper.
Confirm workers and any delegates have stopped before finish. Report each
cleanup outcome; a refused close remains cleanup-pending without undoing the
integration. Keep branches, commits and durable evidence. Failed, unmerged,
return-only and ephemeral worktrees remain available. Current source changes
do not migrate existing pinned runs; use their original packages and evidence.
