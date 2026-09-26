---
bump: minor
---
A repeated `next` for the same action now prints a short packet: status, callback, keepalive marker, what changed since it was last printed, the stage references and the full stage prompt. The run-level rules (locators, recovery, delegation rule and the original request) become a reference to the run's `rules.md`. `next --full` prints everything, and a new action, a status change or a changed rules block prints the full packet. Packets now point at material instead of asking for a reread: "Read first" is now "Results this stage builds on", and the context index and bound Until Loop card are opened only when they are not already in context.
