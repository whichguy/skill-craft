# Named sections in the knowledge home's fact files: journal (2026-10-10, batch 1012 task A2)

Plan v5 task A2. Base `8932b849` (main), branch `batch1012c-1bbefb`. The plan is
`docs/shiploop-commit-and-spec-lifecycle-plan-2026-10-10.md` (section 0e names A2 as open: "`SECTIONS` constants, writer entries,
section-heading notice: waits for the inner-loop session's 8-stage graph on main"). Packet text (`render()`, `_producer_packet()`,
`emit()`, `packet_head()`, `DUTIES`, `stage_lines`, `_knowledge_lines`, `_render_improve`, `_checked_line`, `_stage_gates`,
`shiploop_prompts.py`) belongs to the inner-loop session and was not edited; what it needs to print is under "Lines for the packet
owner". Evidence is compact under `docs/experiments/knowledge-sections-20261010/`.

**Status: built and tested offline; no live run has seen the notice.** The decision to turn the notice into a refusal is the owner's,
after the first live pair (see "Measure").

## Question

The owner (through the `inner-loop` session, which owns packet text) asked that `spec.md`, `environment.md` and `architecture.md` be
referenced verbosely at every stage that uses them, and that ShipLoop generate them properly in place. Agreed with that session: the
engine side supplies (a) the section headings as constants that packets quote, (b) the writer entries so the "keeps these up to date"
line prints on the stages that discover commands, facts and decisions, and (c) a section check at the closes. Can (c) be a
check that costs a cleared-context model nothing it cannot act on, given that nearly no saved home has the headings?

## What was built

| Concern | Where (all in `skills/shiploop/scripts/shiploop_knowledge_home.py` unless named) |
|---|---|
| The headings as constants, in `__all__` | `SECTIONS: Dict[str, Tuple[str, ...]]`: `spec.md` (Requirements, Non-functional requirements, Retired), `environment.md` (Targets and runtimes, Commands, Access and accounts, Platform facts), `architecture.md` via `ARCHITECTURE` (Stack, Structure, Conventions, Interfaces and boundaries, Decisions, Superseded), `test-strategy.md` (Harnesses and suites, Commands, ID convention, Real-boundary checks). A spec's acceptance criteria stay inside each `R-<n>`, with no heading |
| One wording of what the architecture holds | `ARCHITECTURE_HOLDS` is unchanged (a refusal, the callback contract and three packets print it verbatim). A test pins that the headings it quotes (`'## Decisions'`, `'## Superseded'`) are in `SECTIONS[ARCHITECTURE]` and that every architecture section is a thing the wording says the file holds |
| Writer entries on the 8-stage graph | `STAGE_FILES`: research, validate-existing and test keep `environment.md`; implement keeps `environment.md` and `architecture.md`; carry-forward keeps `architecture.md` and `environment.md`. verify reads the architecture and writes nothing, so it has no entry. `CLOSES` untouched. A guard test pins every `STAGE_FILES` and `CLOSES` key to `shiploop_stage_spec.STAGES` |
| The counted notice | `section_notices(state, stage) -> list[str]`, `NOTICE_PREFIX = "ShipLoop knowledge notice: "` (both in `__all__`), helpers `_outline` (headings outside code fences), `_section_state` (`present`, `empty`, `missing`), `_section_hint` (the words for what a file holds). `[]` at a stage that is no close; for each file of `SECTIONS` that exists and has text (the `_filled` rule), one line per missing or empty heading, in the table's order; never raises |
| One heading syntax | `_HEADING` is shared by the outcome-section reader `_sections` (levels one to three, bodies flat, unchanged and pinned) and the notice (levels one to four) |
| Printed at the close | `shiploop_navigator._knowledge_close`: right after the commit and the skipped-files notice, `knowledge.section_notices(after, stages[-1])` to stdout, line by line. The terminal block, the retire step and every raise keep their order and behaviour |
| Fixture | `test/shiploop_knowledge_support.write` writes each living file with all of its `SECTIONS` (spec keeps `R-1`) so no suite that fakes a home prints 17 notice lines at each close |
| Docs | `references/project-knowledge.md` (each row's Sections, a "Named sections" paragraph), `SKILL.md` (one sentence in the paragraph that lists the home's files), the module docstring, SPEC S-11 (own commit), the change note `changes/shiploop/knowledge-sections.md` (minor), `LEARNINGS.md` |

## Commits

| Commit | What |
|---|---|
| `917488b3` | `SECTIONS`, the writer entries, the stale-key guard, the change note; two existing tests edited (below) |
| `7c962446` | `section_notices`, `NOTICE_PREFIX`, the shared `_HEADING`, the 17 unit tests, `home_scan.py` and `home_scan.json` |
| `22b3e169` | `_knowledge_close` prints the notice; the fixture writes sections; the close unit tests; four real-CLI route tests |
| `934f3994` | The reference table, the "Named sections" paragraph, SKILL.md, the docstring, the reference pin test |
| `7ee0c9c6` | SPEC S-11 amendment (own commit, `No-Change-Note: harness spec amendment`) |
| `691f5e41` | The mutation record, 55 of 55 killed, and the tests that closed its five survivors |
| (the last commit) | This journal and the `LEARNINGS.md` entry |

## Decisions and deviations

| Item | Disposition |
|---|---|
| A refusal at the closes | **Not built, by the evidence.** `home_scan.json` (29 saved homes): every home would get at least one notice line (273 lines, 0 homes with none, median 9). A refusal would fire at every first close of an existing-style run until packets quote the headings. The first live pair decides (see "Measure"); the task said not to build the refusal |
| No refusal for `architecture.md` alone | As agreed: the prepare close already requires the file, and its refusal names what it holds |
| "Starts with" is a plain prefix | The task's rule is "text starts with the heading, case-insensitive". A first version added a word boundary (`Commands` would not match `Commandsx`); dropped, because it made `## ID conventions` (a plural) a false notice. Cost of the plain prefix: `## Structured data` hides a missing `Structure`. Pinned both ways by `test_starts_with_is_a_plain_prefix_so_a_longer_word_still_counts`. Raising a notice for a section that is there is worse than missing one that is not |
| Fenced code blocks | Added (not in the task). A shell comment (`# install`) inside a ```sh block under `## Commands` would otherwise read as a level-1 heading, and a heading written inside a block would count. `_outline` skips headings between fences (``` or ~~~, closing mark of the same kind at least as long and no text after it); 5 mutation rows cover it |
| `either_way_prefix` in the scan | Added to `home_scan.py` (not asked): the homes whose file has a heading that is a prefix of the table's heading as well (`Non-functional` for `Non-functional requirements`), heading words only. It is the delta a looser matching rule would make; a later decision, not built |
| The fixture writes sections | `shiploop_knowledge_support.write` now writes all of a living file's sections (not in the task). Without it every suite that fakes a home (full-runtime, test-loop, lint, navigator-contract, the inner fixture) prints 17 lines at each close; a drift guard pins that a fixture home gets no notice |
| Two existing tests edited (both legitimately broken by the new writer entries) | `ArchitectureTests.test_the_architecture_is_a_living_file_plan_and_step_plan_keep_and_prepare_requires` asserted `implement`'s packet lines do not name `architecture.md`; it now uses `verify`. `shiploop-packet-completeness` `test_an_inner_packet_lists_exactly_the_grounding_files_and_none_that_is_missing` asserted the whole `implement` packet lacks the missing file's path; it now asserts on the "Ground this stage's decisions" line, which is what must omit a missing file, and that the line still names a present one |
| The notice's text | Generic, no text per heading beyond the heading: "add a '## <heading>' section (<the file's sections, or ARCHITECTURE_HOLDS>), or write 'none' under it when nothing applies". The "'none'" clause is generic and is there because a heading that legitimately has nothing (access and accounts of a script) could otherwise never clear its own notice |
| Where the notice prints | After the knowledge commit, as the task says. A non-terminal commit that fails returns before it (its own stderr line is the output); the next close prints the lines again. The same lines repeat at every close until fixed, which is what "per close" counts |
| The change note | Added in the first commit (not the last) so every commit of the series passes `check-release-boundary`; one note for the series |
| `shiploop-mock-replay` | Not a file under `test/`: the catalog entry runs `skills/shiploop-e2e-audit/harness/check_suite.py --suite mock`. It runs in the quick tier with `--changed-from` |
| 29 homes, not 27 | The main session measured 27; the scan finds 29 homes with a `docs/shiploop` directory under `/Users/dadleet/e2e-runs`. Its figures were text presence; the scan counts headings, so they differ (for example "Platform facts" in 1 home as a heading, not 27) |

## Method and evidence

Fail-first for each behaviour, run and seen red for the intended reason before the code:

| Step | Red before the code | Green after |
|---|---|---|
| 1. tables | 5 of 7 `SectionsTests` red (no `SECTIONS`; `KeyError` on the five new stages; the prepare and release-plan lines absent); the stale-key guard and the verify test pass at once, as guards | knowledge suite 130 tests |
| 2. the notice | 16 of 17 `SectionNoticeTests` red (`AttributeError: section_notices`); the `_sections` reader pin passes at once, as a guard | knowledge suite 147 tests |
| 3. wiring | 2 of 6 `SectionNoticeCloseTests` (one with four subtests) and 2 of 4 real-CLI route tests red (`0 != 17` lines); the print-nothing cases are guards | the footprint below |
| 4. docs | the reference pin red with 18 missing headings, the prefix and the sentence | knowledge suite 155 tests, then 157 with the survivor tests |

| Evidence | File | Result |
|---|---|---|
| The saved homes, read only | `docs/experiments/knowledge-sections-20261010/home_scan.py`, `home_scan.json` | 29 homes, 273 notice lines (8 to 11 a home, median 9), none without one; per file and heading: present, empty, missing, and the either-way-prefix count; the headings the files really use |
| Mutation check | `docs/experiments/knowledge-sections-20261010/mutation_check.py`, `mutations.json` | 55 one-line breaks of the module and the wiring, 55 killed in the last full run (sources clean in Git before and after). The first full run killed 50: the level rule tested only at level 2, the fence tested only as a backtick block, and the last-versus-first accepted stage (every test had one) |
| Footprint | see "Results" | |

## Findings

- **Firm (saved homes, `home_scan.json`).** The proposed headings are nearly absent: `environment.md` has `Commands` and `Access and
  accounts` in 0 of 29 homes, `Targets and runtimes` in 0, `Platform facts` in 1; `test-strategy.md` has `ID convention` and
  `Real-boundary checks` in 0, `Harnesses and suites` in 0, `Commands` in 2; `spec.md` has `Requirements` in 19, `Retired` in 24,
  `Non-functional requirements` in 0. `architecture.md` is in 0 homes (all saved before the file existed): null, not zero.
- **Firm.** The models write `environment.md` as prose under its `# Environment` title (29 of 29 homes carry that title; the other
  headings are `Delivery` in 7 and `Runtime` in 2), so the first live pair will see about 9 lines a home, up to 17 when the architecture
  file is written as prose too, at each of the four closes until the headings are written.
- **Firm, small.** 11 of 29 homes write `Non-functional` where the table says `Non-functional requirements`, which the starts-with rule
  does not accept (the heading would have to be the longer). Under a rule that also accepts a heading that is a prefix of the table's,
  the count for that heading falls from 29 missing to 18. `either_way_prefix` shows the same for `Harnesses and suites` (3 homes write
  `Harness`) and `Targets and runtimes` (1 writes `Targets`). Not built: packets that quote the headings make it moot, and a looser
  rule would let a short unrelated heading (`Test`) stand for a longer section name.
- **Exploratory.** Whether a model clears the notice once it reads it is unmeasured. The `'none'` clause is the one guess in the text:
  it assumes a model prefers writing `none` to inventing content.

## Lines for the packet owner

The engine now supplies, and these are the lines it cannot print itself:

1. **Quote the headings, never hard-code them.** At each stage in `knowledge_home.STAGE_FILES` that writes a fact file, after the
   existing "keeps these up to date" line, print `knowledge_home.SECTIONS[name]` for each of the four files that stage keeps, as
   `## <heading>`: "Where an item goes in <file>: ## A, ## B, ... Add it under its heading and create the heading if the file lacks
   it; write 'none' under a heading that has nothing." The notice text already says the same at the close, so a stage may keep it to one
   sentence.
2. **Say where each kind of item goes.** research, validate-existing, test: a working command is `environment.md` `## Commands`, a
   platform fact is `## Platform facts`, a target or runtime version `## Targets and runtimes`, an alias for access `## Access and
   accounts` (never a value). implement: a new working command or fact the same way; a deviation from the plan is
   `architecture.md` `## Decisions` as the next unused `AD-<n>`. carry-forward: the run's decisions in `## Decisions`, a decision that
   no longer holds under `## Superseded` with its reason and its replacement's ID. test-strategy and its stage: the commands under
   `## Commands`, the test-ID rule under `## ID convention`.
3. **At the closes (optional).** The Checked-by lines of prepare, test-spec, release-plan and release-verify may add: "ShipLoop also
   prints one 'ShipLoop knowledge notice:' line per section the four fact files lack; it does not refuse." The lines name the file by
   absolute path, the heading and the fix, so no packet needs to repeat them.
4. **`stage_lines` now prints, with no packet edit,** "This stage keeps these up to date" for research, validate-existing, implement,
   test and carry-forward, and the matching "ShipLoop refuses prepare/release-plan if any of these is missing or empty" lines
   (prepare for research; release-plan for the rest). `architecture.md` at implement and carry-forward names no later close, because
   prepare is behind them. Check that the longer implement and carry-forward packets stay inside the packet bounds you hold (the
   bounds suite is green).

## Measure

The first live pair after this lands counts `ShipLoop knowledge notice:` lines per close, with one grep of the `complete` calls' stdout
in the host events (the other knowledge lines start `ShipLoop knowledge: ` and do not match). No threshold. The baseline is the saved
homes: 273 lines over 29 homes (median 9), each repeated at every close while unfixed. What to read from the pair: whether packets that
quote `SECTIONS` get the headings written (lines per close fall toward 0 by `release-verify`), which headings stay missing, and whether
a model writes `none` or invented text under a heading with nothing to say. Turning the notice into a refusal (by name, with the exit
in the message) is the owner's decision after that; it is not built.

## Deferred

- The refusal itself (above).
- A looser match (a heading that is a prefix of the table's); the either-way counts are in `home_scan.json`.
- Counting the notice lines in the harness (`metrics`): additive, absent means unknown, wanted only if the pair needs it beyond a grep.
- `README.md`'s own sections (no table): the index lists what each file answers; not asked.

## Results

On the final tree (`SHIPLOOP_PROGRESS=off`, no `GIT_CONFIG_NOSYSTEM` exported for the quick tier, load average 5.4 to 7.2 on a shared
machine). Compact record: `docs/experiments/knowledge-sections-20261010/footprint.json`.

| Run | Result |
|---|---|
| `bash test/run-all.sh --group quick --changed-from 8932b849` | 45 suites: **44 passed, 1 failed** (`shiploop-mock-replay`, below). Includes shiploop-knowledge (157 tests), callback-contract, actual-improve-cli, packet-completeness, packet-bounds, guidance, delegation, test-groups, navigator-contract, test-loop, lint, e2e and e2e-commit-counters |
| by name: shiploop-e2e, shiploop-e2e-commit-counters, shiploop-full-runtime, shiploop-progress-data, shiploop-retire | all exit 0 |
| `shiploop-mock-replay` (`check_suite.py --suite mock`) | **5 of 37 tests fail, and the same 5 fail at the base `8932b849`** (exported with `git archive` and run in the scratchpad). `test_dag_replay` still expects the old graph edge `prepare -> get-next-work-item`; the 8-stage graph goes to `step-plan`. Not touched here: the oracle belongs to the E2E apparatus, and the failure predates this series |
| Mutation check | 55 of 55 killed (`mutations.json`) |
| `scripts/check-release-boundary.py --base 8932b849 --head HEAD` | OK |

The suites were also run at each step (step 1: guidance, delegation, progress-data, e2e-commit-counters, test-groups, callback-contract,
actual-improve-cli, full-runtime, packet-completeness, packet-bounds, step-packets, e2e-packet-anatomy; step 3: those plus
navigator-contract, retire, e2e, test-loop, lint), all exit 0 apart from the two tests that `implement`'s new writer
entry legitimately broke (edited, above). `shiploop-knowledge` was catalogued at 15.0 s in `test/suite_catalog.py` and measured 24 to
29 s before and after this series (28.8 s at the base); the catalogue is not changed here.
