# Survey guide

Survey is its own durable action before research, behavior, and spec. Its output
is environment.md: a concise prose brief followed by exactly one H2 named machine
and one fenced JSON object. That fence is structured content within
Markdown-authoritative state, not a JSON sidecar.

## Minimal valid local greenfield machine record

Do not guess types. This is a complete, valid machine object for a local-only
greenfield increment with no external reader, writer, UI, or handles. The prose
brief above it is required too.

~~~~markdown
Local-only greenfield work. No external writer, account, or UI is in scope.

## machine

~~~json
{
  "kind": "greenfield",
  "augment": false,
  "references": [],
  "tools": [],
  "mcp": [],
  "mcp_considered": "none(no external reader is in scope)",
  "handles": [],
  "initiation": "none",
  "ui": false,
  "ui_craft": "none(no user-facing surface)",
  "exclusive": []
}
~~~
~~~~

Do not turn booleans into quoted strings, use null for required lists, or omit
exclusive. The validator distinguishes a missing field from an explicit empty
list.
Omit optional layout/routing objects when there is no destination contract;
empty objects are not a valid placeholder for their required typed fields.

## Conditional typed fields

- Brownfield requires kind brownfield, augment true, and a nonempty references
  list of objects with nonempty path and why. Greenfield requires augment false.
- Each handle is an object with nonempty source and need, resolve equal to
  list, inspect, ask, or create, and string value. Inspect requires a nonempty
  value except credential inspection, whose value must be empty. List, ask,
  and create have empty values. List/ask block plan; initiation needed requires
  at least one create handle, while initiation none/done forbids create.
- Each nonempty exclusive row has nonempty artifact and use, plus dont_use as a
  string list. Use must appear in tools or mcp, must not appear in its own
  dont_use, and all rows designate the same writer. Nonempty exclusive also
  requires nonempty references and both layout and routing.
- Layout has nonempty string lists reserved and product. Routing has nonempty
  strings user_entrypoint, confirmation, and source; reserved_routes is a
  nonempty string list; routing source exactly matches a references path.
- UI is a Boolean. UI false requires ui_craft in the form none(reason). UI true
  requires a non-none ui_craft token and a references path containing that
  token. Its later DAG must include a design-producing seed that feeds another
  seed.

## Inventory before planning

Record evidence for:

- kind: greenfield or brownfield, and augment only when adding to the existing
  brownfield product tree;
- relevant repository files, product docs, ADRs, official documentation, skill
  references, and MCP resource URIs; every reference has a constraint-focused
  why;
- tools and MCPs that are actually in scope for this increment, plus one
  read-capable mcp_considered token; list unauthenticated or deferred systems
  in prose, not as usable capability;
- non-secret handles and initiation facts. Record an expected account role and
  a documented non-mutating probe, never an account address, credential value,
  or secret ID. An observation may say when it was observed, but that does not
  make availability a timeless fact; a user decision or failed safe probe is a
  reason to pause, not to call it established;
- UI/CLI/operator surfaces and the design conventions they must follow;
- client–service invocation protocol when a client will call a service;
- existing README.md and, if it exists, root AGENTS.md as references only.
  Product docs are later DAG work when needed, never the survey's mutation.

Research turns these surveyed constraints into a bounded question/source
candidate. It uses the paired `research.md` and `research-evidence.md` records
under the research loop, not an untyped extension of `environment.md`. See the
[research draft schema](research-loop.md#draft) and
[evidence/freshness boundary](research-loop.md#evidence-and-freshness). Survey
does not require a research provider or new tool, and its safe observations never
authorize externally mutating probes.

## Destination writers

For each destination artifact, designate one writer:

~~~json
{
  "artifact": "<destination artifact>",
  "use": "<designated writer>",
  "dont_use": ["<overlapping mutation tool>"]
}
~~~

dont_use lists competing mutation mechanisms, not a fallback ladder. The
designated writer must be in the surveyed usable tools/MCP set. If it fails,
pause and obtain direction; do not switch writers silently.

Research and preserve writer constraints that later agents would otherwise
guess:

1. Read/create/mutate/validate/publish responsibilities and anti-patterns.
2. Required library, runtime, module, wrapper, registration, and product-facing
   call mechanics. Reuse existing patterns before introducing another stack.
   These are destination structure, not the client invocation protocol.
3. Reserved versus product paths. Writer-owned/bootstrap/overwrite-prone files
   are reserved; product code never lands there.
4. Writer syntax lint/validation and live list/status/preflight identity
   oracle. Destination-mandated syntax wins over generic format rewrites.
5. User entrypoint, reserved routes, routing-level confirmation, bound
   action probes, and the separate live acceptance path.
6. Safe setup/status probes, configuration files that must remain tracked, and
   applicable enablement prerequisites. Never store credentials or secret IDs.

When no destination writer exists, record that plainly. Do not invent a
platform, a client stack, a linter, or a deployment process.

## Client–service invocation

When any client will call a service — an HTML page, CLI, SDK, another
process, or operator surface — consider both systems' invocation protocol
before authoring any communication between them.

This is distinct from routing (how a user reaches the surface) and from
writer/runtime mechanics (how files land and how internal modules are
structured). Destination call mechanics are not the client call path.

Record, from primary documentation and existing destination patterns:

1. **Service-visible operations.** What the service actually exposes at the
   invocation boundary: names, arity, wrappers, required envelopes. That set
   is defined by the platform's invocation rules (for example only parse-time
   top-level entrypoints, a single dispatcher, or a generated stub). Internal
   module exports, later global assignments, and helpers that are convenient
   to unit-test are not visible operations unless the platform documents them
   as callable.
2. **Client call conventions.** What the client side needs in order to use
   those operations. For an HTML-style client, that is the page-side
   interaction: required includes or bootstrap, the documented stub or
   library, the exact call shape, argument serialization, success/failure
   handling, and the return/error envelope the page must unwrap. Define those
   conventions as the client interaction; do not invent a parallel RPC that
   looks like a local function.
3. **Order.** Freeze this contract in survey/research before spec. Sequence
   planning needs a producer for it before any step that writes a call site.
   Implementation tests must exercise the real client path, not only a
   substitute exec of internal functions.

If no client calls a service, record that plainly. A missing invocation
contract is missing authority, not an implementation detail.

## Human-facing surfaces

When UI is true, cite the applicable UI craft guidance and record the existing
destination conventions. Planning creates an early design-producing step before
surface implementation. Its output covers distinctive identity, layout, and
interaction behavior including useful feedback and empty/error/success states.
Later steps consume that output rather than substituting a generic template.
When the surface calls a service, HTML/page-side call conventions belong in
Client–service invocation, not as a later implementation guess.

## Freeze discipline

Research extends the survey evidence before behavior/spec. Once the sequence
stage freezes `environment.md`, `spec.md`, and the DAG, do not hand-edit them to
resolve new learning. Before any execution receipt, `revisit --to research`
preserves this survey while archiving research and downstream planning proof; a
changed survey fact uses `revisit --to survey` instead. The execution
`carry-forward` checkpoint may record a current non-secret overlay, but it is
not authority to rebase this approved historical survey contract. `context
environment` presents the unchanged baseline alongside the labeled overlay.
Pause for missing authority or use the mandatory post-inner obligation mapping
and a validated pending-only correction. Never put secrets, live delivery URLs,
session hashes, raw logs, or generic ShipLoop proposals in product docs. See
[Carry-forward checkpoint](carry-forward.md) and
[later research discoveries](research-loop.md#later-discoveries).
