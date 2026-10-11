---
bump: patch
---
A visit with no packet reads as recorded by ShipLoop, not skipped: the page's legend, visit count, table, card list and the
visit's Outcome line say "recorded by ShipLoop", and facts.md counts "N recorded by ShipLoop". The export keeps
`stages[].skipped` and adds `stages[].recorded` from the engine's summary: "expectations matched" (an 8-stage
validate-existing whose expectation checks all matched) or "not applicable" (a stage left out of the item); older exports
without it keep the previous Outcome wording.
