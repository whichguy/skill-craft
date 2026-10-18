# Run analysis brief (read-only)

The owner wants an analysis report for each of two live ShipLoop runs, inspecting the prompts (packets) and the model's
responses, answering three questions:
1. **Step by step:** was implementation a series of steps, each implemented, proven and reviewed in plan order?
2. **Improve effectiveness:** did each Improve review find and fix real problems (cite them), at what cost, and did its fixes
   hold or prevent a later failure? Which reviews were rubber stamps (trivial passes that missed something a later stage hit)?
3. **Directive sufficiency:** for each stage, did the prompt tell the model HOW to execute relative to the stage's purpose
   (the method, the order, what to read, what done means, how it is checked), or did the model have to guess, search
   ShipLoop's own source, misread, loop or get refused? Judge from the model's reasoning (THINK), its words (SAY) and its
   calls, not from the prompt alone.

You are READ-ONLY: edit nothing anywhere; no `sf`, no tests, no ShipLoop commands.

## Inputs
`DIR` (given in your task) holds `index.json` (one row per step: n, tag, stage, reviews, outcome, calls, says,
think_chars, model_seconds, packet_chars) and `DIR/in/<NN>-<tag>.*`: `packet.md` (the prompt ShipLoop wrote),
`transcript.md` (in order: THINK = the model's reasoning, SAY = its words to the user, CALL = a tool call, OUT = the tool's
output, clipped), `result.md` (what it submitted), and for Improve steps `improve-handoff.md` (the review's prompt),
`improve-review-<n>.md` (the reviewer's responses), `improve-passes.md`, `improve-receipt.md`.
Context: the two runs are Grok 4.7 medium against the owner's Salesforce org. Chess (`report-chess`) ran on ShipLoop 1.5.0
plus the first efficiency wave; Battleship (`report-bs`) ran on the integration branch after the packet-review plan
(knowledge as a table of contents, one progress block, gates stated, a per-step Proof that ShipLoop runs, step-scoped
checks, revisit lines, the procedure walk). The plan and its findings: `/Users/dadleet/src/skill-craft/.claude/worktrees/
shiploop-eff-int-c5f79b/docs/shiploop-packet-review-plan-2026-10-17.md`; the chess packet review (findings F1-F12) is in
`docs/experiments/packet-review-2026-10-17/` there. Known run facts: chess collapsed its 3 planned steps into one after an
item-wide check failed S1; Battleship planned 4 steps and ran each with a Proof and an Improve, twice (a test-stage revise
because the mutation gate tested the org copy restarted every step); Battleship's host idled after done.

## Output
Write `DIR/analysis-<group>.json`:
```json
{"group": "...", "steps": [{"tag": "...", "purpose": "<the stage's purpose in one line>",
  "directive": 1, "directive_evidence": "<what the prompt said vs what the model had to work out; quote THINK/SAY lines ≤200 chars>",
  "response": "<did the result serve the purpose; one line>", "step_by_step": "<implement/step stages only: step id, order, proof, review>",
  "improve": "<Improve steps only: findings real or not, edits, cost, held or missed>", "gaps": ["<concrete missing or misleading directive, with the fix and where it is generated if you can find it by git grep>"]}],
 "run_level": {"step_by_step": "...", "improve": "...", "directive": "..."}, "best": ["..."], "worst": ["..."]}
```
Return a 10-line summary: the answer to each of the three questions for your group with evidence, the worst directive gap,
and the most effective prompt feature. Be concrete; no generic advice.
