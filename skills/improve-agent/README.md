# Improve Agent

~~~mermaid
flowchart LR
    Request[Request] --> Route{Consumer contract?}
    Route -->|No| Helper[Ask Agent helper-managed worktree]
    Route -->|Yes| Owned[Ask Agent consumer-owned, in place]
    Helper --> Worker[One fresh agent runs /improve inline]
    Owned --> Worker
    Worker --> Verify[Parent verifies receipts, SHAs and checks]
    Verify --> Relay[Relay Improve's summary and delivery state]
~~~

`improve-agent` runs one Improve invocation in a fresh native agent while the
invoking conversation keeps working. Use `improve` when the review loop should
run in the conversation itself. It starts no agents by default.

The two skills split one job:

| Skill | Runs the loop | Starts agents |
|---|---|---|
| `improve` | In the invoking conversation | None, unless an independent review is explicitly requested |
| `improve-agent` | In one fresh native agent, which runs `/improve` inline | Exactly one worker |

## Start with a normal request

~~~text
Use $improve-agent on the parser changes while I keep working on the docs.
Use $improve-agent on formatter.py and its tests. Do not commit anything.
~~~

The parent writes the assignment. It leads with the current context and
desired improvements, then says `Run /improve using <selected improve card>`
once, then gives the workspace, authority, evidence and return binding. The
worker is the only candidate writer, starts no further agents, and returns
Improve's completion summary together with the locators, changed paths, commit
SHAs and checks. The parent verifies those against the candidate before it
relays or delivers anything.

## Workspace routes

A standalone request uses Ask Agent's helper-managed default: an isolated
worktree, with delivery as `commits`, `patch` or `report-only`. A consumer that
supplies a complete consumer-owned contract, such as a ShipLoop
`delegation: ask-agent` Improve packet, gets the in-place consumer-owned route.
That route needs the `ask-agent/consumer-owned-workspace/v1` capability and
fails closed when the contract is incomplete.

## Dependencies

This package is prompt-only. It needs the host-selected `improve` and
`ask-agent` skills installed alongside it, and it resolves their loaded cards
instead of guessing a checkout path.
