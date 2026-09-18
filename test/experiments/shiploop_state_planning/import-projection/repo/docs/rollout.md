# Staged release boundary

The fixture's proposed delivery order is local contract/reader verification,
then a 5% writer canary with both reader versions active, then a mixed-reader
stage, then a wider writer stage. Moving between stages requires the evidence in
`accepted-nfr.md` and an explicit authorized promotion decision.

There is no live environment, database, deployment credential, or release owner
in this repository. Planning a stage is not permission to enable it. On a failed
stage, hold the stage and preserve compatible records for investigation and
reconciliation; do not delete shared edits to make a rollback appear clean.
