# Bootstrap — host-local engine

The **devloop-run** card does not vendor the full engine in the monorepo. On first
`--setup` (or first real invoke), it can materialize an engine under:

```text
${DEVLOOP_DATA_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}}/devloop
```

## Pin file

Default: card-local `references/engine-pin.json` (override with `DEVLOOP_ENGINE_PIN`).

```json
{
  "version": "0.1.0",
  "url": "https://…/devloop-engine-0.1.0.tar.gz",
  "sha256": "<hex>",
  "tarball": "devloop-engine-0.1.0.tar.gz"
}
```

- **https://** downloads require `sha256` (pin or `DEVLOOP_ENGINE_SHA256`); mismatch fails closed.
- **file://** accepts a `.tgz` (optional sha recommended); absolute path after `file://`.
- Placeholder URLs containing `REPLACE_WITH` are treated as unset (seed path only).

## Sources (first match)

1. **`DEVLOOP_BOOTSTRAP_CMD`** — command that installs into `$1` (tests / custom ops)
2. **`DEVLOOP_ENGINE_URL`** or pin **url** — `file:///path/to.tgz` or `https://…tgz`
3. **Seed copy** from an existing valid engine at Hermes / `/opt/data` (no network)

Never writes into Hermes skillhub leaf `devloop` (foreign engine tree).

## Safety

| Guard | Behavior |
|-------|----------|
| sha256 | Required for non-file https; mismatch → exit 2, no install |
| Safe extract | Rejects `..`, absolute paths, unsafe links; flattens one top-level package dir |
| Marker last | `.skill-craft-engine.json` written after entrypoint validates |
| Lock | `mkdir` lock dir under data parent (portable; no flock); re-check engine after acquire |
| Unmarked force | `--force-bootstrap` alone refuses replace without marker; need `--force-hard` |

## Flags

| Flag | Effect |
|------|--------|
| `--setup` | Ensure engine; bootstrap if needed; print path |
| `--no-bootstrap` | Fail closed if missing |
| `--force-bootstrap` | Rebuild host-local tree (marker-owned only) |
| `--force-hard` | Allow replace of unmarked host-local tree |
| `--probe` | Resolve only (no bootstrap); use `--setup` to materialize |

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

## Packaging a release

```sh
./scripts/package-devloop-engine.sh --from /path/to/engine --version 0.1.0 --out dist
# → dist/devloop-engine-0.1.0.tar.gz + .sha256 + pin fragment
# Publish tarball as a GitHub Release asset; update references/engine-pin.json url+sha256
```
