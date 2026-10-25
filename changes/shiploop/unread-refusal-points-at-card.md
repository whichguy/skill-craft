---
bump: patch
---
- **The unread refusal points at the platform card:** when a base run names a test ID but no line says whether it
  passed, the refusal asks for a reporter that marks each outcome on the line that names it and points at the stack's
  platform card. The Python card now names `pytest -v` and `python -m unittest -v`, and the Node card Jest's
  `--verbose`, beside its existing `node --test` reporters.
