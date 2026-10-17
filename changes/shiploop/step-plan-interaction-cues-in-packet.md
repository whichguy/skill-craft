---
bump: minor
---
The step-plan packet again prints the interaction, UI and service-state planning bullet in duty 9 for a work item that may
change them: a Design basis paragraph or exact section links, rechecking the Interaction design guide's matching
subsections; baseline and delta; actors, events, connections and state owner; planned recovery checks; for UI the
component, interaction and skin premises, the design guidance identity and version or digest (or named fallback) and the
rich interactions planned; the UI decisions the step owns; locators of sources and checks. The packet file again lists
the Interaction design guide's path.
- Why: the head budget change moved this bullet to references/plan-record.md to fit the 20,000-character host print, which
  left a UI item's step plan with only a pointer. A model starting with no context rarely opens a pointed-to file, so the
  obligations did not reach the model.
- When: ShipLoop decides from the original request and the item's title and context. Words for a user interface,
  interactions, events, connections or held state ("client state", "state owner", not the verb "state") mean the item
  may change them. An item with none of these words keeps the short form, the pointer to the Plan record guide alone, so
  its packet does not grow. The node bug-fix case's packets are unchanged.
- Size: a UI item's step-plan head is 19,862 characters inline and 19,788 on the ask-agent route at a normal install
  (83-character run directory, 96-character CLI path), within 20,000. To fit, it leaves out the lookups and chrome the
  packet file repeats (the results it builds on, the progress view, the pause command), in the head's existing order.
  No duty is dropped.
