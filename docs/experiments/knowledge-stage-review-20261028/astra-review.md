# Astra review: a knowledge stage per step, or knowledge in document (2026-10-28)

Model `gpt-6-astra`, persona `codex-astra`, effort `max`, fallback `False`, exit `0`, sandbox `workspace-write`. Asked from the per-step iteration branch after 2b-2 (`28c8f878`), on the owner's question of 2026-10-28.

## Question

Review a design choice for ShipLoop's per-step iteration and recommend one option, with reasons and risks.

Repository (read freely): /Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0
- Design: docs/shiploop-review-after-tests-design-2026-10-27.md, sections 8 (8.2, 8.2b the knowledge stage, 8.2c skills), 9 and 9.1 (build order; 2b-2 is done, 2b-3 is the knowledge stage).
- Stage table: skills/shiploop/scripts/shiploop_stage_spec.py (rows implement, test, document, verify, carry-forward).
- Stage duties: skills/shiploop/scripts/shiploop_prompts.py, the "implement", "document" and "carry-forward" entries of the duty table (implement duty 4 writes AD-n, commands and spec acceptance lines; document duty 3 writes AD-n; carry-forward duty 1 updates all three knowledge files, duty 2 the queue, duty 3 the skill decision).
- Spec gate: skills/shiploop/scripts/shiploop_knowledge_home.py step_spec_refusal (a step may only add marked lines inside an existing R-n).
- Open items: skills/shiploop/scripts/shiploop_assumptions.py OPEN_ITEM_STAGES.

Current flow per step (inline route, built on the branch): implement -> test -> document -> Improve review of the step's code, tests and docs (edits left uncommitted) -> ShipLoop commits the step -> next step. Verify still closes the item; carry-forward closes it per item (knowledge, queue, skill decision).

The owner's question: "Do we need to introduce a stage at all during the sequence after we implement? ... do we need to update the architecture, environment or anything we've better understood about the specs? Just as a reflection to determine if the definitions need any updating as well, do we need to introduce a consideration of whether there are any more tasks that should be added?"

Option A (the 2b-3 cut in the design doc): a new model stage `knowledge` after each step's review. It writes spec clarified/satisfied-by lines, AD-n, environment facts, and makes the skill decision (moved from carry-forward). Script gates at its done. Carry-forward keeps the queue.

Option C (my proposal): no new model stage.
- Document becomes the step's one place to record knowledge: its duty gains a short reflection (spec clarified/satisfied-by lines with the step marker, AD-n, environment commands and harnesses). Implement's duty-4 write-back and document's duty 3 merge into it.
- The step review (after document) reviews those edits as docs and may correct them, writing what it learned the same way.
- The spec gate and a unique-AD check run on the final tree at the step commit (the commit stage, 2b-4).
- "More tasks": document may record open items (`assumptions`, due at carry-forward) for work outside the step plan. Work the item itself lacks stays a send-back to step-plan. Carry-forward still places every open item in the queue.
- The skill decision stays per item at carry-forward.

Evidence:
- Across 13 recorded runs all 20 carry-forward skill decisions were `none`.
- Knowledge writes today are scattered: carry-forward in 36036c and 491d9a, after document in 978478, inside an item commit in 759a03.
- 36036c wrote satisfied-by lines for every requirement, but only at carry-forward.
- A per-step packet is about 13,500 to 17,000 characters (head budgets in test/shiploop_e2e/head_table.json). Option A adds one model action per step: three on a three-step item. The pilot was framed at 7 to 15 model actions.
- The owner's standing priorities: quality first, then tokens, then time; KISS; one place per duty; scale ceremony to measured gain.

Answer:
1. Which option, or a better third.
2. What each option loses: for example, does C lose what the review teaches, and does A duplicate the review?
3. Where the "new tasks" consideration belongs per step.
4. The script gates you would keep.
5. Open unknowns a pilot should measure.
Be concrete; cite the files.

## Answer

I recommend **Option C, with explicit review write-back, preservation of every step’s open items, and gates on the final tree before commit. Pilot that shape; defer a separate `knowledge` model stage.**

The owner’s request establishes a duty to reflect after each step. The available evidence supports doing that duty consistently; it does not yet establish that it needs another model action.

1. **Make document responsible for consolidating the step’s knowledge.**

   Use this sequence:

   `implement → test → document and reflect → Improve and correct → gated commit`

   Keep implement’s `learned` and `decisions` handoff, including evidence. Move its durable write-back into document’s expanded duty. Also address **test’s existing writes**: duties 1–2 currently record harnesses and architecture decisions. Consolidating only implement and document would leave a third writer doing the same work. Test should supply the observed commands, facilities and decisions that document records. [shiploop_prompts.py — implement and test knowledge duties](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_prompts.py:1421)

   Document’s reflection should answer, briefly: what became clearer about an existing requirement; what this step actually demonstrated; which architecture decision or environment fact changed; and what remains to be done. Each knowledge file gets a change locator or a concise no-change reason. Require consideration, not edits for their own sake. This extends document’s existing responsibility for durable facts and missing AD entries. [shiploop_prompts.py — document duties](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_prompts.py:1479)

   Carry-forward should retain item-wide reconciliation, queue maintenance and the skill decision. It should consume the step records and add genuinely new closing observations, rather than repeat every step’s reflection. Keep verify while its remaining obligations are being relocated; choosing C is not evidence that those obligations can disappear.

   This is a quality argument as well as a cost argument: **C puts the knowledge edits inside the change the existing review examines.** A puts another authoring action after that review. The design itself identifies the resulting risk of changing requirements or adding executable skills after verification. [design — §9, findings 1 and 7](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/docs/shiploop-review-after-tests-design-2026-10-27.md:569)

2. **C can preserve what review teaches, but that must be an explicit completion obligation.**

   | Consideration | Option A | Option C |
   |---|---|---|
   | Focused reflection | Gets a dedicated opportunity to synthesize the completed review. | Adds responsibility to document and Improve; reflection may receive less attention. |
   | Review-derived knowledge | A later stage can extract it from review evidence. Extraction can still omit or misinterpret it. | Improve must update the affected knowledge files and final result as it discovers or corrects facts. |
   | Checking knowledge quality | Newly authored knowledge follows the step review; structural gates cannot establish its truth. | Knowledge is reviewed with code and tests, including corrections made during Improve. |
   | Skills useful within the item | Can create a skill after S2 for S3. | Delays that decision until carry-forward. This is a real capability loss. |
   | Cost and lifecycle | Adds a model action, result, retries and handoffs per step. | Expands existing duties and requires reliable evidence retention. |

   **A does not inherently duplicate review.** Checking correctness and extracting durable lessons are distinct jobs. It duplicates work if it reassesses the same decisions or rewrites facts already captured upstream. Its strongest case is a measured failure to perform synthesis inside the existing stages.

   **C does not inherently lose review lessons.** Require Improve to update knowledge and unresolved obligations **before its final non-material pass**, rather than append an unchecked reflection afterward. There is already a useful mechanism: `finish_improve(..., final_result)` can replace the parked producer result. Review-added assumptions must enter that final document result; leaving them only in review prose is insufficient. [shiploop_navigator.py — final-result import](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_navigator.py:3981)

   The reported 20 `none` skill decisions across 13 runs support deferring an unconditional per-step skill decision. They do **not** prove there were no missed reuse opportunities. Existing-skill visibility in test, document and review packets is independently useful and does not require moving skill creation to every step. [design — knowledge evidence and skills proposal](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/docs/shiploop-review-after-tests-design-2026-10-27.md:445)

   For three non-skipped steps, A adds three model actions over C: 15 versus 12 within the proposed iteration sequence, counting each Improve invocation once. The historical **7→15** comparison also includes other lifecycle changes. Packet sizes establish material overhead, not a token-cost forecast: the current inline heads include document at 13,594 characters, implement at 16,771 and test at 18,150. [head_table.json — current packet measurements](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/test/shiploop_e2e/head_table.json:22)

3. **Consider new tasks during document’s reflection, and again when review discovers something new. Keep queue editing at carry-forward.**

   Use the consequence of the finding to route it:

   | Finding | Disposition |
   |---|---|
   | An in-scope implementation defect | Fix it through the current work/review loop. |
   | The item’s step plan lacks required work or a prerequisite for a remaining step | Send back to step-plan immediately. Do not postpone it to carry-forward. |
   | Work already assigned to a later step | Preserve the finding for that step; avoid a duplicate task. |
   | Non-blocking work outside the item’s plan | Record an open assumption due at carry-forward, with why it matters and what would settle it. |
   | Requirement intent must change | Send back through planning; never disguise it as a clarification or an ordinary follow-up. |

   Two implementation details are essential.

   First, adding `document` to `OPEN_ITEM_STAGES` is insufficient: add it to `CARRY_FORWARD_PRODUCERS` too, so `due_stage: "carry-forward"` is valid. [shiploop_assumptions.py — producer sets](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_assumptions.py:27)

   Second, retain obligations **per step and plan revision**. `current_actions()` currently retains only the latest done result per `(workitem, stage)`, and `open_items()` reads that projection. I reproduced the consequence with a small isolated probe: S1’s document assumption disappears after S2 submits an empty list. The revision-aware aggregation already required by §9 must therefore arrive before per-step document assumptions are relied upon. [shiploop_planning_revision.py — latest-result projection](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_planning_revision.py:102), [shiploop_assumptions.py — open-item reader](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_assumptions.py:183)

   Carry-forward should explicitly disposition every surviving finding: map it to queue work, resolve it with evidence, or retain an appropriate later-stage obligation. Its successful completion alone should not silently count as resolving everything; the current reader’s settlement rule makes that a particular risk. [shiploop_assumptions.py — settlement behavior](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_assumptions.py:214)

4. **Keep the gates, but attach them to the authoritative final result and candidate tree.**

   | Gate | What I would require |
   |---|---|
   | Reflection completion | A concise disposition for spec, architecture and environment; `assumptions`, including an explicit empty list when appropriate. No forced knowledge-file edits. |
   | Spec preservation | Only marked additions under requirements that existed and were current at the iteration base. Preserve established text; route intent changes to planning. |
   | Architecture integrity | Unique **definition** IDs, retained superseded decisions and valid references. Ordinary mentions of an AD must not count as duplicate definitions. |
   | Obligation retention | Valid due stages and evidence locators; retain earlier steps’ findings and review additions; handle planning invalidation explicitly. |
   | Final validation | Applicable lint and active test/doc commands on the final candidate. Preserve the existing RED, mutation, ID and floor obligations; invalidate receipts when their relevant inputs change. |
   | Commit integrity | Bind receipts to item, plan revision, step, base and candidate. Commit that exact tree, persist the pending operation, retry idempotently, and advance only after success. |
   | Skill decision | Keep it at carry-forward. Retain shape, file and trial checks; validate cited repeat/future-use IDs rather than accepting arbitrary nonempty strings as sufficient evidence. |

   **The existing spec gate needs strengthening under either option.** It derives valid requirement spans from the edited file, rather than checking that their IDs existed in the baseline. An isolated probe accepted a newly appended `## R-2 (W1/S1)` and marked requirement text. It also accepted a marked contradictory clarification—which illustrates the separate semantic limitation. Fix baseline membership mechanically; leave truth, completeness and intent preservation to review. [shiploop_knowledge_home.py — step_spec_refusal](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_knowledge_home.py:593)

   Three related changes should be part of the C implementation:

   - **Do not skip reflection because public documentation is unchanged.** `_document_entry()` currently auto-completes document when the diff touches no code or test path. That rule cannot establish that there is no architecture, environment or specification learning. Public-doc work may be N/A while reflection remains due. [shiploop_navigator.py — document omission](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_navigator.py:4377)
   - **Update the lifecycle contract too.** `shiploop_iteration.STAGES` already includes `knowledge`, and `commit_decision()` explicitly reopens it. C requires removing that assumption and defining the appropriate repair/revalidation route. [shiploop_iteration.py — stage contract](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_iteration.py:32), [commit_decision](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_iteration.py:133)
   - **Include post-implement learning in the commit message.** `_step_commit()` currently builds its message from the implement result. Consolidate document and review findings so the step’s look-back contains what was learned later. [shiploop_navigator.py — step commit](/Users/dadleet/src/skill-craft/.claude/worktrees/per-step-iteration-6adde0/skills/shiploop/scripts/shiploop_navigator.py:3021)

   I would recut **2b-3 as knowledge consolidation and obligation retention**, then complete **2b-4’s final-tree commit enforcement before the live pilot**. Prompt changes alone do not complete C.

5. **Measure whether the knowledge changes later work correctly—not merely whether reflection produced text.**

   The pilot should answer:

   - Does C miss consequential facts discovered only during review?
   - Are satisfaction claims accurate and scoped to the clauses actually demonstrated, with cross-step and real-boundary obligations still pending?
   - Can the next step find and use the new decision, command or harness without rediscovering it?
   - Do S1 findings survive S2/S3, review amendments and send-backs, without stale findings returning?
   - Does document’s broader duty degrade user-facing documentation or code-review quality?
   - Would a skill created before the item ends materially improve a later step?
   - What are the actual input/output tokens, additional file reads, retries and non-overlapping model time?

   Include cases where review changes an AD or environment fact, no public docs need editing, several steps discover separate follow-ups, and a repeated procedure could benefit S3. Compare matched runs and repeat material regressions; battleship alone may underexercise the strongest argument for A.

   External guidance supports this measured tradeoff: focused sequential stages can improve accuracy, while additional evaluation loops should justify their token and latency costs through quality gains. It does not establish which arrangement wins here. [Anthropic — workflow patterns and tradeoffs](https://claude.com/resources/articles/common-workflow-patterns-for-ai-agents-and-when-to-use-them)

   **Reconsider A if C repeatedly misses important knowledge despite explicit duties and reliable handoffs, or if useful within-item skill reuse is demonstrated.** The current evidence establishes the need for timely capture and stronger enforcement; a dedicated model stage remains an unproven means of achieving it.

This was a read-only review; no repository files were changed.
