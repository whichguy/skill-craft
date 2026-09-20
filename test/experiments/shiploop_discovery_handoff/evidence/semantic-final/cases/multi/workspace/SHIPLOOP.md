# Project knowledge

Read current source and docs/environment.md, then retain the discovery decision and exact evidence locators in this index.

## 2026-09-20 — Remote document-generation discovery

- [DISCOVERY.md — scope, observations, conditional design, and gates](DISCOVERY.md#remote-document-generation-discovery) is the current decision note. It records the fresh target identities, source and fixture-receipt locators, and the boundary between queued acceptance and verified completion.
- [BASELINE.txt — unchanged fixture baseline](BASELINE.txt) records the required narrow test run and its coverage limit.
- Revalidate before planning or implementation: document-worker creation permission in `folder-shared`; `ReviewState` uniqueness/atomicity/migration authority; processor, recovery, and lost-acknowledgement ownership; conditional-write/read-back behavior; and the consumer result contract. The historical `tenant-blue`/writer-enabled note is stale relative to the fresh synthetic observations cited in the decision note.
