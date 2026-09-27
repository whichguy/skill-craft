---
bump: patch
---

`improve-start` prints only the runtime's JSON packet on stdout (its status and
archive lines go to stderr), so a host can parse the output as JSON, as it can
the runtime's own `start`.
