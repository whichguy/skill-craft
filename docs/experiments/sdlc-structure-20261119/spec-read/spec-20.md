# Help-desk ticket service

## Requirements

### R-1 Ticket deadlines

Basis: 2026-11-21 request for configurable response windows and a timestamp set once. For a newly created ticket,
add the priority's configured hours to its creation instant. The defaults for urgent, high, normal and low are
4, 24, 72 and 168 hours. Expose positive whole-hour environment overrides. Calculate and persist due when a ticket
is created, including while gated off. A priority or configuration change leaves any stored due value intact.
Acceptance: create all four priorities at 2025-09-01T08:00:00.000Z and observe 12:00Z that day, 08:00Z on September
2, 4 and 8, respectively. Override urgent to 8 hours and observe 16:00Z for a new ticket. Change the original
priority and restart with different hours. The original keeps 12:00Z.

### R-2 Visibility and filtering

Basis: 2026-11-21 request for due, overdue=true and legacy responses while disabled. With literal DUE_TIMES=on,
the API's ticket representations include due as a UTC timestamp. Human CLI list and show display due for the
same setting. Keep raw CLI and weekly report schemas stable. In enabled HTTP listings, overdue=true requires
status open or in_progress and due strictly earlier than the service clock. Apply the condition before cursor
pagination, with existing filters retaining their OR relationship. Ignore overdue unless its value is exactly true
and the feature is enabled. With the feature off, omit due and preserve legacy listing behavior and CLI output.
Acceptance: compare HTTP and CLI at both gate settings. At exactly due the ticket is excluded; one millisecond
later qualifying active tickets appear, and resolved or closed tickets are excluded. Traverse a filtered page.

### R-3 Backfill and activation

Basis: 2026-11-21 request for existing production data and activation after the data file holds due. Offline,
calculate only missing due timestamps from each ticket's own saved creation time and priority. Preserve tickets,
audit, outbox and counters. Enabled startup refuses a persistent file containing tickets missing due. It can use an
empty or in-memory store. Acceptance: start off on a legacy file, demonstrate enabled startup refuses it, backfill it
and confirm enabled HTTP reads. Re-run under different hours and verify existing deadlines and the data file stay
unchanged. Reuse atomic replacement and the single-writer operating model (docs/operations.md).

### R-4 Rollback reads every ticket

Basis: 2026-11-21 request to roll back to 1.4.0 using the new file. Keep the version-1 document readable by 1.4.0,
including tickets written after backfill. Accept that its writer projects away due. Retain a snapshot before
rollback and support restoring earlier deadline values on roll-forward without replacing current ticket records.
Acceptance: run the original 1.4.0 server on the new file, enumerate all IDs, write a ticket change via 1.4.0,
then backfill with the snapshot. Compare original deadlines and current ticket fields by ID.

### R-5 Existing service behavior

Basis: 2026-11-21 request to keep existing behavior and tests. Preserve HTTP, notifier, audit, persistence,
CLI and report entry points, dependency-free Node and the original tests. Add new node:test tests under test/.
Acceptance: npm test runs old and new suites. docs/api.md, README.md and docs/operations.md describe the interface.

## Non-functional requirements

Use Node.js 22+ with no dependencies. Keep one atomic version-1 file under the existing single-writer rule. Verify
new startup failure gives an actionable data error. Keep established terminal table, details and errors stable.
No graphical interface or new operational service is in scope. Verify against isolated files and local processes.
Production remains owned by the service operator.

## Retired

None.
