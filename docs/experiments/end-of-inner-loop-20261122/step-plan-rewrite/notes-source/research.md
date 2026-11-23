# Research

Existing contracts resolve the consequential questions: src/tickets/states.js defines closed as final but resolved as non-final; comments must accept resolved. src/tickets/validate.js normalizes names by trimming and exact matching applies to assignees. Body text may contain newlines; default is trim outer whitespace and reject blank text, following existing text normalization while allowing multiline. src/persistence.js explicitly selects record fields and defaults earlier absent additions; extend the record with comments while retaining version 1. src/outbox.js deduplicates pending keys, so each comment needs its own key and payload. src/templates.js requires a template or the worker marks notifications dead. src/store.js defines audit and copy semantics; augment that mechanism. test/helpers.js runs isolated HTTP server and supports file-backed restart. No dependency or remote access is needed; local filesystem and Git access were proven by workspace start and test run.

## Assumptions
- Evidenced: names are normalized with existing validation and compared exactly (src/tickets/validate.js, src/store.js).
- Evidenced: notification events are asynchronous and retryable (src/outbox.js, src/worker.js).
- Evidenced: state lives in a single optional data file (src/persistence.js).
- Default: comment IDs are sequential per ticket; chronological insertion order survives restart; test duplicate timestamps.
- Default: comment bodies retain internal newlines and are trimmed at their boundaries. Verify at HTTP boundary.
