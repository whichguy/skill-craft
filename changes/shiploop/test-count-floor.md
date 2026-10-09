---
bump: minor
---
ShipLoop now also refuses a test run of an item's command that ran fewer tests than the most any run of that command it accepted for the item has run since the item's latest step plan, so a test removed or newly skipped to pass is no longer a pass. The test-author probe sets the first number, test-refine (whose duty is to explain removed cases) is not held to it and restarts it, and a revised step plan starts it again; the refusal names both numbers and the stage's real exit, and the packets state the rule.
