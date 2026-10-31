---
bump: patch
---
Stage prompts say what their gates do:
- the step-plan template's check row no longer names a criterion (a lint or build command confirms no behaviour);
- an expectation's `from` is used only to settle an open item due at the item, and the template adds that row only
  when one is due;
- the test packet's mutation line describes the per-survivor rule;
- release, release-verify and handoff print the restate-`unverified` rule in the head;
- test-strategy declares test IDs as the runner prints them (`test_TC_1_output` does not show `TC_1`);
- intake cites sentences as RUN/request.md numbers them, ranges allowed and nothing copied, and a cut request points
  at RUN/request.md;
- product-acceptance names ShipLoop's own worktree return in `summary` rather than `unverified`, and prints the
  one-line optional Backchain audit instead of the route paragraph.
