---
name: plan-dispatcher
description: >-
  Use when executing or resuming an agreed dependency graph with one main
  dispatcher and parallel native workers: claim ready steps, preserve launch
  state, collect result evidence, verify outcomes, and identify successors.
  Planning belongs to the caller; this skill executes the plan.
version: 0.6.7
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

The main conversation is the sole dispatcher: bind `scripts/dispatch.js` to the
absolute directory of this loaded `SKILL.md` (requires Node.js 18+; copyable
package, no author checkout), and follow each response's `instruction`, exact
`next_argv`, and `actions` — never derive schedules, recovery work, or
successors from prose or conversation memory. Native workers run bounded tasks
and return evidence (an explicitly serial caller may run one task in its current
conversation via `executor: {"kind":"main-context","id":"..."}` at capacity 1).
Full schemas and state rules live in [the protocol](references/protocol.md).

## Route & profile selection

- **Default helper-managed profile:** Before execution, bind the selected
  `ask-agent` card and run `capabilities --skill-card ABS` (`shiploop-chain-ask-agent-managed-worktree/v1`
  with `helper-managed-worktree`, `prepared-inspection`,
  `returned-commit-delivery`, `fingerprint-bound-close`, and
  `ignored-output-report`; never infer compatibility from version numbers) plus
  unchanged `identity --skill-card ABS`. For every Git task, explicitly select
  Ask Agent's helper-managed route (it is not Ask Agent's default) and complete
  helper preparation before freezing dispatcher context; non-Git work omits
  managed workspace preparation.
- **Compact profile (`source.agent_harness` == `{"schema":"agent-harness/v1","ask_agent_interface":"compact"}`):**
  The coordinator owns the run from `init` without taking over ShipLoop callbacks.
  Per claim, prepare one compact `ask-agent` task packet, keep its path/hashes,
  launch with its emitted prompt/workspace unchanged (worker runs `worker-start`
  and `worker-finish`), run `verify-return` after native collection, and then
  write/publish the Dispatcher report (`report` + `next_argv`).
- **Scope sharing & planning context:** Omit `read_only` for write scopes; set
  `context.read_only: true` + `write_scope: []` for read-only work (two active
  attempts may share a workspace only when both set `read_only: true` on the same
  canonical path and distinct resources). When ShipLoop supplies immutable planning
  artifacts, check `capabilities` for `shiploop-planning-artifacts/v1` before
  passing `planning_context: {path, sha256, source}`; conflicting planning facts
  stop affected work and report to the parent without changing the graph.
  Optionally run `validate-graph INPUT.json` (`graph_validation: execution-graph/v1`)
  before saving an immutable binding. See
  [Ask-Agent preflight](references/protocol.md#ask-agent-compatibility-and-managed-git-preflight)
  and [immutable planning context](references/protocol.md#immutable-planning-context).

## Progress & native boundary status

Use the script's returned `progress` (`completed`, `active`,
`awaiting_verification`, `pending`, `blocked`, `failed` plus `counts.remaining`),
refreshing via `next_argv` at continuation boundaries rather than reconstructing
categories from history; see
[categorical progress](references/protocol.md#categorical-progress). Note that
`pending` includes dependency-ready work (use `actions`, not `dependency_ready`),
`active` includes unconfirmed `launching` work, and `awaiting_verification`
remains unaccepted until `settle`.

Write concise Markdown status updates at every native-agent boundary grounded in
returned facts (no invented steps, percentages, or ETA, and no dumping internal
protocol IDs unless diagnosing an issue):

1. **Right before every native launch, retry, or follow-up turn:** identify the
   assignment and state that it is launch intent until confirmed.
2. **On every native return (including failure/block/cancel):** report the outcome,
   pending dependencies, and explicitly state that a worker return is not parent
   acceptance until verified and settled. Announce whole-run completion only when
   `next` reports `complete: true`. Cadence/native notifications never replace
   boundary updates, and a `report` returns control to the parent rather than
   ending the run.

## Execute

1. **Initialize or resume:** Pass the agreed per-step `task`/`ready`/`done`
   [graph](references/protocol.md#graph) (never stripping unresolved dependencies),
   an absolute `RUN` dir outside worker workspaces, a unique dispatcher owner,
   and optional `planning_context` / `capacity` (`init` once; `next` to resume).
2. **Claim ready slots:** Follow `next_argv` and exact `call` templates
   ([exact calls](references/protocol.md#exact-calls)). Verify external inputs,
   shared resources, `planning_context_check`, and available capacity (serial
   `main-context` = `1`), then claim as many eligible non-deferred candidates as
   safely fit capacity — never invent or drop eligible slots arbitrarily.
3. **Prepare context:** For non-compact Git work (including `main-context`),
   run Ask-Agent `identity`, `capabilities`, quiescent `prepare --source <actual
   initiating checkout>`, and `inspect --phase prepared`, storing the exact
   receipt and return target in immutable readiness/pending-job records before
   freezing `context.workspace` and calling `start` (non-Git uses generic
   workspace/readiness). `start` emits `action: launch` for native workers or
   `action: execute` (no native handle) for `executor.kind: "main-context"`.
   `packet`, `check-context`, and `reconcile` never authorize launch or acceptance.
4. **Launch or execute bounded work:** Give fresh native workers the complete
   packet unchanged beside a compact **Current learnings** bullet block (or
   explicitly state none apply; keep parent launch/collection prose out of the
   worker packet), default to the broadest general-purpose agent keeping host
   tools/permissions (disclose host filtering), and record confirmed handles with
   `launched`. Workers verify `check-context --receipt` in their operation
   directory, check planning artifact hashes if present, stay within write scope,
   collect any permitted sub-delegates, and drive every `definition_of_done` item
   using `Confirm by:` without installing tools or editing checks: rerun all checks
   in one pass after the last edit and stop on `SUCCEEDED`, `BLOCKED` (proven
   unachievable per [exit criteria](references/protocol.md#exit-criteria)), or
   `FAILED` (still failing after 3 fix attempts). Wait via native timed
   collection/wakeup per Ask-Agent guidance (no custom timers or file polling).
   In `main-context` (`action: execute`), follow the same preparation check and
   `definition_of_done` flow in the current conversation, ending the bounded task
   phase by returning the `report` response (with `next_argv`) to the dispatcher.
5. **Report, verify, and settle:** Workers write their result artifact
   (`criteria`, `discrepancies`, `recommendations`, self-contained handoff summary
   with Git receipt/revisions), run the exact `report` argv to publish only the
   inbox receipt, and return to the parent without following `next_argv`. The
   parent independently checks every `definition_of_done` item, integrates and
   verifies returned Git contributions (confirming native workers stopped first,
   or all task-owned commands finished for `main-context`), preserves findings in
   parent handoffs, and calls `settle`
   ([verification & settlement](references/protocol.md#parent-verification-and-settlement)).
   Treat proven-unachievable items or missing required confirmations as blocked
   for planning (`verification.disposition: "replan", passed: false` — see
   [replanning](references/protocol.md#replanning)); settle fixable failures without
   `replan` to receive an unlimited `retry` action. When ShipLoop owns cleanup,
   let ShipLoop's callback close or retain accepted/superseded workspaces.
6. **Advance on completions:** Follow `settle` -> `next_argv` -> claim/start
   eligible newly unlocked and previously capacity-deferred steps immediately (no
   whole-wave barrier; see
   [completion-driven dispatch](references/protocol.md#completion-driven-dispatch)).
   Dependent steps requiring integrated code must depend on a merge-and-verify
   step rather than isolated branch completion. Report concrete blockers when no
   slot can launch; finish only when `next` returns `complete: true` with verified
   integration/evidence (execution never authorizes publication/deployment).

## Recover

Rehydrate strictly from `next` / `instruction` / `next_argv` (`packet` never
authorizes launch, acceptance, or scheduling). Reconcile uncertain native starts
through native inventory before retrying; `main-context` attempts resume or
verify their saved receipt directly without spawning. Retry only after
confirming the old worker stopped and inspecting effects — or, if its host
session ended and its handle can no longer be inspected (and workers cannot
outlive sessions or share mutable external state), retry with
`confirmed_stopped: false, native_status: "unavailable"`. Each retry allocates a
fresh attempt with `prior_attempts` attached (requiring fresh pre-`start` Git
preparation; recovered in-flight Git attempts reuse/inspect their existing
preparation receipt). Takeover confirms the prior dispatcher stopped and uses a
fresh `owner` ID; never break locks by age (`ELOCKED` / `ESTATELOST` /
host-portability limits in [recovery and limits](references/protocol.md#recovery-and-limits)
and [host evidence](references/host-matrix.md)). For busy receipt writes, retry
publishing the saved envelope without rerunning the task.
