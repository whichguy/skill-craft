---
bump: minor
---
Change `shiploop-drive`'s default `--resume-mode` to `fresh`, starting a clean host session on cross-model switches (`prepare -> step-plan`) so the execution model does not pay a full cold cache-write over the prelude transcript while preserving warm `--resume` / `exec resume` for same-target restarts (`--resume-mode warm` remains available to warm-resume across model switches).
