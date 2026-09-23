---
name: backchain
description: >-
  Use when an implementation task needs a dependency-aware plan before coding:
  backward planner / backchain / precondition-first planning, dependency DAGs,
  elaborating incomplete plans, or scheduler-ready step graphs. Turns a natural-language
  coding request into a forward draft then backward-chaining enriched DAG with explicit
  unresolved risks, then directly calls the selected Until Loop to repeat dependency
  review until two consecutive trivial/no-change reviews.
version: 0.3.9
author: Backchain
license: MIT
platforms:
  - linux
  - macos
metadata:
  hermes:
    category: software-development
    tags:
      - planning
      - backchain
      - dependency-dag
      - implementation-plan
      - backward-chaining
    related_skills:
      - plan
      - writing-plans
      - subagent-driven-development
      - next-best-questions
---

# Backchain

Use Backchain when an implementation task needs an explicit dependency graph before work
starts. It turns a raw coding description into a forward draft, then **backward-chains**
that draft into an enriched dependency DAG with explicit unresolved risks. For a complete
planning result, Backchain binds the selected actual **Until Loop** card and its package-relative
ephemeral adapter to review and improve the scoped plan until Until Loop returns its exact
terminal receipt. Backchain does not implement a second loop, counter, or recovery state.

## Mode selection (prompt-first)

| Mode | When | Product label |
|------|------|----------------|
| **Native** (default) | Grok / Claude / Codex / Hermes chat | **native-unvalidated** plan JSON plus selected Until Loop binding |
| **Structural check** | Checkout available; user wants waves/validation | **script-packaged** via `--package-only` |
| **One-shot harness** | Candidate generation→elaboration | `run-prompt.sh` (one-shot; not convergence) |
| **NBQ experiment** | Explicit EVSI / casebook A/B only | **nbq-experiment** — never default |

**Native procedure (any host):**

Read `references/convergence.md` and `references/technical-lenses.md` before planning.
The full technical index must actually be loaded before a planning review, even when the
request looks simple; classify inapplicable categories explicitly. Resolve the actual
selected Until Loop card and its `references/runtime-ephemeral.md` in full, then use its
package-relative ephemeral adapter. No Git prerequisite applies unless the planning task
itself needs repository evidence.
No ambient Until Loop installation, custom Backchain pass counter, pass ceiling,
or substitute scheduler is allowed.

### Compatibility-native plan

1. Load `prompts/generator.v1.md` (or package copy) with `{{RAW_PROMPT}}` → draft JSON.
2. Load `prompts/dependency-review.prompt.md` with goal + draft → dependency-context JSON (`source: native`).
3. Resolve only evidenced facts; unevidenced world-state is not `initial_state`.
4. Load `prompts/elaborator.v1.md` with draft + rendered dependency context → enriched JSON.
5. Freeze the enriched plan artifact and original request as the plan-only Until Loop child
   candidate described in `references/convergence.md`. One Until Loop callback may use the
   Backchain review primitive and dependency review/elaboration for an authorized repair,
   while legacy seed/null edges and `goal_needs` remain preserved.
6. Return `{plan, convergence}` only after the exact selected Until Loop terminal `complete`
   receipt plus the final Backchain domain evidence. Otherwise return an honest incomplete
   binding companion. Report `mode=native` and `structural_plan_status: unknown` outside
   the plan unless a deterministic validator receipt exists for this exact plan. Keep
   `parallel_groups: []` in the canonical plan until that receipt exists.
7. Optional checkout packaging: `bash harness/run-prompt.sh --package-only enriched.json`
   proves only its structural result, never Until Loop completion.

### Source-aware native plan (explicit `backchain-caller/v1` selection)

Use this for requests with supporting specifications or source verification when the host
prepares the companion packet. Read `references/caller-contract.md` first. Original
request, selected source snapshots, caller packet, and selected lens findings travel as
the same data through generator, dependency review, elaborator, and the selected Until Loop
child context; existing plan JSON/schema remain unchanged.

1. **Plan/draft:** generate, dependency-review, and elaborate with the retained caller
   data. Preserve action/stage/action ID/owner/workflow stage, observed locator bases,
   source authority/provenance/currentness/revision/digests, resolved locators, and
   distinct candidate identities in the companion.
2. **Review/audit diagnostic:** `prompts/audit.prompt.md` returns review only. It does
   not start Until Loop or claim convergence. Applicable unavailable, stale, or ambiguous
   normative sources keep source review incomplete absent inspected supersession evidence.
3. **Repair/revise:** an active selected Until Loop callback may use the audit primitive,
   fresh whole-plan review, and the one-revision `prompts/revise.prompt.md` within exact
   bounds. Running/completed work, accepted facts, and protected items remain immutable;
   new nodes/edges need permission and rewires need a source-linked old-to-new map.
4. Bind the frozen candidate, source/lens context, bounds, and no-commit/no-project-
   execution scope to the selected whole Until Loop card. Until Loop owns
   recurrence, the two-consecutive-trivial gate, resume, budget/stop handling, and its
   terminal receipt. Backchain never supplies a pass ceiling or interprets a counter.
5. Only an exact Until Loop `complete` receipt plus final candidate-specific source/bounds/
   validation evidence permits `review.convergence` to say converged planning. A revised
   graph has `parallel_groups: []` and structural status `unknown` until deterministic
   validation for its exact output digest. Keep experiments scoped to exact condition,
   consumer, target, receipt scope/fidelity, and disposition.

Use `references/technical-lenses.md` to select applicable technical discovery questions,
`references/technical-lens-cards.md` for cards, and `references/technical-interactions.md` for
cross-lens questions. These are triggers and aids, never requirements by themselves.

**Question ≠ fact.** An unanswered question is not evidence and must not invent a `D*` by itself. An unevidenced world-state a step actually presupposes still needs a predecessor that would produce that evidence, or an honest `unresolved` — never a raw assumption.

Harness inventory, env, exit codes: `references/harness.md`. Dependency context shape: `references/dependency-context.md`.

## Procedure (automated packaging)

**One-shot candidate packaging** (checkout + Claude-compatible runner):

The commands below do not run Until Loop or semantic convergence. A direct CLI exit 0
proves only its documented structural result. The scripts and benchmark prompts remain
one-pass primitives; bind their resulting candidate to selected Until Loop separately.

```sh
bash harness/run-prompt.sh --prompt samples/oauth-login-tests.prompt.md
# defaults: elaborator TRACE on; relationship learnings on stderr
# options: --report compact|full · --no-trace · --quiet · --model sonnet · --from-draft · --package-only
# opt-in:  --nbq | --next-best-deps  (dependency-scoped next-best-questions before elaborate)
```

**Alternate elaborator backends:** `BACKCHAIN_ELAB_BACKEND` accepts `router` (default),
`ollama`, `ask-ollama`, or `cmd`. Use `BACKCHAIN_ELAB_MODEL` to pin the alternate model;
`cmd` also requires `BACKCHAIN_ELAB_CMD` and executes an executable path through its shebang.
Only the elaborator changes: a full `--prompt` run still needs the router for generation, while
`--from-draft` can use an alternate backend without a Claude-compatible runner. Audit identity in
`run.json`: `stages.elaborator.requested_model` is the requested pin and
`stages.elaborator.served_model` is the backend-reported model (with `served_models` retaining the
full list). Treat a missing served identity as unknown; the legacy top-level `model` is not proof
of which alternate model produced the elaboration.

**Opt-in next-best deps (`--nbq`):** default **off**. When set, after `draft.json` exists and
**before** the elaborator, Backchain builds a dependency-scoped problem from the draft, runs the
external **next-best-questions** skill (`infogain.py --json`), writes `nbq-problem.txt`,
`nbq-deps.json`, `nbq-context.md`, and injects that context as `{{NBQ_CONTEXT}}` into the elaborator
prompt. The elaborator may use ranked questions as five-lens **interrogation aids** only — no new
plan schema fields. If `--nbq` is set and the skill/command fails, the runner **exits 5** (does not
silently skip). **Critical:** `OLLAMA_URL` must be the chat endpoint
`http://127.0.0.1:11434/api/chat` (bare host:port → HTTP 405 and empty buckets with zero model calls).
Backchain normalizes bare URLs when possible. For tests: `BACKCHAIN_NBQ_CMD` (args: problemPath
outJsonPath). Skill root: `BACKCHAIN_NBQ_SKILL_DIR`. Casebook:
`bash harness/casebook-run.sh --track A --cases oauth-seeded-user --nbq`.

This generates a draft, elaborates it, **persists** recomputed `parallel_groups`, and validates
structure. It always saves **`compact-report.md`** and the exhaustive **`full-report.txt`**.
Stdout defaults to `--report compact`: a `Step | Work | Needs | Conditions` table with unique
direct supplier IDs, initial/unresolved count notes, initial facts and unresolved descriptions,
dependency-only parallel candidates, and validation/completion/advisory summaries. `--report full`
prints the exhaustive backchain: every statement, produce, input relation/need/match detail, wave,
chain, edge, and fidelity walk. Canonical JSON preserves exact artifact/match contracts. `--quiet`
silences progressive learnings only; it does not
suppress the final selected report. Artifacts under `results/run-prompt-*/` include
**`packaged.json`**, **`validation.json`**, **`handoff.json`**, both report files, and `run.json`
(`artifacts.compact_report` and `artifacts.full_report`). The canonical JSON contract is unchanged.
Exit `0` only when structure is valid; inv-7-only failures exit `1` with diagnostics (no silent fix).

**TRACE (default on):** elaborator TRACE_MODE writes non-empty `trace.txt` when the elaborator emits
a `<trace>` block (`--no-trace` for JSON-only). The generator never produces a trace. Operator
stderr gets only a deterministic **TRACE pointer** (not per-pop prose mirrors).

**Three operator channels:** (1) **stderr status** = deterministic **deltas** (stage banners,
`+` insert / `→` new edge / `·` null / compact ids-only `∴` package line; subject chips,
word-safe trunc); (2) **`trace.txt`** = elaborator **audit** when TRACE on (Goal phase +
per-pop `kept`/`wired`/…); (3) **selected stdout report** = compact by default or exhaustive with
`--report full`; both durable report files are always written. NDJSON twin:
`relationship-events.ndjson`. Disable progressive status with `--quiet` or
`--no-relationship-status`. Spec: `docs/relationship-status-spec.md`.

**Health metrics (operator):** structural ok, `completionStatus`, inv-7 diagnostics, and
dependency-safe waves. Same-depth steps may start together (not resource- or file-aware). Do **not**
score plans by seed-step count or discovered-step (`D*`) count — both can vary across one-shot runs;
judge by closed needs, honest `unresolved`, and a usable handoff DAG. A rich seed draft with few or
no `D*` can be ideal. Prefer empty seed `inputs`; if inv-7 fires, re-run generation with verbatim
`initial_state` pastes rather than asking the elaborator to rewrite seed edges.

**Parallel agents:** paste `results/.../handoff.json` (precomputed `waves`, `edges`, `critical_path`,
`steps` with `produces`/`inputs`) into the orchestrator — do not re-derive schedule from path
letters. Waves are conservative barriers; edges allow eager starts when a step’s own suppliers
are done. Packaging also runs a **forward fidelity walk** (multi-root → multi-sink along depth waves): each
step’s inputs must be ready from earlier waves / `initial_state`, and each edge’s `need` must
exact-match a supplier `produces` or carry a sparse `match`. Results land on handoff as
`forward_fidelity` + optional **`edge_semantic_warnings`** — **advisory** relationship honesty after
backprop freeze, not structural failures. Parallel workers should trust waves/edges and inspect
`forward_fidelity.issues` when non-empty. The compact report is a reading aid: its direct
dependencies do not establish executor assignment, worktree isolation, file/resource safety,
merge safety, or runtime completion.

**`completionStatus=complete` without `goal_needs`:** means structure is valid and `unresolved` is
empty — **not** that the goal sentence was separately proven covered. Optional `goal_needs` (when
hand/harness-supplied) is the goal-closure check.

**Manual multi-step (templates remain authoritative):**

1. Put the unedited request into `prompts/generator.v1.md` at `{{RAW_PROMPT}}`; save its
   JSON-only draft. Demo requests live under `samples/*.prompt.md`. The generator derives the
   request's terminal observable conditions into `goal_needs` **before** drafting any step, then
   runs **environment probes once against those conditions** — repo/worktree state, existing user
   or data state needing transition, release gates, documentation, and systems that must be brought
   into existence. Probes are conditional and **fail to nothing**: an unfired probe adds no step.
   They run at spec level, never per step.
2. Put that draft into `prompts/elaborator.v1.md`, set `{{TRACE_MODE}}` to `off`, and save
   the JSON-only enriched plan. The elaborator runs a **five-lens back-check per step** (CLAIM /
   NEEDS / SUPPLY / PULL / RESOLVE): deep interrogation of what that step needs to run, what it
   claims when done, whole-graph supply scan up the chain, one-hop downstream pressure on its
   produces, then wire / enrich / insert `D*` / unresolved — never a shallow edge-only pass. Three
   disciplines live **inside** RESOLVE, not as extra lenses: **CARRIER** (a producer names the
   concrete artifact when its `produces` could cover more than one thing, and the consuming edge's
   existing optional `inputs[].artifact` names the same carrier); **HOIST** (a need shared by two
   or more steps is supplied **once**, at the **lowest common ancestor** of its consumers and never
   higher — hoisting to a shared root would serialize independent branches; prefer **widening an
   existing step** over inserting a redundant `D*`, and re-check acyclicity before committing); and
   **EVIDENCE** (a need is closed only by request/inspect evidence it already holds, or by a
   predecessor whose execution would produce inspectable evidence of it — never a raw assumption;
   unproducible evidence stays `unresolved`).
   These duties are cumulative with the in-place rewrite duty, not alternatives to it. Trace
   mode is for offline/manual debugging only: `harness/bench.sh` always renders it as `off` and
   does not parse trace-mode output.
3. Recompute `parallel_groups` with `computeParallelGroups` from `harness/lib.js` (or use
   `packagePlan` / `run-prompt.sh --package-only`), then validate with `validateStructure`
   before using the plan. Do not leave `parallel_groups` as `[]` if multi-member waves exist.
4. For a complete Backchain planning invocation, run `references/convergence.md` over
   the candidate and preserve its companion report. Repackage after any graph revision.
   `prompts/rubric-judge.md` and `prompts/compare-judge.md` assess benchmark candidates;
   neither substitutes for the two consecutive planning reviews.

## Plan document shape

A complete plan JSON object has these **required top-level keys** (see `schema/plan.schema.json`):

`goal`, `initial_state`, `steps`, `parallel_groups`, `unresolved`

Optional top-level key: **`goal_needs`** — array of non-empty strings naming terminal needs that must appear in some step’s `produces` or in `initial_state` for `completionStatus` to report **complete**. Empty array is allowed and means no goal constraints (same as omitting the field). When present, the field is shape-strict (non-array, non-string, empty, or whitespace-only elements → schema / invariant 1 invalid). Division of labor: the **generator authors it** — deriving the request's terminal observable postconditions before drafting any step — and may legitimately emit `goal_needs: []` when the request implies no checkable terminal condition, but must never invent an entry to fill the field. The **elaborator preserves a supplied array verbatim** (never edits, reorders, extends, or drops entries) and is responsible for ensuring every entry is **covered** by some step's `produces` or `initial_state`, closing any gap by wiring, widening, inserting a `D*`, or recording it in `unresolved`. The elaborator still must not invent this field when a draft lacks it.

- **`goal`**: a single sentence describing the **end state** the plan achieves — not a task
  title or verb-first to-do ("User authentication works end-to-end," not "Add auth").
- **`initial_state`**: concrete facts already true **and evidenced** before any step runs
  (request-supplied or planning-time inspection). Implementers may rely on these; they are not
  guesses. Vague or assumed entries just push hidden work onto elaboration.
- **`steps`**: at least one step; every step's `produces` has **at least one** non-empty string
  (schema `minItems`).

Every step has exactly **five fields**: `id`, `statement`, `produces`, `inputs`, `origin`.  
`origin` is `seed` or `discovered`. Do **not** invent extra step or plan fields
(`dependents`, `flags`, `rationale`, `preconditions`, etc.).

**`statement` and every entry in `produces` are postconditions (state/conclusion), never
actions, commands, or tool calls.** Write what becomes true when the step is done — e.g.
"the database migration has been applied," not "run the migration"; "the User model exposes a
fullName getter," not "add a fullName getter." The same discipline applies to each `produces`
string (concrete artifacts named as achieved state, not as work-to-do).

**Elaborator in-place rewrite:** if a seed draft leaks into tactics (tool names, commands,
verb-first instructions), the elaborator **rewrites `statement` and `produces` in place** to
the intended postcondition state. The corrected text *is* the record — do not emit a separate
changelog field. This never changes a step's `id` or `origin`.

Generator drafts use seed IDs `S1`, `S2`, …; the elaborator inserts discovered steps as `D1`, `D2`, …
in creation order (never invent free-form discovered ids). Leave generator-drafted steps as
`origin: "seed"`; only elaborator-inserted steps use `origin: "discovered"`. **Generator drafts
must keep `unresolved` as `[]` and must never write `origin: "discovered"`** — those belong to
the elaborator only. **Seed step `id`s are immutable** — never rename or renumber an existing
seed. **Never remove an existing `inputs[]` edge** from the draft (you may add edges and widen
`statement`/`produces` in place).

Each **input** is an object with required keys `need` (string) and `from`:
- `from: null` — need is already true in `initial_state` (must be listed there; not an unspoken “world” fact).  
- `from: "<step id>"` — need is supplied by that step's `produces`.  
- **Never** write the string `"initial"` (or any other sentinel) in `from` — only `null` or a real step id.  
Optional sparse fields: `artifact` (concrete carrier) and `match` (only when need vs supplier
wording is non-obvious). Do not invent other input keys.

Each **unresolved** entry has required keys `step`, `need`, and `reason`:
- `reason: "residual-risk"` — gap cannot be closed; **no** `cycle` field.  
- `reason: "circular"` — committing the edge would cycle; **required** `cycle` array of ≥2 step
  ids describing the refused loop (bookkeeping only — do **not** also put that edge in `inputs`).

**Never leave a genuine need silently dropped.** Close it with an input edge, widen the step,
insert a discovered supplier, or record it in `unresolved` — never omit a real gap from the plan.

After elaboration, recompute `parallel_groups` with `computeParallelGroups` from
`harness/lib.js` (do not hand-edit longest-path groups). Elaborator/generator output should
leave `parallel_groups` as `[]` until that recompute.

## Structural invariants (validator)

Keep seed step IDs and existing input edges intact. The structural validator enforces seven
invariants (agents loading only this skill must still honor them):

1. **Schema shape** — closed fields/enums; only the five step fields above; inputs use
   `need`/`from` (+ optional `artifact`/`match`); unresolved uses the reason-specific shape.  
2. **Acyclic committed edges** — no dependency cycles; circular residual risk is bookkeeping
   in `unresolved`, not committed `from` edges.  
3. **Suppliers exist** — every non-null `inputs[].from` references an existing step id.  
4. **Discovered steps consumed** — every `discovered` step is used as a supplier elsewhere.  
5. **No double-track** — a need is not both an input and unresolved for the same step.  
6. **Bookkeeping consistency** — residual-risk / circular bookkeeping step refs exist, and
   stored `parallel_groups` match recomputed longest-path depth groups.  
7. **Null origins declared pre-existing** — every `from: null` need must also appear in
   `initial_state` (exact match after trim + whitespace collapse). A bare null is not a free
   “world is true” token. Semantic need↔`produces` matching is **not** structural (prompt /
   elaborator layer); structural checks only prove provenance and declared assumptions.

**Structural vs complete:** `validateStructure` returns `{ ok, failures }` (invalid vs valid).
Separately, `completionStatus(plan)` reports `invalid` | `incomplete` | `complete`:
structure-ok plans with non-empty `unresolved` are **valid incomplete** (normal for residual
gaps). Optional `goal_needs` (when present) must be covered by `produces` or `initial_state` for
**complete** (match after trim + whitespace collapse; case-sensitive). Malformed `goal_needs`
is **invalid**, not silently ignored.

## Layout and verification

A marketplace or skill-directory install ships only this skill directory (`SKILL.md`,
`prompts/`, `references/`). The paths below, the harness commands above and the gate below
exist only in a Backchain **source repository** checkout; the native procedure and plan
contract on this card need none of them.

| Path (source checkout) | Purpose |
| --- | --- |
| `prompts/` | Generator, elaborator, rubric-judge, compare-judge templates |
| `schema/plan.schema.json` | Plan document schema |
| `fixtures/` | Adversarial draft-plan cases for benchmarks |
| `samples/` | Natural-language requests for generator demos |
| `harness/` | Structural validation + `bench.sh` scoring |

### Local-change gate (maintainers, source checkout)

When changing Backchain itself with a `test-harness` skill installed, its contract is
`<test-harness>/references/gate-snippet.md` + `local-change-gate.md`, for example:

```bash
bash "<test-harness>/scripts/run-harness.sh" \
  --repo "$(git rev-parse --show-toplevel)"
```

Require `PASS_CLEAN` or `PASS_CLEAN_SCOPED`. Paste `chat-card.md`. Do **not** treat bare suite exit 0 as sufficient.

| | |
|---|---|
| **Inner suite** | `make test-fast` |
| **Residual** | LLM bench / casebook — not RESULT |

- **Install:** use your host's plugin marketplace (`backchain` plugin). From a source
  checkout, `./install.sh` installs into Claude Code and the Hermes skillhub:  
  - Claude Code: `~/.claude/skills/backchain`  
  - Hermes skillhub: `~/.hermes/skills/software-development/backchain`  
  - Flags: `--claude-only` / `--hermes-only`; never overwrites an existing path
- **LLM bench / casebook (optional residual, not RESULT):**  
  `bash harness/bench.sh --run --label <name>` ·  
  `bash harness/bench.sh --compare <labelA> <labelB>`

### Habitat matrix (Claude Code / Hermes Docker)

| Habitat | Skill install path | Notes |
| --- | --- | --- |
| Claude Code (host) | `~/.claude/skills/backchain` | `./install.sh` or `--claude-only` |
| Hermes skillhub (host) | `~/.hermes/skills/software-development/backchain` | `./install.sh` or `--hermes-only` |
| Hermes Docker container | `/opt/data/skills/software-development/backchain` | Same files as host when `~/.hermes` is bind-mounted at `/opt/data` |

The **skill package** is `skills/backchain/SKILL.md` (this card). The generator/elaborator
templates, schema, and `make test-fast` harness live in the **host repository** checkout —
they are **not** assumed to be mounted into the Hermes container. Skill-only Hermes operators
follow the procedure and plan contract on this card; run the deterministic suite from the
host repo when changing code.

You can use the generator and elaborator prompts directly in any Claude Code or Hermes
session that has the skill installed, or run scored fixture passes with the harness on the
host repo.
