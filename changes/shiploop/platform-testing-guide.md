---
bump: minor
---
- **Platform testing guide:** discovery records the platform guide each target follows under `## Targets and runtimes`
  (`GUIDES/platforms/<name>.md`, or none). Test-strategy, plan, prepare and step-plan then point to that card's
  `## Testing` section, so the platform's testing rules (deploy before test, the reporter ShipLoop reads) reach the
  stages that decide tests.
- **Salesforce card:** it gains the `## Testing` heading, and its org-bound test advice now matches the mutation check's
  remote-test skip.
