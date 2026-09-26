---
bump: minor
---
Tests now run on a script-enforced loop. `step-plan` must record the work
item's test commands in its result (`test_commands`, each `focused` or
`regression`; an empty list needs `test_commands_na` with the reason).
`test-green` loops on the focused commands and `regression` on all of them, on
the Until Loop bound to the selected Improve card: ShipLoop writes the loop
contract with the exact commands, and each iteration runs every command, fixes
the code (never a check) and reruns the whole list, for at most 4 iterations.
Both stages accept only `done` or `blocked`. `done` needs the loop's terminal
packet, checked against the contract, and then ShipLoop runs every command
itself from the repository (10 minutes each, 30 per stage) and refuses unless
each exits 0, printing the failures. The prompt-only pass-or-stop loop now
covers `implement`, `test-refine` and `integration-verify`.

The packet-size caps in the test suite are removed; complete prompts take
priority over packet length.
