# spec: re-cut draft (worker A)

## 1. Goal (R1)

Define the required behaviour and its acceptance criteria: write each requirement as R-<n> in HOME/spec.md, and this
run's added, modified and retired IDs with their basis in FEATURE/spec.md.

## 2. Duty

1. Start from HOME/spec.md (quoted below), the research and discovery results and
   RUN/notes/current-system-baseline.md. Keep every R-<n>: change a requirement in place, and move a dropped one under
   ## Retired with its reason. Keep unaffected requirements as they are.
2. Write each requirement under HOME/spec.md ## Requirements as R-<n>, with its acceptance criteria inside it
   (Behavior-model guidance): the behaviour, its boundaries, its error behaviour and the consumer outcome. Give each
   criterion positive, failure and boundary expectations, the consumer surface where it is observed, and how it will
   be confirmed. Split independently verifiable clauses. Keep bundled behaviours visible when they share one ID.
3. Number requirements R-<n> only. A choice of structure or technology is not a requirement: record it as an AD-<n>
   decision in HOME/architecture.md ## Decisions, never in HOME/spec.md. A product decision in the spec never uses
   the AD- prefix.
4. Map every request outcome to at least one criterion (Behavior traceability guidance). Keep approved scope. Write
   each unresolved prerequisite or user decision in FEATURE/spec.md as open, not hidden in implementation detail.
5. In FEATURE/spec.md, list the IDs this run adds, modifies and retires. For each, give its request or decision basis,
   the concrete preserved and changed behaviour, its source-section locators and its evidence limits, and mark the
   implementation and checks still pending.
6. Assess non-functional requirements under HOME/spec.md ## Non-functional requirements (Requirements definition
   guide): operating conditions, measurable bounds or observable criteria, verification method, a justified
   exclusion, or a target still unresolved. Invent no target. Record a material requirement conflict in `summary` as
   open; it keeps dependent work unready.
7. Apply the State and data assessment: write the affected resources, target identities, before and after invariants,
   recovery, and the applicable checks and unknowns in FEATURE/spec.md.
8. For each selected service boundary, specify verifiable contracts (Service discovery guidance): current authority,
   freshness versus revocation, incremental state preservation, async completion and recovery, and owned event
   coverage. Mark an inapplicable concern in one line. Add no service to fill a template.
9. Decide the state and information lifecycle (Interaction design guide), in proportion to the request, and write
   each decision as a requirement in HOME/spec.md. For each piece of state: its owner and where it lives; who may read
   it (information one user must not see, such as an opponent's hidden game state or another person's record, stays
   off that user's client; information a lone user could only misuse against themselves may stay there); how
   simultaneous changes resolve; what ends it (finished, abandoned, expired) and what removes it; the runtime quotas
   it meets. For personal or secret data: where it is shown, stored and logged, how long it is kept, how it is
   removed. Map each to what the runtime already offers. Add no identity, sharing or persistence the request does not
   call for. When the request leaves one open, record your default as an assumption in `summary`. For affected UI,
   state the component, interaction and skin premises and truthful async feedback as consumer-visible behaviour.
10. Before you submit, fix any of these in HOME/spec.md or FEATURE/spec.md:
    - an example or expected result that cannot be replayed exactly: name the concrete inputs, values, identifiers
      and sample interactions;
    - an expected result that a weaker stand-in would pass: a hardcoded value, a missing assertion, a title-only
      test, an absent required name;
    - a documented command that does not run what it claims on the target runtime: run it once and record the exit
      code and the cases it executes;
    - a requirement, test ID or case dropped or weakened against the prior accepted version;
    - a claim about what the runtime, platform or a library can do that a decision depends on, with no
      primary-documentation source or probe result: check it, and correct the spec where it is wrong.
11. Request a Backchain `review` / `audit` only for a material prerequisite ambiguity, a pending or corrective
    dependency, or an acceptance gap (Backchain planning guide). It is read-only, one pass, changes no candidate and
    completes no parent action. On a material finding you may request exactly one `repair` / `revise` within your
    edit bounds:
    - it needs every loop resource on the Loop resources line; a MISSING one blocks it, and no other install
      substitutes;
    - put the line `Backchain passes: one` beside the binding marker in the child request;
    - keep its start contract within the state budget, measured with the printed command;
    - a forbidden revision, a nonterminal child or an unresolved finding leaves this stage incomplete: do not report
      done.
    Run the printed `backchain-check` after each candidate revision; a failure is a finding. Cite its receipt in
    `evidence_refs`. The only call route is `source-aware-native`.
12. A complete spec establishes criteria, not implementation or test success. Put in `evidence_refs` HOME/spec.md,
    FEATURE/spec.md, and each requirement section and source you used.

## 3. Checked by

- A change to HOME/ that loses an earlier R-<n> or AD-<n> ID, or that looks like a credential.

## 4. Guides to keep

- Behavior-model guidance (behavioral-requirements.md#behavior-model): item 2. Today's text never cites it; item 2 now
  does.
- Behavior traceability guidance (behavioral-requirements.md#traceability-and-review): item 4. Today's text never
  cites it; item 4 now does.
- State and data assessment (requirements-definition.md#state-and-data-change-assessment): item 7.
- Service discovery guidance (service-discovery.md#verification): item 8.
- Drop: Current-system baseline guide (current-system-baseline.md#planning-and-review-handoff). Unsure: item 1 reads
  the baseline; keep the label if the owner wants the handoff rules beside it.
- Policies the prose names: Requirements definition guide (item 6), Interaction design guide (item 9). Backchain
  planning guide (item 11) is printed by the Backchain block.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| S1 Define behaviour, boundaries, criteria, NFRs, error behaviour, consumer outcomes. | Items 2, 6 |
| S2 Independent positive, failure, boundary expectations before coding. | Item 2 |
| S3 Preserve approved scope; mark unresolved prerequisites or decisions explicitly. | Item 4 (FEATURE/spec.md) |
| S4 Number requirements R-<n> only. | Item 3 |
| S5 Structure/technology is AD-<n> in architecture.md; spec never uses AD-. | Item 3 |
| S6 Reconcile the delta: preserve, add, modify, retire with basis. | Items 1, 5 |
| S7 Retain accepted intent outside run notes; pending work explicit. | Items 2, 5 (HOME/spec.md and FEATURE/spec.md are durable) |
| S8 NFR assessment: conditions, bounds, methods, exclusions, unresolved targets. | Item 6 |
| S9 Invent no target; no dependent work ready with material conflicts open. | Item 6 |
| S10 State and data assessment: resources, identities, invariants, recovery; checks and unknowns. | Item 7 |
| S11 Separate verifiable clauses and surfaces; bundled behaviours visible. | Item 2 |
| S12 Definition completion is criteria, not implementation or test success. | Item 12 |
| S13 Read the prior current-system baseline and accepted requirements. | Item 1 |
| S14 Define the delta with preserved/changed behaviour; locators and limits for planning and Improve. | Item 5. "and Improve": CUT (R3) |
| S15 Service boundaries: authority, freshness vs revocation, state preservation, async, events. | Item 8 |
| S16 Service discovery guidance makes them verifiable; mark inapplicable briefly. | Item 8 |
| S17 Planning review focus lead "(the Improve child applies these ...)". | Item 10 lead. Improve mention CUT (R3); the `planning_review: none` swap row for this lead becomes unneeded |
| S17 focus condition 1 (replayable examples). | Item 10 |
| S17 focus condition 2 (weaker stand-in). | Item 10 |
| S17 focus condition 3 (documented command runs what it claims). | Item 10 |
| S17 focus condition 4 (dropped or weakened ID or case). | Item 10 |
| S17 focus condition 5 (capability claim without source or probe). | Item 10 ("correct the plan" becomes "correct the spec") |
| Develop: behaviour, error handling, consumer outcomes before any code. | Item 2 |
| Test: positive, failure, boundary expectations per criterion. | Item 2 |
| Deploy: consumer surface where each criterion is observed. | Item 2 |
| Renderer (knowledge home): spec.md is the living spec; keep every ID; change in place; Retired with reason; refuses a lost ID; FEATURE/spec.md lists IDs added, modified, retired. | Items 1, 5; the refusal: Checked by. Propose the renderer drop the `stage == "spec"` line in shiploop_knowledge_home.stage_lines |
| Renderer: Planning phase intent "Reconcile the request with existing requirements; verifiable functional and non-functional criteria; preserve unaffected intent." | Goal, items 1, 2, 6; renderer drops the line |
| Renderer: Improve line | CUT (R3) |
| INTERACTION_DESIGN 1 (stage list; use the guide). | Item 9. Stage list CUT (R3) |
| INTERACTION_DESIGN 2 (actors, channels, events, lifecycle, ownership; baseline/delta). | Discovery item 13 and research item 10 establish them; item 9 decides state ownership |
| INTERACTION_DESIGN 3 (UI design guidance, identity or fallback). | Discovery item 13 records it; plan item 8 (design basis) carries it |
| INTERACTION_DESIGN 4 (component, interaction, skin premises; async feedback; deployment fit). | Item 9 (premises, async feedback); deployment fit: plan item 8 |
| INTERACTION_DESIGN 5 (prefer existing; machine interactions). | Item 9 ("map to what the runtime offers"); machine interactions: discovery item 13 |
| INTERACTION_DESIGN 6 (locators in work-item context; Improve; no nested review). | CUT here: spec has no work items (R3); Improve CUT (R3). Plan item 8 keeps it |
| INTERACTION_DESIGN 7 "State and information lifecycle." | Item 9 |
| INTERACTION_DESIGN 8 (owner, readers, hidden info, simultaneous changes, end, quotas). | Item 9 |
| INTERACTION_DESIGN 9 (personal or secret data). | Item 9 |
| INTERACTION_DESIGN 10 (map to runtime and project layers). | Item 9 |
| INTERACTION_DESIGN 11 (no unrequested identity, sharing, persistence; default as assumption). | Item 9 |
| INTERACTION_DESIGN 12-18 (placement, channels, safeguards, cache). | Moved to plan item 8 (structure, recorded in HOME/architecture.md) |
| _PLANNING_HANDOFF 1, 4 (summary and registered material; absolute evidence_refs). | Item 12 and each item's file |
| _PLANNING_HANDOFF 2-3 (plan and step-plan only). | CUT (R3) |
| Backchain: follow the Backchain planning guide for scoped outcome, prerequisite, consumer review. | Item 11 |
| Backchain: carry requirement sections and test locators through the plan and context fields. | Item 12 (evidence_refs); spec has no work-item context |
| Backchain: only route `source-aware-native`; no embedded mode. | Item 11 ("no embedded mode": CUT, a statement about ShipLoop, not a duty) |
| Backchain audit: review/audit only for a material gap; read-only, one pass. | Item 11 |
| Backchain audit: a material finding may request one repair/revise; needs loop resources; within budget. | Item 11 |
| Backchain audit: one-pass marker line. | Item 11 |
| Backchain audit: whole plan/draft only at plan. | CUT: another stage's route (R3); spec is never offered it |
| Backchain audit: MISSING blocks; no substitute; forbidden, nonterminal or unresolved stays incomplete. | Item 11 |
| BACKCHAIN_CHECK: run after each revision; failure is a finding; cite receipt. | Item 11 (the command itself: "What to execute") |
| Until Loop state budget paragraph (16,384 / 9,216 / 6,144 bytes; long text in files; measure command). | Item 11 points at it; the numbers and the measure command move to "What to execute" beside the backchain-check command (one home per command, R2) |

## 6. Size

- Today: 9,833 characters.
- Proposed: 5,685 characters (57%).

Measured on the default render (ask-agent, planning_review stage, backchain_passes one). Today: prompt(stage) without STAGE_RULES, plus the Develop/Test/Deploy/Tools considerations and the stage-specific renderer lines this draft folds or cuts (Planning phase intent, the environment-discovery and investigation-allowance lines, plan's experiments lines). New: sections 1-3 of this file. Exit conditions are excluded from both.
