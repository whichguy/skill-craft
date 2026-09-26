# Keepalive: keep a run moving across host turns

The ShipLoop script decides the next step, but the host decides when a turn
ends. A model that reports progress and ends its turn leaves an active run idle
until someone prompts again. Keepalive closes that gap from the host side. It is
optional; runs work without it.

## Parts

| Part | What it does |
|------|--------------|
| Packet marker | Every packet prints `Keepalive marker: SHIPLOOP-RUN run=<id> rev=<n> dir=<run dir>`. |
| `shiploop hook-status --run-dir DIR` | Read-only, lock-free JSON: `status`, `stage`, `action`, `revision`, `repo`, `next`. Exit 2 with an `error` field when the run cannot be read. |
| `scripts/shiploop-hook observe` | After a shell command: if the output has a marker whose run id matches the live run, bind this host session to that run. |
| `scripts/shiploop-hook stop` | When the host is about to end a turn: while the bound run is `active` and its revision moved since the last refusal, refuse the stop and name the run's next command. |
| `scripts/shiploop-drive` | Outer driver for unattended runs: starts or resumes host sessions until the run is not active. |

`hook-status` is the only place that decides whether a run can move. The hooks
and the driver never read `state.md` themselves.

## Stop decisions

| Run state | Hook reply |
|-----------|------------|
| `active`, revision moved since the last refusal | Refuse the stop; the reason names `shiploop next --run-dir …`. |
| `active`, revision unchanged since the last refusal | Allow, with a notice that the run made no progress. |
| `paused`, `blocked`, `halted`, `done` | Allow and drop the binding. |
| No binding, unreadable run, hook error | Allow. Hooks fail open. |
| Grok session-end stop, subagent stop | Allow. |

A user stops a run by asking to stop or pause: the agent runs the packet's pause
command, the run becomes `paused`, and the next stop is allowed. A question about
the loop is not a stop. Host interrupts (Ctrl+C, Esc) skip stop hooks entirely.
`SHIPLOOP_KEEPALIVE=off` in the host's environment disables the hooks.
Each stop decision is appended to
`${XDG_STATE_HOME:-~/.local/state}/shiploop/keepalive/decisions.log` with its
reason, and hook failures to `errors.log` beside it.

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
`keepalive-stop` on `turn-end`), and the package generator writes each host's
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
| Claude Code | `~/.claude/settings.json` (`PostToolUse` Bash, `Stop`) | `{"decision":"block","reason":…}` | Hook alone keeps `claude -p` going. |
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
(exit 4), or at `--max-sessions` (exit 5). It keeps one JSON line per session in
`drive.log` and each session's output under
`${XDG_STATE_HOME:-~/.local/state}/shiploop/keepalive/drive/<run id>/`, never in
the run directory.
