# Improve stop rule: one pass that leaves the content unchanged (journal, 2026-10-16)

Status: **implemented on branch `feat/shiploop-eff-stop-6afcbc`, unreleased.** Owner decision 2026-10-16; SPEC S-10 carve-out of that
date ([test/shiploop_e2e/SPEC.md](../test/shiploop_e2e/SPEC.md)). Edit this page rather than deleting from it; mark a claim
superseded with its date and reason.

## Question

An Improve loop ended after two consecutive passes the model called trivial (`required_trivial_reviews: 2`), or after one pass when
the first pass changed nothing and Git agreed (decision 2026-09-26, commit 2be7906b). Does the second confirming pass earn its
time, and can the loop stop on a measured fact instead of a count?

## Evidence (firm, one run, one case)

[improve-value-study.json](experiments/improve-stop-rule-20261016/improve-value-study.json) is the Improve-value study of the live
Salesforce-chess run: five finished stages, 21 passes, 41.2 minutes.

| stage | passes | material passes | what the tail was |
|---|---|---|---|
| spec | 8 | 5 | P6 a one-word label fix (labelled non-trivial), P7 and P8 no change |
| test-strategy | 5 | 1 | P2 no change; P3 polish (non-trivial) reset the streak; P4 and P5 no change |
| plan | 4 | 1 | P2 polish (non-trivial); P3 and P4 no change |
| step-plan | 1 | 0 | no edit; the unchanged-first-pass exit fired |
| test-spec | 3 | 1 | P2 and P3 no change |

8 material passes, 10 that changed nothing. Three polish edits (spec P6, test-strategy P3, plan P2) were classed non-trivial; each
reset the streak and forced two more passes. Limits: one run, analyst-judged materiality, a confirming pass can catch something next
time, same-model passes are weak detectors either way (the study's `limits_of_evidence`).

## Decision

Complete the loop when the report calls a pass trivial AND satisfied AND the checks passed AND the content tree after the pass equals
the tree after the previous pass (the first pass: the tree at start). Content tree = the worktree's Git tree plus the bytes of the
stage result file that lives outside it. A pass that changed the tree never completes the loop, however it is labelled. No count, no
timer, no iteration cap (decision 2026-10-05 stands; the per-stage `loop_limit` removed in b7653edc does not return). The rule only ever
completes a loop earlier; no stage ends cancelled or stopped because of it. It is the 2026-09-26 rule (2be7906b) generalised from
"first pass only" to "any pass".

## Design (what was built, and the two constraints the brief did not state)

Where: `skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py`; ShipLoop's `improve_start_contract`,
`shiploop_standalone_improve.py`, `shiploop_loops.py`; docs and tests listed in the commit.

- **State.** `start_tree` is replaced by `last_tree` (the content tree after the latest pass; at start, the tree at start) and
  `last_pass_changed_tree` (true, false, or null when unmeasured). `trivial_streak` stays in state: gates 0 and 1 still use it.
- **Contract.** New optional `candidate_paths` (absolute files; a missing file counts as `absent`, so creating it is a change).
  ShipLoop lists `run/inbox/<reviewed action>.md` for every Improve stage, so an edit to a plan, step-plan or test-spec result is seen.
- **Gate value.** `required_trivial_reviews` keeps its name; 2 now means "trivial AND unchanged content" and no longer counts two
  reviews. Values above 2 are refused. Packets at gate 2 report `progress.last_pass_changed_tree` in place of `trivial_streak`;
  `unchanged_first_pass` is gone. **Why the name stayed (constraint 1).** ShipLoop's stage loops (test, quality, verify) and the
  Backchain child hand their contracts to the published `until-loop` plugin on Claude Code, whose runtime is the pinned upstream
  0.8.3 and refuses an unknown contract field. A renamed gate field would have broken those loops on every host that uses the
  plugin, so gates 0 and 1, their contracts and their packet shape are unchanged and only gate 2 changed. The stage loops never carry
  `candidate_paths` (a test pins that).
- **Git required (constraint 2). SUPERSEDED 2026-10-17 (F3): a directory outside Git is now measured through a throwaway bare repository; see the update below.** A gate-2 `start` is refused when the tree cannot be measured (outside Git, unreadable candidate):
  otherwise no pass could ever be shown unchanged and the loop would never end. ShipLoop always works in Git (it commits); the
  synthetic non-Git fixtures in about ten test files now `git init` their workspace.
- **Racy Git (finding, firm).** The first run of the new tests was flaky: a pass "changed" nothing, then "changed" it back. The
  measurement copies the real index into a temporary one, whose fresh mtime defeats Git's racy-timestamp protection, so a same-size
  edit made within the cached entry's second was trusted from the stat cache across a second boundary. The copy is now stamped
  mtime 1 so every entry is re-hashed. A deterministic test (`StatCacheTests`) fails without that line. The old
  unchanged-first-pass shortcut shared the flaw.
- **Old shape refused.** A saved run's state with `start_tree` is refused by `next`, `done` and `read_state` with a message naming the
  way forward; ShipLoop's import refuses a terminal or stopped packet that carries `trivial_streak` at gate 2 or
  `unchanged_first_pass` ("written by an older Until Loop"), and one not run at gate 2.
- **Receipt.** The import takes one review reference, the final pass's `review-<n>.md` (it took two, or one for an unchanged first
  pass). The change gate and the `improve-start --restart-stopped` route key on a completion on the first pass.
- **Vendoring.** The runtime script, `ADAPTER.md` and `runtime-ephemeral.md` are now recorded adaptations in `PROVENANCE.json`
  (upstream hash, bundled hash, reason). Not upstreamed: `/Users/dadleet/src/until-loop` is an old clone (0.8.0) and this work may
  not edit outside the worktree. A re-vendor from upstream must carry the change until upstream has it.
- **Run Review.** The exporter reads a gate-2 receipt (no streak) as `trivialRequired: 0` plus a `Review gate` fact.

## Tests

- `test/improve-runtime.test.py` (29 tests): (a) trivial and unchanged completes at pass 1; (b) an edit then a trivial unchanged
  pass completes at pass 2, not 3; (c) a pass labelled trivial that changed the tree does not complete; (d) a material pass then a
  trivial pass that changes again keeps going; A-B-A trees are not a clean pass; (e) an edit to a candidate file outside the worktree
  counts, and without `candidate_paths` it is not seen; (f) an unsatisfied exit, an incomplete label or failed checks with an
  unchanged tree do not complete; (g) the old state, the retired progress key and a gate above 2 are refused; gates 0 and 1 keep
  their meaning and packet shape; the stat-cache regression; the replay below.
- **Replay** (`StopRuleReplayTests`): the study's per-pass labels and changed flags driven through the real runtime. Stops: spec 7 of
  8, test-strategy 2 of 5, plan 3 of 4, step-plan 1 of 1, test-spec 2 of 3; 21 passes become 15; every material pass comes before its
  stop; the stop pass changed nothing. Run against the old runtime, the file fails 14 cases and errors on 17 (subtests counted separately; 29 test methods).
- ShipLoop: `shiploop-standalone-improve`, `shiploop-stopped-improve`, `shiploop-actual-improve-cli` (the contract lists the result
  file; an edit to that file alone keeps the review going), `shiploop-loops` (stage contracts carry no `candidate_paths`),
  `shiploop-run-review`, `until-loop-vendor`, `improve.test.sh`, and the packet suites.

## Findings and open items

- Firm: the rule is script-measured; the label is necessary, never sufficient (the study's `must_not_reintroduce`).
- Interim: saved minutes. The study estimated about 4 of the 40 Improve minutes (6.7 gross); the replay says 6 of 21 passes. A
  different stop rule changes what the model does in later passes, so this is an estimate until a live run measures it.
- Open (owner): Backchain `converge` keeps its two-consecutive-reviews exit condition, but the bundled runtime no longer counts: the
  gate adds a measurement of the workspace content and needs Git (superseded 2026-10-17: a non-Git directory is measured too, so a
  Backchain call in a scratch directory is no longer refused at start). A Backchain call in a non-Git scratch directory at gate 2 was
  refused at start. Plan files outside the worktree are measured only if the contract lists them in `candidate_paths`, which the
  published plugin refuses, so the Backchain texts do not ask for it.
- Open (owner): upstream the rule to whichguy/until-loop, re-vendor, and then retire the gate's name.
- Known limit: a file a check or tool rewrites on every pass and Git does not ignore reads as a change on every pass; the loop then
  never sees an unchanged pass. The runtime's documents say to ignore the file or clean it up. No cap was added (owner rule).

## Related commits

2be7906b (unchanged first pass, the rule generalised here), b7653edc (no loop limit), 11f5a5b9 and 398466a3 (the packet-head work this
branch builds on).

## 2026-10-17 update: scope narrowed to the stages measured (efficiency plan unit U2; status interim, awaiting the owner's S-10 text)

Question: the one-pass rule was applied to every Improve child, including the review after each implement step, which the study said
not to extend to (it measured five planning stages). Finding F1 of the branch review (P1, owner call): the live run has an implement
review whose pass 3 found a real defect (a case-insensitive string comparison) that a rule ending at pass 2 would have stopped before.

Decision proposed (D-6 / R1 of the plan; SPEC S-10 carries the text, flagged PROPOSED 2026-10-17, and a release waits for the owner):

| Improve rule | stages | gate | ends on |
|---|---|---|---|
| `always` | spec, test-strategy, plan, step-plan, test-spec (measured by the study); system-test-author (writes test code), release-plan (both unmeasured; see the review fixes below) | 2 | one trivial, satisfied pass that leaves the content unchanged (above) |
| `step`, `last-item` | implement (every accepted step), carry-forward (the last item) | 3 | the first pass if it is trivial, satisfied and leaves the content as it started; otherwise two such passes in a row after any pass has changed it |

Built: `stage_spec.IMPROVE_GATES` and `improve_gate(stage)` (pinned to the runtime's own constants by test), `improve_start_contract`
passes the stage's gate and says the rule in the repeat condition (the first build also put it in the exit condition: superseded 2026-10-17, see U2-R1 below), the handoff adds one sentence for gate 3, the bridge
imports a terminal packet from either gate (`_UNCHANGED_GATES`). The runtime reads the gate-3 pair from the latest report,
`trivial_streak` and `last_pass_changed_tree`, so no state field was added. A pass that is unchanged but not trivial and satisfied
(or whose checks failed) breaks the pair; a first pass that is unchanged but unsatisfied does not make the next pass a "first pass".

Evidence (firm for the mechanism, interim for the value): `StopRuleReplayTests` replays the study's 21 passes under gate 3: spec 8,
test-strategy 5, plan 4, step-plan 1, test-spec 3, 21 of 21, the count the run took. So the saving measured above (21 passes become
15) belongs to the five measured planning stages only, and gate 3 costs nothing against the old two-pass behaviour on code reviews; whether the
late find that motivated it recurs is one observation (the implement review of the live run), not a rate. `passes.md` (unit U19)
will record what gate 2 would have done at each step review; the plan re-decides at 10 step reviews with 3 or more edits.

F2 (P1): `test/installed-skill-invocation.test.py` was red on the merged tree (2 failures) and `suite_catalog.targeted` returned
13 ids for the runtime script without it. `_PREFIX_SUITE_IDS` now maps `skills/improve/runtime/until-loop/` to `until-loop-vendor`
and `installed-skill-invocation` (test: `VendoredRuntimeSelectionTests`). The two fixtures were rewritten for the one-pass rule (a
pass edits a file, then an unchanged pass completes) and stay outside Git on purpose, so the installed read-only copy also covers F3.

F3 (P1): a non-Git in-place run could never start its first Improve review (the runtime refused an unmeasurable gate, the error was
swallowed, the restart route failed the same way). `_workspace_tree` falls back to `_plain_tree`: `git init --bare` in a temporary
directory, `GIT_DIR`, `GIT_WORK_TREE` and a temporary index, the same excludes and `write-tree`. Nothing is written into the
workspace; `.gitignore` files in it are honoured; Git failures and timeouts still refuse the start with the existing message.
Cost: a large non-Git tree with no ignore rules is hashed on every pass (the 60 s timeout bounds it).

Review (gpt-6.1-sol, medium, read-only, one round, 2026-10-17): two P2 findings, both about the measurement, none in the gate logic.
(1) With `TMPDIR` inside the measured workspace the throwaway repository (and, in a worktree, the temporary index file) was part of the
tree it measured, so no pass could read as unchanged and the loop never ended: fixed (`_tree_excludes` leaves `until-loop-tree-*` out;
fail-first test `test_a_temporary_directory_inside_the_workspace_is_not_part_of_the_tree`, plain and worktree). (2) A nested Git
repository counts as its commit only, so uncommitted edits inside it do not change the tree. The same holds in a worktree (the stop
branch) and is not new; documented in `runtime-ephemeral.md` rather than guarded (KISS: no observed run has one).

Skew (N12): the published until-loop plugin (0.8.3) reads `required_trivial_reviews: 3` as three trivial reviews and refuses
`candidate_paths`. ShipLoop writes gate 3 only for an Improve child, which runs on the bundled runtime of the selected Improve card,
so no stage loop or Backchain child sees it. Recorded in `PROVENANCE.json`. An Improve-only optional field is the upstream
alternative (D-5).

Related commits: 60018152 and 3b9ca9c9 (the stop rule), 2be7906b (the first-pass rule gate 3 keeps), 398466a3.

### 2026-10-17 review fixes (second review of unit U2, one read-only reviewer; status firm for R1 and R2, interim for R3's owner question)

- U2-R1 (P2, confirmed): the frozen exit condition of a gate-3 review said "once any pass has changed the content, two such passes
  in a row are needed". The runtime asks the model to report `satisfied` only when every clause holds against its literal wording
  (ADAPTER.md, `exit_assessment`), so a careful model reports the first clean pass after an edit unsatisfied, and the runtime then
  rejects that pass as the first of the pair. Driven through the real runtime (`TwoPassGateTests.drive`) with the clean pass
  reported unsatisfied: ENN ends at pass 3, EUNN at pass 4, EUN is still open after three. Fixed at the cause: the two-pass rule is a
  runtime gate, not a clause of the exit the model assesses, so `improve_start_contract` no longer writes it into `exit_condition`
  (the repeat condition, the handoff sentence and the runtime's own packets still say it). Pinned by
  `test/shiploop-quality.test.py` `assert_review_gate` (fail-first: 2 failures on the implement and carry-forward reviews) and by two
  new `TwoPassGateTests.SEQUENCES` rows (EUN, EUNN). The review's second observation is kept as designed: a trivial pass with an
  unsatisfied exit is stricter than the streak of 2be7906b (which counted any trivial pass: U then N ended at pass 2), because an
  unsatisfied exit says something still remains; it is rare once the contract no longer invites it, and the SEQUENCES rows UN, UNN
  and ENUNN pin it. The earlier claim "the gate-3 edge is main's" holds for the first pass only.
- U2-R2 (P2, confirmed): exit item 3 of U2 ("G-SUITES exits 0 on INT after the merge") had been measured on the old base e4c675d5.
  Merging the integration tip df8fef57 (nine units later) conflicted in the imports of `test/shiploop-stage-spec.test.py` (both
  kept) and turned `shiploop-loops` red: U11's contract test expected `{**value, "exit_checks": []}` while the stop-rule runtime also
  normalises `"candidate_paths": []`. The expectation now lists both. The merge is committed on the unit branch (ab5313fe).
- U2-R3 (P2, confirmed): the S-10 proposal, the change note and the SKILL.md sentence called all seven `always` stages "document
  stages". The study measured five (spec to test-spec). `system-test-author` writes end-to-end test code (`edits={'tests'}`), the case
  the study said not to extend the one-pass rule to, and `release-plan` is a plan document; neither was measured. The texts now say so,
  and S-10 carries an open question for the owner: should the review after `system-test-author` run at 3? It runs at 2 as written
  because the gate follows the Improve rule, not what a stage edits; running it at 3 needs a per-stage override in `stage_spec`
  (mapping by `edits` would also move `carry-forward`, which edits documentation and needs 3 as the last item's review). Pinned by
  `test/shiploop-stage-spec.test.py` `test_the_s10_proposal_says_which_always_stages_the_study_did_not_measure` (fail-first).

Related commits: c374549f (the unit), 467268e6, ab5313fe (the merge that carries R2), df8fef57 (integration tip merged),
d1ae8537 (U11).
