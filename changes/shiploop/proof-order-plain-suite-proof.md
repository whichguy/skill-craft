---
bump: patch
---
Step-plan's proof-order refusal now also refuses a step whose Proof is a plain suite command, such as `npm test`, when
one of its executed criteria is confirmed by a test file the item base does not have and no earlier step declares. That
Proof runs only the tests that already exist, so it cannot confirm the criterion when implement reports done. The
refusal asks for a Proof that runs the step's behaviour directly. Proofs that name a script or run inline code are not
affected.
