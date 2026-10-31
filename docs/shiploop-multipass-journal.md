# Multi-pass journal: a second, third and fourth pass on one repository

Living record of the work on re-entrant ShipLoop runs (a run that starts from the repository an earlier run left). Plan and
decisions for the owner: [shiploop-multipass-plan-2026-10-31.md](shiploop-multipass-plan-2026-10-31.md). Evidence:
[experiments/multipass-20261031/](experiments/multipass-20261031/). Each finding carries a status (firm, interim, exploratory,
superseded), its evidence and the commit that holds the change; a later edit marks a claim superseded with its date and reason and
never deletes it.

## Brief (owner, 2026-10-31)

Add a set of end-to-end cases that take an existing case and add a feature, to validate, trace and track the delta from the prior
feature: keep the right files from the prior run, separate what this run does from what the old run did, and decide whether
current-activity files need names apart from the permanent decisions (architecture should be fairly permanent and updated when
the increment changes it). Prompt, plan and spec are checked against the new feature only; the old features have their own
tests. First make sure ShipLoop is set up for a second, third and fourth pass: the nth run knows where to put new data, does
not repeat old decisions and inherits some of them.

## Where things stand

| Finding | Status | Evidence |
|---|---|---|
| F1 A second pass appends decisions after the last heading; 4 of 4 grew architecture.md outside its named sections (3 with a heading of their own, one with a live decision under `## Superseded`, which the engine then reads as retired) | firm (4 runs, one case pair, Codex Terra) | [ledger](experiments/multipass-20261031/ledger-saved-pairs.json), `test/shiploop-e2e-delta.test.py` (`SavedPairsTest`) |
| F2 `environment.md` is a chronological log from the first pass on: 1 to 7 stage-report sections added per pass, 4.5 to 6.4 KiB growth in pass 2 | firm (8 runs) | [ledger](experiments/multipass-20261031/ledger-saved-pairs.json), [by stage](experiments/multipass-20261031/stray-headings-by-stage.json) |
| F3 Provenance and titles are run-relative: "Basis: current request" in 4 of 4 pass-2 specs, 3 of 4 specs still titled for the first feature | firm (4 runs) | [ledger](experiments/multipass-20261031/ledger-saved-pairs.json) |
| F4 Planning is delta-first: tests cite no preserved requirement (0 of 19 cases), `primary` is the new IDs plus at most one kept ID, no earlier test was touched; `follows` still names kept IDs in 3 of 4 | firm (4 runs) | same |
| F5 A chain of three or more links lost its earlier links' regression checks and quality acceptance | firm (reproduced) | `ChainTest`, [chains.py](../test/shiploop_e2e/chains.py) |
| F6 `knowledge_reads` is empty on every Codex run because it counts only read-tool calls | interim (instrument) | `metrics.json` of the eight runs |
| F7 No harm to function: all eight runs passed, 14 of 14 on the follow-on, every earlier requirement and decision kept | firm (negative result) | [brownfield journal](shiploop-brownfield-baseline-journal.md), [ba45b9d2](https://github.com/whichguy/skill-craft/commit/ba45b9d2ada380d6f2aafe4e628f62eef5b29356) |
| F8 A third and fourth pass have never run | open | Round 1 below |

## Round 0: eight saved runs read for what a second pass leaves (2026-10-31)

**Question.** The engine's design keeps a product's knowledge in three living files and everything about one run in its run
folder ([project-knowledge.md](../skills/shiploop/references/project-knowledge.md), "Repository knowledge home"). After a second
pass, do the permanent files stay permanent, and does the run build on what the first left?

**Material.** The four ticket pairs of the 2026-10-29 brownfield rounds on Codex `gpt-6.1-terra` at `xhigh`: `bf-codex-r1` and
`bf-codex-r2` (hookless, [ba45b9d2](https://github.com/whichguy/skill-craft/commit/ba45b9d2ada380d6f2aafe4e628f62eef5b29356)),
`hooks-before` (base `8dde0855`) and `hooks-after` (Wave A, [5faca0d3](https://github.com/whichguy/skill-craft/commit/5faca0d3d1d61630c88302d75b78ad50d0cf1dd9)).
Each pair is `ticket-assignment` (pass 1, on `fixtures/node-tickets`) then `ticket-escalation` (pass 2, continuing from pass 1);
all eight runs passed. Their living files are in [saved-pairs/](experiments/multipass-20261031/saved-pairs/).

**Method.** [delta.py](../test/shiploop_e2e/delta.py), built for this, read each run against the head it started from, using the
engine's own entry parser. [cut_saved_pairs.py](experiments/multipass-20261031/cut_saved_pairs.py) and
[attribute_stray_headings.py](experiments/multipass-20261031/attribute_stray_headings.py) regenerate the evidence. No model was
called.

**Result, pass 2 (four runs).**

| run | R added | AD added | AD born retired | stray headings added (spec / env / arch) | environment.md KiB | architecture.md KiB | `follows` delta / kept | test cases delta / kept |
|---|---|---|---|---|---|---|---|---|
| bf-codex-r1 | 2 | 1 | 0 | 1 / 7 / 1 | 6.8 to 12.9 | 2.2 to 3.8 | 3 / 5 | 6 / 0 |
| bf-codex-r2 | 2 | 1 | **1 (AD-3)** | 0 / 1 / 0 | 5.8 to 10.3 | 2.1 to 3.4 | 3 / 4 | 6 / 0 |
| hooks-before | 2 | 1 | 0 | 0 / 6 / 1 | 6.7 to 11.7 | 2.1 to 3.3 | 3 / 5 | 4 / 0 |
| hooks-after | 2 | 1 | 0 | 0 / 4 / 1 | 5.4 to 11.7 | 1.6 to 3.0 | 3 / 0 | 3 / 0 |

Pass 1 for comparison: stray headings added to `environment.md` 5, 6, 4 and 3; `architecture.md` 1, 0, 0 and 0.

### F1. A second pass appends after the last heading (firm)

- `architecture.md` after pass 2: three runs added a level-2 heading outside the named sections ("Reassignment and escalation
  checks", "New feature real-boundary checks", "Integrated verification due", the last also a second "Real-boundary checks"),
  and the fourth, `bf-codex-r2`, wrote `AD-3` and a boundary-checks heading as level-3 headings after `## Superseded`.
- The engine reads position, not meaning: `knowledge_home.entries` marks `AD-3` retired. Called on the saved repository,
  `shiploop_navigator._entry_lines` prints `- AD-3 (now under Superseded in KNOWLEDGE/architecture.md):` above the text
  "AD-3 Bulk assignment and escalation (implemented)". A third pass that follows `AD-3` is told, by the script, that the
  decision it must respect no longer holds.
- Mechanism: the model appended with a heredoc (`cat >> docs/shiploop/architecture.md`, event 85 of that run's `events.jsonl`).
  The file ended with `## Superseded` and `None.`
- Where pass 2 updated `architecture.md` in place (`changed_sections`, the named sections whose text changed): `bf-codex-r1` Structure and
  Interfaces and boundaries; `hooks-before` Decisions; `bf-codex-r2` only Superseded (its worker job and escalation marker are described
  nowhere but under that heading); `hooks-after` none. Two of four runs put the update where it lives.
- What it does not show: harm. The deciding facts are in the pass-2 text; the pass-3 effect of the mislabel is unmeasured
  (Round 1).

### F2. `environment.md` is a log from the first pass on (firm)

- Every one of the eight runs added level-2 headings that are no named section (pass 1: 5, 6, 4, 3; pass 2: 7, 1, 6, 4) and
  every run holds 1 to 3 named sections twice (two `## Commands`). The file grew 5.4 to 6.8 KiB in pass 1 and a further 4.5 to 6.4 KiB in pass 2
  (KiB of 1,024 bytes throughout this journal).
- Attribution by the stage whose knowledge commit first held each of the 36 stray headings in the four final files
  ([by stage](experiments/multipass-20261031/stray-headings-by-stage.json)): prepare 7, release-plan 6, operations 5,
  carry-forward 5, release-verify 4, discovery 4, system-test-author 3, test-strategy 2. Every one is a stage reporting what it
  did ("Prepared environment", "Verified assignment checks", "Returned result", "Operational observations"), and pass 2 adds a
  second set beside the first ("Local release for bulk reassignment and escalation" beside "Local delivery and rollback").
- No named section of `environment.md` changed in three of four pass-2 runs (`hooks-after` changed Harnesses and suites): the facts of the
  pass, such as the commands that worked, were written into sections of their own and not into `## Commands`.
- Run-relative words in the lines pass 2 added: "this run", "current change", "new feature", "this request", "latest change" in
  all four.
- The design intends part of this: decision X11 of the
  [consumer contract](shiploop-consumer-contract-2026-10-11.md) lets release-plan keep the standing procedure "under whatever
  heading the run uses", without run-specific values, and no gate polices headings. The intent was a standing procedure; the
  runs wrote reports. Since D1 (2026-10-17) a packet lists each living file by contents, so the headings are what every later
  stage's packet shows of the file.
- Status of the cause: firm for the attribution (Git history), interim for the reading of the duty texts that name no heading.

### The third pass's first packet (firm for what it lists; interim for the cap)

- [render_pass3_intake.py](experiments/multipass-20261031/render_pass3_intake.py) builds a three-commit repository from a saved pair's second-pass
  files and starts a real run on it with `shiploop init` and the `ticket-comments` prompt. No model is called. The four listings are committed
  ([pass3-intake-*.txt](experiments/multipass-20261031/)); `ThirdPassPacketTest` pins two of them to the engine as published (1.26.0).
- For `bf-codex-r2` the model is shown: `spec.md` titled "Ticket assignment specification" and listing R-1 to R-7; `environment.md` as 22
  headings under its title (`## Commands` twice, "Prepared environment", "Returned result", "Operational observations", and a dated
  "Bulk reassignment and escalation discovery (2026-10-29)" with six subsections); `architecture.md` with `AD-3` under `## Superseded`. The
  inherited learnings (the last three commit messages, the newest lessons commit in full) are quoted correctly: that half of inheritance works.
- The listing prints at most 40 headings of a file and then "N more headings" (`_CONTENTS_LINES` in `shiploop_navigator.py`), in file order, so
  the sections appended last are the ones cut. `environment.md` listed 12 to 16 headings after pass 1 and 16 to 27 after pass 2 (+4 to +11 a
  pass). At those rates the fastest-growing pair is first cut in the packet of the fifth pass and the slowest not before the ninth.
  Arithmetic from the observed growth, not seen on a run.

### F3. Provenance and titles are run-relative (firm)

R-1 to R-5 were kept byte for byte and R-6 and R-7 were numbered correctly in all four runs (no collision, no change to an
earlier entry). Both new entries of every pass-2 spec say "Basis: current request", which means another request in pass 3.
Three of four specs are still titled "Ticket assignment specification" after the second feature.

### F4. Planning is scoped to the delta (firm)

No test the first pass wrote was modified or deleted (0 of 4). Pass 2 modified 8 to 9 of the 27 source files that existed at its
start. `primary` held the two new requirements plus at most one that was kept. Of 19 planned test cases none cites a requirement the
run did not add. The `follows` of the step plans is looser: 4 or 5 kept IDs beside 3 new in three runs, none in the fourth.
Planning time did not grow on Terra: 322 s then 328 s (`bf-codex-r2`), 250 s then 422 s (`hooks-after`).

### F5. Chains of three lost their earlier regression (firm)

`run.load_case` read one level. On a three-link catalog link 3 ran link 2's own checks and none of link 1's, and
`case_quality` returned nothing when link 2 declared no quality block. Reproduced by running `load_case` on a temporary catalog
before the change; the two existing follow-ons keep byte-identical lists (a test pins both). `scorecard.requires_acceptance`
read a case's own declaration, so a third link would have run the acceptance it inherits without being required to observe it.

### F6. The inheritance counter is blind on Codex (interim)

`knowledge_reads` is `[]` in all eight runs. It counts read-tool calls, and Codex reads by shell (`cat docs/shiploop/spec.md`,
event 39 of `bf-codex-r2-ticket-escalation`). The ledger's `writes` block counts shell reads (1 to 4 per file) and shell appends
(`environment.md` 7 and `architecture.md` 2 in that run). It misses appends made by a patch tool: `hooks-after` shows 0 appends and
still filed `AD-2` after `## Superseded`. The ledger counts the outcome (stray, born retired) and treats appends as an indicator.

### F7. Function was not harmed (firm, negative)

All eight runs passed; the follow-on kept every earlier requirement and decision and added two requirements and one decision each.
The defects above are hygiene that compounds with the number of passes, not a measured failure of a second pass.

## Harness changes (03d046c6, aa601d37)

| Change | Anchor | Effect on earlier results |
|---|---|---|
| `chains.py`: `follows` read to its end for regression, quality and the scorecard's requiredness | SPEC S-11 "Follow-on chains", S-12 | none: `battleship-scoring` and `ticket-escalation` keep their lists, every case keeps its requiredness; `scorecard/6` stays |
| `delta.py` and the `delta` block of `metrics.json` | SPEC S-11 table row | none: a record beside the verdicts, no baseline row, no verdict |
| `ticket-comments`, the third link of the ticket chain, with `reference_ticket_comments.py` | SPEC S-11 | a new case; the style stays out of every suite |
| suites `shiploop-e2e-delta` (66 tests) and `shiploop-e2e-ticket-comments` (17) | `suite_catalog.py` | `test-groups` pins moved from 113/168 to 115/170 |
| the two pins the quick tier found: `metrics.json`'s extra keys (`delta`, `delta_unmeasured` beside the counters, still in no result and no baseline row) and the S-13 probe terms of the new case | `shiploop-e2e-commit-counters.test.py`, `probe_terms.json` | none: both are registrations the tier asked for |

Hermetic checks: 66 tests for the chain and the ledger (one through `run.main` with the three fake hosts), 17 for the new link, 50 for `test-groups`.
The quick tier (65 suites, 628 s at `--jobs 8`) found three failures: the two registrations above, and `brownfield-tickets`' follow-on test, which
passes alone (24 of 24 in 115 s) and is the load flake the 2026-10-29 notes already record for that test. Mutation checks on the new tests
(chain read one level, `born_retired` always empty, tests classed as source, append detector dead, `stray_added` always empty) each
failed the tests that should catch them (3 to 7 tests per mutation).

### Calibration of `ticket-comments` (firm, hermetic)

The link asks for comments on tickets and names no decision. Two decisions of the base decide whether it is right: the outbox holds
back a second notice with the same key while the first waits (decision 6), and the data file's record functions name every field it
keeps and older files take a default (decision 8). On the escalation reference (the second link's stand-in): the base fails all three of
the link's checks; the reference passes them and the earlier links' 5 checks and its 5 retention checks; each of seven defects fails
exactly the one check that reads what it breaks; and the 14 hidden checks the link inherits all pass on the reference. No independent
alternative delivery exists yet (the pair has one): the checks read HTTP behaviour only, so the risk of fitting the reference is
small but unmeasured.

One unexplained event: in the first run of the test, `comments-newest-first` also failed the `persisted` check; twelve repeats
and one later full run did not reproduce it. The machine was at load average 11. The test now prints a failing check's exit code
and output, so a recurrence is identified as load or as a defect.

## Round 1: the live third pass (pending)

**Question.** Does a third pass inherit what the second left, and do the defects of Round 0 compound or harm it?

**Run.** `ticket-comments` on Codex `gpt-6.1-terra` at `xhigh`, marketplace source (ShipLoop 1.26.0), continuing from the saved
`bf-codex-r2-ticket-escalation`, whose `architecture.md` holds the mislabelled `AD-3` and whose `environment.md` holds 7 stray
sections. It waits on the machine-wide lease of port 4180, held by another session's `ticket-import` runs.

**Predictions, written before the run** (scored by [round1_readout.py](experiments/multipass-20261031/round1_readout.py), which reads only
the run's `result.json` and its delta block).

1. The run passes every check: the earlier links' 5, its own 3 and its 5 retention checks, and the 14 inherited hidden checks (a
   miss would be a finding: the first run to fail a retained requirement).
2. Its two comment notices are distinct (the decision is in the pass-1 spec as R-3), so check 2 passes.
3. Its step plans and test cases are scoped to new requirements: test cases cite no kept ID; `follows` names more kept IDs than the new ones.
4. `environment.md` gains 3 or more stray headings and 4 KiB or more, and no named section of it changes; `architecture.md` gains a
   stray heading or a born-retired entry (4 of 4 pass-2 runs did).
5. The mislabelled `AD-3` is cited or ignored without comment; it is not repaired by the run, which has no instruction to look.
6. The spec keeps R-1 to R-7 byte for byte and adds R-8 or more with "Basis: current request" wording.

Result: not yet recorded.

## Decisions made without asking (routine, AGENTS.md "Decisions")

- Work in an isolated worktree (`feat/multipass-c5fc75`), because three other sessions commit to `main` in the canonical checkout.
- The ledger is a record, not a verdict: placement, appends and relative wording are not retention checks until an engine change that
  enforces them has a baseline (SPEC S-9, S-15).
- `ticket-comments` declares no `quality` of its own and inherits the escalation acceptance; a new acceptance module waits for Round 1.
- No change to `LEARNINGS.md`: this is not an E2E round, and a touch of that file satisfies `release.py`'s `e2e_round_missing` for
  every earlier ShipLoop commit.
- The live run uses the default subject (Codex Terra at `xhigh`, hooks on), so its row is comparable with the 2026-10-29 rounds.

## Not done, and unknowns

- Pass 3 and 4 behaviour on a live run (Round 1 is the first).
- Whether naming the target heading in the reporting stages' duties, or a counted notice at each knowledge close, reduces
  `stray_added`. It is an engine change and the owner's decision; the ledger is its readout.
- A modifying increment (a request that changes or retires an earlier requirement) and a second chain on a smaller base.
- An independent alternative delivery for `ticket-comments`, and a persistence check for the pass-4 link.
- `knowledge_reads` on Codex is still empty; `delta.writes` is its heuristic replacement.
