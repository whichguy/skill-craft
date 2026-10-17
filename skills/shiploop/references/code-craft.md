Code craft. Write for the next maintainer, a person or a model, who opens one
file cold with no run history. Every rule serves that reader.
1. Match the house. The repository's error types, validation helpers, docstring
   style and logging come first; record any justified departure. Add no
   dependency, option or fallback without a present need. An argument that
   lets an existing unit serve this change instead of a copy is a present need.
2. Fail at the door. A function reachable from outside its module (exported
   API, CLI handler, request or event handler, callback) checks its arguments
   before any effect: required values present, type and shape, range or allowed
   set, and consistency between arguments. Reject with the house error type,
   naming the argument, the constraint and the received value (redacted when
   sensitive). Code called only by validated code may trust its caller; say so
   once where that is not obvious. Never swallow an error or substitute a
   success default; keep the original cause when rethrowing.
3. State the contract where it lives. A new file opens with one or two lines on
   its purpose. A public function's docstring gives purpose, argument
   constraints, return, errors raised and side effects. In a body, comment only
   what the code cannot say: why this approach, an invariant, a workaround and
   its trigger. On a function or class whose logic is particularly complex, add
   a tombstone: a short `Tombstone:` comment naming an approach tried or
   considered and rejected, and why, so it is not reintroduced.
4. Spend tokens on information. Comments are read by people and by models:
   each one carries what the code cannot say, in the fewest tokens. Delete
   comments that restate a name, signature or the next line. No banners,
   change history or commented-out code. Prefer a precise name to a comment
   and one authoritative explanation to several.
5. Small, not thin. KISS and YAGNI limit features and speculative
   abstractions. They never remove an argument check, an error path, a
   contract docstring, or the rich UI interaction the plan calls for.
6. Make failure diagnosable, and leave nothing behind. Check a response's
   contract, not only transport success. Before mutation or cleanup, keep the
   context that explains a failure: operation, relevant IDs, expected versus
   observed. Errors name the operation and that mismatch. Reuse the existing
   debug switch for short, redacted state summaries at major actions, with no
   diagnostic work while it is off. Keep secrets and duplicate stack traces out
   of user-facing messages. Release what you acquire on every path, failure
   included: handles, connections, temporary files, listeners, locks.
7. Write text that can be translated. User-facing messages go through the
   repository's message catalog or i18n helper when one exists; otherwise keep
   each message one whole sentence with named placeholders, never assembled
   from fragments, so it can be externalized later. Format numbers, dates,
   currency and plurals through locale-aware APIs. Keep log text, error codes
   and machine identifiers stable and untranslated.
8. Put it where it belongs. New code lives in the namespace the step plan
   chose, with the narrowest visibility a present consumer needs. A new name
   must not collide with or shadow one in the shared space of any runtime it
   runs in (such as globals, an import path, a shell or a platform org) or in a
   library the code uses. No new generic bucket such as `utils`. Stored data
   follows the planned schema and storage policy.
9. Compose before you build, and build to compose. Before writing a new unit,
   evaluate reusing an existing one unchanged, composing existing ones, or
   augmenting one (a new argument, an extension point, or a shared piece
   extracted from existing code) while its current callers keep working.
   Augment only when the units share one meaning, not merely similar code: a
   near-copy of existing logic is a defect, and so is a parameter that fuses
   two different rules. A new unit does one job behind a narrow interface, with
   its side effects at the edges and a pure core, so others can combine and
   check it. State the option chosen and why in one line.
10. Run independent work concurrently where it pays. Show the gain first (I/O
    waits, large independent batches); add no concurrency or caching without
    that reason. Use what the runtime provides: threads, async I/O, worker
    processes, batch or bulk APIs. Keep it correct: no shared mutable state
    without its guard, a bound on how many run at once, ordered results where
    order matters, and each concurrent task's error surfaced. Where the platform
    forbids it (a single-threaded runtime, governor limits), use its batch or
    async facility.
11. Use the platform first. Before writing infrastructure (authentication,
    scheduling, queues, caching, retries, logging, storage, search,
    notification), check what the runtime, the platform or an existing service
    provides (HOME/environment.md ## Platform facts, Service discovery
    guidance). Use it, and write only the glue.
12. Bound every remote call. Give it a timeout. Retry only idempotent
    operations, with backoff and a limit. Page or limit every list it fetches,
    and check the response's contract (rule 6).
13. Configuration, not constants. No hard-coded URLs, IDs, credentials,
    limits or environment names in code. Read them from the project's
    configuration or the platform's settings, and secrets from its secret store.
14. Seams for determinism. Inject the clock, randomness and I/O into the units
    that use them, so behaviour can be replayed in a check and in diagnosis.
