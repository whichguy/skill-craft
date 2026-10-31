# Planning frameworks A: BMAD-METHOD, GitHub Spec Kit, Kiro, cc-sdd

Researched 2026-10-30 from source files (shallow clones read directly) plus kiro.dev docs and a few third-party evaluations. Facts are cited with a URL or a `[prefix] path`. Inferences for ShipLoop are labelled **(inference)**.

## 0. Versions observed, URL prefixes, method, caveats

| Framework | Observed | Notes |
|---|---|---|
| BMAD-METHOD | **stable v6.12.4 (2026-10-14)**, branch `V6.12`, commit bab9082c. **v7 preview alpha** on default branch `main` (commit 61e01f82, 2026-10-18) and `dev` (867c546e, 2026-10-27). 54.8k stars, created 2025-04-13. | README says v7 ETA was 2026-10-16; no `v7*` tag or `V7` branch existed on 2026-10-30. `main` and `V6.12` are architecturally different (see 1.1). |
| GitHub Spec Kit | **v1.2.5 (2026-10-28)**, main commit 7370e592 (2026-10-30). 144k stars, created 2025-08-21, MIT. | `/converge` added v0.11.2 (2026-06-18); `/clarify` was formerly `/quizme`. |
| Kiro (AWS) | docs fetched 2026-10-30; the Specs page says "updated: October 15, 2026"; IDE 1.x, CLI V3. | Product source is closed. `kirodotdev/Kiro` is only an issue tracker (4.4k stars), but it contains one real generated spec I read. |
| cc-sdd | **v3.1.0 (2026-09-23)**, commit e2a0c671. 3.7k stars, MIT, created 2025-07-17. | Kiro-style SDD as 17 Agent Skills. |

URL prefixes used below (all GitHub blob paths):

- `[BM]` = https://github.com/bmad-code-org/BMAD-METHOD/blob/main/ (v7 alpha)
- `[BM6]` = https://github.com/bmad-code-org/BMAD-METHOD/blob/V6.12/ (stable)
- `[SK]` = https://github.com/github/spec-kit/blob/main/
- `[CC]` = https://github.com/gotalab/cc-sdd/blob/main/
- `[KR]` = https://github.com/kirodotdev/Kiro/blob/main/

Caveats:

- I read prompts from shallow clones; I did not run any framework.
- kiro.dev pages, Fowler, RanTheBuilder, Uvik and the arXiv abstracts were read through WebFetch's summarizing model, so treat quoted details from them as "re-verify before external use".
- Failed fetches: kiro.dev/docs/specs/concepts/ (404), /docs/specs/feature-specs/design-first/ (404; the real path is /tech-design-first/), /docs/hooks/triggers/ (404; hook types learned from a search result for /docs/hooks/types/), arXiv 2606.04967 PDF (unreadable; abstract page used), the original Reenbit benchmark (only second-hand figures exist, so excluded).
- Kiro's official pages I could fetch do not document the `tasks.md` syntax. I used a real Kiro-generated spec in Kiro's own repo and cc-sdd's Kiro-compatible template instead.

---

## 1. BMAD-METHOD

### 1.1 Two lines, and a long history of simplification

- **Stable v6.12.4** (`V6.12`) already uses `src/bmm-skills/{agents,plan,ship,v6-shims}`. Phase 4 is "a single chain: `bmad-sprint-planning → bmad-build → bmad-code-review`" ([BM] CHANGELOG.md, v6.11.0). `bmad-create-story` and `bmad-dev-story` are deprecated shims. `bmad-check-implementation-readiness` was folded into sprint-planning as a PASS/CONCERNS/FAIL readiness gate ([BM] CHANGELOG.md v6.11.0).
- **v7 alpha** (`main`) replaces `bmad-spec`, `bmad-ticket` and `bmad-correct-course` with **Sofia, the Product Owner** (`bmad-agent-po`), and adds a ticket tree: initiative, then epic, then story, all kept under `{output_folder}/{active_initiative}/`. CHANGELOG "Unreleased" says: "Sofia the Product Owner ... replaces `bmad-spec`, `bmad-ticket` and `bmad-correct-course`". Docs: [BM] docs/plan/set-up-the-ticket-tree.md.
- Older shapes, for context. v6.0.3 had four phases plus a parallel Quick Flow track, and `check-implementation-readiness` ([BM6 history] https://github.com/bmad-code-org/BMAD-METHOD/blob/v6.0.3/docs/reference/workflow-map.md). The v6.0.3 roster had Scrum Master Bob, QA Quinn, Quick-Flow Barry and Paige; v6.3.0 (2026-04-09) merged Bob, Quinn and Barry into Developer Amelia ([BM] CHANGELOG.md). `bmad-help` replaced `workflow-init` and workflow tracking in 6.0.0-Beta.1, and the "Scale Adaptive System" doc was removed in 6.0.0-alpha.22 ([BM] CHANGELOG.md). Scale adaptation now lives in "Size follows the intent" ([BM] docs/plan/choose-a-planning-path.md): edit directly, one Build, an epic of many Builds, or a project of many epics.
- **Script-rendered prompts (the ShipLoop pattern).** Every v7 skill's `SKILL.md` is a stub that runs `uv run .../render_skill.py` and says "The command prints the skill's workflow: follow it", with a `HALT: <reason>` output meaning report the reason and stop ([BM] skills/bmad-build/SKILL.md). v6.11 added "immutable, content-addressed snapshots" of exactly what ran, with a manifest of hashes ([BM] CHANGELOG.md v6.11.0).
- Repo policy worth noting ([BM] AGENTS.md): prompt text "an agent reads in full on every run", so "do not add instructions for exotic cases"; "Prefer deleting an instruction to hedging it"; "Automated tests assert outcomes produced by deterministic code."

### 1.2 Phases, gates, personas (v7 alpha)

The docs say the planning skills are "independent tools, not stages. Pick the ones the gap calls for" ([BM] docs/plan/choose-a-planning-path.md). The order is advisory, but the typical flow is:

| Step | Skill (agent, menu code) | Gate / approval |
|---|---|---|
| Idea shaping, optional | `bmad-brainstorming` (Mary the Analyst, BP); `bmad-forge-idea`; `bmad-prfaq` (WB) | User picks the exit: hardened, killed or clearer ([BM] skills/bmad-forge-idea/SKILL.md). |
| Evidence, optional | `bmad-deep-recon` (Analyst MR/DR/TR/TS/CR/UV) | One hard "plan gate" before research ([BM] skills/bmad-deep-recon/references/codebase.md). |
| Brief / PRD / UX | `bmad-product-brief` (CB), `bmad-prd` (John the PM, PRD), `bmad-ux` (Sally, CU) | Fast or Coaching path; reviewer gate (rubric walker plus lenses as parallel subagents) at Finalize ([BM] skills/bmad-prd/SKILL.md). |
| Architecture | `bmad-architecture` (Winston, CA) | Writes an "architecture spine" of invariants (AD-n); deterministic `lint_spine.py`, then reviewer gate ([BM] skills/bmad-architecture/references/reviewer-gate.md). |
| Requirements and slicing | **Sofia** `bmad-agent-po`: SPEC, TICKETS, REFINE, BOARD, VALIDATE, REPLAN, STORE | "A yes approves what was shown", and on the repo store that yes is also the approval to commit ([BM] skills/bmad-agent-po/workflow.md). Fresh-context subagent validation of every draft `tickets.toml` ([BM] skills/bmad-agent-po/references/validate.md). |
| Implement one story | `bmad-build` (Amelia, BD) or unattended `bmad-build-auto` | CHECKPOINT 1 (approve the plan); `READY FOR DEVELOPMENT` standard ([BM] skills/bmad-build/workflow.md, step-02-plan.md). |
| Review | `bmad-code-review` (CR), lenses inside Build | Triage with a verdict per finding; loopback capped at 5 ([BM] skills/bmad-build/step-04-review.md). |
| Close the epic | `bmad-retrospective` (ER), then Sofia's closure check | Verdict Accepted / Accepted-with-open-items / Rejected, judged against the epic's Requirements and Done when, with a source reference on every finding. Any unfinished ticket forces a machine verdict of rejected; a human decision overrides ([BM] skills/bmad-retrospective/references/acceptance-verdict.md). |

The Scrum Master, QA and Quick-Flow personas no longer exist. QA is a Developer menu item (`bmad-qa-generate-e2e-tests`); the Test Architect is a separate module ([BM] docs/reference/skills-and-agents.md).

**Stable v6.12.4 differs.** Planning ends with `bmad-spec` (SPEC.md) plus optional `stories.yaml`, then `bmad-create-epics-and-stories`, then `bmad-sprint-planning` (readiness gate, then `sprint-status.yaml`), then Build per story ([BM6] docs/plan/choose-a-planning-path.md and src/bmm-skills/plan/).

### 1.3 Prompts and templates that drive each step (file → what it does)

- **`bmad-prd` SKILL.md** ([BM] skills/bmad-prd/SKILL.md). Discovery order is "Brain dump → Stakes calibration → Working mode → mode-scoped work". Its stance is "Elicitation, not direction", and it forbids "quizzing the user through a tree of LLM-shaped choices". Finalize is an 8-step sequence: memlog audit, input reconciliation, reviewer pass, triage open items, polish, handoffs, close.
- **`bmad-agent-po/references/spec.md`** ([BM] skills/bmad-agent-po/references/spec.md). Turns any input into a container's Requirements and Constraints. Eight "Spec Law" rules, including "Requirements say WHAT, not HOW" and "Requirement ids are never reused or renumbered". Two self-validation passes: Coherence, then Preservation. `Open question:` and `Assumption:` lines replace guessing.
- **`slice.md`** ([BM] skills/bmad-agent-po/references/slice.md). Epic rules: "Done is one runnable check"; "Split, never shrink"; tests go in every story; the first entry is a tracer bullet; an epic of more than three entries closes with a "Refactor sweep"; 8-12 stories is "typical, not a limit" ([BM] skills/bmad-agent-po/customize.toml).
- **`validate-checks.md`** ([BM] skills/bmad-agent-po/references/validate-checks.md). Sections Ticket, Set, Tree, Dependencies, Closure. Example test (paraphrased): a builder must be able to write each story's acceptance criteria from the epic, the entry and its references; if not, the epic is what gets fixed.
- **`bmad-build` workflow.md and step-01..05** ([BM] skills/bmad-build/). Step 1 clarify and route, step 2 plan, step 3 implement, step 4 review, step 5 present. The plan template is [BM] skills/bmad-build/plan-template.md.
- **`bmad-build-auto`** ([BM] skills/bmad-build-auto/step-02-plan.md): "No human interaction: do not ask questions or wait for approval in this step."
- **Architecture spine template** ([BM] skills/bmad-architecture/assets/spine-template.md). Each AD has Binds, Prevents and Rule. The inclusion test (paraphrased): fix a decision only if two units built independently one level down could choose incompatibly, the call is non-obvious, and it is a real trade-off ([BM] skills/bmad-architecture/SKILL.md).
- **Readiness gate (stable)** ([BM6] src/bmm-skills/plan/bmad-sprint-planning/references/readiness-gate.md). One question: "could a developer implement these epics without inventing decisions nothing records?" Verdicts PASS / CONCERNS / FAIL. It traces requirements to stories and stories back to intent, in both directions, and surfaces conflicts between artifacts.
- **`bmad-advanced-elicitation`** ([BM] skills/bmad-advanced-elicitation/SKILL.md, assets/methods.csv). 71 named methods in 12 categories (collaboration 12, core 11, creative 9, advanced 8, risk 7, technical 6, and others). `scripts/pick_methods.py` serves the catalog so it never enters context. The menu offers 5 category-diverse methods plus Reshuffle, List all and Proceed. "Never change the work unless the user accepts the proposal."
- **`bmad-party-mode`** ([BM] skills/bmad-party-mode/SKILL.md). Roundtable of installed agents or custom personas; modes `session`, `auto`, `subagent`, `agent-team`. It is user-invoked ("until the user signals done").

### 1.4 Artifacts: names, lifetime, location (v7)

Everything lives under `_bmad-output/initiative-<slug>/` (configurable) ([BM] docs/plan/set-up-the-ticket-tree.md; tree in [BM] skills/bmad-agent-po/workflow.md).

| Artifact | Lifetime | Notes |
|---|---|---|
| `initiative-<slug>.md`, `epic-<slug>.md` | **Living**; the ticket is "the spec at its altitude" | Requirements as `R<n> (source ids)` lines, Constraints, Done when, Boundaries, Notes with `Decision:` / `Assumption:` / `Open question:` / `Source conflict:`. Template: [BM] skills/bmad-agent-po/assets/ticket-template.md |
| `.memlog.md` per ticket | **Living**, append-only, canonical | Written only via `memlog.py`. Requirements are re-derived from the memlog plus `sources:`. Hand edits "are overwritten on the next run". |
| `tickets/tickets.toml` | Living; table order is build order | Entry keys: id, type, title, description, `verify`, `covers`, `after` ("prerequisites only, not sequence"), `hitl`, `risk`, `unknown`, `refine`, `plan_checkpoint`, `done_checkpoint` ([BM] skills/bmad-agent-po/assets/tickets-template.toml) |
| `story-<slug>-plan.md` | **Per-story**, kept as evidence | The build's plan plus `status`, `baseline_revision`, `risk`, review logs. Entries need no story file. |
| `prd-*`, `brief-*`, `ux-*`, `architecture-*` (spine), `research-*` | Per-run folders, adopted as `companions:` | AD ids and R ids are stable, never renumbered. |
| `deferred-work.md` (interactive Build) / a `deferred:` list in the plan frontmatter (Build Auto) | Living backlog of deferred findings and split-off goals | [BM] skills/bmad-build/step-04-review.md; skills/bmad-build-auto/step-04-review.md |
| `AGENTS.md` managed block | **Long-lived** | From `bmad-project-context`; each line verified, provenance line with date and SHA ([BM] AGENTS.md). |
| `epic-<slug>-retrospective.md` | Per-epic record | [BM] tools/ticket-tree-rules.md |
| Stable v6.12: `SPEC.md` (five-field kernel: Why, Capabilities, Constraints, Non-goals, Success signal), `stories.yaml`, `sprint-status.yaml` | Living / living / living | [BM6] src/bmm-skills/plan/bmad-spec/SKILL.md, bmad-sprint-planning/sprint-status-template.yaml |

### 1.5 Question-asking

**How questions are generated:**

- **Documents (brief, PRD, UX, architecture).** There is no fixed question list. The skill opens with a brain dump, reads the stakes, then offers a working mode ([BM] skills/bmad-prd/SKILL.md; skills/bmad-product-brief/SKILL.md):
  - **Fast path**: "batch remaining gaps into one or two consolidated questions" and draft with `[ASSUMPTION]` tags.
  - **Coaching path**: open-ended, section by section; the brief skill says "Push back when an answer is thin".
  - Architecture's load-bearing calls "are shown, not silently made": alternatives with a lean, and the user chooses.
- **Sofia**: "ask only what is unsettled, with the answer I would pick" ([BM] skills/bmad-agent-po/customize.toml). Epic refinement is "one message sized to the initiative"; on a small initiative it is a single question: does the epic need anything before its stories? Sparse input gets a choice between a best-effort draft (every gap becomes an `Open question:`) and a guided walk ([BM] skills/bmad-agent-po/references/spec.md).
- **Forge idea**: "one question at a time, in dependency order", includes its own best answer, finds discoverable answers itself ([BM] skills/bmad-forge-idea/SKILL.md).
- **`bmad-build`**: no interview in step 1; step 2 says "Do not ask the human during investigation" and investigates the code and ticket first. Only unresolved choices become an `## Open Questions` list, "one entry per gap: the choice, the options, and what each option means"; the run HALTs for answers, which are written into the frozen intent block and the entry deleted. If the answers expose a new gap, ask again ([BM] skills/bmad-build/step-02-plan.md).
- **`bmad-build-auto`** (unattended): if several defensible readings give observably different outcomes, it HALTs with status `blocked`, condition `intent gap`, listing the questions ([BM] skills/bmad-build-auto/step-02-plan.md).
- **`bmad-project-context` interview**: "Never ask what a scan could answer"; "Ask recall questions, not review lists"; batches of at most eight ([BM] skills/bmad-project-context/SKILL.md).
- **Script-enforced unanswered questions**: an entry's `unknown = "..."` ("one-sentence user question; `tickets.py next` blocks the entry until removed") ([BM] skills/bmad-agent-po/assets/tickets-template.toml).

**Counts / batching:** no hard cap in the docs. Fast path is 1-2 batched questions; coaching and forge are one at a time; project-context at most 8 per batch.

**Who answers:** the user for scope, preference and intent. The repo or web for facts (project-context scans, deep-recon, PRD research subagents). `bmad-build` answers from the ticket, companions, repo and history before asking.

**Write-back:** `memlog.py append --type decision|assumption|question|...` as it happens; the doc is distilled from the memlog at finalize; open questions end as `Open question:` or `Assumption:` lines in Notes, and a resolved one is a dated `Decision:` line (even a declined suggestion is recorded so it is not re-asked: [BM] skills/bmad-agent-po/references/validate.md).

### 1.6 Research, spikes, experiments

- **`bmad-deep-recon`** ([BM] docs/plan/research-a-decision.md; skills/bmad-deep-recon/). Types market, domain, technical, competitive, user-voice, academic-lit, plus a "select" shape; modes Draft (write a prompt for your own deep-research tool), Process (file and check a finished report), Run (research in session at `quick|standard|deep`, verification `normal|high|max`). It is triggered by "a decision" the research must support.
- **Codebase mode** ([BM] skills/bmad-deep-recon/references/codebase.md). This is the most relevant pattern for a "key questions" harness:
  - The ask becomes numbered factual questions of four shapes: `how does X work`, `why is X this way`, `where does X live`, `what touches X`.
  - The questions are written so they do not state the intent; researcher subagents see only the questions, because a researcher who knows what is being built reports what should be instead of what is.
  - The user approves the question set at "the plan gate", the only hard stop.
  - Roles: locators, analyzers, historians (git history for `why`), verifiers.
  - Output is a document where every claim cites `path:line (symbol) @ sha` or `sha "subject" #pr`, with no recommendation in it.
  - A script, `recon_kit.py anchors`, re-finds every citation; claims get a verification ledger (`tally`).
  - Decisions found in history are offered as ADRs, written only when approved.
  - `bmad-build` re-checks research claims against current code before relying on them.
- **Spikes**: ticket type `spike`, time-boxed, acceptance includes "The answer is recorded, with its consequences, where the waiting tickets can find it" ([BM] skills/bmad-agent-po/assets/spike-template.md). Sofia offers "plan a spike first when only code can answer it" ([BM] skills/bmad-agent-po/references/slice.md). A spike is added "when you ask for one" ([BM] docs/plan/set-up-the-ticket-tree.md).
- **Prototypes**: "The method has no prototype phase and needs none"; after a prototype the user must decide throw away, keep, or drop ([BM] skills/bmod-method/help/prototyping.md).
- PRD discovery spawns web-research subagents by default; architecture verifies named technologies' current versions on the web and recommends a starter for greenfield ([BM] skills/bmad-architecture/SKILL.md).

### 1.7 Task decomposition and traceability

- **Granularity**: a story is "one step toward the epic's Done when, sized for one agent session"; build plans target a "single user-facing goal" within 900-1600 tokens, and neither limit is a gate ([BM] skills/bmad-build/workflow.md). Docs size a session at about 500 lines changed in a handful of files ([BM] docs/build/build-a-change.md). Build routes `oneshot` for 100 lines or fewer, else `full` ([BM] skills/bmad-build/customize.toml).
- **Dependencies**: `after` in `tickets.toml` is prerequisites only; order is table order. `tickets.py` computes readiness (`next`, `status`) and flags `cycle`, `drift`, `unpinned_after`, `undeclared_after`, `order_conflict`. A prerequisite is met when done or in review ([BM] skills/bmad-agent-po/scripts/tickets.py docstring). Separately, fresh-context subagents check "missing prerequisites `tickets.py` cannot see" ([BM] skills/bmad-agent-po/references/validate.md).
- **Inside a story plan**: tasks written as `FILE -- ACTION -- RATIONALE`, ordered by dependency; ACs in Given/When/Then; an I/O and Edge-Case Matrix; a Code Map of what to reuse and what not to change ([BM] skills/bmad-build/plan-template.md). A "Matrix Test Audit" requires every matrix row to have a covering test that actually ran: "A covering test that exists but did not run ... counts as missing" ([BM] skills/bmad-build/step-03-implement.md).
- **Traceability**: source ids → initiative `R<n> (FR-2)` → epic `R<n> (parent R3)` → entry `covers = ["R1"]` → plan AC "(R<m>)" → retrospective verdict against Requirements and Done when. Closure uses implementation evidence, "not child status" ([BM] skills/bmad-agent-po/references/validate-checks.md).
- **Parallelism**: there are no `[P]` markers; independent epics run in parallel when "boundaries are explicit" and "each stream needs an owner" ([BM] docs/plan/choose-a-planning-path.md).

### 1.8 Verification gates before and after implementation

- Before: validate checks on the draft breakdown (Set / Tree / Dependencies) with the model fixing the Dependencies section first; PRD and spine reviewer gates; `READY FOR DEVELOPMENT` (actionable, logical, testable, complete, sufficient, coherent); CHECKPOINT 1; plan token check; `tickets.py` readiness. Stable: readiness gate.
- After: review lenses. Quick is a single lens; thorough is Blind Hunter, Edge Case Hunter, Verification Gap and Intent Alignment auditors, as context-free subagents ([BM] skills/bmad-build/customize.toml). Triage assigns exactly one verdict per finding (`high|medium|low|false|maybe-false`) with evidence, then routes it: `intent_gap` / `bad_plan` loop back, `patch` is auto-fixed, `defer` goes to `deferred-work.md`. Findings are logged to a Review Triage Log; loopbacks past 5 HALT ([BM] skills/bmad-build/step-04-review.md).
- Unattended: "Using subagents when instructed is mandatory" and never run them detached ([BM] skills/bmad-build-auto/workflow.md).

### 1.9 Cross-session state and brownfield

- State: the plan's `status` (draft, ready-for-dev, in-progress, in-review, built, done, blocked, dropped) is the only status; "No skill moves a ticket past `built`"; `done` is set by the user or an orchestrator via `tickets.py mark` ([BM] tools/ticket-tree-rules.md). `baseline_revision` is recorded before any code change. Stable: `sprint-status.yaml` with preserve-never-downgrade merging by `sprint_plan.py`.
- Brownfield: `bmad-document-project` is deprecated; "Build follows what it finds" ([BM] docs/existing-codebases/start-in-an-existing-codebase.md). Run `bmad-project-context` (verified AGENTS.md block), optionally `bmad-deep-recon` codebase mode and `bmad-architecture` (which "ratifies the conventions the codebase already shows"). `bmad migrate method` moves v6 trees to v7 ([BM] skills/bmad/references/migrate.md).
- The project's own admission test (docs, with external studies cited): anything "derivable from source is read live and never stored"; repo instruction files that restate derivable facts showed "no improvement in success rate and +20% inference cost" ([BM] docs/existing-codebases/theory-of-project-context.md). Those studies are about context files, not BMAD planning.

### 1.10 Evidence of effectiveness

- **BMAD itself publishes no planning benchmark.** Its `bmad-eval` doc page says "This page is being written" ([BM] docs/toolsmith/bmad-eval.md). The CHANGELOG claims blind validation of the verification-gap reviewer on seven real commits from a production HIPAA platform (project-reported, review layer only; #2535).
- **Third party:**
  - Uvik Software, Q4 2026 (page dated 2026-10-15): 50 brownfield Python tickets, claude-sonnet-5, 45+45 minute boxes. BMAD merge rate 82% (41/50), $4.23 per merged ticket, 55 min median, spec phase 43.9% of tokens, median spec 188 lines, 28 min spec time. Spec Kit 80%, Kiro 82%, OpenSpec 84%, no-spec control 72%; stated noise ±10 percentage points (https://uvik.net/spec-driven-development-benchmark/).
  - RanTheBuilder (Ran Isenberg), Feb 2026: BMAD v6.0.3, Spec-Kit v0.1.6, OpenSpec v1.2.0, one medium backend feature in Cursor with Sonnet 4.5. Scores out of 5: OpenSpec 4.00, BMAD Quick 3.74, BMAD Full 3.65, Spec-Kit 2.77. BMAD Full took about 6 days and $200; the others 1-1.5 days. The author credits BMAD's adversarial review and course-correction (https://ranthebuilder.cloud/blog/i-tested-three-spec-driven-ai-tools-here-s-my-honest-take/).
- Both are n=1 case or small-n, vendor- or hobbyist-run. Directional only.

### 1.11 Worth borrowing vs ceremony (BMAD)

**Worth borrowing (for a script-driven harness):**

1. Prompts rendered by a script with a `HALT:` protocol, and a script that owns readiness (`tickets.py next/status`, the `unknown` gate, drift/cycle detection). Same architecture as ShipLoop packets.
2. Investigate first, then batch only the leftover choices (options plus consequence) into one HALT; freeze the approved intent; unattended runs halt only on observably divergent readings.
3. Codebase "blind factual question" research with commit-pinned citations and a script that re-verifies anchors.
4. `R<n>` ids with source ids in parentheses, never reused; entry `covers`; closure judged on evidence not child status.
5. Matrix test audit ("a test that did not run counts as missing"): a script-checkable exit check.
6. Review triage that forces a verdict plus evidence on every finding and routes by cause (intent gap vs bad plan vs patch vs defer).
7. Append-only memlog as canonical memory with documents re-derived from it.
8. "Never ask what a scan could answer."

**Ceremony / no evidence:** named personas with icons and voices; party mode; the 71-method elicitation menu (user-triggered, no measured effect); brainstorming "100+ ideas"; "make them sweat" coaching; the brief → PRFAQ → PRD → UX → architecture chain for anything below organization scale (BMAD itself says skip a PRD unless several people or epics must agree); HTML keepsakes. Uvik's data shows BMAD's heavier front end cost the most tokens and minutes for no merge-rate gain over lighter tools.

---

## 2. GitHub Spec Kit

### 2.1 Stages in order, commands and gates

Documented flow ([SK] docs/reference/agentic-sdd.md): `/constitution → /specify → /clarify → /plan → /checklist → /tasks → /analyze → /implement → /converge`. README minimal flow: constitution, specify, plan, tasks, implement, converge, "Repeat implement and converge until convergence reports `Converged`" ([SK] README.md).

- "only `/speckit.specify` is strictly required before `/speckit.plan`"; clarify, checklist and analyze are optional quality gates to add when there is meaningful ambiguity ([SK] docs/reference/agentic-sdd.md).
- There are no personas; each command is a prompt file in [SK] templates/commands/*.md, executed by the user's coding agent (about 40 integrations in `src/specify_cli/integrations/`).
- **Workflow engine** ([SK] workflows/speckit/workflow.yml, workflows/ARCHITECTURE.md). The shipped `speckit` workflow is `specify → gate(approve/reject) → plan → gate → tasks → implement`. It omits clarify, analyze, checklist and converge. Step types: command, shell, slot, gate, if, switch, while/do-while, fan-out/fan-in. State is saved after each step and `specify workflow resume <run_id>` continues. It is the closest analogue to ShipLoop's script-owned graph (**inference**).
- **Side tracks as extensions** (not core): `assess` runs intake → research → define → shape → decide, verdict `go | needs-clarification | kill`, written to `.specify/assessments/<slug>/` ([SK] extensions/assess/README.md). `bug` runs assess → fix → test with verdict `verified|partial|failed` ([SK] README.md). The `git` extension owns feature branches via hooks ([SK] extensions/git/README.md).
- A bundled **`lean` preset** strips specify/plan/tasks/implement to one prompt and one artifact each ("just the prompt, just the artifact"), and its `specify` says "Make informed defaults for unspecified details" ([SK] presets/lean/README.md, presets/lean/commands/speckit.specify.md).

### 2.2 Prompts and templates

- **`/specify`** ([SK] templates/commands/specify.md, templates/spec-template.md). Short name of 2-4 words; spec dir `specs/NNN-short-name/` (or timestamp prefix); `.specify/feature.json` records the feature dir. Mandatory sections: prioritized, independently testable User Stories (P1..Pn) with Given/When/Then, Edge Cases, `FR-001` requirements, `SC-001` measurable technology-agnostic success criteria, Assumptions. After writing, it generates `checklists/requirements.md` (content quality, requirement completeness, feature readiness) and re-validates up to **3 iterations**.
- **`/clarify`** ([SK] templates/commands/clarify.md): see 2.4.
- **`/plan`** ([SK] templates/commands/plan.md, templates/plan-template.md). Technical Context (unknowns written as `NEEDS CLARIFICATION`), a **Constitution Check** ("GATE: Must pass before Phase 0 research. Re-check after Phase 1 design."), Complexity Tracking table for justified violations. Phase 0 → `research.md`; Phase 1 → `data-model.md`, `contracts/`, `quickstart.md`. Rule: "ERROR on gate failures or unresolved clarifications."
- **`/tasks`** ([SK] templates/commands/tasks.md, templates/tasks-template.md): see 2.5.
- **`/analyze`** ([SK] templates/commands/analyze.md): see 2.6.
- **`/checklist`** ([SK] templates/commands/checklist.md, templates/checklist-template.md): see 2.6.
- **`/implement`** ([SK] templates/commands/implement.md). Reads checklist state as a read-only gate: counts checked and unchecked, and asks "Do you want to proceed with implementation anyway?" if any are open. Then creates/verifies ignore files, executes phase by phase (halt on a failed non-[P] task; mark `[X]` in tasks.md).
- **`/converge`** ([SK] templates/commands/converge.md). Compares the code to spec, plan, tasks and constitution and classifies gaps `missing | partial | contradicts | unrequested`. "completion claims are not evidence", so existing tasks are re-assessed regardless of checkbox state. Its only write is appending `## Phase N: Convergence` tasks to tasks.md ("APPEND-ONLY, NEVER REWRITE"); if nothing remains the file stays byte-for-byte unchanged.
- **`/constitution`** ([SK] templates/commands/constitution.md, templates/constitution-template.md). Fills placeholders from user input or repo context, semantic-versions the constitution, emits a temporary Sync Impact Report.

### 2.3 Artifacts, lifetime, location

| Artifact | Location | Lifetime |
|---|---|---|
| `constitution.md` | `.specify/memory/` | **Long-lived**, versioned (MAJOR/MINOR/PATCH) |
| `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`, `checklists/*.md` | `specs/NNN-short-name/` | **Per feature**; what happens after delivery is the team's choice: flow-back, flow-forward (immutable record) or living spec ([SK] docs/concepts/spec-persistence.md) |
| `.specify/feature.json`, `.specify/extensions.yml`, `.specify/init-options.json` | `.specify/` | Pointers and config |
| Assessments and bug reports | `.specify/assessments/<slug>/`, `.specify/bugs/<slug>/` | Per idea / per bug |

Feature branch per spec exists only if the `git` extension is installed: the mandatory `before_specify` hook runs `speckit.git.feature` and creates `001-feature-name` or a timestamped branch; the spec directory name and branch name "are independent" ([SK] extensions/git/README.md; templates/commands/specify.md). Fowler reads branch-per-spec as treating a spec as living for one change, not a feature's lifetime.

### 2.4 Question-asking (the part most relevant to ShipLoop)

| Command | Max questions | How chosen | Format | Who answers | Write-back |
|---|---|---|---|---|---|
| `/specify` | **3** `[NEEDS CLARIFICATION]` markers total ("LIMIT: Maximum 3") | Only if the choice "significantly impacts" scope/UX, has several readings, and has no reasonable default. Priority "scope > security/privacy > user experience > technical details". Everything else: informed guess recorded under Assumptions | All questions presented together, each with an option table A/B/C/Custom and implications; reply like "Q1: A, Q2: Custom - ..." | User | Marker replaced in `spec.md`; checklist re-run |
| `/clarify` | **5 per session** (rerunnable "as many times as needed", each on a different area) | Internal scan of the spec against a 10-category taxonomy (below), each marked Clear / Partial / Missing; candidates dropped if they would not change implementation or validation, or are about tech-stack/task breakdown; if more than 5 unresolved, "select the top 5 by (Impact * Uncertainty) heuristic"; keep category balance | **Exactly one at a time**; multiple choice (2-5 mutually exclusive options) or answer in ≤5 words; leads with `**Recommended:** Option X - reasoning`; user can say "yes"/"recommended"; "Never reveal future queued questions in advance"; stop on "done" | User | After each answer: `## Clarifications` → `### Session YYYY-MM-DD` → `- Q: ... → A: ...`, then the answer is applied to the relevant section (FR, data model, NFR as measurable criterion, edge case); file saved after every answer; the requirements checklist is re-evaluated; final coverage table Resolved / Deferred / Clear / Outstanding |
| `/checklist` | **3** generated questions, up to 2 follow-ups (max 5) | "Derive up to THREE initial contextual clarifying questions (no pre-baked catalog)" from signals in the prompt and spec; archetypes: scope refinement, risk prioritization, depth calibration, audience framing, boundary exclusion, scenario-class gap; skip any already answered | Q1-Q3 with option tables A-E | User | Shapes the checklist content |
| `/plan` Phase 0 | n/a | Every `NEEDS CLARIFICATION` in Technical Context, every dependency, every integration becomes a research task | Research agents | **Model research** | `research.md`: Decision / Rationale / Alternatives considered |

`/clarify` taxonomy ([SK] templates/commands/clarify.md): Functional Scope & Behavior; Domain & Data Model; Interaction & UX Flow; Non-Functional Quality Attributes (performance, scalability, reliability, observability, security/privacy, compliance); Integration & External Dependencies; Edge Cases & Failure Handling; Constraints & Tradeoffs; Terminology & Consistency; Completion Signals; Misc/Placeholders (TODOs and ambiguous adjectives like "robust").

Questions have a written quality bar: a full interrogative ending in `?`, never a topic label or requirement id as the prompt, plus one plain-language "Why it matters" sentence. If skipped, the command warns that "downstream rework risk increases".

Methodology doc: "Forcing Explicit Uncertainty Markers" stops the LLM from "making plausible but potentially incorrect assumptions" ([SK] spec-driven.md).

### 2.5 Task decomposition and traceability

- tasks.md: Phase 1 Setup, Phase 2 Foundational (blocking), Phase 3+ one phase **per user story in priority order** with story goal and "Independent Test", final Polish. Strict line format `- [ ] T001 [P] [US1] Description with file path`. `[P]` means different files and no dependency on incomplete tasks. Dependency graph, parallel examples per story, MVP-first strategy ([SK] templates/tasks-template.md).
- "Tests are OPTIONAL: Only generate test tasks if explicitly requested" (opposite of BMAD and cc-sdd defaults). Field constraints from data-model.md are quoted verbatim into task text.
- Ordering within a story: tests (if requested) → models → services → endpoints → integration. Dependencies are expressed as phase order, `[P]` markers, and a dependency section, not as a machine-readable graph.
- Traceability is by ids: `FR-###` / `SC-###` → tasks (by explicit ids or keyword inference in `/analyze`) → `[US#]` labels. Custom checklists require ≥80% of items to carry a trace reference or a `[Gap]` / `[Ambiguity]` / `[Conflict]` / `[Assumption]` marker.
- For large features, scope each `/implement` run to avoid context exhaustion, delegate `[P]` tasks to subagents, or split into a "spec of specs" ([SK] docs/concepts/complex-features.md).

### 2.6 Verification gates before implementation

- Spec quality checklist `checklists/requirements.md` (created by `/specify`, kept in sync by `/clarify`), max 3 repair iterations.
- **Constitution Check** at plan start and after design; violations need a Complexity Tracking entry.
- **`/checklist` = "Unit Tests for English"**: "Checklists are UNIT TESTS FOR REQUIREMENTS WRITING". Items ask about requirement quality (completeness, clarity, consistency, measurability, coverage), never "verify the button works"; IDs `CHK001+`; `[x]` is reviewer-owned, and the command "MUST NOT mark generated items `[x]`".
- **`/analyze`**: "STRICTLY READ-ONLY". Loads spec, plan, tasks, constitution progressively; six detection passes (duplication, ambiguity, underspecification, constitution alignment, coverage gaps, inconsistency); severity CRITICAL/HIGH/MEDIUM/LOW; constitution conflicts are "automatically CRITICAL"; max 50 findings; stable ids so reruns are "deterministic"; coverage table per requirement key; metrics; offers remediation only on approval.
- `/implement` checklist gate; `/converge` afterwards.

### 2.7 State and brownfield

- State: checkboxes in `tasks.md`; `.specify/feature.json`; optional git branch/commits (git extension hooks `before_*`/`after_*`); checklist files. Workflow runs persist `RunState` and resume.
- Brownfield ([SK] docs/guides/existing-projects.md): `specify init --here --force`; write a constitution only from "principles already true for the repository"; pick "a bounded first change"; the new `spec.md` "defines the change you intend to make", not a retroactive spec of existing behavior; run clarify, plan against the repo, tasks, analyze, implement, converge.

### 2.8 Evidence of effectiveness

- No vendor-published benchmark. The README links talks only.
- Uvik Q4 2026: Spec Kit 1.0 80% merge (40/50), $3.33 per merged ticket, 44 min median, spec phase 34.0% of tokens, median spec 132 lines, 18 min. Size effect (best spec arm vs control): 1-2 file tickets no gain (85% vs 85%); 3-5 files +15 points (85% vs 70%); 6+ files 80% vs 50% (+30). Bug-fix and refactor tickets: 0 gain; feature and data-pipeline tickets: +30. Specs covering ≥6 of 8 checklist items (goal, scope, inputs/outputs, data changes, edge cases, acceptance tests, constraints, no-change list) merged 89.3% vs 60.0% (https://uvik.net/spec-driven-development-benchmark/; vendor, ±10 pp noise).
- RanTheBuilder Feb 2026 (Spec-Kit v0.1.6): lowest score of the three tools, 2.77/5. Paraphrasing the post as relayed by the fetch summarizer: `/clarify` gives structured multiple-choice elicitation and templates flag unknowns instead of guessing, but the produced code did not faithfully match the spec's intent, and Spec Kit has no built-in code review.
- Fowler/Böckeler (Oct 2025, anecdotal): spec-kit was "repetitive, verbose, tedious to review" ("I'd rather review code than all these markdown files"); the agent ignored research notes about existing classes and regenerated them as duplicates; the constitution was sometimes over-applied; checklists act as a definition of done but, being interpreted by the AI, are not guaranteed to be respected (paraphrases; https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html). No measurements.
- arXiv 2606.04967 taxonomy compares Spec Kit, OpenSpec, BMAD, GSD, Spec Kitty, Reversa; it finds "a lack of benchmarks for the full process" (https://arxiv.org/abs/2606.04967).

### 2.9 Worth borrowing vs ceremony (Spec Kit)

**Worth borrowing:**

1. `/clarify`'s mechanics: taxonomy scan → coverage map → Impact×Uncertainty queue → hard cap → one question at a time → each with a recommended answer and a one-sentence stake → incremental write-back in place + dated Q→A log + final Resolved/Deferred/Clear/Outstanding table. Directly scriptable (the coverage status table and the Q→A log can be validated by a script).
2. `/specify`'s "cap the blockers, guess the rest, record Assumptions" policy.
3. `NEEDS CLARIFICATION` in plan → Phase 0 research task per unknown → Decision/Rationale/Alternatives (questions drive research).
4. "Unit tests for English" with trace markers, reviewer-owned checkboxes, and `/implement` reading checkbox counts read-only.
5. `/analyze`: read-only, deterministic ids, coverage table, severity rubric, constitution as authority.
6. `/converge`: "completion claims are not evidence", append-only gap tasks, repeat until "Converged".
7. The workflow engine (YAML steps, gates, persisted state, resume).
8. Assess track: "Evidence Against the Idea" section is mandatory; `go` requires adequate evidence else `needs-clarification` ([SK] extensions/assess/README.md).

**Ceremony / no evidence:** the nine-article constitution (Library-First, CLI mandate...) in the methodology doc, reported as over-applied; 8+ markdown files per feature; mandatory section templates; branch numbering; hook boilerplate in every command. Uvik shows no gain for 1-2 file tickets; the project's own `lean` preset concedes the point.

---

## 3. Kiro (AWS)

### 3.1 Stages and gates

(kiro.dev/docs/specs/, /feature-specs/, /feature-specs/requirements-first/, /feature-specs/tech-design-first/, /bugfix-specs/, /quick-spec/, /plan/, /analyze-requirements/, /correctness/, /best-practices/; all fetched 2026-10-30)

- **Spec types**: Feature Spec, Bugfix Spec, Quick Spec; plus **Plan mode** (conversational, not saved). Kiro asks whether you are building a Feature or fixing a Bug; for features you pick Requirements-First (Requirements → Design → Tasks) or Design-First (Design → Requirements → Tasks). The best-practices page says the workflow cannot be switched once a spec is started; create a new spec and copy content over.
- **Gates**: each document passes through an approval gate; if you are not satisfied you edit it or ask for changes and Kiro regenerates it until you approve. The docs' flowcharts call these "Happy?" checkpoints (kiro.dev/docs/specs/feature-specs/). Quick Spec runs "without approval gates" between phases (kiro.dev/docs/specs/quick-spec/). Optional **Analyze Requirements** runs after requirements and before design.
- **Bugfix Spec**: `bugfix.md` with Current / Expected / Unchanged behavior, then `design.md` (root cause, fix approach, properties to test), then tasks with property-based tests.
- **Execution**: run one task or "Run all", which builds a dependency graph and groups independent tasks into waves: "Waves execute sequentially; tasks within a wave execute concurrently."
- **Hooks**: `.kiro/hooks/*.json`; spec-task triggers `PreTaskExec` (can block with exit code 2) and `PostTaskExec` exist on IDE and CLI V3 (from a search result for kiro.dev/docs/hooks/types/; I did not read the page itself).
- **Steering** (`.kiro/steering/`): `product.md`, `tech.md`, `structure.md`, plus custom files; inclusion modes `always | fileMatch | manual | auto` via front matter; workspace beats global; AGENTS.md supported; `#[[file:...]]` references (kiro.dev/docs/steering/). Whether generating steering analyzes the repo or asks questions is not stated.

### 3.2 Artifacts and format

Location `.kiro/specs/<name>/` (confirmed by the real sample, [KR] .kiro/specs/github-issue-automation/; the docs pages I fetched do not state the path). Per feature, in repo ("Store specs in the project repo", kiro.dev/docs/specs/best-practices/).

From the real Kiro-generated spec in [KR] .kiro/specs/github-issue-automation/:

- `requirements.md`: Introduction, **Glossary** of named components, then `### Requirement N` with a **User Story** and **Acceptance Criteria** in EARS: "WHEN a new issue is created, THE Issue_Manager SHALL ...". Docs pattern: "WHEN [condition/event] THE SYSTEM SHALL [expected behavior]". Kiro's own pages show only that WHEN ... SHALL form; cc-sdd's `ears-format.md` documents the five standard EARS patterns (event, state, unwanted behavior, optional feature, ubiquitous) plus combined forms ([CC] tools/cc-sdd/templates/shared/settings/rules/ears-format.md).
- `design.md`: Overview, Architecture, Components and Interfaces, Data Models, **Correctness Properties** (22 numbered properties, each with "**Validates: Requirements 1.1, 5.5**"), Error Handling, Testing Strategy (unit, property-based, integration, CI).
- `tasks.md`: nested checkboxes (`- [x] 1.`, `- [ ] 2.1`), each ending `_Requirements: 6.1, 6.2_`; optional test tasks marked `- [ ]*`; property-test sub-tasks naming the property ("**Property 1: Bedrock API Invocation**"); explicit "Checkpoint" tasks; a Notes footer ("Tasks marked with `*` are optional"; "Each task references specific requirements for traceability").

Docs side: tasks have "Discrete, trackable tasks", "Clear descriptions and expected outcomes", "Dependencies between tasks" and "Optional vs required tasks"; "Sync Files" on `tasks.md` re-scans the code and marks tasks already done (kiro.dev/docs/specs/best-practices/, /requirements-first/).

### 3.3 Question-asking

Official docs do not state counts or generation rules for any of these (kiro.dev pages above):

- **Feature Specs (both workflows)**: the first draft is generated from the prompt; the user then reviews, iterates and confirms. No pre-draft interview is documented.
- **Quick Spec**: clarifying questions "up front", covering "scope, constraints, edge cases, and anything else that affects the output".
- **Plan mode**: the planner asks structured questions to refine the initial idea; the docs' example shows lettered multiple choice plus "Other", answerable as "1=a, 2=b", free-form, or skipped. The planner is read-only (files, code intelligence, grep/glob, web). The plan stays in the conversation. After approval the plan is handed to the execution agent.
- **Analyze Requirements**: after requirements exist, Kiro "reasons across your full requirement set" and streams clarifying questions into chat. Each lists the requirements involved, explains the issue in plain language and offers suggested fixes; you can type your own answer or dismiss. Resolving a question updates `requirements.md`. Checks: logical inconsistencies, ambiguities ("large files"), conflicting constraints, unstated assumptions, missing edge cases.

### 3.4 Research, decomposition, verification

- **Research**: no research phase; Design-First lets you upload diagrams or pseudocode ("High Level" vs "Low Level Design") and Kiro derives requirements. Bugfix design phase explores the codebase for root cause.
- **Decomposition and traceability**: EARS clauses → numbered requirements → design "Correctness Properties" → task `_Requirements:_` back-references → optional property-based tests. Properties map to EARS-formatted requirements, and hovering a property shows its linked requirement and task (kiro.dev/docs/specs/correctness/). Property-based testing is optional by default, IDE-only, and uses shrinking; the docs describe the result as evidence rather than formal proof.
- **State**: tasks marked in-progress/done in the UI; Sync Files; specs in git.
- **Brownfield**: steering files plus codebase reading; Bugfix "Unchanged Behavior" with `WHEN ... THE SYSTEM SHALL CONTINUE TO ...` is a built-in regression-boundary statement.

### 3.5 Evidence

- No AWS-published benchmark found. SoftwareSeni: "GSD, AWS Kiro, and Tessl have no equivalent published benchmark" (https://www.softwareseni.com/the-30-plus-framework-landscape-navigating-spec-driven-development-options-in-2026/).
- Uvik: Kiro 82% merge (41/50), $2.35 per merged ticket (cheapest of the four spec arms), 41 min median, spec phase 32.1% of tokens, 106-line median spec, 16 min; but Kiro ran in its own IDE harness, so not like-for-like.
- Fowler/Böckeler (Oct 2025, anecdotal): for a small bug Kiro made four user stories with 16 acceptance criteria, which the author likened to "using a sledgehammer to crack a nut"; Kiro's three files were easier to review than spec-kit's.

### 3.6 Worth borrowing vs ceremony (Kiro)

**Worth borrowing:**

1. **EARS** as a script-lintable requirement grammar (regex-detectable WHEN/IF/WHILE/WHERE/SHALL patterns), plus "Unchanged behavior" (`SHALL CONTINUE TO`) as an explicit regression boundary.
2. Requirement → Property → Task → test chain with machine-readable back-references (`Validates: Requirements x.y`, `_Requirements: x.y_`).
3. Analyze Requirements as a questions-from-the-whole-set pass with suggested fixes and dismiss.
4. Requirements-first vs design-first as a routing choice at intake.
5. Dependency graph → waves for execution.
6. Optional (`*`) tasks and explicit checkpoint tasks.
7. Spec-task hooks that can block (`PreTaskExec`).

**Ceremony / no evidence:** three documents for every change including small bugs (Fowler); "Happy?" approval at every document; PBT is optional and IDE-only; no published effectiveness data.

---

## 4. cc-sdd (briefly)

Kiro-style SDD as 17 Agent Skills for 8 hosts. Described as "Kiro-inspired ... Existing Kiro specs remain compatible" ([CC] README.md). Skills live in [CC] tools/cc-sdd/templates/agents/claude-code-skills/skills/ and shared rules/templates in [CC] tools/cc-sdd/templates/shared/settings/{rules,templates}.

- **Flow**: `kiro-discovery` (entry) → `kiro-spec-init` → `kiro-spec-requirements` → optional `kiro-validate-gap` (brownfield) → `kiro-spec-design` → optional `kiro-validate-design` → `kiro-spec-tasks` → `kiro-impl` → `kiro-validate-impl` (GO/NO-GO). Extras: `kiro-spec-batch` (many specs by dependency wave), `kiro-spec-quick`, `kiro-steering`, `kiro-debug`, `kiro-review`, `kiro-verify-completion`.
- **Gates**: `spec.json` records phase and `approvals.{requirements,design,tasks}.{generated,approved}` plus `ready_for_implementation`; `-y` auto-approves ([CC] .../templates/specs/init.json; skills kiro-spec-design, kiro-spec-tasks).
- **Artifacts and lifetimes** (default root `.kiro/`, configurable with `--kiro-dir`): per-spec `.kiro/specs/<feature>/{spec.json, brief.md, requirements.md, design.md, research.md, tasks.md}`; long-lived `.kiro/steering/{product,tech,structure}.md` (plus optional `roadmap.md` for multi-spec work and custom steering files); editable `.kiro/settings/{rules,templates}/` that hold the generation rules ([CC] README.md "Customization"; templates under tools/cc-sdd/templates/shared/settings/). `design.md` carries a required File Structure Plan that drives task `_Boundary:_` annotations; `tasks.md` also holds `## Implementation Notes` that carry learnings between tasks.
- **Discovery routes**: A extend existing spec, B "no spec needed", C new single spec, D multi-spec decomposition (20+ tasks), E mixed ([CC] .../kiro-discovery/SKILL.md). Step 1 is a metadata-only scan; deep context loading is delegated to a subagent returning under 200 lines, with the main context under about 500 lines; it writes `brief.md` (and `roadmap.md`) to disk before suggesting the next command ("Files on disk are the source of continuity").
- **Question-asking**:
  - Discovery works from a list of seven candidate questions, asked "sequentially (not all at once)" and prioritizing boundary discovery (who/why, outcome, boundary candidates, out-of-boundary, existing vs new, upstream/downstream, constraints). It says: "Ask only questions whose answers you cannot infer from the context already loaded".
  - Then 2-3 approaches with trade-offs and a recommendation; after the user picks, a subagent runs a viability check (maintenance, licenses, compatibility, showstoppers).
  - Requirements: "do not generate requirements that contain your own assumptions"; ask "as many questions as needed". This is the opposite stance from Spec Kit's cap-and-guess. Requirements scope test: if a criterion "can be written without mentioning any technology, it belongs in requirements" ([CC] .../kiro-spec-requirements/SKILL.md).
- **Research**: design classifies the feature (new, extension, simple addition, complex integration) and runs full discovery (web, dependencies, patterns), light discovery (integration points, escalate if risky) or none; findings go to `research.md` with Decision / Alternatives / Risks ([CC] .../rules/design-discovery-full.md, design-discovery-light.md, templates/specs/research.md).
- **Task decomposition** ([CC] .../rules/tasks-generation.md): "Order implies dependency"; phases Foundation → Core → Integration → Validation; max 2 levels; sub-tasks 1-3 hours; every executable sub-task has an "observable completion" bullet; `_Requirements:_` numeric ids only; `_Boundary:_` (component from design) and `_Depends:_` annotations; `(P)` only if boundaries do not overlap; optional tests as `- [ ]*`. `_Blocked:_` marks stuck tasks.
- **Mechanical-then-judgement gates**: requirements, design and tasks each have a review gate that runs "Mechanical Checks" first (numeric ids present, every requirement id appears in design/tasks, boundary sections populated) and then judgement review, with at most **2 repair passes** before escalating to the user ([CC] .../rules/requirements-review-gate.md, design-review-gate.md, tasks-generation.md). Design must state what the spec owns, what is out of boundary and allowed dependencies; "If the boundary cannot be explained in a few direct bullets, it is probably still too vague".
- **Implementation loop** ([CC] .../kiro-impl/SKILL.md): one sub-task per iteration; a fresh implementer subagent (TDD, feature-flag RED/GREEN) returns a parseable `## Status Report` / `- STATUS:`; a fresh reviewer returns `## Review Verdict` / `- VERDICT:`; rejected twice → implementer again, third rejection → debug subagent (`- NEXT_ACTION: RETRY_TASK | BLOCK_TASK | STOP_FOR_HUMAN`, max 2 debug rounds); selective commit per task; learnings appended to `## Implementation Notes` in tasks.md and passed to later tasks; `kiro-verify-completion` demands fresh evidence before marking `[x]`; feature-level `kiro-validate-impl` GO/NO-GO, remediation capped at 3 rounds.
- **State and brownfield**: `spec.json`, `tasks.md` checkboxes, `roadmap.md` (spec list with dependencies); `kiro-steering` bootstraps `product/tech/structure.md` from the codebase and syncs drift; `kiro-validate-gap` writes gap analysis to `research.md`.
- **Evidence**: none quantitative. The philosophy note ([CC] docs/guides/why-cc-sdd.md) is argument only and says it is not for solo work that fits one session. I found no third-party benchmark of cc-sdd (Uvik tested Kiro, not cc-sdd).
- **Worth borrowing:** discovery routing with "no spec needed" as a first-class route; metadata-first scan and subagent summary budget; `brief.md` written before suggesting the next step; boundary-first terminology carried from discovery to tasks; mechanical checks before judgement and a bounded repair loop; parseable status/verdict blocks (the same idea as a ShipLoop callback); `verify-completion` with fresh evidence; `Implementation Notes` learning propagation.
- **Ceremony / no evidence:** three approval states per spec, 17 skills, per-task fresh implementer plus reviewer plus debugger for small work, claims about "faster at team scale" without data.

---

## 5. Cross-framework comparison for "ask key questions about the prompt"

| | Taxonomy / coverage map | Cap | Cadence | Default offered | Unattended behavior | Where answers go |
|---|---|---|---|---|---|---|
| Spec Kit `/clarify` | 10 categories, Clear/Partial/Missing | 5 per session, rerunnable | one at a time | recommended option plus reason | n/a (interactive) | dated Q→A bullets plus edited sections |
| Spec Kit `/specify` | implicit priority order | 3 markers | batch | option table | informed guess plus Assumptions | markers replaced |
| BMAD docs | none fixed; stakes plus form-factor probes | none | Fast: 1-2 batched; Coaching: open-ended | `[ASSUMPTION]` tags; "answer I would pick" | headless: gaps become `Open question:` / `Assumption:`; build-auto HALTs on `intent gap` | memlog, then Notes lines |
| BMAD build | whatever investigation cannot settle | none | one batch, HALT | options plus consequences | HALT blocked | frozen intent block |
| BMAD project-context | "what no scan reaches" | ≤8 per batch | batch | n/a | n/a | ledger, AGENTS.md |
| cc-sdd | 7 candidate boundary-first prompts, skipped when inferable | no cap in discovery; requirements: "as many as needed" | sequential | 2-3 approaches with a recommendation | questions are skipped when inferable; `-y` only auto-approves phase approvals | brief.md / requirements.md |
| Kiro | not documented | not documented | Plan mode MC; Analyze streams | suggested fixes | Quick Spec asks up front, no gates | requirements.md |

Which questions go to the user vs model research:

- Spec Kit: scope/UX/security preferences → user; tech unknowns in plan → research agents.
- BMAD: preferences and scope → user; repo facts → scans/deep-recon/subagents; "a scan could answer" is a defect to ask.
- cc-sdd: "Skip questions that steering documents already answer"; technical research → subagents.

Research triggers: Spec Kit (every unresolved `NEEDS CLARIFICATION` or dependency in Technical Context), cc-sdd (feature classification), BMAD (a decision, or a ticket `unknown`/spike, or "only code can answer it").

---

## 6. Evidence summary (all of it is weak, and most of it vendor- or hobbyist-run)

| Source | Design | Result | Caveats |
|---|---|---|---|
| Uvik Software SDD Benchmark, Q4 2026 (https://uvik.net/spec-driven-development-benchmark/) | 50 brownfield Python tickets (20 small, 20 medium, 10 large), claude-sonnet-5, blind senior reviewer, 45-min spec + 45-min build boxes | Merge: OpenSpec 84, Kiro 82, BMAD 82, Spec Kit 80, none 72. Review defects per merged ticket: Kiro 0.39, OpenSpec 0.40, BMAD 0.49, Spec Kit 0.57, none 0.86. Cost per merged ticket: Kiro $2.35, none $2.43, OpenSpec $2.71, Spec Kit $3.33, BMAD $4.23. Spec-phase tokens 28-44% of total | Staff-augmentation vendor; ±10 pp noise stated, and the 72% control trails the best arm by 12 pp and the weakest spec arm by 8 pp; page dates inconsistent (updated 2026-10-08, run 2026-10-15); Python, one model; Kiro in its own IDE; raw CSV claimed but not checked by me |
| RanTheBuilder (Feb 2026) | one backend feature, Cursor plus Sonnet 4.5; BMAD v6.0.3, Spec-Kit v0.1.6, OpenSpec v1.2.0; 13 scored dimensions | OpenSpec 4.00, BMAD Quick 3.74, BMAD Full 3.65, Spec-Kit 2.77; BMAD Full about 6 days and $200 vs 1-1.5 days for the rest | n=1, subjective, old versions |
| Fowler/Böckeler (Oct 2025) | hands-on, Kiro and spec-kit | qualitative critique: verbosity, review burden, agent ignored notes | no measurements |
| arXiv 2606.04967 (Jun 2026) | taxonomy of 6 frameworks | notes missing benchmarks for the full process | no empirical results |

Nothing in the four frameworks' own repos measures planning quality or question-asking effectiveness. The only measured link to "asking key questions" is Uvik's 8-item spec-completeness finding (≥6 items: 89.3% merge vs 60.0%; group sizes not published).

---

## 7. Mapping to ShipLoop (inference, not sourced fact)

ShipLoop planning stages and what each framework offers:

- **intake** (map request to outcomes/boundaries/open questions): kiro-discovery's metadata-only scan and route A-E including "no spec needed"; Spec Kit `/specify`'s 3-marker cap with Assumptions; `/clarify` taxonomy as the checklist for what intake must classify; Uvik's 8 completeness items as a minimal intake checklist (goal, scope, I/O, data changes, edge cases, acceptance tests, constraints, no-change list).
- **discovery** (inspect repo, baseline tests, environment.md): BMAD project-context's admission test and "never ask what a scan could answer"; managed block with date and SHA and re-verification on refresh; Spec Kit's "constitution from repo evidence, not invention".
- **research** (resolve consequential unknowns): BMAD deep-recon codebase mode (blind factual questions, plan gate, anchors script); Spec Kit plan Phase 0 (question → research task → Decision/Rationale/Alternatives); BMAD `unknown` gate on a work item; assess's "Evidence Against" section.
- **spec** (R-n plus acceptance lines): BMAD stable `R<n>` with source ids; Kiro EARS; Spec Kit independently testable prioritized stories and FR/SC ids; "Unchanged behavior".
- **test-strategy**: Kiro properties derived from requirements with back-references; BMAD I/O matrix plus matrix test audit; Spec Kit "unit tests for English" for requirements quality before tests for code.
- **plan**: BMAD slicing rules (tracer bullet first, "Done is one runnable check", "Split, never shrink"); cc-sdd mechanical checks plus bounded repair; Spec Kit per-story independent test; Kiro waves.
- **prepare** (readiness): BMAD readiness question; `/analyze` read-only coverage table; cc-sdd validate-gap.
- **per work item (step-plan → test-spec → build)**: bmad-build's investigate-first plan and frozen intent; cc-sdd's parseable status/verdict blocks and `verify-completion`; `/converge`'s append-only gap tasks.

Loop caps seen (data points only; your memory notes say ShipLoop loops are unbounded and any limit needs an owner decision): Spec Kit 3 spec-validation iterations, 5 clarify questions, 3 markers, 50 analyze findings; BMAD review loopback 5; cc-sdd 2 repair passes, 2 debug rounds, 3 remediation rounds.

## 8. Top ideas to borrow (full URLs)

1. **Clarify queue with coverage taxonomy, hard cap, a recommended answer per question, and in-place dated write-back** — https://github.com/github/spec-kit/blob/main/templates/commands/clarify.md (with the cap-and-guess policy in https://github.com/github/spec-kit/blob/main/templates/commands/specify.md).
2. **Blind factual question sets for research** (four question shapes, plan gate, fresh-context researchers, commit-pinned citations, script-verified anchors, no recommendation) — https://github.com/bmad-code-org/BMAD-METHOD/blob/main/skills/bmad-deep-recon/references/codebase.md; paired with "never ask what a scan could answer" in https://github.com/bmad-code-org/BMAD-METHOD/blob/main/skills/bmad-project-context/SKILL.md.
3. **Investigate first, then ask only the leftover choices (options plus consequence), freeze the approved intent; unattended halts only on observably divergent readings** — https://github.com/bmad-code-org/BMAD-METHOD/blob/main/skills/bmad-build/step-02-plan.md and https://github.com/bmad-code-org/BMAD-METHOD/blob/main/skills/bmad-build-auto/step-02-plan.md.
4. **Script-checked traceability and readiness with mechanical checks before judgement, and a bounded repair loop** — https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/templates/shared/settings/rules/tasks-generation.md and design-review-gate.md (same folder); BMAD `tickets.py` + `unknown` gate https://github.com/bmad-code-org/BMAD-METHOD/blob/main/skills/bmad-agent-po/assets/tickets-template.toml; Kiro's real sample showing `Validates: Requirements` and `_Requirements:_` https://github.com/kirodotdev/Kiro/tree/main/.kiro/specs/github-issue-automation.
5. **Route by size and shape at intake, with "no spec" as a legitimate route** — https://github.com/gotalab/cc-sdd/blob/main/tools/cc-sdd/templates/agents/claude-code-skills/skills/kiro-discovery/SKILL.md; evidence for why: Uvik size buckets (1-2 files no gain, 3+ files gain) https://uvik.net/spec-driven-development-benchmark/; BMAD "Size follows the intent" https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/plan/choose-a-planning-path.md.

Also noted but not top five: `/converge` ("completion claims are not evidence", append-only gap tasks) https://github.com/github/spec-kit/blob/main/templates/commands/converge.md; Spec Kit workflow engine https://github.com/github/spec-kit/blob/main/workflows/ARCHITECTURE.md; BMAD review triage https://github.com/bmad-code-org/BMAD-METHOD/blob/main/skills/bmad-build/step-04-review.md.
