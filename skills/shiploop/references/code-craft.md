Code craft. Write for the next maintainer, a person or a model, opening one file cold with no run history.
1. Match the house. Its error types, validation helpers, docstring style and logging come first; record any justified
   departure. No dependency, option or fallback without a present need; an argument that lets an existing unit serve
   this change instead of a copy is one.
2. Fail at the door. A function reachable from outside its module (exported API, CLI, request or event handler,
   callback) checks its arguments before any effect: presence, type and shape, range or allowed set, consistency
   between arguments. Reject with the house error type naming the argument, the constraint and the value (redacted
   when sensitive). Code called only by validated code may trust its caller; say so once where not obvious. Never
   swallow an error or substitute a success default; keep the original cause when rethrowing.
3. State the contract where it lives. A new file opens with one or two lines on its purpose; a public function's
   docstring gives purpose, argument constraints, return, errors raised and side effects. In a body, comment only what code
   cannot say: why this approach, an invariant, a workaround and its trigger. On a particularly complex function or
   class, a `Tombstone:` comment names an approach considered or tried, then rejected, and why, so it is not reintroduced.
4. Spend tokens on information. Comments are read by people and models, so each carries what the code cannot, in the
   fewest tokens. No comments restating a name, signature or the next line; no banners, change history or
   commented-out code. A precise name beats a comment; one authoritative explanation beats several.
5. Small, not thin. KISS and YAGNI limit features and speculative abstraction, never an argument check, an error path,
   a contract docstring or the rich UI interaction the plan calls for.
6. Make failure diagnosable, and leave nothing behind. Check a response's contract, not only transport success. Before
   mutation or cleanup, keep the context that explains a failure (operation, IDs, expected versus observed); errors
   name the operation and the mismatch. Use the existing debug switch for short redacted state summaries at major actions,
   with no diagnostic work while it is off. Keep secrets and duplicate stack traces out of user-facing messages.
   Release what you acquire on every path, failure included: handles, connections, temporary files, listeners, locks.
7. Write text that can be translated. User-facing messages go through the message catalog or i18n helper when one exists,
   otherwise one whole sentence with named placeholders, never assembled from fragments. Format numbers, dates,
   currency and plurals with locale-aware APIs. Keep log text, error codes and machine identifiers stable and
   untranslated.
8. Put it where it belongs. The namespace the step plan chose, the narrowest visibility a present consumer needs. A new
   name must not collide with or shadow one in any runtime's shared space (globals, import path, shell, platform org) or
   a used library. No generic bucket such as `utils`. Stored data follows the planned schema and storage policy.
9. Compose before you build, and build to compose. Before a new unit, weigh reusing one unchanged, composing several,
   or augmenting one (an argument, an extension point, a shared piece extracted) while current callers keep working.
   Augment only units that share one meaning: a near-copy of existing logic is a defect, and so is a parameter fusing
   two different rules. A new unit does one job behind a narrow interface, side effects at the edges, a pure core. State the
   choice and why in one line.
10. Run independent work concurrently where it pays. Show the gain first (I/O waits, large independent batches); no
    concurrency or caching without it. Use the runtime's threads, async I/O, worker processes or bulk APIs. Keep it
    correct: shared mutable state guarded, a bound on how many run at once, order kept where it matters, each task's
    error surfaced. Where the platform forbids it (single-threaded runtime, governor limits), use its batch or async
    facility.
11. Use the platform first. Before writing infrastructure (authentication, scheduling, queues, caching, retries,
    logging, storage, search, notification), check what the runtime, platform or an existing service provides
    (HOME/environment.md ## Platform facts, Service discovery guidance); use it and write only the glue.
12. Bound every remote call. A timeout; retries only for idempotent operations, with backoff and a limit; every list
    paged or limited; the response's contract checked (rule 6).
13. Configuration, not constants. No hard-coded URLs, IDs, credentials, limits or environment names in code; read them from
    the project's configuration or the platform's settings, secrets from its secret store.
14. Seams for determinism. Inject the clock, randomness and I/O into the units that use them, so behaviour can be
    replayed in a check and in diagnosis.
