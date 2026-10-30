# ShipLoop document stage: review and proposal (2026-10-30)

Status: proposal for the owner. P0 is fixed and verified live on Codex Terra (journal §5, C1; owner go 2026-10-30);
P1-P6 await a decision. Evidence and experiments: [shiploop-document-stage-journal.md](shiploop-document-stage-journal.md).

## 1. Verdict

The document stage's prompt is close to right in principle. It documents from observation ("document nothing you did
not observe working"), links to one authoritative home instead of copying a contract, and records step learnings in
the three living files. Research supports both choices (§3 of the journal). Four problems matter:

1. **A contract bug, not a wording problem.** The document stage's Until Loop scope allows "only the paths its
   accepted step plan declares, plus docs/shiploop/". The duty says to update the README, and `ITEM_COMMITS` commits
   documentation files, but the loop forbids touching them. A model that follows the contract literally (Codex Terra
   xhigh, ask-agent pilot, 2 of 2 steps) leaves the README alone and writes the product's API reference into
   `docs/shiploop/`, ShipLoop's own knowledge home. Its notes say so in as many words (journal L3).
2. **Code contracts are nobody's job at this stage.** Implement writes docstrings (Code craft 3), the per-step review
   checks them afterwards, and the document stage's duty never mentions them. Tombstones, argument constraints, and
   file and class docs live only in a linked reference section. Strong models open the link and do the work (E1 arm
   A); nothing in the packet's exit conditions requires it.
3. **The knowledge home fills with noise.** Under the current text the stage records test counts, npm notice lines,
   a host classifier's refusal of `pkill`, and an architecture decision for a choice local to one class (E1 arm A,
   18 knowledge lines across three scenarios). The "persistent change only" test you asked for is not in the prompt.
4. **Deployment docs have no owner.** release-verify and operations write only `environment.md`. No stage compares
   the product's operator documentation (how to start, configure, check health, deploy and roll back) with what the
   release showed.

"Dumping more prompt text" is not the fix: the research's strongest result is that restated or agent-written context
lowers task success and raises cost (arXiv 2602.11988), so each added line below answers an observed miss, and the
mechanical checks move into scripts.

## 2. What the side experiment showed (E1, exploratory)

Three post-implement scenarios built from the E2E `node-base` fixture, each with planted documentation defects:

- **S1 Basket:** a new class with vacuous docstrings, comments that restate code, a removed-approach note, a public
  array that bypasses the limit, and a spec that departs from a project convention.
- **S2 rename:** `getUser` → `findUser`, with stale mentions in README.md and docs/api.md.
- **S3 health route:** no start or port docs, and HEAD /health answers 404.

Arm A ran today's duty text, imported from the skill. Arm B ran the proposed text (§4, P1-P3). Subject: Sonnet 5.5
(the owner allows it for exploratory rounds), one run per cell. Judge: one blind Opus 5.5 pass. The packet keeps the
live layout but replaces the Until Loop with its exit and repeat lines, so it cannot show the scope bug (§1.1).

| Measure | A (today) | B (proposed) |
|---|--:|--:|
| Deterministic checks passed (39 in all) | 38 | 38 |
| Knowledge-home lines added | 18 | 8 |
| Product Markdown lines added | 38 | 30 |
| S1 comment lines in `src/basket.js` (18 code lines) | 27 | 16 |
| ADs added | 2 (one for a single-class choice) | 1 (the real departure) |
| Transient facts in environment.md | test counts, npm notice, host `pkill` refusal | none |
| Blind judge preference (3 scenarios) | 0 | 3 |
| Judge total, 5 dimensions x 3 scenarios (max 75) | 51 | 68 |
| of which concision / knowledge (max 15 each) | 7 / 6 | 13 / 14 |
| of which contract / reader docs / drift | 12 / 15 / 11 | 14 / 14 / 13 |
| False or unsupported statements the judge found | 7 | 3 |

Reading: on a strong model the current prompt already gets the contracts, a tombstone, the drift fixes and the
caveats. The proposed text keeps that and cuts the noise: about half the knowledge-home writing and 40% fewer
comment lines for the same checks, preferred blind in all three scenarios. n = 1 per cell on one subject model, and
this judge family is reported to favour shorter answers (research F3.8); the deterministic checks tie, so read it as
direction, not size. One of B's three flagged statements is a refinement for P1: its tombstone cites the run mark
`(W1/S1)` in product source, because the removed approach had no test to cite.

## 3. The drift hint (E2, measured)

A script-derived packet line, in the style of carry-forward's "commands that passed and environment.md does not
name": identifier-shaped names (an underscore or a camel hump) the item's code removed and no longer has, which a
living doc still mentions (dated records, changelogs, journals and experiments excluded).

- S2: exactly the two planted mentions (README.md:7, docs/api.md:6); S1 and S3: none.
- skill-craft's last 30 commits: 27 print "none"; three large refactors print 10 candidates, none a real stale
  mention in a living doc (a CLI placeholder, a host error name, release output).
- Sonnet found S2's mentions without the hint, so its value is for weaker subjects and larger repositories
  (unmeasured). It is advisory text, never a gate.

## 4. Proposal

Ranked by evidence and cost. "Routine" means a fix ShipLoop's decision rule lets a session make and record; "owner"
means it needs your call (AGENTS.md "Decisions").

| # | Change | Where | Evidence | Kind |
|---|---|---|---|---|
| P0 | The document loop's scope names the documentation files ShipLoop commits (README, `docs/`, the docs path class) next to the step plan's paths and docs/shiploop/, and says product documentation never goes in docs/shiploop/. One test pins that the document contract's scope and `item_scope.commit_scope` agree | `shiploop_loops._build` (`scope`); new test in `test/shiploop-*` | L3 (firm) | routine bug fix |
| P1 | Duty item 2 becomes **Contracts at the code**: reconcile the docstring and comments at each changed file, class and entry point with the code and the tests that observe it, in the house form; state constraints with the error a violation raises, return, other errors and side effects only where they apply; one contract-versus-narration example; a stated constraint the code does not check is a defect to fix now; define a tombstone in one clause (what must not return, why, its test ID or AD-<n>; never a run or step mark in product code); delete comments that restate the code or that the change made false. Done-when 1 and the repeat rule name contracts | `DUTIES["document"]`, row `document` done-when, `REPEAT["document"]` | E1 (exploratory), research F1.3, F3.7, F4.4 | owner (prompt) |
| P2 | Reflect gets an admission test: record only what the code and README cannot tell a later reader, what changes a later step, stage or run, and what holds after the item; probes, counts, host quirks and one-off workarounds stay in the summary or notes. An AD only when the step sets or departs from structure, a dependency, an interface or a convention; a choice local to one unit stays in its docstring or tombstone. environment.md takes commands a later stage will run | `DUTIES["document"]` item Reflect; same clause in carry-forward's knowledge item | E1 (exploratory), research F5.1-F5.4 | owner (prompt) |
| P3 | Reader docs are placed by reader in one line (use and setup in the README, reference in the existing API doc, start, configuration, health check and known limits where operators look), and the packet prints the drift hint with "fix each stale mention below" | `DUTIES["document"]` item 3; `shiploop_navigator` beside `CHANGED_SINCE_BASE` | E1, E2 (measured) | owner (prompt + hint) |
| P4 | House style records the docstring form and the doc tooling (for example one-line JSDoc, Google Python sections, TSDoc; a doc linter if the repository has one) next to comment density, and the document packet links House-style guidance | `house-style.md#extract-the-house-style` item 4; document guide table | code read; E1 S1: both arms wrote multi-line JSDoc under a recorded one-line convention and neither said so | routine |
| P5 | Deployment docs: operations (or release-verify) compares the product's operator docs with what the release and its checks showed; a step the docs state wrongly or omit is `add-work` with one documentation-only corrective item when it misleads, else an open item for handoff | `DUTIES["operations"]` item 2 | code read; L6 (one README claim caught at release-verify in 22 runs) | owner (product behaviour) |
| P6 | Hygiene: the comment above `CODE_CRAFT` says implement, test and document carry it (only implement and the review focuses do); the comment "What a producer packet prints instead of CODE_CRAFT" has no code under it | `shiploop_prompts` | code read | routine |

Not proposed:

- **Carrying the full Code craft block (about 3,500 characters) in the document packet.** P1's compact item gave the
  same contract outcome in E1, and the research says not to restate a rubric.
- **A fresh-context document review.** That is SDLC gates experiment SG2 (declared in PR #27, merged; not yet run),
  whose result should decide it.
- **Doc linters run by ShipLoop.** The lint gate already runs markdownlint where a repository configures it; adding
  docstring linters per language is a stack rule ShipLoop avoids.

Size: P1-P3 take the duty from 2,972 to 4,305 characters with the commit rule, about 1,300 more in an 18,200-character
packet (+7%). Every added clause maps to a miss in E1 or L3; items 1 and 4-7 keep their wording.

## 5. Verification before release

1. P0 and P6 with their test, on the quick tier (`--changed-from` the merge base).
2. P1-P4 as one change with a change note, rendered with `packets.py --offline` and `render_diff.py`, and
   `packet_changes.json` entries for the new lines.
3. One live round on the owner's current runner (Codex gpt-6.1-terra xhigh, hooks on) over `node-add-function`,
   `node-rename` and a Basket-shaped case, both arms, graded by `grade.py`'s checks ported into the E2E probes, with
   the per-step Improve review's doc findings counted as the misses the document stage left.
