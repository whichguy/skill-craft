# Keepalive: keep a run moving across host turns

The ShipLoop script decides the next step, but the host decides when a turn
ends. A model that reports progress and ends its turn leaves an active run idle
until someone prompts again. Keepalive closes that gap from the host side. It is
optional; runs work without it.

## Parts

| Part | What it does |
|------|--------------|
| Packet marker | Every packet prints `Keepalive marker: SHIPLOOP-RUN run=<id> rev=<n> dir=<run dir>`. |
| `shiploop hook-status --run-dir DIR` | Read-only, lock-free JSON: `status`, `stage`, `action`, `revision`, `progress`, `repo`, `next`, and what the stop asks for: `loop` (the innermost Until Loop's `kind`, `status`, `iteration` and read-only `next`), `callback` (the step's `complete` command) and `delegation`. Exit 2 with an `error` field when the run cannot be read. |
| `scripts/shiploop-hook observe` | After a shell command: if the output has a marker whose run id matches the live run, and the command was a ShipLoop command that drives the run (`workspace start`, `init`, `next`, `resume`, `complete`, the Improve bind/complete/reconcile verbs), bind this host session to that run. A marker printed by any other command (reading a packet file, a log or a transcript) never binds; hosts that do not report the command keep marker binding. |
| `scripts/shiploop-hook stop` | When the host is about to end a turn: while the bound run is `active` and its revision moved since the last refusal, refuse the stop and name the run's next command. |
| `scripts/shiploop-hook skill` | After a Skill-tool call (Claude Code only): append the call to the bound run's `skill-calls.jsonl`. It never blocks the call; see [Skill calls](#skill-calls-claude-code-only). |
| `scripts/shiploop-drive` | Outer driver for unattended runs: starts or resumes host sessions until the run is not active. |

`hook-status` is the only place that decides whether a run can move.

If a host session prints a second packet while its keepalive has never bound
that run, the packet command warns once on stderr ("ShipLoop keepalive is not
active in this <host> session") with the host's fix, such as restarting Grok so
its leader loads the plugin hooks. A session that was bound and later released
does not warn. Its
`progress` field is `<revision>.<callback attempts>.<loop iteration>`: an accepted
result, a refused callback (the model is fixing and resubmitting) and each reported
iteration of the innermost Until Loop (an active Improve review's, else the current
inner stage's) all count as progress, so a long review, a stage's loop or a fix
loop is not mistaken for a stall. Running `next` binds the run again but is not
progress: a re-bind of the same run keeps the stop's memory. No count of
continuations without an accepted result releases the turn: only a host's own cap
(Grok's, below) ends one.

Each stop also counts the turn's continuations (the host's `stopHookActive` /
`stop_hook_active` flag marks a continuation). Grok ends a turn after 8
continuations; from the 6th the reason asks harder not to stop, and the
decision log records `continuation N/8`. When Grok does end the turn, one
"continue" resumes the run. The hooks
and the driver never read `state.md` themselves.

## Stop decisions

| Run state | Hook reply |
|-----------|------------|
| `active`, progress moved since the last refusal | Refuse the stop; the reason names the report the run is owed: while the step's Until Loop is active, its next iteration report (the receipt's read-only `next_argv`); once a stage's loop has ended, the step's `complete` callback; otherwise, and always under `delegation: ask-agent`, `shiploop next --run-dir …`. Every reason also names `next` for a model that lost context. |
| `active`, a host background task still running | Refuse the stop; the reason says to wait for the task in this turn. |
| `active`, progress unchanged since the last refusal | Allow, with a notice that the run made no progress. |
| `paused`, `blocked`, `halted`, `done` | Allow quietly and drop the binding. A `blocked` run waiting on the user (`awaiting` in hook-status) stays stopped until the user's reply resumes it. |
| No binding, unreadable run, hook error | Allow. Hooks fail open. |
| Grok session-end stop, subagent stop | Allow. |

A user stops a run by asking to stop or pause: the agent runs the packet's pause
command, the run becomes `paused`, and the next stop is allowed. The script
refuses a pause whose reason is context housekeeping (a clear, a context
boundary, compaction, a fresh conversation), and the decision log records each
pause's reason. A question about the skill, the loop or its cost is neither a
stop nor a resume, and neither is "continue" when the run is waiting on the
user: `resume` then requires `--answer "<their words>"` (a decision) or
`--observed "<what they reported>"` (steps only a person could take, or the
output of an outside service's check once it exits 0), and refuses a bare
"continue". The reply is recorded in `decisions/<action>.md` and shown in
the next packet. Host interrupts (Ctrl+C, Esc) skip stop hooks entirely.
`SHIPLOOP_KEEPALIVE=off` in the host's environment disables the hooks.

No hook is needed after a host compacts context: `next`, the recovery command
every stop reason names, always rewrites the full packet file and prints its head.
Each stop decision is appended to
`${XDG_STATE_HOME:-~/.local/state}/shiploop/keepalive/decisions.log` with its
reason, and hook failures to `errors.log` beside it.

## Skill calls (Claude Code only)

A packet says to invoke the improve skill (the Skill tool, skill `improve`, the argument it prints) at every Improve
stage, and a model that does not leaves a review the skill never ran. Wording did not change that in live runs, so a hook
records the calls and the Improve stage's `complete` checks them.

- **The record.** `scripts/shiploop-skill-call` (the `skill-calls` hook, event `after-skill`, a `PostToolUse` hook matching
  `Skill`) appends one JSON line to the bound run's `skill-calls.jsonl`: `ts` and `at`, `skill` (normalised, so
  `skill-craft:improve` is `improve`), `called_as`, `args` (cut at 2,000 characters), `session`, `tool_use_id` and, for a
  subagent, `agent_id`. Only a session the keepalive hooks bound to the run writes it, only a regular file inside that run
  directory, and the hook is silent and never blocks the call. The file is evidence, not state, and is append-only.
- **The gate.** `complete --action=<improve id>` refuses until the record holds a call to `improve` made after that Improve
  stage started (the child's `start.json`) whose `args` carry the stage's handoff path or its action id; quoting is ignored.
  The refusal's first line names the fix: invoke the Skill tool with skill `improve` and the printed argument, let it
  finish, run `complete` again.
- **When it does not apply.** The gate holds only when this command runs in a Claude Code session whose hooks bound this
  run and whose hooks include the Skill-call hook (the bind records that as `skill_hook`, judged from the hook
  configuration the hook was loaded from, so an install from before this hook never holds a run to a record nothing
  writes). It also does not apply under `delegation: ask-agent` (a fresh worker runs the review, out of this session's
  hooks), on Grok, Codex, Cursor or OpenCode, with no hooks installed, or with `SHIPLOOP_KEEPALIVE=off`. Then `complete`
  accepts the review on the Improve runtime's own receipt and, once the import is accepted, says so once per run (stderr,
  and a `gate` line in the record).

## Several agents on one run

ShipLoop's run lock already serializes CLI commands. Keepalive adds one rule:
only the run's owner session is ever kept alive.

- The first session to bind a free run owns it. A parallel-chain worker, a
  second terminal or any other session that binds the same run is let go at its
  turn end ("another session owns this run").
- Ownership is released when the owner's turn ends normally, when the driver
  finishes a session, or after 30 minutes with no hook activity from the owner
  (a closed or crashed session). Any tool call by the owner refreshes the claim.
- Subagent tool calls (Claude `agent_id`, Grok `subagentType`) never bind; the
  parent owns the run.
- Every read-modify-write of a binding or owner record holds an exclusive file
  lock, and two registrations of one host for the same stop (for example a
  plugin and `shiploop-hook install`) get the same answer.
- Only one `shiploop-drive` runs per run; a second one exits with code 3.

## Hosts

A marketplace install of the ShipLoop plugin carries the hooks. ShipLoop
declares them in `host-hooks.json` (`keepalive-observe` on `after-shell`,
`keepalive-stop` on `turn-end`, and for Claude Code only `skill-calls` on `after-skill`), and the package generator writes each host's
own file: `hooks/hooks.json` for Claude and Grok, `hooks/codex.json`,
`hooks/cursor.json`. Their argument-free entry scripts
(`scripts/shiploop-keepalive-observe`, `scripts/shiploop-keepalive-stop`) run
`shiploop-hook … --host auto`, which tells Grok (`GROK_PLUGIN_ROOT`), Cursor
(`CURSOR_PLUGIN_ROOT`), Codex and Claude apart. Claude Code runs them as
installed. Codex asks you once, in an interactive session, to trust the new
plugin hooks; approve the ShipLoop entries.

Grok (1.0.41) lists a plugin's hooks but never runs them, headless or
interactive, even for a plugin installed with `--trust` (observed 2026-09-25).
So ShipLoop installs its Grok hooks itself: any `shiploop` command that runs
under Grok (`GROK_AGENT=1`, which Grok sets for every shell command) writes
`~/.grok/hooks/shiploop-keepalive.json` when it is missing, or repairs it when
its script is gone, and says so on stderr. Global hooks are always trusted. New
Grok sessions load them; a session that is already open picks them up from
`/hooks`, then `r`. `SHIPLOOP_KEEPALIVE=off` skips this, and
`scripts/shiploop-hook uninstall --host grok` removes it.

A skill-directory install adds them with `scripts/shiploop-hook install --host HOST`
(repeat `--host`; `status` and `uninstall` take the same form), the only route
for OpenCode. `install.sh` never writes host hook config. Use one route per host.
Hermes is not supported.

| Host | Registered in | Continue signal | Unattended (headless) |
|------|---------------|-----------------|-----------------------|
| Claude Code | `~/.claude/settings.json` (`PostToolUse` Bash and Skill, `Stop`) | `{"decision":"block","reason":…}` | Hook alone keeps `claude -p` going. |
| Codex | `~/.codex/hooks.json` (`PostToolUse`, `Stop`); approve once when Codex asks | `{"decision":"block","reason":…}` | Hook alone keeps `codex exec` going. |
| Grok | `~/.grok/hooks/shiploop-keepalive.json`, written by ShipLoop on its first command under Grok | `{"decision":"block","reason":…}`; at most 8 per turn | Hook alone keeps `grok -p` going. |
| Cursor | `~/.cursor/hooks.json` (`afterShellExecution`, `stop`) | `{"followup_message":…}` | `cursor-agent -p` never fires `stop`: use `shiploop-drive`, which resumes the chat. |
| OpenCode | `~/.config/opencode/plugins/shiploop-keepalive.js` | The plugin sends the next message on `session.idle` | `opencode run` exits first: use `shiploop-drive`, which resumes the session. |

Grok also runs `~/.cursor/hooks.json` and a project's `.claude/settings.json`.
The hook recognizes the sending host from its payload and leaves an event to that
host's own entry, so one event is decided once.

## Driver

```sh
scripts/shiploop-drive --host claude --run-dir RUN -- --model sonnet --max-budget-usd 10
```

Arguments after `--` go to the host command unchanged; the driver adds no
permission flags. Each session gets the run's next command as its prompt and runs
in the run's repository. Cursor and OpenCode resume the session bound to the run;
the other hosts start a fresh session each time, so every session begins with a
clean context.

The driver stops when the run is not active (exit 0 when done, 3 when paused,
blocked or halted), when a host exits non-zero without advancing the run (exit 4,
often a host that could not start), after two sessions in a row without progress
(exit 4), or, only when you pass `--max-minutes N`, once N minutes of wall clock
have passed (exit 5; a session's timeout is cut to the time left). There is no
ceiling by default: runs are meant to go on for a long time. It keeps one JSON line per session in
`drive.log` and each session's output under
`${XDG_STATE_HOME:-~/.local/state}/shiploop/keepalive/drive/<run id>/`, never in
the run directory.
