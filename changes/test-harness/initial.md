---
version: 0.1.0
---
New skill: run a repository's test suite through a harness that audits what the run did beyond its exit code (unintended writes to tracked files, leftover artifacts, live service calls, secret-shaped or traceback output), with an audit-only default, an optional fix-and-rerun loop confined to a disposable worktree, a hard one-hour wall-clock cap, and a machine-written report (a greppable RESULT line, a chat card, markdown, HTML and JSON). It needs bash, Python 3 and git, makes no network calls, and keeps run records under `${XDG_STATE_HOME:-$HOME/.local/state}/test-harness/runs` (override with `TEST_HARNESS_RUN_ROOT`). Verified on macOS and in one Linux container (Debian 13, aarch64); other platforms have not been run.
