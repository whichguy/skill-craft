# ShipLoop: planning speed, size caps, step-relative tests and UI quality (plan, 2026-10-28)

Status: **proposal**. Execute: ask. Decisions for the owner are in section 7. They are ShipLoop behaviour
trade-offs and loop limits, which `AGENTS.md` "## Decisions" keeps for the owner.

Evidence:
- the D7 before-runs, in [the brownfield journal](shiploop-brownfield-baseline-journal.md) ("The before-runs") and
  [results/d7/before-runs.json](experiments/brownfield-baseline-20261028/results/d7/before-runs.json);
- the 2026-10-05 planning-ledger account (memory `planning-seven-minute-ceiling-2026-10-05`).

## 0. The request

The owner's words, 2026-10-28, in order:

> I don't want to have a 30-minute planning session at all. I'm not sure how that happened. I really want to eliminate
> any arbitrary small cap things that are hard-coded into any of the prompts or code. Identify the plan to either change
> our expectations or fix the things that weren't working as we intended. Also consider byproducts of things that we
> didn't consider and need to consider. Also consider if there are any proposals for changing something in the SDLC
> process that would help implement. One of the key considerations is that I really want to make sure that we use an
> extra fancy UI whenever we develop something, and I'd like to update the prompt template with that.

> It looks like we may have the test definitions wrong. The test should not test for every primary requirement on every
> iteration, but rather the primary requirements for that particular stage of the build. It's all relative to what the
> intention was for that particular step.

Read as five asks:
1. planning should be fast, with no "30-minute session";
2. remove arbitrary small hard-coded caps;
3. a plan that either changes expectations or fixes what did not work as intended, including byproducts;
4. SDLC process changes that would help;
5. an extra fancy UI by default for anything with an interface, written into the prompt templates.

Plus one more: tests relative to each step's intention.

## 1. How the 30 minutes happened

- On 2026-10-05 the owner set an alarm: "If planning takes more than 7 minutes, we need to rethink what we're doing in
  planning." The same day it was corrected to "anything where planning takes more than 30 minutes".
- That was a signal to rethink, never a budget. Two places then treated it as one:
  - the E2E harness reads `planning` "for the owner's 30-minute rule" (SPEC, the S-10 carve-out row);
  - the brownfield design's D6 "charged" discovery to "the 30-minute planning window", bounded by "the remaining
    allowance".
- An allowance invites work to fill it. The D7 runs planned for 17.4, 30.1 and 48.7 minutes on DeepSeek flash.
- **Correction:** there is no planning allowance. D6 is withdrawn. The harness keeps reporting the planning window as a
  record, with its Improve share, and judges no run by a number (decision Q1).

## 2. What the evidence says (D7 before-runs, n=1 per case)

| | user-listing | ticket-assignment | ticket-escalation (follow-on) |
|---|---|---|---|
| Hidden checks | 11/11 | 18/18 | 14/14 (7 kept from run 1) |
| Planning window | 17.4 min | 30.1 min | 48.7 min |
| of it Improve | 10.0 (58%) | 17.2 (57%) | 25.7 (53%) |
| of it authoring | 7.4 | 12.9 | 23.0 |
| Discovery | 0.6 min | 1.6 min | 2.4 min |
| Refusals | 25 | 27 | 18 |
| `environment.md` after | — | 72 KB | 87 KB |

1. **Correctness held without any baseline.** Both planted defects were fixed, and the follow-on lost nothing. On these
   cases the brownfield design's as-is account closes no correctness gap. The instrument fits in context, so "too big to
   read" is untested.
2. **Improve review is more than half of planning in every run.** The spec stage's own writing took 0.5-1.4 min, and its
   review took 2.2-7.5 min.
3. **Living files grow, and every later stage reads and reviews them.** The follow-on's extra planning time sits in
   test-strategy, step-plan and carry-forward, the stages that work over those files.
4. **Ten caps on what the model writes refuse and force a rewrite.** Section 4 lists them. They produced 3-5 refusals
   per run, each a turn of trimming meaningful text.
5. **Step-relative tests are half there.** Section 5 has the detail.

## 3. Change the expectations (E)

- **E1.** No planning allowance. Planning is expected to take minutes, not tens of minutes. Each E2E card shows the
  window and its Improve share. Growth across runs of the same product is a defect to fix, not a budget to manage.
  Whether to set a target figure at all is Q1.
- **E2.** The brownfield as-is account (design section 10, step 1) is not built on this evidence. D7 showed no
  correctness gap on cases that fit in context. The value of recording knowledge has to come from cases that do not fit.
  Q5 holds it until a large case shows a gap.
- **E3.** Cost is judged in minutes and turns until the Claude-host Ollama runs measure tokens (F7).
- **E4.** The E2E subject stays DeepSeek flash after the 2026-10-29 Grok reset; Grok runs only checks that need
  another host (owner, 2026-10-28, `AGENTS.md` "## Decisions", 917e0c2b). So the waves' reruns stay comparable
  with the D7 before-runs. Expectations are per subject. Sonnet plans a small request in about 5 minutes, DeepSeek flash in 17-49, and
  Luna xhigh took 375. A change is measured on the E2E subject, and a ship decision on the agreed pairing.

## 4. Fix what did not work as intended (F), ranked by measured gain

### F1. Improve at planning (53-58% of the window) — largest gain

- **Today.** A model-run Improve review follows spec, test-strategy, plan and step-plan.
- **Proposal.** One review over the finished planning bundle (spec, environment, architecture, plan) at prepare, instead
  of one per stage. The script checks at each stage stay as they are.
- **Measured potential.** The removed reviews cost 10.0, 17.2 and 25.7 min. One bundle review costs roughly the largest
  single review (about 3-9 min). The expected saving is about 40-50% of each planning window.
- **Risk.** A defect found late costs a rewrite of more than one document. On 2026-10-05 the ledger found review missed
  the costliest defect anyway (the test-red revise).
- **Measure.** Rerun the three D7 cases. The hidden checks must stay at 43/43, and planning should drop.
- This changes the Improve schedule the owner set in 2026-09 (planning stages plus the last item), so it is Q2.

### F2. Arbitrary small caps — remove them (owner)

The inventory of `skills/shiploop/scripts` falls into three kinds.

**Refusing caps on the model's own text.** These are the ones the owner means.

| Constant | Value | What it bounds | Seen refusing in D7 |
|---|---|---|---|
| `STEP_TASK_LIMIT` | 700 | a step's task | yes (733) |
| `STEP_PROOF_LIMIT` | 600 | a step's proof | |
| `STEP_CRITERIA_LIMIT` | 1,200 | the criterion texts a step names | yes (1,304; 1,220) |
| `STEP_NOTES_LIMIT` | 1,200 | a step's notes | |
| the decisions field (navigator, 1,200) | 1,200 | an implement result's decisions | yes (1,214; 1,466) |
| `OPEN_ASSUMPTIONS_LIMIT` | 1,200 | a work item's open assumptions | |
| `ROWS_LIMIT` | 1,200 | concern rows | yes (1,370) |
| `WORK_ITEM_CONTEXT_LIMIT` | 2,500 | a work item's context | yes (2,772) |
| `NARRATIVE_LIMIT` | 900 | the narrative block | |
| `HEADLINE_LIMIT` | 100 | the result headline | yes |

- **Why they exist.** Later packets print these fields in their look-back (S-7: printed packets stay small).
- **Proposal: spill, don't refuse.**
  - A field of any length is accepted.
  - When it is longer than its print budget, ShipLoop writes it whole to a run file. The look-back prints its first
    line and the file's path, which S-7 already allows ("large planning context is fine in files").
  - The headline stays one line, because it is a single display line; it gets no character limit.
  - One supported version: each refusal is removed, and no fallback keeps it.

**Truncating display limits.** `PRINT_LIMIT` 16,000, `HEAD_LIMIT` 20,000, `TAIL_CHARS` 6,000, `PAGE_BYTES` 12,000,
`SUMMARY_LIMIT` 400, `FIELD_LIMIT` 2,000, `NOTE_LIMIT` 2,000, `BLOCK_LIMIT` 6,000, `ARGS_LIMIT` 2,000 and
`INSIDE_CHARS` 100.
- These cut what the model or the owner sees.
- Proposal: keep a limit only where the full text is one command away, which means the cut names that command. Otherwise
  spill to a file the same way.
- An audit step lists each one's reader and whether its cut names the rest.

**Safety guards.** `SPEC_LIMIT` 256 KB, `MAX_FILE_BYTES` 2 MB, `PAGE_TEXT_LIMIT` 12 MB, `TRACE_LIMIT` 32 MB and
`DIFF_CELL_CAP` 4M.
- These protect a reader from a binary or runaway file, not the model's writing.
- They stay, each with its reason in a comment.

**Done when:**
- a script lists every numeric limit in `skills/shiploop/scripts` with its kind;
- a test fails if a new refusing cap on model text appears;
- the D7 cases rerun with no size refusals and no growth in packet head bytes beyond the spilled references.

### F3. Step-relative test definitions (owner)

**Already right.** A test-spec writes "one `test_cases` row per ID the step plan's focused commands list; no other ID"
(`DUTIES["test-spec"]` step 1). Tests are written for the step's intention.

**Two places reach past the step:**
1. **The primary-coverage gate** (`shiploop_primary`, TS1).
   - At the last work item's done test-spec, every primary requirement of the run must have a case in some item's
     test-spec. When one is missing, the refusal asks the last item to add it: "Missing: R-20. Add a case …". That
     attaches a test to a step whose intention it is not.
   - Fix: move the check to where intentions are set.
     - At step-plan, each step names the requirements it serves.
     - At plan, ShipLoop checks that the run's primary requirements are all served by some step.
     - A gap is a plan gap, closed by adding or widening a step.
   - Test-spec stays strictly step-relative, and verify still runs the whole existing suite as regression.
2. **The test-strategy wording.** It plans "per requirement" from "KNOWLEDGE/spec.md and the spec changes since the run
   began".
   - In the follow-on it planned only its own R-13 to R-20, so it behaved well.
   - The wording still invites whole-spec planning as the spec grows.
   - Fix: plan for the run's spec changes plus the preservation set they touch (the design's consumer-scope rule).
     Everything else is covered by the existing suite, run as is.

This is Q3.

### F4. Living files that only grow (byproduct; follow-on cost)

- **Today.** `environment.md` was 72 KB after one run and 87 KB after two. Every stage that reads it pays, and Improve
  reviews it again.
- **Proposal.**
  - Living files hold the current truth, rewritten in place: commands, harnesses, targets, decisions.
  - Per-run narrative (what was tried, evidence logs) stays in the run folder and the commit message.
  - A record (not a refusal) on the E2E card shows each living file's size after each run.
- **Measure.** The follow-on's test-strategy, step-plan and carry-forward minutes return to the first run's.

### F5. Lint at Improve (template bug) — fixed, held

- Commits 18844f21 and 8764d1b1 (first made on branch `claude/priceless-hertz-be6123` as d0916465 and e740819b; the
  branch is not merged, these are the same patches).
- They land with this plan's first release, so the D7 after-runs share one base.

### F6. Repeated model habits

- `--check-only` at Improve, and a skipped skill call at a new Improve stage, each cost about a turn, several times per
  run.
- **Proposal.** Make the producer and Improve callbacks look different: an Improve-only `improve-done` verb, so the
  producer's preview habit has nothing to attach to.
- Low gain, so it rides with F1. If F1 removes most planning Improve stages, half of these disappear with them.

### F7. Harness

1. ~~E6 slices should take the run lock.~~ Done on main in 98e7aff0 (a step slice holds its case lock), so run.py no
   longer takes a live slice for an orphan. A separate runs root is needed only beside slices from older checkouts.
2. Tokens and cost on Claude-host Ollama runs. E3 needs them.

## 5. Byproducts we had not considered (B)

- **B1. Knowledge slows the next run.** Every byte a run leaves in a living file is read and reviewed by every later
  run. The brownfield as-is account would add more. Any knowledge added must pay for itself in a later run's minutes
  (F4, E2).
- **B2. Review cost scales with document size.** Spec Improve took 2.2, 6.2 and 7.5 min as the spec grew. F1 and F4
  compound.
- **B3. Removing caps can grow packets.** Spilling to files keeps printed heads small. Measure packet head bytes
  before and after (S-7 record).
- **B4. A budget becomes a target.** The 30-minute "allowance" shows how a number turns into expected work. No new
  figure should enter a prompt as an allowance.
- **B5. The host keeps context across stages** (peak 157-160K). Same-shaped commands with different rules invite
  carried-over habits (F6).
- **B6. Our instrument fits in context.** Conclusions about large repositories need a large case (P6).
- **B7. Fancy UI costs time and needs observable acceptance.** Model judgement is not evidence (S-9). The UI rule must
  name what a script or a rendered check can observe (P4).

## 6. SDLC process proposals (P)

- **P1. Intention-first steps.**
  - A step's plan names its intention: the requirements it serves and the outcome it adds.
  - Its tests, Improve focus and done-when are read against that intention, never the whole spec.
  - Coverage of the run's request is a plan property, checked at plan (F3).
- **P2. One review per phase.** One Improve over the planning bundle, one per implemented item (as today) and one at
  the end (F1).
- **P3. Living files are rewritten, not appended** (F4).
- **P4. An extra fancy UI by default** (owner). Template text for the prompts (`shiploop_prompts.DUTIES`). It is
  generic, with no stack or library named:
  - **spec:** "When the deliverable has a user interface (a page, an app screen, a rendered report, a terminal
    interface), add a non-functional requirement for a deliberately designed, polished interface, not a default one.
    Write its observable criteria:
    - a consistent visual system (spacing scale, type scale, a color palette with a light and a dark theme);
    - designed empty, loading and error states;
    - a layout that works at a narrow and a wide width with no horizontal overflow;
    - visible focus states, and contrast that meets WCAG AA;
    - motion only where it explains a change, and respecting reduced motion;
    - one consistent icon set."
  - **plan:** "The `ui` concern row records the design system choice (tokens, components, theme) as an AD-<n>, before
    any screen is built."
  - **step-plan:** "A step that changes an interface names the UI criteria it meets in its Design basis."
  - **test-spec and product-acceptance:** "The UI criteria are checked on the rendered interface: captured in both
    themes and at both widths, with each criterion observed in the capture (a contrast measurement, an overflow check, a
    focus-state capture). Structure alone does not close a UI criterion (as today for rendered interactions)."
  - Byproducts: more minutes per UI feature, and a capture tool per platform, which the existing browser capability
    record covers. The criteria are observations, so acceptance stays scripted or rendered, never model taste.
- **P5. Brownfield, re-scoped.**
  - Keep D8, done.
  - Keep D9's quoted open questions only where a run has open questions.
  - Defer the as-is account (design section 10, step 1) until a large case shows a correctness or cost gap.
  - Take the consumer-scope rule from section 10, step 2, in F3.
- **P6. A large brownfield case.** A base well beyond the subject's context, for example 30-60k lines, with a request and
  a follow-on, so the regime the design targets is actually tested. It is an instrument for E2 and B6.

## 7. Decisions for the owner (Q)

| # | Decision | Recommendation |
|---|---|---|
| Q1 | A planning target figure, or none? | None in prompts or code. The harness records the window and Improve share on every card, and a rise across runs of one product is a defect |
| Q2 | Improve at planning: one bundle review at prepare instead of after spec, test-strategy, plan and step-plan | yes, measured on the three D7 cases (hidden checks must stay 43/43) |
| Q3 | Step-relative tests: move primary coverage from the last test-spec to plan; tighten the test-strategy wording | yes |
| Q4 | Remove every refusing cap on model text; spill to files instead | yes; keep the safety guards; audit the display limits |
| Q5 | Brownfield: defer the as-is account until a large case shows a gap | yes |
| Q6 | The fancy-UI template text (P4) as written | yes, with any changes to the criteria list |

## 8. Order of work

- **Wave A**, one release:
  - F5 (land the lint fix);
  - F2 (remove refusing caps, spill to files);
  - F3 (step-relative coverage and test-strategy wording);
  - P4 (fancy-UI template text);
  - (F7.1 already landed on main, 98e7aff0.)
  - Verification: rerun the three D7 cases from the release commit.
- **Wave B**: F1 (one planning review), measured by the same rerun, then F4 (living files) and F6.
- **Wave C**: P6 (large case) and F7.2. Revisit E2 and Q5 with that evidence.
- **Batch discipline.** Each wave lands as one release with one verification batch. No engine change lands while a
  batch runs.

## 9. Coordination with design T (2026-10-28)

The owner asked overlapping sessions to stop and agree on owners. Design T (session "E2E (fork)", branch
`feat/per-step-iteration-6adde0`, `docs/shiploop-review-after-tests-design-2026-10-27.md` §8-§9) accepted this split.

**Design T owns:**
- the step and stage structure: verify retired, gates in each step, a commit stage per step, step skills;
- test gradations, where each step runs its own cases and the full regression runs at the last step;
- the per-step bookkeeping;
- its own F5 and F6, which are not this plan's (this plan's items are "plan F-n");
- the ask-agent step boundaries.

**This plan owns:** plan F2 (spills), plan F3 (coverage at plan), P4 (fancy-UI text) and the Improve-lint fix.

**Order:**
1. Lanes C (F6+F5), then B (2d and step 3), merge onto the design T branch.
2. Wave A rebases there: design T names the commit to build on.
3. Design T lands on main after its pilot E2E rounds and README, not before 2026-10-29.
4. The lint fix (18844f21, 8764d1b1), D8, the node-tickets case pair and this plan's documents land on main now. Design T
   rebases onto them, and they meet at `test/test-groups.test.py`'s suite counts.

**Constraints for the Wave A rebase:**
- **Plan F3.** Test gradations already make each step run its own cases (`iteration.due_cases`, `active_commands`).
  Request coverage at plan does not exist on design T and stays this plan's to build. It must line up with
  `due_cases` and the step-plan criteria gate (`_check_step_sizing`).
- **Plan F2.** Lane F6 adds a "Lint coverage:" line right after "Result:" in every lint block and in `gate()`'s two
  refusals. A display cut that pages or trims a lint block keeps the Result and Lint coverage lines together.
- **The lint fix.** On design T's base the step review belongs to document (2b-2), not implement, so 18844f21's
  "implement review" wording is checked when design T rebases onto it.

## 10. Landed

- **Plan F2 (2026-10-29), on the design T release `9d8c2793`.** Every refusing cap on the model's text is gone: the work
  item context, open assumptions, step task, Proof and criteria, step notes, concern rows, test layers and the headline's
  100 characters. The step block, the concern rows and the test layers print a field whole within its print budget
  (`STEP_TASK_PRINT` 700, `STEP_PROOF_PRINT` 600, `STEP_CRITERIA_PRINT` 1,200, `ROWS_PRINT` 1,200, `LINES_PRINT` 1,200);
  past it they print what fits and name `RUN/fields/<action>-<field>.md`, which `emit` writes from state
  (`shiploop_fields`). The offline render diff of `node-fix-bug` (inline and ask-agent, run directory 83 and 163, CLI path
  96) passes with `--unit F2`: every printed text shrinks, and the head table is rewritten for the stages design T left.
  `test/shiploop-packet-bounds.test.py` lists every numeric limit by kind (`LIMIT_KINDS`) and fails on a new one without a
  kind or on a refusal that states a limit. Measured 2026-10-29 (LEARNINGS, "Wave A before and after"): the three D7 cases rerun on Codex Terra with hooks on had 0 size-limit refusals after, 2 before.
- **Plan F3 (2026-10-29), on F2.** Primary coverage moves from the last test-spec to the plan.
  - `shiploop_primary.check_queue` replaces TS1's `check_test_spec`. A done plan, and a done carry-forward that replaces the
    future queue, must leave every primary requirement of the spec in some work item's `follows`, and each `follows` ID
    needs an entry in `spec.md` or `architecture.md`. The exit is to widen a work item or add one.
  - A work item takes an optional `follows` (shape only: R-<n>/AD-<n>, each once). The plan and carry-forward packets print
    each primary ID with the items that follow it; the last test-spec no longer gets the coverage block, so each
    step's tests follow that step's own intention (`iteration.due_cases`, `active_commands`).
  - Retired with one supported version: `suite_requirements`, `canonical_suite`, `test_spec_coverage` and TS1's refusal.
  - Offline render diff, same four settings as F2, against the release: all 10 stages pass; the carry-forward packet grows
    by 165 characters (the `follows` row shape and the coverage rule), approved in `packet_changes.json` key F3.
  - Measured 2026-10-29 (LEARNINGS, "Wave A before and after"): hooks-on Terra, three cases, hidden checks 43 of 43 before and after; no run
    left a primary requirement out of `follows`, so the refusal itself is exercised by tests only.
- **Plan P4 (2026-10-29), on F3. The fancy-UI template text (Q6, approved 2026-10-28).**
  - The spec's non-functional duty states the observable criteria for a deliverable with an interface (visual system with a
    light and a dark theme; empty, loading and error states; narrow and wide layouts without overflow; focus states and
    WCAG AA contrast; motion only where it explains a change, honoring reduced motion; one icon set). The step plan's Design
    basis names the ones a step meets. A test-spec row for a UI criterion and product acceptance close it only on the
    rendered interface in both themes and at both widths. No stack or library is named.
  - **Changed from the draft in section 6.** The plan stage would have recorded the design system as an AD-<n> on the
    `ui` concern row, but the plan head ends its required text exactly at the 19,500-character bound, so the sentence
    moved to the step plan's Design basis: the first UI step records the design system, which is where the first
    screen is built.
  - The criteria are observations, so acceptance stays scripted or rendered, never model taste (B7). Not measured: a UI
    case (the D7 cases have no interface), and the extra minutes per UI feature.
- **Review of Wave A (2026-10-29): an independent reviewer read the engine diff and the author checked it again; every confirmed
  finding is fixed in the commit that follows F2, F3 and P4.**
  - **Field-file names (release blocker).** A step ID was checked only for whitespace and became part of
    `RUN/fields/<action>-<id>-task.md`, so `x/../../../../outside` wrote outside the run, a 230-character ID made every later
    `next` fail, and a NUL raised. `shiploop_fields.component` now turns any name into one safe component (letters, digits,
    `.`, `_`, `-`, at most 80 characters, a digest of the original when it changed), so no step ID is refused and two
    different IDs never share a file.
  - **Primary block overflowed the plan head (release blocker).** The head budgets were measured on a walk whose spec
    records no primary requirements. With one, the plan head's required text ended at 19,686 (bound 19,500); with six, the head
    passed the 20,000 cut and a host that keeps only the first and last 10,000 characters lost the duties. The block is one short
    line at plan (at most six IDs, then how many more) and a fuller one line at carry-forward, `PrimaryRequirementHeadTests`
    measures one, six and thirty, and the plan head ends its required text at or under the bound for any number.
  - **Cuts that lost the content.** `fields.block` printed only a block's label when a long first row did not fit, and
    `fields.inline` printed only the first line of a multi-line field; a block now prints some of its first row, and an inline
    field its first characters on one line.
  - **Also fixed.** The Improve opening shows a headline cut as the narrative does; the `context` command writes the field files
    it names; the carry-forward duty and refusal say a completed or current item counts and only a future item can be widened;
    the protocol and carry-forward references document `follows` and the coverage rule; one stale comment.
  - **New guards.** A hostile or long step ID stays inside `RUN/fields/`; a new inline `len(...) > N` check fails
    `test_no_inline_length_check_is_a_new_cap`.
  - **Left as is (reviewer residuals, judged low):** a retired ID is accepted in `follows`, and `add-work` rows get only a shape
    check. P4's criteria are prompt text and no gate checks them, by design (B7).
