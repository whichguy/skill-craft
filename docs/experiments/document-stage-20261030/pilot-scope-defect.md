# L3 evidence: the document loop scope in the 2026-10-29 per-step pilot (Codex gpt-6.1-terra xhigh, ask-agent)

Source run: ~/e2e-runs/20261029/pilot-terra-ask-agent-32f436 (outside the repository; excerpted here).

## Loop contract context.scope (run/loops/nav-0fcdd8adcbe14d8b9dc0b1c86762eb32-contract.json)

Workspace ~/e2e-runs/20261029/pilot-terra-ask-agent-32f436/.shiploop-runs/seed/worktree. Work item W1: only the paths its accepted step plan declares, plus docs/shiploop/ where this stage writes it. Preserve every other change.

## Loop contract context.authority

Edit only in scope. Do not push, install or download anything, edit a recorded command or change a check's expected result. ShipLoop callbacks belong to the parent; the loop never calls them. Commit nothing: ShipLoop commits the change when the document stage and its review are accepted.

## The stage's own notes, line 2 (run/notes/nav-0fcdd8adcbe14d8b9dc0b1c86762eb32.md)

README remains unchanged because this loop's scope is limited to step-plan paths and docs/shiploop/. Its missing link to the maintained records reference is a carry-forward item for the owner to resolve within an authorized wider scope. Parser documentation did not need changes: S2 changes only selection, and its existing example and focused tests passed. No remote, deployment, operator or separate error guide applies to these synchronous local helpers; errors are documented in records.md. No generated product output was created.

## The step commits (worktree git log --stat)

```
ae8852e docs(shiploop): record in-this-node-js-project-add-f098bc knowledge after carry-forward

 docs/shiploop/architecture.md |  2 ++
 docs/shiploop/environment.md  | 18 ++++++++++++++++++
 docs/shiploop/spec.md         |  2 ++
 3 files changed, 22 insertions(+)
9207e5b Validate selector arguments before reading record fields

 docs/shiploop/records.md |  2 +-
 src/records.js           | 16 +++++++++++++---
 test/records.test.js     | 17 +++++++++++++++++
 3 files changed, 31 insertions(+), 4 deletions(-)
d70c709 feat(W1/S2): Select matching records in order with strict equality

 docs/shiploop/architecture.md |  2 +-
 docs/shiploop/environment.md  |  4 ++--
 docs/shiploop/records.md      | 14 ++++++++++++-
 docs/shiploop/spec.md         |  2 ++
 src/records.js                | 16 ++++++++++++++-
 test/records.test.js          | 46 ++++++++++++++++++++++++++++++++++++++++++-
 6 files changed, 78 insertions(+), 6 deletions(-)
8b503a1 feat(W1/S1): Parse line-oriented records with validation and line-numbered errors

 docs/shiploop/architecture.md |  4 +++
 docs/shiploop/environment.md  |  8 +++++-
 docs/shiploop/records.md      | 15 +++++++++++
 docs/shiploop/spec.md         |  2 ++
 src/records.js                | 37 ++++++++++++++++++++++++++
 test/records.test.js          | 60 +++++++++++++++++++++++++++++++++++++++++++
 6 files changed, 125 insertions(+), 1 deletion(-)
```

## Packet duty line the model was given (run/packets/nav-0fcdd8adcbe14d8b9dc0b1c86762eb32.md)

46:2. **Observe and write.** Run each changed behaviour, then update the README, API, user, operator, error and design
