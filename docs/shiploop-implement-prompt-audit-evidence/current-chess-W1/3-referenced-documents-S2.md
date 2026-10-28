# 3. The documents the S2 prompt references

Rendered by ShipLoop's own `emit()` from branch `shiploop/implement-prompt-2d6ecc` (4eae0910) for the Salesforce chess case, work item W1 "Deploy the chess engine and pass the rules tests" (1 of 2), using run 2's real records: its spec, architecture and environment files, W1's latest accepted step plan and test spec, and both work items (`docs/shiploop-implement-prompt-audit-evidence/render-chess-W1-example.py`). The step plan predates the new schema, so each step was given what a step plan must now record: S1's check is the run's own C1 project-file check, S2's is its local C9 check (a deploy is a remote effect, so it cannot be a step Proof), plus cards and a match row. Only machine paths are shortened: RUN = the run directory, WORKTREE = the product checkout, <skills> = the skills directory.

| Document | How the prompt uses it | Where |
|---|---|---|
| `references/implement-guidance.md` | inserted word for word as "Current stage guidance" | printed prompt |
| `references/code-craft.md` | inserted word for word after the guidance (code steps only) | printed prompt |
| `platforms/salesforce.md`, `coding-practices.md#composition-and-layers`, `coding-practices.md#state` | S2's **Cards**: read before the first edit | step block |
| `coding-guidance.md#select-guidance`, `house-style.md#match-while-building`, `service-discovery.md#development-handoff`, `repeatable-test-suites.md#select-target-native-tests` | the stage's guide locators | packet file |
| Until Loop `ADAPTER.md`, "Start from a parent-written contract" | how to invoke the loop off Claude Code | loop block |
| `RUN/reference.md` | the long form of the rules, policies and recovery | packet file |
| `HOME/spec.md` (R-2..R-8, R-12, R-13), `HOME/architecture.md` (AD-1, AD-2), `HOME/environment.md` | the step's anchors | packet file |

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

## platforms/salesforce.md (whole file)

*A Card on S2's step block: read before the first edit.*

````markdown
# Salesforce development

Return to the [guidance selector](../coding-guidance.md#select-guidance) when
the runtime or boundary changes. Identify the Apex/LWC boundary, transaction
entry point, API version, and permission context. Verify the selected API
version and supported access mode before relying on a default; do not copy an
obsolete assumption that all work is system mode. Record sharing, object
permissions, and field permissions as separate requirements. Use supported
user-mode operations or deliberate field-sanitization and error behavior as
appropriate; `with sharing`, a visible control, or a passing mock alone does
not establish CRUD/FLS enforcement. [Salesforce's secure Apex guidance](https://developer.salesforce.com/docs/platform/lwc/guide/apex-security.html)
is the version-sensitive starting point.

Design collection-based entry points. Inspect query/DML placement and
transaction-wide consumption under realistic bulk input, including existing
automation, ordering, duplicate handling, partial-success policy, and useful
errors. A single-record unit test cannot prove bulk safety.

In LWC, preserve public and wire-data ownership and use the actual cache-refresh
mechanism for the source. Check asynchronous success, failure, stale results,
and rendered states. JavaScript doubles do not establish Apex execution,
permission behavior, governor use, or org behavior; exercise those boundaries
in an identified disposable org when required.

Apex class, trigger and metadata API names are org-wide unless a package
namespace prefix qualifies them; check the org and installed packages for a
clash before choosing one. In a managed package, a `global` member is a
permanent contract once released, so prefer `public` until a subscriber needs
it. Without a package namespace, LWC components share the org's default `c`
namespace.

Model stored data in the org's schema: extend an existing standard or custom
object before creating one, and choose field types, required flags, uniqueness,
lookup or master-detail relationships and sharing deliberately; renaming a
custom field's API name breaks the code, reports and integrations that use it.
Keep configuration in custom metadata types, which deploy with the code, rather
than in records.

## Service discovery

Before choosing component, tab or app names, list what the target org already has
(`sf org list metadata --metadata-type LightningComponentBundle`, `CustomTab`,
`CustomApplication`). A Tooling query on `CustomTab.Name` returns INVALID_FIELD,
so use the metadata listing for tab evidence. Treat another ShipLoop run against
the same org as a naming constraint: pick names it does not use.
Separate the deploy from each visibility step (permission-set assignment, app or
tab access): each is its own command with its own authorization, planned by name
at release-plan.

A consumer entry is source metadata, not a side effect. `lightning__Tab` in a
component's `js-meta.xml` only makes the component eligible for a tab; it creates
no tab anyone can open. Plan the entry as files at step-plan: a `CustomTab`
(`tabs/<Name>.tab-meta.xml`) and, when the design needs one, an app
(`applications/<Name>.app-meta.xml`) that lists the tab, plus the permission set
or profile visibility that shows them. Confirm the tab with
`sf org list metadata --metadata-type CustomTab --target-org <alias>` and look
for its API name. The Tooling `CustomTab` query returns no rows for a Lightning
component tab and would stay red after a good deploy. Run that confirm once at
release-check, beside `sf project deploy validate` (the dry-run), so its
"not there yet" output is on record before the real deploy.

When Salesforce is an affected service boundary, apply the conditional
[service discovery guide](../service-discovery.md). Record the observed selected
tool or supported route, current org/role evidence, and the separate authority
needed for metadata/schema, configuration, and record CRUD. An MCP inventory or
developer deployment identity does not establish the runtime caller's access.
For incremental work, reconcile prior accepted intent, current local source or
metadata definition, observed org state, and the requested delta; preserve
unrelated fields and automation. A safe authorized metadata/state read is
discovery evidence, not authority to mutate the org.

For each runtime read, record sharing, object CRUD, and field-level security
(FLS) separately. `with sharing` alone does not establish CRUD/FLS enforcement.
If caching is selected, identify its actual native owner and refresh mechanism:
do not attach generic invalidation plumbing to Apex wire results or Lightning
Data Service without verifying the selected source's supported refresh path.
For an asynchronous metadata deployment or background operation, an accepted
request/ID is not final status; retain the terminal status and authorized
read-back.

Example: before adding `ReviewStatus__c`, inspect the selected object's current
metadata and preserve an observed `Consent__c` field and automation. Plan an
additive change, keep remote records authoritative through the current runtime
adapter, leave a cache conditional on authorization/invalidation evidence, and
verify the final metadata/status read-back for the intended role.

Apply [target-native test selection](../repeatable-test-suites.md#select-target-native-tests)
to the affected repo/org metadata and actual deployment route. LWC Jest checks
components locally; Apex tests execute in the org; browser checks observe the
Lightning consumer. None substitutes for the others' required boundary.
Select Apex coverage for changed or affected Apex behavior, or when the actual
deployment/packaging/CI gate requires it. Check the payload, target environment,
effective test level and applicable coverage rule rather than inferring them
from an org label. A verified LWC-only development deployment with no affected
Apex and no Apex test gate may exclude Apex tests; do not add Apex or empty test
classes to fill an inventory. Reopen that exclusion when its basis changes.
[LWC testing](https://developer.salesforce.com/docs/platform/lwc/guide/testing)
and the [deployment command's test-level contract](https://developer.salesforce.com/docs/platform/salesforce-cli-reference/guide/cli_reference_project_deploy_start.html)
are starting points; verify the rules for the operation actually selected.

For a Lightning consumer, distinguish the org/instance identity from the
feature's authenticated entry: an app, custom tab, component or other supported
page. Use supported navigation (for example a generated `PageReference` URL)
and verify the destination after redirects, with the intended user's role,
visible feature and required interactions. Preserve a non-secret usable route
in the handoff; an instance home alone is not the app link. A custom tab in an
existing shell can be correct; verify a particular app/navigation identity when
the accepted design requires it, without inventing an org-wide branding rule.
Do not hard-code a Salesforce hostname as the universal consumer boundary.
[Salesforce navigation](https://developer.salesforce.com/docs/platform/lwc/guide/use-navigate-basic.html)
and [page types](https://developer.salesforce.com/docs/platform/lwc/guide/reference-page-reference-type.html)
define the supported navigation contract. This supplements the generic
[browser evidence guidance](../testing-and-documentation.md#lightweight-and-browser-checks).

Open that browser session from the org's existing CLI authentication rather than
asking the user to sign in: `sf org open --target-org <alias> --url-only --path
<page>` prints a one-time front-door URL for the page, which a browser tool can
open directly. At discovery, run it once (without opening the page) to prove the
route, and record the alias and page path. Keep the URL out of evidence and
logs: it is a session credential. Ask the user only when the CLI has no working
authentication for the target org.
````

## coding-practices.md#composition-and-layers

*A Card on S2's step block: read before the first edit.*

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

## coding-practices.md#state

*A Card on S2's step block: read before the first edit.*

````markdown
## State

Identify the authoritative owner, scope, lifetime, and allowed transitions.
Where applicable, define atomicity, persistence, concurrency, retry or
idempotency, cancellation, and partial-failure recovery. Derived caches need a
validity and invalidation rule; consumers must not become competing authorities.
Validate before irreversible effects and preserve or repair invariants after a
partial failure. Recheck old/new representation compatibility when data
persists. Use the simplest sufficient mechanism: stateless behavior does not
need a store, event bus, or queue.
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

Run nav-5ea5279645284125b13d1192fa8e95d2. Packets name a section as reference#<anchor>; open it only when the packet says to, or after a reset.

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

*S2's anchors. The packet file quotes architecture.md and environment.md whole and the followed R-n entries of spec.md by value; the step block names the sections.*

````markdown
# Spec

No earlier requirements exist. Every ID below is added from the original request. Preserved behavior: none. The current system at discovery was an empty repository (run/notes/current-system-baseline.md). That sentence is the as-of baseline.

W1 observed R-1 and the rules oracles in R-2 through R-8 in alias `de`: `SLChessRulesTest` reported `Tests Ran` 11 and `Outcome Passed`. The rules half of R-12 and the middlegame `legalMoves` bound in NFR-1 were in that same run. R-9, R-10, R-11, the game half of R-12, the depth-2 count and the Opera game in NFR-1, and the full metadata set in R-13 stay open for the board item, system-test, release, and release-verify.

## Requirements

### R-1 Project shape

Basis: the request says the Salesforce DX root is the current directory, not a subfolder.

Behavior: `sfdx-project.json` and `force-app/` sit at the repository root. `packageDirectories` is `force-app`. `sourceApiVersion` is `67.0`.

Acceptance:

- Positive: both paths exist at the root and the package directory is `force-app`. Confirmed by reading `sfdx-project.json` in the worktree.
- Failure: a nested project folder is not the root. Confirmed by the same read.
- Boundary: `docs/` stays outside `force-app` so it is not deployed.

State: source files only. No org records.

### R-2 Engine surface

Basis: `SLChessEngine` is a public class with static methods only. A position is a FEN string.

Behavior: `startFen()` returns `rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`.

Acceptance:

- Positive: that exact string. Confirmed by an Apex test calling `SLChessEngine.startFen()`.
- Failure: any other start string fails that assertion.
- Boundary: the method takes no arguments.

### R-3 Legal moves

Basis: `legalMoves(String fen)` returns every legal move for the side to move, UCI, sorted alphabetically.

Behavior: promotions use a trailing `q`, `r`, `b`, or `n` (`e7e8q`). Castling is `e1g1`, `e1c1`, `e8g8`, `e8c8`.

Acceptance, confirmed by Apex tests calling `SLChessEngine.legalMoves` and comparing the list size and, where listed, the membership:

- Positive: start position has 20 moves. Kiwipete `r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1` has 48, including `e1g1` and `e1c1`. Position `8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1` has 14. Position `rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8` has 44. The returned list equals its own sort using Apex string order, so `e1c1` precedes `e1g1`.
- Failure: a move that leaves the mover's king in check is absent. From `4r3/8/8/8/8/8/4R3/4K3 w - - 0 1`, the white rook on e2 is pinned by the black rook on e8, so `e2d2` is absent and `e2e3` is present. A sort that is not alphabetical fails.
- Boundary: no legal moves in the stalemate and checkmate fixtures in R-7.

Oracle source: Chess Programming Wiki perft depth 1, recorded in run/notes/research.md.

### R-4 Apply move

Basis: `applyMove` returns the FEN after a legal move with castling rights, en-passant square, halfmove clock, and fullmove number.

Acceptance, confirmed by Apex tests of these exact transitions:

- Positive: `applyMove(startFen(), 'e2e4')` returns `rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1`.
- Positive: `applyMove(startFen(), 'g1f3')` returns `rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1`. A capture or pawn move sets the halfmove clock to 0. A black move increments the fullmove number. A white move does not.
- Positive: `applyMove('4k3/8/8/8/8/8/8/4K2R w K - 0 1', 'e1g1')` returns `4k3/8/8/8/8/8/8/5RK1 b - - 1 1` (king on g1, rook on f1, the K right gone). `applyMove` of `h1h2` on that same start returns `4k3/8/8/8/8/8/7R/4K3 b - - 1 1` (the rook moved, the king stayed, and the K right is gone). `applyMove('4k3/8/8/8/8/8/8/R3K2R w KQ - 0 1', 'e1e2')` returns `4k3/8/8/8/8/8/4K3/R6R b - - 1 1` (the king stepped, both rooks stayed, and both K and Q are gone). `applyMove('4k3/8/8/8/8/8/r7/R3K3 b Q - 0 1', 'a2a1')` returns `4k3/8/8/8/8/8/8/r3K3 w - - 0 2` (capturing the rook on a1 drops Q).
- Positive: `applyMove` of `e7e5` on the R-4 `e2e4` FEN returns `rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2`. `applyMove(startFen(), 'e2e3')` returns `rnbqkbnr/pppppppp/8/8/8/4P3/PPPP1PPP/RNBQKBNR b KQkq - 0 1` (a one-square pawn push sets no en-passant square and sets the halfmove clock to 0). `applyMove('4k3/8/8/4p3/8/5N2/8/4K3 w - - 4 7', 'f3e5')` returns `4k3/8/8/4N3/8/8/8/4K3 b - - 0 7` (a knight capture sets the halfmove clock to 0).
- Failure: see R-5.
- Boundary: the en-passant square is set only for a two-square pawn push, and it is cleared by any other move.

### R-5 Illegal moves

Basis: an illegal move throws `SLChessEngine.IllegalMoveException`, a public exception class inside `SLChessEngine`.

Acceptance:

- Positive: `applyMove` on the start position with `e2e5` throws that type. Confirmed by an Apex test.
- Failure: returning a FEN, or throwing a different type, fails.
- Boundary: the grader calls the engine directly for the illegal case. The controller is not required to throw this type (R-9).

### R-6 En passant

Basis: the en-passant target is set after every two-square pawn push whether or not a capture is possible.

Acceptance:

- Positive: `e2e4` from the start sets the target to `e3` (R-4), and no black pawn attacks `e3`.
- Positive: `applyMove('rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3', 'e5d6')` returns `rnbqkbnr/ppp1pppp/3P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3`.
- Failure: omitting `d6` after a double push when no capture exists fails R-4. Allowing en passant when the target is `-` fails.
- Boundary: a one-square pawn push does not set a target (the `e2e3` result in R-4).

### R-7 Status

Basis: `status(String fen)` returns `ongoing`, `check`, `checkmate`, or `stalemate` for the side to move.

Acceptance, confirmed by Apex tests:

- Positive: start position is `ongoing`.
- Positive: after fool's mate `f2f3 e7e5 g2g4 d8h4` the position is `rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3` and the status is `checkmate`. The queen on h4 attacks e1 through g3 and f2. d2 and e2 still hold white pawns, d1 holds the white queen, f1 holds the bishop, and f2 is attacked, so the king has no flight.
- Positive: after scholar's mate `e2e4 e7e5 d1h5 b8c6 f1c4 g8f6 h5f7` the position is `r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4` and the status is `checkmate`. The queen on f7 is adjacent to the king and is protected by the bishop on c4. d8, d7, and f8 are blocked by black's own queen, pawn, and bishop.
- Positive: `8/8/8/8/8/6K1/5Q2/7k b - - 0 1` is `stalemate`.
- Positive: after `e2e4`, `f7f6`, `d1h5` from the start position, `status` is `check` and `legalMoves` is not empty. The queen on h5 attacks e8 through the empty squares g6 and f7. This is not the sequence `e2e4 e7e5 d1h5`: the pawn on f7 still blocks that diagonal, so that position is not check.
- Failure: checkmate or stalemate reported as `ongoing` fails.
- Boundary: status is about the side to move, not the side that just moved.

### R-8 Rules

Basis: all piece moves, both-side castling never out of, through, or into check, en passant, promotion to `q`, `r`, `b`, or `n`.

Acceptance:

- Positive: Kiwipete includes both white castles (R-3). From `4k3/8/8/8/8/8/8/4K2R w K - 0 1`, `e1g1` is present and its result FEN is in R-4. `applyMove('4k3/8/8/8/8/8/8/R3K3 w Q - 0 1', 'e1c1')` returns `4k3/8/8/8/8/8/8/2KR4 b - - 1 1` (king on c1, rook on d1). From `4k3/8/8/8/8/8/8/4K2R w - - 0 1`, `e1g1` is absent because the K right is missing. From `4k3/8/8/8/8/8/8/4KN1R w K - 0 1`, `e1g1` is absent because a knight on f1 blocks the king. From `4k3/8/8/8/8/5r2/8/4K2R w K - 0 1`, `e1g1` is absent: the black rook on f3 attacks f1, which the king would cross, and the white king on e1 is not in check. From `4k3/8/8/8/8/8/4r3/4K2R w K - 0 1`, `e1g1` is absent because the rook on e2 checks the king. From `4k3/8/8/8/6r1/8/8/4K2R w K - 0 1`, `e1g1` is absent because the rook on g4 attacks g1, the square the king would land on.
- Positive: from `r3k2r/8/8/8/8/8/8/4K3 b kq - 0 1`, `legalMoves` contains `e8g8` and `e8c8`. `applyMove` of `e8g8` on that FEN returns `r4rk1/8/8/8/8/8/8/4K3 w - - 1 2` (king on g8, rook on f8, both black rights gone). `applyMove` of `e8c8` on that same FEN returns `2kr3r/8/8/8/8/8/8/4K3 w - - 1 2` (king on c8, rook on d8). From `r3k2r/8/8/8/8/8/5R2/4K3 b kq - 0 1`, `e8g8` is absent because the white rook on f2 attacks f8, and `e8c8` is present.
- Positive: from `8/P7/8/8/8/8/8/k1K5 w - - 0 1`, `legalMoves` contains `a7a8q`, `a7a8r`, `a7a8b`, and `a7a8n`, and no bare `a7a8`. `applyMove` of `a7a8q` returns `Q7/8/8/8/8/8/8/k1K5 b - - 0 1`. `applyMove` of `a7a8r` returns `R7/8/8/8/8/8/8/k1K5 b - - 0 1`. `applyMove` of `a7a8b` returns `B7/8/8/8/8/8/8/k1K5 b - - 0 1`. `applyMove` of `a7a8n` returns `N7/8/8/8/8/8/8/k1K5 b - - 0 1`.
- Failure: castling through check, or a promotion without a letter, is absent from `legalMoves` and throws on `applyMove`.
- Boundary: underpromotion is required, not only queen.

Confirmed by Apex tests that list the moves and apply one of each promotion letter.

### R-9 Controller

Basis: the grader calls `SLChessController` with legal moves only.

Behavior: `@AuraEnabled public static` methods:

- `legalMoves(String fen)` returns `List<String>`
- `applyMove(String fen, String move)` returns `String`
- `status(String fen)` returns `String`

The values match the engine. An illegal move may be reported in whatever way suits the board, including `AuraHandledException`.

Acceptance:

- Positive: for each ply of fool's mate, scholar's mate, and the Opera game below, `legalMoves` contains the played move, `applyMove` returns the same FEN as the engine, and `status` matches the engine. Confirmed by Apex tests in one transaction per game.
- Opera game UCI, 33 plies, last move mates: `e2e4 e7e5 g1f3 d7d6 d2d4 c8g4 d4e5 g4f3 d1f3 d6e5 f1c4 g8f6 f3b3 d8e7 b1c3 c7c6 c1g5 b7b5 c3b5 c6b5 c4b5 b8d7 e1c1 a8d8 d1d7 d8d7 h1d1 e7e6 b5d7 f6d7 b3b8 d7b8 d1d8`. Final status `checkmate`.
- Failure: a controller result that disagrees with the engine fails.
- Boundary: the grader does not call the controller with an illegal move.

State: no custom object. The controller does not store the game.

### R-10 Board

Basis: two people play on one screen.

Behavior: `slChessBoard` renders the FEN as an 8 by 8 board. A person selects a piece, then a destination. The board shows whose turn it is and the status (`check`, `checkmate`, `stalemate`, and the side to move while ongoing). An illegal destination is refused and the position stays. A pawn promotion uses queen unless the person picks another of `q`, `r`, `b`, `n`. New game restores `startFen()`. The component calls `SLChessController` and renders the returned FEN and status.

Acceptance:

- Positive: the markup shows 64 squares, the text `White to move` or `Black to move`, the status words from R-7 (`ongoing` may be shown as the turn line alone), and a button labeled `New game`. Confirmed by those strings existing in the component source and, after deploy, in the org copy of the bundle.
- Positive: the click handler calls the controller and replaces the FEN only when `applyMove` returns. Confirmed by reading the controller call in the component.
- Failure: a destination that is not in `legalMoves` does not change the FEN.
- Boundary: game state lives in the component. New game or a reload clears it. Both people see the same board. No second Salesforce user is required.
- Open gap: this host cannot open the Lightning page. The visual play-through stays for release-verify. Apex play-through in R-9 is the grading path and is not a substitute for saying the screen was opened.

### R-11 Navigation metadata

Basis: the board must open in the org and be removable later, without other metadata.

Behavior:

- `tabs/SLChess_Board.tab-meta.xml` is a Lightning component tab whose `lwcComponent` is `slChessBoard`.
- The component meta exposes `lightning__Tab` and `lightning__AppPage`.
- `applications/SLChess.app-meta.xml` is standard navigation and contains the tab.
- `flexipages/SLChess_Play.flexipage-meta.xml` places the component on an app page.

Acceptance:

- Positive: those files exist with those names and the tab points at `slChessBoard`. Confirmed by reading the files and by a successful deploy of those names.
- Failure: a custom object, field, permission set, static resource, trigger, profile, label, or flow is out of scope. Confirmed by the file tree under `force-app` containing only classes, the bundle, the tab, the app, and the flexipage.
- Boundary: profiles and permission sets are not edited. Tab visibility without a profile edit is the open gap in R-10.

### R-12 Org tests

Basis: at least 8 Apex test methods in classes named `SLChess...Test`, run in the org, covering fool's mate, scholar's mate, castling, en passant, promotion, stalemate, and standard move counts.

Acceptance:

- Positive: the org run of each test class exits 0 and the human output shows at least 8 passing methods. Each method is named with its case id, `TC_1`, `TC_2`, and so on, as its own word. An Apex method name cannot contain a hyphen, and a longer name such as `TC_1_mate` would hide `TC_1`. The methods cover fool's mate, scholar's mate, castling, en passant, promotion, stalemate, and the standard move counts. Confirmed by `sf apex run test --target-org de --class-names <TestClass> --synchronous --result-format human --code-coverage`, one class at a time.
- Failure: a failing method or a missing topic fails the run.
- Boundary: local inspection of the test class does not replace the org run.

### R-13 Deploy

Basis: deploy to alias `de` and do not stop until the org tests pass.

Acceptance:

- Positive: `sf project deploy start --target-org de` from the repository root succeeds for this project's own metadata. Confirmed by that command's success output.
- Failure: a deploy error stops release until fixed.
- Boundary: every org command uses `--target-org de`. No credential is printed or stored. `sf org display` is not run.

State change: the org gains the `SLChess` Apex classes, `slChessBoard`, the `SLChess_Board` tab, the `SLChess` app, and the `SLChess_Play` flexipage. Before: those names are not part of this project. Recovery: the names are prefixed so a later destructive delete of those members can remove them. This run does not delete them.

## Non-functional requirements

### NFR-1 CPU

Operating condition: one synchronous Apex transaction on alias `de`, whose CPU limit was probed as 10000 ms (`run/scratch/cpu-limit.txt`).

Bound: `legalMoves` on the Kiwipete FEN in R-3 finishes inside that transaction and returns 48 moves. A depth-2 count, defined as the number of legal replies summed over every legal move of the start position, equals 400 and finishes in one transaction. Counting only the 20 root moves does not pass. The 33-ply Opera game in R-9, calling `SLChessController.legalMoves`, `applyMove`, and `status` on every ply, finishes in one transaction.

Verification: Apex tests that perform those three workloads and assert the counts and the final mate. The org test result is the pass. No tighter millisecond budget is invented.

### NFR-2 Metadata and credentials

Bound: deploy only the metadata in R-11 and the Apex classes. Do not change profiles or permission sets. Do not print or store credentials.

Verification: the `force-app` file list, and org commands that use `--target-org de` and not `sf org display`.

### NFR-3 Exclusions

No availability target, no retention period, and no WCAG level are specified by the request. The board is a plain LWC on one screen. No server persistence, so there is no durability target and no log of the position. Those are excluded because the request forbids custom objects and does not ask for them.

## Retired

None.
````

## HOME/architecture.md (whole file)

*S2's anchors. The packet file quotes architecture.md and environment.md whole and the followed R-n entries of spec.md by value; the step block names the sections.*

````markdown
# Architecture

How the chess engine and board are built. Product behavior is in `spec.md`.

## Stack

Apex on API 67.0, deployed to the Developer Edition org alias `de`. The UI is one Lightning web component, `slChessBoard`, with no third-party script. There is no local chess library and nothing is installed. The org's synchronous CPU limit, probed at 10000 ms, is why move generation stays on a 64-square integer board instead of a string scan per attack.

## Structure

- `SLChessEngine` owns the rules. Public static methods only. No instance state.
- `SLChessController` is the Aura-enabled face of those methods for the component and for the grader.
- `SLChessRulesTest` and `SLChessGameTest` own the org assertions. They do not share data.
- `slChessBoard` owns the on-screen game: the current FEN, the selected square, and whose click is next. A reload clears it. The bundle is a Lightning web component ES module. It has no `package.json` and no third-party import. Apex tests do not import it.
- `SLChess_Board` tab, `SLChess` app, and `SLChess_Play` flexipage are the navigation that opens the component. They own no rules.
- After W1 the worktree contains `SLChessEngine` and `SLChessRulesTest` only. `SLChessController`, `SLChessGameTest`, `slChessBoard`, the tab, the app, and the flexipage belong to the next item.

## Conventions

Public Apex, static engine, 4-space indent. Class names start with `SLChess`. The component bundle is `slChessBoard`. Metadata is limited to the classes, that bundle, the tab, the app, and the flexipage. `packageDirectories` is `force-app`. `docs/` stays outside it.

## Interfaces and boundaries

- A position is a FEN string. A move is UCI. `legalMoves` returns a sorted `List<String>`.
- `applyMove` returns the next FEN or throws `SLChessEngine.IllegalMoveException`.
- `status` returns `ongoing`, `check`, `checkmate`, or `stalemate`.
- The controller uses the same three names, `@AuraEnabled public static`. It may throw `AuraHandledException` for a move the board should refuse. The grader does not send those.
- The component calls only the controller. It does not parse rules itself beyond choosing a promotion letter, with queen as the default.
- No custom object, cache, or async job. Two people share one screen and one component instance.

## Real-boundary checks

- Org Apex tests. Where: remote-resident, in alias `de`. Target: the deployed `SLChessRulesTest` and `SLChessGameTest` classes. Framework: `sf apex run test --synchronous`, one class at a time. Access: the CLI is already logged in. Deployment prerequisite: `sf project deploy start --target-org de`. Invoke with the commands in `environment.md`. A local reading of the class is not this check. Status: `SLChessRulesTest` passed at the W1 test stage (exit 0, `Tests Ran` 11). `SLChessGameTest` is planned. Expected red before a class exists: `run/scratch/expected-red-missing-class.txt` exit 1.
- Deploy effect. Where: remote. Target: the same org. The command's success output is the check. Status: W1 saw `sf project deploy start --target-org de` exit 0 for `SLChessEngine` and `SLChessRulesTest`. The release check of the full metadata set stays planned.
- Board play. Where: a browser against the deployed Lightning app. Target: tab `SLChess_Board` or flexipage `SLChess_Play`. First step probed now: open `run/scratch/standin-board.html` in Safari through `osascript` and read the document title. Result: no title returned; the call was terminated after 30 seconds (`run/scratch/browser-standin-probe.txt`). This host has no browser MCP tool, and `sf org open` is not used because it prints a login URL. Access gap: R-10's on-screen play stays unobserved. The default Apex suite does not require a browser. The source-string check is not a substitute for saying the page was opened. Owner: release-verify.
- No service cache, event bus, or permission set is in scope. Live profile visibility of the tab without a profile edit stays the open gap recorded on R-10 and R-11.

## Decisions

### AD-1 Integer board

Choice: represent the position as 64 squares while generating moves, and convert to FEN only at the boundary. Why: a middlegame `legalMoves`, a depth-2 count of 400, and a 33-ply game each have to finish inside one 10000 ms transaction. Alternatives: rescan the FEN string for every attack, which spends CPU on parsing. Status: accepted for implementation.

### AD-2 No stored game

Choice: the controller does not persist the position. Why: the request forbids custom objects, and both players use one screen. Alternatives: a custom object or platform cache. Status: accepted.

### AD-3 Metadata allow-list

Choice: deploy only `SLChess` classes, `slChessBoard`, `SLChess_Board`, `SLChess`, and `SLChess_Play`. Why: the request names those kinds and requires that the work can be removed later by name. Alternatives: a permission set or a profile edit so the tab is visible. Status: accepted. Tab visibility without a profile edit remains an open gap, not a reason to add a permission set.

### AD-4 Queen default

Choice: the board promotes to a queen unless the person picks `r`, `b`, or `n`. Why: the request allows queen as the default and still requires all four letters in the engine. Alternatives: a modal that blocks until a letter is chosen. Status: accepted. The engine still accepts all four letters.

### AD-5 Simple click board

Choice: the board is an 8x8 click surface. A person clicks a piece, then a destination. Text shows whose turn it is and the status. An illegal destination is refused. A pawn promotes to a queen unless the person picks `r`, `b`, or `n`. New game restores the start FEN. There is no drag, animation, or sound. Why: the request asks for a simple board two people play on one screen, and the grader plays through Apex. Alternatives: drag-and-drop and animated moves. Status: accepted.

## Superseded

None.
````

## HOME/environment.md (whole file)

*S2's anchors. The packet file quotes architecture.md and environment.md whole and the followed R-n entries of spec.md by value; the step block names the sections.*

````markdown
# Environment

Facts below are marked binding (required by the request or by an observed runtime), observed (read from this checkout or the org), or proposal (a default this run will use until a later stage replaces it).

## Targets and runtimes

- Binding. Product edits happen in the isolated worktree. The Salesforce DX root is that worktree root (`sfdx-project.json` and `force-app/`), which is the repository root. The original checkout stays at the empty baseline until the guarded workspace return at release or handoff. Source: intake result and `git log` in the worktree (`6051fc5`).
- Observed. There is no Git remote, no CI config, and no deploy hook. Returning the worktree to the original checkout does not deploy and does not have to precede an org check. The consumer path is an explicit `sf project deploy start --target-org de` of this project's own metadata, then synchronous Apex tests. Uncertainty: none found for a hidden CI route, because no remote or workflow files exist (`find` of the worktree, baseline suite output).
- Binding. Delivery target is the Developer Edition org selected by CLI alias `de`. Development, test, and delivery share that one org. There is no separate sandbox ladder. Do not treat the org as a place for unrelated metadata changes.
- Observed. Salesforce CLI `@salesforce/cli/2.154.4` on darwin-arm64, node `v25.9.0` (`run/scratch/sf-version.txt`).
- Observed. Anonymous Apex on alias `de` compiled and executed, and `Limits.getLimitCpuTime()` printed `10000` (`run/scratch/cpu-limit.txt`). That is the synchronous CPU budget the engine must stay inside.
- Observed. The CLI's template constant `DEFAULT_API_VERSION` is `67.0` in `@salesforce/templates/lib/utils/constants.js` of the installed CLI `2.154.4`. Use `sourceApiVersion` `67.0`. Revalidate at the first deploy if the org rejects it.

## Commands

- Binding org deploy: `sf project deploy start --target-org de` from the repository root. No other target flag. If `--wait` is passed it must be at least 5; omitting it is allowed. The `sf` on PATH is a wrapper that deploys only Apex classes, tabs, apps, and flexipages named `SLChess*`, plus the `slChess*` LWC bundle, from the project's package directory (`sf_guard.py` deploy scope). `packageDirectories` must be `force-app` so `docs/` is not deployed. Do not pass `--metadata-dir`, destructive-change flags, or a manifest that names other types.
- Binding org tests, one class at a time: `sf apex run test --target-org de --class-names <TestClass> --synchronous --result-format human --code-coverage`.
- Binding W1 focused proof: `sh tests/rules_gate.sh` from the repository root. The human command above stays the regression command, and it is the command the script runs after a successful deploy. The script exists because that human reporter prints `Pass`, which is not a pass mark, and because `sf apex run test` does not deploy the working tree, so a local change to `SLChessEngine.cls` cannot fail it. Contract for `tests/rules_gate.sh`: if `force-app/main/default/classes/SLChessEngine.cls` is missing, print `cannot load force-app/main/default/classes/SLChessEngine.cls` and exit 1 without calling `sf`. Otherwise run `sf project deploy start --target-org de`; on a non-zero status print that same line and exit 1 without running tests, so a failed deploy cannot leave the org's previous class looking green. On success, run `sf apex run test --target-org de --class-names SLChessRulesTest --synchronous --result-format human --code-coverage`, and on each output line replace a whitespace-separated field that is exactly `Pass` with `PASSED` and a field that is exactly `Fail` with `FAILED`. The human table prints the runtime after the outcome, so `Pass` is not the last field (`SLChessRulesTest.TC_1   Pass              80` in the W1 red-check record). Then exit with the test command's status. Do not add `force-app/main/default/.gitkeep`: the deploy wrapper rejects that file.
- Observed safe identity read: `sf org list` (human format). Do not run `sf org display`.
- Observed runtime probe already used: `sf apex run --target-org de --file <scratch apex>`.
- No linter, formatter, type checker, or local test runner is configured. Apex is compiled by the org deploy and test commands. ShipLoop's script lint may still run on changed files; it is not a product command.

Planned at prepare, and kept here as that as-of record. Each command below is the suite entry. A probe of the absent class `SLChessEngineTest` exited 1 (`run/scratch/expected-red-missing-class.txt`). At prepare, the same command for `SLChessRulesTest` and for `SLChessGameTest` also exited 1, each with `INVALID_INPUT` because the class does not exist (`run/scratch/prepare-rules-runner.txt`, `run/scratch/prepare-game-runner.txt`). The runner starts. At prepare the classes were absent, so that red result was expected. `sfdx-project.json` and `force-app/` were absent then (`run/scratch/prepare-local.txt`). `sf` and `rg` are on PATH. No product linter is configured, so no lint runner was started. Deploy was not run at prepare.

Observed at the W1 test stage, after that baseline. `sfdx-project.json` and `force-app/` are present. `sh tests/rules_gate.sh` exited 0. It deployed this tree, then printed `SLChessRulesTest.TC_1` through `TC_11` with the field `PASSED`, `Tests Ran` 11, and `Outcome Passed` (`run/scratch/w1-gate.txt`). The regression command for `SLChessRulesTest` exited 0 with `Tests Ran` 11 and `Outcome Passed`; its human outcome field is still `Pass` (`run/scratch/w1-regression.txt`). `sf project deploy start --target-org de` exited 0 and listed `SLChessEngine` and `SLChessRulesTest` (`run/scratch/w1-deploy-check.txt`). `SLChessGameTest`, the board, the tab, the app, and the flexipage are outside this observation. System-test and release still run the commands below for their own stages. Verify reran the gate, the regression, the project-file check, the engine source search, and `sf project deploy start --target-org de`. Each exited 0. The gate and the regression each showed `Tests Ran` 11.

Full suite, one class at a time. Inclusion: every `SLChess...Test` method. Cost: one synchronous org round trip per class. Prerequisite: a successful deploy of that class. The rules class prints `TC_1` through `TC_11`. The game class prints `TC_12` through `TC_14`.

```sh
sf apex run test --target-org de --class-names SLChessRulesTest --synchronous --result-format human --code-coverage
```

```sh
sf apex run test --target-org de --class-names SLChessGameTest --synchronous --result-format human --code-coverage
```

Smoke is the rules class only. It does not cover the Opera game or the depth-2 count.

```sh
sf apex run test --target-org de --class-names SLChessRulesTest --synchronous --result-format human --code-coverage
```

Focused source checks, local, no org. Inclusion: project shape, metadata names, and the board strings. Cost: under a second. They do not prove org behavior.

```sh
test -f sfdx-project.json && test -d force-app
```

```sh
rg -n "lwcComponent>slChessBoard" force-app && rg -n "lightning__Tab" force-app && rg -n "lightning__AppPage" force-app && rg -n "SLChess_Board" force-app && rg -n "SLChess_Play" force-app
```

```sh
rg -n "White to move" force-app/main/default/lwc/slChessBoard && rg -n "Black to move" force-app/main/default/lwc/slChessBoard && rg -n "New game" force-app/main/default/lwc/slChessBoard
```

```sh
rg -n "legalMoves" force-app/main/default/lwc/slChessBoard && rg -n "applyMove" force-app/main/default/lwc/slChessBoard && rg -n "status" force-app/main/default/lwc/slChessBoard
```

```sh
rg -n -i "queen" force-app/main/default/lwc/slChessBoard
```

Deploy. Inclusion: this project's metadata. Prerequisite: `packageDirectories` is `force-app`. W1 saw this command exit 0 for `SLChessEngine` and `SLChessRulesTest`. Release still runs it when the rest of this project's metadata is in the tree.

```sh
sf project deploy start --target-org de
```

## Skills

- Observed. The repository has no `SHIPLOOP.md`, `README.md`, `AGENTS.md`, or `.grok` skill links (`ls` during discovery). No product skill fits this chess engine. Do not edit skill packages. Revalidation: if a later commit adds a repository skill index, read it before adding a skill at carry-forward.

## Harnesses and suites

- Observed baseline, unchanged checkout, missing coverage. Command: `find . -type f -not -path './.git/*'` from the worktree. Exit 0. Output lists only `./.git` (`run/scratch/baseline-suite.txt`). No Apex tests, no `package.json`, no sfdx project. This is missing coverage, not a pass. Prerequisite before feature checks: create the Salesforce DX project at the worktree root. Evidence needed: `sfdx-project.json` with `packageDirectories` `force-app`. That paragraph is the discovery as-of record. W1 later added `sfdx-project.json`, `force-app/` with `SLChessEngine` and `SLChessRulesTest`, and `tests/rules_gate.sh`.
- Selected harness: Salesforce Apex tests run in alias `de` by `sf apex run test --synchronous`. Role: the only runner that compiles and executes the engine. Fit: the grader plays games in one anonymous Apex transaction, and each test method is its own transaction with the probed 10000 ms CPU limit. Availability: the CLI is logged in; a missing class named `SLChessEngineTest` is rejected (`run/scratch/expected-red-missing-class.txt`, exit 1). That rejection is the expected-RED control. It is not a product failure. Prerequisites: `--target-org de` on every org command, no credentials printed. Setup: none beyond the existing login. Isolation: no custom objects and no static game state, so methods do not share rows. Fixture lifecycle: each method builds its FEN in memory and asserts. Runner and coverage: the human result format with `--code-coverage`. Revalidation: if a test method exceeds the CPU limit, split that method, not the assertion. There is no local Apex runner and no python-chess install. Inspection of source is a separate check and is not a retained org assertion.
- `SLChessRulesTest` holds `TC_1` through `TC_11`. Those eleven methods passed in alias `de` at the W1 test stage: the gate and the regression command each exited 0 with `Tests Ran` 11. `SLChessGameTest` is planned to hold `TC_12` through `TC_14` (controller games and the depth-2 count). At least eight methods are required; fourteen are planned so each spec fixture has a method.
- Planned map. Surface is the Apex test method unless noted. Due means the stage that must see a pass. W1 already observed `TC_1` through `TC_11` in the org; the system-test column for those rows is still due. `TC_12` onward are unobserved.

| Id | Proves | Surface | Due | Negative and fixture |
| --- | --- | --- | --- | --- |
| TC_1 | R-2 start FEN, R-7 ongoing | `SLChessRulesTest.TC_1` | test, then org at system-test | any other start string fails |
| TC_2 | R-3 start has 20 moves | `SLChessRulesTest.TC_2` | test, then org | count other than 20 fails |
| TC_3 | R-3 Kiwipete 48, includes `e1g1` and `e1c1`; NFR-1 middlegame `legalMoves` | `SLChessRulesTest.TC_3` | test, then org | 48 is the pass; timing is the transaction finishing |
| TC_4 | R-3 counts 14 and 44, Apex sort, `e1c1` before `e1g1` | `SLChessRulesTest.TC_4` | test, then org | an unsorted list fails |
| TC_5 | R-3 pin: `e2d2` absent, `e2e3` present | `SLChessRulesTest.TC_5` | test, then org | the pinned capture being legal fails |
| TC_6 | R-4, every `applyMove` result string in that requirement | `SLChessRulesTest.TC_6` | test, then org | any differing FEN fails |
| TC_7 | R-5 `e2e5` throws `IllegalMoveException`; R-6 `e5d6` result | `SLChessRulesTest.TC_7` | test, then org | a returned FEN for `e2e5` fails |
| TC_8 | R-7 fool's mate FEN and `checkmate` | `SLChessRulesTest.TC_8` | test, then org | a non-mate status fails |
| TC_9 | R-7 scholar's mate FEN and `checkmate` | `SLChessRulesTest.TC_9` | test, then org | a non-mate status fails |
| TC_10 | R-7 stalemate FEN and the check sequence `e2e4 f7f6 d1h5` | `SLChessRulesTest.TC_10` | test, then org | empty legal moves on the check position fails |
| TC_11 | R-8 castle bans, both-side castle results, four promotion results | `SLChessRulesTest.TC_11` | test, then org | a missing letter or a castle through f3 fails |
| TC_12 | R-9 fool's mate and scholar's mate through `SLChessController` | `SLChessGameTest.TC_12` | test, then org | a controller FEN that differs from the engine fails |
| TC_13 | R-9 and NFR-1 Opera game, 33 plies, final `checkmate`, one transaction | `SLChessGameTest.TC_13` | test, then org | a ply absent from `legalMoves` fails |
| TC_14 | NFR-1 depth-2 sum is 400, not 20 | `SLChessGameTest.TC_14` | test, then org | counting only the root moves fails |
| source | R-1, R-10 strings, R-11 file names, NFR-2 file tree, and the component source naming `legalMoves` and `applyMove` | local `rg` and `test` commands | verify | a nested project, a forbidden metadata type, or a component that never calls `applyMove` fails. Call order and a refused click stay with the board case |
| deploy | R-13, NFR-2 | `sf project deploy start --target-org de` | release | a deploy error stops release |
| board | R-10 play on the Lightning page | browser, opt-in, not in the default suite | release-verify | see the access gap in architecture.md |

- Owner of the Apex cases is the test class. Owner of the full-project deploy is the release stage. Owner of the board case is release-verify. Prerequisite for every org case is the deploy. W1 marked `TC_1` through `TC_11` passed in the org. `TC_12` through `TC_14`, the release deploy of the remaining metadata, and the board case stay open.
- R-12's rules-class command was observed at W1: `SLChessRulesTest` exited 0 with 11 methods. The game-class command, and the pair as a system-test pass, stay planned. The pass bar is at least eight passing methods whose names are `TC_1` and the following ids. NFR-3 has no product check: the request excludes an availability target, a retention period, and a WCAG level. The file-tree check for R-11 is what shows no custom object was added.

## ID convention

- Requirement ids `R-<n>` and `NFR-<n>` live in `docs/shiploop/spec.md`. Decision ids `AD-<n>` live in `docs/shiploop/architecture.md`.
- Apex test method names are the case ids `TC_1` through `TC_14`. The human test output must show each id as its own word. A hyphen is illegal in an Apex method name, and `TC_1_mate` would not show `TC_1` as its own word. `SLChessRulesTest` has taken `TC_1` through `TC_11`. `TC_12` through `TC_14` stay free until `SLChessGameTest` exists.

## Access and accounts

- Observed. `sf org list` exit 0 shows exactly one connected org with alias `de`: username `jim.wiese.affa2a21369f@agentforce.com`, org id `00Daj000018BzO3EAK`, status Connected, marked default org (`run/scratch/sf-org-list.txt`). Q1 from intake is answered: the alias is one org. No session material was retained.
- Binding. The request grants this run a non-destructive deploy of this project's own metadata and the synchronous test command. Scope is this run only. Operator is the already authenticated CLI user. Deployed runtime is that org. End users of the board are two people on one screen; the org does not identify them separately.
- Observed. This session has no browser MCP tools. The PATH wrapper also denies `sf org open` because that command prints a login URL. Q2 stays with release-verify: this host cannot open the Lightning UI. It does not block the engine or the Apex grader. No further access grant is required for deploy or Apex tests; the alias is already connected.
- Observed org shape: `OrganizationType` Developer Edition, `InstanceName` USA838, `IsSandbox` false (`run/scratch/org-identity-query.txt`). One org, not a sandbox ladder.

## Platform facts

- Observed at discovery. Empty repository. Only commit `6051fc5` "Empty baseline for the first ShipLoop run" on branch `shiploop/run-808ce1b64b18b2b7`. No house style, no canonical Apex sample, no reusable library. House style is therefore a proposal: public Apex classes, static engine methods, 4-space indent, names prefixed `SLChess` except the component bundle `slChessBoard`, metadata limited to classes, the LWC, `tabs/SLChess_Board.tab-meta.xml`, `applications/SLChess.app-meta.xml`, and optional `flexipages/SLChess_Play.flexipage-meta.xml`. W1 later added `SLChessEngine` and `SLChessRulesTest` in that style. The discovery commit remains the as-of baseline.
- Binding. Positions are FEN strings. Moves are UCI, sorted alphabetically. En-passant target is set on every double pawn push. Castling UCI is the king move `e1g1`, `e1c1`, `e8g8`, `e8c8`. Status strings are `ongoing`, `check`, `checkmate`, `stalemate`.
- Binding. Controller methods are `@AuraEnabled public static` so anonymous Apex and the LWC can call them. Illegal controller moves may throw `AuraHandledException`. Illegal engine moves throw `SLChessEngine.IllegalMoveException`.
- Observed platform limit: synchronous CPU 10000 ms. The engine must answer middlegame `legalMoves`, a depth-2 count, and a game of about 35 plies inside one transaction each.
- No custom objects. Game state for the board is component state only. No cache, queue, or async worker is required.
````

