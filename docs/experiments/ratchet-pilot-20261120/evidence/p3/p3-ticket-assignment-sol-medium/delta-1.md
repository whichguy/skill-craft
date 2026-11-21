# Closing look

Read the specification, plan, build and test reports, API and operations documentation, README, and decision records for cursor pagination and assignment. The packet contained no fix or referee reports. Inspected the request decoder, query parser, storage, worker, and CLI formatting to follow up on the live results.

Ran `npm test` and all 127 tests passed. Started the service with `npm start` on an OS-assigned port, using temporary version 1 data and notification files. Exercised assignment, replacement, clearing, overlapping equivalent PUTs, lifecycle changes, ticket reads, combined filters, and cursor continuation after reassignment. Probed name lengths at 1, 64, and 65 ASCII characters and at 32 and 33 supplementary characters, JSON body sizes at 65536 and 65537 bytes, whitespace, controls, malformed input, missing and extra fields, duplicate members, and a valid JSON body sent as `text/plain`. Used the CLI table, raw listing, ticket history, and weekly report. Forced a save failure and retried after restoring writes. Restarted with the worker enabled and verified saved ownership and delivery of assignment and requester notices. Also checked that a saved name with surrounding spaces prevents startup.

## Clauses added

- **C-164** · product keeps to it: no. A raw 0xFF in a PUT became U+FFFD and was stored in the name. The malformed filter `D%FFana` and the properly encoded literal replacement character both selected that ticket.
- **C-165** · product keeps to it: no. With Sam assigned, a raw body containing an assignee of Dana followed by an assignee of null returned 200, cleared ownership, and appended the clear to the audit.
- **C-166** · product keeps to it: no. The service accepted internal U+0085, U+2028, and U+2029. Each introduced a line boundary inside a ticket row in both CLI listing modes when read with Unicode line splitting.
- **C-167** · product keeps to it: no. The CLI printed `assignee Dana -> null` for both a clear and assignment to the literal name `"null"`. The audit API returned distinct JSON values.
- **C-168** · product keeps to it: yes. With the original cursor and filters, the next page included the ticket newly assigned to Dana and excluded the ticket reassigned to Sam. It remained in ticket id order.
- **C-169** · product keeps to it: yes. Compared the legacy file before startup and after API reads with the worker off. The bytes matched.
