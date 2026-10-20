---
bump: minor
---
- **Spec write-back at implement:** an inline step that settles what a requirement should say adds one acceptance line
  inside that requirement's R-<n> entry in KNOWLEDGE/spec.md, ending `(<item>/<step>)`, and ShipLoop commits it with
  the step. Any other spec change at implement is refused: a changed or removed line, an unmarked line, or a line
  outside a current requirement. The refusal names send-back for a real requirement change.
- **Send-back after a refused implement done:** when the item-scope or spec gate refuses an implement done and names
  send-back, that action's send-back is accepted even though its Until Loop has already completed. Before, the
  refusal's own exit was refused in turn.
