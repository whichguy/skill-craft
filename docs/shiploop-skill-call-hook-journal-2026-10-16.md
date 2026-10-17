# Skill-call hook and the Improve-stage gate: journal (2026-10-16)

Living record of the Claude-only hook that records Skill calls and of the `complete` gate on an Improve stage. Branch
`feat/shiploop-eff-hook-6afcbc` (base 398466a3). Edit a claim rather than deleting it: mark it superseded with the date and reason.

## Question

Can ShipLoop make sure the improve skill is invoked at every Improve stage, when packet wording has not (owner rule: enforce by
script, not by prompt)?

## Evidence that motivated it

- 2.1.0 live run: 3 of 4 Improve reviews were written by a model-written script that reported to the runtime directly.
- 2.4.0 live slice: the skill was invoked for 1 of 4 Improve stages; after the first, the model wrote `scratch/imp.sh` and reused it.
- 11f5a5b9 added "at every Improve stage and not from memory of an earlier one" to the packet; its commit message records that
  this was unproven and that a Skill-call hook was the fallback. The duplicate-review refusal (`_duplicate_review_gate`) does not
  fire when the notes are specific.

## What was measured before building (status: firm, n=1 each, Claude Code 2.1.301)

- A `PostToolUse` hook with matcher `Skill` fires for a Skill-tool call and its stdin carries `tool_name`, `tool_input.skill`,
  `tool_input.args`, `tool_use_id`, `session_id`, `prompt_id` and `transcript_path`. Recorded as
  `test/fixtures/shiploop-keepalive/claude-skill.json` (scrubbed). PostToolUse is enough; PreToolUse was not needed.
- The Bash tool's `CLAUDE_CODE_SESSION_ID` equals the hook payload's `session_id` (probe: both `1a37243e-...`). The gate depends on it
  to find the binding of the session that runs `complete`; `health_notice` already relied on the same equality.
- A real `claude -p` session with the ShipLoop observe and skill hooks bound a scratch run and wrote the Skill call to the run's
  `skill-calls.jsonl` (session and tool-use id present). Its binding had `skill_hook: false`, correctly, because the hooks came from
  `--settings` and not from a plugin package or `~/.claude/settings.json`.
- The hook costs about 50 ms for a call from an unbound session (no subprocess is spawned).

## Design decisions and why

- **Where the gate reads "bound".** `complete` runs in a Bash subprocess, so it looks up the binding of its own Claude session
  (`CLAUDE_CODE_SESSION_ID`) for this run. The observe hook records `skill_hook` on the binding, judged from the hook configuration
  the hook was loaded from (a plugin package's `hooks/hooks.json`, or a complete settings install). Reason: a session bound by hooks
  that lack the Skill-call hook (an install from before this change) would otherwise be held to a record nothing writes, and every
  Improve `complete` would be refused forever.
- **`delegation: ask-agent` is not gated.** A fresh worker runs the review there, outside this session's hooks.
- **"After the packet was emitted"** is the mtime of the child's `start.json`, written before the packet that names the call and
  rewritten by `improve-start --restart-stopped` (a restarted review needs a new call). The packet file itself is rewritten by every
  `next`, which would void a call made before a context reset.
- **The not-enforced note is said after the import is accepted**, not before: a refusal's first line is the fix
  (`parent-return.md`), and a notice printed first displaced it in six existing tests.
- **No hash-frozen text changed:** `improve_start_contract` and the Improve packet wording are untouched; packets are byte-identical
  to 398466a3 on node-fix-bug (12 packets, 157,514 characters before and after, rendered at equal path lengths).

## Open

- The live measurement: a Claude run through several Improve stages, to see the invocation rate move from 1 of 4 and whether a model
  that is refused follows the named exit. Not run here (no live E2E).
- A subagent's Skill calls are recorded with their `agent_id` under the parent's session id; this was reasoned from the existing
  subagent handling, not measured.
- Not enforced anywhere but Claude Code inline runs (Grok, Codex, Cursor, OpenCode have no Skill-tool hook; `ask-agent` runs the
  review elsewhere). The note says so once per run.

## Adversarial review before release (2026-10-16)

A read-only reviewer ran the merged branch (release worktree, probes kept under the session scratchpad `review/`). No P0.

| Finding | Status | Evidence |
|---|---|---|
| P1: a Codex or Cursor process started from a Claude shell inherits `CLAUDECODE` and `CLAUDE_CODE_SESSION_ID`, so a Claude session bound to the same run gated it, and it has no Skill tool to satisfy the gate. | **Fixed:** `NESTED_NON_CLAUDE` (`CODEX_SANDBOX`, `CODEX_THREAD_ID`, `CURSOR_PLUGIN_ROOT`) is checked in `skill_gate`; an OpenCode marker is not known, so an OpenCode started from a bound Claude shell is still gated (open). | `test_codex_or_cursor_started_from_a_bound_claude_shell_is_not_gated` (fails on the old source). |
| P3: the refusal's named command was the bare `complete`, so a model following it literally dropped its `--final-result`, `--notes` or `--no-commit`. | **Fixed:** the refusal says those flags belong on the command too (`then run: ` still ends the first line). | `test_without_a_record_the_import_is_refused_and_the_named_fix_accepts_it` (fails on the old source). |
| P3: closed stdin or strict-UTF-8 bytes made the hook entry exit 1 with a traceback. | **Fixed** in `hook_main` (shared with observe and stop): an unreadable stdin is an empty payload. | `test_the_entry_script_survives_a_closed_stdin_and_bytes_that_are_not_text` (fails on the old source). |
| P2: `skill_hook` is judged from the configuration on disk, not from what the live session registered; a mid-session `shiploop-hook install` or a changed tool name leaves an unsatisfiable gate. | Known limit, not changed (the `SHIPLOOP_KEEPALIVE=off` exit and a fresh session exist). | Code reading only. |
| P2: a Skill call before the session was bound, a subagent with its own session id, and a user-typed `/improve` leave no record. | Known limits; the exit is a repeat call in the main session. | Probes `skill-then-bind-then-complete`, `subagent-own-session-id`. |
| P3: `start.json` rewritten after the call voids it; an argument past 2000 characters is cut; `evilplugin:improve` counts as improve; clearing `CLAUDECODE` in the `complete` environment skips the gate; a FIFO at `skill-calls.jsonl` blocks. | Known, adversarial only; not changed. | Probes. |

Open for the live round: whether a Claude model refused here follows the named exit; the invocation rate against 1 of 4.
