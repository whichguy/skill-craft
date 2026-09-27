---
bump: minor
---
`workspace start` now checks, before creating anything, that the host sandbox lets
it write the `.shiploop-runs` parent and the repository's Git directory. When a
sandbox refuses (Codex `workspace-write`, a Grok sandbox profile, Claude's Bash
sandbox) it exits 3 with a `SHIPLOOP-GRANT-NEEDED` block naming the blocked
paths, the repair intent, the grant for the detected host and the exact rerun
command. Every later run-bound command rechecks, so a harness restarted without
its grants stops before a commit fails. `--workspace-root` is now optional: the
default is a new `<repo-parent>/.shiploop-runs/<repo>-<stamp>`, so one grant of
that parent covers every later run.
