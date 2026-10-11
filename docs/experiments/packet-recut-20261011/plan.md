# plan: re-cut draft (worker A)

## 1. Goal (R1)

Build the dependency plan and the work-item queue: write the plan to FEATURE/plan.md, structure decisions to
HOME/architecture.md, and return the ordered queue in `work_items` and the load-bearing assumptions in `assumptions`.

## 2. Duty

1. Reopen the accepted intake, discovery, research, spec and test-strategy results, RUN/notes/discovery.md,
   RUN/notes/research.md, RUN/notes/current-system-baseline.md, FEATURE/spec.md, HOME/test-strategy.md and the
   decision sections HOME/README.md links. Sort the open gaps into researchable unknown contracts, owner or access
   gaps, and known setup prerequisites, and name the first consumer each gap affects. When one boundary is blocked,
   keep independent research and conditional planning eligible under their own prerequisites.
2. Write the plan in FEATURE/plan.md backward from the desired outcomes to their producers (Dependency-planning
   guidance). Order readiness, implementation, integration and release work so no consumer runs before its
   prerequisites. Give each item ready and done conditions, its candidate scope, the check that proves it, its
   authority boundaries and its correction route. The plan implies no unrun test and no authorized external
   operation.
3. Apply Initial-plan reconciliation to HOME/architecture.md, HOME/spec.md, the non-functional requirements and the
   State and data assessment. Map each applicable obligation, and every acceptance criterion, to its work item,
   prerequisites, observing test and release or recovery conditions, or record a reasoned exclusion or an open need.
   Write the mapping in FEATURE/plan.md ## Reconciliation and each item's `context`. A filled template is not proof.
4. Carry the initial baseline's evidence and classification into `evidence_refs` and each affected item's `context`
   (Initial repository baseline guide). Put a foundation repair, setup prerequisite or missing-test bootstrap in the
   earliest feasible item before the feature that depends on it. Its readiness evidence is the original check's
   passing rerun, or, when none can rerun, a separately recorded passing characterization of unchanged application
   behaviour after the bootstrap. Keep the original no-suite observation. An expected-RED repair may start its own
   work. A bootstrap may make only the smallest test-only harness, dependency or configuration edits, and it tests
   unchanged application behaviour. Its completion alone neither makes the repository healthy nor unblocks dependent
   features without that passing evidence. A failure of unknown relatedness stays blocking. Do not waive or absorb an
   unrelated failure.
5. Plan each missing test facility as its own prerequisite work item (Reusable test facilities). Record in the
   consuming item's `context` its definition locator, readiness gap and owner.
6. Include the environment preparation and delivery work as items. Ask for delivery authority at the first concrete
   boundary that needs it (Delivery authority guidance).
7. When the work adds code or stored data, write a short Namespace and data map in FEATURE/plan.md
   ## Namespace and data map, and put each item's entries in its `context`:
   - list every execution environment the code runs in or reaches: the local checkout, a remote runtime behind an MCP
     server, API or CLI, a hosted platform, each service of a multi-service system;
   - for each, map its current library structure (packages, modules, prefixes, exported surfaces, where similar
     responsibilities live), how it resolves names, and what the new code will import, be called by or share names
     with (Namespace and placement guidance). Inspect a remote environment through its interface, not the local tree;
   - decide a home namespace and visibility for each new responsibility across all items, so later items extend the
     layout, and how new names, including names shared between services, avoid collisions;
   - decide how each environment stores the data (Schema and storage guidance): the existing and destination schema,
     their owner and change mechanism, or for a new schema its store, keys, field types, constraints, relationships,
     version and migration, and its storage policy (authority, retention, sensitive fields, quotas).
   Plan no empty package or directory for a hypothetical future.
8. Decide the interaction structure (Interaction design guide) and record each decision as an AD-<n> in
   HOME/architecture.md:
   - placement: the simplest one that meets the requirements in HOME/spec.md. A single-user game or tool with no
     shared or lasting state runs entirely in the client. Add server state, identity, a store or a live channel only
     for a requirement that needs it, and use the runtime's native storage, identity, cache, workflow and
     notification services before building your own;
   - safeguards, at every placement: the personal-data handling in HOME/spec.md, a server-side check on every action
     by a caller the product does not control, validation and abuse limits on anonymous input, and a record of every
     background or asynchronous failure that reaches whoever must act;
   - channels: for each hop, the lightest channel that meets the stated freshness: request/response; polling at a
     stated interval; email or platform notification for changes hours apart; server-sent events, WebSockets or
     platform push only when seconds matter. After a push, a poll gap or a reconnect, read the authoritative state
     back. Cache only derived data, in the runtime's cache, with an expiry that matches the allowed staleness. State
     each channel's and cache's cost against the runtime's quotas.
   Then write a Design basis in FEATURE/plan.md ## Design basis. Recheck the guide's relevant subsections instead of
   copying a prior plan. Give the baseline and delta; the state, event and connection agreements and their planned
   recovery checks (including a crash after acknowledgment but before processing accepted work, where it applies);
   deployment fit; and source and check locators. For UI, give the component, interaction and skin premises, the
   selected design guidance locator with its identity, version or digest (or the named fallback), and each meaningful
   async cue with its purpose and reduced-motion alternative, or an explicit static choice. For a human-facing UI,
   default to an ambitious, highly interactive design: name the rich interactions planned (direct manipulation,
   inline editing, live preview, keyboard paths, animated transitions) and any scaled back, with its user, target or
   accessibility reason. For a consequential UI choice, give the guide's ambition, the reuse, evolve or upgrade
   decision, rough effort and benefit, and the compatibility check. Reuse accepted choices for unaffected scope and
   the existing design and test facilities. Put each affected item's locators and short decisions, including planned
   check locators, in its `context` and in `evidence_refs`. Start no nested review.
9. In HOME/architecture.md, record each structure or technology decision as AD-<n> (choice, why, alternatives,
   status) under ## Decisions, move a decision that no longer holds under ## Superseded, and update ## Stack,
   ## Structure, ## Conventions and ## Interfaces and boundaries where this plan changes them.
10. Give each work item a compact `context` that a fresh reader can act on, with the full source locators in
    `evidence_refs` and longer notes in FEATURE/plan.md. For each applicable entry give its locator, decision,
    rationale, scope and revalidation condition:
    - each convention, canonical test or example, verified skill, MCP or library contract, environment or delivery
      decision, and approved exception;
    - a selected local skill: the repository index or selection-note locator and what to revalidate for this item's
      inputs. No fit is a current observation; later items reread the index for skills learned during this run;
    - the test strategy: the HOME/test-strategy.md locator and the item's compact test decisions (execution and
      target location, fixture and suite choices, what to recheck);
    - the baseline and spec: the exact sections, gaps and revalidation conditions of
      RUN/notes/current-system-baseline.md and FEATURE/spec.md;
    - the service decisions: the exact current note locators and revalidation conditions;
    - the readiness checks of the item's prerequisites.
    A later packet does not replay earlier stages' references, so the item carries them. Copy no source transcript,
    invent no decision ledger, and do not treat a context summary as proof.
11. Plan the before and after decisions and the preservation checks from the baseline and FEATURE/spec.md. Plan
    durable documentation work when recovered knowledge exists only in run notes.
12. Map accepted service choices to the affected schema and config, query and cache, worker and status, business and
    UI, logging, test and operator files, only as needed (Service discovery guidance), and order their prerequisites
    and checks.
13. For each work item, state in its `context` the module format its files use (for example CommonJS or ESM, with or
    without a package.json) and the loadable seam its tests import, so a test can load before the implementation
    exists.
14. Before you fix the item IDs, check the draft once for coherent increments. Split a deliverable that needs
    different prerequisites, exposes a useful intermediate contract or artifact, or can be implemented and checked on
    its own. Merge fragments that share prerequisites and an implementation boundary without a useful checkable state
    of their own. A small change may use one item; there is no minimum count, quota or scaffolding item. Keep
    preservation and negative requirements as checks on the affected item unless they need their own change. Each
    item already gets step planning, validation, build, test, documentation, verification and commit: do not add
    those as items. Keep a cross-item or later-environment check at the boundary where it is due.
15. For each dependency, name the supplier and the concrete output or state the consumer needs. Authoring an artifact
    differs from applying it in a running environment: a runtime integration check may need both, independent code
    authoring does not. A shared topic, list order or shared file alone is not a dependency. Record independent
    branches and file or resource conflicts in FEATURE/plan.md; an isolated workspace alone does not make parallel
    work safe. ShipLoop runs the queue one item at a time, so put each prerequisite before its consumers.
16. Return the load-bearing assumptions in `assumptions`, starting from RUN/notes/research.md ## Assumptions and the
    discovery notes. Give each exactly the fields the template shows for its disposition (evidenced: `evidence`;
    probed: `check`, `evidence`; open: `check`, `consumer`, `reason`). An open assumption's `consumer` is the ID of
    the work item in `work_items` that settles it.
17. Return the complete ordered `work_items`, each with only `id`, `title` and optional `context`. Cover every approved
    outcome, including required independent work with no downstream consumer. FEATURE/plan.md alone does not fill the
    queue.
18. Keep in `summary` and FEATURE/plan.md the key reference statements, decisions, constraints and acceptance context
    of this pass. Consolidate upstream material for a fresh execution context as supporting references, not as a
    replacement assignment or a restatement of the request. Each item's ready and done conditions stay its only
    execution directive. Put in `evidence_refs` FEATURE/plan.md, HOME/architecture.md, any execution graph and every
    source used; an unrecorded conversation is not a handoff.
19. Run the dependency audit of the Backchain planning guide on every route. You may also request one Backchain
    `plan` / `draft` through `source-aware-native`, the only call route. Nothing refuses a plan without it and
    ShipLoop cannot see whether the child ran, so say in `summary` which route you took and why. If you request it:
    - every resource in the printed "Selected Backchain and Until Loop resources" block is required. A `MISSING`
      entry is the blocker to report; never substitute a sibling, cache or other install;
    - Backchain runs the selected Until Loop with `Backchain standalone Until Loop binding: <binding-id>`. The child
      is plan-only: it may change the candidate plan and permitted planning companions, and may not commit, push,
      merge, run the project or broaden scope. Until Loop owns the callback handle, progress, the review gate,
      recovery and the terminal transition; copy none of it;
    - write the child's start contract with `required_trivial_reviews: 0` and this exit condition verbatim,
      appending only case-specific clauses: One complete dependency review/fix/check cycle has run; every finding
      of that cycle is repaired within the edit bounds; every `Confirm by` clause on a step this cycle may change
      meets the planning guide's Outcomes rule; the printed `backchain-check` is ok on the final candidate and its
      receipt is cited; final candidate-specific domain evidence is saved. A pass that completes that cycle reports
      `exit_assessment: satisfied` even when it repaired the candidate, and no second review runs. Put the line
      `Backchain passes: one` beside the binding marker in the child request. Keep the contract within the state
      budget;
    - record the binding id, candidate and receipt paths in `evidence_refs` and the affected items' `context`;
    - report done only with the child's exact `complete` receipt saved, with the final candidate's identity and its
      domain evidence. A nonterminal, unresolved or incompatible child leaves this stage incomplete. The draft is a
      candidate; ShipLoop owns acceptance.
    Run the printed `backchain-check` after each candidate revision. It reads a candidate graph in Backchain's plan
    schema (Backchain SKILL.md, "Plan document shape"), not a prose plan. A failure is a finding; cite its receipt in
    `evidence_refs`. A structural plan, a planned check or an experiment that merely ran is not execution evidence.
    Keep material findings visible in `summary`. Carry the selected requirement sections and test locators through
    the plan and the items' `context`.

## 3. Checked by

- An `assumptions` entry with a key its disposition does not take, an evidence file that does not exist, or an open
  assumption whose `consumer` is not a work item in `work_items`.
- A change to HOME/ that loses an earlier R-<n> or AD-<n> ID, or that looks like a credential.

## 4. Guides to keep

- Dependency-planning guidance (backchain-planning.md#dependency-audit): item 2.
- Initial-plan reconciliation (requirements-definition.md#initial-plan-reconciliation): item 3.
- State and data assessment (requirements-definition.md#state-and-data-change-assessment): item 3.
- Delivery authority guidance (delivery-authority.md#ask-at-the-first-concrete-boundary): item 6.
- Namespace and placement guidance (coding-practices.md#namespaces-and-placement): item 7.
- Schema and storage guidance (coding-practices.md#schema-and-storage): item 7.
- Service discovery guidance (service-discovery.md#development-handoff): item 12.
- Reusable test facilities (repeatable-test-suites.md#reuse-and-define-test-facilities): item 5.
- Drop (never cited): Current-system baseline guide, Git-history investigation guide, Decision carry-forward guidance,
  UI planning ownership when applicable. Unsure about Git-history investigation guide and Decision carry-forward
  guidance: their sections (project-knowledge.md#investigate-git-history-for-planning,
  #carry-context-into-the-new-plan) back items 1 and 10; if the owner wants them cited, add "(Decision carry-forward
  guidance)" to item 10 and "(Git-history investigation guide)" to item 1.
- Policies the prose names: Initial repository baseline guide (item 4), Interaction design guide (item 8). The
  Backchain block prints the Backchain planning guide (item 19).

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| P1 Dependency-aware plan from outcomes back to producers. | Item 2 |
| P2 Order readiness, implementation, integration, release so consumers wait. | Item 2 |
| P3 Ready/done, scope, check evidence, authority, correction routes. | Item 2 |
| P4 Plan implies no unrun tests or authorized operations. | Item 2 |
| P5 Reopen the discovery evidence handoff. | Item 1 |
| P6 Distinguish unknown contracts, owner/access gaps, setup prerequisites. | Item 1 |
| P7 First affected consumer; independent work stays eligible. | Item 1 |
| P8 Initial-plan reconciliation over architecture, spec, NFRs, state and data. | Item 3 |
| P9 Map obligations to item, prerequisites, test, release/recovery, or exclusion. | Item 3 |
| P10 Preserve the mapping in plan notes, context, evidence_refs; a template is not proof. | Item 3 (FEATURE/plan.md ## Reconciliation). Unsure: the heading is new; name another if FEATURE/plan.md has a fixed outline |
| P11 Module format and loadable test seam per item. | Item 13 |
| P12-16 DESIGN_BASIS_DUTY (recheck, design basis contents, UI, ambition, consequential choices, reuse). | Item 8, second half (FEATURE/plan.md ## Design basis) |
| P17 Submit to the mandatory Improve handoff. | CUT (R3, R7) |
| P18 Plan stays a draft until that loop completes; dependent work waits. | CUT (R3): the graph enforces it |
| P19 Link the plan and any execution graph in evidence_refs so Improve reviews them. | Item 18 (link kept; "so Improve reviews" CUT, R3) |
| P20 No extra review stage; do not claim the loop ran. | CUT (R3): an Improve mention. Unsure: "do not schedule an extra review stage" also forbids adding a review work item; item 14 already forbids duplicating stages as items |
| P21 Keep these as ordinary notes, not new result fields. | Item 18 (the fields are the template's) |
| P22 Use the Initial repository baseline guide. | Item 4 |
| P23 Carry baseline evidence and classification into evidence_refs and context. | Item 4 |
| P24 Foundation repair or bootstrap in the earliest item, with passing rerun or characterization as readiness. | Item 4 |
| P25 Preserve the original no-suite observation. | Item 4 |
| P26 Expected-RED repair may start its own work. | Item 4 |
| P27 Bootstrap: smallest test-only edits; completion alone is not health. | Item 4 |
| P28 Unknown relatedness stays blocking; no silent waive or expansion. | Item 4 |
| P29 Retain conventions, examples, contracts, decisions, exceptions as locator plus decision, rationale, revalidation. | Item 10 |
| P30 Item-specific summary in context; locators in evidence_refs. | Item 10 |
| P31 Selected local skill: index locator and what to revalidate. | Item 10 |
| P32 No fit is current; later items reread the index. | Item 10 |
| P33 Use the Run-wide test strategy source. | Item 10 (HOME/test-strategy.md). The renderer label stays in "What you work from" |
| P34 Carry its locator and test decisions into context. | Item 10 |
| P35 Reopen the current-system baseline and change spec. | Items 1, 11 |
| P36 Before/after decisions and preservation checks. | Item 11 |
| P37 Sections, gaps, revalidation in evidence_refs and context; durable doc work. | Items 10, 11 |
| P38 Reopen the knowledge index and service decision sections. | Item 1 |
| P39 Map service choices to affected files only as needed. | Item 12 |
| P40 Order their prerequisites and checks. | Item 12 |
| P41 Note locators and revalidation in evidence_refs and context; earlier references not replayed. | Item 10 |
| P42-49 Namespace and data map (environments, structure, remote inspection, home namespace, storage, record, no empty package). | Item 7 |
| P50-53 Coherent increments: split, merge, no minimum. | Item 14 |
| P54 Preservation and negative requirements as checks. | Item 14 |
| P55 Do not duplicate inner stages as items. | Item 14 |
| P56 Cross-item checks at their boundary. | Item 14 |
| P57 Supplier and concrete output per dependency. | Item 15 |
| P58 Authoring vs applying. | Item 15 |
| P59 Shared topic, order or file is not a dependency. | Item 15 |
| P60 Independent branches and conflicts in plan notes; workspaces do not prove parallel safety. | Item 15 |
| P61 One item at a time. | Item 15 |
| P62 Prerequisites before consumers; readiness checks in context. | Items 10, 15 |
| P63 Complete ordered work_items with id, title, context; link the plan note. | Items 17, 18 |
| P64 Cover every approved outcome, including independent work. | Item 17 |
| P65 A plan note alone does not populate the queue. | Item 17 |
| P66 A small change may use one item. | Item 14 |
| P67 Assumptions from the discovery and research notes. | Item 16 |
| P68-71 Fields per disposition. | Item 16 |
| P72 ShipLoop refuses extra keys; consumer must be a work item. | Checked by; item 16 keeps the consumer rule as a duty |
| Develop: namespaces, placement, schema and storage up front. | Item 7 |
| Test: a missing test facility is its own prerequisite work. | Item 5 |
| Deploy: environment preparation and delivery work; delivery authority at the first boundary. | Item 6 |
| INTERACTION_DESIGN 1 (stage list, use the guide). | Item 8; stage list CUT (R3) |
| INTERACTION_DESIGN 2 (actors, channels, events, ownership; baseline/delta). | Item 8 (design basis: baseline and delta, agreements); established at discovery item 13 and research item 10 |
| INTERACTION_DESIGN 3 (UI design guidance and identity). | Item 8 |
| INTERACTION_DESIGN 4 (premises, async feedback, deployment fit). | Item 8 |
| INTERACTION_DESIGN 5 (prefer existing; machine interactions). | Item 8 ("native services first"); machine interactions: discovery item 13 |
| INTERACTION_DESIGN 6 (locators in item context and evidence_refs; Improve handoff; no nested review). | Item 8 (last two sentences); Improve CUT (R3) |
| INTERACTION_DESIGN 7-11 (state and information lifecycle decisions). | Decided at spec item 9; item 8 applies them ("requirements in HOME/spec.md", "personal-data handling in HOME/spec.md") |
| INTERACTION_DESIGN 12-13 (simplest placement; native services first). | Item 8 |
| INTERACTION_DESIGN 14 (safeguards at every placement). | Item 8 |
| INTERACTION_DESIGN 15-18 (channels, read back, cache, cost). | Item 8 |
| WORK_ITEM_CONTEXT 1 (compact locator, decision, rationale, scope, revalidation in notes and context; locator in evidence_refs). | Item 10 |
| WORK_ITEM_CONTEXT 2 (no transcripts, no ledger, summary is not proof). | Item 10 |
| _PLANNING_HANDOFF 1 (preserve statements, decisions, constraints, acceptance context). | Item 18 |
| _PLANNING_HANDOFF 2 (consolidate upstream material as supporting references). | Item 18 |
| _PLANNING_HANDOFF 3 (task/ready/done is the sole directive). | Item 18 ("ready and done conditions stay its only execution directive") |
| _PLANNING_HANDOFF 4 (register files and sources; unrecorded conversation is not a handoff). | Item 18 |
| TEST_FACILITY 1 (reuse before a new facility; never assume availability). | Item 5 plans the facility; the reuse-first rule is applied at test-strategy item 5. Unsure: keep "reuse before defining" in item 5 if plan may define one test-strategy did not name |
| TEST_FACILITY 2 (definition locator, interface, readiness, owner, revalidation). | Item 5 |
| TEST_FACILITY 3 (item context; Improve child's notes). | Item 5 (context); Improve CUT (R3) |
| TEST_FACILITY 4 (planning names missing work; owner builds it first). | Item 5 |
| TEST_FACILITY 5 (readiness is not execution; reopen the definition). | Test-strategy item 5 and the later stages that test. Unsure: CUT here only because plan executes nothing |
| Backchain route: follow the guide; carry sections and test locators; only `source-aware-native`. | Item 19 |
| Backchain plan call: resource gate, MISSING blocks, no substitute. | Item 19 |
| Backchain plan call: record binding id, candidate, receipts. | Item 19 |
| Backchain plan call: structural plan or experiment is not execution evidence. | Item 19 |
| Backchain plan call: "Material findings remain visible and cannot clear ordinary Improve." | Item 19 ("keep material findings visible"); Improve CUT (R3) |
| Backchain plan call: Source-aware native caller section holds the capability check, old-loop incompatibility, no-fallback. | Item 19 cites the guide; the details stay in backchain-planning.md#source-aware-native-caller |
| Backchain plan call: child is plan-only; restrictions belong to the child, "not the Improve executor's authority". | Item 19; Improve clause CUT (R3) |
| Until Loop state budget (16,384, 9,216, 6,144 bytes; files in context.resources; measure command). | Item 19 points at it; numbers and command move to "What to execute" (R2) |
| Native call: request exactly one plan/draft within scope; binding line. | Item 19 |
| _BACKCHAIN_PLAN_CHOICE (your choice; ShipLoop cannot see it; audit not optional; say the route; contract applies only if requested; backchain-check reads the plan schema). | Item 19 |
| _BACKCHAIN_PLAN_GATE_ONE (Until Loop owns the runtime; start contract with gate 0 and the exit condition verbatim; satisfied after one cycle; marker line). | Item 19, verbatim exit condition kept (test/shiploop-navigator-contract.test.py BackchainGateDocumentsTest pins it to Backchain's convergence reference) |
| Backchain terminal evidence: complete receipt, nonterminal leaves incomplete, draft is a candidate. | Item 19 |
| BACKCHAIN_CHECK. | Item 19 (the command: "What to execute") |
| Renderer: Planning phase intent "...; its Improve child evaluates whether the evidence supports it." | Goal and item 2; Improve clause CUT (R3); renderer drops the line |
| Renderer: Planning experiments guide, investigation notebook, "keep experiment prompts behind these locators". | CUT from the producer packet (R3): printed only because an Improve child follows; they belong to the Improve card |
| Renderer: "At plan, supplied work_items replaces the complete ordered queue; omission retains it." | Stays as a result-shape note in "What to execute" (it describes the field). Item 17 always supplies the queue |
| Renderer: "Revalidate the current work-item queue ... in the producer result or Improve final_result." | Item 17; the Improve final_result clause CUT (R3) |
| Renderer: HOME/architecture.md description (stack, structure, conventions, interfaces, AD-<n>, Superseded). | Item 9; propose the renderer print only the file's section list on the location line |
| Renderer: Improve line. | CUT (R3) |

Backchain modes: this draft is the default `one`. Under `converge`, item 19's start-contract bullet becomes "Until Loop
owns ... its `required_trivial_reviews: 2` gate" (today's _BACKCHAIN_PLAN_GATE_CONVERGE) and the "say which route"
sentence goes. Under `none`, item 19 becomes the spec-style audit item (spec.md item 11) with "No whole `plan`/`draft`
is requested in this run." `_backchain_guidance` keeps building these variants.

## 6. Size

- Today: 19,298 characters.
- Proposed: 14,780 characters (76%).

Measured on the default render (ask-agent, planning_review stage, backchain_passes one). Today: prompt(stage) without STAGE_RULES, plus the Develop/Test/Deploy/Tools considerations and the stage-specific renderer lines this draft folds or cuts (Planning phase intent, the environment-discovery and investigation-allowance lines, plan's experiments lines). New: sections 1-3 of this file. Exit conditions are excluded from both.
