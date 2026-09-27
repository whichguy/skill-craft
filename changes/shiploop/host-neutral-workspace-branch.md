---
bump: patch
---

The execution worktree branch is `shiploop/run-<id>` on every host instead of
`codex/shiploop-<id>`, which named Codex on Grok and Claude runs. Workspace
records made with the old name are refused.
