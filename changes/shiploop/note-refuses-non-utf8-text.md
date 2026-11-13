---
bump: patch
---
`shiploop note --text` with a byte that is not UTF-8 is now refused with a plain message (exit 2, nothing written) instead of ending in a Python traceback; a `--file` already was.
