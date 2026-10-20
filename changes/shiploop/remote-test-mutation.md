---
bump: minor
---
- **Mutation check on a hosted platform:** when every focused command tests a deployed copy, a command a platform card
  lists under `## Remote tests`, the check now records `skipped` with the card and command named. Before, it mutated a
  local copy those commands never read, so every mutant survived and good tests were refused. The Salesforce card
  lists `sf apex run test` and `sf apex run`. Local tests, such as Jest, are still mutation-checked.
