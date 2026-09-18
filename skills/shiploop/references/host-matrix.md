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
| Codex | `$shiploop:shiploop` | `shiploop@skill-craft-market` |
| Claude Code | `/shiploop:shiploop` | `shiploop@skill-craft-market` |
| Grok | Select the installed plugin's ShipLoop skill | Native marketplace package |
| Cursor | Select the installed plugin's ShipLoop skill | Native marketplace package |
| Hermes | Select the installed ShipLoop card | Host-supported materialized package |

The marketplace name identifies the catalog; the plugin name supplies the
Codex/Claude skill namespace. Keep one discovered installation per skill.
Skill-directory installations are a separate distribution mode and do not
establish that a marketplace package was selected. Inspect the loaded card's
absolute path and plugin identity when validating an installation.

Package leaf: **shiploop**. All hosts execute the same Python 3 CLI and
interpret its returned action. No host-specific `/goal` invocation is needed.
Stored DAG prompts retain the planning grammar but are instructions for the
host, not permission to bypass ShipLoop's action cursor.

New runs use navigator protocol 3. `next` rehydrates the current owner and action
from authoritative Markdown. Submit the exact callback printed in that packet;
retained older modes follow their recorded protocol rather than a guessed
conversion.

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
