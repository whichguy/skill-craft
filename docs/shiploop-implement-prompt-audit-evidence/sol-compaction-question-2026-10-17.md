Adversarial review of a prompt rewrite. Do not modify any files. Be terse; ranked lists.

Context: these are static instruction texts that a script inserts word for word into the packet an LLM receives to
implement one step of a software feature (ShipLoop's implement stage). The owner wants a more compact prompt with no
obligation lost.

1. Compare CURRENT and CONCISE for each of the two texts. List every obligation that CONCISE drops, weakens, broadens
   or makes ambiguous, quoting both versions. Say "none" if none. Also list anything CONCISE says more clearly.
2. SYMBOLIC is an alternative rendering of only the Considerations section, with a legend and symbols. Would an
   implementing model (Claude Sonnet, Grok, GPT) misread any line? Which symbols are safe and which are risky? Is it
   worth it, given that it saves 35% of characters but only about 16% of tokens?
3. Give your verdict: adopt CONCISE as is, adopt it with named fixes, or keep CURRENT.

=== CURRENT implement guidance ===
# Implement guidance

ShipLoop inserts each section below into every implement packet, word for word (shiploop_static.static_text).
Edit the guidance here; the packet tests pin what each packet prints.

## Method
Complete this step's assigned criteria (Serves), with the connections they need, so this step's part works at its
boundary. Follow the R-n requirements and AD-n decisions that constrain it. Build nothing a later step owns, and do
not claim a whole R-n is satisfied because this step contributes to it. A step can change code, configuration,
platform settings, data, content or documents; the method is the same.

1. Read the assignment and its anchors: the criteria, their quoted R-n, the item's AD-n, the HOME sections under
   Anchored in, and the listed cards. Give a reason for any card you set aside. Use each listed step skill for its
   purpose (invoke it, or read its SKILL.md and follow it). Write a short checklist of the constraints these put on
   this step in RUN/notes/<action>.md. Reuse it each iteration, refresh an entry when its anchor changes, and rebuild
   it from this packet after context loss.
2. Inspect what exists: the parts this step changes, what depends on them, the existing example, and the services the
   surrounding environment already provides.
3. Settle scope, authority and design before building, using the considerations below. Where the anchors settle a
   question, follow them. Where they are silent, decide within the assignment and write it back. If the work
   conflicts with an R-n or AD-n, or needs something outside the assignment, report revise.
4. Build and check: run the relevant checks after each meaningful batch of changes, and run the Proof on the final work.
5. Compare the final change with every checklist entry and each consideration.
6. Record `considerations`, `evidence` and the write-backs.

## Considerations
Answer each in `considerations`: the concrete handling and the anchor that governs it, or why this step does not
affect it. "Handled", "reviewed" and a bare "N/A" are not answers.
1. Whole step [criteria · ## Structure]. Everything the assigned criteria need at this step's boundary: the change and
   its connections (entry points, registration, wiring, configuration, permissions, content, documentation a criterion
   requires), placed where ## Structure says. Note any changed usage or operations for the document stage.
2. Interactions [criteria · ## Interfaces and boundaries · interaction AD-n]. Those this step affects or its criteria
   require. People: what they see and do; waiting, error and empty states; accessible use. Systems: contracts,
   untrusted input and its validation, which actors may do what, sensitive output, slow, failed or repeated messages,
   compatibility with existing consumers. New work outside the assignment: report revise.
3. Building [## Stack · ## Commands]. Produce a valid artifact the way this project builds or validates it. Add no tool
   or dependency without a present need, and record any you add.
4. Deploying [## Targets and runtimes · ## Access and accounts · ## Platform facts · ## Real-boundary checks]. Target,
   order, settings per environment, staged or reversible activation where the risk calls for it, the check after, and
   the undo. Perform only the effects the run's recorded authority covers. Preparing or recording a release action
   does not authorize running it.
5. State [## Structure · storage AD-n · ## Non-functional requirements]. What the step reads, creates or changes, with
   its owner and its shape before and after; compatibility with stored state; ordering, atomicity and concurrent
   updates. Any transition it needs is prepared, applied only where authorized, safe to rerun, and recoverable from a
   partial failure. Invent no storage.
6. Operating [## Non-functional requirements · ## Conventions · ## Platform facts]. What an operator can see and
   diagnose; cost, limits and capacity; independent work run in parallel where the platform supports it and the gain
   is real; secrets and permissions over time; retention, cleanup and owner.
7. What exists [## Structure · ## Conventions · ## Skills · ## Platform facts]. Before creating anything, reuse it
   unchanged, combine existing pieces, or extend one. That applies in the repository and to the services the
   environment already provides (identity, storage, queues, scheduling, caching, logging, search, notification).
   Duplicate none. Keep current behaviour working, and follow the example.
8. Proof [## Commands · ## Harnesses and suites]. What demonstrates each assigned criterion now.

## Evidence and proof
- `evidence`, one entry per assigned criterion: what you ran or inspected, what you observed, where the output is,
  what it establishes and what it does not. A description of the change or a future check is not evidence. For
  document work, an inspected passage plus a consistency check is.
- An unconfirmed assigned criterion blocks done. A check a later stage owns stays deferred, with its owner, and is
  never presented as done.
- Do not weaken or replace the Proof to get accepted. If it cannot validly assess this step now, report revise naming
  the mismatch. A passing Proof never replaces criterion evidence.
- Add no permanent tests or suites here; the test stage writes them. Temporary probes in RUN/scratch are allowed.

## Write back
- A new implementation decision that fits every R-n and AD-n: the next AD-<n> under architecture.md ## Decisions, with
  its basis. A change to, or departure from, an R-n or AD-n is a revise; recording an AD-n does not authorize it.
- A command that now works: environment.md ## Commands. A platform fact or limit: ## Platform facts. A new module,
  file or data entry: architecture.md ## Structure. Never edit spec.md here.
- For a step that changes code, Code craft (inserted below) is the detail under these considerations. Report it
  through them, not as a second assessment.

=== CONCISE implement guidance ===
# Implement guidance

ShipLoop inserts each section below into every implement packet, word for word (shiploop_static.static_text).
Edit the guidance here; the packet tests pin what each packet prints.

## Method
Complete this step's criteria (Serves) and the connections they need, so its part works at its boundary. The R-n and
AD-n bind it. Build nothing a later step owns; never claim a whole R-n because this step contributes to it. Code,
configuration, platform settings, data, content and documents all follow this method.

1. Read the criteria, their R-n, the item's AD-n, the Anchored-in sections and the cards (give a reason for any card
   set aside). Use each step skill for its purpose (invoke it, or follow its SKILL.md). Keep a checklist of the
   constraints in RUN/notes/<action>.md: reuse it, refresh an entry when its anchor changes, rebuild it after context
   loss.
2. Inspect what exists: what the step changes, what depends on it, the example, and the environment's services.
3. Before building, settle scope, authority and design with the considerations: anchors settle a point, follow them;
   anchors are silent, decide within the step and write it back; a conflict with an R-n or AD-n, or work outside the
   step, report revise.
4. Build. Run the relevant checks after each meaningful batch of changes, and the Proof on the final work.
5. Compare the final change with the checklist and each consideration.
6. Record `considerations`, `evidence` and the write-backs.

## Considerations
Answer each in `considerations`: the concrete handling and its anchor, or why the step does not touch it. "Handled",
"reviewed" and a bare "N/A" are not answers.
1. Whole step [criteria · ## Structure]: everything the criteria need at the step's boundary: the change and its wiring
   (entry points, registration, configuration, permissions, content, documentation a criterion requires), placed per
   ## Structure. Note changed usage or operations for the document stage.
2. Interactions [criteria · ## Interfaces and boundaries · interaction AD-n] that the step affects or its criteria need.
   People: what they see and do; waiting, error and empty states; accessible use. Systems: contracts, untrusted input
   and its validation, who may do what, sensitive output, slow, failed or repeated messages, compatibility with
   existing consumers. Work outside the step: report revise.
3. Building [## Stack · ## Commands]: a valid artifact, built or validated the project's way; no tool or dependency
   without a present need, and record any added.
4. Deploying [## Targets and runtimes · ## Access and accounts · ## Platform facts · ## Real-boundary checks]: target,
   order, per-environment settings, staged or reversible activation where the risk warrants, the check after, the
   undo. Only effects the recorded authority covers; preparing or recording a release action does not authorize it.
5. State [## Structure · storage AD-n · ## Non-functional requirements]: what the step reads, creates or changes, with
   owner and shape before and after; compatibility with stored state; ordering, atomicity, concurrent updates. Any
   transition is prepared, applied only where authorized, safe to rerun, recoverable from a partial failure. Invent no
   storage.
6. Operating [## Non-functional requirements · ## Conventions · ## Platform facts]: what an operator can see and
   diagnose; cost, limits, capacity; parallel work where the platform allows it and it pays; secrets and permissions
   over time; retention, cleanup, owner.
7. What exists [## Structure · ## Conventions · ## Skills · ## Platform facts]: reuse, combine or extend before
   creating, in the repository and in the environment's services (identity, storage, queues, scheduling, caching,
   logging, search, notification); duplicate none; keep current behaviour working; follow the example.
8. Proof [## Commands · ## Harnesses and suites]: what demonstrates each criterion now.

## Evidence and proof
- `evidence`, one entry per criterion: what you ran or inspected, what you saw, where the output is, what it shows and
  what it does not. A description of the change or a future check is not evidence; for documents, an inspected passage
  plus a consistency check is.
- An unconfirmed criterion blocks done. A check a later stage owns stays deferred with its owner, never shown as done.
- Never weaken or replace the Proof to pass. If it cannot assess this step now, report revise naming the mismatch. A
  passing Proof never replaces criterion evidence.
- No permanent tests or suites here (the test stage writes them); temporary probes in RUN/scratch are allowed.

## Write back
- A new decision consistent with every R-n and AD-n: the next AD-<n> under architecture.md ## Decisions, with its
  basis. Changing or departing from an R-n or AD-n is a revise; an AD-n does not authorize it.
- A working command: environment.md ## Commands. A platform fact or limit: ## Platform facts. A new module, file or
  data entry: architecture.md ## Structure. Never edit spec.md here.
- On a code step, Code craft (below) details these considerations; report it through them, not as a second assessment.

=== CURRENT code craft ===
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

=== CONCISE code craft ===
Code craft. Write for the next maintainer, a person or a model, opening one file cold with no run history.
1. Match the house: its error types, validation helpers, docstring style and logging come first; record any justified
   departure. No dependency, option or fallback without a present need; an argument that lets an existing unit serve
   this change instead of a copy is one.
2. Fail at the door: a function reachable from outside its module (exported API, CLI, request or event handler,
   callback) checks its arguments before any effect: presence, type and shape, range or allowed set, consistency
   between arguments. Reject with the house error type naming the argument, the constraint and the value (redacted
   when sensitive). Code called only by validated code may trust its caller; say so once where not obvious. Never
   swallow an error or return a success default; keep the original cause when rethrowing.
3. State the contract where it lives: a new file opens with one or two lines on its purpose; a public function's
   docstring gives purpose, argument constraints, return, errors and side effects. In a body, comment only what code
   cannot say: why this approach, an invariant, a workaround and its trigger. On a particularly complex function or
   class, a `Tombstone:` comment names an approach tried or rejected, and why, so it is not reintroduced.
4. Spend tokens on information: comments are read by people and models, so each carries what the code cannot, in the
   fewest tokens. No comments restating a name, signature or the next line; no banners, change history or
   commented-out code. A precise name beats a comment; one authoritative explanation beats several.
5. Small, not thin: KISS and YAGNI limit features and speculative abstraction, never an argument check, an error path,
   a contract docstring or the rich UI interaction the plan calls for.
6. Make failure diagnosable and leave nothing behind: check a response's contract, not only transport success. Before
   mutation or cleanup, keep the context that explains a failure (operation, IDs, expected versus observed); errors
   name the operation and the mismatch. Use the existing debug switch for short redacted summaries at major actions,
   with no diagnostic work while it is off. Keep secrets and duplicate stack traces out of user-facing messages.
   Release what you acquire on every path, failure included: handles, connections, temporary files, listeners, locks.
7. Write translatable text: user-facing messages go through the message catalog or i18n helper when one exists,
   otherwise one whole sentence with named placeholders, never assembled from fragments. Format numbers, dates,
   currency and plurals with locale-aware APIs. Keep log text, error codes and machine identifiers stable and
   untranslated.
8. Put it where it belongs: the namespace the step plan chose, the narrowest visibility a present consumer needs. No
   name that collides with or shadows one in any runtime's shared space (globals, import path, shell, platform org) or
   a used library. No generic bucket such as `utils`. Stored data follows the planned schema and storage policy.
9. Compose before you build, and build to compose: before a new unit, weigh reusing one unchanged, composing several,
   or augmenting one (an argument, an extension point, a shared piece extracted) while current callers keep working.
   Augment only units that share one meaning: a near-copy of existing logic is a defect, and so is a parameter fusing
   two rules. A new unit does one job behind a narrow interface, side effects at the edges, a pure core. State the
   choice and why in one line.
10. Run independent work concurrently where it pays: show the gain first (I/O waits, large independent batches); no
    concurrency or caching without it. Use the runtime's threads, async I/O, worker processes or bulk APIs. Keep it
    correct: shared mutable state guarded, a bound on how many run at once, order kept where it matters, each task's
    error surfaced. Where the platform forbids it (single-threaded runtime, governor limits), use its batch or async
    facility.
11. Use the platform first: before writing infrastructure (authentication, scheduling, queues, caching, retries,
    logging, storage, search, notification), check what the runtime, platform or an existing service provides
    (HOME/environment.md ## Platform facts, Service discovery guidance); use it and write only the glue.
12. Bound every remote call: a timeout; retries only for idempotent operations, with backoff and a limit; every list
    paged or limited; the response's contract checked (rule 6).
13. Configuration, not constants: no hard-coded URLs, IDs, credentials, limits or environment names; read them from
    the project's configuration or the platform's settings, secrets from its secret store.
14. Seams for determinism: inject the clock, randomness and I/O into the units that use them, so behaviour can be
    replayed in a check and in diagnosis.

=== SYMBOLIC considerations ===
## Considerations
Legend: S = HOME/spec.md, A = HOME/architecture.md, E = HOME/environment.md; §x = heading x; → = then; ✗ = never.
Each → `considerations.<key>`: handling + anchor | why untouched. ✗ "handled" ✗ "reviewed" ✗ bare "N/A".
1 whole_step [C · A§Structure]: change + wiring (entry, registration, config, perms, content, required docs) @A§Structure; usage/ops change → note for document.
2 interactions [C · A§Interfaces and boundaries · AD]: people: see/do, wait/error/empty, a11y. systems: contract, untrusted input → validate, who may do what, sensitive out, slow/failed/dup msg, compat w/ consumers. outside step → revise.
3 build [A§Stack · E§Commands]: valid artifact, project's way; new tool/dep only on present need → record.
4 deploy [E§Targets and runtimes · E§Access and accounts · E§Platform facts · A§Real-boundary checks]: target, order, per-env settings, staged/reversible if risky, post-check, undo. effects ⊆ recorded authority; prepared ≠ authorized.
5 state [A§Structure · storage AD · S§Non-functional requirements]: read/create/change: owner, shape before→after, compat w/ stored, order, atomicity, concurrency; transition: prepared, applied only if authorized, rerunnable, partial-failure recovery. ✗ invented storage.
6 operations [S§Non-functional requirements · A§Conventions · E§Platform facts]: observe/diagnose; cost, limits, capacity; parallel where allowed + pays; secrets/perms over time; retention, cleanup, owner.
7 existing [A§Structure · A§Conventions · E§Skills · E§Platform facts]: reuse > combine > extend > create (repo + env services: identity, storage, queues, scheduling, caching, logging, search, notification); ✗ duplicate; keep current behaviour; follow example.
8 proof [E§Commands · E§Harnesses and suites]: what shows each C now.

