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

Reopen the namespace and data entries in HOME/architecture.md ## Structure and each touched environment's tree. Per file,
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
human-facing UI defaults to ambitious and highly interactive: direct manipulation, inline editing, live preview, keyboard
paths, animated transitions; give the reason for any scaled back); the UI decisions this step owns (UI planning ownership
guide); locators of sources and checks.

Interaction design guide:
[actors, channels and state ownership](behavioral-requirements.md#actors-channels-and-state-ownership).
