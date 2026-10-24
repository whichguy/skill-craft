---
bump: minor
---
- **Test layers are result fields:**
  - A done test-strategy lists `surfaces`. Each row covers one code surface at one layer (unit, component or e2e) and
    gives its harness, a status (available, prerequisite or unverified) and a reason.
  - It also lists `targets`: where the tests run, whether that place keeps state, and, if it does, how a test still
    fails on an item's base there (`base_state_route`).
  - `surfaces_na` replaces `surfaces` only when the run writes no code.
- **The test-strategy gate:**
  - Every surface needs a unit or component row, and neither of those layers may be unverified. A missing harness at
    them is `prerequisite` work.
  - Rows may not repeat.
  - The printed lines must fit 1,200 characters.
- **Prepare proves each prerequisite:** prepare's `harness_runs` records, for each prerequisite row, the command that
  ran one test with the harness and its saved output.
- **Each step-plan criterion says `confirm`:**
  - `executed`: a recorded command runs the behaviour. A command that only searches text (grep and its kin) is not
    enough.
  - `searched`: for text the item writes.
  - `inspected`: names an unverified row, by `surface` and `layer`.
- **Item rows:** when the run recorded no surfaces and a step plan's paths hold code, that step plan lists the item's
  own rows.
- **Packets quote the fields by value:**
  - prepare, step-plan, test-spec and test print a required Test layers block, grouped by layer, harness and status,
    with each row's reason where it is not available, and a Test targets block;
  - criteria lines show how each criterion is confirmed.
- **One term per concept in the stage texts:**
  - test-strategy's layers are unit, component and e2e;
  - test-spec names a case's Test layers row instead of a "surface" list;
  - RED points at the Test targets block;
  - verify's send-back is worded by `confirm`.
- **The implement review focus is shorter**, so the improve-commit line stays inside the handoff's first 4,500
  characters. A server entry point's access posture joins the public entry point line.
