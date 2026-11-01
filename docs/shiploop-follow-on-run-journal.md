# Follow-on run: journal

Topic: whether ShipLoop should, after a run is delivered and deployed, reflect on what it learned and re-enter from the top
with an improvement prompt. Design: [shiploop-follow-on-run-design-2026-10-31.md](shiploop-follow-on-run-design-2026-10-31.md).
Evidence: [experiments/follow-on-peek-20261031/](experiments/follow-on-peek-20261031/README.md).

Consumer: the owner, deciding D1 to D4 of the design, and any session that measures or builds the follow-on list. Rounds run in
order, the newest last. A claim is edited later, not deleted: it is marked superseded with the date and the reason.

Status words: firm (read from source or reproduced), interim (one measurement or a small n), exploratory (one reader,
unreplicated), superseded (kept, with the reason).

## Round 0 — 2026-10-31 — design chat, history read, exploratory peek

Question (owner, dictated; verbatim in the design, section 0): is a replanning-style step needed after everything is done and
deployed, one that reconsiders the learnings, decides whether the feature or spec could improve, and re-enters the loop from
the top with a prompt, behind a gate, for substantial features that have not concluded?

Conditions:

- Base commit 4a75a13d052c994c3e855b9d556637fde05c0b58 (origin/main), in an isolated worktree on branch
  `docs/follow-on-design-deeee5`.
- No ShipLoop run and no subject model. One reader, Claude Sonnet 5.5, who also wrote the design. The owner's hold on live E2E
  cycles (d9fefb1144dea7f9a8d85b5897ad1275dbe08a07) is respected: everything here is offline.
- Tools: read-only reading of source and git history; `peek.py` (the coverage ledger's run finder and ShipLoop's own readers).

History searched, before any design, by affected behavior, path and referenced decision (`git log --all -i -E`):

- `--grep='lessons commit|release-verify lessons|Open for the next run'`, and `-S'Open for the next run' -- skills/shiploop`:
  the lessons commit and its delivery.
- `--grep='replan|add-work'`, and `-S'replan'` on `shiploop_navigator.py` (earliest hit cee3d950047846f61924dbd0e4627030b3a64c9e,
  2026-09-17, an Improve-bridge commit that mentions replan only as a lifecycle step; it holds no design rationale).
- `--grep='follow-on|follow on'`, `--grep='follow-up return'`: follow-on cases and the post-return fix path.
- `--grep='unverified'`, `--grep='reconcil'`: the restated leftovers list and the one pre-dispatch return edge.
- `--grep='retrospective|post-delivery|post-release|lessons learned'`: no earlier proposal of this idea; the hits are E2E learning
  commits.

Messages read in full: d9fefb1144dea7f9a8d85b5897ad1275dbe08a07, 6c6265747116b6ba2ca2a8dd11a2f28bb0551b3b,
a6eca10c6cc460047cbd8ec01509509c1d3ceb62, 70d88d379fece7457b9136b39ab8d586fd43cdae,
c6c82b16b8dc57cdb72ea4f43b75cbc1f69ce446, 19c255386d11100ac0e8e080a0848632a0f71ede,
a953e68a8c23fb2738e3cfa51ee4304a73d147b8, 593b4b44cfc0a166e01fe3a61e301ba85833c8a8,
8bae4bd6ff87503eb4a7c5bb160a776725354eb9, ea46f9493c4c3fc2d153cfe16563eb7d84324ffd,
2ae6200e05ef0d95bc05fa592c9ae0cf6ef7d018, c30e706ca8710fa65e74865f54497b032a2ff52c,
fdec0f6ed642165effd33be640974c9ee25c1561, d39b56afba1c8f867028e6feacad03f0103d633c,
49c502ea75d41c7541f7e4cedce770b0a04d4ecd, 5e6643b3525baab5336af01b9fdd3ca580d7f956,
8d51a8e988864479333de044202a20f0e5c481dc and 20769530290a7bc4db71cef6b57afe24d0f2c418. Documents read: SKILL.md, the
navigator, guide-map, carry-forward and run-start references, README sections on the stages and the end of a run, SPEC S-9 to S-16
and Change admission, the coverage-ledger and experiment-route READMEs. The consumer-contract document was searched for the
lessons decisions (K4, K13, X1, X2, X8, X15), not read whole.

Measurement (`peek.py`, `summarize.py`; snapshot of 2026-10-31; a rerun of `peek.py` from the worktree reproduced the figures
of an earlier scratch run exactly, and the 25 strict rows in the same order):

| Measure | Value |
|---|---|
| archived runs found / readable / reached handoff | 125 / 125 / 122 |
| `Open for the next run`: text other than "none" (loose) / real content (strict) | 45 (37%) / 25 (20%) |
| the 25 by class: person, capability, extension, debt, note, decision, gap | 6, 4, 4, 1, 7, 3, 0 |
| runs with an add-work / a send-back | 3 / 30 |
| runs whose unverified list is non-empty at the end (rows, all with an owner) | 38 (47) |
| runs ending with an open assumption row (not a signal) | 59 (121 rows) |

Findings:

- F1 (firm). The reflection and its delivery already exist. `release-verify` requires lessons; the lessons commit is always
  made; the next run's intake and discovery quote it by subject; the follow-up return and the report carry it to the person.
  Cites: the `release-verify` row of `shiploop_stage_spec`, `shiploop_knowledge_home.lessons_body` and `last_lessons`,
  `shiploop_workspace.follow_up_knowledge_return`, `shiploop_navigator._handoff_sections`; d39b56af, 49c502ea, 5e6643b3, 8d51a8e9
  (full hashes in the design, section 6).
- F2 (firm). `add-work` is accepted by every outer stage, `handoff` included (checked by importing `shiploop_stage_spec`:
  `handoff` outcomes are done, blocked, add-work), and reopens every outer stage accepted before it. No edge returns to spec or
  plan after dispatch: the plan Improve reconcile edge is pre-dispatch, and `system-test`, `product-acceptance`,
  `release-verify` and `handoff` block reconciliation. A run tracks one request (SKILL.md). Cites: `_finish`,
  `navigator._accepted_done`, `planning_revision.RECONCILIATION_TARGETS`; c6c82b16.
- F3 (exploratory). The archive's leftovers: the table above. No leftover among the 25 is a gap the system could close
  alone; 3 name a decision a person must make about the spec or scope. Four rows are arguable (3, 11, 16, 22); moving them
  gives at most decision 2 to 4 and leaves gap at 0. Cites: the evidence directory.
- F4 (exploratory, derived from F3). A gate on "something is open" would fire on 20% to 37% of runs and be actionable by the
  system on none of them; a gate on classified leftovers would fire on 2 to 4 runs and route each to a person.
- F5 (firm, from source). The open-assumption count is not a signal: `shiploop_assumptions.open_items` never closes a plan
  row. The unverified count is not an autonomous signal: product-acceptance requires an owner on every entry, and all 47 rows
  have one.
- F6 (interim, from earlier commits; not re-measured here). An end-of-run gate that refuses has refused honest runs: the TS1
  replay refused 5 of 8 (a6eca10c, 70d88d37), and the coverage ledger found no untested behavior at requirement granularity
  (6c626574). Consequence in the design: the follow-on list never blocks `done`.
- F7 (interim, from earlier commits; not re-measured here). No completed-but-wrong baseline exists even in the case built for
  facts only running settles: 26 of 26 completed brownfield runs pass every held-out check (593b4b44), and in XI the 3 baseline
  failures were step-plan stalls, not wrong deliveries (2ae6200e). The E2E set cannot show the value of the idea.
- F8 (observed once; not reproducible from the repository). The only two ShipLoop runs outside the E2E roots on this machine,
  under `~/src/.shiploop-runs`, were unfinished when listed (one at `system-test`, one at `intake`).
- F9 (firm, a limit of the peek). `ledger.find_runs()` reads five roots; the experiment roots `-xr`, `-s7`, `-pf` and
  `-brownfield-interrupted` are not read.

Superseded sketch: the first sketch of the live measurement (M2) reused `ticket-import` as a "late-learnable" case. Reading
2ae6200e showed its failures were stalls and not wrong deliveries, so M2 needs a newly calibrated case (design, section 7).

Routine decisions made in this round (reversible; recorded because AGENTS.md asks): the term "follow-on" (not "successor",
and not "improvement command", since Improve is a stage and a skill); the list lives in the handoff result; no new verb or
option; the work was done in an isolated worktree and committed there, and nothing was pushed.

Harness and test-case changes: none. No skill change, no change note, no release.

Effect on earlier results: none. This agrees with the coverage ledger (6c626574) and with d9fefb11: the leftovers side of the
same ceiling that 593b4b44 measured on the held-out side (every completed run already passes the checks the run never sees).

Next: the replay with a second reader (design, section 7, M1), once the owner has seen the design. The product decisions D1 to
D4 are the owner's.

## Round 1 — 2026-10-31 (late) — rebased onto main, the multipass work folded in, one stale claim corrected

Question: the multipass work of another session landed on main after Round 0, and its memory entry names this design as lacking a
live follow-on case. Does it change the design, and what in revision 1 is wrong?

Conditions: rebased onto 240594c9922c42ac0a761717671f93f220e31743 (ten commits after the Round 0 base, no file overlap). No model
call and no ShipLoop run. One reader, Claude Sonnet 5.5.

Read in full: the multipass [plan](shiploop-multipass-plan-2026-10-31.md) and [journal](shiploop-multipass-journal.md); the commits
03d046c64f2edce109394e2cecf3085b3e1c20c2, aa601d37d2f97434fd51c00e0a05b494c692cb91, 84b6bdd247288d3c81b2c717a7dde3bbfef7fc52,
1bdeac40136b908b591b34883710cb3770b879b2, 737640caa50ef567d154259b7260c907a6cba5dd and 589bc03ebe4bb31759a371e10bbc261bb071aab3.
Skimmed: 39bb5d5da1cb1e36716d0ecacabcfc1725fbb3af and 87d3da8e22ee5158a6d3b877752a22eaf3e8e27b (the SG2 smoke and its closing).

Findings:

- F10 (firm). Revision 1 cited a step that no longer exists. It said the handoff retires the run's feature spec (19c25538,
  2026-10-10). The next day 589bc03e removed the feature folder, the retire, `outcome.md` and the feature list; the engine has no
  retire symbols, and the terminal close is commit, follow-up return, print. Found because the multipass plan says the per-run
  feature folder was removed on 2026-10-11, then checked in the code. Corrected in sections 2, 3.A and 6 of the design. The mistake
  was mine: the Round 0 history search listed 589bc03e and I did not open it, reading only the older commit. Rule kept: before
  citing a decision, read the later commits that touched the same symbols. The SPEC S-11 text I read at the Round 0 base was
  stale on the same point and misled in the same direction; c3c957641aa74ed872d23de6ba066e60cf2bdd66 (2026-10-31, after that
  base) reconciled it, and the SPEC now says the feature-spec folders and the handoff-retire commit are no longer required.
- F11 (firm, from the multipass journal F4 and F7). A second pass works and is delta-first: all 8 saved runs (four pairs, a
  first and a second pass each) passed; in the 4 second passes R-1 to R-5 were kept byte for byte, no earlier test was touched, and
  0 of 19 planned test cases cite a requirement the run did not add. The strongest evidence for shape B so far. (The multipass plan
  says "eight saved second passes"; its journal is exact: eight runs, four of them second passes.)
- F12 (firm, no model). The lessons reach a third pass: the first packet of a pass built from a saved second pass quotes the last
  three commit messages and the newest lessons commit in full (aa601d37, `ThirdPassPacketTest`).
- F13 (interim). The leaks compound. `environment.md` gained 4.5 to 6.4 KiB in the second pass (32 of 36 stray headings are stage
  reports or second copies of the release procedure; 4 are the procedure the consumer contract intends). In 1 of 4 runs a live
  decision was filed under `## Superseded`. The 40-heading cap arithmetic puts the first cut at the fifth pass's packet. A chain of
  follow-on runs would repeat this, so a chain waits for the multipass decisions D2 to D4. (Refined 2026-10-31, Round 2, F16 and
  F17: the third pass repeated the leaks at a steady rate, and the chain now waits for the result of the A/B test of the fix,
  not for a decision. Refined again 2026-11-01, Round 3, F21, F22, F24 and F26: the A/B test met its bar, so the chain now waits
  for the fix's release; the mislabel persists once a lineage has it, on one lineage; the fifth pass's cut is now counted.)
- F14 (firm). `--continue-from` and `follows` are test-harness features (`test/shiploop_e2e/run.py`, `cases.json`). The engine
  records no field for which run another follows. A chain would add one; the recommend-only list does not need it.
- F15 (firm). The multipass apparatus (`chains.py`, `delta.py`, `ticket-comments`) is the fixture and the readout for a mechanics
  test of a follow-on request (design section 7, M2a). It cannot test value, because every pass in the ticket chain passes. M2b, a
  case where the first run completes wrong, is still absent.

Changed in the design: sections 1, 2, 3, 4.5, 4.7, 5, 6, 7 (M2 split into M2a and M2b), 8, 9, 10 (D2's condition) and 11 (U2
extended, U9 and U10 added). D1 to D4 keep their recommendations; D2 gains a dependency.

Superseded: the Round 0 sketch of M2 as one live measurement (now two), and revision 1's claim about the retire (F10).

Routine decisions: rebased rather than merged; revision 2 is a second commit so the correction stays visible; nothing was pushed.

Open: the live third pass of the multipass work (its E1) had no recorded result when this round was written. Read it before M2a is
planned. (Superseded 2026-10-31 by Round 2: E1 has a result, c55d0bc0ad21a2c477d024067378d0c3b1241959.)

## Round 2 — 2026-10-31 (evening) — revision 3: the multipass facts that moved after revision 2

Question: revision 2 stated three things about work that was still moving: the first live third pass as queued and without a
recorded result, the modifying link as designed and not built, and a chain as waiting for the multipass decisions. Which are now
stale, and does anything change a recommendation?

Conditions: base df44fd30d19455515cc2434dd21b18520e2a5f48 (origin/main), in a fresh worktree on branch
`docs/follow-on-rev3-dd7837`. The canonical checkout's local `main` was not the base: it holds two commits that are not on
origin/main, so it had diverged from it, and it was left alone. No model call and no ShipLoop run. One reader, Claude Sonnet
5.5, who also wrote the design.

Read in full: 15ef676f7b20a95d60c8047b0a3fcdac82cb1d3f, c55d0bc0ad21a2c477d024067378d0c3b1241959,
a86bf9b6e5289b28608682303b55faee7f39c134, c981605d36019f0036693883e838207e3edf348d,
d1e5df376a2c883263caa81f2e1a53ae7f864d99 and bf68e9590a009e3087c7acfefa895d158d9b7034, and the multipass journal's summary
table, Round 1, Round 3, routine decisions and unknowns. Its Round 2 (the candidate and the A/B design) was read for its status
line only; the A/B's design and bar are taken from the message of 15ef676f. Read for relevance:
6881e311e78eccaeb7e05644d747315bee9c534a (it matched "follow-on" but concerns the intake question bank) and the head of
df44fd30d19455515cc2434dd21b18520e2a5f48 (the skill card's byte bound; the one fact taken from it is in the design's section 8).
Searched: `git log --all -i --grep='follow-on'`, the history of the multipass documents, and
`git log 4a75a13d052c994c3e855b9d556637fde05c0b58..origin/main -- skills/shiploop agents`, which lists two commits,
7ca88df48f63631f55c8d9b16b27885f667b15a6 (a fix in `shiploop_test_loop.py`) and its release
5de751eebfc58d049032c873365e18e3621c1c7a. No module this design cites changed (the diff of `skills/shiploop/scripts` is one
file, `shiploop_test_loop.py`, 10 lines added), so the Round 0 reading of the engine still holds.

Findings:

- F16 (firm for one run). The first live third pass (E1) passed and repeated the leaks. `ticket-comments` continued from a saved
  second pass on ShipLoop 1.26.0 and Codex gpt-6.1-terra at xhigh: 13 of 13 checks and 14 of 14 inherited hidden checks passed;
  R-1 to R-7 were kept byte for byte, R-8 and AD-4 added, no earlier test touched; planning took 302 s (322 s and 328 s for the
  two earlier passes of that lineage). `environment.md` gained 8 stray headings (+6.0 KiB, 10,531 to 16,637 bytes), and AD-4 was
  filed after `## Superseded`, below the still-mislabelled AD-3, so it was born retired. The multipass journal reads this as
  worse than the same lineage's second pass, which added 1 heading. Read against all four second passes (7, 1, 6 and 4 stray
  headings; +4.5 to 6.4 KiB) it is one heading above the highest count and inside the byte range: the growth per pass looks
  steady and not accelerating, and what builds up is the mislabel. This refines F13 and does not contradict it: a chain still
  repeats the leak, and nothing here shows it growing faster than the pass number. Evidence: c55d0bc0 and the multipass journal's
  Round 1.
- F17 (firm). What a chain waits for moved from a decision to a measurement. The owner approved the multipass D1 to D5 ("Approve
  all", 15ef676f). D2 to D4, the fix for what stages write, is one candidate kept off main until its A/B test (E2) meets a bar
  written before the first run. E2 as last recorded on main (d1e5df37): started 17:33:58; held 41 min 41 s from 17:47:28 so
  another session's two test-writing pilots could use the shared port-4180 lane first, 31 min 21 s of it with nobody holding the
  lane; resumed 18:29:09 with chain A1's second case. No E2 result is on main at df44fd30 (superseded 2026-11-01 by Round 3,
  F21: E2 reported, 6a6badb3). The multipass work's own offline replay found a gap in the candidate: both entries filed as
  retired when new (AD-3, AD-4) were written by the plan stage, which the candidate's packet line does not reach (c55d0bc0). So
  the born-retired entry may survive E2.
- F18 (firm for what exists; hermetic). The modifying link is built. `ticket-sla` (bf68e959) asks a pass to replace "a ticket is
  escalated at most once" with "at most twice, and by priority" and to change the requirement, the decision behind it and the
  tests together. Its acceptance is its own (the second link's hidden check reads the very sentence it replaces, so a correct
  delivery would fail it), its ledger says whether the old entries were changed or left standing, and 11 hand-written variants
  each failed exactly the checks that read what they break. There is no live run: E3 waits for E2 (superseded 2026-11-01 by
  Round 3, F22: E3 ran, a232cf03). Its request is hand-written; none of the peek's three `decision` rows (csv-report numeric
  forms, a delivery route for `ticket.assigned`, person-level delivery) concerns how often a ticket is escalated. So M2b still
  has no case that starts from a real leftover, and `ticket-sla` is the fixture for U10, not a measurement of value.
- F19 (firm, about this document). Revision 2 recorded moving status as fact. It was authored at 17:19:26 and committed, after a
  rebase, at 18:43:03; the owner's approval (15ef676f, 17:29), E1's result (c55d0bc0, 17:40) and `ticket-sla` (bf68e959, 18:41)
  are all ancestors of it, so three of its statements were already stale when it was published. This was known and disclosed to
  the owner, who chose to merge it as written. Rule kept: a status that moves is written "as of <commit>" and points at the
  journal that holds the live state; the design's header says so.
- F20 (firm, from source). The skill card's byte bound limits a build: `card_max_bytes` is 30500 in
  `test/fixtures/shiploop-card-ledger.json` and `skills/shiploop/SKILL.md` is 29,955 bytes, so about 545 bytes of card text; a
  candidate for another change exceeded the bound on 2026-10-31 (df44fd30). Added to the design's section 8 and section 6. (Figure superseded 2026-11-01 by Round 3: 30,011 bytes and about 489 bytes of card
  text as of e13af240; the bound and the reading stand.)

Changed in the design: the header, sections 1, 2, 3.B, 4.7, 5, 6, 7 (M2a and M2b), 8 (one bullet), 9 (one row), 10 (D2's
condition) and 11 (U2, U9, U10). D1 to D4 keep their recommendations.

Superseded (kept above, marked): Round 1's "Open:" line and F13's closing clause; revision 2's statements that E1 was queued and
unrecorded, that `ticket-sla` was designed and not built, and that a chain waits for "the multipass decisions".

Harness and test-case changes: none. No skill change, no change note, no release. Effect on earlier results: F13 is refined by
F16 and Round 1's "Open:" line is superseded; nothing else changes.

Routine decisions: revision 3 is a third commit on top of the published two and not an amendment of them (they are on
origin/main); the base is origin/main because the canonical `main` had diverged; the candidate's own hash (another session's local
branch, not on main) is not cited in the design; nothing is pushed until the owner says so; no release (documents only).

Open: the replay with a second reader (design section 7, M1); a revision 4 when E2 reports; M2a after E2 and E3; the owner's D1 to
D4. (Superseded 2026-11-01 by Round 3: revision 4 is written, and E2 and E3 have reported.)

## Round 3 — 2026-11-01 — revision 4: E2 and E3 reported

Question: revision 3 was published with its moving statements written "as of" its base, df44fd30. Two multipass results landed
on main after that base: the A/B test of the fix for the leaks (E2) and the first live fourth pass (E3). Which statements of
the design do they overtake, and does either change a recommendation?

Conditions: base e13af240100c066489e83c028d97339845402b55 (origin/main), in the worktree and on the branch of revision 3
(`docs/follow-on-rev3-dd7837`). Revision 3 was rebased onto 17cbbd9b830e8e95385617f0c1c9fb68dd850546, tested (the quick tier, pinned to that base)
and pushed first, as published 7bb1c35683a18d37bd800df12a2f4c45c32ecc77, at the owner's word. Main then moved by five commits (a Python 3.9
floor, release skill-craft 2.27.2 and shiploop 1.26.2, two documents); revision 4, the second commit, was rebased onto the last of them and its
facts were re-checked against it. No model call and no ShipLoop run. One reader, Claude Sonnet 5.5, who also wrote the design.

Read in full: 6a6badb3e6b8bd858015817c40ee216addf76ba6 (E2), a232cf038789b532c8485c7583136177cb6be929 (E3) and
9d5067f3d6b38ff0231e3e98835d78fb96e5a37a (the fix to the fourth link's case); the multipass journal's summary table, the results
of E2 and E3, its routine decisions and its unknowns; the multipass plan's diff from df44fd30 to the base; the E3 readout and
the `environment.md` figures of `e3-ledger.json`. Read in part: the first 40 lines of ed2f0a34 (another session's learning
commit, which cites a candidate for another change measured at 30,440 bytes against the card bound; that candidate is not on
main). Searched: a keyword pass (follow-on, multipass, ticket-sla, chain, superseded, SKILL.md, card, port-4180, lease) over the
messages of the 19 commits between df44fd30 and 17cbbd9b found the multipass commits above and nothing else that bears on the
design; the others, judged by subject and by the lines of six of them that mention the card or bytes, are other sessions' E2E
apparatus, retention and Salesforce work. `git diff --stat` over that range lists 23 files, none under `skills/`, `agents/`,
`plugins/`, `changes/` or the card ledger. The five commits after it, up to the base, were checked the same way and by the diff of
the card: the multipass plan, journal, readouts and cases are unchanged; no module the design cites changed (the diff names the CLI
entry scripts, the hook scripts, the README and a new `shiploop_pyfloor.py`); the one fact of the design they move is the card's
size, which release 2.27.2 raised from 29,955 to 30,011 bytes against the unchanged bound of 30500 (94bccf23 added one sentence naming
the Python 3.9 floor), so Round 2's F20 stands in its reading and its figure of about 545 bytes becomes about 489 (marked in F20
above). The candidate branch was rebased again onto the base while this was written, and still does not touch the card. The Round 0
reading of the engine holds.

Findings:

- F21 (firm for three chains per arm, one pair of cases, passes 1 and 2, Codex gpt-6.1-terra at xhigh). The fix for the leaks met
  its bar. E2 ran 2026-10-31 17:33:58 to 21:40:17: three chains of two passes on the 1.26.0 tree and three on the candidate. 12 of
  12 runs passed and B1 to B5 all held. Stray headings added to `environment.md`: 0 in all six fix passes, 7, 7, 2, 6, 5 and 8 in the
  control (second passes 0, 0, 0 against 7, 6, 8). A pass that added a decision changed a live section of `architecture.md` in 6
  of 6 fix passes against 3 of 6. Second-pass time was 1.02 times the control's (limit 1.2); tokens 49.1 M a run against 49.0 M.
  B1 (no entry filed as retired when new) held without being tested: the control never did it in six passes. The notice caught
  the mislabel once live (B3 pass 2), printed in the packet of a stage after `plan`, the route the offline replay had predicted;
  it is the first live catch. Limits: the candidate is a bundle, the passes are 1 and 2, the machine was shared. The candidate is
  not on main; the release is recommended and is the owner's call. Evidence: 6a6badb3 and the multipass journal's Round 2 result.
- F22 (firm for one run; the persistence of the mislabel is exploratory, n=2, one lineage). The first live fourth pass (E3)
  delivered what it was asked and repeated both leaks. `ticket-sla` continued from E1's output on published ShipLoop
  (skill-craft 2.27.1, ShipLoop 1.26.1, no fix), Codex gpt-6.1-terra at xhigh: 993 s, 37.0 M tokens, 158 model calls. All 16
  hidden checks passed, requirement R-7 was changed in place, all 8 IDs were kept and one earlier test file was modified. It is
  recorded FAILED, 15 of 16 checks, on one check of the new case that was wrong (F23). `environment.md` gained 9 stray headings
  (+6.4 KiB, 16,637 to 23,175 bytes), and the new decision AD-5 was filed under `## Superseded` behind AD-3 (mislabelled since
  the lineage's saved second pass) and AD-4 (E1's). Two of two later passes (E1, E3) filed their new decision as retired. Both
  continue the lineage whose saved second pass (bf-codex-r2) made the mislabel; one of the four saved second passes made it and
  none of E2's six control passes did. This extends F13 and F16. The multipass commit reads it as the mislabel compounding with
  the pass number (it needs a trailing `Superseded` section, which exists only after an earlier pass has made one). I read it
  more narrowly: the evidence is one lineage, so it shows the mislabel persisting once made, and the pass number is not
  separated from the lineage. It also leaves open what F16 could not say, whether a pass retires or supersedes an old decision,
  because AD-3 was already marked. Evidence: a232cf03, the multipass journal's Round 3 result, `round3-readout-output.txt` and
  `e3-ledger.json` under `docs/experiments/multipass-20261031/`.
- F23 (firm). A case written from the request and a synthetic prior had two wrong words at its first contact with a real prior.
  Its retention check looked for the word `comment`, copied from the previous link; the prior spec already contained it, so the
  in-place route could not pass. The ledger's pattern for the old rule used the request's wording ("at most once") where the third
  pass had written "enqueued once". The calibration passed because its synthetic delivery added a requirement ID, taking the other
  of the two routes through the check, and the pattern had been written from the request. Both are fixed (9d5067f3), with three
  tests that fail on the old case file; the verdict was corrected after the result was seen and both verdicts are kept. For M2b:
  a case that tests a follow-on request takes its checks from a real prior pass and exercises each route. Evidence: 9d5067f3, a232cf03.
- F24 (firm, from the saved file; one run). After the fourth pass `environment.md` holds 40 headings (1 title, 33 level-2, 6
  level-3; 23,175 bytes), exactly the listing cap (`_CONTENTS_LINES` is 40 in `shiploop_navigator.py`), where aa601d37 had put the
  first cut at the fifth pass's packet by arithmetic. Counted by a short script over
  `~/e2e-runs-multipass/20261031/mp-codex-ticket-sla/work/docs/shiploop/environment.md` (outside the repository), skipping fenced
  code; the rendered listing was not printed. As of the base, the fifth pass has not run.
- F25 (firm, about this document). F19's rule reached the headline of a passage and not every sentence. By my count of the
  revision 3 text, 15 sentences state a status that E2 or E3 overtook ("waits for E2", "has not run", "queues behind"); 3 carry
  "as of" and 12 do not, mostly in table rows and bullets. Revision 3 landed with E2 and E3 already on main (they were pushed while
  it waited for the owner's word), so those 12 were stale from the day it landed. Revision 4 corrects them and labels each moving
  statement it keeps. A search of a draft for "waits", "not run", "queues", "pending", "running" and "next" finds them.
- F26 (firm for the reasoning; no recommendation changes). What a chain waits for moved a third time: from a decision (revision
  2) to a measurement (revision 3) to a release (revision 4: the fix met its bar and is not on main). Beyond the release, one
  question the A/B does not answer applies to a chain and not to a person-started pass: the fix was tried on passes 1 and 2, and
  a chain reaches the later passes, where a mislabel, once made, persists. It is stated in 4.7 and U9 and not in D2's wording.
  D2's condition keeps its text, with its two parts marked (met; not yet merged). Whether to add "seen on a third pass" is the
  owner's call.

Changed in the design: the header, sections 1, 2, 3.B, 4.7, 5, 6 (three rows updated and three added), 7 (M2a and M2b), 8 (one
clause), 9 (one row), 10 (D2's parenthesis) and 11 (U2, U9, U10). D1 to D4 keep their recommendations.

Superseded (kept above, marked 2026-11-01): Round 2's F17 sentence "No E2 result is on main at df44fd30" (true as of that base), F18's
"There is no live run: E3 waits for E2", Round 2's "Open:" line and F20's byte figure (29,955 bytes, about 545 of headroom); revision 3's
statements counted in F25.

Harness and test-case changes: none. No skill change, no change note, no release. Effect on earlier results: F13 and F16 are extended
by F22 (the later-pass mislabel is now two of two); F17's gate moved (F26).

Routine decisions: revision 3 was pushed first, unchanged except for the rebase (its hash changed when it was rebased onto the base),
and revision 4 is a second commit on top of it, so the stale statements and their correction both stay visible in history (the owner's
order: merge, then E2 as revision 4); E3 is folded in with E2 although the owner's words named E2, because the design says in several
places that a fourth pass has not run and E3 landed within hours of E2; the candidate's branch is named and its hashes are not
(another session's local branch, rebased since the A/B); a moving statement is labelled "as of" the base and the candidate's state "as
read for this revision"; no release (documents only); main moved while revision 4 was being checked, so it was rebased a
second time and the card figure it stated was corrected before the push.

Open: the replay with a second reader (design section 7, M1), which could now include the runs under `~/e2e-runs-multipass` (whether
they reached handoff is not checked); M2a, after whatever the owner orders on port 4180 next (the multipass plan names a smaller second
chain); the fix's release and a fix-arm third or fourth pass (the multipass journal's next measurements); the owner's D1 to D4; a revision 5 when the fix is released or a fix-arm later pass reports. (Superseded 2026-11-01 by Round 4: the replay is done and its set included the
`-multipass` runs, 14 of which reached handoff; revision 5 folds in the replay and E4's pre-registration, so the next revision waits for the fix's release or an
E4 result.)

## Round 4 — 2026-11-01 — the replay with a second reader (design section 7, M1)

### Plan (written and committed before any reader was called; the result follows below it)

Question (design section 7, M1): do readers other than the first agree with the first reader's classes of what finished runs
leave under `Open for the next run`, on `gap` and `decision` in particular? The first reader (Claude Sonnet 5.5, who also wrote
the design) found 0 gaps and 3 decisions (F08, F22, F23) in 25 rows from 122 finished runs, and marked four rows arguable (F03,
F11, F16, F22). The owner answered "Yes" to "Should I run the M1 replay with a second reader next?" (2026-11-01). The replay is
offline: it calls models on short texts, runs no ShipLoop and respects the owner's hold on live E2E cycles
(d9fefb1144dea7f9a8d85b5897ad1275dbe08a07).

Conditions: base e81fdb55d58bdb0bcc8c1643d93d5973709100e4 (origin/main), in a fresh worktree on branch
`docs/follow-on-m1-replay-8e83c2`. Read for the plan: design section 7 and the peek's README, `classification.json`, `peek.py`
and `peek.json` (17cb4e4ad859f89bbc578c06abf974e47e0933e3 created them and 671873bce787d9e9c25bbbe8ab64e7c7f7061db0 touched
them); `ledger.find_runs()` of the coverage ledger (6c6265747116b6ba2ca2a8dd11a2f28bb0551b3b). The commits behind the new rows
were read in Round 3.

Set. 32 rows, one per run. F01..F25 are the 25 frozen strict rows of the peek (their texts are `peek.json`'s, their labels are
`classification.json`'s). N1..N7 are the strict rows of runs that are not in the snapshot: a scan of every `~/e2e-runs*` root, the
way `ledger.find_runs()` reads them, found 44 runs finished since the snapshot (so 166 finished runs now against the snapshot's
122) and 7 with real text under `Open for the next run`: `-hostonly` 2, `-multipass` 3 (E2's A2 and B3, E3), `-xr` 1 and `~/e2e-runs`
1. The other new runs' text is "none" or opens with a "none" phrase, or the run had not reached handoff (`-tl` 1). `build_set.py`
builds the set (`rows.json`, sha256 3b4c67b18f9dfe7a5fb6b98263b38c1bbef22cd7b6740222f4e4d879a7c827be): full text, and the
request of each run as its numbered sentences (17 distinct requests). The first reader labelled N1..N7 before any other reader was
called (`first-reader-new-rows.json`, sha256 a7e424970ed18602fc9fb2b00cff5bd8e2e105283e0adb7fefb6df64c2bd97a9): N1 person
(arguable: capability), N2 note, N3 extension, N4 note, N5 note, N6 extension (arguable: note), N7 note (arguable: debt); no gap.

Readers, all blind to every label, note and arguable flag, to case and run names, and to each other. The prompt holds the seven
class definitions of `classification.json` verbatim, each row's full text and its request (home directory prefix redacted);
rows are shuffled and renamed r01..r32 and requests lettered by first appearance (`make_prompts.py`).
- sol-a, the second reader and the main comparison: Codex GPT-6.1 Sol (gpt-6.1-sol, fallback disabled) through
  `ask.sh sol --json --effort xhigh --profile ask` in an empty temporary directory (read-only sandbox, web search off). Class
  order as in the file, shuffle seed 20261101, prompt sha256 a71e3d77ebd38637fe837eb0477c3bf6b502a5a2e1220c9b008632fdf58251ab.
- sol-b, the retest of sol-a (its own noise): the same model and effort, class order reversed, seed 20261102, prompt sha256
  1b13815bf30be49b79174d4276b5bca90e62080cf5a154cd3967ce77fa15ff07.
- grok, the third reader: `ask.sh grok --json --no-tools` in an empty temporary directory, file class order, seed 20261103,
  prompt sha256 d985061da8648dd58f463a21f0f6f8fc208b58f3ba9c34b2476a207115c60ed1. It classifies all 32 rows blind, which is the
  design's "third reader" for every disagreement, and makes a 2-of-3 majority possible.
A reply that is not one JSON array with all 32 ids and valid class names is rerun once with the same prompt; a second failure is
reported as a failed reader. `parse_reader.py` reads a reply; `compare.py` computes everything below (its self-test passes).

Measures: fine agreement over the seven classes and coarse agreement over the five groups of `classification.json` (person and
capability; extension and debt; note; decision; gap) for every pair of readers, over all 32 rows and over the 25 frozen and the 7
new; Cohen's kappa on the coarse groups (descriptive, n is small); the gap and decision analyses; the 2-of-3 majority of first,
sol-a and grok.

Reading, the design's three rules made precise before the run:
- G. A row that sol-a or sol-b labels `gap` is a candidate. It is confirmed if grok also labels it `gap` and, on my reading of the
  row, its run's request and its state, a request sentence is unmet or an assumption was refuted in a way that needs no person.
  A confirmed gap means D2 has a real use: record the run. A candidate that is not confirmed is listed and not counted.
- N. If no gap is confirmed, `decision` is the only live class. Its count is the 2-of-3 majority over the 166 finished runs
  (the first reader's was 3 of 122). Building a field for it stays the owner's call (D4), and the recommendation stays not to build
  until runs of the owner's own features show more.
- D. The `decision` class is separable from `extension` and `note` if the Jaccard overlap of the sets of rows that first and sol-a
  label `decision` is at least 2/3. Below that, readers cannot agree on it and it cannot be script-routed: show the non-note
  leftovers unclassified. The design's two test rows, F22 (decision or extension) and F11 (note or decision), are reported for
  every reader; the rule uses the whole set.
- Rows with three different majority votes are unresolved and go to the owner.

Predictions (probability, written before any reader was called; `compare.py` scores them):
- P1. sol-a labels no row `gap` (70%).
- P2. Coarse agreement between first and sol-a is at least 26 of 32 (65%).
- P3. Jaccard(first, sol-a) on `decision` is at least 0.67 (55%).
- P4. At least half of the fine disagreements between first and sol-a fall on rows the first reader marked arguable (60%).
- P5. sol-a and sol-b agree on at least 28 of 32 rows (60%).

Not concluded whatever the numbers: agreement between readers does not make a label true; it says nothing about the value of a
follow-on run (design M2b) or about the owner's own features; the readers share the first reader's class definitions; the
corpus is E2E cases, small and saturated.

Files: `docs/experiments/follow-on-replay-20261101/` (`build_set.py`, `make_prompts.py`, `parse_reader.py`, `compare.py`,
`rows.json`, `first-reader-new-rows.json`, `prompts/`). The archives live outside the repository, so `build_set.py` reproduces only
on the owner's machine.

### Result (2026-11-01; exploratory; 32 rows, four readers, E2E cases only)

The three calls ran in parallel from 05:57:33: sol-a returned at 06:01:02 (3 min 29 s), sol-b at 06:01:11 (3 min 38 s), grok at 06:03:00
(5 min 27 s). sol-a and sol-b: `gpt-6.1-sol`, effort xhigh, fallback off, read-only sandbox, web search disabled (the envelope says so);
grok: `grok-4.7` (served `grok-4.7-build`, verified), effort xhigh, `--no-tools`. The Codex CLI printed a warning that its version (0.166.0) differs
from the runner's contract (0.144.5). The prompt hashes in the status files matched the plan. No reply needed a rerun and no log shows a tool or command
call. Evidence: `docs/experiments/follow-on-replay-20261101/` (`README.md`, `compare-output.txt`, `extra-output.txt`, `third-look.txt`, `readers/`).

Findings:

- F27 (interim; 32 rows). The first reader's classes hold across readers. All four label 28 of the 32 rows alike. First against sol-a: 28 rows
  alike on the seven classes, 30 on the five coarse groups (kappa 0.91); against sol-b 28 and 28 (0.83); against grok 30 and 30 (0.91). The three other
  readers agree with one another on 30 to 32 rows. `note` (11 rows), `debt` (1) and `capability` as the first reader read it (4) are unanimous.
- F28 (interim). No gap is confirmed. The first reader, sol-a and grok labelled none. sol-b, with the classes listed in reverse order, labelled F01 and
  N1 `gap` (sol-a called both `capability`, grok `person`); grok did not agree, and both runs record the open item with a person as owner and no authenticated
  browser as the reason (`third-look.txt`). The `person` / `capability` / `gap` line is where the definitions are least stable: the same reader moved
  across it when their order changed.
- F29 (interim). `decision` is the only live class, and it is smaller than the first reader said. F08 (csv-report numeric forms) and F22 (the delivery route
  of `ticket.assigned`) are `decision` for all four readers; F23 (record the requesting user's answer to A1, among other handoff duties) is `person` for all
  three others. By majority: 2 rows out of 166 finished runs (1.2%); the first reader alone: 3 (1.8%); the snapshot: 3 of 122 (2.5%). Rule D is met exactly:
  Jaccard(first, sol-a) is 2/3, by one row. The design's two test rows agree across all four readers (F22 `decision`, F11 `note`).
- F30 (interim). One class per text is lossy. The rows the readers split on that are not the gap line, F18 and F23, each mix items of different classes (F18:
  three optional items and an unconditional "stop it by hand"; F23: an answer to record, a place where knowledge lives, a readiness check). The follow-on list in the
  design would classify entries, not whole texts, so this split would not arise there; whether readers agree entry by entry is not measured.
- F31 (firm, about the first reader). The `arguable` flags did not predict disagreement. Of the seven flagged rows (F03, F11, F16, F22, N1, N6, N7) six kept the
  first reader's class in every reader; the other three rows readers moved (F01, F18, F23) were not flagged. Prediction P4 missed. On F18 the majority is the better class.

Predictions (written before the run; `compare.py` scores them): P1 (70%) held; P2 (65%) held, 30 of 32; P3 (55%) held, at the threshold; P4 (60%) missed, 1 of 4;
P5 (60%) held, 30 of 32. Four of five.

Rules applied. G: no gap is confirmed. N: with no gap, `decision` is the only live class, 2 of 166 by majority (3 by the first reader); the recommendation stays not
to build the follow-on list until runs of the owner's own features show more. D: `decision` is separable from `extension` and `note` on this evidence, by one row.

Not concluded: the classes are not shown to be right (every reader had the first reader's definitions); nothing about the value of a follow-on run (design M2b) or
about the owner's own features (none of the 32 rows is one); the new rows are correlated (the same few ticket cases).

Routine decisions: the post-hoc statistics are in `extra_stats.py`, separate from the pre-registered `compare.py`, which was not changed after the readers were called;
the raw replies are kept in `readers/` and the readers' thinking summaries are not; the third look at the two gap candidates was made even though rule G was already not met
(Grok did not agree), to record why they are not gaps.

Open: revision 5 of the design folds this result in (the commit after this result, described below); the owner's D1 to D4; M2a
and M2b as before; a rerun of `peek.py` and this replay when runs of the owner's own features have finished (the cost is a few
minutes and a few model calls).

Changed in the design (revision 5, the commit after this result): the header, sections 1, 2, 3.B, 3.C, 4.7, 5 (a subsection for
the replay; the multipass bullets), 6 (the row for 3d5732d0, the as-of labels), 7 (M1 done with its result; M2a's lane), 8 (the
card figure's as-of), 9 (three rows), 10 (D1, D2, D4) and 11 (U1, U6, U9 and a new U11). D1 to D4 keep their recommendations:
the replay applies the design's own reading rule, so D1 and D4 lose the wait for M1 and now say what to wait for instead (runs
of the owner's own features). The peek's README marks its "one reader" claims as superseded.

Facts re-checked against 3d5732d0 (main moved while the replay ran, and the multipass work pre-registered its Round 4 there):
the multipass plan and journal changed (E4 fixed on 2026-11-01 before any run: six runs in three matched pairs on passes 3 and
4, each fix run beside a run without the fix on the same prior, bar B1 to B4, control K, predictions P1 to P8; not started);
`skills/shiploop/SKILL.md` is still 30,011 bytes against 30500 and the card ledger is unchanged; the candidate is still only on
the other session's local branch, rebased onto 3d5732d0. The multipass Round 4 names this journal's F21 to F26 reading (the
mislabel persists once a lineage has it) as one of the two readings E4 separates, and U9 as the open question. Its reading rule
says what each outcome would mean: a run without the fix that does not leak on the tidy prior would read as the mislabel bound
to a seeded lineage.

Superseded (marked 2026-11-01): the design's statements that M1 was a plan or that no second reader had classified the rows
(sections 1, 3.C, 7, 10, 11); Round 3's "Open: the replay with a second reader" (done, Round 4).

## Round 5 — 2026-11-01 — the build: the recommend-only follow-on list, and its live check

### Plan (written and committed before any live run; the result follows below it)

What happened. The owner replied to the Round 4 question "Keep D4 at 'do not build now'?" with "Rebase, Merge to main and publish,
implement improvements" (2026-11-01, verbatim). I read it as: build the recommend-only list of the design (D1 a follow-on run, D2
recommend-only, D3 no ceiling, D4 build), then rebase, merge to main and publish. That reading is mine; the feature commit says so
and is the one to revert if it was not meant. The design's own rule N, fixed before the M1 replay, still says the list will
recommend a run rarely (decision in 1.2% to 1.8% of finished runs, no gap), so this release is no new evidence of demand.

Built (feature commit 826c951ccfdecb8f48e406f8fbdacb6a69daabbc, on origin/main d06e18a56ee43db8d04dc872e680d4efdd33f076, which holds
skill-craft 2.28.1 and ShipLoop 1.27.0): `skills/shiploop/scripts/shiploop_follow_on.py` and its wiring; its message holds the
shape decisions, the tests (14 new, fail first) and the packet-size figure. Two things of the design's draft changed at build, both
recorded there: no per-entry `id` and no per-entry `evidence_refs` (the script resolves the cited record from `source`), and a fifth
source kind, `result:<stage>`.

Question for the live round (design U1, the unknown the offline replay cannot answer): given the built list, does a real model at
the handoff write a list the gate accepts, with sources it can cite and classes a reader finds supported by the cited record?

Conditions. Host Codex, model gpt-6.1-terra, effort xhigh, `--source checkout` (this checkout's build, the plugin tree recorded in
each run's `invocation.json`), planning review `stage`, the harness's defaults otherwise, started with `test/shiploop_e2e/run.py` and
nothing else, one run per output folder under `/Users/dadleet/e2e-runs/2026-11-01/follow-on-live-*`. Cases: `hello` (1 run: a
trivial request, few leftovers), `csv-report` (2 runs: its saved runs gave the peek its F08 `decision`, "whether exponent notation
and a leading + count as numeric", so it is the case where a decision is most likely) and `seat-reservations` (1 run). Those three
need no fixed port: another session's pilots hold the lease of `user-listing`'s (ca85a372a8e79577ac01591d1d07e0ceaee4f0ed). Four runs in all, at most four
at once. The machine's load average was 80 when this was written, from other sessions' work, so durations are not comparable with
the baselines'.

The owner's hold on new live E2E cycles, which other sessions record (d9fefb1144dea7f9a8d85b5897ad1275dbe08a07 and the commits that
cite it), concerns improvement cycles. These four runs are the verification round the release preflight orders after a ShipLoop
change, which AGENTS.md lists as routine ("launching verification runs") and the memory note "proactively run verification" asks
for; they are not a cycle and decide nothing about the next one. If the owner objects, the runs are cheap to stop.

Rules, fixed now (each is read from the run folders by `docs/experiments/follow-on-build-20261101/extract_follow_on.py`, which only
reads):
- R1. The gate holds. Every run reaches `done` with every verdict passing (invoked, plugin, process, shiploop, committed, checks). A
  run that does not, for a reason traced to the list (a refusal loop, a template the model cannot fill), is a defect to fix before any
  release; a run that fails for another reason is reported and does not decide R1.
- R2. First-try shape. The refusals at the handoff that name `follow_on` are counted per run (each `complete` command that leaves the
  cursor at the handoff). Mean at most 1 per run; none above 3.
- R3. Support. Each accepted entry is read against the record its `source` names and called supported, partly supported or
  unsupported; the reader is me, alone (exploratory, no second reader).
- R4. No inflation, no silence. Entries per run are reported. A run whose list is `[]` while its release-verify `lessons.open_next`
  or its unverified list holds an item that is not "none" is flagged as possible silence (a flag, not a defect).
- R5. Recommendation. Each run that recommends a follow-on run is read: is the request file one a person would start?
- R6. Size. The handoff packet's `chars` and `printed` in each run's trace, against the same figures in saved Codex hello runs
  (2026-11-01: 18,957 and 15,375).

Predictions (probability, written before any run):
- P1. All four runs reach `done` with every verdict passing (80%).
- P2. Mean refusals naming `follow_on` is at most 1 per run, and no run needs more than 3 (65%).
- P3. At least 3 of the 4 runs file at least one entry; `hello` files none or one (60%).
- P4. At least one of the two `csv-report` runs files a `decision` entry about numeric forms or arguments (40%).
- P5. No run files a `gap` (85%).
- P6. At least 90% of the entries are supported by their cited record (70%).

Decision rule. The release goes ahead when R1 holds. The other results change the design note's revision 6 and the next measurement
(U11, M3), not the release. If R1 fails for a reason in the list, I fix it, rerun the run that failed, and do not release before a run
passes.

Not concluded whatever the numbers: four lists are an existence check, not a rate; one reader judges support; the cases are the E2E
corpus (small, saturated, every run completes); whether a person ever starts a recommended run is M3 and is not measured; entry-level
agreement between readers (U11) is not measured.

Files: `docs/experiments/follow-on-build-20261101/` (`extract_follow_on.py`, then the per-run extracts and the README).

### Result (2026-11-01; four live runs on Codex only, hermetic checks on the build; exploratory for any rate)

Hermetic, on the feature commit 826c951ccfdecb8f48e406f8fbdacb6a69daabbc and what followed (measured in the worktree, on a machine at load average 50 to 87):
- The new suite `test/shiploop-follow-on.test.py` was written first: against the unchanged code 14 tests gave 7 failures and 9 errors (every CLI route
  said "result has unsupported fields: follow_on"); with the build 14 of 14 passed (45.7 s alone), and also under the system Python 3.9.6, the floor. It has
  17 tests now: ba3297d707329a6500ac036577d3f211b2e6a352 added two route tests (the isolated run's start repository, and a request holding backticks, `$(...)`, quotes, `$HOME` and `;` reaching
  the CLI as one plain argument, run through a real shell) and 12d293a83ab2c05d30bb575b3d0c5989604a3601 one for the stale request file.
- Older suites after the build: callback-contract 98 OK, handoff 133, full-runtime 2, navigator-v4 18, loophole-gates 5 (two new dodge rows), guidance,
  packet-completeness (`follow_on` joins its gate words), head-order, navigator-contract, consumer-delivery, test-loop, package-integrity 11, clean-consumer 3
  and test-groups 52 OK. Four of them (handoff, full-runtime, navigator-v4 and callback-contract's `field_values`) had to carry `follow_on: []`, as predicted
  from d84d30a977aa584ecc748fb34982f2bd7add21df.
- The quick tier (`--changed-from d06e18a56ee43db8d04dc872e680d4efdd33f076`, 42 suites because the navigator is a hub, `--jobs 4`): 1,564.5 s wall, 41 passed and 1
  failed. The failure was a fifth hand-built handoff result, `shiploop-actual-improve-cli` (found only by the tier); 12d293a83ab2c05d30bb575b3d0c5989604a3601 fixed its stand-in and the rerun passed
  (100 tests, 886 s). `shiploop-progress` and `shiploop-cross-run` also failed in a wider sweep and fail on a clean origin/main (72fa7f4cd9ab370703c272eda65a0831575128e4) at the same load
  (2 and 3 failures there): the progress observer's timing, not this change.
- The rest of the ShipLoop family (the suites the tier did not select) was swept three times on the loaded machine. The first sweep (3 at a time, catalog order) was stopped
  by me after 15 suites, with `shiploop-progress` and `shiploop-cross-run` failing as they do on the clean main control. The second (4 at a time, risk first) ran 19 suites
  on the pre-merge tree: 18 passed and `shiploop-e2e-slice` erred once in its temporary-folder cleanup (OSError, Directory not empty; that test alone passes in 7.6 s);
  I stopped it when the third merge changed the tree under it. I then ran `shiploop-workspace`, `shiploop-return-review` and `shiploop-e2e-release-slice` by hand on the merged tree:
  3 tests of the first two failed (a stand-in handoff result without `follow_on`, F37), fixed in 74b2112fabe241c9717ba02d0f2afa01018c89b8. The third sweep (6 at a time) ran the 48 suites no run had yet covered on a tree with the change, on
  the merged tree: 47 of the 48 had finished, all passing except two tests that are not about this change: `shiploop-workspace`'s `test_public_return_is_refused_before_release_or_handoff_without_mutation` (a snapshot comparison that includes the progress observer's file) fails alone on this branch's older main base and on a clean control at that base (72fa7f4cd9ab370703c272eda65a0831575128e4), and passes alone on the final candidate tree (the latest main plus this change) and on a control at the latest main (419dd4f308fb3b26c1902dd829c10c0e0720f048); `shiploop-e2e-ticket-sla`'s `test_a_requirement_edited_in_place_passes_retention_when_it_names_the_new_variable_and_fails_when_it_does_not` (one of five retention checks false under load) passes alone in 8 s. The last suite, `shiploop-e2e-test-adequacy`, was still running when this entry was committed; CI's full tier runs it on the push. The quick tier on the merged tree (`--changed-from 4224161b095792825befe2a384075fab5660ae05`, 46 suites, `--jobs 6`): 46 of 46 passed in 597.6 s wall. On the final candidate tree after the fourth merge, test-groups (52 tests), shiploop-e2e-baseline (177), shiploop-e2e-platform (169), shiploop-e2e (495, 836.7 s) and shiploop-follow-on (17) passed.

Live, scored against the plan (the table, the readings and the verdict blocks are in `docs/experiments/follow-on-build-20261101/`; the entry in
`test/shiploop_e2e/LEARNINGS.md` is c593e8f27d65d7157438d9b14c2dd7c09f3bbc89):
- R1 holds: hello, csv-report twice and seat-reservations all reached `done` with every verdict passing (turns 143, 178, 185, 216; 12.4 to 20.0 minutes).
- R2 holds: all four handoffs were accepted on the first `complete`, so 0 refusals naming `follow_on`.
- R3 holds on n = 2: the two entries (csv-report, class note, source `assumption:A2`) are supported by the assumption they cite.
- R4: entries 0, 1, 1, 0; one flag of possible silence (seat-reservations: `[]` beside a `lessons.open_next` that holds a revalidation condition), not a defect.
- R5 not exercised: no gap and no decision, so no request file and no start command in any run.
- R6 holds: the handoff head printed 16,850 to 17,462 characters against the cut of 20,000 (+1,475 printed on hello against a saved Codex run).
- Predictions: P1, P2, P5 and P6 held; P3 (at least 3 of 4 file an entry; 2 did) and P4 (a csv-report run files a decision; neither did) missed.
- The tested tree is 2da2d4f3d11b0f468c14ff48e6158a7bb334e8ee's (plugin tree bf3be9d89072). The released tree adds ba3297d707329a6500ac036577d3f211b2e6a352 (one `except` clause) and test-only commits.

Findings (status; citations):
- F32 (firm for these runs): a real model fills the list on the first try. The template row and one duty paragraph were enough for 4 of 4 accepted first
  submissions with real sources. Evidence: the four runs, `docs/experiments/follow-on-build-20261101/runs.json`; 7c2ce6cb9345959292c38688106a4c8d16be865c.
- F33 (exploratory): the lists were conservative. Both csv-report runs recorded the default for the open tie rule and header as a `note` on plan assumption
  A2 (which the ledger still shows `open`); hello and seat-reservations said a passing test settled the same kind of A2 and filed nothing. The replay's
  csv-report `decision` (F08) did not recur, and with no arm without the list this round cannot say whether the list changed that. Evidence: `readings.txt`.
- F34 (firm): the targeted run of the suites I expected to hand-build a handoff result missed one, which the quick tier found (F37 adds two more that the tier missed). A gate that requires a key at the
  CLI is found in fixtures by running the tier, not by guessing which suites import the helper (d84d30a977aa584ecc748fb34982f2bd7add21df had the same effect).
  Evidence: 12d293a83ab2c05d30bb575b3d0c5989604a3601.
- F35 (firm): the claim a commit lists as "not covered by a hermetic test" deserves its test. Writing the one for an isolated run's start repository found
  that `source_repo` caught OSError and ValueError while the store raises `StorageError`, so a missing workspace record would have raised out of the final
  `complete` for a run that recommends a follow-on run. A real isolated run always has the record, so no live run could meet it. Evidence: ba3297d707329a6500ac036577d3f211b2e6a352.
- F37 (firm): the quick tier selects suites by the files a branch changes, and it passed 46 of 46 on the merged tree while two suites it had not selected still hand-built a handoff
  result: three tests in `shiploop-workspace` and `shiploop-return-review`, each expecting the return-receipt refusal that follows the follow-on gate. Seven suites in all carry a stand-in
  result that had to get `follow_on: []`. A sweep of the rest of the family found them; CI's full tier on a release push would have found them as a red main, which blocks other
  sessions' Codex resumes. Evidence: 74b2112fabe241c9717ba02d0f2afa01018c89b8.
- F36 (firm): `shiploop-progress` and `shiploop-cross-run` fail on a clean origin/main at load 50 to 87 (72fa7f4cd9ab370703c272eda65a0831575128e4); a failure of either in this branch's tier is
  not evidence about the change.

Changed in the design (revision 6): the status and the header; section 1 (a "Built" bullet, the order bullet); 3.C's verdict; 4.2 (the shape fixed at build:
five texts, no `id`, no `evidence_refs`, five kinds of `source`) and 4.4's source rule; section 6 (three rows); section 8 (what was built, and what was not,
above the sketch); section 9 (two rows measured or partly measured); section 10 (D1 and D4); section 11 (U1, U2). Nothing else in the design moved.

Facts re-checked against origin/main 6a6cb10172f78737b685a127c1c2f2be5c2aca52 (the newest main commits touch the E2E cycle's docs and tests only): the multipass fix is
still off main (its branch tip moved to 065a73f0a4ec); E4 was not re-read; SKILL.md is 30,011 bytes against the 30500 bound and the feature commit did not
change it. The build branch was merged with origin/main at f1a5868da64587610d6711105650caacb2d557fc (a merge, not a rebase: the plan, the evidence and the LEARNINGS entry cite the hashes).

Third merge (9f07ba40a2beeacf9d51b936c55d4177d7dcbe18): origin/main moved to 4224161b095792825befe2a384075fab5660ae05 while the release candidate was being cut, because another session released skill-craft 2.29.0 and ShipLoop 1.28.0 (the
step-plan focused-ID rule) at 09:01. The pending note therefore ships as ShipLoop 1.29.0 and skill-craft 2.30.0 (`release.py --dry-run` on the merged tree; the first candidate's
2.29.0 / 1.28.0 was discarded unpublished). The merge conflicted only in the append-only `LEARNINGS.md` and `baselines.jsonl`, resolved by keeping both sides (the other session's
entry and rows first). SKILL.md is 30,115 bytes against the bound of 30500 (their release added 104; the feature added none). Their step-plan and prompt changes were not in the tree
the four live runs tested, so the merged tree was verified again by the quick tier before the release (the line below).

Fourth merge: origin/main reached d71eaa7198772501b189dff76308d4ee7ac533cb with the multipass work's E4 result (its Round 4: with the fix no later pass filed its new decision under `## Superseded`, 0 of 3, against 4 of 5
for the old ShipLoop; a clean prior still mislabelled, so this journal's lineage reading, F21 to F26, is not needed and not sufficient alone). The design note's multipass subsection now says so
("Update, as of d71eaa7198772501b189dff76308d4ee7ac533cb"), and the statements elsewhere that E4 had not started are marked as of 3d5732d0. D2 is unchanged: the fix is not on main and its release is the owner's word.

Superseded (marked 2026-11-01): Round 4's "the recommendation stays not to build until runs of the owner's own features show more" was not kept: the owner asked for
the build (see the plan above). Its evidence about demand stands. The design's "Nothing is built, adopted or released" (revision 5's status line) is replaced
by revision 6's.

Open (as written before the release; its first two items are done, see "Released" below): the sweep line above while it runs; a post-release run of the published build
(`--source marketplace`) as the check of the exact tree; and still open after it: U11 (entry-level agreement, now possible on model-written entries); M3 on the owner's own
features; M2a (a recommended run started from a model-written request, which no live run reached); E4 and the multipass fix's release (the other session; E4 reported, the
release is the owner's word).

Released (2026-11-01): skill-craft 2.30.0 / ShipLoop 1.29.0, release commit 41ee3d89d580fb715fc90994b2361348550698c7. CI on the release push (run 41332749569) succeeded on all nine jobs (release-boundary, plan, full / core, full / shiploop-1, -2 and -3, full / python-floor, full / e2e-apparatus, hermetic). It was pushed with `scripts/release-push.py` (four checks passed: sync-plugin-views, marketplace packages, release boundary, test-groups). Hosts refreshed: Claude and Grok from 2.29.0 to 2.30.0, and Codex's marketplace on the second try (the first clone timed out at 30 s on the loaded machine); Cursor is the owner's through its app. Smoke on the published build: the no-model probes (`docs/experiments/clean-install-20261101/probes.sh`) passed (the installed plugin 2.30.0 is identical to the published tree; `shiploop --help` and `workspace start` exit 0 on stock Python 3.9.6 in a clean environment; the five hooks exit 0 with python3 absent and under Python 3.7.3; the CLI refuses 3.7.3 with the floor message), and a live Codex hello on the marketplace build passed every verdict (docs/experiments/follow-on-build-20261101/README.md, "The published build"); the paid Claude-host live session was not run. The three sweep failures are accounted for: the last sweep suite, `shiploop-e2e-test-adequacy`, failed one test under a load of up to 270 (22 of 25 mutants survived) and passes alone (1 test, 457.7 s, OK); `shiploop-e2e-ticket-sla`'s failing test passes alone in 8 s; `shiploop-workspace`'s failing test passes on the latest main base. No suite of the family fails because of this change.

## Round 6 — 2026-11-01 — the recommended-run path, live on a primed request (design M2a, mechanics)

### Plan (written and committed before any live run; the result follows below it)

What happened. Round 5 shipped the list and said what its four live runs did not reach: none filed a gap or a decision, so the request file, the printed start command and a
run started from that request were covered by hermetic tests only. The owner answered that closing message with "Determine how to conclude, plan out, and implement."
(2026-11-01, verbatim). I read it as: conclude the open item that is mine to conclude, with a written plan first, and do not wait for a natural gap (a decision in 1.2% to
1.8% of finished runs, Round 4). That reading is mine and the runs are cheap to stop. It is not read as a go for the value question (M2b), for auto-start (D2) or for a
release; a release follows only if a defect needs a fix.

Question (design U2 and the mechanics half of M2a). When a real run files a `decision`, does ShipLoop write a request a person would start and print a command that works as
printed, and does a run started from that request deliver, keep what the project already did, and say what it did with the finding?

Why a primed request. A natural decision is too rare to wait for. The request below reserves one choice for the person in plain words and says nothing about ShipLoop, so the
model-written entry, its source, the gate, the request file and the command are all real; only the occasion is arranged. The result therefore says whether the path works. It
does not say how often the path is used (M3) or whether a follow-on run repairs anything (M2b).

Conditions. Host Codex, model gpt-6.1-terra, effort xhigh, `--source checkout` from a detached worktree at d2c6a5ff62a323a0f29c9d9b06c2f9bb5031a8a7: the release commit
41ee3d89d580fb715fc90994b2361348550698c7 (skill-craft 2.30.0 / ShipLoop 1.29.0) plus its release record, without the init-guard work that origin/main has gained since
(d8a8dce0 and f9f91667 are not in it; their change note is unreleased), so the tree is the one the owner's hosts run. Planning review `stage`, the harness's defaults otherwise,
started with `docs/experiments/follow-on-recommended-run-20261101/launch.sh` over `test/shiploop_e2e/run.py` and nothing else, outputs under
`/Users/dadleet/e2e-runs/2026-11-01/follow-on-live2-dacc9b/`. Two link-1 runs of the same request at once (`link1-a`, `link1-b`); then one link-2 run for every link-1 run that
recommended a follow-on run, started from that run's own `follow-on-request.md` in a copy of its checkout (`--continue-from`). A program without a server leases no port. The
machine is loaded by other sessions' work (load average 56, 104 and 96 over 1, 5 and 15 minutes at 10:30), so minutes are not comparable with any baseline.

The owner's hold on new live E2E cycles (d9fefb1144dea7f9a8d85b5897ad1275dbe08a07, 2026-10-31) concerns improvement cycles, and other sessions have run cycles since. These runs
verify a shipped feature, which AGENTS.md lists as routine ("launching verification runs"), as Round 5's four did. They decide nothing about the next cycle.

Link-1 request (verbatim; `request.txt`):

> Write slug.py, a small command-line tool: `python3 slug.py TITLE` prints TITLE as a URL slug on standard output and exits 0. Lowercase the letters, turn each run of spaces or
> punctuation into a single hyphen, and drop hyphens from both ends, so "Hello, World!" gives hello-world and "  Many   spaces here " gives many-spaces-here. Titles with letters
> outside A to Z, such as é or ü, are my call and not yours: the SEO team has not decided whether those letters are changed to their plain letter or kept as they are, and I will
> tell you when they have, so do not choose. Until then, print "undecided: non-ASCII" on standard error and exit with status 2 for such a title. Add unit tests with unittest.

Checks, each a shell command in the run's folder (`launch.sh`; calibrated before any run by `calibrate_checks.py` on three hand-written variants, 15 of 15 as expected). Link 1:
"Hello, World!" gives hello-world; the spaces title gives many-spaces-here; "Café" exits 2 with "undecided: non-ASCII" on standard error (the reservation was kept);
`python3 -m unittest -q` passes. Link 2: the first two, the unit tests, and "Café" does not end in a traceback (status other than 1), whichever way the finding is settled.

Instruments, before any run: `check_printed_command.py` (runs the start command a finished run printed, on a copy of its checkout) was calibrated by hand on an adversarial request
(backticks, `$(touch ...)`, quotes, a semicolon, a newline, é) with the done packet's own command form: exit 0, a workspace record, the injected marker file absent, the stored
request equal to the file's text but for one trailing newline (what command substitution does). No model was called by any of this.

Rules, fixed now (the folders are read by `docs/experiments/follow-on-build-20261101/extract_follow_on.py`, which only reads, and by `check_printed_command.py`):
- R1. Link 1 holds. Both link-1 runs reach `done` with every verdict passing. A run that fails only the reservation check chose for the reserved letters: it is reported as having
  ignored the request, is not a ShipLoop defect, and its list is still read. A run that fails for a reason traced to the list (a refusal loop at the handoff) is a defect.
- R2. A recommendation exists. At least one link-1 run's accepted handoff lists a `gap` or a `decision`, its request file exists, and the done packet and the report print the
  start command. The entry is read against the record its `source` names (supported, partly supported, unsupported), and so is whether the request file says what the request
  reserved.
- R3. The printed command works as printed (no model): exit 0, a workspace record, the stored request equal to the file's text but for its last newline, a clean stderr, and
  nothing the model wrote run by the shell.
- R4. A run started from the request delivers. Each link-2 run reaches `done` with every verdict passing. A failure is read before it is called a defect of the request: a run
  that refuses or misreads the request is one; a host or environment failure is rerun once.
- R5. Where the finding lands (descriptive): the files link 2's commits touch against link 1's HEAD (expected: slug.py, its tests, files under KNOWLEDGE/), whether link 2's
  intake or spec record names the non-ASCII finding, and what link 2 did for "Café" (kept the reserved error, transliterated, kept the letters).
- R6. Its own list. Link 2's handoff is accepted on its first `complete`; its classes; whether it files the decision again (nobody answers it in link 2).

Predictions (probability, written before any run):
- P1. Both link-1 runs reach `done` with every verdict passing (75%).
- P2. At least one link-1 run files an accepted `gap` or `decision` (85%); both do (60%).
- P3. Neither link-1 run files a `gap` (80%).
- P4. R3 holds for every command tried (90%).
- P5. Every link-2 run reaches `done` with every verdict passing (65%).
- P6. Every link-2 run touches only slug.py, its tests and files under KNOWLEDGE/ or docs (70%).
- P7. At least one link-2 run files a `decision` again (45%).

Decision rule. R2, R3 and R4 hold: the path is shown live on a primed request; the design note's M2a records it; no code change and no release. A mechanical defect (the request
cannot be started, the command misreads the text, a run started from the request is refused at intake or loses the finding for a reason in the request's wording): fix it
generically with the test first, release when preflight and CI pass (routine), and rerun the failed link on the released build. R2 fails (no recommending entry in two runs): the
path stays unproven live; read what each filed and why; a further attempt only with a changed request written down first.

Not concluded whatever the numbers: two primed runs are a mechanics check, not a rate (M3) and not the value of a follow-on run (M2b); M2a's comparison with a hand-written
request on the same base is not run; one host and one model; the person who answers a decision is not simulated (link 2 gets the request as ShipLoop wrote it); U11 is not measured.

Files: `docs/experiments/follow-on-recommended-run-20261101/` (`request.txt`, `launch.sh`, `calibrate_checks.py`, `check_printed_command.py`, then the extracts and the README).

### Addendum 1 (written after the link-2 runs ended and before any further run)

What happened. Link 1 ran twice and link 2 once for each (the result section follows with the figures). Both link-2 runs ended BLOCKED at the spec stage, after 25 turns and about 1.3
minutes (`link2-a`, `link2-b` under the output root): the baseline tests passed, the earlier request was read, and each run accepted a blocked result that asks the requester one
question, with options and a `no_default` reason that quotes the earlier "do not choose":
- link2-a asked "How should non-ASCII letters be handled in slugs? For example, should café become cafe or remain café?" with the options "Convert letters to plain ASCII where
  possible" and "Keep non-ASCII letters"; its reason: the prior request says the requester decides and prohibits choosing on their behalf.
- link2-b asked "What policy should slug.py use for non-ASCII letters?" with the options "Keep non-ASCII letters in the slug", "Convert non-ASCII letters to plain letters" and "Keep
  the interim error for now"; its reason: the original request reserves the policy choice to the requester, and the interim error does not settle the finding.
The harness graded both FAIL on `shiploop` (not done) and `committed` (HEAD unchanged) and classed them BLOCKED ("awaits a person (answer), and states why no default would do");
their checks passed (the earlier behaviour was kept, the product unchanged).

Reading against the registered rules. R4 (each link-2 run reaches `done`) is not met, 0 of 2, and P5 (65%) missed. The plan said a failure is read before it is called a defect of
the request. These runs neither refused nor misread it: they found the finding, read the earlier request through the pointer the request file carries, and asked the requester the
one question the finding leaves open, which is what SPEC S-14 prescribes when no default can proceed. I read the unanswered case as the product working, and as a gap in my plan: it
registered a decision nobody answers and called the outcome "delivers", when a decision can be delivered only once someone answers it. The harness will not resume a blocked run
as if answered (`run.py --resume-run`: a blocked run waits for a person), so the answered half cannot be driven by resuming link 2.

What is added to the plan, registered now, before any further run. Link 3: the same request file with the requester's answer appended (`answer.txt`, verbatim below), in a copy of the
same link-1 checkout, one run for each link-1 run, with the same host, model, effort and tree, started by `launch.sh link3`. The answer is what a person would type when ShipLoop
asked; the harness has no other way to supply it.

> The requester's answer to the decision above: the SEO team has decided that a letter with an accent is changed to its plain letter (é becomes e, ü becomes u), and any other
> character outside A to Z is treated like punctuation. Make that the rule and remove the interim error.

Checks: the first two and the unit tests as before, plus "Café Über" gives cafe-uber and "Café" exits 0 (calibrated with the others: all statuses as expected on the three variants).
- R7. A run started from the request and its answer delivers. Each link-3 run reaches `done` with every verdict passing.
- R8. The finding is closed in the records (descriptive, with the lines quoted): the unit tests exercise the answered rule; the committed spec, architecture and README no longer say the
  policy is undecided or describe the interim error as current.
- R9. Its own list. The handoff is accepted on its first `complete`; a `decision` about the same policy is not filed again (it would mean the list does not see an answered finding as
  closed).

Predictions (written before the link-3 runs): P8, both link-3 runs reach `done` with every verdict passing (80%). P9, neither files a decision again (85%). P10, in both, the committed
knowledge files stop describing the policy as undecided (70%).

Decision rule. R7 and R9 hold: the whole path (a recommendation, a request, a command, a run that asks, an answered run that delivers) is shown live on a primed request; the design note
records it; no code change. A mechanical defect in the answered run or its list (a re-filed decision for a closed finding, a refusal loop at the gate): fix it generically with the test first
and rerun. Still not concluded: as the plan says above, and the person is simulated by one fixed answer, so what a person does when asked is not measured.
