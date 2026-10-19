# Template review, round 2 (read-only, 2026-10-18)

Read `BRIEF.md` beside this file first: its sources, owner rules, read-only rule and safety rule (never open
`*.transcript.md`) all still apply. Your round-1 JSON is in
`/Users/dadleet/src/skill-craft/docs/experiments/run-insights-2026-10-18/template-review/<your-name>.json`.

The templates and partials are now version 2, in the same place,
`/Users/dadleet/src/skill-craft/docs/experiments/run-insights-2026-10-18/templates/`:
- `step-plan.template.md` and `implement.template.md`, with new front matter (`requires`, `gates`);
- the `partials/` folder, which adds `outcome-done`, `outcome-blocked`, `outcome-send-back` and `outcome-add-work`;
- `*.filled.md`, re-rendered from the Battleship records;
- `*.render-report.json`: sizes, bound overrides, placeholders, gate anchors.

The renderer and value tools are in `../packets-tools/` (`tmpl.py`, `prep_values.py`). What changed, and why, is in plan
section 8.4 (`/Users/dadleet/src/skill-craft/docs/shiploop-run-insights-plan-2026-10-18.md`), together with decision 19
(folder symbols: bare words, HOME renamed KNOWLEDGE).

**Important design facts of version 2:**
- Text the code owns is now a slot: the Until Loop argument (`{{loop_argument}}`, rendered from the run's own contract
  file with two declared engine changes) and the outcomes (one partial per N5 outcome).
- The template is written for the state after its `requires` land. It deliberately names fields today's gate refuses
  (`concerns`, `criterion_evidence`, `learned`, `decisions`, `learned_from`). Judge that as "lands with its feature", not
  as a P0, unless the `requires` list misses something the template depends on.

**Your job:**
1. **Re-verify every round-1 finding of yours against version 2.** Mark each `fixed`, `partly`, `open` or `wont-fix`,
   with a reason, in a `round1` list: id, status and why. Verify in code or in the rendered print, not from the plan
   text.
2. **Review version 2 fresh**, with the same four questions and severity scale as round 1, and list new findings
   (`findings`, with new ids). Check especially:
   - text the compression may have made ambiguous or wrong;
   - rules dropped by mistake;
   - gate anchors that do not actually state the rule;
   - contradictions between a partial and a template;
   - anything the `requires` list misses.
3. **Budget.** The prints are step-plan 21,395 and implement 20,471 characters. At the T-D2 producer limits they would
   be about 20.6K and 19.7K, against a 19,500 budget and Grok's 20,000 cut. The static worst case is about 25K for both.
   Say what you would cut, and assess this option. The Until Loop runtime prints the contract's Work, Exit and Repeat in
   every packet it returns, so the ShipLoop packet could replace its ARGUMENT block (about 2.0-2.3K) with a one-line
   pointer. Verify that the runtime prints them: look at `until_loop_ephemeral.py` start/next packets under
   `R/skills/improve/runtime/until-loop/scripts/`, or run it in a scratch directory. Weigh this against the owner rule
   of 2026-10-16 recorded in `shiploop_loops.py` near `BLOCK_HEADING` ("say RUN with the explicit argument and
   command"). Give a recommendation.

Write
`/private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/tmpl-review/<your-name>-r2.json`
with `round1`, `findings`, `budget` and `verdict` (sufficient, necessary, open P0/P1 count, summary). Return a 10-line
summary.
