---
bump: patch
---
A run on the ask-agent route saved at ShipLoop state version 11 or later pairs its steps with its visits as an inline run
does: ShipLoop now issues one implement packet per step on that route too. A run saved before it (state version 10 or
earlier) keeps its reading, with the reason that no visit is tied to a step.
