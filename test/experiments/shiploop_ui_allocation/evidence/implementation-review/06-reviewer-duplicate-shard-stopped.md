# Independent-reviewer duplicate shard

The fresh independent reviewer had started a broad
`bash test/shiploop.test.sh --shard 1/3` despite the root-owned hermetic
aggregate already running. It was outside the required verification plan and
was intentionally stopped incomplete at the root agent's direction.

- Reviewer-owned shell PID: `94481` (`bash test/shiploop.test.sh --shard 1/3`).
- Its orphaned direct child PID: `32784` (`test/shiploop-action-walk.test.py`).
- Sent `SIGTERM` to the shell, verified the child became orphaned, then sent
  `SIGTERM` to that child. Neither PID remained afterward.

No root-owned `test/run-all.sh` process was targeted. This interrupted shard is
not used as passing evidence and does not count as an Improve review or check.
