# Session MCP consider

**Review session MCP before planning.** **Inventory** this session (no
catalog, no install). Prefer a matching **read-capable** tool over inventing
operator tooling. Read-capable = observes the *external* truth in the
done-sentence (deployed URL, live exec, hosted artifact, remote API). A
generic **fs-only** MCP seeing `result.txt` does **not** count. Transient
errors: retry once, then unmatched. Never silent-skip a match.

Reuse a pre-existing CLI/wrapper. **Do not invent a new harness**
(`scripts/*.mjs`). If none: local content-checking `verify_cmd` plus a
concrete request constraint, or fail-closed and ask for a checkable CLI.

**Observe, not act.** Do not implement the product through MCP. Never
fix-then-recheck on the host. **New operator tooling** = committed harness
scripts. Inline `test "$(cat result.txt)" = …` is not tooling.

Print **always**, first matching read-capable tool in session order:

```text
mcp-considered: <server>(<first-matching-read-tool>) | none(<reason>)
mcp-considered: mcp-gas-deploy(list,read) | none(no read-capable session tool matched done-sentence)
```

If a wrapper was chosen: `verify_cmd is the existing MCP-backed CLI <name>; do not write new operator tooling`.
If none: only `do not write new operator tooling` — no generic "prefer MCP".

| Ask | Session MCP | mcp-considered (oracle *consider*, not dest-contract) | verify_cmd |
|---|---|---|---|
| hosted/external ask + matching read MCP (example dest: mcp-gas-deploy) | mcp-gas-deploy (list, read) | `mcp-considered: mcp-gas-deploy(list,read)` | existing wrapper if any; else local content check — no new `*verify*` script |
| `result.txt` / empty session | (empty) | `mcp-considered: none(no read-capable session tool matched done-sentence)` | local content check |
| `result.txt` | fs-only MCP | `mcp-considered: none(no read-capable session tool matched done-sentence)` | local content check |
