# Native host routes

Read the current host's section before preparing or launching. The live tool
schema is authoritative: model names and `Task` capitalization do not identify
capabilities. These are native-tool recipes, not a runtime launcher API.

## Consumer-owned workspace: Codex pilot

For an explicitly selected `workspace_route: consumer-owned`, read
[Consumer-owned workspace](consumer-owned-workspace.md) in full. The host must
provide the consumer's required fresh native context, operation-directory control,
Git-root verification, collection, and stop evidence. If any required capability
is unavailable, leave the action pending; do not substitute inherited context,
the helper-managed default, a host-created worktree, or an external launcher.

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

## Choose one workspace owner and a binding mode

**Helper-managed default only.** The skill helper prepares the current caller
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

Use the broadest available general-purpose native `spawn_subagent`, with
`background=true` and the prepared path in `cwd` where the schema exposes it.
Omit `resume_from`. Do not substitute Grok Bot, a chat model API, or a restricted
`explore`/`plan` worker for coding work.

In headless mode, after useful parent work, collect with native
`get_command_or_subagent_output` using returned handles and an available positive
wait timeout. Incorporate the retrieved result before exit. A notification in
history or forwarded child text alone is not parent collection. Describe this
route as a native join when that is how results were obtained. Native stop is
`kill_command_or_subagent` where exposed; confirm stop before cleanup.

Grok Build 1.0.34 passed the earlier managed snapshot/operation/delivery lifecycle
with native cwd and join. Keep checking the live schema on other versions.
[Official subagent guide](https://docs.x.ai/build/features/subagents).

## Codex

**Helper-managed evidence only.** The operation-directory details below can be
checked live for a consumer-owned pilot, but they do not themselves qualify its
fresh-context, owner-record, recovery, or final-delivery contract.

Use native asynchronous spawn and `fork_turns="none"` where exposed. Do not
substitute an inherited fork for a fresh task. If spawn has no cwd field, give
an explicit `workdir` on every shell call and absolute paths for file operations.
Run the context check from that workdir. Continue parent work before native
wait/completion collection; keep required collection inside the live invocation.

The tested CLI 0.155.1 route passed with explicit operations and native join.
App worktree creation does not change the calling agent's cwd. A separate
user-visible app task or App Server thread is not automatically a native subagent
that returns to this parent; do not create one as a silent replacement.
Use native interruption when exposed and retain unaccepted work.
[Official subagent guide](https://developers.openai.com/codex/subagents).

## Claude Code

Use a fresh general-purpose `Agent` or `Task`, whichever is actually exposed,
with native background mode. Do not use a fork type that inherits parent history.
For the helper-prepared route, **omit `isolation: worktree`**: that option creates
another checkout, not a binding to the supplied helper path. Do not invent a
`cwd` argument. Use native cwd only if the actual schema supports it.

Launch checklist for the observed Agent schema: general-purpose; fresh/no resume;
`run_in_background=true`; no `isolation`; no invented `cwd`.

Otherwise give the worker this concrete operation rule: **every Bash command
begins with `cd "/actual/helper/worktree" &&`**. Run the context check in that
same command scope before task work, and use absolute paths for Edit/Write/Read.
Put that exact rule in the worker-facing delivery clause; do not leave a choice
of an unavailable Bash workdir argument. Report writes use absolute worktree paths too.
Do not treat Git's `-C` option as moving tests, builds or relative file writes.

Native completion notifications are the primary return route in the tested
2.1.278 session. Use TaskOutput only if exposed; it was absent in the routing
probes. Keep a headless parent alive for the native follow-up result. Use
`SendMessage` to the returned agent handle, where exposed, for same-worker
follow-up and for forwarding an approval, decline or revocation to a running
worker; a new `Agent` call starts a fresh context instead. Completion
notifications re-invoke the parent, so do not poll or schedule wakeups merely to
wait for them. Follow the
[shared lifecycle](native-lifecycle.md) for visible status and cancellation;
a promptless ScheduleWakeup or arbitrary timer is not collection. TaskStop
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

Use fresh native background `Task` where exposed. Bind prepared cwd if the
schema actually accepts it; otherwise require explicit operation directories
and absolute file paths. The tested 2026.09.18 CLI delivered automatic task
notifications and passed the managed lifecycle. Its operation paths were
reported by workers; stronger tool-level context checks are now required.
Qualify IDE and CLI separately rather than extending one surface's evidence.

Whole-session `--worktree` or IDE `/worktree` is not a selectable prepared child
path and does not establish dirty-input inheritance. Keep the helper-owned
store outside Cursor's managed cleanup root: Cursor can discover and clean up
externally created worktrees there. Do not change global cleanup settings.
No native task-stop tool was exposed in the tested CLI capability probe;
report an unconfirmed stop and retain work if the current schema lacks one.
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
