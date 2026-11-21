# Referee rulings for round 1

Git cannot resolve `22f8405` in this checkout. The oldest available snapshot, `14feaa0`, carries a 1.4.0 package version but already contains due-time code. Its `test/` tree supplies the incoming test inventory used for the discovery and maintainer checks.

| Dispute | Ruling | Reason |
| --- | --- | --- |
| C-22 | test stands | The observable calls for the 1.4.0 status codes and bodies on equivalent state. Sending the same requests to both releases tests that contract. The missing archive blocks the comparison. |
| C-67 | test stands | The observable explicitly requires unmodified 1.4.0 to start directly on the file written by the new release. Starting that release on the saved file is the required check. |
| C-68 | test stands | The observable requires paging the rolled-back file on 1.4.0, including tickets created by the new release. The test compares the IDs and legacy fields returned by that reader. |
| C-70 | test stands | The observable requires creating a ticket through the rolled-back service and checking the ID against the saved next number. The test exercises allocation on that service. |
| C-124 | test stands | The observable specifies a cursor returned by 1.4.0 and reused on the same query. The test obtains the token and expected continuation from that release. |
| C-138 | test corrected | The observable concerns the values and sequence numbers of earlier audit entries. A seeded version 1 file supplies those entries and lets the test verify them after preparation, a new append, and restart. |
| C-217 | test corrected | The observable describes the existing list columns, ticket details, and history. The test now checks the full expected output for the fixture in each disabled mode using the incoming formatter's legacy output. |
| C-229 | test corrected | The observable describes the dated heading, both breakdowns, and the total. The test now checks the no-`--json` output directly against the existing report format and fixture counts. |
| C-231 | test corrected | The observable asks for new due-time coverage written with `node:test` under `test/`. The test identifies added files using the recorded incoming inventory and checks their source for that coverage. |
| C-232 | test corrected | The observable asks what `npm test` discovers in the changed checkout. The test compares its TAP output with the tests discovered by directly running the incoming file set and the added `node:test` files locally. |
| C-233 | test stands | The observable expressly calls for comparing existing sources with the 1.4.0 baseline and running them. The incoming source inventory verifies continuity from this checkout and leaves the historical comparison unresolved. |
| C-238 | test corrected | The observable asks the new release to reopen files with exhausted counters, preserve state on failed allocations, and allow writes without allocation. The test retains those checks for both counters in both visibility modes. The separate 1.4.0 reopen is outside this observable. |
| U-7 | test corrected | The flow concerns backing up and preparing existing data with visibility off, then enabling it. A version 1 fixture represents the handoff after the prior owner has stopped. The test checks the backup, durable backfill, legacy ticket responses, and activation. |
| U-11 | test stands | The flow explicitly requires unmodified 1.4.0 to use and save the prepared file before returning to the new release and recovering deadlines. The test exercises that actual rollback and return. |
| U-14 | test corrected | The flow requires existing audit and notification activity for comparison across rollout. A version 1 fixture provides prior ticket timestamps, audit entries, and a pending notification. The test still exercises ticket changes, deadline passage, delivery, and restart. |
| U-15 | test corrected | The flow runs `npm test` on the changed checkout. The test now verifies the incoming sources by checksum and checks that the local run passes and executes both incoming and added due-time tests. |

All nine corrected checks passed using their existing acceptance commands. All seven standing checks stopped at the missing `22f8405` object before making their historical comparisons. The acceptance command mappings remain valid.
