# Intake Improve review 1

## Candidate and scope

- Candidate: `<study>/existing/run/notes/intake.md`, with the pending parent producer result at `<study>/existing/run/inbox/nav-1e95ddc90bb44faa934825331a4182dc.md`.
- Product evidence baseline: clean `main` at `8f318f0adb98cb3a6e9c6419e57e48ef96ef2a8e`; no product source, test, dependency, configuration, or durable documentation edits are authorized. This review's writes are limited to the run note and this child review directory.
- Requirements and evidence reopened: `product/README.md`, `product/SHIPLOOP.md`, `product/docs/design.md`, `product/docs/platform.md`, `product/docs/api.md`, `product/host-observation.json`, `product/app.js`, and the packet-selected frontend design card. The product requirement sources remain repository-owned; the design card is a packet-selected planning input only.

## History and independent review

- Read the reachable history in `history-review-one.txt`: one fixture commit, `8f318f0adb98cb3a6e9c6419e57e48ef96ef2a8e Fixture: freeze accepted request and controlled target facts`. It provides context only and does not authorize a change.
- Fresh read-only independent reviewer found two accuracy issues: the design card needed an explicit non-authoritative label, and “required” baseline wording needed its ShipLoop basis and a more careful no-current-evidence statement. The reviewer found no privacy, capability-gap, or live-claim defect. Its returned review is retained in this record rather than treated as authority.

## Findings, plan, and applied correction

1. **I-REV-01 — authority wording:** `intake.md` could be read as making an external card controlling. The current parent packet explicitly selected the card, but accepted user/repository sources must remain controlling. Correction: label it packet-selected and non-binding.
2. **I-REV-02 — discovery-check wording:** `intake.md` called the smoke/probe “required” without naming its process source and stated nonexecution too broadly. Correction: state that no current-run evidence records either command and attribute their discovery candidacy to the selected initial-baseline guidance.
3. No change was warranted to the core capability finding: the controlled target observation still says client persistence is unavailable and the draft API is false; the API still limits export update detection to polling/foreground reconciliation with notification hints.

The two run-note corrections above were applied. They change the accuracy of authority and evidence boundaries, so this is a **non-trivial** review iteration even though there is no product behavior change.

## Checks and limits

- `source-hash-review-one.txt`: all ten frozen product source hashes from the intake inventory verified `OK`.
- `tracked-status-review-one.txt` and `tracked-diff-review-one.txt`: no tracked product modifications or diff. Child runtime metadata is excluded from the product candidate.
- `locator-review-one.txt`: current source locators still expose the accepted journeys, static-target limits, unavailable persistent storage/draft API, and export polling/foreground facts cited by intake.
- `packet-review-one.json`: the exact runtime start packet parses as JSON.
- No `node --check app.js` or environment probe was run because discovery owns the initial product baseline. These review checks establish artifact consistency only; they do not establish product behavior or a live target.

## Continuation

Run two additional distinct reviews after re-reading the corrected note and current evidence. Each must independently confirm that the two corrections are adequate and that no material intake-record issue remains before it can count as trivial; the runtime's two-consecutive-trivial gate was reset by this non-trivial cycle.
