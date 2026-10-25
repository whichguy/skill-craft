---
bump: patch
---
The run trace records only navigator commands on a current run and the packets they print. `chain`, `lint`,
`red-check` and `backchain-check` are not traced, so their read-only views, record-only checks and refusals leave the
run directory exactly as it was (1.12.0 appended to `trace.jsonl` there).
