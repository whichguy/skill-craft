# Help desk ticket service requirements

## Scope

The existing internal JSON API serves help-desk agents. CLI operators and the weekly report are read-only consumers. The pre-merge behavior is documented in README.md, docs/api.md and accepted decisions 5–8, as of 6aa51a6. Hosted identity and throughput were outside the local observation.

## Requirements

### R-1 Merge a duplicate into a surviving ticket

Basis: “Let agents merge duplicate tickets.” (2026-11-21). Add a manual action alongside the lifecycle commands in docs/api.md. The action has the same internal API access boundary as existing mutations. X-Actor supplies the audit label with the documented system default.

- An agent posts `{"into":"T-0001"}` to `POST /tickets/T-0002/merge` with both tickets open. The API returns 200 with T-0002, status `closed` and `mergedInto: "T-0001"`. The survivor's fields and each ticket's original content and creation time are preserved. Confirm via the response and subsequent GETs. Resolved and in-progress participants are eligible too.
- The source's audit gains one `ticket.merged` entry with status and link deltas, the acting label and the source's new updated time. The target's audit and the existing outbox are unchanged. Confirm through the audit and outbox routes. The operation neither deduplicates automatically nor combines requester information.
- The source is absent from its previous active status filter and appears under closed. It remains accessible by ID and cannot be edited or transitioned. Confirm through the standard list, GET and mutation routes.

### R-2 Reject invalid merges and make identical retries safe

Basis: the same request and the final-state and no-op contracts in docs/api.md and decision 7. Add merge-specific state constraints while keeping the normal transition table.

- Malformed or noncanonical IDs, missing/unknown body fields and self-merge yield 400 `invalid`. Unknown source or target yields 404 `not_found`. No state or side effects change. Confirm HTTP error envelopes and readbacks.
- A well-formed request with a closed unmerged participant, a source already merged elsewhere, a target already merged, or a source that already has incoming duplicate links yields 409 `conflict`. Multiple duplicate tickets may point to the same survivor. The survivor may later close normally. Links always point directly to existing survivor records, with no chains or cycles. Confirm against competing requests and state readbacks.
- Exact retries return the persisted source with 200 and preserve its timestamp, link, history and outbox, including when the survivor has since closed. In the single-writer runtime, mutually incompatible simultaneous requests produce one committed effect and a conflict rather than overwritten links. Confirm at HTTP and file boundaries.

### R-3 Keep durable state and existing consumers compatible

Basis: accepted data-file, audit and outbox decisions 6–8 and README.md Command line. Preserve version-1 loading, prior JSON field shapes for ordinary tickets, and the CLI's four raw columns and report status buckets.

- Reopen a legacy file and a file saved after merge. The link and corresponding audit survive restart in one file update. Reject saved links on nonclosed sources or links with invalid, missing, self or already-merged destinations. Confirm by real file read and API or store readback.
- If the synchronous save fails before replacement, the service responds with an error and keeps the original in-memory ticket and audit as well as the prior file. A clean retry records one change. Verify against an induced local write failure. The supported persistence model has one writer.
- The CLI remains read-only. Ticket detail and audit display the link. Raw lists remain positional and the report counts the duplicate as closed. Confirm via CLI and weekly report with the persisted fixture.

## Non-functional requirements

R-2 and R-3 cover integrity and reliability on the documented single-writer runtime. R-1 and R-3 cover compatibility, auditability and privacy through readback, unchanged notification payloads and preservation of claimant data. Merge retains ordinary storage and visibility rules, and uses the existing error and audit channels. No numeric latency target or graphical UI applies. Tests cover local behavior with synthetic data. Hosted perimeter, delivery and load are outside this change.

## Retired

None.
