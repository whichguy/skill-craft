---
name: shiploop
description: Markdown-authoritative SDLC session harness with action-bound evidence.
---

# ShipLoop

Load and follow the canonical ShipLoop skill at `skills/shiploop/SKILL.md`.
ShipLoop 0.9.3 gives one durable action at a time; its Markdown records—not
chat memory or a sidecar—are authoritative.

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
- After interruption, run the recovery command (`next`), inspect actual effects
  and durable evidence, and reconcile before continuing. `next` does not
  advance the graph. Resolve a paused or blocked condition before following its
  printed `resume`; halted and done packets stop.

Existing managed and legacy runs retain their recorded protocol. Follow only
their printed callback and recovery instructions. A legacy packet may authorize
commands such as `context`, `verify`, or `repair`; they are not default
navigator lifecycle steps.
