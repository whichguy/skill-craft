---
bump: minor
---
The handoff lists what the run leaves for a later run in a new result key, `follow_on`: one entry for each leftover,
classified once (gap, decision, person, capability, extension, debt, note), each citing a record the run holds (an
unverified row, an assumption, the release-verify lessons, a stage's result or a commit). ShipLoop refuses only
mechanical faults: a missing list, an incomplete entry, a class outside the vocabulary, a placeholder left in, a source
the run does not hold, a gap that names no request sentence. A gap or a decision makes the script write
`follow-on-request.md` in the run folder and print the command that starts a follow-on run from it, in the done packet
and in the report's new Follow-on section. ShipLoop starts nothing and never blocks `done` for what an entry says. A run
saved without the list still loads.
