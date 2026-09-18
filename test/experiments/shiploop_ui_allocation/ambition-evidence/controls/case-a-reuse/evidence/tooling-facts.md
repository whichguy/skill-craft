# Controlled tooling facts — A

These facts distinguish observed baseline from controlled capability. They do
not establish a live target or third-party package capability.

* The copied product is a non-Git static embedded web fixture. Its existing
  same-origin JavaScript and CSS entrypoints are `app.js`, `index.html`, and
  `styles.css`; [docs/platform.md](../../product/docs/platform.md) records a
  self-only CSP, no deployed server process, no external CDN, no persistent
  WebSocket, and foreground reconciliation.
* The copied UI already owns a native account selector, note list, stable
  textarea editor, save/cancel/back controls, live status regions, focus
  handling, navy/amber/Georgia skin, and narrow responsive composition. Those
  are source-baseline facts, not permission to redesign unrelated journeys.
* The controlled embedded runtime permits ordinary DOM composition, same-origin
  CSS classes, CSS transitions/keyframes, `aria-live`, and a
  `prefers-reduced-motion` media query in the bundled artifact. They are the
  available primitives for this fixture; motion remains an explanatory cue, not
  confirmation of a server-domain outcome.
* `node --check app.js` and `node --test` are the existing product commands.
  The latter currently discovers zero tests. Chrome and Playwright have been
  observed in the research host, but are not installed product dependencies or
  a product browser harness. A future browser assertion must extend the product
  verification path or a target-compatible facility; this control must not add
  a standalone design or test harness.
* There is no `package.json`, lockfile, Bootstrap, Material implementation, or
  other framework/package availability record in this fixture. Treat all such
  packages as unverified candidates, not available tooling. No install is
  allowed.

The available `frontend-design` card is an optional planning input at
`<study>/capabilities/frontend-design/SKILL.md`
with SHA-256 `1608ea77fbb6fc30d13a97d12cfa8ebf31358d40f0dd97beed24829d6b3f45dd`.
Its observed identity is guidance only; it does not authorize an external
dependency, redesign, or unexecuted tool.
