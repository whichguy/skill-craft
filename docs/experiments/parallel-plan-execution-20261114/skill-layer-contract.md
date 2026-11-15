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
- ~~So the time predicate is easy to state: an independent task estimated at 20 s or more clears every host's break-even with margin (the 30 s cells took 35 s to 45 s a task and the whole run fell 25% to 45%); an estimate under about 15 s does not.~~
  ~~One trial per cell, so these are shapes, not rates; an estimate is the caller's, and an unknown estimate means serial.~~ **Superseded 2026-11-15 (journal E14, F47 and F48):** those savings are against a context that ran its waits one after another.
  A context that batches its commands and overlaps its waits (arm A0p, no sub-agents) beat the fan-out in five of six cells (by 9 s to 94 s) and used 0.34 to 0.75 times its input tokens in five of them, so the predicate has two steps. First, overlap the waits in one context
  (start the slow verification commands of all ready tasks as background jobs in one command, then wait); that needs no worker, no binding and no merge. Second, fan out only for the model's own work that one context
  cannot overlap: the saving over the control is (independent tasks minus rounds) times the model's seconds per task, minus the fan-out's overhead, and the cells put the break-even at about 10 s to 14 s of model
  time per task on Claude, 3 s to 21 s on Grok and 43 s to 60 s on Codex (six cells, one trial each, one Grok cell with the opposite sign). The tasks of those cells needed 6 s to 27 s of model time, so the regime of
  minutes a task, where the fan-out should win by hundreds of seconds, is the part with no cell; the published evidence says coupled, shared-file or sequential work loses (E14, comparison-20261115/). An estimate is the caller's,
  and an unknown estimate means serial.
  **E15 note (2026-11-15, journal F53 to F57):** in the recorded ShipLoop runs the waits one context could overlap are about 0.6% of step time (the model's own verification commands are 1.2% of step time,
  and running a window's together would save at most 0.55%); steps are model-bound (77.5% of the window is the model's own time) and ShipLoop's own commands take 18.6% (its test stage alone 6.0%, the mutation check 3.7%).
  So the first step of the predicate, overlap the waits, is read per project from the seconds ShipLoop already records for each command (Salesforce-tagged steps spend 5.6% in verification calls, the rest 0.9%);
  for projects like the recorded ones it does not pay, and the time left to take is the model's own and ShipLoop's own commands, not the project's tests.
- Tokens and cost (E12, F37; the owner's order is quality, then tokens, then time): on Claude the fan-out used 1.4 to 1.7 times A0's input tokens and 2.4 to 3.5 times its dollars at these task sizes (an extra $0.345 for 284 s saved at S = 90); on Grok 0.55 to 0.76 times the
  tokens and 0.86 to 1.38 times the dollars; on Codex about 1.6 times the tokens, and on Codex the parent's polling makes the token cost grow with the length of the wait on both arms. The layer must report the expected time saved and the token multiple before it fans out, so the opt-in is informed.
  The token curve with many more calls a task is a model (R4), not a measurement.
- A recorded ShipLoop step iteration has a median of 154 s (F11), far above every break-even; but 90% of recorded plans have no independent pair (F8), so the gate that matters most in practice is width, not task length.

## 7. Merge and isolation (measured on a toy package, E13)

The repository already has the machinery for writes (Ask Agent's helper-managed worktrees and delivery, `references/git-integration.md`, `workspace-operations.md`); E13 priced the shape with a minimal kit (a git worktree per attempt, a scripted merge in completion order, abort and retry on a conflict) on a four-module Python package with a hidden oracle, at 30 s tasks:

- **Cost.** Isolation plus scripted merging took about 1 s of the kit's own time (five workspaces, five commits, five merges) and added 0 to 11 s to the whole run against a shared checkout (-0.1 s, +6.2 s, +10.6 s; inside the same-condition spread), with equal model calls and input tokens within 6% (F39). The fan-out's win survived writing code: the whole run was 0.50, 0.72 and 0.86 times one context's (F40). All fifteen registered write trials passed the oracle.
- **Rule that held.** Run write tasks together only when their declared paths are disjoint, give each attempt its own worktree from main's current head, merge completed branches into main in completion order before offering any dependent (a dependent starts only from merged work), commit on completion and refuse an empty change, record any file outside the declared paths without refusing it, and treat a conflicting merge as: abort, log the paths, offer the task again from the updated main with a note saying why, run its verification again. Where it was exercised (Claude, Grok) it worked: one conflict, one retry, a valid tree, at a cost of about one task round plus a few seconds (+54.2 s, +60.5 s; F41). A task whose attempts are used up fails with the conflict as the reason and its dependents are blocked (calibrated, not seen live).
- **What failed or was not exercised.** P50 missed as registered: on Codex the three slots ran the second registering task after the first had merged, so the undeclared shared file never conflicted (F42). A shared checkout survived three concurrent appends without a loss, but it has no scope check and no conflict detection, and the fixture's integration task would have repaired a lost import (F43): shared is not evidence that concurrent writes to one file are safe.
- **Not measured.** Large files and repositories (git's cost grows with them), semantic conflicts that a textual merge accepts (the oracle and the suite catch those; no trial produced one), more than four workers, ShipLoop's own commit stage and clean-checkout identity (F15), and unattended recovery of a lost worker (what the retired chain bought).

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
  *Status 2026-11-14:* drafted in `skills/ask-agent` (journal R7): a host command, a small binding file, two card sentences, Codex's slot and wait note and eleven tests; merged to main at fbfebee74d5eee4bdcb4ff93ab750bd6f3d45773 and released as ask-agent 0.11.0 (skill-craft 2.38.0, 9710190f5caaafba9cd114b8f060cb5a02c691cc) on the owner's word.

A recommendation, and its limits, are in the journal's closing entry (R5, with E13's update in R6). None of the three removes the open owner decision that decides whether concurrent ShipLoop steps are wanted at
all (F15, the per-step lifecycle); inside one stage (bounded investigations and reviews), the contract applies as written.
