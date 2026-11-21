# Closing look

Read the request, specification, both cycles' build and test reports, the plan, the previous delta, the README, the API and operations guides, and the assignment decision. The packet contained no fix or referee reports. Checked the HTTP decoder, query parser, persistence reader, CLI formatter and notification path against the live results.

Ran `npm test` and all 135 tests passed. Used `npm start` on an OS-assigned port with temporary data and notification files. Created, assigned, reassigned, cleared, edited, resolved and reopened tickets. Checked a same-owner retry, a missing ticket, inactive-ticket refusals, and the ticket, audit and outbox after invalid requests. Probed names at 1, 64 and 65 ASCII characters and 32 and 33 supplementary characters, body sizes of 65536 and 65537 bytes, wrong types, whitespace, line breaks, an unpaired surrogate, malformed JSON, duplicate members and malformed UTF-8. Checked combined filters, query escaping, page limits and a continuation after reassignment. Ran the CLI table, raw listing, details and weekly report. Restarted with the worker enabled and verified saved ownership and delivery of agent and requester notices. Also restarted on altered copies of saved data and ran an upgrade from the archived Cycle 1 code.

## Clauses added

- **C-171** · product keeps to it: no. With `0xFF` in the saved owner `Sam`, startup succeeded, the API and CLI showed `S�m`, and clean shutdown rewrote the bytes. In a separate copy with `0xFF` in Sam's queued recipient field, the worker delivered that event to `S�m`, the same spelling as an independently assigned agent with a valid U+FFFD in the name.
- **C-172** · product keeps to it: yes. `Dana%25` selected the ticket for `Dana%`, while the incomplete `Dana%` query returned 400. A valid first value still worked with malformed encoding in a later duplicate and an ignored parameter.
- **C-173** · product keeps to it: yes. Cycle 1 queued a notice for a name with internal U+2028 and then cleared ownership. The current release showed the ticket as unassigned and emitted the pending notice with its original recipient, id and key.
