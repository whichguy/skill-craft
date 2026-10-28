# 3. The documents the prompt references

Rendered by ShipLoop's own `emit()` from branch `shiploop/implement-prompt-2d6ecc` (4eae0910) for Battleship step S1, using the 2026-10-16 run's real spec, architecture, environment, criteria and test cases (`docs/shiploop-implement-prompt-audit-evidence/render-battleship-S1-example.py`). Only machine paths are shortened: RUN = the run directory, WORKTREE = the product checkout, <skills> = the installed skill-craft skills directory.

How each is used:

| Document | How the prompt uses it | Where |
|---|---|---|
| `references/implement-guidance.md` | inserted word for word as "Current stage guidance" | printed prompt |
| `references/code-craft.md` | inserted word for word after the guidance (code steps only) | printed prompt |
| `coding-practices.md#composition-and-layers`, `#namespaces-and-placement`, `platforms/node-express.md` | the step's **Cards**: read before the first edit | linked from the step block |
| `coding-guidance.md#select-guidance`, `house-style.md#match-while-building`, `service-discovery.md#development-handoff`, `repeatable-test-suites.md#select-target-native-tests` | the stage's guide locators | linked from the packet file |
| Until Loop `ADAPTER.md`, section "Start from a parent-written contract" | how to invoke the loop off Claude Code | linked from the loop block |
| `RUN/reference.md` | the long form of the rules, policies and recovery | linked from the packet file |
| `HOME/spec.md` (R-3..R-7), `HOME/architecture.md`, `HOME/environment.md` | the step's anchors: quoted whole (architecture, environment) or by entry (R-n) | packet file |

## references/implement-guidance.md (whole file)

*Inserted word for word into the prompt.*

````markdown
# Implement guidance

ShipLoop inserts each section below into every implement packet, word for word (shiploop_static.static_text).
Edit the guidance here; the packet tests pin what each packet prints.

## Method
Complete this step's assigned criteria (Serves) and the connections they need, so its part works at its boundary.
Follow the R-n and AD-n that constrain it. Build nothing a later step owns; never claim a whole R-n because this step contributes to it. Code,
configuration, platform settings, data, content and documents all follow this method.

1. Read the assignment and its anchors: the criteria, their quoted R-n, the item's AD-n, the HOME sections under
   Anchored in, and the listed cards (give a reason for any card set aside). Use each listed step skill for its purpose
   (invoke it, or follow its SKILL.md). Keep a checklist of their constraints in RUN/notes/<action>.md: reuse it each
   iteration, refresh an entry when its anchor changes, rebuild it from this packet after context loss.
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
1. Whole step [criteria · ## Structure]: everything the assigned criteria need at the step's boundary: the change and
   its connections (entry points, registration, wiring, configuration, permissions, content, documentation a criterion
   requires), placed per ## Structure. Note changed usage or operations for the document stage.
2. Interactions [criteria · ## Interfaces and boundaries · interaction AD-n] that the step affects or its criteria need.
   People: what they see and do; waiting, error and empty states; accessible use. Systems: contracts, untrusted input
   and its validation, who may do what, sensitive output, slow, failed or repeated messages, compatibility with
   existing consumers. Work outside the step: report revise.
3. Building [## Stack · ## Commands]: a valid artifact, built or validated the project's way; no tool or dependency
   without a present need, and record any added.
4. Deploying [## Targets and runtimes · ## Access and accounts · ## Platform facts · ## Real-boundary checks]: target,
   order, per-environment settings, staged or reversible activation where the risk warrants, the check after, the
   undo. Only effects the run's recorded authority covers; preparing or recording a release action does not authorize running
   it.
5. State [## Structure · storage AD-n · ## Non-functional requirements]: what the step reads, creates or changes, with
   owner and shape before and after; compatibility with stored state; ordering, atomicity, concurrent updates. Any
   transition it needs is prepared, applied only where authorized, safe to rerun, recoverable from a partial failure. Invent no
   storage.
6. Operating [## Non-functional requirements · ## Conventions · ## Platform facts]: what an operator can see and
   diagnose; cost, limits, capacity; independent work in parallel where the platform allows it and it pays; secrets and permissions
   over time; retention, cleanup, owner.
7. What exists [## Structure · ## Conventions · ## Skills · ## Platform facts]: reuse unchanged, combine or extend
   before creating, in the repository and in the environment's services (identity, storage, queues, scheduling, caching,
   logging, search, notification); duplicate none; keep current behaviour working; follow the example.
8. Proof [## Commands · ## Harnesses and suites]: what demonstrates each assigned criterion now.

## Evidence and proof
- `evidence`, one entry per assigned criterion: what you ran or inspected, what you saw, where the output is, what it shows and
  what it does not. A description of the change or a future check is not evidence; for documents, an inspected passage
  plus a consistency check is.
- An unconfirmed assigned criterion blocks done. A check a later stage owns stays deferred with its owner, never shown as done.
- Never weaken or replace the Proof to pass. If it cannot validly assess this step now, report revise naming the mismatch. A
  passing Proof never replaces criterion evidence.
- No permanent tests or suites here (the test stage writes them); temporary probes in RUN/scratch are allowed.

## Write back
- A new implementation decision consistent with every R-n and AD-n: the next AD-<n> under architecture.md ## Decisions, with its
  basis. Changing or departing from an R-n or AD-n is a revise; an AD-n does not authorize it.
- A command that now works: environment.md ## Commands. A platform fact or limit: ## Platform facts. A new module, file or
  data entry: architecture.md ## Structure. Never edit spec.md here.
- On a code step, Code craft (below) details these considerations; report it through them, not as a second assessment.
````

## references/code-craft.md (whole file)

*Inserted word for word into the prompt for steps that change code.*

````markdown
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
````

## coding-practices.md#composition-and-layers

*A Card on the step block: read before the first edit.*

````markdown
## Composition and layers

Give every changed responsibility a clear owner and a sensible dependency
direction. Separate domain decisions from transport, storage, and presentation
details when the boundary improves current use or testing. Compose existing
collaborators through their supported interfaces; use inheritance only where a
real framework contract or substitutability demands it. Place wiring and
configuration at an appropriate boundary, then verify through the real entry
point and affected consumers. Do not add forwarding layers, factories, or a
dependency-injection container solely for a hypothetical future.

Which important structural constraint can an existing checker enforce? When
useful, calibrate a repository-scoped rule with prohibited and permitted examples,
including an approved boundary and misleading lookalikes. Include a case exposing
a known limited rule or documented blind spot; use a deficient comparator when
already available or cheap. State supported syntax and unresolved dynamic behavior
before enforcement; structural matches do not prove runtime behavior or
authorization. Do not add a checker merely to restate a preference.
````

## coding-practices.md#namespaces-and-placement

*A Card on the step block: read before the first edit.*

````markdown
## Namespaces and placement

Code runs in one or more execution environments, and each has its own name
space. The environment is often not the checkout you edit: a remote runtime
reached through an MCP server, API or CLI, a hosted platform, a container, a
browser, or several services of a multi-service system, each with its own
installed libraries, versions, globals and stored names. List every environment
the change runs in or reaches, and inspect each through its actual interface
(see [Platform discovery](platform-discovery.md#discover-before-choosing-a-mechanism));
the local tree does not show what a remote runtime already defines.

For each environment, map what exists before adding a file, module or public
name: the package or directory layout, naming prefixes, what each module
exports, where similar responsibilities already live, and how the runtime
resolves names. Examples of that last point: files that share one global scope,
an import path where a local module can shadow a library, a shell that sourced
files join, platform-wide class or metadata names, page-wide element and style
names. Names are also shared across environments and with other programs:
environment variables, CLI commands, config and storage keys, API routes,
tables, queues, topics and event types. Give each cross-service name one
owning service and a versioned contract.

List the libraries and services the new code imports, is called by, or shares
a space with, in each environment. Check their exported names, reserved
prefixes and conventions; do not shadow, redefine or monkeypatch their names.
Where the house already reaches an outside library or service through an
adapter, use it rather than calling around it.

Give each new name the narrowest visibility a present consumer needs: local or
module-private first, exported only for a named consumer. A public name is a
contract. Place code by responsibility and dependency direction, in the
environment where it must run, next to its nearest collaborators. Forecast
where the next planned siblings will go, from the queued work items and
accepted spec, so the first file does not set a layout the second must break;
do not create empty packages or directories for hypothetical futures. Follow
the house casing and prefixes, and avoid generic buckets (`utils`, `common`,
`misc`) unless the house already uses one with a clear rule. Confirm with each
environment's own check: an import or load test, a deploy validation, or a
search for the new name in that environment and its dependencies. The
[platform cards](coding-guidance.md#conditional-index) give runtime-specific
examples.
````

## platforms/node-express.md (whole file)

*A Card on the step block: read before the first edit.*

````markdown
# Node.js and Express development

Return to the [guidance selector](../coding-guidance.md#select-guidance) when the deployment target or transport changes. Identify who signs in, how, and how authorization is checked before touching state.

`express-session` issues a signed cookie holding only a session ID; the server verifies by looking up that ID in a store. The default `MemoryStore` "will leak memory under most conditions" and "does not scale past a single process" — not for production. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/)) For federated sign-in, use Passport with `openid-client`'s generic OIDC strategy, configured with the provider's discovery endpoint and client ID/secret. ([passportjs.org/openid-client](https://www.passportjs.org/packages/openid-client/)) Express has no built-in authorization; role checks are hand-written middleware run after session/Passport deserialization (`req.user`). ([expressjs.com/security](https://expressjs.com/en/advanced/best-practice-security/)) Store roles in your own DB table, not the session store, so revocation doesn't require killing every session.

`node:sqlite` is built in but currently Stability 1.2 "Release candidate," not fully stable. ([nodejs.org/api/sqlite](https://nodejs.org/api/sqlite.html)) `better-sqlite3` is synchronous and single-writer; WAL mode lets reads proceed during writes, but SQLite "still serializes writes with exactly one transaction holding the write lock at any moment," and transactions across `ATTACH`ed DBs are not atomic as a set. ([better-sqlite3 performance docs](https://github.com/WiseLibs/better-sqlite3/blob/master/docs/performance.md)) With PostgreSQL via `pg`, transactions require one dedicated client from `pool.connect()`, not `pool.query()` — mixing clients breaks isolation. Isolation levels are Read Committed (default), Repeatable Read, and Serializable, set via `BEGIN TRANSACTION ISOLATION LEVEL`. ([node-postgres transactions](https://node-postgres.com/features/transactions), [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)) Redis belongs as a session/cache store, not primary transactional storage.

Node is single-threaded per process; running several instances (cluster, PM2, containers) breaks anything held in process memory — in-memory sessions, rate-limit counters, cron schedules, Socket.IO room state — each needs an external store or shared adapter instead. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/)) `better-sqlite3` writes serialize at the DB level regardless of process count, so multiple instances hitting one file queue on the writer lock. A single-user, client-only tool needs none of this: no session store, no lock, no queue.

Request/response over native `http`/Express is supported by default; polling is client-implemented with no framework support. SSE uses plain `res.write()` over a kept-open `text/event-stream` response, which works with one instance but needs a Redis pub/sub fan-out across several, since a client's stream lives on one process only. `ws` is a low-level standalone WebSocket library; Socket.IO adds rooms, reconnection, and fallback, and across multiple instances requires `@socket.io/redis-adapter`. ([socket.io Redis adapter](https://socket.io/docs/v4/redis-adapter/)) Platform push uses `web-push` with VAPID keys from `webpush.generateVAPIDKeys()`. ([web-push GitHub](https://github.com/web-push-libs/web-push))

Redis as an app-level cache needs explicit TTLs; `connect-redis`'s session TTL uses the cookie's expiry or defaults to 86400 seconds. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/)) Express has no built-in HTTP cache layer — add `Cache-Control` headers or a reverse proxy.

Node's built-in `.env` loading (`node --env-file=.env app.js`, plus `--env-file-if-exists` and `process.loadEnvFile(path)`) is still experimental as of the version checked; environment-set variables win over file values, and the built-in parser does no variable expansion, unlike `dotenv`.

For scheduling, in-process `node-cron` supports overlap prevention and a `noOverlap` distributed-coordination option, but real multi-instance coordination needs that feature or an external scheduler. ([node-cron docs](https://nodecron.com/docs/)) BullMQ (Redis-backed) gives durable queues with retries via `attempts` plus `fixed`/`exponential` backoff; without a backoff function, jobs retry without delay, and there's no built-in dead-letter queue — build one from the `failed` event once attempts are exhausted. At-least-once delivery means handlers must be idempotent: key off job IDs and re-fetch state instead of trusting a re-passed payload. ([BullMQ retrying docs](https://docs.bullmq.io/guide/retrying-failing-jobs))

Check PostgreSQL connection limits, Redis's `maxmemory-policy`, BullMQ concurrency/rate-limit options, and Node's EOL/support window against the linked pages rather than a remembered number.

A local single-process `node app.js` run proves route logic and DB queries, but not multi-instance session sharing, Socket.IO cross-instance delivery, cron dedup under multiple replicas, or real SIGTERM behavior. Test graceful shutdown — the process manager sending SIGTERM and `server.close()` finishing in-flight requests while refusing new ones — by sending a real SIGTERM to a running instance, not Ctrl-C in a dev terminal. ([expressjs.com graceful shutdown](https://expressjs.com/en/advanced/healthcheck-graceful-shutdown/))

## Current facts (as of 2026-09-26)

- Node.js 24 is Active LTS, Node 26 is Current, entering LTS October 2026. ([nodejs.org releases](https://nodejs.org/en/about/previous-releases), [endoflife.date/nodejs](https://endoflife.date/nodejs))
- Express is at ~5.2.x.
- `node:sqlite` is Stability 1.2, "Release candidate." ([nodejs.org/api/sqlite](https://nodejs.org/api/sqlite.html))
- BullMQ documentation is current at [docs.bullmq.io](https://docs.bullmq.io/).
- Socket.IO's Redis adapter is documented for v4. ([socket.io Redis adapter](https://socket.io/docs/v4/redis-adapter/))
- `csrf-csrf` is the current maintained package per its npm page. ([npm csrf-csrf](https://www.npmjs.com/package/csrf-csrf))

Recheck these against the linked pages before relying on them.

## Claims to check

- "Express 5 needs no try/catch anywhere." Only promise rejections thrown from an `async` handler passed directly to Express are auto-forwarded; errors thrown inside detached callbacks (timers, event emitters) still need manual handling. ([betterstack Express 5 guide](https://betterstack.com/community/guides/scaling-nodejs/express-5-new-features/))
- "`csurf` is the current standard CSRF package." It is deprecated/archived with no security fixes; use `csrf-sync` or `csrf-csrf`. ([npm csrf-csrf](https://www.npmjs.com/package/csrf-csrf))
- "`node:sqlite` is a fully stable API." It is Stability 1.2, not 2 (Stable). ([nodejs.org/api/sqlite](https://nodejs.org/api/sqlite.html))
- "Default `express-session` `MemoryStore` is fine for small production apps." The docs say it leaks memory and doesn't scale past one process. ([expressjs.com/session](https://expressjs.com/en/resources/middleware/session/))
- "Socket.IO automatically syncs rooms/broadcasts across horizontally scaled instances." It requires explicitly installing `@socket.io/redis-adapter`. ([socket.io Redis adapter](https://socket.io/docs/v4/redis-adapter/))
- "`--env-file` is a drop-in dotenv replacement." It has no variable expansion and is still experimental in the version checked.
````

## Coding decision guide: coding-guidance.md#select-guidance

*A guide locator in the packet file, opened on demand.*

````markdown
## Select guidance

At planning and at a relevant execution or review boundary, inspect the actual
entry point, callers, requirements, tests, versions, and examples. Select a
practice card for a changed concern; select a platform card after identifying
the runtime, artifact, boundary, and version. A mixed change can need several.
Reuse current tools and contracts before a new dependency or framework.

Record applicable decisions and material unknowns, not `N/A` boilerplate for
every card. A card is a prompt to make a consequential decision explicit; it
does not create a new state machine, security program, or test layer.
````

## House-style guidance: house-style.md#match-while-building

*A guide locator in the packet file, opened on demand.*

````markdown
## Match while building

At test authoring and implementation, reopen the match contract (the step
plan's `match` field, quoted in the packet) and its exemplars before editing;
do not work from a remembered summary.

- Write new code and tests in the exemplars' shape and vocabulary.
- After a first draft, search again using the draft's own names and calls.
  The draft finds existing helpers, constants and fixtures that the plan's
  wording did not; reuse them instead of adding near-duplicates.
- Leave surrounding code in its existing style. Restyling unrelated code needs
  its own reason and its own change.
- When the item must depart from the contract, record the reason in the
  item's result, so verification can judge it.
````

## Service discovery guidance: service-discovery.md#development-handoff

*A guide locator in the packet file, opened on demand.*

````markdown
## Development handoff

Keep one concise, maintained decision as an `AD-<n>` entry in
`docs/shiploop/architecture.md`, linking the repository's own architecture or
design note for the detail instead of copying it. The decision and the structure
it chose have that one home: status (accepted, unresolved, superseded, or not
applicable), target/role observations, the four-way delta, the selected
capability map, data/cache and async contracts, observability coverage/reuse
decision, evidence limits, file roles, and revalidation triggers. The runtime
facts have the other: the runtime map and its versions, ordered prerequisites,
working checks and access stay in `docs/shiploop/environment.md` (or the
repository's own environment note), and the entry links that section instead of
carrying it. Link the entry from the repository knowledge index at
`REPO/SHIPLOOP.md`, preserving existing project-document links and structure. Do
not duplicate a project's documentation.

At planning and operations, reopen the index and the exact current sections,
not a remembered chat transcript or arbitrary whole documents. Retain their
locators in the accepted result's existing `evidence_refs`; where an INNER work
item needs them, put a compact locator and decision/revalidation summary in that
item's existing `context`. The Navigator transports these host-authored
locators; the selected chain collector can bind declared file content, but neither
establishes its factual freshness or semantic sufficiency. Verify the
[discovery evidence handoff](project-knowledge.md#discovery-evidence-handoff),
including explicit file references for the selected transport. No new
result field, runtime projection, ledger, or stage is required.

Discovery/research establishes observed facts and decisions; specification makes
freshness, authorization, completion, retention, and observability criteria
testable; test strategy identifies local/remote surfaces, identities, fixtures,
setup, teardown, and suite membership. The plan orders metadata/configuration,
service/adapter, cache/worker, UI, observability, test, and delivery work only
when justified. Step planning reopens and revalidates its exact sections before
edits. Operations and handoff retain current log/audit retrieval and recovery
locators, observation dates, and unresolved limitations.
````

## Target-native test selection: repeatable-test-suites.md#select-target-native-tests

*A guide locator in the packet file, opened on demand.*

````markdown
## Select target-native tests

Use the existing discovery and environment notes to identify the affected
execution boundaries and actual deployment/promotion test gates. Relevant server
code, served client code, configuration, generated definitions and existing test
assets may live behind an MCP/API rather than in the local repository. An exposed
tool list describes access operations, not a complete inventory of that system.
Use bounded supported reads of the selected system and authoritative definitions;
retain source/target identity, revision when available, and observation limits.
Do not inspect unrelated systems or assume every remote runtime has a test runner.

In the existing test-strategy/case records, retain the native-suite decision and
its discovery/environment evidence:

- Select checks when affected behavior needs that runtime's evidence or the
  actual release operation requires them, including existing remote code affected
  by configuration or dependency changes. Reuse its supported tests/facilities.
- Exclude a native suite only with evidence that neither the affected behavior
  nor the actual release gate requires it. Unrelated code can exist without
  requiring its suite; no code, runner or empty tests should be invented.
- If applicability is unknown, retain the discovery gap and earliest dependent
  owner. If required but unavailable, retain the named prerequisite and due phase
  as blocked/unrun. Missing access, an empty local search or a successful MCP call
  cannot justify N/A or prove a test passed.

Use the existing [local/remote execution contract](#plan-local-and-remote-execution)
for commands, definitions, registration, isolation, authority and results; no
second inventory or row per language is required. At `implement` and `test`,
revalidate affected decisions against actual local and remote code/configuration,
dependencies and test-definition changes. At `release-plan`, recheck the actual
target, payload and operation's test gate. Update the existing cases and evidence
when their basis changes; a prior exclusion is not permanent.
````

## Until Loop ADAPTER.md: Start from a parent-written contract

*Named by the loop block's How to invoke line (hosts other than Claude Code).*

````markdown
## Start from a parent-written contract

Apply this section first. When the argument or the parent's packet names a
contract file (`Contract: <absolute path>`) and a receipt
(`Receipt: <absolute path>`), the parent already interpreted the request:

- Skip interpretation. Do not build, edit, retype or re-serialize a contract,
  and skip "Interpret the request before starting".
- Start the run with exactly this command, using this card's
  `scripts/until_loop_ephemeral.py`:
  `python3 <script> start --receipt <Receipt> < <Contract>`.
- The file wins over the argument text. Any Work, Exit or Repeat lines in the
  argument are a copy for reading; where they differ from the file, follow the
  file.
- Before starting, check the receipt. If it exists and its `status` is
  `active`, continue that run: run its `next_argv` once and follow the returned
  packet. If it is `complete` or `stopped`, the run is over: return to the
  parent with that result. Never start a second run for the same receipt.
- Never write or edit the receipt; the runtime writes every packet there.

Then follow "Follow the returned action" for each packet until the run is
complete or stopped, and hand the terminal result back to the parent. The
parent submits its own callback; this loop never calls it. Read the other
sections only when a packet needs them.
````

## RUN/reference.md (whole file)

*Named in the packet file for the rules' long form, the policies and recovery.*

````markdown
<!-- shiploop-reference: 1.5.0 -->
# ShipLoop run reference

Run nav-ed6e723bcc914e36830cd2b06c0bf4d0. Packets name a section as reference#<anchor>; open it only when the packet says to, or after a reset.

## Rules for every step {#rules}

This packet assigns one script-selected SDLC producer step.  The script owns the
durable graph, action identity, and legal successor; you own the engineering
judgment, repository work, evidence, and result. Perform only the current step
before its callback, then immediately follow the newly returned packet.
Preserve unrelated work and do not choose a successor, advance parent state
yourself, or treat a previous packet as the current assignment.

Use the Stage readiness and completion guide for this activity's Definition of
Ready (inputs and prerequisites) and Definition of Done (scoped output and due
evidence). Definition complete, tests planned, tests authored and tests passed
are different claims; retain later-phase verification without claiming it now.

Read the current repository, run state, applicable instructions, and relevant
durable lessons before relying on earlier notes.  Treat Git history, plans, tool
descriptions, and prior results as context to recheck, not authority or proof.
Use actual observations for test, build, integration, release, and consumer
claims.  Keep scope, target authority, artifact identity, operation effects, and
consumer behavior distinct.  A missing prerequisite, permission, access, or
trustworthy check is unresolved or blocked; it is not a successful N/A.
Blocked means work this stage cannot do: a missing target or account, a missing
approval, or a command with no replacement available inside the stage. A retained
command that does not run what it claims (for example a test path the runner does
not expand) is a documentation fix made in this stage, then rerun, not a blocker.
Write temporary files (command output, a report you pipe into a tool) in the
packet's Scratch directory, not /tmp: /tmp is shared with other runs and
sessions, and a fixed /tmp name can read another run's file.
ShipLoop runs unattended: no one is watching and nothing arrives on standard
input. When a decision is open, take the default that best fits the request and
the recorded knowledge, record it as an assumption (the alternatives and why
this one) in the result's summary (only plan's result has an assumptions list),
and continue. When a step can only be done by a person (a sign-in, a
grant, an observation in a signed-in browser), record it as an open item in the
result, with who must do what and what they should report, and continue with
everything that does not depend on it. Only when nothing further can proceed
without the person, report blocked with `blocked_by` user (or access, for a
sign-in) and `awaiting`: `{"kind": "answer", "question": "...", "options": [...], "no_default": "..."}`
for a decision, or `{"kind": "present", "steps": [...], "report": "...", "no_default": "..."}`
for something only a person can do; `no_default` says why no recorded default
would do, and ShipLoop refuses a wait without it. Ask one decision per question,
in words the user can answer in one reply. The run then stops until the user's
own reply resumes it.

For identity or access discovery, use supported non-mutating probes and
sanitized evidence. Normal supported tool-managed authentication and tool
configuration metadata without session material remain allowed. Builders and
reviewers must not read, decode, retain, or report local authentication,
session, or credential-store contents.

Requested runtime / entry point / material dependency: preserve each original
user requirement, and distinguish it from a verified contract, observed practice,
or assumption in the existing notes/results. Record local-test-route evidence
separately from target compatibility. A local fixture or preview cannot supply a
target capability absent from the requested runtime. Delivery outside the present
scope does not by itself make requested-runtime compatibility N/A. Establish
compatibility with target-compatible source or local evidence where possible;
otherwise keep the gap unresolved.

Follow the packet's Maintained requirements policy. Read the applicable accepted
product requirements, including preserved and cross-cutting conditions, from
their repository-owned home; a new request changes scope without erasing
unaffected rules. Carry requirement and test locators into work-item context.
Do not infer approved intent from code/tests or silently relax a condition to
match them. Keep proposals and verification gaps distinct from accepted intent.
Follow the packet's Reference handoff policy: distinguish package guidance,
repository-owned requirements/tests and run-local evidence. Resolve and verify
the selected file/section against its named root; retain exact applicable
locators for downstream work, not merely a link to this policy.
Use the packet's Requirements definition guide to reconcile existing specs and
define applicable non-functional requirements. Current explicit user instructions
supersede conflicting older clauses; preserve unaffected conditions and retain
clarification, requirement, and verification locators for cold recovery.
Later clarifications must be actual user instructions for this same request with
their durable user-source/decision basis; an unverified host summary is not an
instruction. Use the active correction/revision route for affected frozen contracts.

Return the packet's concise producer result with a truthful outcome, summary,
and useful evidence locators. For relevant product work, include the selected
maintained requirement sections and test/evidence locators in the result's
existing evidence_refs so a later reader can recover them. If a required
source is missing, report the gap rather than inventing a locator or omitting it.
A justified N/A is still an output that states
what was assessed and why it does not apply. ShipLoop starts an Improve child
after planning results (spec, test-strategy, plan, step-plan, test-spec,
system-test-author, release-plan), after each accepted implement step, and after
the carry-forward that leaves no work item pending. Run only the checks this step's change needs. When this step changes no
product file, its check is the named command, its exit code and its required output
substrings: record them, cite the earlier accepted stage that ran the same command,
and do not reread history to repeat it.

## Blocked, and waiting for a person {#blocked}

ShipLoop runs unattended: no one is watching and nothing arrives on standard input.
- An open decision: take the default that best fits the request and the recorded knowledge, record it as an
  assumption (the alternatives and why this one), and continue.
- A step only a person can do (a sign-in, a grant, an observation in a signed-in browser): record it as an open item
  in the result (who must do what, what they report back) and continue with everything that does not depend on it.
- Only when nothing further can proceed without the person: outcome `blocked` with `blocked_by` user (or access, for
  a sign-in) and `awaiting`, one decision per question, in words the user can answer in one reply:
  - a decision: `{"kind": "answer", "question": "...", "options": [...], "no_default": "..."}`
  - something only a person can do: `{"kind": "present", "steps": [...], "report": "...", "no_default": "..."}`
  `no_default` says why no recorded default would do; ShipLoop refuses a wait without it. The run then stops until
  the user's own reply resumes it.
- Blocked means work this stage cannot do (a missing target, account or approval, or a command with no replacement
  inside the stage). A retained command that does not run what it claims is a documentation fix made in this stage,
  then rerun, not a blocker. A problem this run can fix itself is repaired in this stage.

## Result outcomes {#outcomes}

The result file holds one `shiploop-state` block whose object has "outcome" and "summary" as top-level fields; do
not wrap it in action or result keys. An outcome other than done keeps headline and evidence_refs and drops the
done-only fields (work_items, assumptions, steps, test_commands, ...):
- repeat: {"outcome": "repeat", "summary": "<what is still open>"}
- blocked: {"outcome": "blocked", "blocked_by": "user | access | external", "summary": "<what stopped the work>"},
  plus "awaiting" only as described in reference#blocked
- revise: {"outcome": "revise", "summary": "<what in the step plan or test spec is wrong>"}: the item goes back to
  step-plan with this result as evidence
- replan (only where the packet allows it): {"outcome": "replan", "summary": "...", "work_items": [{"id": "...",
  "title": "...", "context": "..."}]}
A packet lists the outcomes its stage accepts; any other is refused.

## Recovery {#recovery}

After an interruption or a reset, run the packet's Recover command: it only reads the saved state and reprints the
current packet. Check the paths and the task and repository identity, then reconcile actual effects with the saved
history and relevant evidence before repeating work. If the same run cannot be located, keep recovery incomplete; do
not initialize a replacement or invent a callback. If paused or blocked, resolve the condition and follow the
printed resume route; if halted or done, stop. Keep the run directory and the Recover command in any durable handoff:
they locate state.md and store no other graph position.
Recover: python3 <skills>/shiploop/scripts/shiploop next --run-dir=RUN

## Progress reporting {#progress}

Progress: do not reprint this packet's ShipLoop status block; it orients you.
The user sees the run's status through a host status hook where one exists. At
start/recovery and after each callback, tell the user at most one line of your
own: the item, the stage just finished and the stage now starting. Show the whole
block unchanged only when the user asks for the full status. At milestones a packet
also carries a ShipLoop narrative section; follow its first line, which says whether
you paste the narrative to the user as written or the host already showed it. Only the current owner reports overall progress. State labels say which action is assigned, not that work, tests, or
Improve iterations have occurred.  Describe Improve activity only from its own
observed records; do not infer a review count, completion percentage, or ETA.
Run to completion by default within scope and authority. Emit progress as an
intermediate update, then immediately continue the active packet's current owner
while authorized runnable work remains. Do not wait for acknowledgement, ask
whether to continue, or end the turn merely to deliver a report. Follow the exact
callback and its returned packet, including a bound Improve child; a producer's
done or a child's completion is not run completion. Respect explicit user stops
and paused/blocked/halted/done states. A user message that asks to stop or pause,
or says not to implement, is a stop for product work: run the current packet's pause
command, answer it, and resume only on an explicit continue. A question or comment
about this skill, the loop, its progress or its cost is not a stop: answer it
briefly and keep following the current packet. Do not pause on your own to ask
whether the run is worth continuing or to confirm the process for a small task;
the user's request already authorizes the run. Never end the turn while a ShipLoop
command is still running: keep each one in the foreground until it returns, and if
the host moves it to a background task, wait for that task in this same turn before
anything else. A `complete` that reruns tests can take minutes, and a headless host
ends the whole session when the turn ends, losing the callback. If a host keepalive
hook refuses to end the turn, its reason names this run's next command: run it and
follow the packet. Resolve recoverable conditions through the
printed route and ask only for an actually missing decision, authority, or access.

## Requirements and references {#requirements}

Requested runtime / entry point / material dependency: preserve each original
user requirement, and distinguish it from a verified contract, observed practice,
or assumption in the existing notes/results. Record local-test-route evidence
separately from target compatibility. A local fixture or preview cannot supply a
target capability absent from the requested runtime. Delivery outside the present
scope does not by itself make requested-runtime compatibility N/A. Establish
compatibility with target-compatible source or local evidence where possible;
otherwise keep the gap unresolved.

Follow the packet's Maintained requirements policy. Read the applicable accepted
product requirements, including preserved and cross-cutting conditions, from
their repository-owned home; a new request changes scope without erasing
unaffected rules. Carry requirement and test locators into work-item context.
Do not infer approved intent from code/tests or silently relax a condition to
match them. Keep proposals and verification gaps distinct from accepted intent.
Follow the packet's Reference handoff policy: distinguish package guidance,
repository-owned requirements/tests and run-local evidence. Resolve and verify
the selected file/section against its named root; retain exact applicable
locators for downstream work, not merely a link to this policy.
Use the packet's Requirements definition guide to reconcile existing specs and
define applicable non-functional requirements. Current explicit user instructions
supersede conflicting older clauses; preserve unaffected conditions and retain
clarification, requirement, and verification locators for cold recovery.
Later clarifications must be actual user instructions for this same request with
their durable user-source/decision basis; an unverified host summary is not an
instruction. Use the active correction/revision route for affected frozen contracts.

## Policies and guides {#policies}

Each label is what a packet or stage text names; open only the section a step needs.
- Access-readiness policy: <skills>/shiploop/references/research-loop.md#early-access-readiness
- Delivery-authority policy: <skills>/shiploop/references/delivery-authority.md
- Environment lifecycle policy: <skills>/shiploop/references/environment-lifecycle.md
- Cross-run knowledge policy: <skills>/shiploop/references/project-knowledge.md
- Maintained requirements policy: <skills>/shiploop/references/project-knowledge.md#maintained-product-requirements
- Requirements definition guide: <skills>/shiploop/references/requirements-definition.md
- Stage readiness and completion guide: <skills>/shiploop/references/testing-and-documentation.md#stage-readiness-and-completion
- Initial repository baseline guide: <skills>/shiploop/references/execution-planning.md#initial-repository-baseline
- Reference handoff policy: <skills>/shiploop/references/project-knowledge.md#reference-handoffs-and-destinations
- Consumer testing guide: <skills>/shiploop/references/testing-and-documentation.md#lightweight-and-browser-checks
- Repeatable test-suite guide: <skills>/shiploop/references/repeatable-test-suites.md
- Selected-case reconciliation guide: <skills>/shiploop/references/testing-and-documentation.md#test-cases
- Real-boundary selection guide: <skills>/shiploop/references/testing-and-documentation.md#surface-selection
- Interaction design guide: <skills>/shiploop/references/behavioral-requirements.md#actors-channels-and-state-ownership
- Worktree and artifact policy: <skills>/shiploop/references/workspace-lifecycle.md
- Navigator contract: <skills>/shiploop/references/navigator.md
- Environment lifecycle note (host-authored, if present): RUN/notes/environment-lifecycle.md
- Repository knowledge index (host-authored, if present): WORKTREE/SHIPLOOP.md
- ShipLoop skill card: <skills>/shiploop/SKILL.md
- State: RUN/state.md · results: RUN/results · inbox: RUN/inbox

## Workspace and the source return {#workspace}

All product work happens in the execution checkout; run state, results and reports stay outside it. Each item is
assembled there, and ShipLoop commits its declared files when verify is accepted; the original branch is returned only
at release or handoff, after the assembled-candidate checks. There, `workspace plan-return` commits product files still uncommitted onto the
run branch (never run evidence or protected paths) and binds a path review;
decide every path with `workspace review-return --keep PATH... --exclude PATH...` (keep lasting work, exclude
transient output), then `workspace return`. The release packet prints the exact commands. No automatic push,
cleanup or publication is implied.
````

## HOME/spec.md (whole file)

*The step's anchors. The packet file quotes architecture.md and environment.md whole and the followed R-n entries of spec.md by value; the step block names the sections.*

````markdown
# Spec

Single-player Battleship, Node.js HTTP server, no npm dependencies. Basis for all R-<n>: the original request (intake) plus recorded defaults. Status: R-1..R-7 implemented in work item W1 and confirmed by its tests (see docs/shiploop/environment.md ## Harnesses and suites); the full-game browser observation is re-run at system-test.

## Requirements

### R-1 Server startup and port
Basis: request ("server.js starts the server on the port in the PORT environment variable (default 3000)").
- AC-1.1 `PORT=<n> node server.js` listens on `<n>`; with PORT unset it listens on 3000. Confirmed by: subprocess test runs `PORT=<free port> node server.js`, GETs `/` on that port, then kills it; a second subprocess with PORT unset is not bound in tests (3000 may be taken) so the default is confirmed by the unit test of the port-parsing function `resolvePort(undefined) === 3000` in AC-1.3.
- AC-1.2 Unknown route returns HTTP 404 JSON `{"error": ...}`; wrong method on a known route returns 405. Confirmed by: HTTP test.
- AC-1.3 Boundary: `resolvePort(env)` returns 3000 for undefined, empty, non-numeric (`"abc"`), fractional (`"1.5"`) or out-of-range (`"-1"`, `"65536"`) PORT, and the integer for `"0"` (ephemeral), `"8080"`, `"65535"`. Confirmed by: unit test of the port-parsing function.

### R-2 Game page
Basis: request ("GET / serves a playable HTML page titled 'Battleship' ... 10x10 grid").
- AC-2.1 `GET /` returns 200, `Content-Type: text/html`, body contains `<title>Battleship</title>`. Confirmed by: HTTP test.
- AC-2.2 The page renders a 10x10 grid (100 clickable cells, rows/cols 0-9), starts a game via `/api/new` on load and via a "New game" button, fires via `POST /api/fire` when a cell is clicked, and shows miss / hit / sunk on that cell, a status message, and "Game over" when `gameOver` is true. Fired cells cannot be fired again in the UI and further clicks are ignored after game over. Confirmed by: HTTP test that body contains the grid/script hooks (`id="board"`, `/api/new`, `/api/fire`) and a replayable smoke: start the server, `curl -s localhost:$PORT/api/new`, then `curl -s -X POST -d '{"game":"<id>","row":0,"col":0}' localhost:$PORT/api/fire` returns JSON with `result` and `gameOver`; plus a browser check of the page at the system-test stage (click cells, observe hit/miss/sunk marks).
- AC-2.3 The page never receives ship positions (see R-5).

### R-3 New game
Basis: request ("GET /api/new starts a game and returns JSON with a game id").
- AC-3.1 `GET /api/new` returns 200 JSON `{"game": "<id>", "size": 10, "ships": [lengths]}`; `game` is a non-empty string, unique per call. Confirmed by: HTTP test (two calls yield different ids).
- AC-3.2 Each game has a fleet placed by the computer: carrier 5, battleship 4, cruiser 3, submarine 3, destroyer 2 (17 cells), all in-bounds, straight horizontal or vertical, no overlap. Placement is random per game. Confirmed by: unit tests over many random seeds/placements.

### R-4 Fire
Basis: request ("POST /api/fire with JSON {game,row,col} returns JSON with result miss|hit|sunk and gameOver").
- AC-4.1 Firing at a cell with no ship returns 200 `{"result":"miss","gameOver":false,...}`. Confirmed by: unit and HTTP tests with a deterministic fleet.
- AC-4.2 Firing at a ship cell that leaves the ship with unhit cells returns `"hit"`; hitting the last unhit cell of a ship returns `"sunk"` (response also names the ship in `ship`). Confirmed by: unit tests.
- AC-4.3 `gameOver` is true exactly when the response sinks the last ship, and false otherwise. Confirmed by: unit test shooting every ship cell.
- AC-4.4 Response always includes `row` and `col` echoing the shot.
- AC-4.6 Worked example (deterministic fleet with only a destroyer at row 0, cols 0-1, plus a second ship at row 5, col 5 of length 1 for the test): fire (9,9) -> `miss`, gameOver false; fire (0,0) -> `hit`; fire (0,1) -> `sunk` with `ship:"destroyer"`, gameOver false; fire (5,5) -> `sunk`, gameOver true; fire (5,5) again -> 400 (game over). Confirmed by: unit test with an injected fleet.
- AC-4.5 Errors, all JSON `{"error": msg}`: malformed JSON, missing/non-integer/out-of-range (not 0-9) row or col, or missing game -> 400; unknown game id -> 404; cell already fired -> 400 and game state unchanged; any fire after gameOver -> 400. Body over 10 KB -> 413. Confirmed by: unit and HTTP tests per case, boundary values -1, 10, 0, 9, 1.5, "3", null.

### R-5 Hidden state
Basis: spec stage state lifecycle (opponent's hidden fleet must not reach the client).
- AC-5.1 Ship positions are held only on the server; no response before game over contains the fleet layout. Confirmed by: test that scans `/api/new` and every `/api/fire` response for fleet fields.
- AC-5.2 Games are in-memory, owned by the server process, kept up to 1000 at once; the oldest is evicted beyond that; a restart removes all games (unknown id then returns 404). Concurrent requests are handled in order by single-threaded Node; each fire is atomic. Confirmed by: unit test creating 1001 games with a small injectable cap/the real cap and checking the first id returns 404 while the latest works.

### R-6 Rules module separation
Basis: request ("Keep the game rules in a module the server uses").
- AC-6.1 Rules live in `game.js` (no http import, no I/O); `server.js` requires it and holds no placement/hit logic. Confirmed by: test requires `game.js` without starting a server; grep check that server.js does not contain rules.
- AC-6.2 Rules accept an injectable random source so placement is testable. Confirmed by: unit test.

### R-7 Tests
Basis: request ("cover them with node:test tests under test/ that run with `node --test`").
- AC-7.1 `node --test` from the repository root exits 0 and runs rules tests and server (HTTP) tests from `test/`. Confirmed by: running the command; counts recorded.
- AC-7.2 Tests use only `node:test` and `node:assert`, no npm packages, no fixed ports. Confirmed by: grep and run.

## Non-functional requirements
- NFR-1 No npm dependencies: no package.json dependencies; only Node built-ins. Confirmed by: grep for require of non-`node:`/relative modules.
- NFR-2 Input safety: request bodies capped at 10 KB; game ids unguessable (crypto random UUID); user input never echoed into HTML. Confirmed by: HTTP tests.
- NFR-3 Performance: a fire request is O(1); placement completes in under 50 ms per game (rejection sampling on 10x10). Confirmed by: unit test timing generous bound over 1000 placements.
- NFR-4 Portability: runs on Node >= 18 built-ins (observed v25.9.0). Excluded: accessibility beyond keyboard-focusable buttons for cells, auth, persistence, multi-player, deployment, localization (not requested).

## Retired
None.
````

## HOME/architecture.md (whole file)

*The step's anchors. The packet file quotes architecture.md and environment.md whole and the followed R-n entries of spec.md by value; the step block names the sections.*

````markdown
# Architecture

## Stack
Node.js (v25.9 observed, built-ins only: `http`, `crypto`, `fs`, `node:test`, `node:assert`). CommonJS. Plain HTML/CSS/JS page, no framework or build.

## Structure
- `game.js`: pure rules module (no I/O, no http). Exports `createGame`, `fire`, `placeFleet`, `FLEET`, `SIZE`, `createStore` (in-memory map with cap).
- `server.js`: HTTP layer. Exports `createServer(options)` and `resolvePort(env)`; starts listening only when run directly (`require.main === module`).
- `package.json`: minimal, `"private": true`, no dependencies, scripts `start` and `test` (CommonJS by default; no `type` field).
- `public/index.html`: the page, served by `GET /` (read once at startup from disk).
- `test/*.test.js`: node:test tests (only test files go under `test/`: node --test runs every .js there); `test-support/helpers.js` shared helper.

## Conventions
2-space indent, semicolons, `'use strict'`, `const`, small functions, JSON errors `{error}`. Source: proposal in environment.md (no prior code).

## Interfaces and boundaries
- `GET /` -> HTML; `GET /api/new` -> `{game,size,ships}`; `POST /api/fire` `{game,row,col}` -> `{result,gameOver,row,col,ship?}`; errors per R-4. Fleet positions never leave the server.
- Boundary: server.js depends on game.js, never the reverse.

## Real-boundary checks
- Status after W1: TC-1..TC-5, TC-7, TC-8..TC-17 pass locally; TC-6 passed locally in headless Chrome and is re-observed on the assembled checkout at system-test (owner: agent). No remote targets.
- Local only; no remote target. TC-2 (real process, real socket) and TC-4..TC-13 (real HTTP over loopback to `createServer`) are the real boundary. TC-6 drives the page in headless Chrome against a locally started server (client against local target), opt-in; due system-test stage. A passing unit test is not a passing browser case. Browser probe passed (RUN/scratch/probe-out.txt); no access gaps.

## Decisions
- AD-1: Rules in `game.js` with injectable random source and injectable fleet for tests (basis R-6, AC-6.2).
- AD-2: In-memory `Map` keyed by `crypto.randomUUID()`, oldest-evicted at 1000 games (basis R-5, NFR-2).
- AD-3: Fire responses omit fleet layout; `ship` name only on `sunk` (basis R-5).
- AD-4: Tests start the server on port 0; the port-from-env path is checked via `resolvePort` plus one subprocess test (basis R-1, AC-7.2).

- AD-5: Placement: server holds the fleet and game state (the request requires server-side computer placement and a server fire API); the page is a thin client with no persistence. Channel: request/response only, no polling, SSE or WebSockets. Safeguards: server-side validation of every fire, 10 KB body cap, 1000-game cap, unguessable ids. Basis R-4, R-5, NFR-2.
- AD-6: One work item (W1) delivers game.js, server.js, page, package.json and all tests: single increment with one proving command (`node --test`); the rules seam `require('./game')` and `require('./server')` (exports `createServer`, `resolvePort`) is loadable by tests before the page exists. Basis R-1..R-7.
- AD-7: UI is a single static page, vanilla JS, keyboard-operable cell buttons (arrow keys move focus, Enter/Space fire), CSS transition on hit/miss marks disabled under `prefers-reduced-motion`, live status in an `aria-live` region, New game button. Scaled back (no drag placement, no animations beyond a short mark transition) because the player does not place ships. Design guidance: repository fallback (none present). Basis R-2.

- AD-8: `server.js` takes the route from `req.url.split('?')[0]` instead of `new URL(req.url, base)`, because `new URL` throws on targets like `//` (found in W1 verify, answered 500; now 404). Basis R-1 AC-1.2.

## Superseded
None.
````

## HOME/environment.md (whole file)

*The step's anchors. The packet file quotes architecture.md and environment.md whole and the followed R-n entries of spec.md by value; the step block names the sections.*

````markdown
# Environment

## Targets and runtimes
- Observed: Node.js v25.9.0 (`node --version`), built-ins only; no npm dependencies, no package install. Binding requirement (request): `node --test` runs the tests; `node server.js` starts the server.
- Development/test target: local machine, localhost HTTP. Delivery target: the source checkout `/Users/dadleet/e2e-runs/20261016/battleship-e2eaudit-4dd3b4b4/work`, via ShipLoop's guarded workspace return. No CI, deploy or publication route exists (empty repo, no remote). Return triggers nothing.
- Uncertainty: none material.

## Commands
- Test: `node --test` (from repo root; runs every .js file under `test/`, 21 tests, 1 skipped = opt-in browser case). Observed working in W1.
- Browser case: `BATTLESHIP_BROWSER=1 node --test test/browser.test.js` (needs Google Chrome; observed 1 pass).
- Smoke of the live API: `PORT=0 node server.js` prints the chosen port; `curl -s localhost:<port>/api/new`, then `curl -s -X POST -d '{"game":"<id>","row":0,"col":0}' localhost:<port>/api/fire` (observed).
- Run: `PORT=<n> node server.js` (default 3000).
- No linter, formatter or type checker configured; none installed (install nothing).

## Platform facts
- Greenfield: repo contained only an empty baseline commit (2bf890e); no README, AGENTS.md, CLAUDE.md, package.json, tests or reusable code. Source: `git log`, `ls`.
- Baseline: `node --test` on unchanged checkout: exit 0, 0 tests (missing coverage). Output: RUN/scratch/baseline.txt.
- House style (proposal, no existing code): CommonJS modules, 2-space indent, semicolons, `'use strict'`, small pure functions, rules in `game.js`, HTTP in `server.js`, UI in `public/index.html` or inlined, tests in `test/*.test.js` with `node:test` + `node:assert/strict`.
- Proposal: HTTP API tests start the server on port 0 (ephemeral) to avoid port clashes.

## Skills
- No repository-local skills; no fit. Source: empty repo.

## Access and accounts
- None needed; local only, no credentials.

## Harnesses and suites
All checks below are **planned**, not passed (nothing implemented). Harness: `node:test` + `node:assert/strict`, built into Node v25.9 (revalidated: `node --test` ran, exit 0, 0 tests at baseline). Isolation: each test builds its own game objects; HTTP tests start `createServer()` from `server.js` on port 0 in `before`, close it in `after`; no shared state, no fixed ports. Fixtures: deterministic fleets injected through `game.js` (`createGame({fleet})`) and injectable `random`. Revalidate when Node major changes.

Files: `test/game.test.js` (rules, unit), `test/server.test.js` (HTTP integration, subprocess port test), `test/browser.test.js` (opt-in consumer test).

| Layer | Requirement | Check (planned) | Surface | Due |
|---|---|---|---|---|
| unit | R-1/AC-1.3 | TC-1 resolvePort cases | game/server module | test |
| integration | R-1/AC-1.1 | TC-2 subprocess `PORT=<free> node server.js`, GET / | process + HTTP | test |
| integration | R-1/AC-1.2 | TC-3 404 and 405 JSON | HTTP | test |
| integration | R-2/AC-2.1 | TC-4 GET / 200 text/html, `<title>Battleship</title>` | HTTP | test |
| integration | R-2/AC-2.2 | TC-5 page has `id="board"`, `/api/new`, `/api/fire` hooks | HTTP | test |
| consumer | R-2/AC-2.2 | TC-6 headless Chrome driven over CDP (Node built-in `WebSocket`): load page, assert 100 `#board` cells, click every cell in order until the status shows Game over, assert each clicked cell has class hit/miss/sunk and at least one of each of hit, miss and sunk was seen; opt-in `BATTLESHIP_BROWSER=1` | browser | system-test |
| integration | R-3/AC-3.1 | TC-7 /api/new JSON shape, ids unique | HTTP | test |
| unit | R-3/AC-3.2 | TC-8 placement: 5 ships 5/4/3/3/2, 17 cells, in bounds, no overlap, over 500 random games | rules | test |
| unit | R-4/AC-4.1-4.4,4.6 | TC-9 miss/hit/sunk/gameOver worked example; TC-10 gameOver only on last ship; TC-11 echo row/col | rules + HTTP | test |
| unit+HTTP | R-4/AC-4.5 | TC-12 error cases: bad JSON, missing/-1/10/1.5/"3"/null row or col, unknown game 404, repeat shot 400 unchanged state, fire after over 400, 413 oversize | rules + HTTP | test |
| integration | R-5/AC-5.1 | TC-13 no fleet fields in any response | HTTP | test |
| unit | R-5/AC-5.2 | TC-14 eviction cap | rules | test |
| unit | R-6 | TC-15 game.js loads without http/net, injectable random; server.js has no rules (grep check) | rules | test |
| check | NFR-1,7.2 | TC-16 grep: no non-node:/relative requires, no fixed ports in tests | repo | verify |
| unit | NFR-3 | TC-17 1000 placements under generous time bound | rules | test |
| meta | R-7/AC-7.1 | `node --test` exits 0 and prints the TC names | repo | verify |

Expected-RED control: before implementation, `node --test` on the new test files must fail (modules missing); recorded by the test stage's base run.
Facility status (W1): `test-support/helpers.js` built and in use (startServer, request, seededRandom); ready; owner: this repo; revalidate when `server.js` exports change. Original plan: none to reuse (greenfield); smallest new facility is a helper in `test-support/helpers.js` for `startServer()` and `request()` using `node:http`; owner: work item W1 test stage. Lives outside `test/` because `node --test` (probed on Node v25.9, RUN/scratch/nt) executes every .js file under a `test/` directory, so a helper there would run as a counted test file.
Browser: headless Google Chrome 
(`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --headless=new --disable-gpu --no-sandbox --virtual-time-budget=2000 --dump-dom <url>`) probed now against a stand-in page in RUN/scratch/probe.html: it ran the page script and printed the DOM, exit via kill after output (see RUN/scratch/probe-out.txt). `--dump-dom` cannot click, so TC-6 launches Chrome with `--headless=new --remote-debugging-port=0 --user-data-dir=<tmp>`, reads the `ws://` URL from stderr, and sends `Page.navigate` / `Runtime.evaluate` (click via `element.click()`) over Node's built-in `WebSocket`; second probe printed a DevTools ws endpoint (RUN/scratch/cdp-probe.txt), and Node reports `typeof WebSocket === 'function'`. Probe succeeded, so no access gap. The test kills Chrome in `after` and removes the temp profile. `timeout` is not installed on this host; do not use it in commands.

## Commands
Full suite (inclusion: every file under test/; `test/browser.test.js` is discovered too but its test is declared with `{skip: !process.env.BATTLESHIP_BROWSER}`, so it reports as skipped (not failed) by default and TC-6 never counts toward the default floor; cost a few seconds; no prerequisites; prints TC-1..TC-17 names):
```sh
node --test
```
Smoke (bounded subset, rules only; not evidence for the full suite):
```sh
node --test test/game.test.js
```
Opt-in browser consumer case (needs headless Chrome path above; prints TC-6):
```sh
BATTLESHIP_BROWSER=1 node --test test/browser.test.js
```
Run server:
```sh
PORT=3000 node server.js
```
Lint/format/type: none configured.

## ID convention
Test IDs are `TC-<n>` (n from the table above) and each appears as its own word at the start of the test's printed name, e.g. `TC-9 miss, hit, sunk and gameOver worked example`. Several IDs may be listed in one name, separated by spaces; sub-cases use `TC-12 (bad JSON)`, never `TC-12a`.

## Readiness
Prepared environment: worktree with Node v25.9.0; `node --test` starts and exits 0 with 0 tests (runner works; RUN/scratch/prepare-runner.txt). Headless Chrome + CDP probed for TC-6. Nothing to install or provision.

## System tests
Catalog (all run against the real `node server.js` process or the real page; candidate: assembled worktree; owner: agent; due: system-test; runnable now):
| Case | Requirement | Expected outcome | Executable |
|---|---|---|---|
| ST-1 | R-1..R-5 | full game over HTTP on a real port: 17 ship hits, 5 sunk, gameOver true, then 400 | `node --test test/system.test.js` |
| ST-2 | R-3, R-5 | two games are independent with unique ids | `node --test test/system.test.js` |
| TC-6 | R-2 | headless Chrome plays a full game on the page | `BATTLESHIP_BROWSER=1 node --test test/browser.test.js` (host dependent: needs Chrome) |
System cases sit in the default full suite (`node --test`) except the browser case. Cost: about 1 s plus 3 s for the browser case. Nothing needs a release or deployment.

## Release plan
- Target: the user's local source checkout (branch main). No deployment, publication, CI or remote exists; the product is run locally with `node server.js`.
- Steps: (1) `workspace plan-return` then `workspace return` fast-forward main to the run branch (authority: the user's request to build in this repository; local file operation only). (2) Consumer checks in a clean copy of the returned result: `node --test` and `node --test test/system.test.js`. (3) The person starts `node server.js` and opens `http://localhost:3000/`.
- Prerequisites: all system tests green (done); Node on PATH. Stop condition: any consumer check fails.
- Delivery authority: local source return only, no push, no remote. Nothing else needs approval.
- Pre-release check (release-check): `node --test` exit 0 in the worktree. Post-release (release-verify): the consumer checks above run in a clean copy; present: both commands exit 0 and show `ℹ fail 0`; absent (empty directory, observed at release-check): `node --test test/system.test.js` exits 1 with "Could not find 'test/system.test.js'", while plain `node --test` exits 0 with 0 tests, so only the system-test command tells present from absent.

## Rollback
Run from the repository root; undoes the fast-forward return when nothing was committed after it:
```sh
git reset --keep 2bf890e3c79d0b4220ff8dc3d0225a9dd482e8ed
```
````

