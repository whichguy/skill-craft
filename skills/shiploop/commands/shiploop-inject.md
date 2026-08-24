Add a discovered intermediate step to the running DAG. Exec harness
`inject-step --statement <label> --prompt <text> --produces <text> [--id Sn]
[--need <n> --from <id>] [--before <id>...]` only. Legal only in phase
`implement`. Refuses on plan-hash drift, unsafe/duplicate id, or a
`--before` target that is not `todo`/`ready`. Does not re-run `dest plan`,
clear receipts, or start the new step. Not `/devloop`.
