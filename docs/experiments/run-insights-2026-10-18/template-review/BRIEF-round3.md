# Template review, round 3 (read-only, final verification, 2026-10-18)

Read `BRIEF.md` and `BRIEF-round2.md` beside this file first. Every rule in them still applies. Your earlier files are in
`/Users/dadleet/src/skill-craft/docs/experiments/run-insights-2026-10-18/template-review/`: `<your-name>.json` and
`<your-name>-r2.json`.

**What changed since round 2.** Committed 04242a9f, plus the uncommitted working tree under `templates/` and
`packets-tools/`. Plan sections 8.4 and 8.5 have the details.
- Round-2 fixes:
  - revisit blocks are excerpt-class, with the send-back locator;
  - `stop_outcomes` is a slot;
  - the look-back wording;
  - KNOWLEDGE in the generated locators;
  - the fill rules state what the gates really refuse;
  - `awaiting` gains a service kind;
  - A0's considerations (titles in the head, full text in the appendix);
  - the seven-field `criterion_evidence`;
  - later steps print with their criteria, plus an anchor ID line;
  - `requires` is complete, with a lands-with note.
- Engine changes E1-E4 are declared in plan 8.5.
- New budget rule: refuse slots count at their bound, and every other slot can shrink to a pointer (the renderer does this
  before passing the budget). The progress bound is 900.
- **Decision 20 (owner, 2026-10-18):** the packet no longer prints the Until Loop ARGUMENT block. The loop-invoke partial
  ends with "Contract: <abs> · Receipt: <abs>" and says the loop prints its Work, Exit and Repeat in every packet it
  returns. "Done when" points at the loop's exit conditions.
- Measured static worst case:
  - reference install: step-plan 19,366, implement 19,396 (budget 19,500);
  - Battleship's install: 19,666 and 19,758 (Grok cuts at 20,000).
- The re-rendered prints are in the scratch folder `tmpl-v2/` beside this brief: `<stage>.filled.md` and
  `<stage>.render-report.json`. The filled files in `templates/` will be refreshed after this round.

**Your job:**
1. Mark each round-2 finding of yours (`<your-name>-r2.json`, both `findings` and `round1` entries still open or partly
   fixed) as `fixed`, `partly`, `open` or `wont-fix`, with a reason verified in the files or the code.
2. Look for anything decision 20 or the compression broke, such as:
   - a model that has not started the loop no longer knowing what "done" means;
   - a gate anchor that no longer states its rule;
   - a lost rule;
   - a contradiction.
   Report new findings with the same scale.
3. Give a final verdict: open P0 and P1 count, sufficient, necessary, and whether the template is ready to land once its
   `requires` are met.

Write `<your-name>-r3.json` beside this brief, with `status`, `findings` and `verdict`. Return an 8-line summary.
