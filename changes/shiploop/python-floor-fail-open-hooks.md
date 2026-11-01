---
bump: patch
---
ShipLoop now declares and checks its Python floor (3.9, with `git` on PATH). On an older Python the CLI exits 2 with one line naming the requirement, where it used to fail with a bare traceback. The plugin's hook entries no longer print an error on every tool call when `python3` is missing or too old: they do nothing and exit 0.
