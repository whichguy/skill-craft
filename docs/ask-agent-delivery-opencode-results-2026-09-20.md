# Ask Agent delivery and OpenCode validation

Status: implementation complete; validation complete with the host limitations below.

The [plan](ask-agent-delivery-opencode-plan-2026-09-20.md) separates deterministic
Git delivery, native-host lifecycle evidence, and installation. No earlier verdict
is overwritten. Native stop and semantic acceptance remain parent responsibilities;
the workspace helper validates Git/filesystem evidence.

## Baseline

- Workspace helper: 18 real-Git tests passed before implementation.
- Previous worktree harness: 34 tests passed before implementation.
- Focused installer baselines passed before its edits.

## Implementation

- Per-worker launch contract declares `patch`, `commits`, or `report-only`.
- Optional helper delivery proofs make patch transfer, commit completeness, and
  report-only input preservation mechanically inspectable. Commit mode requires
  a clean inherited snapshot; dirty snapshots use explicit patch delivery.
- Managed experiment event schema v2 binds native workers and attempts to helper
  receipts, operation roots, terminal state, task result, delivery mode, acceptance,
  cleanup, and retained artifacts. Legacy evidence remains legacy.
- OpenCode native skill-directory installation targets the XDG config root and
  retains ownership, symlink/copy, status, and uninstall safeguards.

## Evidence location

Current campaign:
`/Users/dadleet/Documents/Codex/experiments/ask-agent-delivery-20260920T055228Z/`.

Exact preflight executables: Grok Build 1.0.34, Codex 0.155.1, Claude Code 2.1.278,
Cursor 2026.09.18-9a7762b, OpenCode 1.18.31. All current live cases use the frozen
Ask Agent **0.5.1** package:

- Package tree SHA-256: `d98c65e21ee9da889a1a6b87fcc0396aee92cb66ef36e241e04b802c9b092e78`.
- Helper SHA-256: `af842ce7cf2c141f7adbc77bfe9199375614a7ae60beca9ea0c386775472319d`.
- Immutable freeze record: campaign `operator/freeze.json`.

## Verification scope

The real-Git delivery suite exercises dirty-parent patch integration, clean
commit integration, rename handling, dirty-baseline rejection, incomplete
deliverables, transient or report paths in commits, and report-only preservation.
The managed-harness suite exercises failed/cancelled/unknown native outcomes,
wrong roots, reused identities, callback/session boundaries, cleanup chronology,
retained failed retries, actual archive digests, legacy evidence, immutable source
identity, and parseable create-only CLI verdicts. Its live fixture deliberately
uses **patch** for code and **report-only** for analysis; it does not claim live
commit handoff across every provider.

OpenCode installation is checked separately: isolated HOME/XDG configuration,
symlink and copied packages, ownership-aware status/uninstall, and an installed
helper invocation from an unrelated working directory. A no-model OpenCode
`debug skill` probe checks native discovery when the same source also appears in
the Claude-compatible directory.

Independent review found and corrected a receipt-source HEAD comparison that
incorrectly depended on the parent's later HEAD. A separate real CLI check found
internal Path/tuple indexes leaking into the verifier's JSON output; only public
serializable summaries now leave the validator. Native event locators provide
trace provenance, not independent proof of semantic acceptance.

## Mechanical results

`PYTHONDONTWRITEBYTECODE=1 bash test/run-all.sh --group core` passed: **30 suites,
0 failed**. The campaign retains `operator/core.log` and `operator/core-summary.json`.
This includes 18 workspace-helper tests, 9 delivery tests, 14 managed-evidence
tests, and the previous 34 worktree-harness tests. The delivery suite now includes
a successful two-commit handoff and rejects omitted, reordered, wrong-base,
abbreviated, and extra commit IDs.

OpenCode installer cases cover all-host selection, host isolation, spaced XDG
paths, copy/symlink discovery, status/uninstall ownership, and copied installed
helper execution. Independent installer review found no actionable findings.

Full generated-view synchronization completed. The core package parity checks
and standalone Ask Agent offline marketplace validation passed. Source, frozen
test package, and generated plugin package have identical tree/helper digests,
recorded in `operator/final-parity.json`. Whitespace checks passed for the changed
tracked files and the new Ask Agent/test/report files.

The optional skill-creator Python validator could not run because its PyYAML
dependency was unavailable in both checked runtimes. Repository-native
frontmatter and package checks passed in the core aggregate. No dependency was
installed to work around that optional check.

## Live managed-worktree results

These are v2 results against the frozen package, not process-exit claims. Each
case uses two native workers, dirty inherited caller inputs, a code patch and a
report-only task. `COMPLETE` requires actual operation directories, native
returns, parent work while results are pending, integration, four retained
reports, and helper close. It does not prove operating-system isolation or every
interactive session mode.

| Host/profile | Strict verdict | Native return and directory evidence |
| --- | --- | --- |
| Grok Build 1.0.34 | COMPLETE | Native `spawn_subagent` cwd binding; actual operation roots; native join. |
| Codex 0.155.1 | COMPLETE | Fresh `spawn_agent`, explicit operation directories; native join. CLI output omitted spawns, so the exact public source-session events were used. |
| Cursor 2026.09.18-9a7762b | COMPLETE | Native `Task`, automatic completion notifications; reported operation cwd/Git roots bind to the two helper receipts. No native child-cwd field is claimed. |
| OpenCode 1.18.31, persistent TUI and process-local background flag | COMPLETE for the managed lifecycle | Native `task` notifications; child bash tool outputs independently show `pwd` and Git root inside each helper worktree. See the pilot caveats below. |
| Claude Code 2.1.278, normal profile | FAILED | Native returns, integration, reports and helper close passed. The code worker's observed shell cwd was a separate native Claude worktree, and the caller gained an unexpected `tasks/in-progress/prompt-improvements-backlog.md`. |
| Claude Code 2.1.278, hooks disabled for this invocation | PARTIAL | File delivery and preservation passed. Both workers operated through absolute paths / `git -C`, but their actual shell cwd remained the caller. The strict directory check correctly refused qualification. |

Verdicts are under each campaign case's `operator/`: Grok
`verification-summary.json`; Codex `verification-v2.json`; Cursor and OpenCode
`verification-v2-normalized.json`; both Claude cases `verification-v2-strict.json`.
Earlier verifier outputs and normalization corrections remain preserved. In
particular, effective `git -C` targets must not be substituted for observed shell
cwd. The controlled Claude result does not erase the normal-profile failure, and
the unexpected file's writer was not established by the public hook events.

OpenCode's main run had six argument-validation failures before child creation:
the emitted calls contained invalid `task_id` values despite the instruction to
omit a resume handle. Two later calls still supplied nonexistent `ses`-prefixed handles;
public session metadata confirms that the host actually created two new children.
`native-call-boundaries.json` retains this prompt-compliance issue separately
from the successful lifecycle. OpenCode therefore remains a conditional pilot.

## Native cancellation and permission controls

- Grok Build: native `kill_command_or_subagent` acknowledged cancellation; native
  collection confirmed the stopped task. The helper worktree remains registered,
  with no integration or close record.
- Codex: native `collaboration.interrupt_agent` acknowledged interruption of the
  running worker; the helper worktree remains registered and unclosed.
- Claude: native `TaskStop` succeeded and the parent received a stopped task
  notification. Its intended child sleep had already been denied by host tool
  policy, so this proves task-stop signaling rather than interruption of a running
  shell command. The worktree was retained.
- Cursor: a separate bounded capability probe found no native task-stop tool in
  the exposed session schema. Its search found only an unrelated browser tracing
  stop operation. No cancellation child was launched. Evidence:
  `cursor-cancel-capability/operator/cancellation-capability.public.json`.
- OpenCode: no native task cancellation was established by the exposed CLI/TUI
  capabilities; no cancellable-child success is claimed.
- OpenCode permission control: exactly one native `write` to a prepared external
  worktree was denied by the process-local `external_directory` rule. The sentinel
  SHA-256 stayed unchanged, no fallback tool ran, and the worktree remains retained.
  Evidence: `opencode-permission-denied/operator/verification.json`.

Cancellation and permission-denied workspaces intentionally remain available
for inspection. Successful managed fixtures archived their reports before closing
their two worker worktrees.

## OpenCode session and feature controls

- **Background flag disabled:** the native Task silently ran synchronously until
  its delayed child completed. The request was not rejected as unsupported.
  `opencode/operator/control-background-disabled.json` records
  `FAILED_NO_SILENT_FALLBACK`. Do not treat that route as asynchronous support.
- **Background flag enabled, one-shot CLI:** a valid fresh Task call omitted
  `task_id`, launched a delayed child, and the parent performed arithmetic. The
  parent nevertheless exited after 23.164 seconds before the native callback or
  child result marker. The child's public shell record exists, but no final child
  assistant result was delivered. Evidence:
  `opencode-one-shot-enabled/operator/observed-disposition.json`. An earlier
  invalid-input attempt remains recorded separately.
- **User input while a TUI child is pending:** not qualified by this campaign.
  Earlier transport attempts did not record the arithmetic user message in the
  actual parent session; they cannot prove host buffering. A corrected real-PTY
  control confirmed user-message ingestion but failed to create a child: all six
  native launch calls contained invalid UUID `task_id` values despite omission
  and empty-string instructions. No child session was created. Evidence:
  `opencode-interaction-corrected/operator/verification.json`. The source of that
  argument behavior (model versus host parameter processing) is unresolved.

These controls preserve failure and transport history rather than relabeling it
as success. The original persistent-TUI managed case proves native return and
worktree delivery; it does not establish reliable fresh launch on every attempt,
interactive input during pending work, or survival after a one-shot parent exits.
All campaign-owned persistent TUI processes were closed after their children
completed; the corrected launch-failure control had no children. No global host
configuration, credentials, permission policy, or feature flags were changed.

## Delivery decision

The implementation is ready for the validated helper, delivery-mode, installer,
and Grok Build/Codex/Cursor native-workspace routes. Keep OpenCode as an explicit
persistent-session pilot. Claude's file handoff works in these fixtures, but this
campaign does not qualify it as running commands from the assigned helper root.
Neither a successful message nor a zero process exit should override these
directory and session-lifetime results. Changes remain local and unpublished.

## OpenCode qualification boundaries

OpenCode's native Task background mode is gated by the process-local
`OPENCODE_EXPERIMENTAL_BACKGROUND_SUBAGENTS=true` flag. The matching installed
[task implementation](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.31/packages/opencode/src/tool/task.ts)
creates a native child and injects results into the parent; it does not expose a
child cwd argument. Explicit worktree operation paths must therefore be checked.

The [official skill locations](https://opencode.ai/docs/skills/) include the native
XDG config skill directory and Claude-compatible skill directories. This supports
shared portable packages, not separate host-specific skill bodies.

Permission controls use the documented [inline runtime configuration](https://opencode.ai/docs/config/)
and [external-directory permission](https://opencode.ai/docs/permissions/) only in
the disposable process. No global experimental flags, hooks, credentials, or
permission settings are changed by this campaign.
