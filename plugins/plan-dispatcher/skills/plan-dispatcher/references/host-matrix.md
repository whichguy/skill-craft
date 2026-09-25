# Host evidence and prerequisites

The instruction card and Node helper use one portable contract. Native execution
must use the host's currently available tools and fresh context capability.

| Host | Local helper | Native delegation evidence |
| --- | --- | --- |
| Codex | Requires Node 18+ and local files; copied-package CLI tested | Previous four-worker native pilot; current worktree experiment documented in the repository report |
| Claude Code | Same prerequisites; no host API in helper | Not live-tested for this package |
| Grok | Same prerequisites; no host API in helper | Bounded single-parent parallel/join and cascading fan-out pilots with native workers in external sibling Git worktrees; repository live harness retains native I/O and exact return evidence (2026-09-18) |
| Hermes | Same prerequisites; bind package, run and artifact paths inside its habitat | Not live-tested for this package |

No row establishes restart-safe native collection. Inspect actual host capabilities
for async launch, handle retention, notification/join, lookup and cancellation.
If missing, report the unavailable capability rather than simulating workers.

Use a selected installed skill directory or a copied package. Do not use ambient
same-name scripts, an author checkout, or host-specific absolute paths in prompts.
The repository installer can expose the card; discovery is not native execution
verification. This worktree has not been installed into persistent host profiles
or published to a marketplace.
