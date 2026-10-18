# Packet review brief (read-only)

The owner wants every prompt ("packet") that ShipLoop sent in one live run judged: is it **concise, accurate, effective**, and how could it be optimized? You review one group of consecutive steps. You are READ-ONLY: edit nothing in any repository, run no `sf`, no tests, no ShipLoop command.

## The run
Salesforce chess case (Apex chess engine + Lightning web component board, deployed to the owner's org alias `de`), host Grok 4.7 at medium effort, ShipLoop 1.5.0 plus unreleased efficiency work. 26 stages accepted in 155.6 min; 11 Improve reviews (21 passes, ~51 min); 573 model tool calls; 8 context compactions; 5 `complete` refusals; it ended blocked at release-verify waiting for a person. The app works (the owner played it), all 4 case checks pass.

## Inputs (all under `PR = /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/pkt-review`)
- `PR/index.json`: one row per step (n, tag, stage, reviews, outcome, calls, model_seconds, minutes, packet_chars, fresh_start = compaction and the re-grounding cost, improve min/passes, context).
- `PR/in/<NN>-<stage>.packet.md`: the whole packet ShipLoop wrote (paths shortened to `<run>`, `<worktree>`, `<out>`).
- `PR/in/<NN>-<stage>.result.md`: what the model submitted. `PR/in/<NN>-<stage>.calls.txt`: every tool call the model made (seconds from run start, tool, command or path, clipped).
- Improve steps: `PR/in/<NN>-improve-<stage>.packet.md` plus `.improve-handoff.md`, `.improve-opening.md` (the prompt the improve skill received), `.improve-review-<n>.md`, `.improve-passes.md`, `.improve-receipt.md`, `.improve-parent-return.md` and pass/report JSON.
- `PR/refusals.txt`: the 5 refusals' texts. `PR/facts.md`: script-measured run facts.
- Measured already (do not redo, build on it): across the 25 stage packets, 53% of all characters are the knowledge files (HOME/spec.md, environment.md, architecture.md) quoted whole in each packet; 7% is "Current stage guidance" (the only stage-specific part); 7% is the original request quoted whole every time (4.7 KB); the rest is header, checked-by, status, narrative, template, rules, references, hand-offs. Revisit packets share 94% of lines with the first visit.
- Generator source (to name WHERE a fix goes, by file and symbol, never line numbers): `/Users/dadleet/src/skill-craft/.claude/worktrees/shiploop-eff-int-c5f79b/skills/shiploop/scripts/` (shiploop_navigator.py, shiploop_stage_spec.py, stage guidance text, loops, handoff/improve modules) and `skills/shiploop/references/`. `git grep` a quoted phrase to find its source.

## Owner rules the proposals must respect (flag any conflict explicitly)
1. MAIN TENET: context is cleared between stages; each packet must work alone after context loss. Repeating a stage's own operating and review rules across packets is grounding, not waste. Test every consolidation against this.
2. Compact packets printed whole (~8 KB target); rules and code craft as one-liners; reference, do not reprint unchanged long text; packets list readable references.
3. Prompts: concise, meaningful change: cut ineffective detail, keep every obligation. Intent → observable outcome → the model grades its own result against it.
4. Improve packet minimal: run /improve on the handoff, then call done; no packet pre-announces Improve.
5. Host print cut (measured): Grok prints up to 20,000 characters whole; above that only the first ~10,000 and last ~10,000 reach the model unless it opens the packet file. Claude passes ≥30,000 whole; Codex ≥40,000.
6. KISS: fix what breaks or misleads a normal run; one-line fixes preferred; no adversarial-only guards.

## For EACH step in your group
Read the packet, then the calls and the result (and for Improve the handoff, opening and reviews). Judge with evidence from what the model actually did:
- **concise** (1-5): text the stage cannot act on, duplicated blocks, boilerplate restated in long form, knowledge quoted the stage does not use (check the calls: did it reopen the files anyway? did it read the packet file because the print was cut?).
- **accurate** (1-5): instructions that are wrong for this stage or this platform, stale or contradictory lines, references that do not exist, placeholders, checked-by text that does not match what the gate did (see refusals).
- **effective** (1-5): did the model do the stage's job without wasted calls, refusals, loops or drift; which packet lines it visibly followed or ignored; where it spent its time and whether a packet change would have saved it.
- **findings**: concrete, each with the quoted packet text (≤200 chars), the evidence (call times, result text, refusal), the proposal (an exact rewrite, a move to a reference, a deletion, or a reorder), where it is generated (file + symbol), characters saved per packet and across the run, and the risk to any obligation or the main tenet.

## Output
Write `PR/out/<group>.json`:
```json
{"group": "...", "steps": [{"tag": "...", "concise": 0, "accurate": 0, "effective": 0, "one_line": "...", "findings": [{"id": "G-n", "kind": "redundant|inaccurate|ambiguous|missing|misordered|dead-text|oversize|effective-line", "quote": "...", "evidence": "...", "proposal": "...", "source": "file:symbol", "chars_saved_per_packet": 0, "applies_to_stages": ["..."], "risk": "..."}]}],
 "cross_cutting": [{"id": "...", "pattern": "...", "evidence": "...", "proposal": "...", "source": "...", "est_chars_saved_run": 0, "risk": "..."}],
 "best_lines": ["packet lines that clearly worked, with evidence"]}
```
Return a 10-line summary: the 3 biggest optimizations with evidence, the worst inaccuracy, and the most effective packet feature. Be concrete and short; no generic advice.

## Owner input during this review (2026-10-17)
"We definitely don't need the ShipLoop Navigator as a prefix, necessarily." Treat the `ShipLoop navigator | <stage> | revision N` first line, the `# ShipLoop navigator result` template heading and the `ShipLoop navigator:` prefix on refusals as candidates to drop or shorten; say what (if anything) reads that text (git grep for parsers, hooks, keepalive, status readers) so removing it is safe.
