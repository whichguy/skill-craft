# Astra review of the implement prompt (2026-10-17)

persona codex-astra, model_used gpt-6-astra, effort xhigh, fallback False. Question: astra-question-2026-10-17.md.

The biggest defect is the completion contract: **one step must satisfy whole requirements that may depend on later steps**. That encourages scope expansion, fabricated evidence, or an endless loop. Fix that before polishing the considerations.

My top five changes, ranked:

1. **Make step criteria the completion unit; requirements remain binding constraints.**

   Conflicting phrases: “each requirement this step serves is satisfied,” “works where it will run,” and “Later steps (do not start them).”

   If R-1 requires saving and retrieving information through an interface, a storage step cannot satisfy R-1 before the interface exists. As the implementer, I would either build ahead or quietly reinterpret “satisfied.”

   Replace the opening and completion language with:

   > Complete this step’s stated C-n criteria, including the connections they require. Follow the R-n requirements and AD-n decisions that constrain this work. Do not implement portions assigned to later steps or claim that a whole R-n is satisfied merely because this step contributes to it. Provide current evidence for every C-n assigned to this step.

   Apply this consistently to **Done when, evidence coverage, and the loop exit conditions**. The current result schema is criterion-based, while the prose requires requirement-based evidence.

   If a criterion itself requires later work, that is a planning defect requiring `revise`.

2. **Give both execution routes an explicit assignment, and repair the loop’s unsuccessful exits.**

   Changing only the ask-agent Work line to “all of this item’s plan” leaves “Write no tests and start no later step,” singular Proof, and singular result obligations behind. A model cannot resolve that reliably.

   Use one packet shape with an assignment slot:

   > Assigned steps: `<one step for inline; ordered step range for ask-agent>`. Work on one assigned step at a time, in order. Complete its criteria, Proof, result, and any review required by the workflow before advancing. Do not start steps outside this assignment. Exit successfully only when every assigned step meets Done when.

   The whole-plan packet must supply or unambiguously locate **each assigned step’s** criteria, Proof, cards, and anchors. A broader Work sentence alone is insufficient.

   Also replace:

   > “Repeat while … the latest iteration changed the work to fix it”

   with:

   > Continue while a completion condition is unmet and a justified investigation or fix remains. Investigation may make progress without editing files. If no justified next action remains, report revise with the blocker and attempts made; an iteration without an edit never establishes completion. Apply the seven-attempt rule to the same underlying failure.

   “No iteration limit” and a seven-attempt limit for one failure can coexist. The dangerous ambiguity is what happens when neither success nor another edit is justified. A user stop must immediately take the pause path.

3. **Turn anchors into a comparison task, rather than a reading suggestion.**

   “Anchored in” and “naming the anchor you followed” invite citation without compliance. I could write “follows AD-2” while violating its operative constraint.

   Replacement:

   > Before editing, read the assigned criteria, their quoted R-n requirements, the item’s AD-n decisions, and the relevant HOME sections. Keep a short working checklist of the constraints they impose on this step. Reuse it during the loop; refresh affected entries when an anchor changes, and reconstruct it after context loss. Before done, compare the final change with each applicable constraint and identify the evidence supporting compliance. A conflict requires revise.

   Two accompanying corrections:

   - The packet quotes every **item `follows` R-n**, but selects anchors from **step criterion R-n**. Those sets can differ. Quote the step-referenced requirements too, along with applicable non-functional requirements.
   - “Cards (read the ones that fit)” preserves the original failure mode of never opening coding guidance. Replace it with:

     > Read the listed step cards before editing. Apply their relevant directions; give a concrete reason for any card you exclude.

   This requires an initial read and a final comparison, without rereading whole files on every iteration or adding a planned per-step AD mapping.

4. **Separate implementation choices from changed decisions and authorized external effects.**

   These instructions conflict:

   - “it never re-decides what they settled”
   - “Where they are wrong … stop and report revise”
   - “a design choice … or a departure from one: the next AD-`<n>`”

   The last phrase offers a way to legitimize a forbidden departure simply by documenting it.

   Replace that write-back rule with:

   > Record a new implementation decision only when it is consistent with existing requirements and decisions and remains within the assignment. If it changes or departs from an existing requirement or decision, report revise; recording a new AD-n does not authorize the departure.

   Also replace “Existing state … is migrated first.” It can imply running a production migration during implementation, and it prescribes an order that is not universally safe:

   > Define and prepare any required state transition, including compatibility during rollout, safe reruns, and recovery from partial failure. Apply it only where this stage has authority. Record release-owned actions in their required order; preparing or documenting an action does not authorize executing it.

   Treat authority already recorded for the run as sufficient. This should clarify boundaries, not introduce repeated permission requests.

5. **Require observations that distinguish success from failure, without adding gates.**

   The current schema accepts this:

   ```json
   {
     "considerations": {
       "state": "Handled according to architecture.md.",
       "proof": "Checked and satisfactory."
     },
     "evidence": [
       {"criterion": "C1", "observed": "Implemented successfully."}
     ]
   }
   ```

   Requiring a named anchor does little to prevent it.

   Replace the result instructions with:

   > For each consideration, identify the concrete handling and applicable anchor, or explain why this step does not affect it. “Handled,” “reviewed,” and unexplained “N/A” are not answers.
   >
   > For each criterion, state what you inspected or ran, the actual observation, and where the supporting output or artifact can be found. Explain what that observation establishes and any remaining limit. An implementation description or planned future check is not an observation.

   Example:

   > `C-2: Ran <command> against <target>; observed <actual result>. Output: <locator>. Demonstrates <criterion clause>; does not establish <deferred behavior>.`

   For document work, inspected passages and a concrete consistency check can be evidence; execution is not universally required.

   Replace “Grade your work” with:

   > Inspect the final change against the applicable constraints and observed results. Record unresolved discrepancies. This check does not replace the scheduled Improve review.

   Wording can discourage boilerplate; **non-empty-field validation cannot establish truth**. The existing Improve review should compare these claims with the actual change and evidence.

Other specific misreadings worth fixing:

6. **“After each change, run the Proof and the checks this kind of work has.”**  
   I might run expensive checks after every small edit or select arbitrary checks because “this kind” is undefined.

   > Run relevant checks after meaningful batches of changes. Run the step’s Proof against the final work under review. After subsequent changes, repeat checks whose evidence may have been invalidated; recording results alone does not invalidate them.

7. **“Fix the work, never the check.”**  
   This becomes harmful when the supplied Proof names a file created by a later step—the exact historical failure.

   > Do not weaken or replace Proof to obtain acceptance. If Proof cannot validly assess this step at this point in the plan, report revise with the mismatch.

   An empty deferred-check list or placeholder command can exit zero. Proof success must not substitute for criterion evidence.

8. **“Record what you could not confirm” versus “an answer of ‘not checked’ is not done.”**  
   It is unclear whether honest uncertainty blocks acceptance.

   > An unconfirmed current criterion blocks done. A check explicitly owned by a later stage may remain deferred, with its owner and expected confirmation recorded; do not present it as completed evidence.

9. **“Find every interaction … including ones the plan did not list.”**  
   I could turn one step into a system-wide redesign.

   > Trace the interactions affected by this step and those required for its criteria. Handle issues within the assignment; report newly discovered work outside it through revise.

10. **“Write no tests” versus “A throwaway probe … is allowed.”**  
    An assertion-based probe is still a test in ordinary language.

    > Do not add permanent test cases or suites in this stage. Run existing checks; temporary probes in RUN/scratch are allowed.

11. **“Code … or `item_scope.behavioural(item paths)`.”**  
    An item-level predicate can classify a document-only step as a code step. Conditional lint obligations also need reassessment if implementation discovers a necessary code change. Use actual step applicability; acknowledge that the item predicate is a conservative fallback.

For the senior-engineer considerations, **retain the eight categories**. None needs another top-level split. Strengthen their boundaries instead:

| Concern | Current coverage | Specific adjustment |
|---|---|---|
| Security and trust | Authority, secrets and permissions appear, but trust handling is implicit. | **Interactions:** identify untrusted inputs, permitted actors/actions, validation, and sensitive outputs. **Operations:** secret and permission lifecycle. |
| Backward compatibility | Mostly implicit in “keep what works working.” | **Interactions / State:** compatibility with existing consumers, artifacts, configurations, and stored state. |
| Concurrency | Duplicate delivery and partial state changes are covered; conflicting simultaneous changes are not. | **State:** ordering, atomicity, concurrent updates, and recovery where applicable. |
| Performance | Cost and limits appear under Operations. | **Operations:** applicable capacity/latency limits. **Proof:** observations supporting any performance claim. |
| Error handling | Already covered across Interactions, State and Operations. | Keep it; distinguish user/system response, recovery, and diagnostic information. |
| Feature flags | Not explicit; not universally needed. | **Deploying:** staged activation or another reversible rollout mechanism when required. Do not mandate flags. |
| Observability | Explicitly covered. | **Operations:** what an operator can diagnose. **Proof:** what demonstrates current criterion satisfaction. |
| Documentation | HOME write-backs are explicit; user/operator handoff is weaker. | **Whole step:** documentation required by current criteria. Record changed usage/operations for the later document stage. |
| Accessibility | Explicitly covered in Interactions. | Require relevant observations under Proof when this step has a human interaction. |

Keep **Build** separate from **Proof**: producing a valid artifact and demonstrating acceptance are different obligations. Keep **State** separate from **Interactions**: compatibility, migration, and recovery deserve attention beyond interface contracts.

`CODE_CRAFT` should supply detailed guidance underneath these considerations. Do not make the implementer produce a second parallel self-assessment. State once:

> Apply CODE_CRAFT where this step changes code; report its relevant outcomes through the eight considerations.

For order, use **a short sequence around a checklist**:

> Read the assignment and anchors → inspect existing behavior and examples → resolve scope, authority and design gaps → implement and check → compare final work with constraints → record results and write-backs.

The eight considerations are questions revisited during that sequence, not eight implementation phases. State and deployment risks often need resolving before building.

Place exact criterion text and operative anchor excerpts near the step assignment. Keep section locators beside the relevant consideration. Missing sections should say what absence means:

> `(not recorded; determine applicability—absence is not permission or evidence that the concern is covered)`

For length, cut repetition rather than obligations:

- Keep planning provenance and slot-filling mechanics in the design document, outside the executable packet.
- Define completion once. Let the final `/until-loop` invocation explicitly reference this packet’s **Done when**, rather than restating a slightly different contract.
- Put full anchor locators in one place; use IDs and short section names elsewhere.
- Keep long-form references as lookup material, separate from the initial reading requirements.
- Replace repeated self-grading language with the single final comparison above.
- Preserve the step display, accepted-step summaries, deferred work, quoted commits, and final `/until-loop`. Those directly address context loss and the binding owner decisions.