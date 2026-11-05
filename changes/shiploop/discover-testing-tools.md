---
bump: patch
---
Automatically discover testing tools from the host and repository, preferring
available, suitable Chrome DevTools for browser inspection and interaction.
Diagnose and recover failed tool routes before declaring UI automation
unavailable, and preserve runtime, session, target-access and product-test
evidence separately for later checks.
Attempt an existing UI before authentication work. When sign-in is needed,
discover supported adjacent CLI, SSO or credential-provider routes, use only
the scope needed for the tests, and resume the same UI check afterward.
