# intake: re-cut draft (worker A)

## 1. Goal (R1)

Map the request to outcomes, boundaries and open questions, and write them in this result's `summary`, with HOME/README.md
created or updated as the index of the knowledge home.

## 2. Duty

1. Map every sentence of the request to an outcome, a boundary or an open question, and list each in `summary`. The
   boundaries are the repository and run scope, explicit user constraints, authority limits, consumers and entry
   points, and known risks. Mark each statement as a fact or an assumption.
2. For each open question, write in `summary` who answers it (discovery, or a recorded default), what it blocks, and
   what discovery must establish before planning, testing, implementation or release is trusted.
3. List in `summary` the permitted source hints for discovery: team or workspace, channels, internal sites and docs,
   private repositories, owners, and ambiguous internal terms. A hint is a lead, not a verified definition or access.
   Put a sensitive locator only in an authorized knowledge home, never in ordinary or public notes. Ask no
   questionnaire for a hint that available evidence can resolve.
4. Name in `summary` where the result must become usable. A request that names the target is the grant (Delivery
   authority guidance).
5. Say in `summary` where the outcome will be visible, and when. In an isolated run the source checkout stays at its
   starting snapshot until the final return. An outcome in a deployed target (an org, a site, a store) exists only
   after release. A source-level check is not the requested outcome.
6. For a product people interact with, list in `summary` the open questions of its interaction and state model: the
   actors and how the runtime identifies them; whether state is shared across people, devices or sessions; how long
   it lives and what ends it; what must stay hidden from whom; and what the runtime already provides for each. Answer
   from the request where it says so. Otherwise record the default you take and what it rules out.
7. If this request continues an earlier run, follow Prior-run and recovery guidance instead of starting new work.
8. Create or update HOME/README.md as the index of the knowledge home: what each file answers.
9. Implement nothing and add no scope. Put in `evidence_refs` the absolute path of every file this stage wrote and
   each source it used.

## 3. Checked by

Nothing beyond the exit conditions and the shared mechanical checks.

## 4. Guides to keep

- Prior-run and recovery guidance (project-knowledge.md#new-work-versus-recovery): item 7.
- Delivery authority guidance (delivery-authority.md#ask-at-the-first-concrete-boundary): item 4.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| Establish outcome, repo and run boundaries, constraints, authority limits, consumers, risks, open questions. | Item 1 |
| Distinguish facts from assumptions; identify what discovery must establish first. | Item 1 (facts/assumptions), item 2 (what discovery must establish) |
| Retain permitted source hints and ambiguous internal terms for discovery. | Item 3 |
| Sanitize hints; sensitive locators only in an authorized knowledge home. | Item 3 |
| Hints are leads; no separate questionnaire when evidence can resolve. | Item 3 |
| State where the result will be visible and when. | Item 5 |
| Isolated run: checkout at starting snapshot; deployed outcome only after release; say both so INNER is not read as idle; a source-level check is not the outcome. | Item 5. "So a long INNER run is not read as idle": CUT: a reason, not an obligation |
| Interaction and state model open questions (actors, sharing, lifetime, hiding, runtime support). | Item 6 |
| Answer from the request; otherwise ask, naming the default and what it rules out. | Item 6. "Ask" becomes "record the default": the unattended rule (STAGE_RULES) already says to take the default and record it as an assumption |
| Do not implement or silently broaden scope. | Item 9 |
| Consideration "Deploy: Name where the result must become usable; a request that names the target is the grant." | Item 4 |
| _PLANNING_HANDOFF: preserve key statements, decisions, constraints, acceptance context in summary. | Items 1-6 (each names `summary`) |
| _PLANNING_HANDOFF: at plan and step-plan, consolidate upstream material. | CUT: another stage's guidance (R3); kept in plan item 18 |
| _PLANNING_HANDOFF: step task/ready/done is the sole execution directive. | CUT: another stage's guidance (R3) |
| _PLANNING_HANDOFF: register every produced planning file and source as an absolute path in evidence_refs. | Item 9 |
| Goal "confirm the request, boundaries and open questions". | Goal |
| Renderer: "This stage keeps these up to date: HOME/README.md." | Item 8 (the renderer line stays as the location line) |
| Renderer: Improve line | none printed today at intake |

## 6. Size

- Today: 2,330 characters.
- Proposed: 2,411 characters (103%).

Measured on the default render (ask-agent, planning_review stage, backchain_passes one). Today: prompt(stage) without STAGE_RULES, plus the Develop/Test/Deploy/Tools considerations and the stage-specific renderer lines this draft folds or cuts (Planning phase intent, the environment-discovery and investigation-allowance lines, plan's experiments lines). New: sections 1-3 of this file. Exit conditions are excluded from both.


## Tightened (pass 2)

Duty size (inline): 2,011 -> 1,485 characters (-27%). Goal: "Map the request to outcomes, boundaries and open questions in this result's `summary`."; short goal: 'map the request'.

Text now in `DUTIES['intake']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. Map each sentence of the request to an outcome, boundary or open question in `summary`. Boundaries: repository and
   run scope, user constraints, authority limits, consumers and entry points, risks. Mark each fact or assumption.
2. Each open question: who answers it (discovery or a recorded default), what it blocks, what discovery must
   establish first.
3. List discovery's source hints in `summary` (team or workspace, channels, internal sites and docs, private
   repositories, owners, ambiguous terms). A hint is a lead, not a verified fact. Put a sensitive locator only in an
   authorized knowledge home. Ask no questionnaire for what evidence can resolve.
4. Name where the result must become usable; a request that names the target is the grant (Delivery authority
   guidance).
5. Say where and when the outcome is visible: an isolated run's source checkout stays at its snapshot until the
   final return, and an outcome in a deployed target exists only after release.
6. For an interactive product, list the open interaction and state questions: actors and how the runtime identifies
   them; shared state across people, devices or sessions; its lifetime and what ends it; what stays hidden from
   whom; what the runtime already provides. Answer from the request, else record the default and what it rules out.
7. A request that continues an earlier run follows Prior-run and recovery guidance.
8. Implement nothing; add no scope. `evidence_refs`: each source used.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
