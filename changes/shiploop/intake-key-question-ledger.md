---
bump: minor
---
Intake asks the key questions about the request through a category catalog (K1 outcome and consumer to K11 risks) and
records them in its result: `question_categories` (each of K1-K11, applies or not with a reason) and `questions` (id,
category, question, what it changes, route, default, what it blocks). On Codex Terra 6.1 the shipped intake raised 49%
of the decisions a vague request leaves open (51% at xhigh effort); with the ledger it raised 91% (98% at xhigh). The
gain reaches the spec (spec carried 0.90 of those decisions against 0.78). The template asks for both fields; ShipLoop
checks their shape when present, keeps them in the stored intake result for the stages after it, and refuses them at
another stage.
