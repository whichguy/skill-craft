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
  follow-on runs would repeat this, so a chain waits for the multipass decisions D2 to D4.
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
planned.
