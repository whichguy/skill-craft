---
bump: minor
---
The ask-agent route has the same step boundaries as the inline route (design T section 9.1, 2c-1; owner decision G1,
2026-10-29: "Adopt (a2)").
- ShipLoop issues one implement action per planned step on both routes. On the ask-agent route a fresh worker builds the
  step in the shared execution checkout; it makes no commit, runs no callback, starts no later step and leaves no
  delegate writing. The step is then tested, documented, reviewed and committed by ShipLoop before the next one starts.
  Before, one implement action built every step with a chain, and ShipLoop committed the item once at the end.
- The step plan records no execution graph on either route, and no packet asks for one or for a chain.
- A saved run from before it is refused with a reason (state version 11): an ask-agent run's single implement action
  would otherwise be read as the first step.
- The item-level commit stage, the several-steps wording and the ask-agent branches of the step view, the test loop and
  the Improve hand-off are gone.
