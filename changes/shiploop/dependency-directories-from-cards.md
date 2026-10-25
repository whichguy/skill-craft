---
bump: patch
---
- **The base run's dependency directories come from the platform cards:** the test stage's base run and mutation check
  link an ignored directory in from the checkout only when a platform card lists it under `## Dependency directories`.
  The Node card lists `node_modules`, and the Python card `.venv` and `venv`, so those stacks behave as before. A stack
  that installs its runner elsewhere adds one bullet to its card, not a change to the engine. A card lists only
  directories a command reads as input, never build output.
