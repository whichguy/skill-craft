---
bump: patch
---
The Grok adapter's list of direct ShipLoop subcommands now includes `check`, the verb that replaced `complete --check-only` in ShipLoop 1.21.0. Before, a Grok-hosted E2E run could not credit or run `shiploop check`, and `test_direct_subcommand_allowlist_matches_the_current_shiploop_cli` failed in CI's full tier (the 1.21.0 release commit, job `full / e2e-apparatus`).
