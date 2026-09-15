---
name: shiploop
description: Markdown-authoritative SDLC session harness with action-bound evidence.
---

# ShipLoop

Load and follow the canonical ShipLoop skill at `skills/shiploop/SKILL.md`.
ShipLoop 0.10.0 gives one durable action at a time; its Markdown records—not
chat memory or a sidecar—are authoritative. New navigator runs use protocol 2:
one shared INNER graph and per-work-item `{stage, action}` records in the same
state. While an item is active, root is `inner-loop` with no action and the
item supplies the only effective prompt and callback.

- Before doing stage work, use `init` once for a genuinely new delivery, or use
  `next` for its existing run. Confirm the printed original goal and repository
  before resuming. A missing or relocated locator must recover the same run and
  identity or remain incomplete; never replace it with `init`.
- Preserve the packet's absolute CLI, repository, and run-directory locators
  plus its exact `Recovery command:` in durable host handoff material. They are
  locators only, never copied node/action/status/successor state.
- Give a worker one current packet and relevant references. The parent/run owner
  alone submits its action-bound callback and consumes the returned packet; a
  worker does not create or advance a parent run.
- Treat each Improve assignment as one call-and-return campaign. ShipLoop does
  not record its review phases or counters; it receives one completion when the
  owner finishes the campaign. At carry-forward, completed item records remain
  `done` with no action and the next item is created automatically.
- After interruption, run the recovery command (`next`), inspect actual effects
  and durable evidence, and reconcile before continuing. `next` does not
  advance the graph. Resolve a paused or blocked condition before following its
  printed `resume`; halted and done packets stop.

Recorded navigator-v1, managed, and legacy runs retain their recorded protocol.
`init --execution-mode=navigator-v1` exists for compatibility fixtures; normal
new work uses protocol 2. Follow only the existing run's printed callback and
recovery instructions. A legacy packet may authorize commands such as `context`,
`verify`, or `repair`; they are not default navigator lifecycle steps.
