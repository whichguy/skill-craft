# Release-evidence triage contract v2

This is an additive contract. `specs/release-contract.md` remains the v1 authority.
Use this version when `data/bundle.json` has `workflow: "release-v2"`. Apply every
v1 matching, latest-numeric-attempt, output, and no-deployment rule. It adds an
optional numeric `max_age`, whose default is `null`. When `max_age` is not null,
each selected receipt must contain numeric `age`; a selected `pass` whose age is
missing or greater than `max_age` makes the decision `blocked`.

For v2 write the v1 object with `workflow: "release-v2"`, add top-level
`"max_age": <input value>`, and add `age` to every selected row (or `null` for a
missing row). This does not alter v1 input or output behavior.
