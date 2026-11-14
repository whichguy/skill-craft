# Skill-layer contract: dispatch and collect independent work, whatever the harness (proposal)

Status: a proposal from the parallel-plan-execution study (journal `docs/shiploop-parallel-execution-journal.md`, README Amendments A5 to A7). Nothing in `skills/`, `agents/`,
`hosts.py` or a marketplace file changes with it; every number cites a journal entry and the commit that holds its evidence. It is a contract and a set of bindings, not code.

## 1. What was asked

The owner, 2026-11-14: "my intention is to introduce a skill layer that abstracts shiploop from the mechanics, hopefully of a particular harness that we're running in. We would be able to
differentiate, in the skill, which harness we're running in, and then make the appropriate call on how to dispatch and merge the agent." The first request was: use each harness's native
agent contexts (a sub-context does a task, only the outcome is kept in the main context or a file), parallel where the plan's dependencies allow it, opt-in, dynamic, harness-independent.

The shape that follows: ShipLoop (or any caller) says **what** is independent and what each task must return. The layer says **how**: it detects the harness, picks the binding for it, dispatches each
claimed task to a fresh native context, collects the outcomes and reports. The caller contains no harness-specific text; the layer contains no ShipLoop-specific text.

## 2. What already exists, and what the study adds

| Already in the repository | What it gives | Where the study stops short of it |
|---|---|---|
| Ask Agent (`skills/ask-agent`, `references/host-capabilities.md`, `native-lifecycle.md`, `task-interface.md`) | Per-host recipes for a fresh native context (Grok `spawn_subagent` background and `get_command_or_subagent_output`; Codex native spawn with `fork_turns` "none" and native wait; Claude a fresh general-purpose `Agent` or `Task` and completion notifications), workspace and Git delivery | The recipes are prose the model selects by reading; the host is not detected by a script, and nothing measures what a dispatch costs |
| Plan Dispatcher (`skills/plan-dispatcher`) | A durable ready set: claim, launch state, collect, verify, successors | Heavy: a 60 s ideal fan-out took 587 s on Codex (F3, `test/shiploop_e2e/LEARNINGS.md`); the study's `dagkit.py` is the minimal stand-in |
| In Parallel (`skills/in-parallel`) | One coordinator composing Ask Agent and Plan Dispatcher; disjoint write scopes; an aggregate result | Same weight; no break-even policy |
| ShipLoop's `detect_host` (`skills/shiploop/scripts/shiploop_grants.py`) | Exact-marker host detection, innermost first | Works in the parent and in a sub-agent on all three hosts (E10, F30) |
| The retired implementation chain (F2) | Isolation and unattended retry of a lost worker | Retired because it conflicted with the per-step lifecycle (G1); its speed gain was never measured |

The study adds four things the repository does not have: **measured bindings** (E1, E9, E10, E11), a **detection rule with its failure modes** (E10), a **decision policy** from a cost curve (R4, E12), and a
**conformance fixture** that qualifies a binding on a host and version (`analysis5`, arm A3).

## 3. The contract

### What the caller supplies (a task set; a file)

For each task: `id`; `instruction` (the whole task, because a fresh context has no memory of the conversation); `deps` (ids of earlier tasks; an omitted `deps` means unknown, never independent, F4);
`paths` (what the task writes, for write tasks); the shape of the outcome it must return (a small JSON object; the study used `{"answer": integer}`); optionally `seconds` (an estimate) and a timeout.

### What the layer guarantees (clauses; each is script-enforced or an explicit instruction, never a hope)

- **C1 readiness is the script's.** A task is handed out only by `ready --claim --capacity N`; a task whose dependency has not recorded a successful outcome is never offered (refusal category `premature`).
  The model never reads the graph to decide what may start (the study's arm A2 is a diagnostic of model scheduling, not a design).
- **C2 workers never choose successors or revise the graph.** The parent launches workers and relays one-line acknowledgements; a worker's only side effects are its task and its outcome callback.
- **C3 fresh contexts, outcome-only retention.** Each task runs in a fresh native context. The worker reports through the script's callback (`begin`, then `complete`), the outcome is recorded by the
  script (hash-chained to its inputs), and the parent never needs the worker's transcript. In the pilot the parent's own input in A3 was 0.73 times A0's on Claude and on Codex (F22 as corrected, F28).
- **C4 binding by host, serial otherwise.** The layer detects the host (section 4), selects that host's binding (section 5) and checks that the binding's tool is present. If the host is `unknown`, the tool is
  absent or the binding is not qualified (section 9) for this host version, the layer runs the tasks one at a time in the current context (the study's arm A0) and says so. It never substitutes shell
  background jobs or a model subprocess for a native agent.
- **C5 capacity and release.** At most `capacity` claimed-and-unfinished tasks at once; a claim whose launch failed is returned with `release` and offered again. Codex's capacity is 3 (it holds one of four slots).
- **C6 opt-in and gate.** Fan-out runs only when the caller opts in and the predicate of section 6 holds; otherwise the layer runs serially and records why.
- **C7 failure.** A failed task makes its dependents `prerequisite-failed` and they are reported `not_run`; no task has two terminal outcomes; the final report names every task exactly once and must match the ledger.
- **C8 journal.** Every transition is appended to a timing-ordered ledger (`ts`, kind, step, pid), the ground truth for any timeline. A benchmark may read the host's own record of its agents as a cross-check.
- **C9 workers know they are workers.** The instruction to every worker says it is a worker and must not start agents (E10: the Claude and Codex sub-agents list an agent-starting tool and nothing in the
  environment tells a child it is one; the script's lease is the guard).
- **C10 merge.** For read-only work the merge is the dependent task reading recorded outcomes through the script (the pilot's `integrate` phase, 4 s to 11 s). For writes, see section 7.

## 4. Detecting the harness

Primary: the repository's own `detect_host`, exact marker names, innermost first: `CODEX_SANDBOX` or `CODEX_THREAD_ID` is `codex`; else `GROK_AGENT`, `GROK_SESSION_ID` or `GROK_SANDBOX` is `grok`; else
`CLAUDECODE` is `claude`; else `unknown`. It named the right host in the parent and in a native sub-agent on all three hosts (E10).

Rules the trials add: never match a prefix (the Grok and Claude environments contained `CODEX_COMPANION_*` from the launching session); use the nearest host ancestor only if the environment is silent (process
ancestry continues through the launching session); confirm by tool inventory (the binding's native tool must be present: Claude `Agent` or `Task`, Codex `spawn_agent` (listed as `collaboration.spawn_agent`),
Grok `spawn_subagent`) and treat a mismatch as `unknown`; a sub-agent cannot tell from its environment that it is one (C9).

## 5. Bindings (measured; Claude Code 2.1.325, Codex 0.169.0, Grok Build 1.0.77)

| | Claude Code | Codex | Grok Build |
|---|---|---|---|
| Start a worker | `Agent`, general-purpose; the four calls for a round in one assistant message, about 1.9 s apart | `spawn_agent` with `fork_turns` "none" and a short `task_name` | `spawn_subagent`, general-purpose (never `explore` or `plan`), background |
| Collect | completion notifications re-enter the parent as new turns (several `result` events in `-p` mode); no polling | `wait_agent` with a timeout; the parent polled in 10 s slices, so its calls grow with the wait (5, 12, 17 polls at S = 0, 30, 90, E12); H asks for one long wait, which cut the parent's `wait_agent` calls from 12 to 3 at S = 30 (A9, F38) | `get_command_or_subagent_output` with all task ids and a long `timeout_ms`, or `wait_commands_or_subagents` |
| Concurrency | four at once observed | four slots including the parent: three workers | four at once observed |
| Host's own record (for the ledger cross-check) | stream `system` task events, `parent_tool_use_id` on every call | one rollout file per thread, naming parent and depth | `logs/unified.jsonl`, a session id on every tool call |
| Token accounting | sum `usage` over every `result` event for the parent; `modelUsage` is the whole run, cumulative | the turn's usage is the parent's; each child's rollout adds its own | the end usage is the whole run; per-call `shell.turn.inference_done` has the session id |
| Tool name pitfall | the init event lists the tool as `Task`, calls and the model say `Agent`: accept both | the model reports `collaboration.spawn_agent`; the call is `spawn_agent` | none seen |
| Where the per-agent spawn cost sits (F32) | in the model writing each child prompt, about 1.9 s each, all four in one model call | one model call per spawn, 5.6 s to 6.8 s each | in the host starting each child in turn, 3.4 s to 5.6 s each, after one model call that issued all four |
| Host-specific wording (H) | no effect: the packet already issues the four `Agent` calls in one model call; whole run 39.6 s against 43.2 s (P33 held) | no effect on spawning: one spawn per model call under H too (P41 missed), whole run 107.5 s against 109.9 s (P42 missed); the long-wait sentence at S = 30 cut the parent's waits from 12 to 3 and its model calls from 25 to 15, total input tokens -11.5%, whole run within 5 s (P43, P44 held): **the one H that earned its place** | no effect (E11, F33): the anonymous packet already issues the spawns in one model call |
| Cost that grows with the task (E12, F37) | none seen: calls and input tokens flat across S | the parent's polling: model calls 23, 29, 49 (A0) and input tokens 449k, 612k, 1.06M; A3 707k, 988k, 1.71M at S = 0, 30, 90 | none seen: calls flat across S |

Anything not measured is not in the table.

## 6. When to fan out (a predicate a script can compute)

Fan out only if all hold: the opt-in is set; the plan exposes width of at least 2 (two tasks with no dependency path between them) and, for writes, disjoint declared `paths` (E0: 61% of independent pairs
share paths, F10); the estimated seconds of each independent task are above the host's break-even; the host is qualified (section 9). The break-even comes from a cost curve, not a constant, and is a
number per host and version:

- Time (E12, twelve trials, F34 to F36): the fan-out's fixed costs stay fixed as tasks lengthen (A3 minus A0 outside the work phase, S = 0 / 30 / 90: Claude 21.4 / 19.4 / 15.1 s, Grok 43.0 / 37.9 / 34.5 s, Codex 26.6 / 22.5 / 30.5 s) and the saving
  grows with the task: the whole-run ratio A3 / A0 is 1.22 / 0.55 / 0.44 (Claude), 1.18 / 0.63 / 0.52 (Grok) and 1.10 / 0.75 / 0.69 (Codex), a saving of 56%, 48% and 31% at 90 s more per task. The break-even per-task time is
  overhead / (independent tasks minus rounds): 7.1 s (Claude), 14.3 s (Grok), 13.3 s (Codex, three slots). The pilot's tasks (5 s to 15 s) were at or just under it, which is why it lost.
- So the time predicate is easy to state: an independent task estimated at 20 s or more clears every host's break-even with margin (the 30 s cells took 35 s to 45 s a task and the whole run fell 25% to 45%); an estimate under about 15 s does not.
  One trial per cell, so these are shapes, not rates; an estimate is the caller's, and an unknown estimate means serial.
- Tokens and cost (E12, F37; the owner's order is quality, then tokens, then time): on Claude the fan-out used 1.4 to 1.7 times A0's input tokens and 2.4 to 3.5 times its dollars at these task sizes (an extra $0.345 for 284 s saved at S = 90); on Grok 0.55 to 0.76 times the
  tokens and 0.86 to 1.38 times the dollars; on Codex about 1.6 times the tokens, and on Codex the parent's polling makes the token cost grow with the length of the wait on both arms. The layer must report the expected time saved and the token multiple before it fans out, so the opt-in is informed.
  The token curve with many more calls a task is a model (R4), not a measurement.
- A recorded ShipLoop step iteration has a median of 154 s (F11), far above every break-even; but 90% of recorded plans have no independent pair (F8), so the gate that matters most in practice is width, not task length.

## 7. Merge and isolation (what is not measured)

The study ran read-only work. For writes the repository already has the machinery (Ask Agent's helper-managed worktrees and delivery, `references/git-integration.md`, `workspace-operations.md`) and the
rule from E0: only tasks with disjoint declared paths run together, and a dependent integration task runs the combined checks after the barrier. No trial measured the cost of worktree preparation, delivery or
conflict handling, so this contract gives no time or token figure for it and the layer must not claim one. A write fixture (disjoint edits in a shared checkout; the same with isolated worktrees and a merge;
one overlapping edit that conflicts) is the next measurement before a write fan-out is enabled.

## 8. Qualification: when a binding may be used

A binding is qualified for a host and version when the conformance fixture passes: the study's `analysis5`, arm A3, on that host's owner profile: five of five answers correct, `verify` OK, a faithful final report,
exit 0, nothing left running, a peak of at least 3 in both the ledger and the host's own agent record, no refused attempt. The identity probe (E10) passes in the parent and in one sub-agent. Re-run on a version
change; record the version (the repository's existing notes qualify Claude Code 2.1.278, Codex 0.155.1 and Grok 1.0.34; the study ran 2.1.325, 0.169.0 and 1.0.77). The apparatus is `launch.py`,
`score.py` and `calibrate.py` (159 cells, no model call) in this folder.

## 9. Options for where it lives (the owner's decision)

- **A. Extend In Parallel and Ask Agent with a detection script, the bindings table as data, the predicate and the fixture.** Least new surface; In Parallel keeps one coordinator; inherits their weight.
- **B. A new thin dispatch skill over a minimal script (the study's `dagkit.py` shape: `ready --claim`, `begin`, `complete`, `release`, `outcome`, `verify`) that calls Ask Agent for the fresh native context.**
  The fastest route measured; a fourth skill beside Ask Agent, In Parallel and Plan Dispatcher, with the duplication that implies.
- **C. Only the detection and the bindings table go into Ask Agent as machine-readable data; ShipLoop calls Ask Agent directly and keeps its own per-step lifecycle.** Smallest change; gives ShipLoop
  harness independence for its existing native delegations (for example the per-step review) but not for concurrent steps.

A recommendation, and its limits, are in the journal's closing entry once E11 and E12 are scored. None of the three removes the open owner decision that decides whether concurrent ShipLoop steps are wanted at
all (F15, the per-step lifecycle); inside one stage (bounded investigations and reviews), the contract applies as written.
