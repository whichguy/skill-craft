---
version: 0.1.0
---
Centralize repeated artifact and script names and share repository-path
validation between coordination and delivery. Keep Git's slash protocol
separate from native filesystem paths, reject ambiguous drive-qualified
scopes before dispatch, and read JSON and helper responses as UTF-8 independent
of the caller's locale. Cover path boundaries and locale behavior with tests.
