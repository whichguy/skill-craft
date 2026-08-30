Add a discovered intermediate step to the running DAG. Exec harness
`inject-step --statement <label> --prompt <text> --produces <text> [--id Sn]
[--need <n> --from <id>] [--before <id>...]` only. Legal only in phase
`implement`. Refuses on plan-hash drift, unsafe/duplicate id, or a
`--before` target that is not `todo`/`ready`. Does not re-run `dest plan`,
clear receipts, or start the new step. `--prompt` is not required to cite
`environment.md` practice references or `mcp_considered` (those
script gates apply to seed steps only). When `exclusive` is nonempty, the
discovered prompt still needs `Tools:`, a `Use:` line whose entries include
the designated `exclusive[].use`, and a parsed `Don't use:` line (a token
under `Use:` does not count; overlap with `Don't use:` is a gap).
The implement Next envelope still
reprints Frozen session environment above that stored prompt — paste that
block with the discovered prompt.
