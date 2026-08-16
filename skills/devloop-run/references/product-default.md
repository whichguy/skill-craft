# Product default — DevLoop

## Rule

**Default DevLoop** = the **engine** via the user-facing skill **`devloop`**
(package leaf `devloop-run`; `scripts/devloop-run` → `scripts/devloop_cli.py`).

Harnesses (Grok, Claude, Codex, Cursor, Hermes chat) are **shims only**: resolve,
bootstrap if needed, exec the engine, report exit codes and receipts.
They must **not** reimplement DEFINE / PROVE / BUILD / DELIVER+LEARN.

## Package leaves

| Leaf | Role |
|------|------|
| `devloop` | **User-facing** skill / slash on Grok, Claude, Codex, Cursor (`~/.<host>/skills/devloop`) |
| `devloop-run` | **Source** portable card + shim (`skills/devloop-run`, `scripts/devloop-run`). Hermes card dest stays this name |
| `devloop` (Hermes engine) | **Reserved** Hermes skillhub engine path — never a skill-craft `skills/devloop` package |
| `devloop-native` | **Demoted** optional offline evidence gates (freeze/prove/stop). Not DevLoop default |

## Grok parity (target)

Grok completion of a real loop must work with:

- Host-local engine (`~/.local/share/devloop` or `DEVLOOP_HOME`)
- Grok model transport (`DEVLOOP_TRANSPORT=grok` / host affinity)
- **No** `HERMES_BIN` and **no** `~/.hermes/.../devloop` required at runtime

**Host affinity (shipped in card):** `DEVLOOP_HOST=grok` (or `--host grok`) never
selects the live Hermes leaf unless `DEVLOOP_ALLOW_HERMES_SEED=1`. Nested invoke
(`DEVLOOP_DEPTH`≠0) exits 2. Full engines without a declared `grok` transport
capability fail closed at invoke (override: `DEVLOOP_ALLOW_LEGACY_ENGINE=1`).

Pin 0.2.0 declares `transports: ["hermes","grok"]`. Until a matching host-local
engine is bootstrapped, the card must fail closed with exit **2** and next steps —
not fall back to host-agent improvisation or `devloop-native`.

**Write-safe:** prefer `DEVLOOP_WRITE_SAFE_ROOT`; host-local default under
`$XDG_STATE_HOME/devloop` (not `/opt/data` unless that path is a writable container root).

## Agent procedure (card)

The handshake is [SKILL.md](../SKILL.md): review session MCP for a
read-capable oracle **before interpolating or planning**, print
`mcp-considered`, interpolate argv, exec the shim. Every run is an
independent engine worktree. COMPLETE is `AFTER exec exit=0` only.
The Grok `/devloop` slash is [commands/devloop.md](../commands/devloop.md)
(installed to `~/.grok/commands/devloop.md`).

1. Banner: `DevLoop — mode=engine host=<host> engine=<path-or-pending>`
2. `SKILL_ROOT` = directory containing the installed `SKILL.md`
3. User form: `/devloop <plain English>` (headless:
   `grok -p '/devloop <plain English>' --always-approve`)
4. **COMPLETE** only when engine exit is 0 **and** the shim printed
   `AFTER exec exit=0`. Exit 2 is not success.

**Forbidden:** host-written charters as the acceptance path; host BUILD;
inventing a fourth argv piece; invoking the host goal harness or `/loop`
to drive DevLoop; suggesting `devloop-native` as “DevLoop.”
