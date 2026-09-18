# ShipLoop host matrix

**Status:** session dispatcher.

**Honesty:** discovery (skill installed) ≠ a live `.shiploop/` run.

## CLI working directory

When exec'ing the harness, set the **process** working directory to
`repo_root` (or the running step's worktree during implement). Do not exec
from `$HOME`. `init --repo PATH` then writes `PATH/.shiploop`; later
`next` / `complete` / `status` can walk from that cwd. This is process cwd,
not re-rooting the host chat (`move_agent_to_root`).

| Host | Install | Discovery path | Invoke (typical) | Runtime smoke |
|------|---------|----------------|------------------|---------------|
| Grok | symlink | `~/.grok/skills/shiploop` | `/shiploop` | pending |
| Claude Code | symlink + plugin view | `~/.claude/skills/shiploop` | `/shiploop` | pending |
| Hermes | materialize-copy | `…/software-development/shiploop` | `/shiploop` | pending |
| Codex | symlink | `~/.codex/skills/shiploop` | `/shiploop` | pending |
| Cursor | symlink | `~/.cursor/skills/shiploop` | `/shiploop` | pending |

Package leaf: **shiploop**. All hosts execute the same Python 3 CLI and
interpret its returned action. No host-specific `/goal` invocation is needed.
Stored DAG prompts retain the planning grammar but are instructions for the
host, not permission to bypass ShipLoop's action cursor.

Version 0.9 requires `complete --action ID --result /absolute/result.md`.
Bare completion, `--trivial`, `--advance`, and `--inner-loop` overrides are
not supported. `next` rehydrates the exact current action from authoritative
Markdown. `context` pages only the current step or iteration when needed.

The script executes lint/test manifests, checks their freshness, binds each
iteration to a distinct verbose learning commit, and gates merging on two
trivial-only passes plus fresh final verification and a broader-plan decision.
The host still judges test meaningfulness and materiality. Follow the exact
printed command; never infer a transition from Git dirt or changed HEAD.

Only one step is active. Worktree creation is local and does not re-root the
host conversation. Host-specific runtime certification still requires a live
run on that host; hermetic CLI tests are not proof of that certification.

| Claim | Requires |
|-------|----------|
| Packaged multi-host | install + hermetic tests green |
| Runtime verified on H | a live `init`/`next`/`complete` run on H |
