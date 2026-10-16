---
bump: patch
---
Script quality pass: re-raised errors keep their cause and carry the value or
position that failed (progress data, item scope, lint, git timeout, planning
context); transition hooks catch `Exception` rather than `BaseException` and
name an unexpected hook failure on stderr; `shiploop-drive` and `lint --show`
reject non-positive counts at the command line; every public function and
class has a docstring; cryptic helper and variable names were replaced; and a
dead variable, two `assert`s used as control flow and a closure over loop
variables were removed. `SHIPLOOP_DEBUG` names a status-hook failure on stderr.
