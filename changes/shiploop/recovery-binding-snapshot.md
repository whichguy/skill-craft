---
bump: patch
---
Add a nonmutating workspace binding snapshot for recovery inspection. It uses only an existing shared lock, refuses pending transactions and unsafe Git metadata, and permits dirty active builder worktrees without recovering state or writing Git objects.
