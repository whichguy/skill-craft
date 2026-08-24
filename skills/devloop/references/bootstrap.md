# Bootstrap — host-local engine

The **devloop** card does not vendor the full engine in the monorepo. On first
`--setup` (or first real invoke), it can materialize an engine under:

```text
${DEVLOOP_DATA_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}}/devloop
```

## Pin file

Default: card-local `references/engine-pin.json` (override with `DEVLOOP_ENGINE_PIN`).

```json
{
  "version": "0.2.0",
  "url": "https://github.com/whichguy/skill-craft/releases/download/devloop-engine-v0.2.0/devloop-engine-0.2.0.tar.gz",
  "sha256": "<hex>",
  "tarball": "devloop-engine-0.2.0.tar.gz",
  "transports": ["hermes", "grok"]
}
```

- **https://** downloads require `sha256` (pin or `DEVLOOP_ENGINE_SHA256`); mismatch fails closed.
- **file://** accepts a `.tgz` (optional sha recommended); absolute path after `file://`.
- Placeholder URLs containing `REPLACE_WITH` are treated as unset (seed path only).

## Sources (first match)

1. **`DEVLOOP_BOOTSTRAP_CMD`** — command that installs into `$1` (tests / custom ops)
2. **`DEVLOOP_ENGINE_URL`** or pin **url** — `file:///path/to.tgz` or `https://…tgz`
3. **Seed copy** from Hermes / `/opt/data` — **only** when host is `hermes`/`auto` or
   `DEVLOOP_ALLOW_HERMES_SEED=1` / `--allow-hermes-seed`

Never writes into Hermes skillhub leaf `devloop` (foreign engine tree).

## Host affinity (Grok parity)

| Host (`DEVLOOP_HOST` / `--host`) | Hermes leaf in resolve | Hermes seed bootstrap |
|----------------------------------|------------------------|------------------------|
| `grok`, `claude`, `codex`, `cursor`, `auto` | **No** (default) | Only with allow flag |
| `hermes` | Yes | Yes |

On **invoke** (not `--setup`/`--probe`):

- Nonzero `DEVLOOP_DEPTH` / `DEVLOOP_NESTING` → exit **2** (anti re-entry).
- `host=grok` requires `GROK_BIN` or `grok` on PATH; exports `DEVLOOP_TRANSPORT=grok`.
- `host=cursor|claude|codex` (and `auto` + a full engine) require an **explicit**
  `DEVLOOP_TRANSPORT=grok` or `=hermes`. Unset transport does **not** fall through
  to Hermes chat. Use Grok `/devloop`, or set transport + `GROK_BIN` / Hermes
  explicitly.
- Full engines without declared `transports` including `grok` → exit **2** until a
  Grok-capable pin ships (override: `DEVLOOP_ALLOW_LEGACY_ENGINE=1`, unsupported).
- Error text must **not** suggest `evidence-gates` as DevLoop.

## Safety

| Guard | Behavior |
|-------|----------|
| sha256 | Required for non-file https; mismatch → exit 2, no install |
| Safe extract | Rejects `..`, absolute paths, unsafe links; flattens one top-level package dir |
| Marker last | `.skill-craft-engine.json` written after entrypoint validates |
| Lock | `mkdir` lock dir under data parent (portable; no flock); re-check engine after acquire |
| Atomic swap | Previous host-local generation parked until `mv` succeeds; restore on failure |
| Unmarked force | `--force-bootstrap` alone refuses replace without marker; need `--force-hard` |

## Flags

| Flag | Effect |
|------|--------|
| `--setup` | Ensure engine; bootstrap if needed; print path |
| `--no-bootstrap` | Fail closed if missing |
| `--force-bootstrap` | Rebuild host-local tree (marker-owned only) |
| `--force-hard` | Allow replace of unmarked host-local tree |
| `--probe` | Resolve only (no bootstrap); use `--setup` to materialize |
| `--host NAME` | Force affinity: `grok\|hermes\|claude\|codex\|cursor\|auto` |
| `--allow-hermes-seed` | Allow Hermes leaf seed on non-Hermes hosts |

## Marker

Host-local installs write `.skill-craft-engine.json` (schema 1) for provenance:

```json
{
  "schema": 1,
  "mode": "host-local",
  "source": "<url or seed path>",
  "version": "<pin version>",
  "sha256": "<if known>",
  "timestamp": "UTC ISO"
}
```

Pins that ship Grok parity **must** include `"transports": ["hermes", "grok"]`.
The card refuses `host=grok` bootstrap when the pin lists transports without `grok`.

## Host detection (skill-dir symlinks)

`install.sh` puts a **symlink** at `~/.grok/skills/devloop` (source leaf
`devloop`). File lookup uses
`pwd -P` (physical checkout). Host affinity uses the **logical** invoke path
(`BASH_SOURCE` / `pwd` without `-P`) so Grok skill-dir installs detect `host=grok`
and skip Hermes seed. Tests: D26 in `test/devloop-run.test.sh`.

## Packaging a release

Default publish surface: **skill-craft** GitHub Release tags `devloop-engine-v*`
(not a separate `devloop-engine` repo unless deliberately migrated).

```sh
./scripts/package-devloop-engine.sh --from /path/to/engine --version 0.1.1 --out dist
# → dist/devloop-engine-0.1.1.tar.gz + .sha256 + pin fragment
# Deny-check fails if staged tree contains /Users/, /home/, .hermes/profiles, etc.
# Publish tarball as a GitHub Release asset; update references/engine-pin.json url+sha256
```

## Runtime honesty

| Host | Model transport |
|------|-----------------|
| Hermes | Hermes chat (`HERMES_BIN`) — default on that host |
| Grok | **Grok transport required** (`transports` includes `grok` in pin 0.2.0). Hermes must **not** be required. Missing grok transport → exit 2, never reimplement the loop in the host agent. |
| Claude/Codex/Cursor | Resolve/bootstrap; invoke without explicit `DEVLOOP_TRANSPORT=grok\|hermes` → exit 2 (no auto-Hermes) |

Card bootstrap/probe is multi-host. Completing a full engine loop without the matching
transport is a **fail-closed** state — never fall back to `evidence-gates` as DevLoop.
