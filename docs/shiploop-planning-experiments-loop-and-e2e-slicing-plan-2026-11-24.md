# ShipLoop Planning Redesign: Isolated Experiment Loop & Vertical E2E-First Slicing (2026-11-24)

## Diagnosis & Evidence

Recent ShipLoop empirical runs and journals established three structural gaps in how planning works today:

1. **Planning experiments rarely execute under `Plan Improve` alone.**
   Across 272 finished current-era runs (`docs/experiments/sdlc-structure-20261119/evidence/more-cuts.txt`), plans
   recorded 584 assumptions (`288 evidenced`, `142 probed`, `154 open`) and 132 plans had at least one `probed`
   assumption, yet there were **0** `improve-reconcile` events, and `Plan Improve` edited anything in only 6% of 270
   reviews (substantive edits in 2–3%). Models treat `Plan Improve` as a late prose review rather than an active
   make-plan → identify-experiments → run-isolated-experiments → refine-plan loop, and `intake` questions routed
   `"experiment"` had no downstream carrier or gate at `plan`.
2. **Work queues collapse to one item, and `step-plan` cuts horizontally.**
   281 of 282 accepted plans queued 1 work item (`docs/shiploop-sdlc-structure-journal.md` R3), and `step-plan` duty 4
   explicitly instructed models to *"Cut a larger item at a module or layer boundary (interface first, then each
   side)"*, producing bottom-up horizontal slices (storage/schema before API/UI) that delay end-to-end integration
   until late in the run.
3. **Guardrails from prior experiments must stay intact.**
   - **Small-task speed (Round 6, 2026-11-20):** Defaulting small cohesive items to 1 step saved 19–44% wall-clock
     time with no quality loss. Small single-surface tasks must remain 1 item / 1 step, and zero-experiment plans must
     finish on iteration 1 of `plan`'s Until Loop.
   - **Up-front requirements guard against scope creep (Ratchet pilot, 2026-11-20..22):** Unbounded post-build spec
     enrichment added 59 clauses of which blind judges accepted only 10 (6/9 tested failed a correct reference) at
     3.2×–6.6× ShipLoop's runtime. Known requirements stay up front in `KNOWLEDGE/spec.md`; progressive enrichment
     sequences *implementation* vertically (`W1` spine → `W2..Wn` enrichments), never inventing unrequested spec scope.
   - **Owner decisions preserved:** Keep the full Improve sequence (`Plan Improve`, `improve-reconcile`, and all other
     Improve stages); preserve the 23-stage graph, protocol 4, and state version 7 backward compatibility; keep all
     stage Until Loops unbounded (`there is no iteration limit`).

## Design (Four Sequences)

### Sequence A — Isolated Experiment-Driven Planning via `plan`'s Stage Until Loop

- Add `plan` to the script-written Until Loop (`shiploop_stage_spec.STAGE_SPEC["plan"]` gets
  `entry_runs=("loop-contract",)` and `complete_runs=("loop-terminal",)`; `shiploop_loops.PRELUDE_STAGES = ("plan",)`
  and `shiploop_loops.STAGES = (*PRELUDE_STAGES, *stage_spec.INNER)`).
- `plan`'s loop contract encodes the iterative loop explicitly:
  1. Draft or refine the provisional plan.
  2. Identify load-bearing assumptions and `intake` `route: "experiment"` questions whose outcome could materially
     change the plan.
  3. Execute worthwhile experiments in isolated sandboxes under `RUN/experiments/<exp-id>/` (or a disposable temp
     copy of the repo outside `WORKTREE` when code must change — never mutating product files in `WORKTREE`).
  4. Fold observed evidence into the plan (`RUN/inbox/<action>.md`) and `KNOWLEDGE/architecture.md`, and repeat until
     no material experiment remains (0 experiments = 1 fast pass).
- `Plan Improve` (`improve="always"`) and `improve-reconcile` remain intact after `plan` finishes its loop, so
  `--planning-review stage` still reviews the evidence-clarified plan and `--planning-review none` still gets
  experiment-driven planning inside `plan` itself.

### Sequence B — Carry `intake` `route: "experiment"` Questions & Decision-Linked `assumptions`

- Extend `shiploop_assumptions.canonical()` for `stage == "plan"` with two optional, strictly checked fields:
  - `"question"`: `Q<n>` linking an assumption row to an `intake` question.
  - `"effect"` (on `probed` rows): nonempty text stating how the experiment outcome changed or confirmed the plan.
- Add `assumptions.experiment_questions(state)`, `assumptions.check_experiment_questions(...)`, and
  `assumptions.experiment_question_lines(state, stage)`.
- Quote `intake`'s `route: "experiment"` questions into `research` and `plan` packets alongside the explicit
  `RUN/experiments/<exp-id>/` sandbox locator, and refuse a `done` `plan` (at `check`, `complete`, and `Plan Improve`
  import) that silently drops any `route: "experiment"` question.
- Recheck `_check_submitted_assumptions` before consuming a cached `shiploop check` yes so deleted experiment output
  files outside `WORKTREE` cannot slip past `complete`.

### Sequence C — Vertical End-to-End-First Slicing & Rolling-Wave Progressive Enrichment

- Add optional `slice` (`"spine" | "enrich" | "prerequisite" | "corrective"`) to `work_items` in
  `shiploop_navigator._normalise_work_items` and display it in `_work_item_block` when present.
- Enable rolling-wave `concerns` in `shiploop_concerns.py`: `W1` (and every single-item plan) must still map all 15
  concern rows explicitly, while later items (`W2+`) in a multi-item plan may use `"deferred"` instead of guessing
  all 15 rows before `W1` lands. `step-plan` for a deferred item gets an explicit reminder to assess concerns from
  `KNOWLEDGE/` and the completed slices without requiring pre-bound concern mappings.
- Update `DUTIES["plan"]` (duties 1, 3, 14, 16, 17): small cohesive single-surface tasks remain 1 item; multi-surface
  or feature-rich requests slice vertically (`W1` `slice: "spine"` delivers a thin working end-to-end slice with a real
  executable E2E smoke check inside `W1`; `W2..Wn` `slice: "enrich"` progressively enrich capability bands while all
  known requirements stay up front in `KNOWLEDGE/spec.md`).
- Flip `DUTIES["step-plan"]` duty 4 from horizontal layer cuts (*"module or layer boundary"*) to vertical
  end-to-end-first cuts while keeping `inline step-plan` packet heads strictly under 20,000 characters, and explicitly
  allow quick read-only/scratch probes in `RUN/scratch`.
- Upgrade `DUTIES["reflect-and-revise"]` duty 2 (multi-item form) to explicitly sharpen pending enrichment items
  (`W2+`) from what the completed slice revealed, carry `W1`'s E2E smoke check forward as a regression baseline, and
  run a small isolated probe in `RUN/experiments/` if a new consequential unknown surfaced.

### Sequence D — Hermetic Validation & Bounded Live Theory Checks

- Update affected hermetic suites (`shiploop-stage-spec`, `shiploop-loops`, `shiploop-packet-completeness`,
  `shiploop-improve-schedule`, etc.) and add a dedicated `test/shiploop-planning-loop.test.py` suite covering
  Sequences A, B, and C end-to-end through the real CLI and bundled Until Loop runtime.
- Add two `stage_suite` scenarios under `test/shiploop_e2e/stage_cases/plan/`:
  1. `plan/experiment-uncertainty-trap`: plants a `Q1` (`route: "experiment"`) where naive static reading predicts one
     runtime behavior while running an isolated probe exposes a concrete trap that flips the plan's architecture and
     queue.
  2. `plan/vertical-e2e-first-enrichment`: a multi-surface (storage + API + CLI/UI) request testing whether `plan`
     produces a vertical `W1` (`slice: "spine"`) with an in-W1 E2E smoke test followed by `W2+` (`slice: "enrich"`)
     enrichment items rather than horizontal layer slices.
- Run bounded live validation (1 sample per scenario via `stages.py live --samples 1`) in this isolated worktree
  before considering any merge to `main`.
