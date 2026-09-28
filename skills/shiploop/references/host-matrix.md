# ShipLoop host matrix

**Status:** script-managed graph and state; the invoking conversation executes work.

**Honesty:** discovery (skill installed) ≠ a live `.shiploop/` run.

## CLI working directory

Bind the CLI from the selected, loaded [skill card](../SKILL.md), and pass
absolute repository and run-directory paths. For isolated work, execute product
commands in the returned worktree. Changing the process working directory does
not create or move a model conversation. Follow the selected card's `workspace
start` or `init` instructions and each returned command exactly.

| Host | Marketplace invocation | Selected package |
|------|------------------------|------------------|
| Codex | `$skill-craft:shiploop` | `skill-craft@whichguy` |
| Claude Code | `/skill-craft:shiploop` | `skill-craft@whichguy` |
| Grok | Select the installed plugin's ShipLoop skill | Native marketplace package |
| Cursor | Select the installed plugin's ShipLoop skill | Native marketplace package |
| Hermes | Select the installed ShipLoop card | Host-supported materialized package |

The marketplace name identifies the catalog; the plugin name supplies the
Codex/Claude skill namespace. Every skill-craft skill ships in the one
`skill-craft` plugin, so ShipLoop and Improve install together. Keep one discovered installation per skill.
Skill-directory installations are a separate distribution mode and do not
establish that a marketplace package was selected. Inspect the loaded card's
absolute path and plugin identity when validating an installation.

Package leaf: **shiploop**. All hosts execute the same Python 3 CLI and
interpret its returned action. No host-specific `/goal` invocation is needed.
Stored DAG prompts retain the planning grammar but are instructions for the
host, not permission to bypass ShipLoop's action cursor.

New runs use navigator protocol 4, the only protocol. `next` rehydrates the current owner and action
from authoritative Markdown. Submit the exact callback printed in that packet.
A saved run from a retired protocol or mode is refused with an error that names
it; start a fresh run rather than guessing a conversion.

The invoking conversation performs the producer work, then follows the selected
Improve skill and its bound Until Loop runtime. ShipLoop imports accepted child
evidence and chooses the next graph action. It does not launch a model process.
Never infer a transition from Git dirt or changed HEAD.

Only one step is active. Worktree creation is local and does not re-root the
host conversation. Host-specific runtime certification still requires a live
run on that host; hermetic CLI tests are not proof of that certification.

| Claim | Requires |
|-------|----------|
| Packaged multi-host | install + hermetic tests green |
| Runtime verified on H | a live `init`/`next`/`complete` run on H |

## Sandbox write grants

An isolated run writes to two places outside a strict sandbox's default reach:
the `<repo-parent>/.shiploop-runs` parent (worktree and run state) and the
repository's shared Git directory (`git worktree add` and every commit). Start
and every later run-bound command try one real write in each and exit **3** with
a `SHIPLOOP-GRANT-NEEDED` block when refused. Nothing is created first.

Observed on 2026-09-27 (evidence: `docs/shiploop-grant-preflight-journal.md`):

| Host and mode | `.shiploop-runs` | `.git` (repo is cwd) | Grant that fixed it |
|---|---|---|---|
| Claude, default (no Bash sandbox) | writable | writable | none needed |
| Claude, Bash sandbox on | refused | writable | `--add-dir` (mid-session: `/add-dir`) |
| Codex `workspace-write` (its default) | refused | **refused** (kept read-only) | `-c 'sandbox_workspace_write.writable_roots=[runs, .git]'`; mid-session `/permissions` |
| Grok, sandbox off (its default) | writable | writable | none needed |
| Grok `--sandbox workspace` | refused | writable | restart with a `~/.grok/sandbox.toml` profile adding both; no mid-session change |

Grant the stable `.shiploop-runs` parent, not a single run's root, so one grant
covers later runs. The script names the host from `CODEX_SANDBOX`/`CODEX_THREAD_ID`,
then `GROK_AGENT`, then `CLAUDECODE`, innermost first, because a nested host
inherits its launcher's variables. Granting is the user's decision.
