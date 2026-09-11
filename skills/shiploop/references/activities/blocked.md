# Recoverable block

Do not claim success or invent a missing prerequisite. Preserve the current
action and pause with a specific, non-secret reason:

~~~sh
shiploop pause --run-dir "$RUN_DIR" --reason "what is missing and who can resolve it"
~~~

After the user or external system resolves the blocker, resume to reprint the
same action. A scope, writer, or acceptance change belongs in a later explicit
plan revision; do not hand-edit authoritative records while paused.
