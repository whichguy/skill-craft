---
bump: patch
---
Keepalive now lets a turn end after 14 continuations with no accepted result (twice the per-action test-run refusal budget), with a notice to submit `blocked` or `revise`; a refused callback still counts as progress until then, and an accepted result starts the count again. When `handoff` is refused for want of a current workspace return, the refusal now says whether no return was made or the recorded one is stale (for example after ShipLoop's own `docs/shiploop/` commit at `release-verify`) and prints the exact `workspace plan-return` and `workspace return` commands. `system_commands` and `consumer_checks` can no longer name `criteria`, which nothing checked.
