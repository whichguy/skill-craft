---
bump: patch
---

On POSIX, default runners try to preserve captured prefixes in private run
diagnostics when capture aborts for commands with inherited stdin or explicit
empty input, including empty-file formatter calls. Commands sent non-empty
stdin keep their existing timeout output and abort cleanup behavior and produce
no recovery artifact. The interrupted action is unchanged. Raw output may
contain secrets, and synchronous best-effort publication has no latency bound.
