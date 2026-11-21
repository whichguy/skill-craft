# Help desk ticket service

## Requirements

### R-1 Fixed ticket deadlines

The November 2026 due-time request specifies creation time plus 4, 24, 72 and 168 hours for urgent, high, normal and low. The HTTP create response shows the resulting UTC due instant when enabled. An operator can override each priority via the environment. Test each default, an override and invalid input. Priority edits and restarts under new settings retain the deadline once it is stored. Existing create, update and transition semantics remain defined by [the API](../api.md).

### R-2 Ticket representations and overdue lists

The November 2026 request specifies a `due` field on ticket responses. At the HTTP boundary test create, get, list, update and transition. With the exact flag value `DUE_TIMES=on`, `GET /tickets?overdue=true` returns only open and in-progress tickets with a due instant strictly earlier than the service clock. Equality remains current. Apply this condition before the existing cursor page and in conjunction with the existing status/priority predicate. Existing default and other query behavior remain documented in [the API](../api.md). Test active, resolved and closed tickets, page boundaries and filtering together.

### R-3 Pre-exposure backfill and rollback

The November 2026 request specifies durable deadlines for historical tickets from their stored creation times and priorities, and rollback to 1.4.0 over the new data file. Before exposure, save any missing deadlines without changing ticket IDs, ordinary fields, audit, outbox or sequence counters. Repeated startup and settings changes preserve populated deadlines. Persist deadlines on new tickets even while disabled so new writes are rollout-ready. With `DUE_TIMES` unset or anything other than `on`, compare the old response shapes and ignored overdue query behavior. Fail startup before listening if the data file cannot be prepared. Verify candidate and archived 1.4.0 startup on the same fixture with every ticket counted. Existing one-writer ownership and backup rules apply. Production access and actual promotion are outside local verification.

## Non-functional requirements

Keep Node's standard library and existing suite, preserve the data file's atomic replacement boundary, and add node:test checks for the new behaviors. Keep the human CLI's established table/detail format and the weekly report's four raw columns. No new UI, service, account, or data owner is involved.

## Retired

None.
