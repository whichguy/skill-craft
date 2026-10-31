---
bump: patch
---
The Apps Script platform card now has a Testing section that says how to test a deployed project, and the test-strategy, plan, prepare and step-plan packets point to it once the environment notes name the card. A test that calls the deployment never sees the checkout, so the section tells the plan to name the deployment as a test-strategy target that keeps state. ShipLoop then does not run those tests on the item's base, and the mutation check skips them and records why. A step that changes deployed code also names, in its Proof or in an expectation, one command that reads the deployed result. No script changed: a card the model reads gained one section.
