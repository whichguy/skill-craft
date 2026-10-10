---
bump: patch
---
The packet that asks for `improve-bind` is kept in its own file, `packets/<action>-improve-bind.md`, so the later `improve-start` packet (`<action>-improve.md`) no longer overwrites it and both can be audited.
