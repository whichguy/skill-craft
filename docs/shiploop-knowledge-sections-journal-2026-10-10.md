# Named sections in the knowledge home's fact files: journal (2026-10-10, batch 1012 task A2)

Plan v5 task A2. Base `8932b849` (main), branch `batch1012c-1bbefb`. The plan is
`docs/shiploop-commit-and-spec-lifecycle-plan-2026-10-10.md` (section 0e names A2 as open: "`SECTIONS` constants, writer entries,
section-heading notice: waits for the inner-loop session's 8-stage graph on main"). Packet text (`render()`, `_producer_packet()`,
`emit()`, `packet_head()`, `DUTIES`, `stage_lines`, `_knowledge_lines`, `_render_improve`, `_checked_line`, `_stage_gates`,
`shiploop_prompts.py`) belongs to the inner-loop session and was not edited; what it needs to print is under "Lines for the packet
owner". Evidence is compact under `docs/experiments/knowledge-sections-20261010/`.

**Status: built and tested offline; no live run has seen the notice.** Two independent reviews (a code lens and a tenet lens) found
the first build short of the task's addendum and silent at one of the four closes; the fix round below closed every finding it
confirmed. A third round (the size round, same day) made the notice **one line per file** after the block's size was recorded as an
open risk: a prose home's block fell from 18 lines and 6.9 KB (8.9 KB at a long checkout path) to 4 lines and 1.8 KB (2.2 KB), and
a line now counts a file, so the counts below changed meaning. The decision to turn the notice into a refusal is the owner's, after the
first live pair (see "Measure").

## Question

The owner (through the `inner-loop` session, which owns packet text) asked that `spec.md`, `environment.md` and `architecture.md` be
referenced verbosely at every stage that uses them, and that ShipLoop generate them properly in place. Agreed with that session: the
engine side supplies (a) the section headings as constants that packets quote, (b) the writer entries so the "keeps these up to date"
line prints on the stages that discover commands, facts and decisions, and (c) a section check at the closes. Can (c) be a
check that costs a cleared-context model nothing it cannot act on, given that nearly no saved home has the headings?

## What was built

State after the fix round. Where the first build differed, the fix round's table says so.

| Concern | Where (all in `skills/shiploop/scripts/shiploop_knowledge_home.py` unless named) |
|---|---|
| The headings as constants, in `__all__` | `SECTIONS: Dict[str, Tuple[str, ...]]`: `spec.md` (Requirements, Non-functional requirements, Retired), `environment.md` (Targets and runtimes, Commands, **Skills**, Access and accounts, Platform facts), `architecture.md` via `ARCHITECTURE` (Stack, Structure, Conventions, Interfaces and boundaries, Decisions, Superseded), `test-strategy.md` (Harnesses and suites, Commands, ID convention, Real-boundary checks). A spec's acceptance criteria stay inside each `R-<n>`, with no heading. `Skills` is the repository's local skill directory (step-plan's per-step skills and carry-forward's skill decision read it) |
| One wording of what the architecture holds | `ARCHITECTURE_HOLDS` is unchanged (a refusal, the callback contract and three packets print it verbatim). A test pins that the headings it quotes (`'## Decisions'`, `'## Superseded'`) are in `SECTIONS[ARCHITECTURE]` and that every architecture section is a thing the wording says the file holds |
| The duties and the constants are one list | `SectionsTests.test_every_heading_a_packet_duty_names_for_a_living_file_is_one_of_its_sections` scans every `shiploop_*.py` except the constants' own module for `<file>.md (## A, ## B)` and `<file>.md ## A` (whitespace joined, source string joins removed), reads each heading by prefix as the notice does, and fails on a heading `SECTIONS[file]` lacks or on a file for which it finds none (so it cannot pass on a scan that reads nothing) |
| Writer entries on the 8-stage graph | `STAGE_FILES`: research, validate-existing and test keep `environment.md`; **step-plan keeps `{feature}/plan.md`, `architecture.md` and `environment.md`** (appended last); implement keeps `environment.md` and `architecture.md`; carry-forward keeps `architecture.md` and `environment.md`. verify reads the architecture and writes nothing, so it has no entry. `CLOSES` untouched. A guard test pins every `STAGE_FILES` and `CLOSES` key to `shiploop_stage_spec.STAGES` |
| The counted notice | `section_notices(state, stage) -> list[str]`, `NOTICE_PREFIX = "ShipLoop knowledge notice: "` (both in `__all__`), helpers `_outline` (headings outside code fences) and `_section_state` (`present`, `empty`, `missing`). `[]` at a stage that is no close. Otherwise **one line per file of `SECTIONS` that exists, has text (the `_filled` rule) and has anything to report, four at most**, in the table's order; never raises. A line is `<prefix><absolute path> has no 'A', 'B' section and an empty 'C' section (this close is accepted); for each, write its content under a '## <heading>' (add the heading if missing), or write 'none' there if it does not apply.` Either part may be absent; the headings are quoted exactly as in `SECTIONS`, each list in the table's order, missing before empty, and the word is `section` in the singular always, so the grammar is regular for a reader. The path is the same first word in every variant. The `architecture.md` line ends with ` architecture.md holds <ARCHITECTURE_HOLDS>.`: the only line with words beyond the headings, once in the block |
| What opens a fence, and the file's first bytes | `_FENCE` is the CommonMark opener (up to three spaces; three or more backticks or tildes; no backtick in the text after a backtick run). The file is read as `utf-8-sig`, so a byte order mark before a first-line heading is no text |
| One heading syntax | `_HEADING` is shared by the outcome-section reader `_sections` (levels one to three, bodies flat, unchanged and pinned) and the notice (levels one to four, at the start of the line) |
| Printed at the close | `shiploop_navigator._knowledge_close`: right after the commit and the skipped-files notice, `knowledge.section_notices(after, close)` to stdout, line by line, where `close` is the last stage among this call's accepted rows that is in `CLOSES` (else the last row, which `section_notices` gates itself). The terminal block, the retire step and every raise keep their order and behaviour |
| Fixture | `test/shiploop_knowledge_support.write` writes each living file with all of its `SECTIONS` (spec keeps `R-1`) so no suite that fakes a home prints 18 notice lines at each close |
| Docs | `references/project-knowledge.md` (each row's Sections, a "Named sections" paragraph: what counts, the reading limits, how to count), `SKILL.md` (one sentence in the paragraph that lists the home's files), the module docstring, SPEC S-11 (own commits), the change note `changes/shiploop/knowledge-sections.md` (minor), `LEARNINGS.md` |

## Commits

First build (branch `batch1012c-1bbefb`, from `8932b849`):

| Commit | What |
|---|---|
| `917488b3` | `SECTIONS`, the writer entries, the stale-key guard, the change note; two existing tests edited (below) |
| `7c962446` | `section_notices`, `NOTICE_PREFIX`, the shared `_HEADING`, the 17 unit tests, `home_scan.py` and `home_scan.json` |
| `22b3e169` | `_knowledge_close` prints the notice; the fixture writes sections; the close unit tests; four real-CLI route tests |
| `934f3994` | The reference table, the "Named sections" paragraph, SKILL.md, the docstring, the reference pin test |
| `7ee0c9c6` | SPEC S-11 amendment (own commit, `No-Change-Note: harness spec amendment`) |
| `691f5e41` | The mutation record, 55 of 55 killed, and the tests that closed its five survivors |
| `fefd6566`, `b252f51e` | This journal's first version, the `LEARNINGS.md` entry and the footprint record; then the open-risk paragraph on the size of the block |

Fix round (after the two reviews; each commit green, the tests written first and seen red for the reason named in its message):

| Commit | Finding(s) | What |
|---|---|---|
| `9d2d5f25` | C1 | The close among the call's accepted rows prints the notice; unit cases and the plain-`complete` and `improve-complete` real-CLI routes at test-spec |
| `e013bfa2` | C2, T1 | `Skills` in `SECTIONS["environment.md"]`, `environment.md` appended to `STAGE_FILES["step-plan"]`, the duty-to-constants pin, the reference row, the change note |
| `746f7fa9` | C3, C4 (b), T4 | The CommonMark fence opener; the byte order mark; the tests for both and for the documented reading limits |
| `6bee2e23` | C5, T5 | One path token in both variants; "(this close is accepted)"; `ARCHITECTURE_HOLDS` once per block |
| `c019c369` | C4 (a, c, d), T2, T3 | The reference states what the code does: the reading limits, the count by occurrence, SECTIONS pinned to the duties; the pin test; the change note |
| `1756a5cc` | T3 | SPEC S-11 (own commit, `No-Change-Note: harness spec amendment`): the Skills heading, the lines on the accepting call, the count by occurrence |
| `c6339e16` | T3 | The comment above `NOTICE_PREFIX` (no behaviour) |
| `6dbaf403` | all | The mutation record regenerated (84 of 84 killed), the saved-home scan on 30 homes; the round 1 records kept as `*-round1.json` |
| `39bafe7b` | T6 | This journal, the `LEARNINGS.md` entry, `footprint.json` of the fix round |

Size round (one line per file; each commit green, the tests written first and seen red for the reason named in its message):

| Commit | What |
|---|---|
| `142724a7` | `section_notices` is one line per file; the tests, the reference, `SKILL.md` and the change note follow; the documented counting commands are run by a test on a synthetic events log |
| `bfa52287` | SPEC S-11 (own commit, `No-Change-Note: harness spec amendment`): the line counts a file; both counting commands |
| `1370161a` | The mutation record (99 of 99), the saved-home scan on 31 homes, the byte measure before and after (`notice_bytes.py`) |
| the commit that carries this journal (`git log -1 -- docs/shiploop-knowledge-sections-journal-2026-10-10.md`) | This journal, the `LEARNINGS.md` entry, `footprint.json` of the size round |

## Fix round: the reviewers' findings

Each finding was reproduced before it was fixed (a reviewer's probe, or the new test seen red). Two reviewers: code (C) and tenet (T).

| # | Finding | Verdict | Disposition |
|---|---|---|---|
| C1 | The test-spec close printed no notice: `_knowledge_close` decided on `stages[-1]`, and in the same call the script records validate-existing, so the new rows were `[test-spec, validate-existing]`. The pinned unit case `(['prepare','step-plan'], 0)` pinned the same blind spot; all four route tests used `complete` at prepare or intake | **Confirmed.** The reviewer's real-CLI probe (`improve-complete` at test-spec, prose home) printed `notice lines=0` with `section_notices` giving 17; the plain `complete` at test-spec with `--planning-review none`, which the reviewer had not run, was silent the same way | Fixed (`9d2d5f25`). `[prepare, step-plan]` now prints too: the close was accepted and checked its files, whatever the script records after it; the commit's subject still names the last stage (unchanged). Route tests assert the new rows are exactly `[test-spec, validate-existing]` first, so they cannot pass on a route that never met the case |
| C2, T1 | The addendum's two items were not built: `Skills` in `SECTIONS["environment.md"]`, and `environment.md` in `STAGE_FILES["step-plan"]`; the journal recorded no deviation | **Confirmed**, and the duties on main name `## Skills` (the step-plan duty, the carry-forward duty, a loop text) | Fixed (`e013bfa2`). The first build read the task text and missed the addendum, which overrode it; the journal's deviation table now records that. The reviewer's suggested guard is built: a duty that names a heading `SECTIONS` lacks is red (it failed on `Skills` alone before the fix, and only on it) |
| C3 | The fence opener's indent rule was untested: loosening `\s{0,3}` to `\s*` left every test green | **Confirmed** (the only survivor of the reviewer's 21 mutations) | Fixed (`746f7fa9`): the four-space case is a test and a mutation row; the tab case, which `\s{0,3}` also admitted, was red and is fixed |
| C4 | The heading recogniser misreads an indented heading, a byte order mark, a setext heading and an unclosed fence | **Partly confirmed** (all four reproduced; rare in practice) | BOM: fixed (`utf-8-sig`, one line; Notepad and Windows PowerShell write one). Indented ATX heading, setext heading and the unclosed fence: **kept and documented** in the reference (the owner's rule: fix what a normal run shows, document the rest). Widening `_HEADING` to three spaces would also change the outcome-section reader that shares it and is pinned to read what it read before. Two of the three limits are pinned by `test_only_an_atx_heading_at_the_start_of_the_line_counts_as_the_reference_says`; the unclosed fence follows CommonMark and is described. "A comment or `---` counts as a body line" is accepted: it is text under the heading |
| C5 | The two notice variants end the path differently (`<path> has no ...` against `<path>: ...`), so a reader that takes the second word as the file gets `path:` for an empty line | **Confirmed** | Fixed (`6bee2e23`): `<path> has an empty '<H>' section`; a test takes the same word from both variants |
| T2 | The reference and the change note say a packet quotes `SECTIONS` and none is hard-coded; no packet code references it | **Confirmed** (`grep` of the scripts: only the constants' module, `SKILL.md` and the reference name it) | Fixed (`c019c369`): both say `SECTIONS` is the one list, a packet is to quote it (the packet owner's work), and a test pins every duty heading to it |
| T3 | The recommended count, one `grep` of the events, undercounts: a call's whole stdout is one JSON line | **Confirmed** on `/Users/dadleet/e2e-runs/20261010/pc1i-checkers-sonnet/events.jsonl`: `grep -c 'ShipLoop knowledge: '` gives 1, `grep -o ... \| wc -l` gives 2, both in event line 478 | Fixed (`c019c369`, `1756a5cc`, `c6339e16`): the reference, SPEC S-11, this journal and the code comment say count by occurrence and per event. The small `metrics` counter the first journal deferred is **still not built**: a documented command is enough for one pair |
| T4 | A line that starts with inline triple-backtick code opens a phantom fence, so later headings are reported missing | **Confirmed** (the new test was red for it) | Fixed (`746f7fa9`) |
| T5 | A model reading the lines alone cannot tell that the close was accepted; the architecture hint is 480 characters repeated six times | **Accepted in part** | Each line says `(this close is accepted)` (24 characters), and `ARCHITECTURE_HOLDS` is printed once, on the first architecture line (`6bee2e23`; **since the size round** it is on the architecture file's one line). **Not added:** "the edit rides in the next accepted stage's knowledge commit": every stage packet already says ShipLoop commits the home when the stage is accepted (`stage_lines`), and 18 repeats would be the waste this finding removes from the architecture lines. No per-heading text was invented |
| T6 | The commits table named neither `fefd6566` nor `b252f51e` and ended "(the last commit)" with no SHA | **Confirmed** | Fixed in this journal; the last row gives the `git log` that finds the commit carrying it, because a commit cannot name its own SHA |

Equal-footing numbers for the size of the block (a home whose four files are prose, the same files, the path of a scratch directory):
before the round 17 lines, 6894 bytes, the six architecture lines 3252 of them; after 18 lines, 6708 bytes, the architecture lines
2407, the longest line 554 characters. One heading more, 186 bytes less. (The size round below replaced all of it: 4 lines, 1792
bytes at a comparable path.)

## Size round: one line per file (2026-10-10, same task, after the fix round)

**Question.** The notice printed one line per missing or empty heading, 17 or 18 for a typical existing-style home (6.7 KB on a short
path, 8.9 KB at a real checkout path), on stdout ahead of the next packet at each of the four closes until the model fixes the files.
The inner-loop session is cutting packets in half; a block that size at every close works against that, and most of its bytes were the
absolute path (18 times) and the per-file hint. Can the same facts be said in a block a model reads at a glance, without inventing text?

**Change.** One line per file that has anything to report, four at most a close (above: "The counted notice"). Decisions:

| Item | Disposition |
|---|---|
| The unit | The file: it is what a cleared-context model opens and edits, and the path is the only long word on the line. Every missing and every empty heading of that file is named, quoted as in `SECTIONS`; nothing is invented per heading beyond its name |
| The fix text | `for each, write its content under a '## <heading>' (add the heading if missing), or write 'none' there if it does not apply.` One text for missing and empty headings. The task's example said "leave it if it does not apply"; **not taken**: a line that stays forever for a heading with nothing to say cannot clear itself, which is why the fix round chose `none` (a body line, so the heading counts as present) |
| The grammar | Regular on purpose: always `no ... section`, always `an empty ... section`, `section` singular even for several names (`has no 'A', 'B' section`). A reader splits on the fixed words; the plural would have needed three more branches. Missing before empty, each list in the table's order |
| The per-file hint | **Dropped** (`<file> has the sections A, B, ...`): the line already names the headings the file lacks, and the hint repeated them for the headings it has. `ARCHITECTURE_HOLDS` stays, once, on the architecture file's line, after the fix: no other file's description is needed because the headings are the description |
| Counting | A line counts a file. Files: `grep -o 'ShipLoop knowledge notice: ' events.jsonl \| wc -l`. Headings: the quoted names before each line's first semicolon (see "Measure"). `SECTIONS` headings may therefore contain neither a quote nor a semicolon (`SectionsTests` pins it). A path that has an apostrophe or a semicolon would miscount the headings; not guarded, documented in the reference |
| Unchanged | A notice, not a refusal; never raises; only at the four closes; the close among the call's accepted rows; no packet text (`render`, `_producer_packet`, `emit`, `packet_head`, `DUTIES`, `stage_lines`, `_knowledge_lines`, `_render_improve`, `_checked_line`, `_stage_gates`, `shiploop_prompts.py`); the only edit in `shiploop_navigator.py` is a comment |

**Bytes, before and after** (`docs/experiments/knowledge-sections-20261010/notice_bytes.py`, run on `39bafe7b` extracted with `git archive`
and on this tree with `--scripts`; the block is the sum of line bytes plus newlines; records `notice_bytes-before.json`, `notice_bytes.json`):

| Measure | Before | After |
|---|---|---|
| prose home, a temporary directory (`environment.md` path 99 characters) | 18 lines, 6870 bytes, longest line 563 | 4 lines, 1792 bytes, longest 698 |
| the same, `environment.md` path 137 characters (the longest saved E2E checkout) | 7554 | 1944 |
| the same, path 212 characters (the length at which the old block is the "8.9 KB at a real checkout path" quoted before: 8904 bytes) | 8904 | 2244 |
| 31 saved homes at their real paths, lines per home | 9 to 14 | 3 to 4 (29 homes print 3, two print 4: only two homes have an `architecture.md`) |
| the same, bytes min / median / mean / max | 3242 / 3675 / 3820 / 5262 | 985 / 1039 / 1075 / 1698 |
| the same, total over the 31 homes | 118421 | 33339 |

The prose home is the case the owner named (existing-style files with no sections): about a quarter of the bytes, 4 lines instead of 18.
The longest line grew (the architecture line now carries the whole `ARCHITECTURE_HOLDS`, which used to be on its first of six lines);
on every line the path, the headings and the acceptance come first (they end at character 297 at most, for a 137-character path:
`environment.md` 290, `architecture.md` 297), then the fix (it ends at 423), and on the architecture line what the file holds last, so a
reader that cuts a line at 300 characters keeps what is missing and that the close is accepted. The 6708 bytes quoted by the fix round
were a slightly shorter temporary directory (`6726` at 91 characters on the same code; `6870` at 99 here).

## Decisions and deviations

| Item | Disposition |
|---|---|
| The task's addendum (2026-10-10, from the inner-loop session) | **Missed by the first build, built in the fix round.** Its items 1 and 2 (`Skills`; `environment.md` appended last to step-plan) overrode the task text; items 3 to 6 needed no engine work (no `Lessons:` harvest and no script-built commit body; an `AD-<n>` edit at implement or verify lands in the item commit; the stale-key guard uses `stage_spec.STAGES` of this tree, as it does). The first journal recorded no deviation for this. The constants and the duties on main now agree, and a test keeps them so |
| A refusal at the closes | **Not built, by the evidence.** `home_scan.json` (30 saved homes in the fix round; 31 now): every home would get at least one notice (fix round: 314 per-heading lines, median 10; size round: 95 file lines and 328 headings over 31 homes, 0 with none). A refusal would fire at every first close of an existing-style run until packets quote the headings. The first live pair decides (see "Measure"); the task said not to build the refusal |
| No refusal for `architecture.md` alone | As agreed: the prepare close already requires the file, and its refusal names what it holds |
| "Starts with" is a plain prefix | The task's rule is "text starts with the heading, case-insensitive". A first version added a word boundary (`Commands` would not match `Commandsx`); dropped, because it made `## ID conventions` (a plural) a false notice. Cost of the plain prefix: `## Structured data` hides a missing `Structure`. Pinned both ways by `test_starts_with_is_a_plain_prefix_so_a_longer_word_still_counts`. Raising a notice for a section that is there is worse than missing one that is not |
| Fenced code blocks | Added (not in the task). A shell comment (`# install`) inside a ```sh block under `## Commands` would otherwise read as a level-1 heading, and a heading written inside a block would count. `_outline` skips headings between fences; since the fix round a fence opens as CommonMark says (three-space indent, no backtick after a backtick run) and closes with its own mark at least as long and no text after it |
| `either_way_prefix` in the scan | Added to `home_scan.py` (not asked): the homes whose file has a heading that is a prefix of the table's heading as well (`Non-functional` for `Non-functional requirements`), heading words only. It is the delta a looser matching rule would make; a later decision, not built |
| The fixture writes sections | `shiploop_knowledge_support.write` now writes all of a living file's sections (not in the task). Without it every suite that fakes a home (full-runtime, test-loop, lint, navigator-contract, the inner fixture) prints a notice line per section at each close; a drift guard pins that a fixture home gets no notice |
| Existing tests edited (all legitimately broken by the new writer entries or headings) | `ArchitectureTests.test_the_architecture_is_a_living_file_plan_and_step_plan_keep_and_prepare_requires` asserted `implement`'s packet lines do not name `architecture.md`; it now uses `verify`. `shiploop-packet-completeness` `test_an_inner_packet_lists_exactly_the_grounding_files_and_none_that_is_missing` asserted the whole `implement` packet lacks the missing file's path; it now asserts on the "Ground this stage's decisions" line. Fix round: the exact `SECTIONS` table, the `WRITERS` map (step-plan joined it), the step-plan assertion in `ArchitectureTests` (now the first two entries, `environment.md` appended), and the literal counts 17 and 4 (now computed from `SECTIONS`) |
| The notice's text | Generic, no text per heading beyond its name: one fix sentence for the whole line, and `ARCHITECTURE_HOLDS` once on the architecture file's line. The `'none'` clause is generic and is there because a heading that legitimately has nothing (access and accounts of a script) could otherwise never clear its own notice (the fix round had a per-file section list as well; the size round dropped it) |
| Where the notice prints | After the knowledge commit, as the task says. A non-terminal commit that fails returns before it (its own stderr line is the output); the next close prints the lines again. The same lines repeat at every close until fixed, which is what "per close" counts |
| The change note | Added in the first commit (not the last) so every commit of the series passes `check-release-boundary`; one note for the series, `bump: minor`. Levels may differ between notes and the largest wins (`scripts/release.py plan()` takes `max(bumps)`; it refuses only a mix of `bump:` and `version:` notes for one skill); the eight-stage inner loop's note is `major`, so shiploop will release as a major. Nothing here says the notes must share a level |
| `shiploop-mock-replay` | Not a file under `test/`: the catalog entry runs `skills/shiploop-e2e-audit/harness/check_suite.py --suite mock`. It runs in the quick tier with `--changed-from` and fails 5 of 37 at the base too (below) |
| 29 homes, then 30, then 31 | The main session measured 27; the first scan found 29 homes with a `docs/shiploop` directory under `/Users/dadleet/e2e-runs`; the fix round's scan finds 30 (`20261010/hello-8stage-13d278dd` landed in between, the first home with an `architecture.md`); the size round's finds 31 (`20261010/checkers-8stage-88d412e9`, the second home with an `architecture.md`). Counts of headings differ from the main session's figures of text presence (for example "Platform facts" in 1 home as a heading, not 27) |

## Method and evidence

Fail-first for each behaviour, run and seen red for the intended reason before the code.

First build:

| Step | Red before the code | Green after |
|---|---|---|
| 1. tables | 5 of 7 `SectionsTests` red (no `SECTIONS`; `KeyError` on the five new stages; the prepare and release-plan lines absent); the stale-key guard and the verify test pass at once, as guards | knowledge suite 130 tests |
| 2. the notice | 16 of 17 `SectionNoticeTests` red (`AttributeError: section_notices`); the `_sections` reader pin passes at once, as a guard | knowledge suite 147 tests |
| 3. wiring | 2 of 6 `SectionNoticeCloseTests` (one with four subtests) and 2 of 4 real-CLI route tests red (`0 != 17` lines); the print-nothing cases are guards | the footprint below |
| 4. docs | the reference pin red with 18 missing headings, the prefix and the sentence | knowledge suite 155 tests, then 157 with the survivor tests |

Fix round (the same discipline; the numbers are in each commit message):

| Step | Red before the code | Green after |
|---|---|---|
| C1 the close | the unit cases `[test-spec, validate-existing]` and `[prepare, step-plan]` (`0 != 17`); the plain-`complete` route at test-spec (`0 != 17`); the `improve-complete` route at test-spec (`0 != 17`); both route tests assert the rows `[test-spec, validate-existing]` first | `SectionNoticeCloseTests` 8 tests; both routes |
| C2/T1 Skills, step-plan, the pin | 5 tests red: the exact table, the `WRITERS` map with step-plan, the step-plan release-plan refusal line, the step-plan test, and the duty pin (red on `Skills` for `environment.md` alone) | knowledge suite 160 tests |
| C3/C4/T4 fence and BOM | the tab, inline-code and backtick-in-text cases and both BOM cases red; the four-space case and the two documented limits pass at once, as guards | knowledge suite 163 tests |
| C5/T5 wording | the exact missing and empty lines, the path-word test, the architecture-once test (`ARCHITECTURE_HOLDS` 6 times, expected 1) | knowledge suite 164 tests |
| T2/T3 docs | the reference text at HEAD fails all eight new pin assertions | knowledge suite 164 tests |

| Evidence | File | Result |
|---|---|---|
| The saved homes, read only | `docs/experiments/knowledge-sections-20261010/home_scan.py`, `home_scan.json` (size round, 31 homes; the fix round's is `home_scan-round2.json`, round 1's `home_scan-round1.json`) | Size round: 31 homes, **95 notice lines** (29 homes print 3, two print 4: only two have an `architecture.md`) naming **328 headings** (median 10 a home), none without a notice; the headings named equal, home by home, the per-heading lines the previous commit printed. Fix round: 30 homes, 314 per-heading lines (9 to 12 a home, median 10); the 29 homes of round 1 printed 273 + 29 = 302 lines: exactly one more each, the `Skills` heading, present in 0 of 30. Per file and heading: present, empty, missing, and the either-way-prefix count; the headings the files really use |
| Bytes of the block | `docs/experiments/knowledge-sections-20261010/notice_bytes.py`, `notice_bytes-before.json` (the commit before the size round, `39bafe7b`), `notice_bytes.json` | The size round's table above: a prose home 6870 -> 1792, 7554 -> 1944 and 8904 -> 2244 bytes at three path lengths; the 31 saved homes, median 3675 -> 1039 |
| Mutation check | `docs/experiments/knowledge-sections-20261010/mutation_check.py`, `mutations.json` (size round, 99 of 99; round 2: `mutations-round2.json`, 84 of 84; round 1: `mutations-round1.json`, 55 of 55) | Size round: 99 one-line breaks of the module and the wiring, 99 killed (sources clean in Git before and after): 68 rows carried, 31 new or re-anchored, 16 dropped with the code they broke. Fix round: 84 of 84; its first run killed 83 of 84 because one row did not apply (a comment line sat between the two lines it replaced), corrected and the whole script run again. Round 1's first full run had killed 50 of 55; the reviewer's own 21 mutations found one survivor that neither record had (the fence indent), now a row |
| Footprint | `docs/experiments/knowledge-sections-20261010/footprint.json` (fix round: `footprint-round2.json`) | see "Results" |

## Findings

- **Firm (saved homes, `home_scan.json`, 31 homes since the size round; the counts per heading below are the 30-home scan of the fix round, `home_scan-round2.json`, and the new home changes none by more than one).** The proposed headings are nearly absent: `environment.md` has `Commands`, `Skills`,
  `Access and accounts` and `Targets and runtimes` in 0 of 30 homes and `Platform facts` in 1; `test-strategy.md` has `ID convention`,
  `Real-boundary checks` and `Harnesses and suites` in 0 and `Commands` in 2; `spec.md` has `Requirements` in 20, `Retired` in 25 and
  `Non-functional requirements` in 0. `architecture.md` is in 1 home, the first written after the file existed: the five other
  figures for it are null (the file was absent), not zero.
- **Firm.** The models write `environment.md` as prose under its `# Environment` title (30 of 30 saved homes carry that title; the other
  headings are `Delivery` in 8 and `Runtime` in 2), so the first live pair will see about 10 headings named a home, in 3 lines (up to 18
  headings in 4 lines when the architecture file is written as prose too), at each of the four closes until the headings are written
  (round 2 said "about 10 lines": since the size round a line is a file).
- **Firm, small.** 12 of 30 homes write `Non-functional` where the table says `Non-functional requirements`, which the starts-with rule
  does not accept (the heading would have to be the longer). Under a rule that also accepted a heading that is a prefix of the table's,
  the count for that heading would fall from 30 missing to 18. `either_way_prefix` shows the same for `Harnesses and suites` (3 homes write
  `Harness`) and `Targets and runtimes` (1 writes `Targets`). Not built: packets that quote the headings make it moot, and a looser
  rule would let a short unrelated heading (`Test`) stand for a longer section name.
- **Firm (a reviewer's probe and three new route tests).** A close that is followed in the same call by a stage the script records is
  the common case at test-spec, and a count taken from the last row alone would have been silent there. Any later per-close figure
  must be read against the call, not against the stage the history ends with.
- **Firm.** The host events log a call's whole stdout as one JSON line, so a line count (`grep -c`) is wrong for any multi-line output;
  count occurrences.
- **Firm (size round, `notice_bytes.json`).** A prose home's block is 4 lines and 1.8 to 2.2 KB at path lengths of 99 to 212 characters,
  from 18 lines and 6.9 to 8.9 KB; the 31 saved homes print 3 or 4 lines (median 1039 bytes) where they printed 9 to 14 (median 3675).
- **Exploratory.** Whether a model clears the notice once it reads it is unmeasured. The `'none'` clause is the one guess in the text:
  it assumes a model prefers writing `none` to inventing content.

## Lines for the packet owner

The engine supplies, and these are the lines it cannot print itself:

1. **Quote the headings, never hard-code them.** At each stage in `knowledge_home.STAGE_FILES` that writes a fact file, after the
   existing "keeps these up to date" line, print `knowledge_home.SECTIONS[name]` for each of the four files that stage keeps, as
   `## <heading>`: "Where an item goes in <file>: ## A, ## B, ... Add it under its heading and create the heading if the file lacks
   it; write 'none' under a heading that has nothing." The notice text already says the same at the close, so a stage may keep it to one
   sentence. The duties that name headings today are pinned to `SECTIONS` by a test, so a heading a duty renames is red until
   `SECTIONS` follows; quoting the constants instead removes the pin's reason.
2. **Say where each kind of item goes.** research, validate-existing, test: a working command is `environment.md` `## Commands`, a
   platform fact is `## Platform facts`, a target or runtime version `## Targets and runtimes`, an alias for access `## Access and
   accounts` (never a value), the repository's local skill directory `## Skills`. step-plan: the same for a command it finds working,
   and a new `AD-<n>` under `architecture.md` `## Decisions`. implement: a new working command or fact the same way; a deviation from
   the plan is `architecture.md` `## Decisions` as the next unused `AD-<n>`. carry-forward: the run's decisions in `## Decisions`, a
   decision that no longer holds under `## Superseded` with its reason and its replacement's ID, the skill decision under
   `environment.md` `## Skills`. test-strategy and its stage: the commands under `## Commands`, the test-ID rule under `## ID convention`.
3. **At the closes (optional).** The Checked-by lines of prepare, test-spec, release-plan and release-verify may add: "ShipLoop also
   prints one 'ShipLoop knowledge notice:' line per file whose sections are missing or empty; it does not refuse." A line names the
   file by absolute path, the headings it lacks, that the close is accepted and the fix, so no packet needs to repeat them; the block
   is at most four lines.
4. **`stage_lines` now prints, with no packet edit,** "This stage keeps these up to date" for research, step-plan, validate-existing,
   implement, test and carry-forward, and the matching "ShipLoop refuses prepare/release-plan if any of these is missing or empty"
   lines (prepare for research; release-plan for the rest, `environment.md` of step-plan included). `architecture.md` at step-plan,
   implement and carry-forward names no later close, because prepare is behind them. Check that the longer step-plan, implement and
   carry-forward packets stay inside the packet bounds you hold (the bounds suite is green).

## Measure

The first live pair after this lands counts `ShipLoop knowledge notice:` per close. A line is a file, and the host events log a
`complete` call's whole stdout as one JSON line, so count by **occurrence**, not by line. Four commands, run from the folder of the
`events.jsonl` (the first two are the totals; the third gives the files per close; the fourth the headings of one close):

    grep -o 'ShipLoop knowledge notice: ' events.jsonl | wc -l
    grep -o 'ShipLoop knowledge notice: [^;]*' events.jsonl | grep -o "'[^']*'" | wc -l
    awk '{n=gsub(/ShipLoop knowledge notice: /,"&")} n{print NR": "n}' events.jsonl
    sed -n '<N>p' events.jsonl | grep -o 'ShipLoop knowledge notice: [^;]*' | grep -o "'[^']*'" | wc -l

The first counts files reported (four at most a close). The second counts headings: the quoted names before each line's first
semicolon (the fix text and the architecture words come after it and are not read). The third prints, for each event line that has
a notice, its file count; `<N>` in the fourth is that event's line number. (The other knowledge lines start `ShipLoop knowledge: ` and
do not match.)

Verified two ways. `SectionNoticeTests.test_the_documented_commands_count_files_and_headings_in_an_events_log_and_a_single_close`
builds a synthetic `events.jsonl` in the shape the host logs (one JSON line per call, newlines escaped; a prepare close that reports 4
files and 18 headings, an event with only the commit line, a test-spec close that reports 1 file and 2 headings) and runs the four
commands through a shell: 5 files, 20 headings, per event `1: 4` and `3: 1`, 2 headings in event 3, and `grep -c` gives 2 where the
occurrences are 5 (wrong, as T3 found). `home_scan.py` reads the printed lines of all 31 saved homes with the same fields: 95 files and
328 headings, and for **each of the 31 homes** the headings named now equal the number of per-heading lines the commit before this round
printed (`notice_bytes-before.json`, measured with that commit's module: 328 in all), so no heading was lost or invented by the
regrouping. No saved `events.jsonl` holds a notice yet, so a real log was not available; the
sibling lines of the commit still count 2 by `grep -o` and 1 by `grep -c` on `pc1i-checkers-sonnet/events.jsonl` (T3), which is the
shape the commands rely on.

The first version of this section said "one grep" of the events and counted lines per heading; both are **superseded** (2026-10-10,
fix round for the method, size round for the unit). A close that the script followed with another stage (test-spec, then
validate-existing) prints in the same call since `9d2d5f25`. No threshold. The baseline is the saved homes: 95 file lines naming 328
headings over 31 homes (3 or 4 lines and median 10 headings a home), each repeated at every close while unfixed (the fix round's
baseline of 314 lines over 30 homes counted headings; 314 + 14 for the new home is the 328). What to read from the pair: whether packets that quote
`SECTIONS` get the headings written (headings per close fall toward 0 by `release-verify`), which headings stay missing, and whether a
model writes `none` or invented text under a heading with nothing to say. Turning the notice into a refusal (by name, with the exit in
the message) is the owner's decision after that; it is not built.

## Open risks

- **Size ahead of the packet (reduced, not gone).** The notice lines print before the next packet on the `complete` call's stdout. A
  prose home now prints 4 lines, 1.8 KB on a scratch path and 2.2 KB at a 212-character path (it printed 18 lines, 6.9 and 8.9 KB;
  the saved homes' median is 1 KB). A model that reads the output through `head -N` or `cut` still meets the notice before the packet
  head, though the headings and the fix come first on every line. Measured as text only; whether it still costs a re-orientation is for
  the first pair (`metrics` re-orientation after a clear). If it does: print the notice after the packet head, a small edit not made on
  a guess.
- **Repeats.** An unfixed file prints its lines at each of the four closes; the count per close is the measure, but a model sees the same
  lines up to four times.
- **The reading limits.** An indented heading, a setext heading and anything after a fence that is never closed are not read, so a file
  written that way gets a notice for a section it has. Documented in the reference; models write column-0 ATX headings, and no saved
  home contains the others.
- **Duty text is matched by shape.** The duty pin finds `<file>.md (## A, ## B)` and `<file>.md ## A`. A duty written another way
  (`## A of environment.md`) is not seen; the pin then passes silently for it. The scan fails when it finds no heading for a file at
  all, which guards the whole-scan case only.

## Deferred

- The refusal itself (above).
- A looser match (a heading that is a prefix of the table's); the either-way counts are in `home_scan.json`.
- Counting the notice lines in the harness (`metrics`): additive, absent means unknown, wanted only if the pair needs more than the
  commands in "Measure".
- `README.md`'s own sections (no table): the index lists what each file answers; not asked.
- Widening the heading reader to indented and setext headings: it would change the outcome-section reader that shares `_HEADING`.

## Results

Fix round, on the tree at `6dbaf403` plus this commit's docs (`SHIPLOOP_PROGRESS=off`, no `GIT_CONFIG_NOSYSTEM` exported for the
quick tier; load average 5.6 at the start and 10.9 at the end, a shared machine, no timing-sensitive failure and no rerun needed).
Compact record: `docs/experiments/knowledge-sections-20261010/footprint.json`.

| Run | Result |
|---|---|
| the catalog commands of `bash test/run-all.sh --group quick --changed-from 8932b849`, one suite at a time in the foreground (the serial tier is longer than one call) | 46 suites: **45 passed, 1 failed** (`shiploop-mock-replay`, below). Includes shiploop-knowledge (164 tests), callback-contract (61), actual-improve-cli (63), packet-completeness (24), packet-bounds (10), guidance (62), delegation (51), test-groups, navigator-contract, test-loop, lint, e2e (406) and e2e-commit-counters |
| by name: shiploop-full-runtime, shiploop-progress-data, shiploop-retire | all exit 0 |
| `shiploop-mock-replay` (`check_suite.py --suite mock`) | exit 2: **5 of 37 tests fail, and the same 5 fail at the base `8932b849`** (a `git archive` of the base run in the scratchpad gives the same five, the same message). `test_dag_replay` still expects the old graph edge `prepare -> get-next-work-item`; the 8-stage graph goes to `step-plan`. Not touched here: the oracle belongs to the E2E apparatus, and the failure predates this series |
| Mutation check | 84 of 84 killed (`mutations.json`) |
| `python3 scripts/check-release-boundary.py --base 8932b849 --head HEAD` | OK (exit 0) |

First build, for the record: 44 of 45 quick suites passed (the same one failing), mutation 55 of 55, the footprint suites at each step.
`shiploop-knowledge` is catalogued at 15.0 s in `test/suite_catalog.py` and measured 24 to 32 s before and after this series (28.8 s at
the base); the catalogue is not changed here.

Size round, on the tree at `1370161a` plus this commit's docs (`SHIPLOOP_PROGRESS=off`, no `GIT_CONFIG_NOSYSTEM` exported for the
quick tier; two serial streams ran in parallel on a machine shared with two other batch worktrees; no timing-sensitive failure and no
rerun needed). Compact record: `docs/experiments/knowledge-sections-20261010/footprint.json` (the fix round's is `footprint-round2.json`).

| Run | Result |
|---|---|
| fail-first, before the code | `SectionNoticeTests`, `SectionsTests`, `SectionNoticeCloseTests`: 21 failures and 2 errors; `RefusalRouteTests` 3 failures; the improve-complete route 1 failure; all "the behaviour is absent" (18 lines where 4 were expected, the fix text, the quoted names) |
| green after | `shiploop-knowledge` 167 tests (164 before: three added, the others rewritten for the new line), `RefusalRouteTests` 25, the improve-complete route 1 |
| the catalog commands of `bash test/run-all.sh --group quick --changed-from 8932b849` (`--list`), 46 suites | **45 passed, 1 failed** (`shiploop-mock-replay`, below). Includes shiploop-knowledge (167 tests), callback-contract (61), actual-improve-cli (63), packet-completeness (24), packet-bounds (10), guidance (62), delegation (51), e2e (406), e2e-commit-counters (103), test-groups (28) |
| by name: shiploop-full-runtime, shiploop-progress-data, shiploop-retire | all exit 0 (2, 11 and 26 tests) |
| `shiploop-mock-replay` (`check_suite.py --suite mock`) | exit 2: the same 5 of 37 as at the base (`expected edge prepare -> get-next-work-item`). The E2E apparatus fixed it on origin/main in `13d278dd`. `git rebase origin/main` conflicts in `test/shiploop_e2e/LEARNINGS.md` (both sides append an entry; the rebase was aborted, head unchanged), so the confirmation is an exported copy of this tree with that commit's patch applied: `check_suite.py --suite mock` runs 38 tests, exit 0 |
| Mutation check | 99 of 99 killed (`mutations.json`), 3 minutes 19 seconds in the foreground; the sources were clean in Git before and after |
| `python3 scripts/check-release-boundary.py --base 8932b849 --head HEAD` | OK (exit 0), before and after the docs commit |
