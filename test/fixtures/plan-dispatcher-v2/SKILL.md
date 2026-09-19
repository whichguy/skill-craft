---
name: plan-dispatcher
description: >-
  Use when executing or resuming an agreed dependency graph with one main
  dispatcher and parallel native workers: claim ready steps, preserve launch
  state, collect result evidence, verify outcomes, and identify successors.
  Planning belongs to Backchain or the caller; this skill executes the plan.
license: MIT
metadata:
  version: 0.1.1
  author: Backchain
  platforms:
    - linux
    - macos
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
When using Ask-Agent for repository changes, read its Git integration reference
before launch and pass its relevant contract to each worker. The dispatcher owns integration
ordering and acceptance; it may delegate integration execution.

Bind `scripts/dispatch.js` to the absolute directory containing this loaded
SKILL.md, not the current project, PATH or another installation. Requires Node.js
18+ and a trusted local filesystem. The complete package is copyable; it needs
no author checkout. Read [the CLI contract](references/protocol.md) when starting
or recovering a run. Every helper call reloads durable state.

## Execute

1. Use an agreed graph with per-step task, ready and done contracts. When the
   input is Backchain JSON, use its checkout exporter if available; otherwise
   preserve the caller's explicit dependency and contract information in the
   documented format. Never discard unresolved needs to make a graph executable.
   Choose one absolute run directory shared by all workers, outside their
   workspaces, and a unique dispatcher owner. Initialize once; resume with `next`.
2. `next` returns dependency-ready IDs and recovery actions. Check readiness
   facts, including initial-world inputs, native capacity and shared resources.
   `claim` selected IDs. A claim reserves work but does not mean an agent exists.
3. Prepare a separate worktree/workspace per concurrent worker and an immutable
   readiness artifact describing the facts actually checked. Git workers use
   external sibling worktrees: never place a checkout inside another checkout.
   Record the exact initiating checkout/branch and revision as the return target,
   even when it is a linked worktree. Name the integrating owner, worker base,
   contribution scope and synchronization policy in the readiness evidence and
   worker handoff. Carry required uncommitted inputs explicitly; a worktree from
   HEAD does not contain them. Supply the context
   to `start`. Native start input is `{owner,attempt,context}`; only its first
   `action: launch` response authorizes calling ask-agent with the complete
   returned packet. A serial caller instead supplies
   `executor:{kind:"main-context",id:"stable-id"}` in that same atomic start
   request. Its first response is `action: execute`, records no native handle,
   and records the caller's main-context execution attestation for the bounded
   task. The helper cannot authenticate a live conversation, so a recovery or
   takeover dispatcher must explicitly confirm it may resume that identity. A
   `reconcile` response never authorizes a new launch or a second execution.
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
   explicit task constraint may prohibit it. Record the confirmed native handle
   with `launched`, announce the assignment and the parent's next action, and
   retain a parent-owned pending-job entry with the label, handle, last observed
   status and returned report/result when available. Continue useful parent work.
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
   For `action: execute`, do the task in the current main conversation instead.
   Do not call ask-agent, launch a native worker, wait for a native handle or
   fabricate one. Preserve the returned executor identity on recovery and attest
   it remains appropriate before resuming; `next` returns `resume` while task work
   remains and `verify` after its receipt exists.
5. A worker writes its result/envelope at the packet's concrete `outputs` paths,
   publishes a `report` using the returned argv, and returns those paths plus
   SUCCEEDED, FAILED or BLOCKED with a brief assignment reminder and next action
   and owner. Substantial results begin with a self-contained handoff summary;
   repository results include the Git receipt, exact contribution/target
   revisions and integration state. The report writes only its inbox receipt.
   On native return, acknowledge the task label and reported outcome, update the
   pending-job entry and distinguish that return from verification or acceptance.
   Read the assigned handoff and independently check the task's done contract,
   relevant tests/artifacts and actual commit identity. Record the verifier's
   evidence and `settle` the exact receipt. Native execution requires verifying
   the worker stopped before settlement releases resources, including delegates.
   For a main-context execution, `confirmed_stopped` means all task-owned commands
   have finished; it does not mean the main conversation terminated. Independent
   verification is a distinct checking phase with actual tests or inspections;
   it need not use a separate agent. Only accepted results unlock successors. Before integrating, recheck the target
   revision and reassess changed targets; serialize updates to that target and
   verify the combined behavior. Worker completion alone does not prove
   integration.
6. Use each settlement's refreshed `ready` list immediately. It may offer multiple
   successors and still-ready work deferred earlier. Check readiness/resources,
   then claim as many eligible IDs as current native capacity permits; keep the
   rest pending. Do not wait for an entire wave or reschedule accepted work.
   After a confirmed-stopped retry or resume, refresh with `next` as well.
   No ready IDs is not completion while work is active, blocked or unresolved.
   See [completion-driven dispatch](references/protocol.md#completion-driven-dispatch).
   A dependent step receives accepted supplier evidence.
   If it needs integrated code, depend on an explicit merge-and-verify step and
   use that accepted commit as its base. Completion in an isolated branch does
   not put the code into another worktree.
7. Finish when `next.complete` is true and the required integration/verification
   outcomes have evidence. Report integration status and next action/owner;
   retain handoffs needed for unresolved work or recovery. Report failed or unresolved work honestly. Execution
   does not extend authorization for publication, deployment or external effects.

## Recover

Use `next` and `packet` to rehydrate; do not reconstruct from conversation memory.
An unsent claimed attempt can start. A saved intent without a confirmed handle
must be reconciled through native inventory and the full dispatch identity before
any retry. Hosts without reliable lookup leave that outcome unknown. An attempt
with `executor.kind:"main-context"` is already entered: resume it in the current
main conversation, or verify its saved receipt, without spawning or waiting on a
native worker.

Retry only after confirming the old worker stopped and inspecting its effects;
the helper creates a fresh attempt on the next claim and rejects stale reports.
Takeover requires confirming the old dispatcher stopped; keep active worker
handles and use a new, never-reused owner ID. The helper does not verify these
attestations or cancel native work. Orphan locks are never stolen by age; see
[recovery details](references/protocol.md#recovery-and-limits).

For a busy receipt write, preserve the exact envelope and return its paths to
the parent for publication retry. Do not rerun the task. Saying “I'm done” alone
does not call this skill, accept work or wake a lost parent conversation.

See [host evidence](references/host-matrix.md) before claiming portable native
recovery. Saved state does not establish survival or notifications across sessions.
