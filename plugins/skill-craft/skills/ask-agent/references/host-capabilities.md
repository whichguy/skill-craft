# Native host routes

Read the current host's section before preparing or launching. The live tool
schema is authoritative: model names and `Task` capitalization do not identify
capabilities. These are native-tool recipes, not a runtime launcher API.

## Which host section applies

Run `scripts/ask_agent_host.py` from this selected skill package once before the
first native launch of a session. It names the host from exact environment
variable names, innermost host first (a nested host inherits its launcher's
variables; never match a prefix such as `CODEX_`, because Codex plugin variables
are set in Claude Code and Grok sessions), and prints that host's binding
from [host-bindings.json](host-bindings.json): tool names, spawn, fresh and
fork arguments, concurrency capacity, observation timeout, and qualification
status (`qualified`, `pilot-ide`, or `unqualified`). Read the
`section` it names. `unknown` means no binding matched: use the live schema and
the sections below. The binding is data; the live schema wins where they differ,
and the difference is disclosed. The script launches nothing.

## Consumer-owned workspace: Codex pilot

For an explicitly selected `workspace_route: consumer-owned`, read
[Consumer-owned workspace](consumer-owned-workspace.md) in full. The host must
provide the consumer's required fresh native context, operation-directory control,
Git-root verification, collection, and stop evidence. If any required capability
is unavailable, leave the action pending; do not substitute inherited context,
the helper-managed route, a host-created worktree, or an external launcher.

The host-specific success evidence below is for the helper-managed route unless
it expressly qualifies this complete consumer route. It may inform a live schema
check, but does not establish the ShipLoop-bound Improve composition. The only
currently documented consumer binding is a Codex native pilot. Bounded native
fixtures exercised a complete fresh Improve owner, guarded return into a dirty
caller, actual interruption and recovery of the same child invocation, and refusal
of incomplete contracts, unknown/running owners, caller drift, and stale review
evidence. The fixtures synthesized earlier ShipLoop stages; they establish the
bound child and delivery boundary, not an executed full ShipLoop product workflow.
They do not establish a filesystem sandbox, token or latency savings, automatic
return after the parent ends, or behavior on other hosts. Keep per-run evidence
and check the live capabilities for the actual invocation. Do not infer support
on Claude, Grok, Cursor, OpenCode, or another host from this Codex pilot or older
managed-route evidence.

## Current workspace

For an explicitly selected `workspace_route: current`, use the launch table in
[Current workspace](current-workspace.md#record-the-baseline-and-launch). The
worker runs in the caller's checkout, so no workspace owner or binding mode
below applies. The evidence in this file is for the helper-managed route and
does not qualify the current route on any host.

## Choose one workspace owner and a binding mode

**Helper-managed route only.** The skill helper prepares the current caller
snapshot. Native tools launch and return the worker. After preparation, do not
request a second host-created worktree: it may select a different branch, omit
dirty inputs, and acquire a second cleanup owner.

| Binding mode | When to use | What is established |
| --- | --- | --- |
| Native cwd | The exposed spawn schema accepts the prepared path | Startup directory binding, plus independently checked operation context |
| Explicit operations | Spawn has no tested prepared-path binding | Correct cwd for each shell command and absolute file paths; no claim about startup cwd or sandbox roots |
| Native creation bridge | A separately qualified hook/adapter delegates creation to the helper | Not enabled by this package; requires baseline, identity and retention proof |

Before task operations the worker runs the packaged `check-context --receipt`
from the assigned directory. A failure blocks task writes. This command derives
its own cwd and Git root; a prompt echo or `git -C WORKTREE` is not a substitute.
Set cwd on every shell call (or begin that call with `cd WORKTREE &&`), including
retries. A previous shell's `cd` is not assumed to affect later tools. Other file
tools use absolute paths in the assigned worktree. A subdirectory is allowed
only while its Git root remains that exact worktree. Recheck after a directory
change or unexpected tool routing. Native permissions still apply.

## Grok Build / coding CLI

Use general-purpose native `spawn_subagent` with the prepared path in `cwd`
where the schema exposes it. Omit `resume_from` and omit `isolation="worktree"`
(`isolation` is `none|worktree` in 1.0.92 and mutually exclusive with `cwd`).
Grok Build has no native parent-history fork mode (`resume_from` continues a
completed child subagent by ID only); when a caller requests a forked review,
fall back to a fresh worker carrying essential conversation context inline.
Do not substitute Grok Bot, a chat model API, or a restricted `explore`/`plan`
worker for coding work.

Multiple foreground `spawn_subagent(background=false)` calls issued in one turn
execute concurrently and block up to 10 minutes without yielding the turn
(verified on 1.0.92). For `background=true`, after useful parent work, collect
with native `get_command_or_subagent_output` using all returned handles and a
positive `timeout_ms: 120000`. Incorporate the retrieved result before exit. A
notification in history or forwarded child text alone is not parent collection.
Describe this route as a native join when that is how results were obtained.
Native stop is `kill_command_or_subagent` where exposed; confirm stop before
cleanup.

Grok Build 1.0.34 passed the earlier managed snapshot/operation/delivery lifecycle
with native cwd and join; 1.0.77 and 1.0.92 passed neutral fresh spawn,
foreground parallel streaming, and ShipLoop review brief probes. Keep checking
the live schema on other versions.
[Official subagent guide](https://docs.x.ai/build/features/subagents).

## Codex

**Helper-managed evidence only.** The operation-directory details below can be
checked live for a consumer-owned pilot, but they do not themselves qualify its
fresh-context, owner-record, recovery, or final-delivery contract.

Use native asynchronous `spawn_agent` with `fork_turns="none"` for fresh tasks
(`fork_turns="all"` is the default on 0.171.0 and inherits full parent
conversation turns, which may be selected deliberately when a consumer requests
a forked review). Do not substitute an inherited fork for a fresh task. Spawn
has no `cwd` field: pass an explicit `workdir` on every shell call and absolute
paths for file operations. Run the context check from that workdir. Continue
parent work before native wait/completion collection; keep required collection
inside the live invocation.

Codex allows four concurrent agents including the parent, as the `spawn_agent`
description says: launch at most three workers at once and the rest as slots free.
Wait with `wait_agent` and the
observation timeout from [Native lifecycle](native-lifecycle.md) (`timeout_ms:
120000`), not short polls: every poll is a model call (measured on 0.169.0 with 30 s
tasks: 12 polls against 3 for the same work, finishing within 5 s of each other).
Native stop is `interrupt_agent` where exposed; retain unaccepted work.

The tested CLI 0.155.1 route passed with explicit operations and native join;
0.169.0 and 0.171.0 passed fresh (`fork_turns="none"`) and forked
(`fork_turns="all"`) probes. App worktree creation does not change the calling
agent's cwd. A separate user-visible app task or App Server thread is not
automatically a native subagent that returns to this parent; do not create one
as a silent replacement.
[Official subagent guide](https://developers.openai.com/codex/subagents).

## Claude Code

Use `Agent` or `Task`, whichever is actually exposed. For fresh workers use
`subagent_type="general-purpose"` (or omit) and omit `resume`; for a deliberate
forked review that inherits parent conversation history, `subagent_type="fork"`
is verified on 2.1.330 (runs on the parent's model and effort, ignoring model or
effort overrides). Do not use a fork type when a fresh context is required.
For the helper-prepared or consumer-owned route, **omit `isolation: worktree`**
(and `isolation: remote`): that option creates another checkout, not a binding
to the supplied path. Do not invent a `cwd` argument. Use native cwd only if the
actual schema supports it.

Launch checklist for the observed Agent schema: `subagent_type="general-purpose"`
for fresh (`subagent_type="fork"` only when forked history is requested); no
`resume`; `run_in_background=false` for blocking serial or single-turn parallel
foreground calls (2.1.330 verified 3 foreground `Agent` calls running concurrently
in one turn without yielding), or `run_in_background=true` for async background
work; no `isolation`; no invented `cwd`.

Otherwise give the worker this concrete operation rule: **every Bash command
begins with `cd "/actual/helper/worktree" &&`**. Run the context check in that
same command scope before task work, and use absolute paths for Edit/Write/Read.
Put that exact rule in the worker-facing delivery clause; do not leave a choice
of an unavailable Bash workdir argument. Report writes use absolute worktree paths too.
Do not treat Git's `-C` option as moving tests, builds or relative file writes.

Native completion notifications are the primary return route for backgrounded
workers in the tested 2.1.278–2.1.330 sessions. Use TaskOutput only if exposed;
it was absent in the routing probes. Keep a headless parent alive for the native
follow-up result. Use `SendMessage` to the returned agent handle, where exposed,
for same-worker follow-up and for forwarding an approval, decline or revocation
to a running worker; a new `Agent` call starts a fresh context instead.
Completion notifications re-invoke the parent, so do not poll or schedule wakeups
merely to wait for them. Follow the
[shared lifecycle](native-lifecycle.md) for visible status and cancellation;
a promptless ScheduleWakeup or arbitrary timer is not collection. `TaskStop`
signaling was observed previously; interruption of a running shell command was
not qualified by that cancellation fixture.

Existing-worktree `EnterWorktree(path=...)` is not the general route: 2.1.278
rejected both a primary caller and an external linked caller in the targeted
probes. It must not be silently replaced with another checkout. Scoped
WorktreeCreate integration remains separately qualified; this skill installs
no hooks and changes no global settings. Session-scoped 2.1.278 probes did bind
one dirty worker and two concurrent clean workers to distinct helper-created
paths, including native startup and unprefixed Bash cwd. WorktreeRemove did not
fire in those probes, so automatic hook cleanup is still unqualified. A future
bridge must keep receipt ownership, hook lifetime and helper close explicit.
Native worktrees default to a fresh
repository-default branch; `worktree.baseRef="head"` still does not reproduce
the helper's dirty layers. [Worktrees](https://code.claude.com/docs/en/worktrees)
and [creation hooks](https://code.claude.com/docs/en/hooks#worktreecreate).

## Cursor IDE / CLI

Use native `Task` with `subagent_type="generalPurpose"` (camelCase). For fresh
workers omit `resume` and omit `environment="cloud"` (which runs on a remote VM
and separate worktree); for a deliberate forked review inheriting parent
conversation history, pass `resume="self"` (verified live in Cursor IDE
2026-11-23). `Task` has no `cwd` parameter: require explicit `working_directory`
on every shell command and absolute paths for file tools, verifying canonical
`pwd` and Git root on entry.

In Cursor IDE (2026-11-23 probes), multiple foreground `Task` calls with
`run_in_background=false` issued in one turn executed concurrently (93% overlap)
without yielding to turn-end notifications; `run_in_background=true` delivers
completion notifications after the parent ends its turn (do not poll). Cursor
IDE passed fresh, forked (`resume="self"`), foreground parallel, and ShipLoop
Improve review probes; `cursor-agent` CLI (2026.09.23) remains separately
unqualified (the earlier 2026.09.18 CLI passed the old managed lifecycle only).
Qualify IDE and CLI separately rather than extending one surface's evidence.

Whole-session `--worktree` or IDE `/worktree` is not a selectable prepared child
path and does not establish dirty-input inheritance. Keep the helper-owned
store outside Cursor's managed cleanup root: Cursor can discover and clean up
externally created worktrees there. Do not change global cleanup settings.
No dedicated task-stop-only tool is exposed (`Task` supports `resume` +
`interrupt=true` to steer/interrupt); report an unconfirmed stop and retain work
if the current schema lacks one.
[Subagents](https://cursor.com/docs/subagents) and
[worktree cleanup](https://cursor.com/docs/configuration/worktrees).

## OpenCode

The tested 1.18.31 route is a **persistent-parent TUI pilot**, with
`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` scoped to that host process.
Do not change global settings or start another host process during delegation.
If the current session lacks the capability, report the prerequisite.

Use native `task(background=true)` and **omit `task_id` entirely** for a fresh
worker. It is a resume handle, not a task label; never fabricate one after an
argument error. Retain actual returned IDs. No child-cwd argument was established;
use each bash tool's `workdir` and absolute file paths, and run the context check.
An external helper path may require an `external_directory` permission decision;
do not weaken permissions globally or switch to an unguarded tool after denial.

The persistent TUI passed the earlier managed lifecycle with automatic native
returns and tool-observed operation paths. Fresh-call argument failures remain
recorded. A flag-disabled control ran synchronously; an enabled one-shot CLI
control exited before delivery. Interactive user input while a child remained
pending and native cancellation are still unqualified. Do not turn these into
support claims based on process exit or later resume.
[Versioned task implementation](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.31/packages/opencode/src/tool/task.ts)
and [permissions](https://opencode.ai/docs/permissions/).

## Different machines and client APIs

Cloud/remote execution needs the repository, helper and inputs on the worker's
actual machine. A committed clone does not reproduce local dirty state, and
local report paths are not automatic artifact transfer.

Codex App Server, Cursor ACP/SDK and OpenCode's server expose useful session
APIs, but a separate client must own their lifecycle, events and connection back
to this conversation. They are not transparent fallbacks for native Task. Keep
an explicitly requested external orchestration product separate from this skill.
