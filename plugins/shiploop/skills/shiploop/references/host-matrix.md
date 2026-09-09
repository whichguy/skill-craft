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

Package leaf: **shiploop**. Reprint and closer are `/shiploop next` and
`/shiploop complete` on this leaf.

Grok cannot invoke `/goal` from this skill. The packet Next **is** the
until-loop in the parent chat. Every `/shiploop next` / `complete` rehydrates
from `.shiploop/` files; the skill holds no inner A/B. When done is if/else
on facts not in files (`produces` true? this cycle trivial?). Complete a
running implement step with `--inner-loop parent --improve <line>` (Grok
default). Use `--inner-loop goal --improve <line>` only if this host actually
ran `/goal`. Emitted policy requires evidence; `--improve` does not dest-verify
the claim. The script never auto-advances from git dirty/HEAD moved.

| Claim | Requires |
|-------|----------|
| Packaged multi-host | install + hermetic tests green |
| Runtime verified on H | a live `init`/`next`/`complete` run on H |
