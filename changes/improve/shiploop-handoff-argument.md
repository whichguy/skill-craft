---
bump: minor
---
The improve skill accepts `ShipLoop Improve: <handoff path>` as its argument. ShipLoop's Improve packet now only invokes
the skill and names the done command (owner, 2026-10-11). The handoff file ShipLoop writes takes the place of the packet
in the "ShipLoop whole-skill subcall" section: the binding marker, the result under review, the start, commit and
return commands, and the evidence files.
