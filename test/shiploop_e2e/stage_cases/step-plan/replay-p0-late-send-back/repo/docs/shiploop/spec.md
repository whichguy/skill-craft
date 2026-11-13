# Living spec

Seeded by the E2E harness: the stages before step-plan are recorded without doing them, so the request is the specification.

## Requirements

R-1: In this Node.js project, add a new module src/records.js exporting parseRecords(text) and select(records, field, value). parseRecords reads one record per non-blank line; a line holds fields `key=value` joined by `;`, a key is a lower-case letter followed by lower-case letters, digits or underscores, and values are trimmed: parseRecords('name=ada;team=x\n\nname=bob;team=y') returns [{name:'ada',team:'x'},{name:'bob',team:'y'}]. It rejects malformed input: a field with no `=`, an empty or invalid key, or a key repeated on one line throws a SyntaxError whose message names the 1-based line number; a non-string argument throws a TypeError. select returns the records whose field equals value, in input order (select(rows,'team','x') on the rows above returns the first record only); a non-array records throws a TypeError. Cover it with node:test tests; npm test must pass.
