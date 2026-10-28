---
name: backchain
description: >-
  Use when an implementation task needs a dependency-aware plan before coding:
  backward planner / backchain / precondition-first planning, dependency DAGs,
  elaborating incomplete plans, or scheduler-ready step graphs. Turns a natural-language
  coding request into a dependency-aware DAG with explicit unresolved risks, then binds it
  to the selected Until Loop for repeated dependency review. Supplied drafts retain their
  seed identities and use backward elaboration. The default gate requires two consecutive
  trivial/no-change reviews; one cycle runs when the caller states `Backchain passes: one`.
version: 0.6.3
author: Backchain
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: prompt-only
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
starts. For a fresh request, synthesize a compact DAG directly, check dependency questions,
and elaborate only when evidence requires a graph repair. A supplied draft keeps its seed
identities and is backward-chained into an enriched DAG. For a complete planning result,
bind the candidate to the selected actual **Until Loop** card and its package-relative
ephemeral adapter. Until Loop owns repeated review and its exact terminal receipt; Backchain
does not implement a second loop, counter, or recovery state.

## Mode selection (prompt-first)

| Mode | When | Product label |
|------|------|----------------|
| **Native** (default) | Grok / Claude / Codex / Hermes chat | **native-unvalidated** plan JSON plus selected Until Loop binding |
| **Structural check** | Backchain development checkout available; user wants waves/validation | **script-packaged** via `--package-only` |
| **One-shot harness** | Candidate generation→elaboration | `run-prompt.sh` (one-shot; not convergence) |
| **NBQ experiment** | Explicit EVSI / casebook A/B only | **nbq-experiment** — never default |

**Native procedure (any host):**

Read `references/convergence.md` and `references/technical-lenses.md` before planning.
The full technical index must actually be loaded before a planning review, even when the
request looks simple; classify inapplicable categories explicitly. Read the selected
Until Loop card (`SKILL.md`, or the caller's explicitly selected bundled `ADAPTER.md`)
and its `references/runtime-ephemeral.md` in full. Resolve that reference and the
ephemeral adapter relative to the selected card's directory. No Git prerequisite applies unless the planning task
itself needs repository evidence.
No ambient Until Loop installation, custom Backchain pass counter, pass ceiling,
or substitute scheduler is allowed.

### Fresh request (default)

1. Load `prompts/direct.v1.md` with the unedited request as `{{RAW_PROMPT}}`. When
   `backchain-caller/v1` is selected, include the same original request, source snapshots,
   caller packet, and triggered lens findings as data. Direct synthesis is for fresh
   requests only; never use it to replace an existing draft.
2. Run the unchanged `prompts/dependency-review.prompt.md` against the candidate and the
   same retained request/caller/source/lens data. Resolve questions only with user answers
   or inspected evidence; an unanswered question is not a fact.
3. If an answer or inspection changes a dependency, supplier, step claim, or unresolved
   need, or an open material question must be recorded as a real unresolved dependency,
   load `prompts/elaborator.v1.md` with the candidate and dependency context. Otherwise
   carry the candidate forward without an unchanged rewrite.
   Whenever invoked, the elaborator performs the complete five-lens pass, coverage audit,
   and forward relationship check.
4. Freeze the candidate and original request as the plan-only Until Loop child described
   in `references/convergence.md`. Until Loop owns the full recurring review, technical-lens
   applicability screen, repair/check cycle, and terminal receipt.

### Supplied draft or legacy automated path

For a supplied draft, go directly to the elaborator. Preserve its seed IDs, input edges,
`goal_needs`, and existing `confirm` entries; fill missing confirmations without rewriting
unaffected content. When the one-shot compatibility pipeline is explicitly selected for a
raw request, use the generator/dependency-review/elaborator sequence below. Neither is the
default fresh-request route.

1. Load `prompts/generator.v1.md` (or package copy) with `{{RAW_PROMPT}}` → forward draft JSON.
2. Load `prompts/dependency-review.prompt.md` with goal + draft → dependency-context JSON
   (`source: native`); resolve only evidenced facts.
3. Load `prompts/elaborator.v1.md` with the draft and rendered context → enriched JSON.
4. Freeze the enriched plan and original request as the plan-only Until Loop child
   candidate described in `references/convergence.md`. One callback may use Backchain's
   review primitive and dependency review/elaboration for an authorized repair while
   preserving legacy seed/null edges and `goal_needs`.
5. Return `{plan, convergence}` only after the exact selected Until Loop terminal `complete`
   receipt plus final Backchain domain evidence; otherwise return an honest incomplete
   binding companion. Report `mode=native` and `structural_plan_status: unknown` outside the
   plan unless a deterministic receipt exists for this exact candidate. Keep
   `parallel_groups: []` until that receipt exists.
6. Optional packaging in the development checkout,
   `bash harness/run-prompt.sh --package-only enriched.json`, proves only its structural
   result, never Until Loop completion.

### Source-aware native plan (explicit `backchain-caller/v1` selection)

Use this for requests with supporting specifications or source verification when the host
prepares the companion packet. Read `references/caller-contract.md` first. Original
request, selected source snapshots, caller packet, and selected lens findings travel as
the same data through direct synthesis (or the legacy generator), dependency review,
optional elaboration, and the selected Until Loop child context; existing plan JSON/schema
remain unchanged.

1. **Plan/draft:** for a fresh request, use direct synthesis and dependency review with
   the retained caller data; elaborate only if evidence requires a graph repair. The
   supplied existing candidates go straight to elaboration; the legacy generator/elaborator
   path remains available for automated raw-request drafts.
   Preserve action/stage/action ID/owner/workflow stage, observed locator bases, source
   authority/provenance/currentness/revision/digests, resolved locators, and distinct
   candidate identities in the companion.
2. **Review/audit diagnostic:** `prompts/audit.prompt.md` returns review only. It does
   not start Until Loop or claim convergence. Applicable unavailable, stale, or ambiguous
   normative sources keep source review incomplete absent inspected supersession evidence.
3. **Repair/revise:** an active selected Until Loop callback may use the audit primitive,
   fresh whole-plan review, and the one-revision `prompts/revise.prompt.md` within exact
   bounds. Running/completed work, accepted facts, and protected items remain immutable;
   new nodes/edges need permission and rewires need a source-linked old-to-new map.
4. Bind the frozen candidate, source/lens context, bounds, and no-commit/no-project-
   execution scope to the selected whole Until Loop card. Until Loop owns
   recurrence, the review gate (by default two consecutive trivial reviews; one cycle when
   the child request carries `Backchain passes: one`, as `references/convergence.md`
   defines), resume, budget/stop handling, and its terminal receipt. Backchain never
   supplies a pass ceiling or interprets a counter.
5. Only an exact Until Loop `complete` receipt plus final candidate-specific source/bounds/
   validation evidence permits `review.convergence` to say converged planning. A revised
   graph has `parallel_groups: []` and structural status `unknown` until deterministic
   validation for its exact output digest. Keep experiments scoped to exact condition,
   consumer, target, receipt scope/fidelity, and disposition.

Use `references/technical-lenses.md` to select applicable technical discovery questions,
`references/technical-lens-cards.md` for cards, and `references/technical-interactions.md` for
cross-lens questions. These are triggers and aids, never requirements by themselves.

**Question ≠ fact.** An unanswered question is not evidence and must not invent a `D*` by itself. **EVIDENCE** in **RESOLVE**: unevidenced world-state is not `initial_state`; an actually required state needs a predecessor that produces inspectable evidence or an honest `unresolved` — never a raw assumption.

Harness inventory, env, exit codes: `references/harness.md`. Dependency context shape: `references/dependency-context.md`.

## Procedure (automated packaging)

**One-shot candidate packaging** (Backchain development checkout + Claude-compatible runner):

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

**Template and validation notes:** `direct.v1.md` is for fresh requests. Supplied plans go
straight to `elaborator.v1.md`; the legacy generator/elaborator pair remains for automated
raw-request drafts. The elaborator's five lenses (CLAIM / NEEDS / SUPPLY / PULL / RESOLVE),
goal closure, evidence rules, carrier naming, lowest-common-ancestor hoisting, and
true-immediate-dependency test remain operative. Packaging recomputes `parallel_groups`;
a structural receipt does not replace the selected Until Loop's review or terminal receipt.
Repackage after any graph revision. Benchmark judges do not substitute for planning review.

## Plan document shape

A complete plan JSON object has these **required top-level keys** (the development checkout's `schema/plan.schema.json` states them as a schema):

`goal`, `initial_state`, `steps`, `parallel_groups`, `unresolved`

Optional top-level key: **`goal_needs`** — array of non-empty strings naming terminal needs that must appear in some step’s `produces` or in `initial_state` for `completionStatus` to report **complete**. Empty array is allowed and means no goal constraints (same as omitting the field). When present, the field is shape-strict (non-array, non-string, empty, or whitespace-only elements → schema / invariant 1 invalid). Division of labor: fresh-request direct synthesis authors it before drafting any step; the legacy generator does so for its compatibility path. Either may emit `goal_needs: []` when the request implies no checkable terminal condition, but must never invent an entry. The **elaborator preserves a supplied array verbatim** (never edits, reorders, extends, or drops entries) and is responsible for ensuring every entry is **covered** by some step's `produces` or `initial_state`, closing any gap by wiring, widening, inserting a `D*`, or recording it in `unresolved`. The elaborator still must not invent this field when a draft lacks it.

- **`goal`**: a single sentence describing the **end state** the plan achieves — not a task
  title or verb-first to-do ("User authentication works end-to-end," not "Add auth").
- **`initial_state`**: concrete facts already true **and evidenced** before any step runs
  (request-supplied or planning-time inspection). Implementers may rely on these; they are not
  guesses. Vague or assumed entries just push hidden work onto elaboration.
- **`steps`**: at least one step; every step's `produces` has **at least one** non-empty string
  (schema `minItems`).

Every step has **five required fields**: `id`, `statement`, `produces`, `inputs`, `origin`,
plus one optional field, `confirm`.  
`origin` is `seed` or `discovered`. Do **not** invent extra step or plan fields
(`dependents`, `flags`, `rationale`, `preconditions`, etc.).

**`confirm`** (optional array) records how each produce is confirmed. Each entry is
`{ "produces": "<exact text of one of this step's produces>", "by": "<command, observation,
or inspection>; pass when <expected result>", "level": "execute" | "inspect" | "unconfirmable" }`
and names a produce at most once. Author one for every step's produces, work steps included,
not only verification sinks. The confirmation must pass the two-people test: two people running
it separately would be forced to agree. `execute` means the condition must be exercised;
`inspect` means inspection is sufficient. Give content criteria (docs, changelogs, test coverage)
a command-checkable confirmation, such as a search for required terms. A criterion no available
check can confirm keeps its produce and gets `level: "unconfirmable"` with `by` naming what would
confirm it, rather than being dropped. When a check relies on an external oracle (golden, fixture,
or snapshot), the confirmation also confirms that the oracle agrees with the task. The exporter
turns each confirmed produce into the done string `<produce>. Confirm by: <by>` (`inspect` adds
`(inspection is sufficient)`; `unconfirmable` reads `Confirm by: unconfirmable here — <by>`).
A produce without an entry stays valid and exports unchanged; packaging reports it in the
advisory `unconfirmed_produces` list. The elaborator and revise preserve existing entries and
repair them when they rewrite a produce, the same way they preserve `goal_needs`.

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

1. **Schema shape** — closed fields/enums; only the five step fields above plus optional
   `confirm`; inputs use `need`/`from` (+ optional `artifact`/`match`); unresolved uses the
   reason-specific shape. Each `confirm` entry names the exact text of one of its step's
   `produces`, at most once, with a non-blank `by` and a `level` of `execute`, `inspect`, or
   `unconfirmable`.  
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
A produce without a `confirm` entry is neither a structural failure nor incomplete; it is only
the advisory `unconfirmed_produces` signal.
Separately, `completionStatus(plan)` reports `invalid` | `incomplete` | `complete`:
structure-ok plans with non-empty `unresolved` are **valid incomplete** (normal for residual
gaps). Optional `goal_needs` (when present) must be covered by `produces` or `initial_state` for
**complete** (match after trim + whitespace collapse; case-sensitive). Malformed `goal_needs`
is **invalid**, not silently ignored.

## Layout and verification

A marketplace or skill-directory install ships only this skill directory (`SKILL.md`,
`prompts/`, `references/`, `evals/`), published from Skill Craft. The paths below, the
harness commands above and the gate below live in the separate Backchain **development
checkout** and are not shipped with this skill; the native procedure and plan contract on
this card need none of them.

| Path (development checkout) | Purpose |
| --- | --- |
| `prompts/` | Generator, elaborator, rubric-judge, compare-judge templates |
| `schema/plan.schema.json` | Plan document schema |
| `fixtures/` | Adversarial draft-plan cases for benchmarks |
| `samples/` | Natural-language requests for generator demos |
| `harness/` | Structural validation + `bench.sh` scoring |

### Local-change gate (maintainers, development checkout)

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

- **Install:** use your host's plugin marketplace (`backchain` plugin). From a Skill Craft
  checkout, `./install.sh --skill backchain` installs the skill directory:  
  - Claude Code: `~/.claude/skills/backchain`  
  - Hermes skillhub: `~/.hermes/skills/software-development/backchain`  
  - Flags: `--claude-only` / `--hermes-only`; never overwrites an existing path
- **LLM bench / casebook (optional residual, development checkout, not RESULT):**  
  `bash harness/bench.sh --run --label <name>` ·  
  `bash harness/bench.sh --compare <labelA> <labelB>`

### Habitat matrix (Claude Code / Hermes Docker)

| Habitat | Skill install path | Notes |
| --- | --- | --- |
| Claude Code (host) | `~/.claude/skills/backchain` | `./install.sh --skill backchain` or `--claude-only` |
| Hermes skillhub (host) | `~/.hermes/skills/software-development/backchain` | `./install.sh --skill backchain` or `--hermes-only` |
| Hermes Docker container | `/opt/data/skills/software-development/backchain` | Same files as host when `~/.hermes` is bind-mounted at `/opt/data` |

The **skill package** is `skills/backchain/SKILL.md` (this card). The generator/elaborator
templates ship with it; the schema and `make test-fast` harness live in the Backchain
**development checkout** — they are **not** assumed to be mounted into the Hermes
container. Skill-only Hermes operators
follow the procedure and plan contract on this card; run the deterministic suite from the
development checkout when changing code.

You can use the generator and elaborator prompts directly in any Claude Code or Hermes
session that has the skill installed, or run scored fixture passes with the harness in the
development checkout.
