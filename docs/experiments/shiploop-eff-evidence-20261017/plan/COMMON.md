# Shared brief: ShipLoop packet and plan review (read first, once)

Goal of the whole effort: make **ShipLoop** better (efficiency, conciseness, fidelity), generically, for any program or platform (a Node bug fix, a Salesforce app, a long document). Never tune for the sample.
You are a READ-ONLY worker. Do not edit, stage or commit anything in any repository or worktree. Never run `sf`. Never touch the live E2E run folders. Write only the files your task names (under the scratchpad `eff2/` folder).

## Paths
- Scratchpad: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad  (call it SP)
- The artifact, split into text files (the recorded live run): SP/artrev/00-intro.md and SP/artrev/NN-<step>.md. It is a Claude Code (claude-sonnet-5-5) inline-route run of case node-fix-bug on ShipLoop 1.3.0 / plugin 2.3.1: for every stage it shows the packet ShipLoop printed, what the model said and did (every tool call and the output), the result it submitted, ShipLoop's response, and the files left. Paths are shortened to <run>, <worktree>, <skills>, <out>. The page's HTML is at SP/redesign/inner-loop-redesign.html (do not read it whole; use the text files).
- The current plan (revision 4, red-teamed): SP/final-plan.md (sections 4 workstreams with step ids like 3.4a, 7 per-packet table, 10 what NOT to do, 11 open decisions D-1..D-28).
- The branch journal (what is released, what each unreleased branch's review found): /Users/dadleet/src/skill-craft/.claude/worktrees/docs-efficiency-98075a/docs/shiploop-efficiency-journal-2026-10-16.md
- The code, at main `da9e2e75` (skill-craft 2.5.0 / ShipLoop 1.5.0): /Users/dadleet/src/skill-craft (read only; packet generators are in skills/shiploop/scripts/: shiploop_navigator.py `packet_head`, `_render_*`, shiploop_loops.py, shiploop_stage_spec.py `STAGE_PURPOSE`, shiploop_prompts.py, shiploop_reference.py). Unreleased branches (read only): /Users/dadleet/src/skill-craft/.claude/worktrees/shiploop-eff-{stop,loop,packets}-6afcbc.
- Render current offline packets: `cd /Users/dadleet/src/skill-craft && python3 test/shiploop_e2e/packets.py --offline node-fix-bug <empty dir under SP/eff2/render-...>` (check its usage first; it writes packet files; use a fresh dir, never a repo dir).
- Evidence of the Grok live run behind the plan's numbers: SP/sfchess/live2 (events.jsonl, result.json, review-export). Optional; the plan already summarises it.

## Standing owner rules (from the owner's decisions; findings that contradict them must say so and justify)
1. MAIN TENET (S-6): context is cleared or compacted between stages. Every packet must stand alone: it restates how its stage operates and is reviewed; cross-packet repetition is grounding, not waste, unless a script proves a duplicate inside ONE packet. ShipLoop gets no signal about warm or cold contexts. Test every consolidation by it.
2. Scripts own graph position, derivation, validation and the printed return prompts; the model does one step and reports done. Never ask the model to hold state. Hooks must see every command: commands stay literal, absolute, copy-ready (no symbolic path inside a command line).
3. One supported version: no compatibility shims, fallbacks, aliases or migrations; refuse old artifacts.
4. KISS over adversarial guards: fix only what breaks or misleads a normal run; document adversarial-only gaps; prefer one-line fixes. Question the value of every change (unrequested is not valueless; removed is not tidy): for / against / verdict.
5. Prompts: concise AND meaningful. Cut ineffective detail, keep obligations. A prompt that grows past a size bound: raise the bound, do not trim an obligation (but a host cut at ~20,000 printed characters drops the tail, so order matters). Compact packets (~8k) are printed whole; rules and code craft as one-liners; loop mechanics live on the card, EXCEPT the owner now wants the Until Loop block to say RUN the skill with the literal argument layout and the literal command (branch -loop- 0d462ca4).
6. Packets mention Improve only as a directive; the Improve packet = run /improve + call done; ShipLoop binds and writes the opening. Producer text never names Improve in advance.
7. No iteration limit on quality or test loops; stop rules are script-measured, never a model-facing clock or cap.
8. Generic: platform detail only in references/platforms/; no domain words (chess, Salesforce, Battleship, Node specifics) in generators or tests outside fixtures; fixtures synthetic and neutral.
9. Evidence: progress is a script-run test that passed, not a model judgement. Every claim grounded: cite the artifact section and a short quote (under 25 words), a file and symbol (never a line number), or a command you ran. Link heavily. Say "not measured" when you did not measure.
10. Produce for a consumer: every output names who reads it, when and in what form.
11. Owner language preferences: use concise, technically accurate language; paths as symbols in prose (RUN, WORKTREE, HOME, GUIDES) but literal in commands; packets should say explicitly what to run and what comes next (not generalities); the owner floated a first line in every packet that points to a master reference ("read this if you lack context or are unsure") and/or a script call that returns state; the owner prefers pointing to a file the model inspects and then opens subfiles from.
12. ShipLoop must be unattended by default: record defaults and open items; prompt the user only when nothing can proceed.
13. Do not add a directive that makes a model hang or refuse (the credential-pattern refusal was removed for that reason).

## How findings are classified against the plan
For every finding set `plan_relation`: `in_plan` (the plan already has this: give the step id or D-n), `extends_plan` (the plan has the topic but this adds a fact, a wording, or a case), `new` (not in the plan), or `contradicts_plan` (the artifact shows the plan is wrong or risky here: say how).
Rank `impact` high only when a normal run is slower, wrongly refused, misled, or loses an obligation, with evidence from the artifact or code.

## Output discipline
Return the structured result. Keep each field tight (a sentence or two; quotes short). Quote exact packet wording for proposals (the actual replacement text, not a description). Prefer fewer, evidenced findings over many speculative ones, but do not skip real ones.

## Owner updates (2026-10-17, after this brief was first written; later phases must honour them)
- The owner said: when the plan is final, IMPLEMENT it and RUN the Salesforce chess case again (ShipLoop builds a playable chess game in the owner's Developer Edition org `de`). No release or push until the owner sees the result and says go; the run uses `--source checkout` of the integration branch.
- The owner wants the finished app to REMAIN in the org (they will play it): that is the explicit go for `--keep-platform` on that run (use a durable `--output` folder). Contract today (test/shiploop_e2e/README.md, "Keeping what a run made"; run.py `keep_refusal`): kept only for a finished delivery (ShipLoop done and its report written, host ended by itself, every case check passed, no timeout or stop, valid trial); every other ending cleans. Run 2 shows the gap: the deployed app passed the org checks (`deployed`, `tests`, `rules` 28/28) but ShipLoop hit the 4 h cap, so the contract would have removed a working app. Proposal to carry into the plan as a unit: also keep when the org checks pass and the trial is valid even if ShipLoop did not finish, marked "not a pass" (never keep after a user stop or an invalid trial). A kept app makes the case's preflight refuse the next run until it is removed with the printed command or a different prefix is used: say so.
- "Shiloh" in the owner's message is a typo for ShipLoop.
