---
bump: minor
---
A ShipLoop review now reads a short core of the ShipLoop route at each Improve stage:
`references/shiploop-route.md` is 9.7 KB (it was 47 KB, read whole at every stage) and holds every
rule a normal pass needs beyond the handoff. It names the file to open, and when, for each case:
`shiploop-route-recovery.md` (an error, stopped or blocked return, lost state, a half-done pass, the
stopped child, the inline route's text), `shiploop-route-ask-agent.md` (`Route: ask-agent`),
`shiploop-review-inputs.md` (the fixed review inputs, one section per condition),
`shiploop-route-cases.md` (independent review, later decisions, external operations,
`verify_script`, `final_result`) and `shiploop-route-rules.md` (the long form of the core's rules).
The old route's text moved there word for word; no obligation was dropped.
