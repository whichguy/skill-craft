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
- **Git required (constraint 2).** A gate-2 `start` is refused when the tree cannot be measured (outside Git, unreadable candidate):
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
  gate adds a measurement of the workspace content and needs Git. A Backchain call in a non-Git scratch directory at gate 2 is
  refused at start. Plan files outside the worktree are measured only if the contract lists them in `candidate_paths`, which the
  published plugin refuses, so the Backchain texts do not ask for it.
- Open (owner): upstream the rule to whichguy/until-loop, re-vendor, and then retire the gate's name.
- Known limit: a file a check or tool rewrites on every pass and Git does not ignore reads as a change on every pass; the loop then
  never sees an unchanged pass. The runtime's documents say to ignore the file or clean it up. No cap was added (owner rule).

## Related commits

2be7906b (unchanged first pass, the rule generalised here), b7653edc (no loop limit), 11f5a5b9 and 398466a3 (the packet-head work this
branch builds on).
