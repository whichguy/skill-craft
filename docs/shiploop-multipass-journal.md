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
| F8 A third pass works and repeats both leaks: 13 of 13 checks and 14 of 14 hidden checks passed and R-1 to R-7 were kept, but it added 8 stage-report headings (+6.0 KiB) to `environment.md` and filed AD-4 under `## Superseded`, below the mislabelled AD-3; a fourth pass has never run | firm for one run (E1) | Round 1 below |
| F10 The candidate's notice, replayed over 58 real (commit, file) pairs, would have spoken in 57 of them at a knowledge commit and flagged nothing that was standing content beyond the release section X11 allows; both entries filed as retired when new (AD-3, AD-4) were written by `plan`, a stage the candidate's packet line does not reach | interim (offline replay, one case pair) | Round 2, [replay output](experiments/multipass-20261031/replay-placement-output.txt) |
| F11 A request that replaces an earlier rule breaks two things the additive links never met: the nearest-declaration rule hands the new link a hidden check (the second link's at-most-once) that a correct delivery fails by design, and the ledger cannot tell a run that changed the old rule from one that left it standing unless the case names the entries it may change | firm (hermetic: `ModifiedRuleTest`, `MayChangeTest`) | Round 3 |
| F12 The candidate met its pre-registered bar in the A/B (E2): 12 of 12 runs passed and B1 to B5 held. The fix added 0 stray headings to `environment.md` in all six passes against 2 to 8 in the control (second passes: 0, 0, 0 against 7, 6, 8), its architecture file kept every decision under `Decisions`, and time and tokens did not differ (second-pass time 1.02 times, mean tokens 49.1 M against 49.0 M). B1 held without being tested (the control never filed a decision as retired in six passes); the notice caught that mislabel once live (B3 pass 2) | firm for three chains per arm, one case pair, Codex Terra, passes 1 and 2 only | [readout](experiments/multipass-20261031/round2-readout-output.txt), [cost and file views](experiments/multipass-20261031/round2-cost-output.txt), [ledgers](experiments/multipass-20261031/round2-ledgers.json), Round 2 result below |
| F13 The first live fourth pass (E3, published ShipLoop): the delivery is right (16 of 16 hidden checks, its own three, the earlier links' regression) and it edited the escalation requirement in place; its first contact with a real prior exposed two wrong words in the new case (a copied retention word that failed a correct delivery, and ledger patterns written from the request), both fixed; the unfixed fourth pass repeats both leaks (9 stray headings; its new decision AD-5 filed under Superseded behind AD-3 and AD-4 from E1), so the mislabel appears to compound with the pass number | firm for one run; the compounding is exploratory (n=2) | [readout](experiments/multipass-20261031/round3-readout-output.txt), [ledger](experiments/multipass-20261031/e3-ledger.json), Round 3 result below |
| F9 The owner approved D1 to D5 as recommended (2026-10-31, "Approve all"); D2 to D4 were built as one candidate off main; E2 met its bar (F12) and the release is the owner's decision | decision | Round 2 below |

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
  carry-forward 5, release-verify 4, discovery 4, system-test-author 3, test-strategy 2. Thirty are a stage reporting what it did
  ("Prepared environment", "Verified assignment checks", "Returned result", "Operational observations"). Six are release-plan's: four
  from the first pass, each the standing release procedure that X11 lets sit under any heading (18 of the 36 came in each pass), and two from
  the second pass, which are second copies of it ("Local release for bulk reassignment and escalation" beside "Local delivery and rollback").
  (Refined 2026-10-31, the same day: this first said that all 36 were stage reports, which overstated it by the four that X11 intends.)
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

## Round 1: the live third pass (done 2026-10-31)

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

**Result (2026-10-31; started 17:14:41 after 67 tries at the port-4180 lease, ended 17:33; 1,125 s, 365 turns, planning 302 s).** The third pass passed: 13 of 13
checks and 14 of 14 inherited hidden checks; R-1 to R-7 byte for byte, R-8 and AD-4 added; no earlier test touched; 6 of the 27 source files modified; planning did not
grow (302 s, against 322 s and 328 s for the two earlier passes of this lineage). It also repeated both leaks and made them worse
([round1_readout.py](experiments/multipass-20261031/round1_readout.py) and `delta.py`):
- `environment.md` gained 8 level-2 headings that match no named section (10,531 to 16,637 bytes, +6.0 KiB): "Comments discovery (2026-10-31)", "Comment suite plan",
  "Comment preparation", "Comment implementation carry-forward", "Integrated comment suite", "Comment release route", "Returned comments verification" and "Comment
  operational handoff (2026-10-31)". Each is a stage's report named for the feature, two carry a date, and Commands and Harnesses and suites now have two headings each.
  The pass-2 run of this lineage added 1. One named section (Commands) was updated in place.
- `architecture.md`: AD-4 and a heading "Comment real-boundary checks" went in after `## Superseded`, below the still-mislabelled AD-3, so the new decision is born
  retired. The mislabel compounds, as the plan's arithmetic suggested.
- Not repeated: the spec's basis names the request's sections and files ("Basis: request S1-S9; src/app.js ...") and not "current request" (0 hits); step plans follow
  only new IDs (2 new, 0 kept) and 8 test cases cite no kept requirement. The spec is still titled "Ticket assignment specification".

Predictions. P1 held, P2 held, P5 held (AD-3 still retired at the end). P3 missed in the good direction (`follows` named no kept ID; the prediction expected more kept
than new). P4 missed on one clause (a named section, Commands, did change; the 8 strays, the 6.0 KiB and the born-retired AD-4 held). P6 missed in the good direction
(no "current request" wording; R-1 to R-7 untouched and R-8 added held).

Decision rule (plan section 6). Nothing retained was lost, so the leftovers of passes 1 and 2 did not harm function at the third pass (one run, one lineage). The hygiene
is worse than pass 2's, so D2 to D4 stay as approved and E2 decides the fix.

## Round 2: the owner's decision, the candidate and the A/B (E2) (2026-10-31)

**Decision (owner, 2026-10-31, reply "Approve all").** D1 to D5 of [the plan](shiploop-multipass-plan-2026-10-31.md), each as recommended. D2 to D4 were
approved "behind E2". This round reads that as: built now as one candidate, kept off `main`, and merged only when the A/B below meets its bar (unaccepted
candidate code stays out of `main`, AGENTS.md, Decisions, 2026-10-30).

**Candidate.** Branch `feat/multipass-placement-725e1a` (local, not pushed), tip [c1d737dc](https://github.com/whichguy/skill-craft/commit/c1d737dc95c7df6698f20a6ac3464b3d8b40da19) (local; the branch is not pushed), parent
[87d3da8e](https://github.com/whichguy/skill-craft/commit/87d3da8e22ee5158a6d3b877752a22eaf3e8e27b).
- D2, the notice. `knowledge_home.placement_notices(state)` and `PLACEMENT_PREFIX = "ShipLoop placement notice: "`, printed by `_knowledge_close` after any
  accepted stage that changed the home: the stage's edit is read against HEAD before the commit, the lines print after the section notices, none at the terminal
  handoff, and nothing it does can fail a close. One line per living file for a *new* entry filed under Retired (spec.md) or Superseded (architecture.md), or a
  *new* level-2 heading of environment.md or architecture.md that matches no named section or repeats one (the section notice's own prefix rule). A spec's own
  headings are not counted, a rename in place is no repeat, and an old entry moved under Superseded is a supersession and not a misfiling.
- D3, the destination. One packet line for the eight stages the ledger traced all 36 stray headings to (discovery, test-strategy, prepare, carry-forward,
  system-test-author, release-plan, release-verify, operations), built from `SECTIONS` for the files each keeps; six duty edits where the duty asked for a report
  (prepare 7, carry-forward 1, release-plan 2, release-verify 11, operations 5, system-test-author 8). `operations` is declared a writer of environment.md in
  `STAGE_FILES`: the saved runs committed its edits as "knowledge after operations", and without the entry it would never have been told the rule. discovery and
  test-strategy get the packet line only.
- D4. Spec duty item 5 asks for a basis that stays true in later runs (the request's words with the date, or a decision ID; never "current request") and a
  title for the product.
- Around it: the reference (`project-knowledge.md`), the change note `changes/shiploop/placement-notice-and-destinations.md` (minor), and the journaled packet
  ceilings for carry-forward in `head_table.json`.

**Read before building (owner rule, 2026-10-30).**
[7c962446](https://github.com/whichguy/skill-craft/commit/7c962446cc59d3b29ac9d995d6b5ff1129f835f6) found that a section check at the closes would have refused
nearly every first close of an existing-style home, so the named sections are a counted notice; the new notice keeps "a count, never a refusal".
[142724a7](https://github.com/whichguy/skill-craft/commit/142724a7cfcb22344813b63315834586a826917b) cut that notice from 17 lines to one per file because a
notice that costs a cleared-context model its first screen is a defect even when it never blocks, and recorded that changing what a line is changes what a count
means: hence one short line per file, a regular grammar, and a prefix of its own so the section notice's counts keep their meaning.
[22b3e169](https://github.com/whichguy/skill-craft/commit/22b3e16978d695dd2d539a1f767d7122c3864166) proved the notice through the real gate and not only as a
function, and keeps the terminal handoff silent. [917488b3](https://github.com/whichguy/skill-craft/commit/917488b33366a88b25a05fdfb76b512dd27886ec) made the
writer table the way a stage learns which files it keeps, which is why `operations` is in it now.
[d2c55b90](https://github.com/whichguy/skill-craft/commit/d2c55b90c321d8eff214deb398ef0a240e7f9ac4) (X11) allows no gate on a heading and keeps the standing
release procedure in environment.md under the run's heading, so the first release section a run writes is the one stray heading the notice may legitimately print.

**What the tests showed.**
- 27 new tests in `shiploop-knowledge`, each failed first for the right reason (the API or the wording absent); the suite passes (163 tests).
- The first quick-tier run (36 suites, 194 s) failed 4 subtests of `shiploop-packet-recut`, the packet ceilings. Cause: the first cut put the destination line in the
  packets of all 16 stages that keep these files, +353 to +516 characters each, and validate-existing (not one of the eight) and carry-forward went over. The line
  now goes to the eight stages that wrote the strays. Measured with one script in an arm-A tree and in the candidate tree: of the seven producer packets of the
  offline case only carry-forward changes (printed head +81, whole +598 on both routes), and its ceilings were raised with the reason. Over one visit to each of
  the eight stages the line is about 3.2 KB of a run's packets.
- Second quick-tier run: 79 suites in 877 s wall at `--jobs 8` with the machine's load average above 100 for most of it (the `head_table.json` edit pulls the e2e-apparatus suites into the footprint): 77 pass. Two load-sensitive e2e-apparatus suites failed. `shiploop-e2e-lifecycle` passes alone (20 of 20). `shiploop-e2e-brownfield-tickets` fails its disagreeing-grade test alone at load 88 (6 re-graded, bar 4), and the same test fails on the parent tree at load 64 (11 re-graded, and one more check): the load flake the 2026-10-29 notes already record for that pair. A control, not a pass: both are owed a rerun on a quiet machine before any merge..

**E2, the A/B, fixed before any run.**
- Arms. A is ShipLoop at the candidate's parent (it publishes the same skill as the marketplace: no change note was pending). B is A plus the candidate. Both run
  from checkouts (`--source checkout`), as the 2026-10-29 rounds did, so the apparatus is equal.
- Chains. A chain is `ticket-assignment` (fresh on `fixtures/node-tickets`) and then `ticket-escalation` continuing from it, on the harness defaults (Codex
  `gpt-6.1-terra` at `xhigh`, hooks on). Three chains per arm in the order A1 B1 A2 B2 A3 B3, so a drift in the model or the machine falls on both arms; about 35
  minutes a chain. The runs take the machine-wide lease on port 4180 one at a time, after E1.
- Read through the ledger ([delta.py](../test/shiploop_e2e/delta.py), an instrument that does not depend on the candidate) and the run's own events:
  [round2_readout.py](experiments/multipass-20261031/round2_readout.py).
- Bar, set before the runs. B1: no entry is filed as retired when new, in any of B's six passes. B2: the median number of stray headings added to environment.md
  in pass 2 is at most 2 for B and at least 4 for A (the saved pass-2 runs: 7, 1, 6, 4). B3: in B, every pass that added a decision changed a live section of
  architecture.md (the saved runs: 2 of 4). B4: every run passes and no inherited hidden check is lost, in both arms. B5: B's median pass-2 elapsed time is at most
  1.2 times A's.
- Predictions, before the runs. P1: B1 holds. P2: B's median pass-2 stray count is 2 (1 to 3; the standing release section is one the notice may print). P3: A's
  median is at least 4 and A files at least one new entry as retired. P4: B prints a placement notice in at least 4 of its 6 passes and at least one flagged item
  survives to the end (a notice is not always obeyed). P5: all 12 runs pass. P6: B's median pass-2 elapsed time is within 15 percent of A's.
- Reading rule. B1 to B5 all held: recommend the release (the E2E round and `release.py` still apply, and the owner decides). B4 missed: the candidate is harmful;
  drop it. B1, B3 or B5 missed with B4 held: read which stage still leaks (the ledger names the heading and the stage) before changing a word. B2 missed with the
  rest held: the duty edits pull too little, so the notice is the only lever left and its effect is P4's survival count.
- Limits. Three chains per arm, one case pair, one host and model. The saved runs come from four engine states, so arm A is run again here and not borrowed. The
  candidate has not run live: B1's first pass is its first live use, and a breakage there is a finding, not an excuse.
- Status: done at 21:40:17; the result is at the end of this round. E2 started at 17:33:58, when E1 ended; an external scheduling pause (below) sat between the two passes of chain A1, 17:47:28 to 18:29:09.

**An external scheduling pause (not part of any measurement).** At about 17:45 the owner chose, for the shared port-4180 lane, the test-writing pilots of another session
(relayed from its Codex chat "Review ShipLoop E2E improvement loop"): finish the active case, dispatch nothing more, let that session's two pilots run, resume E2 after the
second pilot case. Done at 17:47:28 by stopping only the E2 driver's shell while `A1-ticket-assignment` ran on untouched, so nothing is dispatched after it and the lease is
free for the pilots the moment it ends. Builds, arm order, the bar, the predictions and the scoring are unchanged; a watcher resumes the driver, which skips every case that
already has a result, once two pilot cases (lease holders named `ticket-tests-*` under that session's `model-runs` folder) have each held and released the lease and it has
been free for two minutes. The pause moves wall-clock time only: pass 2 of a chain reads the folder pass 1 left, so the gap between `A1-ticket-assignment` and
`A1-ticket-escalation` changes nothing they measure. The pause's start and end are recorded here when it lifts.

**The pause lifted at 18:29:09 and lasted 41 min 41 s (17:47:28 to 18:29:09).** `A1-ticket-assignment` had finished at 17:49:47 (its `result.json`), so the lane was free from
then. The other session's first pilot (`ticket-tests-published-01`) held the lease from 18:02:28 and finished about 18:05:28; its second (`ticket-tests-published-02`) held it from
about 18:22:08 and finished at 18:27:09. The watcher saw the lease free for two minutes and restarted the driver at 18:29:09; the driver skipped `A1-ticket-assignment` (it has a
result) and began `A1-ticket-escalation` (lease pid 99928). The gap between the two passes of chain A1 is therefore 39 min 22 s of wall clock (17:49:47 to 18:29:09), and
no run measure is affected: bar B5 reads each run's own process seconds, and pass 2 reads the folder pass 1 left. The watcher recognised both pilots by their lease-holder folder
names, as designed, and nothing of the other session's was touched. The other session's own record of the same lane is its commit
`806064425e0649a5bb5ab36409ef5f5ec96aac26`, which states that external queue and CI waiting is excluded from its subject time and that this candidate stays unmerged and is not
policy for its run. The hold marker (`e2-hold.json`), the watcher's log (`e2-hold-watcher-log.txt`) and the driver's log (`e2-driver-log.txt`) are kept in `docs/experiments/multipass-20261031/`.

**Main moved while E2 was being set up.** `origin/main` has since released skill-craft 2.27.1 and ShipLoop 1.26.1 (a fix in `shiploop_test_loop.py` that is unrelated to the
knowledge home). Both arms run the 1.26.0 tree at `87d3da8e`, so the A/B is internally consistent; the candidate does not touch the files that release changed, but it must be
rebased and its tier rerun on a quiet machine before any merge.

**Before the first B run (17:36): what the finished third pass and a replay add. The bar and the predictions above are unchanged.** The E2 driver started arm A's
first chain at 17:33:58, the moment E1 ended.
- A no-model replay of the candidate's notice over the knowledge commits of five lineages ([replay_placement.py](experiments/multipass-20261031/replay_placement.py),
  [output](experiments/multipass-20261031/replay-placement-output.txt); a commit's edit against its parent is what the engine reads before it commits). Of 58 distinct
  (commit, file) pairs the notice would have spoken in 57 at a knowledge commit and in none of the other 1 (E1's "Comment suite plan", which rode in a step commit,
  where the close returns early). The flagged headings read as stage reports or second copies of a named section (Commands is the most frequent); the standing release
  section that X11 allows is flagged about once a pass, as expected; no other flag looked like standing content.
- It shows a gap in the candidate. Both entries filed as retired when new, AD-3 (pass 2 of bf-codex-r2) and AD-4 (E1), were written by the `plan` stage, which is not one
  of the eight that get the packet line, so for `plan` the notice (printed after the stage, to the next stage's model) is the only lever. B1 depends on a later stage moving
  the entry, and the ledger reads the final file. If B1 misses, `plan` is the first place to look, and arm A's six runs stay valid for a second candidate.
- The candidate is not changed now: the design stands as registered, and a second candidate costs only new B runs because arm A is the same base.

### Result of E2 (ran 2026-10-31 17:33:58 to 21:40:17; all 12 runs passed; firm for three chains per arm, one case pair, Codex gpt-6.1-terra at xhigh)

The A/B met the bar it fixed before any run. Evidence: [readout](experiments/multipass-20261031/round2-readout-output.txt) (`round2_readout.py`),
[cost and file views](experiments/multipass-20261031/round2-cost-output.txt) (`round2_cost.py`, written after the first B run to read why a time bar missed on a single pair),
[the 12 run ledgers](experiments/multipass-20261031/round2-ledgers.json), the runs under `~/e2e-runs-multipass/20261031/e2/`, and the baseline rows of both arms in
`test/shiploop_e2e/baselines.jsonl`. The external pause (17:47:28 to 18:29:09, above) sits between the two passes of chain A1 and no measure reads it.

**The bar (the reading rule's five items).**

| | bar | observed | |
|---|---|---|---|
| B1 | no entry filed as retired when new, in any fix pass | 0 of 6 fix passes (the control had 0 of 6 too) | held, but not tested: see below |
| B2 | median stray headings added to `environment.md` in pass 2: fix at most 2, control at least 4 | fix 0, 0, 0 (median 0); control 7, 6, 8 (median 7) | held |
| B3 | a fix pass that added a decision changed a live section of `architecture.md` | 6 of 6 fix passes; control 3 of 6 | held |
| B4 | every run passes and no inherited hidden check is lost | 12 of 12 pass; none lost | held |
| B5 | fix median pass-2 time at most 1.2 times the control's | 1,121.9 s against 1,105.2 s, 1.02 times (pass 1: 958.0 s against 924.7 s, 1.04 times) | held |

The reading rule says that when B1 to B5 all hold, the release is recommended; the E2E round and `release.py` still apply, and the owner decides.

**The predictions (written before any run).** P1 held. P2 missed, in the good direction: the fix's pass-2 median was 0, not 2 (1 to 3). P3 missed: the control's median was 7
(at least 4), but it filed no new entry as retired in any of its six passes. P4: the notice printed in 6 of 6 fix passes (held); the readout counts two flagged items that
survive to the end, but both are the legitimate `Commands` heading, and no final file of the 12 holds a repeated level-2 heading (the new file view), so I do not count a
surviving flag as shown. P5 held (12 of 12). P6 held (1,121.9 s is within 15 percent of 1,105.2 s).

**What the fix did, run by run** (stray = level-2 headings added to `environment.md` that match no named section).
- Stray headings per pass: control 7, 7, 2, 6, 5, 8 (mean 5.8); fix 0 in all six. `environment.md` growth per pass: control 5.9 KB on average, fix 3.7 KB.
- `environment.md` after pass 2: control 10.7, 13.3 and 11.5 KB, of which 8.1, 9.8 and 7.2 KB sit under stray headings; fix 7.0, 7.3 and 8.1 KB with none. The named sections hold
  2.6 to 4.3 KB in the control and 7.0 to 8.1 KB in the fix, so the fix's file is smaller because the stage reports are gone, and it holds more under the sections it names. This is size
  evidence only; I have not compared the facts one by one, and a stage report under a named heading would count as named.
- `architecture.md` after pass 2: control 3.9, 3.8 and 3.3 KB, with 2.1, 1.7 and 1.7 KB under 4, 3 and 3 stray headings (A1's AD-4 and AD-5 sit under headings of their own); fix 2.7, 2.7 and 3.2 KB,
  no stray heading, every decision under `Decisions`. In chain B2 the file holds 3 of its 7 named sections (Decisions, Real-boundary checks, Structure) with the same volume of text, and B3's second pass changed
  only `Decisions`: the fix's runs sometimes write fewer sections. Whether that loses anything a later pass needs is not measured.
- The notice printed once in each of the 6 fix passes. In pass 1 of every chain it came after `test-strategy` (printed in the packet of `plan`) and flagged a new `environment.md` heading that matches no named
  section or repeats one (`Commands` in B1 and B3, "Focused and full commands" in B2); in pass 2 it came after `discovery` in B1 and B2 ("Bulk reassignment and escalation discovery", "Current request discovery") and
  after `plan` in B3, where it flagged `AD-3` filed under `Superseded`. None of the five heading flags survives as a separate heading in the final files. The B3 flag is the mislabel of E1 and of 1 of 4 saved runs,
  printed in the packet of `prepare`, which is the route the replay above predicted (`plan` writes the entry, the next stage is the only lever); the run moved it under `Decisions` and the final ledger has no entry
  born retired. It is the first live catch of that leak. The control did not show the leak in six passes, so this A/B cannot say how often it would have happened without the fix.

**What it cost.**
- Time and tokens: mean tokens processed 49.1 M a run for the fix against 49.0 M for the control; model calls 200 against 206; mutation-check rounds (ShipLoop's test-quality gate, the main source of slow
  runs) 2.7 against 2.8 a run. The control's own second passes span 13.3 to 21.5 minutes (A3 pass 2: six rounds of that gate), the fix's 18.1 to 19.0.
- The seven stages whose wording the candidate changed: median 264 s for the fix against 205 s for the control in pass 1, and 221 s against 251 s in pass 2. The control's own spread over those stages
  (192 to 307 s in pass 2) covers both, so no cost of the wording is shown. An earlier card of this session that read 80 s on three stages from the first pair was inside that spread and was withdrawn.

**Limits and contrary evidence.**
- Three chains per arm; one case pair (assignment then escalation); one host and model; one day on a shared machine. This session's own test suites ran between 18:27 and 18:41, overlapping the start of
  A1 pass 2 (the fastest run, 795.9 s), and other sessions' runs were on the machine at other times.
- The candidate is a bundle (the notice, the packet line, the six duty edits, the spec wording). The A/B cannot say which part does the work. The notice fired after `test-strategy` or `discovery` in five of the six passes,
  stages that carry the packet line but no duty edit, and the passes still ended at 0 stray headings, which points at the notice and the packet line more than at the duty edits, but no arm lacks either.
- B1 held without being tested, and the "survive" count of P4 is an upper bound (above). The fix runs ran from the frozen checkout of the candidate; arm A is the 1.26.0 tree, and main has since
  released 1.26.1 (a fix in `shiploop_test_loop.py` that the candidate does not touch).
- No fix run is a third or fourth pass: the leak compounds with the pass number (E1 added 8 stray headings in a third pass on published ShipLoop), and the fix has been seen only on passes 1 and 2. E3 (below) runs published ShipLoop,
  so it shows the unfixed fourth pass, not the fix's.
- `shiploop-e2e-brownfield-tickets` fails two of its calibration tests on this tree and on the unchanged parent commit (87d3da8e: 11 pairs re-graded against a limit of 4). Another session's learning commit
  b1891ab4656613467a75427a6d57e902e94c3067 lists the same suite with two calibration failures on its own integrated candidate tree and says not to waive them. It looks like base-test flakiness under load,
  not an effect of either change, and it is not investigated here.

**Recommendation (for the owner).** The rule is met and the cost is not measurable, so the release is recommended. Before it: rebase the candidate on current main and rerun its tier on a quiet machine (its earlier tier runs
failed two suites under a load average above 100; one of them, brownfield-tickets, fails on the parent too, and the other, lifecycle, passes alone), add the E2E round entry (this A/B is the round for the candidate; `release.py` reads commit order), then `release.py`, push and the host refresh.
A fix-arm third or fourth pass (the candidate on a chain's later links, or chain B on a small base) is the next measurement and not a condition.

## Round 3: the fourth link, `ticket-sla`, the first that changes an earlier rule (built and calibrated 2026-10-31; E3 ran 21:40 to 21:57, result at the end of this round)

**Why this link.** The first three links add behaviour. A real product also changes a rule it set earlier, and a second request that contradicts the first (here "a ticket is
escalated at most once" becomes "at most twice, and by priority") leaves three places that must change together: the living spec's requirement, the architecture's decision behind
it, and the tests that state it. A run that adds the new behaviour and leaves the old requirement standing has a spec that contradicts its code, and nothing in the three earlier
links can show it. The link asks the question mechanically: did the run change those entries or leave them standing?

**The request** (cases.json `ticket-sla`; delta only, but it names what it replaces, because the old rule is written in three places the run must find). Escalation waits by
priority: urgent tickets keep ESCALATE_AFTER_MINUTES (default 60), high tickets are escalated too after the new ESCALATE_HIGH_MINUTES (default 240), no other priority is
escalated; a ticket still open and unassigned twice its wait after its first escalation is escalated a second time and never a third, also across restarts; "this replaces the
rule that a ticket is escalated at most once: change that requirement, the decision behind it and the tests that state it".

**What was built** (harness only, nothing under skills/):
- `test/fixtures/quality/reference_ticket_sla.py`: the base (the third link's reference), the reference, an alternative and eight defects. The reference keeps the count in the
  outbox's history (a second key per ticket), the alternative on the ticket record (`escalations`, saved in the data file); both change the test that said "escalated once".
- Three own checks run through a small probe (`checks/ticket_sla_probe.py`, stdlib HTTP, so no JavaScript quoting): the waits by priority in two servers, "exactly two and no third"
  with both waits at 0, and the same across a restart over one data file.
- `checks/ticket_sla_accept.py`: the link's hidden acceptance, an acceptance of its own. The second link's `escalation-at-most-once` reads the sentence this request replaces, so a
  correct delivery fails it by design (`ModifiedRuleTest` pins both halves); the nearest-declaration rule would have inherited it. The new module is the second link's other thirteen
  checks plus `sla-waits-by-priority` (own variables, minutes not seconds, no other priority), `sla-second-then-stop` (exactly two, also across a restart, also for a ticket made after
  it) and `sla-second-not-immediate` (a data file written by hand in the base's format with an urgent ticket three hours old: escalated once at the default wait and not again within
  seconds).
- `delta.may_change` in cases.json and in the ledger: per living file, patterns for the earlier entries the request replaces (`"at most once"` in the spec, `"escalat"` in the
  architecture). For such a case the block adds `expected`, `expected_touched`, `expected_untouched` (the old rule stands: the new code may now contradict it) and `unexplained`
  (earlier entries touched that the request did not name), and the one-line form adds `replaced 1/1 left 0 unexplained 0`. A case without the list gets none of the keys, so the eight
  saved pairs' ledgers are unchanged (a test pins that).
- Registrations as for the third link: the suite `shiploop-e2e-ticket-sla` (20 tests), the family and count pins (117 ShipLoop suites, 172 in all), the S-13 probe terms, the breadth
  note, SPEC S-11 and the README.

**Calibration (firm, hermetic; the first run, 227 s).** Every variant failed exactly the checks that read what it breaks:

| variant | own checks failed | new hidden checks failed |
|---|---|---|
| base (the third link's reference) | waits, twice, persisted | waits-by-priority, second-then-stop |
| reference, alternative | none | none (and the other thirteen pass) |
| high-never-escalated, high-uses-urgent-wait, normal-escalated | waits | waits-by-priority |
| escalated-once-only, third-escalation | twice, persisted | second-then-stop |
| count-lost-on-restart | persisted | second-then-stop |
| second-immediate | none | second-not-immediate |
| high-unit-seconds | none | waits-by-priority |

Two defects are seen only by the hidden acceptance (`second-immediate`, `high-unit-seconds`): the own checks use a wait of 0, which neither touches. That is what the hidden
module is for. The chain tests pass too: the reference passes the three earlier links' checks, the new rule's checks and all five retention checks; the run before it, unchanged,
passes the regression and fails the new rule, the tests and the spec; and an old requirement moved under Retired and an old decision under Superseded keep their IDs and pass
retention.

**Decisions made without asking (routine).** ESCALATE_AFTER_MINUTES keeps meaning the urgent wait, so the second link's own escalation check stays valid regression and the request
adds one variable, not two. The link declares its own acceptance (above). The alternative shares the config, worker, template and test edits with the reference and differs in where
the count lives, which is the part a hidden check could fit. `ticket_sla_probe.py` replaces JavaScript one-liners for the own checks.

**Limits.** "Twice the wait" is observed only as "not immediately": a wait of 1 minute would need more than 2 minutes of watching, so a delivery that waits once the wait instead of twice
passes. The alternative is not independent of the reference beyond the count. One case, one base.

**Predictions for E3, written before the run.** E3 is `ticket-sla` continuing from the real third pass (`mp-codex-ticket-comments`), on the published ShipLoop of the day.
1. It passes: the earlier links' checks, its three, the five retention checks and all 16 hidden checks.
2. The spec's old escalation requirement is touched (changed in place or moved under Retired): `expected_touched` of spec.md is not empty.
3. The architecture's old escalation decision is left standing: `expected_untouched` of architecture.md is not empty (the run adds a decision and does not supersede the old one).
4. At least one earlier test file is modified (`prior_tests_modified` is not empty): the request says to change the tests that state the old rule.
5. Planning reads the old rule: the step plans' `follows` or the test cases' `requirement` name at least one kept ID, where the three additive links named none.
6. The leaks continue: `environment.md` gains 3 or more stray headings, and a new decision is born under `## Superseded` again.

### Result of E3 (ran 2026-10-31 21:40:40 to about 21:57:19; the first live fourth pass; firm for one run, and one check of the case was wrong and is corrected)

`ticket-sla` continued from the real third pass (`mp-codex-ticket-comments`, E1) on the published ShipLoop of the day (skill-craft 2.27.1, ShipLoop 1.26.1), Codex gpt-6.1-terra at xhigh: 993.3 s, 158 model calls,
37.0 M tokens processed, engine done, committed. Evidence: [readout](experiments/multipass-20261031/round3-readout-output.txt) (`round3_readout.py`), [ledger](experiments/multipass-20261031/e3-ledger.json), the run under
`~/e2e-runs-multipass/20261031/mp-codex-ticket-sla/` (its original `result.json` and `metrics.json` are kept beside the regraded ones as `*-original-grading.json`), and the baseline row in `test/shiploop_e2e/baselines.jsonl`.

**The verdict, and why it is two.** Recorded: FAILED, 15 of 16 checks. The delivery was right: its own three checks pass, the three earlier links' regression passes, all 16 hidden acceptance checks pass (the three new ones
included), and 4 of the 5 retention checks pass. The failing one is retention[3], "every earlier requirement ID kept and the spec records the feature" (`earlier ids: 8; missing: ; added: ; feature in spec: no`). The run kept all 8
IDs and changed its escalation requirement R-7 in place, naming ESCALATE_HIGH_MINUTES in it, which is what a link that changes a rule should do. The check accepted a new ID or "the feature in the spec", and its feature word was
`comment`, copied from ticket-comments' check; the prior spec already says "comments", so it could never be true here and the in-place route had no way to pass. Triage step 1 of the run's own mismatch note applies: the check is wrong.
It is fixed in 9d5067f3d6b38ff0231e3e98835d78fb96e5a37a (the word is now ESCALATE_HIGH_MINUTES, which only this request introduces) with three tests that fail on the old case file. A regrade cannot apply that fix:
`--resume-run --grade-only` replays the checks recorded at launch (`invocation.json`), so it re-graded the same wrong check; `round3_readout.py` instead runs the case's current commands on the saved work directory and shows both
verdicts. The corrected check passes (`feature in spec: yes`). The recorded result stays FAILED in `result.json` and in the baseline row.

**What the run did** (ledger, with the case's `may_change` patterns corrected to "escalat" because the third pass wrote the old rule as "enqueued once" under "Urgent escalation", not "at most once"):
- Spec: R-7 changed in place (replaced 1 of 1 expected, left 0, unexplained 0); no new requirement, nothing retired. It now says urgent waits ESCALATE_AFTER_MINUTES (60), high ESCALATE_HIGH_MINUTES (240), nothing else escalates,
  a ticket still open and unassigned twice its wait after its first escalation is escalated once more, never a third, and an intervening assignment prevents the second.
- Tests: 137 node tests against the base's 117 (20 more); one earlier test file modified (`test/reassignment-escalation.test.js`; +143 and -1 lines across tests). Source: 5 files modified (+25, -12).
- Architecture: the old escalation decision AD-3 left standing (expected 1, touched 0); a new AD-5 "Priority escalation and continuity" was added.

**The leaks on an unfixed fourth pass.** Both recur: 9 stray headings added to `environment.md`, and the new decision AD-5 filed under `## Superseded` (born retired), behind AD-3 and AD-4 that E1's mislabel had already put there. In the prior file
`## Superseded` was the last section, so the new decision was appended after it: the F1 mechanism, compounding. This is the second of two live later passes on published ShipLoop (E1 and E3) that filed a new decision as retired, against 0 of 6
first and second passes of the E2 control, which suggests (exploratory, n=2) that the mislabel needs a trailing `Superseded` section, which exists only after an earlier pass has made one, and so grows with the pass number. The fix's notice
caught exactly this once in E2 (B3 pass 2), in a file whose last section is `Superseded`; whether it holds from a prior that already carries the mislabel is not measured.

**The predictions (written before the run).**

| | prediction | observed | |
|---|---|---|---|
| P1 | it passes: the earlier links' checks, its three, the five retention checks and all 16 hidden checks | 1 check failing as recorded (the wrong one); 0 with it corrected; hidden 16 of 16 | held once the wrong check is corrected; missed as recorded |
| P2 | the spec's old escalation requirement is touched | R-7 expected and changed in place | held |
| P3 | the architecture's old escalation decision is left standing | AD-3 expected and untouched | held (but see below) |
| P4 | at least one earlier test file is modified | `test/reassignment-escalation.test.js` | held |
| P5 | planning names at least one kept ID | test cases cite 0 kept IDs, step plans 0 (delta IDs AD-5 and R-7 only; R-7, the rule it changed, counts as a delta ID) | missed |
| P6 | the leaks continue: 3 or more stray headings and a new decision born under Superseded | 9 stray headings; AD-5 born retired | held |

**What it shows and what it does not.**
- The link does what it was built for on the spec side: a run given a request that replaces a rule edits the requirement in place, and the ledger now says so (`replaced 1/1`).
- It cannot yet say whether a run retires and supersedes the old decision when it should. In E3 the old decision AD-3 was already filed under `Superseded` by E1's mislabel, so "AD-3 left standing" is the same whether the run saw it was already marked or ignored it.
  A clean test needs a prior produced without the mislabel (a third pass with the fix, or an E1 rerun). That is the next measurement, and it needs the candidate on the earlier links first.
- Method: the case was written from the request and a synthetic prior, and its first contact with a real prior found two wrong words in two places. For a chain B, write retention words and `may_change` patterns from a real prior pass, and give every check the in-place route as well as the new-ID route.
- The correction was made after the result was seen. It is defined from the request alone (the variable the request introduces), the run had named that variable, and the recorded failure stays visible; but a reader should know the verdict changed after the fact.

## Decisions made without asking (routine, AGENTS.md "Decisions")

- Work in an isolated worktree (`feat/multipass-c5fc75`), because three other sessions commit to `main` in the canonical checkout.
- The ledger is a record, not a verdict: placement, appends and relative wording are not retention checks until an engine change that
  enforces them has a baseline (SPEC S-9, S-15).
- `ticket-comments` declares no `quality` of its own and inherits the escalation acceptance; a new acceptance module waits for Round 1.
- No change to `LEARNINGS.md`: this is not an E2E round, and a touch of that file satisfies `release.py`'s `e2e_round_missing` for
  every earlier ShipLoop commit.
- The live run uses the default subject (Codex Terra at `xhigh`, hooks on), so its row is comparable with the 2026-10-29 rounds.
- Round 2 (2026-10-31): the placement notice has a prefix of its own and a spec's headings are not counted; the packet line goes to the eight stages that wrote the
  strays and not to the 16 that keep the files; `operations` is declared a writer of environment.md; the arms are run again from two checkouts (a detached tree at the
  parent and one at the candidate) and the candidate branch stays local and off `main`; the order A1 B1 A2 B2 A3 B3; the A/B starts after E1 so the two never wait
  on each other for port 4180. Each is routine (a choice between equivalent fixes, or launching verification runs) and none changes a default that earlier evidence
  relied on.

## Not done, and unknowns

- Pass 3 and 4 behaviour on a live run (Round 1 is the first).
- Which part of the candidate (the notice, the packet line, the duty edits) does the work, and whether it holds on a third and a fourth pass: E2 shows the bundle on passes 1 and 2 only (F12).
- A second chain on a smaller base (designed, not built; D5 builds it after E2). The modifying increment, `ticket-sla`, is built and ran live once (E3, Round 3); whether a run retires and supersedes the old decision needs a prior without E1's mislabel.
- An independent alternative delivery for `ticket-comments`, and a persistence check for the pass-4 link.
- `knowledge_reads` on Codex is still empty; `delta.writes` is its heuristic replacement.
