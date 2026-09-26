---
bump: minor
---
`next` always prints the full packet. It is the recovery command, and the script cannot know whether the host kept the run rules through a clear, a compaction or a fresh `shiploop-drive` session, so recovery no longer returns the short form with the original request and delegation rule behind a pointer to `rules.md`. `next --brief` replaces `next --full` as the opt-in: it prints the short form for an in-context reprint of an action already shown. Every producer packet now prints its result path, result template and allowed outcomes directly under the callback line instead of at the end, so a host that keeps only the head of long output still has the contract the callback checks; the tail keeps the callback, pause and halt lines.
