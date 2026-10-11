# research: re-cut draft (worker A)

## 1. Goal (R1)

Resolve the consequential unknowns with evidence: write each conclusion and the load-bearing assumption list to
RUN/notes/research.md, and durable facts and access needs to HOME/environment.md.

## 2. Duty

1. Start from the open unknowns in the intake and discovery results and RUN/notes/discovery.md. Revise that question
   frontier with Discovery investigation guidance: check its triggers first, and again when evidence conflicts or a
   dependency emerges. Write a triggered plan and its outcome to RUN/notes/research.md. Investigate directly only
   when no trigger applies and direct investigation suffices.
2. Resolve each consequential unknown with repository, primary-interface or other fit evidence. Record each
   conclusion in RUN/notes/research.md with its source, uncertainty, affected requirement, consumer, prerequisite,
   reuse choice and verification need. Leave an unsupported question open there with its owner and the gate it
   blocks. A recalled fact is not evidence.
3. Every environment read follows the Recursive discovery policy, with bounded experiments (Bounded research
   guidance). The investigation allowance is shared with discovery. Reaching it stops exploration, not the run: record
   the open gaps as assumptions or open items in `summary` and submit.
4. Confirm access to each delivery target with a safe, non-mutating probe (Access-readiness policy). Record each
   proven access need under HOME/environment.md ## Access and accounts as an open item: who can grant it and the gate
   it blocks.
5. For each need, evaluate in order: reuse an existing part unchanged, compose parts, augment one, build new
   (Reuse-before-build guidance). Record the choice in RUN/notes/research.md; for augment or new, say why the earlier
   options do not fit. Assess skills, MCP servers, libraries and environment patterns for actual fit and support. A
   discovered capability is not proof of use or authority to install it.
6. Resolve internal vocabulary and context gaps with Connected knowledge discovery. Open the supporting content
   rather than trusting snippets. Record authority, scope and safe source locators in RUN/notes/research.md. Keep
   evidence readers distinct from runtime dependencies, and keep private context out of public searches.
7. Research quality-target and feasibility unknowns from existing contracts and evidence. A measured baseline does not
   choose user policy.
8. Reopen RUN/notes/current-system-baseline.md and resolve its consequential gaps (Current-system baseline guide).
   Keep the prior as-of account, and append corrections and new evidence as a dated section. An observation or a
   synthetic fixture cannot choose approved product intent.
9. For affected service choices, resolve with discriminating evidence (Service discovery guidance): current state,
   zero-copy and cache tradeoffs, permission-aware invalidation, async recovery and observability gaps. Reuse native
   facilities. Record each unknown and the work that depends on it in RUN/notes/research.md.
10. Resolve the open interaction and state questions from intake and discovery (Interaction design guide): actors,
    channels, events, connection lifecycle and state ownership, and what the runtime and the project's layers offer
    for each. Record the answers in RUN/notes/research.md and runtime facts under HOME/environment.md ## Platform
    facts.
11. List each load-bearing assumption in RUN/notes/research.md ## Assumptions: one whose failure would change a plan
    decision, a consumer or an acceptance check. Mark each evidenced (its source locator), probed (the read or command
    and its saved output) or open (the check that would settle it and why it was not run). Plan builds its
    `assumptions` list from this section.
12. Before you submit, apply Discovery evidence handoff: link each consequential decision from HOME/README.md to its
    exact section and reopen it as a fresh reader would. Put in `evidence_refs` every file this stage wrote and each
    source used.

## 3. Checked by

Nothing beyond the exit conditions and the shared mechanical checks.

## 4. Guides to keep

- Discovery investigation guidance (research-loop.md#plan-the-investigation): item 1.
- Bounded research guidance (research-loop.md#recursive-discovery-and-experiments): item 3.
- Access-readiness policy (research-loop.md#early-access-readiness): item 4. Today's text never cites it; item 4 now
  does.
- Reuse-before-build guidance (research-loop.md#reuse-before-a-new-mechanism): item 5. Today's text never cites it;
  item 5 now does.
- Connected knowledge discovery (project-knowledge.md#connected-knowledge-discovery): item 6.
- Current-system baseline guide (current-system-baseline.md#evidence-and-authority): item 8.
- Service discovery guidance (service-discovery.md#select-scope): item 9.
- Discovery evidence handoff (project-knowledge.md#discovery-evidence-handoff): item 12.
- Policy the prose names: Interaction design guide (item 10). Renderer lines kept: Recursive discovery policy and
  Navigator adapter (item 3). Bounded research guidance and Recursive discovery policy point at the same anchor:
  propose the renderer print it once, under the STAGE_REFERENCES label.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| R1 Resolve material unknowns with repository, primary-interface or other evidence. | Item 2 |
| R2 Connect each conclusion to source, uncertainty, requirement, consumer, prerequisite, reuse, verification. | Item 2 (RUN/notes/research.md) |
| R3 Assess skills, MCP, libraries, patterns for fit; discovery is not use or install authority. | Item 5 |
| R4 Leave unsupported questions open. | Item 2 |
| R5 Connected knowledge discovery for vocabulary and context gaps via MCP readers. | Item 6 |
| R6 Open supporting content; retain authority, scope, safe locators in the evidence handoff. | Item 6 |
| R7 Readers distinct from runtime dependencies; no private context in public searches. | Item 6 |
| R8 Discovery investigation guidance: reuse or revise the question frontier. | Item 1 |
| R9 Triggers first and again on conflict; retain a triggered plan and outcome. | Item 1 |
| R10 Direct path only when no trigger applies. | Item 1 |
| R11 Verify the Discovery evidence handoff before passing conclusions on. | Item 12 |
| R12 Quality-target and feasibility unknowns from contracts; baselines do not choose policy. | Item 7 |
| R13 Reopen the current-system baseline and resolve its gaps. | Item 8 |
| R14 Retain the prior as-of account, record corrections separately; fixtures cannot choose intent. | Item 8 |
| R15 Service choices: state, zero-copy/cache, invalidation, async recovery, observability. | Item 9 |
| R16 Reuse native facilities; retain unknowns and dependent work in the indexed decision note. | Item 9 (RUN/notes/research.md). Unsure: today says "indexed decision note" without a file; this draft names RUN/notes/research.md and indexes the consequential decisions from HOME/README.md (item 12) |
| R17 List each load-bearing assumption in the decision note. | Item 11 |
| R18 Mark evidenced, probed or open with what each needs. | Item 11 |
| R19 The plan's assumption list starts from it. | Item 11; plan item 16 |
| R20 A recalled fact is not evidence. | Item 2 |
| Develop: reuse, compose, augment, then new; record the choice and why. | Item 5 |
| Deploy: confirm access to each delivery target early with a safe probe. | Item 4 |
| Done-when 2 (access needs recorded as open items with grantor and gate). | Exit condition; item 4 says where |
| Renderer: Environment discovery requirement "Mandatory while resolving relevant environment unknowns". | Item 3; renderer drops the line |
| Renderer: one investigation allowance spans discovery and research. | Item 3; renderer drops the sentence |
| Renderer: Planning phase intent "Resolve unknowns using existing evidence first; retain access/owner gaps and each consumer's gate." | Goal, items 2 and 4; renderer drops the line |
| INTERACTION_DESIGN 1-2 (use the guide; identify actors, channels, events, lifecycle, ownership). | Item 10. Stage list CUT (R3) |
| INTERACTION_DESIGN 3-5 (UI guidance, premises, existing capabilities). | Discovery item 13 records the baseline; decisions in spec item 9 and plan item 8 |
| INTERACTION_DESIGN 6 (work-item context; Improve handoff; no nested review). | CUT here: research has no work items (R3); Improve mention CUT (R3). Kept in plan item 8 |
| INTERACTION_DESIGN 7-11 (state lifecycle decisions). | Item 10 resolves the open questions (sentence 10: map to what the runtime offers); the decisions move to spec item 9 |
| INTERACTION_DESIGN 12-18 (placement, channels, safeguards, cache). | Moved to plan item 8 |
| _PLANNING_HANDOFF 1 (preserve statements, decisions in summary and registered material). | Items 2-11 name their files; item 12 |
| _PLANNING_HANDOFF 2-3 (plan and step-plan only). | CUT (R3) |
| _PLANNING_HANDOFF 4 (register files and sources as absolute evidence_refs). | Item 12 |

## 6. Size

- Today: 7,251 characters.
- Proposed: 4,091 characters (56%).

Measured on the default render (ask-agent, planning_review stage, backchain_passes one). Today: prompt(stage) without STAGE_RULES, plus the Develop/Test/Deploy/Tools considerations and the stage-specific renderer lines this draft folds or cuts (Planning phase intent, the environment-discovery and investigation-allowance lines, plan's experiments lines). New: sections 1-3 of this file. Exit conditions are excluded from both.
