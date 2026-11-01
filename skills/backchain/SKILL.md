---
name: backchain
description: >-
  Use when an implementation task needs a dependency-aware plan before coding:
  backward planner / backchain / precondition-first planning, dependency DAGs,
  elaborating incomplete plans, or scheduler-ready step graphs. Turns a natural-language
  coding request into a forward draft then backward-chaining enriched DAG with explicit
  unresolved risks, validated and packaged by its own script, then directly calls the
  selected Until Loop to repeat dependency review, by default until the first
  trivial/no-change review, for one cycle when the caller states `Backchain passes: one`,
  or until two consecutive trivial reviews with `Backchain passes: converge`.
version: 0.6.6
author: Backchain
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: mixed
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
starts: hidden ordering, cutover, fixtures, or rollout preconditions (OAuth plus its tests, a
migration that must not delete the old queue yet, a deploy that needs a smoke check of this
build). Not for a one-line fix, a review-only request, or an agreed plan you only want
executed: Plan Dispatcher runs those.

A run has two halves. You plan and review. `scripts/backchain.py` beside this card checks,
packages and exports plans and keeps every record of the run, and the selected **Until Loop**
owns the review loop. Do not write your own bookkeeping code, hand-build the Until Loop
contract, or keep a pass counter.

## Native procedure

Every command is `python3 -I -B <this skill>/scripts/backchain.py <command> …`; each prints
absolute paths and the next command. Use a new, empty run directory: where the caller or request
lets you write, otherwise outside the project.

1. **Prepare.** `prepare --run DIR --request REQUEST.md`. Add `--draft PLAN.json` to elaborate
   an inherited plan, `--caller PACKET.json` for a `backchain-caller/v1` request (read
   [references/caller-contract.md](references/caller-contract.md) first), `--binding ID` when the
   request carries `Backchain standalone Until Loop binding: ID`, and `--passes one` or
   `--passes converge` when the caller states that marker. It freezes the inputs, resolves
   every resource (the selected Until Loop is the bundled `../improve/runtime/until-loop/ADAPTER.md`
   beside this skill unless `--until-loop` names another; a missing one stops the run) and prints
   the prompts to read, once each, in order.
2. **Plan.** Follow the printed prompts: synthesize the plan from the request into
   `DIR/draft.json`, review its dependencies, and elaborate it into `DIR/plan.json` only when that
   review changes something (otherwise copy the draft). An inherited draft is elaborated (or, with
   a caller packet, audited and revised) directly. Resolve only evidenced facts: an unevidenced
   world-state is not `initial_state`. Leave `parallel_groups` as `[]`; the script computes them.
3. **Freeze.** `freeze --run DIR` checks the candidate (the seven invariants, the draft's
   `goal_needs` and confirmations, an inherited draft's steps and edges, a caller's edit bounds),
   packages it and writes the Until Loop contract. Fix what it reports and run it again.
4. **Loop.** Read the Until Loop card once and start it by its "Start from a parent-written
   contract" route with the printed `Contract:` and `Receipt:`. The caller selects the review
   gate: by default the first trivial review completes, `Backchain passes: one` runs one
   review/fix/check cycle, and `Backchain passes: converge` needs two consecutive trivial
   reviews ([references/convergence.md](references/convergence.md)). Each callback is one cycle:
   assess with [prompts/convergence-review.prompt.md](prompts/convergence-review.prompt.md),
   repair `DIR/plan.json` within the edit bounds, save the assessment JSON (its
   `candidate_identity` is the sha256 `freeze` or the last `record` printed), run `record`, run
   the packet's `verify_script`, and submit the report `record` wrote through the packet's
   `done_argv`.
5. **Finish.** After the loop ends, `finish --run DIR` writes `DIR/result.json`,
   `{plan, convergence}`; with a caller packet, write the final review object of the final
   candidate ([references/caller-contract.md](references/caller-contract.md); its
   `candidate.output_sha256` is the sha256 the last `record` printed) and pass it with
   `--review FILE` to get `{plan, review}`. Return it; say converged only when `finish` does, and
   otherwise report its next action. `export DIR/plan.json` gives Plan Dispatcher the execution
   graph of a complete plan.

A `backchain-caller/v1` action `review` (stage `audit`) is a read-only one-pass diagnostic with
[prompts/audit.prompt.md](prompts/audit.prompt.md): it changes no candidate, starts no loop and
claims no convergence.

**Lenses.** When planning and in every review, screen all categories of
[references/technical-lenses.md](references/technical-lenses.md) against the request, then read
only the applicable or uncertain cards: `lenses T07 T35` prints them. Lenses are triggers and
aids, never requirements by themselves. **A question is not a fact:** an unanswered question
invents no `D*`, and an unevidenced world-state a step presupposes needs a predecessor that would
produce that evidence, or an honest `unresolved`, never a raw assumption.

## Plan document shape

A complete plan JSON object has these **required top-level keys**:

`goal`, `initial_state`, `steps`, `parallel_groups`, `unresolved`

Optional top-level key: **`goal_needs`** — array of non-empty strings naming terminal needs that must appear in some step’s `produces` or in `initial_state` for completion to report **complete**. Empty array is allowed and means no goal constraints (same as omitting the field). When present, the field is shape-strict (non-array, non-string, empty, or whitespace-only elements → schema / invariant 1 invalid). Division of labor: the **generator authors it** — deriving the request's terminal observable postconditions before drafting any step — and may legitimately emit `goal_needs: []` when the request implies no checkable terminal condition, but must never invent an entry to fill the field. The **elaborator preserves a supplied array verbatim** (never edits, reorders, extends, or drops entries) and is responsible for ensuring every entry is **covered** by some step's `produces` or `initial_state`, closing any gap by wiring, widening, inserting a `D*`, or recording it in `unresolved`. The elaborator still must not invent this field when a draft lacks it.

- **`goal`**: a single sentence describing the **end state** the plan achieves — not a task
  title or verb-first to-do ("User authentication works end-to-end," not "Add auth").
- **`initial_state`**: concrete facts already true **and evidenced** before any step runs
  (request-supplied or planning-time inspection). Implementers may rely on these; they are not
  guesses. Vague or assumed entries just push hidden work onto elaboration.
- **`steps`**: at least one step; every step's `produces` has **at least one** non-empty string.

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
or snapshot), the confirmation also confirms that the oracle agrees with the task. `export` turns
each confirmed produce into the done string `<produce>. Confirm by: <by>` (`inspect` adds
`(inspection is sufficient)`; `unconfirmable` reads `Confirm by: unconfirmable here — <by>`).
A produce without an entry stays valid and exports unchanged; `check` lists it in the advisory
`unconfirmed_produces`. The elaborator and revise preserve existing entries and repair them when
they rewrite a produce, the same way they preserve `goal_needs`.

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
seed. **The elaborator never removes an existing `inputs[]` edge** from the draft (it may add
edges and widen `statement`/`produces` in place). **Inherited and generated content differ:** a
step, edge or confirmation in the caller's input (an inherited draft or plan) stays, unless the
caller's `edit_bounds` make it provisional, and `freeze` and `record` check that mechanically; a
later review may remove an edge or step this run itself generated when it finds it unjustified,
recording the reason as a material repair.

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

## Structural invariants

`check` (and `freeze`, `record`) enforce seven invariants; honor them while writing:

1. **Schema shape** — closed fields/enums; only the five step fields above plus optional
   `confirm`; inputs use `need`/`from` (+ optional `artifact`/`match`); unresolved uses the
   reason-specific shape. Each `confirm` entry names the exact text of one of its step's
   `produces`, at most once, with a non-blank `by` and a `level` of `execute`, `inspect`, or
   `unconfirmable`.
2. **Acyclic committed edges** — no dependency cycles; circular residual risk is bookkeeping
   in `unresolved`, not committed `from` edges.
3. **Suppliers exist** — every non-null `inputs[].from` references an existing step id.
4. **Discovered steps consumed** — every `discovered` step is used as a supplier elsewhere, or
   supplies a declared `goal_needs` entry.
5. **No double-track** — a need is not both an input and unresolved for the same step.
6. **Bookkeeping consistency** — unresolved and cycle step refs exist, and stored
   `parallel_groups` match the recomputed longest-path depth groups (`package` writes them).
7. **Null origins declared pre-existing** — every `from: null` need also appears in
   `initial_state` (exact match after trim + whitespace collapse). Semantic need↔`produces`
   matching is not structural; it is the elaborator's and the review's job.

**Structural vs complete:** a structurally valid plan with non-empty `unresolved` is **valid
incomplete** (normal for honest residual gaps); with `goal_needs`, every entry must also be
covered for **complete**. A produce without a `confirm` entry is neither a structural failure nor
incomplete; it is only the advisory `unconfirmed_produces` signal.

## Development checkout

The Backchain development checkout (not shipped with this skill) holds the benchmark harness,
fixtures, samples and the maintainers' change gate: [references/harness.md](references/harness.md).
Install this skill from your host's plugin marketplace as part of the `skill-craft` plugin
(`skill-craft@whichguy`; invoke `/skill-craft:backchain`).
