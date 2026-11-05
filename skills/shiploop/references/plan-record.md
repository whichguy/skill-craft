# Plan record: what a step plan records when the item touches a topic

Step-plan duty 9 lists what every plan record holds. This guide holds the topics a plan records only when the item
touches them. The record goes in the item's `context` or the summary, and it is supporting reference: each step's task and
criteria stay its only directive. Open only the section whose topic the item touches; an item that touches none records
nothing from this guide.

## Topics the item touches

| The item | Record |
|---|---|
| adds or moves code or stored data | [code or stored data added or moved](#code-or-stored-data-added-or-moved) |
| replays a pinned value (fixed dice, seed data) in a check | [pinned values a check replays](#pinned-values-a-check-replays) |
| changes interactions, UI or service state | [interactions, UI or service state](#interactions-ui-or-service-state) |

## Code or stored data added or moved

Reopen the namespace and data entries in KNOWLEDGE/architecture.md ## Structure and each touched environment's tree. Per file,
module and public symbol: environment, home namespace, visibility, collision check (import or load test, deploy
validation, or name search). Per stored field, key, table or payload: owning environment, migration (unneeded, earlier
step, this step, deploy obligation), round-trip check. Reason for a changed placement or schema (Namespace and placement
guidance, Schema and storage guidance, State and data assessment).

## Pinned values a check replays

Each pinned value a check replays (fixed dice, seed data), labelled a source-check fixture apart from the runtime control;
confirm an external oracle (golden file, fixture, snapshot) agrees with the task.

## Interactions, UI or service state

Interactions, UI or service state changing: a Design basis paragraph or exact section links, rechecking the Interaction
design guide's matching subsections and, for services, Service discovery guidance; copy no prior plan. Give baseline and
delta; actors, events, connections and state owner; planned recovery checks; for UI the component, interaction and skin
premises, design guidance identity and version or digest (or named fallback), and the rich interactions planned (a
human-facing UI takes the ambition the request states, and with none stated defaults to ambitious and highly interactive:
direct manipulation, inline editing, live preview, keyboard paths, animated transitions; give the reason for any scaled
back); the UI decisions this step owns (UI planning ownership guide); locators of sources and checks.

Interaction design guide:
[actors, channels and state ownership](behavioral-requirements.md#actors-channels-and-state-ownership).

### Concrete UI direction

At first UI planning, record or reuse the accepted art direction and task
hierarchy alongside its design system, tokens, components and theme in an
AD-<n> under KNOWLEDGE/architecture.md ## Decisions, with named sections for
the choices a step can select. Record the decision before writing the criteria
that cite it. Reuse an AD only when it already records the concrete choices this
step must select; otherwise complete its applicable named sections while preserving
accepted premises. A preliminary direction alone is not those concrete choices.
For a new interface or an authorized visual
change, name the tone; focal activity and supporting
hierarchy; typography and spacing; semantic palette and surfaces; shape and
depth; and one useful detail that gives the product character. Include concrete
tokens and composition choices that a fresh implementer can reproduce, including
where characteristic surfaces appear and their emphasis relative to the primary
activity. Distinguish accent fills from text on tinted surfaces; observe the
actual text and focus treatments through the existing rendered checks. For an
existing product, preserve its accepted identity and components and record only
the authorized delta; missing design documents do not imply a new interface.

Each step that adds or changes visible UI selects its applicable, confirmable
visual choices in a visual criterion, including later screens. The criterion's
own text cites the AD ID and exact knowledge-file and named section, and states a few observable
relationships and necessary anchor values. Also retain the AD in the existing
`follows` and context. Keep criteria concise: do not copy the complete token
table from the AD into each criterion. A fresh
implementer can locate the full decision when its optional packet excerpt is
absent. Only the
choices the step's criteria select are implementation work; other AD choices
remain context and do not expand the step. Existing test-spec and acceptance rows observe
the rendered interface, including the primary activity and important states,
at the applicable widths and themes. Token declarations or an adjective such
as modern are not rendered evidence. Functional counts or interactions do not
confirm these visual choices. If no command can confirm a visual condition,
retain its requirement and selected AD choices in the summary's existing open-item
route, naming who can confirm it and how. Do not claim it verified.

Let the user's task determine composition: for example, a game's board, pieces and turn
state; a chat application's readable message groups, threads, artifacts and
reachable composer; a work application's content and next action. Use realistic
content to resolve density and mobile composition. The requested look guides
these choices while existing identity, platform conventions, accessibility and
scope remain authoritative. For a new graphical UI, fill unspecified choices from
the [light expressive starting point](platforms/ui.md#light-expressive-starting-point);
explicit visual constraints, established identity and platform conventions take precedence.
A small change to
an existing UI records its preserved identity and authorized delta; it does
not create a new concept or reopen an accepted UI AD without a reason from
the request or current product evidence.
