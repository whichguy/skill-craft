# Bootstrap — host-local engine

The **devloop-run** card does not vendor the full engine in the monorepo. On first
`--setup` (or first real invoke), it can materialize an engine under:

```text
${DEVLOOP_DATA_HOME:-${XDG_DATA_HOME:-$HOME/.local/share}}/devloop
```

## Sources (first match)

1. **`DEVLOOP_BOOTSTRAP_CMD`** — command that installs into `$1` (tests / custom ops)
2. **`DEVLOOP_ENGINE_URL`** — `file:///path/to/tree`, `file:///path/to.tgz`, or `https://…tgz`
3. **Seed copy** from an existing valid engine at Hermes / `/opt/data` paths (no network)

Never writes into Hermes skillhub leaf `devloop` (foreign engine tree).

## Flags

| Flag | Effect |
|------|--------|
| `--setup` | Ensure engine; bootstrap if needed; print path |
| `--no-bootstrap` | Fail closed if missing |
| `--force-bootstrap` | Rebuild host-local tree |
| `--probe` | Resolve only (no bootstrap unless combined with missing+invoke path; use `--setup` to force materialize) |

## Marker

Host-local installs write `.skill-craft-engine.json` (schema 1) for provenance.
