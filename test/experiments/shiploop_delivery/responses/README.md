# Recorded teachback evidence

Store a real independent response at `A/<packet-name>.md`,
`B/<packet-name>.md`, or the exploratory `B2/<packet-name>.md`. Do not create
a response merely to make the fixture look complete.

Each file begins with:

```markdown
# Teachback provenance

- Packet: `packets/A/example-r1.md`
- Variant: A
- Repetition: 1 of 2
- Interpreter/session: observed identifier or `unknown`
- Fresh context: yes/no and basis
- Material read or tools used: packet only, or exact listed paths
- Observed at: ISO-8601 timestamp with offset

## Raw response
```

Then retain the response verbatim. If a pre-existing response lacks one of
these fields, add a neighboring `provenance.md` with the available facts rather
than rewriting the raw response. A response is not a ShipLoop callback and does
not prove a deployment, authorization, test, or completed Improve campaign.
