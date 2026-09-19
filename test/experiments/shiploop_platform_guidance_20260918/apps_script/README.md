# Apps Script platform-guidance fixtures

This is a bounded, **non-hosted** Node.js contract experiment for ShipLoop
guidance. It never calls a Google endpoint, starts an OAuth flow, installs a
package, deploys a script, changes an account, or sends a message.

Run it with a compatible Node runtime:

```sh
npm test
```

The fixtures intentionally model only three decision shapes:

- asynchronous `google.script.run`-style control flow and selected documented
  value restrictions;
- serialized state mutation with durable idempotency evidence and a derivative
  cache;
- contiguous spreadsheet-style writes versus a per-cell call budget, plus a
  control that rejects collapsing distinct notification effects.

They are not a Google Apps Script emulator. Read [research.md](/Users/dadleet/src/skill-craft/test/experiments/shiploop_platform_guidance_20260918/apps_script/research.md) for
the source evidence, decision, and live-project validation boundary.
