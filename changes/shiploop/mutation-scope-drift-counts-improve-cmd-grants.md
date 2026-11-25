---
bump: patch
---

- Classify `*Test.*` and `*Tests.*` paths as tests in `path-classes.json`, and exclude executed test-command scripts and stylesheet assets (`.css`/`.scss`/`.sass`/`.less`/`.styl`) from mutation `product_files`.
- Parse test counts via `shiploop_test_counts.count` and record measured duration in `system-test` `default_suite_drift()` regression rows.
- Print the validated, shell-quoted literal Improve continuation command (`next_argv`) in the shared Improve handoff, worker brief, and restart refusal so models run it verbatim without Python JSON extraction glue.
- Make `SHIPLOOP-GRANT-NEEDED` report non-start wording on `next`, `complete`, `lint`, and non-start `workspace` subcommands instead of claiming ShipLoop did not start and created nothing.
