---
bump: minor
---
Generic ShipLoop text no longer names a platform; the examples live in the platform cards.
- The release-plan duties say "granting a role or permission, activating an app or menu entry" and "app or menu entry name and
  URL path" instead of Salesforce's permission set and App Launcher; release-check's dry-run example is "the deploy tool's validate
  or check-only mode"; the release-plan `consumer_entry` refusal and `references/consumer-delivery.md` give a generic tab example.
  `references/platforms/salesforce.md` keeps those examples and gains the `consumer_entry` App Launcher route.
- The `node --test` reporter example leaves the step-plan duty, `COUNT_RULE` and the base-run refusals for
  `references/platforms/node-express.md`; the packets point at `GUIDES/platforms/`. Jest and pytest stay as generic examples.
- `shiploop_test_counts.READERS` is the reader table and `RUNNERS` the list generated from it; the refusal for an unreadable
  focused command names the runners from it, and a test holds the reference's runner list to the table.
- A new lint, `test/shiploop-domain-words.test.py` with `test/domain-words.json`, refuses chess, example-app, Salesforce and
  host-automation words anywhere under `skills/shiploop` outside `references/platforms/`, the guidance selector's index row and
  the README's platform link.
