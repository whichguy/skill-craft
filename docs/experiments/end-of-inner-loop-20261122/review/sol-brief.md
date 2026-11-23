You are an independent design reviewer. Work read-only in this folder: an export of the ShipLoop source
(`skills/shiploop/`) and the journals of earlier studies (`docs/`). Use maximum effort. Cite a file and symbol, or a
journal section, for every factual claim, and mark anything you did not verify yourself.

## The owner's question (verbatim, two messages, 2026-11-22)

1. "One of the key things that I do want to look into is to determine if, after an inner loop run, we need to go into
   key learnings about what was built and the tests that were created, review and update the specs, and potentially
   update the plan. We would actually have a permanent, iterative updating of the plan as a very specific named stage
   at the end of the inner loop. Can you investigate this and help me understand if this is what we should do?"
2. "updating specs, environment, architecture, plan steps, local skills which could be created to enhance future
   operations (which needs reference in architecture), is what I was thinking"

## What ShipLoop is

A script-navigated delivery harness. Scripts own the stage graph and print each stage's packet; the model does one
stage and calls back; the script picks the successor. Context may be cleared between any two stages, so every packet
restates how its stage works. Stages are rows in `skills/shiploop/scripts/shiploop_stage_spec.py` (prelude, inner,
outer). The knowledge home is `docs/shiploop/{spec,environment,architecture}.md` in the product repository
(`skills/shiploop/scripts/shiploop_knowledge_home.py`). `docs/decisions/` holds one decision commit message.

The owner's standing rules that bear on the answer: change something only for a measured difference in outcome
(naming alone never justifies a change); every test or experiment must be able to change a decision or validate one
already made; ShipLoop's loops have no iteration cap; the drivers to optimise for are Sol 6.2 at medium and Sonnet 5.5
at medium.

## Part A: answer the question yourself, before reading Part B

1. What in ShipLoop today already does each of the five things the owner lists (spec, environment, architecture, plan
   steps, local skills with a reference in architecture), where, and with what script checks?
2. What do the recorded studies show about whether doing them more, or in a separate named stage, changes outcomes?
   Read at least: `docs/experiments/step-boundary-replan-20261112/README.md`, `docs/experiments/step-boundary-replay-20261113/`,
   `docs/experiments/knowledge-stage-review-20261028/`, `docs/shiploop-sdlc-structure-journal.md` (round 5 and its
   Limits), `docs/ratchet-pilot-journal.md`, `docs/ratchet-vs-shiploop-journal.md`, `docs/shiploop-multipass-journal.md`,
   `docs/shiploop-follow-on-run-journal.md`, `docs/platform-knowledge-journal.md` (sections 32, 33, 37 and 50 to 53),
   `docs/planning-time-analysis-2026-10-06.md`.
3. Your recommendation for each of the five parts: add a stage, change an existing stage, or leave it. Weigh both
   directions: what a change could gain, and what it could break (for example a writer after the last review, spec
   growth that rejects correct products, a skill or document nobody opens, context growth across runs).
4. The one cheapest test whose result would change your recommendation: its decision rule written before it runs, its
   cost in deliveries, and what each outcome would make us do. If no plausible test would change it, say so.

## Part B: check my claims (only after Part A)

For each claim: TRUE, FALSE or OVERSTATED, with the locator, and a corrected statement where needed.

- B1. `carry-forward` is the last inner stage of every work item. Its duties are the knowledge home, the future
  work-item queue (`work_items`, which replaces the whole future queue when supplied) and a skill decision (none,
  reuse, update or create).
- B2. Each step's `document` stage reflects what the step showed into spec.md, architecture.md and environment.md, and
  its result must carry a `knowledge` record per living file. This was chosen on 2026-10-28 over a separate knowledge
  stage after each step (option C over option A).
- B3. carry-forward writes architecture.md and environment.md, not spec.md (`STAGE_FILES`).
- B4. A created local skill is indexed in environment.md `## Skills` and in the repository's README or AGENTS index,
  not in architecture.md.
- B5. The remaining steps of the current item are not re-planned at a step boundary except through a send-back to
  step-plan, which since ShipLoop 1.34.0 keeps done steps and fixes forward.
- B6. In 300 runs before 2026-11-12, carry-forward replaced the queue 4 times, each only adding a W2 after a single W1,
  and none revised a pending item; 7 of the 8 send-backs after a documented step were plan-time Proof faults.
- B7. In the 273 to 306 runs of the 2026-11-19/20 study, 281 of 282 plans had one work item and the skill decision was
  `none` in 306 of 306; switching off the within-run look-back at earlier `learned` lines changed no hidden check.
- B8. The Ratchet pilot's closing "what did we learn" looks added clauses that outside judges mostly did not accept
  (10 of 59), and 6 of 9 tested closing-look clauses failed on a correct reference; a look built into ShipLoop at
  product-acceptance showed no gain in the audited trials.
- B9. A fact placed under `## Platform facts` in the starting repository's environment.md reached the plan 8 of 8 and
  the product 3 of 3; a page only named in the project's knowledge file was not delivered (0 of 3).
- B10. Nothing yet measures whether the knowledge home makes a later delivery on the same repository better or faster:
  no recorded run withholds it, and the multipass chains could not test value because every pass passed.

Answer in plain prose with short sections: Part A (1 to 4), then Part B (B1 to B10), then anything I did not ask that
you think the owner should hear.
