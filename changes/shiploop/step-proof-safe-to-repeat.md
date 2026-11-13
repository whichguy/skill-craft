---
bump: patch
---
Step-plan's proof bullet now says ShipLoop reruns a step's Proof at the step's done, so the Proof must be safe to repeat. The
tests-are-not-a-step line drops the clause its refusal already states ("a step changing only test files is refused"), which keeps
the step-plan head inside its print bound.
