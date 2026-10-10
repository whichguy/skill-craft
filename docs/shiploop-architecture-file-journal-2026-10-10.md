# The architecture file in the knowledge home: journal (2026-10-10, batch 1012 task A)

Plan v5 task A. Base `e1dc59dc` (the batch integration branch), branch `batch1012a-1bbefb`. The plan is
`docs/shiploop-commit-and-spec-lifecycle-plan-2026-10-10.md` (sections 0d and "Plan of action v5"). Packet text (`render()`,
`packet_head()`, `DUTIES`, `stage_lines`, `_render_improve`, `_checked_line`, `_stage_gates`, `shiploop_prompts.py`) belongs to the packet
owner (the session on branch `exp/four-part-packet-631117`) and was not edited; what it needs to print is under "Lines for the packet
owner". The design and its two audits are kept whole in
`docs/experiments/commit-spec-design-20261010/architecture-design-and-audits.json`; where `task-a.md` overrode them, the table below says so.

## Do not release until the packet owner's sentence has landed

This series lands on the batch branch and then on `main`. **Landing is not a release. Do not release `shiploop` until the plan and
step-plan duty sentence (L2 below) has landed.** Without it, the plan packet only lists `architecture.md` among the files it keeps up to
date, the model is never told what it holds or to number decisions `AD-<n>`, and `prepare` refuses runs whose plan wrote nothing for it
(or writes a stub). The release also needs the E2E round the release preflight demands (`AGENTS.md`); this task ran no live round, only the
offline evidence below.

## Question

Can the knowledge home carry how the product is built (stack, structure, numbered decisions) as a file of its own, kept apart from the
spec, protected from silent loss the way the spec's `R-<n>` requirements already are, without a packet-text change and without a refusal
costing a cleared-context model more than one turn? And can the module name the files an inner stage grounds its decisions in, for the
packet owner to call?

Owner rule behind it: **spec = the contract (survives a change of stack); architecture = stack and structure (survives a change of
spec); separate files, no leakage.**

## What was built

| Concern | Where (all in `skills/shiploop/scripts/shiploop_knowledge_home.py` unless named) |
|---|---|
| The file and the one wording of what it holds | `ARCHITECTURE`, `ARCHITECTURE_HOLDS`; the module header lists it |
| It is a living file; plan and step-plan keep it; prepare requires it | `LIVING`, `CLOSES["prepare"]` (with the other living files, before the feature files), `STAGE_FILES["plan"]` (last) and `["step-plan"]`; `stage_lines` already prints the "keeps these up to date" and "refuses prepare if any of these is missing" lines from the tables, so no packet edit |
| A refused prepare says what the new file holds | `check()` missing-file branch: one line `architecture.md holds <ARCHITECTURE_HOLDS>.`, only when the file is among the missing |
| One retention loop for requirement and decision IDs | `_DECISION_ID` (`\b(AD-\d+)\b`), `_RETAINED` (a tuple of rows: file, pattern, the refusal's name for the file, its word for one ID, the heading a dropped one moves under), `_committed(repo, name)` (replaces `_committed_spec`), the loop at the end of `check()` |
| The refusal: fix, absolute path and command on line 1; the IDs on line 2 in full | `check(state, stage, command="complete")`; `shiploop_navigator._knowledge_gate(..., command)` and its `improve-complete` call pass the route's own verb |
| One "present" rule for the close and for grounding | `_filled(path)` |
| The files an inner stage grounds its decisions in | `_GROUNDING`, `GROUNDING_LABELS`, `grounding(state)` |
| Docs | `references/project-knowledge.md` (table row, "Choose one authoritative home", closes paragraph, the design-decision sentence, two stale statements), `references/service-discovery.md`, `references/testing-and-documentation.md`, `SKILL.md` |
| Spec | `test/shiploop_e2e/SPEC.md` S-11 (and one phrase of S-10), in its own commit |
| Note | `changes/shiploop/architecture-file.md`, `bump: minor` |

## Commits

| Commit | What |
|---|---|
| `eafdf395` | The file is a living file; plan and step-plan keep it; prepare requires it; the refusal's one hint line; `HomeFixture`; the two pins that named the old tuple; the route test through the real CLI; the change note |
| `f217c5f1` | One retention loop (`AD-` beside `R-`); the refusal shape; `check()` takes the route's verb; one route test per gate |
| `76f1ebbd` | `_filled`, `grounding`, `GROUNDING_LABELS` |
| `ef8b91a7` | The references |
| `c55db6ba` | SPEC S-11 and one phrase of S-10 (own commit, `No-Change-Note: harness spec amendment`) |
| `51a5609d` | The boundary test that killed the last mutation survivor; the mutation record, the saved-home scan and the 250-column margin; the design evidence copy |
| (this commit) | This journal and the `LEARNINGS.md` entry |

## Decisions: the design, its audits, and where `task-a.md` overrode them

The design built and tested a scratch prototype; two audits (yagni and code) found no blocker and said "build roughly a third of it".
`task-a.md` decided where they and the design disagreed.

| Item | Disposition |
|---|---|
| ID prefix `D-<n>` (the contract) | **`AD-<n>`.** One saved home already numbers product decisions `D-1`..`D-6` inside `spec.md` and cites them from 7 files, so `D-` is a home-wide namespace the model uses. The check is per file so it could not misfire, but tests and plans citing "D-3" would be ambiguous, and with "one supported version" the prefix cannot change once a home carries IDs. `home_scan.json`: no saved home uses `AD-<n>`; one uses `D-<n>`. The final name is `AD-<n>`; the main session relays it to the packet owner, and "Lines for the packet owner" below uses it |
| `_Retained` class, public `RETAINED` / `dropped_ids`, `Pattern` / `NamedTuple` imports (design) | Cut (yagni): a tuple of rows looped inside `check()`, one `_committed`, nothing public |
| Refusal with the IDs on line 1 (design) | **Changed (code audit, correction 1):** at a 100-character path with 2 IDs the command started at column 277 and a deleted file (25 IDs) pushed the fix to column 299 at a 60-character path. Line 1 carries no ID list; line 2 names every ID, no cap |
| "Keep every earlier decision in `<abs>`: restore the dropped AD-<n> lines or move them under a 'Superseded' heading with the reason, then run the same `<complete\|improve-complete>` command again." (task text, an example) | **Shortened to "Restore the lost AD-<n> in `<abs>` or move it under 'Superseded', then run the same `<complete\|improve-complete>` command again."** The example wording ends in column 306 for a 120-character path, so `cut -c1-250` cuts the command; the shortened line ends in column 240 (and 248 for `improve-complete`). The reason rule (`under a 'Superseded' heading with the reason`) moved to line 2. `cut_margin.json`: `complete` fits up to a 130-character path to the file, `improve-complete` up to 122 (the CLI's `ShipLoop navigator: ` prefix included). Not a threshold the code enforces: the test asserts it at a 120-character path |
| The same shape for the spec's refusal | Done: its two pins (`no longer mentions R-2`) stay green because line 2 keeps that sentence. One template serves both files (S-12) |
| The route's own verb | `check()` takes `command` (default `complete`); the `improve-complete` call of `_knowledge_gate` passes `improve-complete`. A "same command" must be exact for a cleared-context model on both routes. Two lines of the navigator, outside packet text |
| The improve-complete exit | **Two steps, tested** (code audit, correction 3): the knowledge gate runs before `_improve_change_gate`, so the fix the parent writes is the review's uncommitted edit and the next `improve-complete` meets the commit refusal that names `improve-commit`. The test submits both refusals and the accepted call. A note beside the improve route, not a change to line 1 |
| The missing-file hint line (yagni cut it as a one-file special case) | Kept by `task-a.md` decision 4: a cleared-context prepare model has no other description of the new file. It is one line, only when the file is among the missing. If the packet owner's prepare line (L2) prints `ARCHITECTURE_HOLDS`, the hint duplicates it; decide then which carrier stays (open) |
| `ARCHITECTURE_HOLDS` said "the stack and runtime" (code audit) | "the stack (language, frameworks, dependencies and why)"; runtime versions and working commands stay in `environment.md`: one authoritative home (the reference table row says so; a test pins that "runtime" is not in the wording) |
| `grounding()` shipped with no caller (both audits cut it) | Kept (`task-a.md` decision 6: the packet owner depends on it). Table-driven (`_GROUNDING` pairs; the module's own `_expand` for `{feature}`), one `_filled` for the close and for grounding |
| Guard-only tests (first run, credential screen, outside a checkout, the LIVING reader, the progress-data test), A7, A8, two change notes, cosmetic doc edits | Cut, except: the first-run and the word-boundary guards stay (they pin new code paths and killed a mutant), and the `LIVING` membership is one assertion in the first test (no reader test). The progress view needs no change: `_ARCHITECTURE_PATHS` already lists `docs/shiploop/architecture.md` |
| Four stale statements the code audit found | Fixed: `service-discovery.md`, `testing-and-documentation.md`, `project-knowledge.md` ("existing discovery/environment/decision notes" and "a decision file only when no suitable home exists"), the module header. `SKILL.md`'s knowledge-home list gained the file (it enumerated the others) |

## Method and evidence

Fail-first for each behaviour: the tests were written and run before the code and seen to fail for the intended reason (commit 1: 5 errors
and 6 failures in the knowledge suite, and the route test failing on the previous source with `0 != 1` because prepare did not name the
file; commit 2: 5 errors and 6 failures, and both route tests failing because the dropped ID was accepted (exit 0) or the commit gate came
first; commit 3: 9 errors, the API absent). Real-Git tests set `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL=/dev/null`; the route tests
run the real CLI and read the heading to use from the refusal.

| Evidence | File | Result |
|---|---|---|
| Design and two audits, whole | `docs/experiments/commit-spec-design-20261010/architecture-design-and-audits.json` | the prototype, 15 mutants, 27-home prepare-refusal count, the replay, the bind-tree experiment, the credential probe |
| The saved homes, read only | `docs/experiments/architecture-file-20261010/home_scan.py`, `home_scan.json` | 29 homes: the prepare close finds only `architecture.md` missing in 29 of 29; `AD-<n>` used in 0, `D-<n>` in 1; `spec.md` has 45 committed versions in 16 consecutive pairs and none drops an `R-<n>`; `architecture.md` has no version anywhere, so its base rate is null |
| Line 1 against `cut -c1-250` | `docs/experiments/architecture-file-20261010/cut_margin.py`, `cut_margin.json` | where "again." ends, by path length (80 to 140) and verb; no ID on line 1 at any length |
| Mutation check | `docs/experiments/architecture-file-20261010/mutation_check.py`, `mutations.json` | 35 one-line breaks of the module and the knowledge gate, 35 killed in the last full run (sources clean in Git before and after). The first full run killed 34: the pattern without its trailing `\b` survived because the probe `AD-3a` matched `AD-3`, an ID the committed version already held; the probe is now `AD-12a` |
| Footprint | see "Results" | |

## Findings

- **Firm.** The prepare close on a home an earlier version wrote refuses naming only `architecture.md` (29 of 29 saved homes; vacuous as
  evidence about false refusals, since none of those runs could have written it). The relevant evidence is constructed and tested: a
  one-line file passes, a follow-on is refused once and then satisfied by the committed file, a heading or no IDs passes. In the saved
  event logs the prepare close was refused for missing files 0 times organically (1 seeded run), so the refusal is a safety net and the
  plan packet's "keeps these up to date" line carries the request.
- **Firm.** `AD-` collides with nothing in 29 saved homes; `D-` is in use in one. Decisions are recorded at all in 2 of 27 homes (the
  design's count), so for the example apps the file will mostly restate `environment.md` and `test-strategy.md`.
- **Firm for the spec, unmeasured for the architecture.** The HEAD-baseline retention rule dropped an `R-<n>` in 0 of 16 consecutive
  `spec.md` pairs here (and 0 of 360 consecutive pairs over every home file in the design's replay of 27 homes). `architecture.md` has no
  saved version: null, not zero.
- **Firm.** A line-1 refusal that lists the IDs loses its fix to `cut -c1-250`; the shape now measured (`cut_margin.json`) does not.
- **Interim: the shared gap.** The baseline is `HEAD`, so a review that commits its own edit through `improve-commit` and then runs
  `improve-complete` is invisible to the retention check, for `spec.md` too. Measured: an experiment in the design (HEAD baseline sees
  nothing; the bind snapshot tree sees the dropped ID). It is not a rare path: a non-ShipLoop commit edited `spec.md` outside any gate in 15
  of 27 homes (26 commits) and some home file in 18 of 27 (70 commits), and a plan review is the likely editor of `architecture.md`. It is
  deferred for the measured reason (0 drops), not for rarity. Within a run, plan is committed after its first accept, so a revise is gated
  against the previous draft's IDs: a false-refusal source, not observed.
- **Exploratory: the credential screen.** The shared screen flags ordinary architecture lines (the design's probe flagged 4 of 10, the
  code audit's 5 of a typical set: `Password: bcrypt, cost 12`, `SECRET_KEY = os.environ['SECRET_KEY']`, `config.api_key = process.env.API_KEY`,
  `token = get_token()`, `Authorization: Bearer <access token>`), and `check()` screens every home `*.md`, so one flagged line in
  `architecture.md` refuses every later stage that touches the home. The screen is unchanged (out of scope). Mitigation: the reference
  table row says the file records names and shapes, never secret values or code that assigns them, and L2 below carries the same clause.
  **Trigger:** count the credential refusals that name `architecture.md` in the first live pair; if they are frequent the fix belongs in
  `shiploop_privacy` (S-12), not here.
- **Exploratory: cost.** A fifth mandatory file adds a write at plan, a "keeps up to date" line in every step-plan packet, and more for
  plan reviews. Not measured here.

## Deviations from the task text

- `HomeFixture` was kept (decision 7: "unless a test needs it"): `ArchitectureTests` and `GroundingTests` need the repository fixture and
  would otherwise re-run `KnowledgeTests` (which `KnowledgeAfterEveryStageTests` already does once more).
- The line-1 wording is shorter than the decision's example and `check()` takes a `command` (see the table).
- The change note landed in the first commit, not the docs commit: the boundary check is range-wide, but a note belongs with the change.
- The SPEC commit also changes one phrase of S-10 (the list of gates that stand in for review under `none`); `review.py`'s follow-on
  prompt was not edited (cosmetic).
- `_filled` catches `OSError`, so an unreadable file in the home reads as missing in the close (it used to raise) and in `grounding`.
- The prepare route test commits the home first (`git commit` in the test repository), as an earlier version's run would have left it.

## Deferred, and what would build each

- **Bind-tree or run-start baseline for retention (both files).** Trigger: a committed ID dropped in a live pair (grep the work repos'
  history), or a review that rewrote a retained file. If built, use the run's start commit rather than the bind tree (audit correction 2),
  which also stops a producer's first-draft IDs being held hostage on a revise.
- **Harness fields** `architecture` (bool) and `decision_ids` (list, null when the file is absent). Trigger: the first live pair; its
  test goes in a file other than `test/shiploop-e2e.test.py` (at its time limit). It would import the private `_DECISION_ID`, as `run.py`
  imports `_REQUIREMENT_ID`.
- **`document` in `STAGE_FILES`.** Trigger: the first live pair shows `architecture.md` stale at handoff. One tuple, no code.
- **The hint line against the packet owner's prepare line.** Trigger: the packet owner prints `ARCHITECTURE_HOLDS` at prepare; then keep one
  carrier.
- **Credential screen for architecture lines.** Trigger above.
- **Two path-length-sensitive tests, not caused by this change:** `shiploop-status-display`
  `test_every_dry_run_packet_carries_the_block_inside_the_kept_head` fails at this worktree's 94-character path (`END` at 8004 > 8000,
  packet `ask-agent`, `revise`, sequence 20) with this change and with the base source (`git checkout e1dc59dc --` of the two edited
  modules, run, restored: the same 8004); the design reported one more in `shiploop-workspace`
  (`test_return_projection_stays_current_across_terminal_cold_and_report_packets`), which passed here at 94 characters. A real run in a
  longer path may already be past the status window; worth its own task.

## Lines for the packet owner

Engine data you can call: `knowledge_home.grounding(state)` -> `[(label, abs Path)]` in `GROUNDING_LABELS` order (absent files left out),
`knowledge_home.ARCHITECTURE_HOLDS` (the one wording of what the file holds), `knowledge_home.ARCHITECTURE`. **The decision prefix is
`AD-<n>`**, not `D-<n>`.

- **L1** `stage_lines` intro sentence: "Earlier runs' spec, environment, architecture and features are there; open a file when this stage
  needs it."
- **L2** after the `if stage == "spec":` block (packet text, yours):
  `if stage in ("plan", "step-plan"): lines.append("architecture.md is how the product is built, apart from what it must do (that is spec.md): it holds " + ARCHITECTURE_HOLDS + ". Start from the committed file and keep every decision ID (AD-<n>): change a decision in place, or move one that no longer holds under '## Superseded' with the reason and its replacement's ID. ShipLoop refuses a version that loses an earlier ID. Describe credential handling by name (alias, mechanism): no secret values and no code that assigns them, because the credential screen reads this file. " + ("Record each structural choice this plan makes (module format, namespace and data map, storage, dependencies, seams) as the next unused AD-<n>, and list architecture.md in README.md." if stage == "plan" else "If this item makes a structural decision (a new module, dependency, interface, storage or convention), add it as the next unused AD-<n> and cite the ID in the step plan."))`
  and, for prepare, `lines.append("If architecture.md is missing, write it from plan.md and the plan's structural choices: it holds " + ARCHITECTURE_HOLDS + ".")`.
- **L3** `DUTIES["spec"]`, one sentence: "Number requirements R-<n> only. A choice about structure or technology is not a requirement: it
  belongs in architecture.md as an AD-<n> decision, never in spec.md, and a product decision a spec numbers must not use the AD- prefix."
- **L4** (`_stage_gates`, non-close stages that can lose an ID): for `spec`, `plan`, `step-plan`: "a change to docs/shiploop/ that loses an
  earlier requirement (R-<n>) or decision (AD-<n>) ID, or that looks like a credential".
- **L5 / L6** (inner-packet FILES part and DO lines, the environment pointer): yours, built from `grounding(state)`; print nothing when the
  list is empty. Labels are exactly: living spec; feature spec; environment; architecture; test strategy. The feature spec disappears after
  the retire step of task R; do not hard-code it.
- **L7** the harness classifier (`test/shiploop_e2e/packet_anatomy.py`, the `knowledge-home` expression): add the prefixes of any new
  line, or the unclassified share (limit 3%) grows. Editing that file selects the whole e2e family.
- **L8** pins to add with your text (`shiploop-packet-completeness`): the plan, step-plan and prepare cold packets contain
  `ARCHITECTURE_HOLDS` verbatim; inner packets contain one line whose paths equal `grounding(state)`; an inner packet of a run with no
  `architecture.md` names no architecture path.

What the engine prints without any of your edits: the keeps and refuses lines for plan, step-plan and prepare, and the prepare refusal's
hint line when the file is missing.

## What the first live pair must record (the measure, not a threshold)

The hello and Battleship deltas against the last pair before this series: plan wall time and tokens; the number of prepare refusals for
missing files; the number of `knowledge after step-plan` commits; the share of live `architecture.md` files carrying at least one `AD-<n>`
(a grep of the work repos; until it is above zero the retention guard is unproven); the number of credential refusals that name
`architecture.md`; whether any committed `AD-<n>` was dropped by a review.

## Bump

`minor`. `changes/README.md` defines only the three words. The precedent is `shiploop` 0.54.0 (`--planning-review`): a saved run without
the new key is refused with a fresh-run hint, and it shipped as a minor; every release in the log is 0.x minor or patch, and `major` would
be 1.0.0, which no note has taken. Under "one supported version" the refusal by name is the intended handling: a home an earlier version
wrote is asked for the file at its next run's prepare, and the note says so.

## Unverified

No live run, no host CLI, no model call was made. Whether a model writes a useful `architecture.md`, numbers its decisions `AD-<n>`, or trips
the credential screen is unmeasured; so is the cost. The refusal wording was checked against `cut -c1-250` at path lengths up to 140, not in
a live cleared-context model.

## Results (final tree)

All run from this worktree (a 94-character path) with `SHIPLOOP_PROGRESS=off`, one process each, three at a time, on the tree at
`51a5609d` (the source and test files are the final ones; only this journal and the `LEARNINGS.md` entry came after):

| Suite | Tests | Exit |
|---|---|---|
| `shiploop-knowledge` | 73 | 0 |
| `shiploop-callback-contract` | 44 | 0 |
| `shiploop-actual-improve-cli` | 61 | 0 |
| `shiploop-full-runtime` | 2 | 0 |
| `shiploop-lint` | 82 | 0 |
| `shiploop-quality` | 18 | 0 |
| `shiploop-test-loop` | 137 | 0 |
| `shiploop-return-review` | 24 | 0 |
| `shiploop-workspace` | 77 | 0 |
| `shiploop-packet-completeness` | 22 | 0 |
| `shiploop-packet-bounds` | 10 | 0 |
| `shiploop-progress-data` | 8 | 0 |
| `shiploop-keepalive` | 57 | 0 |
| `shiploop-planning-handoff` | 7 | 0 |
| `shiploop-privacy` | 5 | 0 |
| `shiploop-store` | 8 | 0 |
| `shiploop-delegation` | 51 | 0 |
| `shiploop-guidance` | 63 | 0 |
| `shiploop-e2e` | 404 | 0 |
| `shiploop-e2e-commit-counters` | 100 | 0 |
| `shiploop-e2e-fidelity` | 129 | 0 |
| `shiploop-mock-replay` | 37 | 0 |
| `test-groups` | 28 | 0 |

Suites run earlier in the series, per commit, on the then-current tree and green: `shiploop-e2e-reorientation`, `-environment`, `-baseline`,
`-quality`, `-packet-anatomy`, `-runrecord` and `shiploop-run-review` after the SPEC commit; `shiploop-reference-routing`,
`-package-integrity`, `-navigator-contract`, `-cross-run`, `-navigator-dry-run` after the docs commit. The quick tier (`bash test/run-all.sh --group quick --changed-from e1dc59dc`, run after the journal and the `LEARNINGS.md` entry were in the tree, `GIT_CONFIG_NOSYSTEM` not exported): 44 suites selected and completed, 43 passed (including `shiploop-e2e`, `release-preflight`, `shiploop-run-review`, `shiploop-callback-contract` and `shiploop-actual-improve-cli`), 1 failed: `shiploop-status-display`, the pre-existing failure below. The receipt is kept in the session scratchpad, not in the repository.

Pre-existing failure, confirmed on the base source in this worktree: `shiploop-status-display`
`test_every_dry_run_packet_carries_the_block_inside_the_kept_head` (`END` 8004 > 8000, `ask-agent`, `revise`, sequence 20), identical with
the base source of the two edited modules and with this series.
