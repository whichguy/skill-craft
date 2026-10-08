# Batch 1009, group G3 (acceptance): journal (K1, W1, I2, U1)

Living journal for the four audited candidates of group G3, built in worktree `b1009g-aaa47e` on the base
`847fa64e` (skill-craft 1.24.0 and the round-1 analysis). One section per candidate, each landing in its own
commit (a section's heading says "this commit" in the commit that adds it and names the commit after).
Each entry gives the status of its findings (firm, interim, exploratory, superseded), the evidence, and what
stays unmeasured. Evidence: `docs/experiments/batch-1009-round1-analysis-20261008/analysis.json` (why the
candidates exist), `docs/experiments/batch-1009-g3-acceptance-20261008/design-audit.json` (the audited design
and its audit, the acceptance criteria: verdict approve-with-corrections; every correction it required is
applied and listed in "Audit corrections"), and `docs/experiments/batch-1009-g3-acceptance-20261008/head-size.json` (the packet-size measurement below).

**Purpose (owner).** The sample apps exemplify the ShipLoop SDLC; a change counts only if it makes ShipLoop
more faithful to its stages, SPEC (`test/shiploop_e2e/SPEC.md`) and the main tenet, and stays generic: no
sample-app text, threshold or guard.

## K1: a packet lists every file its close will require (commit 3a7bc9f4)

**Built (status: firm that the packet and the gate now name the same files).** `STAGE_FILES` (what a packet
prints) and `CLOSES` (what `knowledge.check` refuses without) were two hand-kept tables and two entries had
drifted: `CLOSES["test-spec"]` requires `{feature}/plan.md`, `CLOSES["release-plan"]` requires
`{feature}/system-tests.md`, and neither was in the packet's list. `stage_files(stage)` is the stage's own list
plus any close file not already in it; the `prepare` and `release-verify` rows, which only copied `CLOSES`,
are gone. Gates unchanged. Test: `KnowledgeTests.test_a_close_packet_lists_every_file_its_refusal_names`
takes the refusal text of the real gate for every close and requires each named file in `stage_lines`. It
failed on the base for exactly `test-spec` and `release-plan` (4 failures: the class and its subclass), passes
after. The round-1 Battleship run met the `release-plan` refusal twice (analysis.json, candidate K1).
End state: validated. Unmeasured: that a live run now writes the file at release-plan without a refusal.

## W1: five wording defects (commit 2b2f4513; status: firm that the text changed, unmeasured that a model behaves differently)

(a) discovery's first Done-when has an outcome for a repository with no suite (recorded as missing
coverage; both round-1 discovery results improvised it). (b) intake asks for a recorded default and research
for an open item with who can grant it, not for a person (S-14, COMMON). (d) the integrate duty says
"confirm ... assembled", not "assemble or commit" (ShipLoop commits; the stage row says so), and an inline
run no longer reads the bound-chain sentence. (e) `_BACKCHAIN_IMPROVE_OWNER` no longer calls Improve
"independent" in a packet that says its passes are self-passes. Tests (fail first, then pass):
`UnattendedWordingTests` in `test/shiploop-guidance.test.py` (7 failing subtests), the integrate test in
`test/shiploop-delegation.test.py` (both routes), the Improve text in `test/shiploop-improve-schedule.test.py`.
The pins prove the wording changed (validated); whether a model behaves differently is unachievable here and
needs a live run. **Not built, by the audit:** (c), the release-plan Improve guard, which contradicts a
recorded owner decision (`test_improve_retains_coding_and_release_capabilities_with_stage_authority`); both
round-1 release-plan Improve children ended on one trivial pass, so nothing broke. It needs the owner's yes.

## I2: the Improve parent packet restates the goal and Done-when (commit 1f5006e7; status: firm that the packet carries them, unmeasured that reviews improve)

`_goal_lines` returned `[]` for an active Improve child, so the packet a cleared model re-reads while the
child runs had no Goal and no Done-when, only a generic line, although the child's frozen exit condition
already carried them (the gap was the parent, MAIN TENET / S-6). Now it prints "Reviewing the returned
<stage> result. Goal: ..." and the stage's done_when under "a done result must meet each". The audit's
wording corrections: the result is "returned", not "accepted" (the parent stays pending until
improve-complete), and the heading is true for the blocked and repeat results that also start a child.
`_improve_line` adds one sentence that the review checks the result against the Done-when above. Tests:
`test/shiploop-packet-completeness.test.py` (all 8 Improve packets carry Goal and every done_when line;
the 7 reviewed producers say so; 15 failures before), `test/shiploop-rehydration.test.py` (the dry run and a
blocked seed; 2 failures before), `test/shiploop-improve-schedule.test.py` (1 before). End state: validated.

## U1: unverified request outcomes have a structured home (this commit; status: firm for the gate and the printing, interim until a live rerun)

**Question.** Both round-1 runs put an "all verified" headline over a limitation that stayed in prose
(analysis.json, candidate U1; the stage row asked for "pending with its owner and due stage" and the content
had nowhere to live). S-14 requires an open item to be recorded; the 2026-10-04 "a13" route was text only.

**Built.** One optional result key `unverified` on a done product-acceptance result: a list of
`{outcome, reason, check, owner, due_stage}`, `[]` meaning every request outcome was observed by an executed
check. No new state key. New module `shiploop_unverified.py`.
- *Refused* at the CLI gate only (like the plan's assumption list): a missing list, an entry that is not
  exactly those five non-empty texts, a text that starts with `<` and ends with `>` (a template placeholder;
  this also closes the partly edited row the audit found, two placeholders in one field included, and leaves
  markup inside a sentence alone), a `due_stage` that is not a later stage
  (release-plan, release-check, release, release-verify, operations, handoff).
- *Stored* shape-only (`canonical`: a list of text mappings), so every saved run loads and a later edit of the
  field set cannot refuse one (the `skill_na` precedent); a test loads an earlier-shape entry through
  `nav.validate` while the gate refuses it, and renders it in a handoff packet (this found and fixed a
  `KeyError` in the first renderer).
- *Recorded and printed, never judged*: whether the list is complete, whether `[]` is true. The plan's
  assumptions recorded open are printed at product-acceptance and handoff ("the ledger does not update
  dispositions"); each entry is printed at the stage it is due at (the audit's finding that `due_stage` was
  validated but never consumed), the whole list at handoff, and a table in the report. The handoff and the
  report tell "none listed" (key present, empty) from "no list recorded" (key absent: unmeasured, not zero)
  and scope both to product-acceptance's list (an open item another stage recorded is in that stage's result).
  The handoff duty is stated once in the packet (`DUTIES["handoff"]`: list each open item as unverified, with
  who reports what); the printed list leads with a fact, and each row labels the check "to settle:", because the
  check is what the owner does and reports, not a person.
- The Checked-by line names all four refusals (word pins `unverified` and `due_stage` in
  `GATE_WORDS`); the stage row's Done-when and `DUTIES["product-acceptance"]` state the three end states of a
  request outcome (observed; observed another way; unachievable here or not yet due, listed, run continues).
- Tests, fail first then pass: `RefusalRouteTests` (five refusal subtests, each paired with the corrected
  result accepted by the same command, and the template row copied unchanged), `UnverifiedRouteTests` (seven:
  assumptions printed and list recorded; due-stage printing with the "to settle:" row and the handoff duty
  stated once; none listed vs no list recorded; the report with escaping; load vs gate; text that only
  contains angle brackets is accepted; off-stage and non-done refusals), packet-completeness `GATE_WORDS`,
  the wording pins in `test/shiploop-guidance.test.py` (the stage row and duty, and the card and the
  system-test reference, each seen failing when its clause is changed). The helpers that drive the CLI past product-acceptance
  (`shiploop-test-loop`, `shiploop-full-runtime`) default `unverified` to `[]`, as they default the plan's
  assumptions; nine test-loop tests and one full-runtime test failed until they did.

**Packet size** (`head-size.json`, 574 dry-run packets, both delegations, status block END, window 8000):
product-acceptance ends at 5487 (was 5022), +465; the largest Improve parent at 4566 (was 4043); discovery
+57, research +48, intake +0 to +6; every other stage unchanged. The heaviest packet, the step-plan producer in
the revise scenario, is unchanged: 7971 of 8000 in this worktree's path (7928 at the shorter path the
comparison used). The figure is path-specific; the margin of 29 characters is an existing fragility, not caused
by this work. New variable-length text sits after the status block END, never in the kept head.

**Audit corrections applied** (wrong claims in the design restated): the "every other stage within 2
characters" claim was wrong (discovery, research, intake grow by W1); product-acceptance grew +465 here, not
+374; 6695 was the narrative END, not the status END; `html_section` did not print the none/not-recorded
distinction (now built and tested); the Checked-by line did not name the due-stage fault (now does);
"accepted" was inaccurate (now "returned"); the open-assumption label asserted staleness and `limit=300`
truncation was unstated (now "recorded open at planning", default bound); the added integrate sentence
duplicated the stage row (dropped); the text pins are "validated", not "validated another way".

**Unmeasured, with named reason (end state: unachievable here).** Whether a Sonnet 5.5 run given the
template row and the gate lists the unexercised interaction instead of `[]`, and whether `check` earns its
place. Only a live run observes either. Exit: rerun the Battleship and Checkers cases on the next published
build and read each product-acceptance result for a non-empty `unverified` with an owner and due stage; drop
`check` if it is filler; if `[]` comes back over an unexecuted page, the next step is a script-visible probe
of consumer surfaces at test-strategy, not a prose-matching refusal.

## Review round 1: an adversarial review of the four commits (status: firm; fixes folded into the commits)

The review found one major and six minor findings; the history was rewritten (nothing was pushed), so the
commit hashes in this file are the rewritten ones.

- **Major, fixed.** The audited design and its audit, the acceptance criteria every commit cites, existed only
  in a session scratchpad. They are exported to `docs/experiments/batch-1009-g3-acceptance-20261008/design-audit.json`;
  this journal, `head-size.json` and the commit messages cite that path.
- **Journal in the same commit as the result, fixed.** The file first appeared in the U1 commit. Each
  candidate's section now lands in its own commit (K1, W1, I2 and U1 each add theirs).
- **Duration pins, fixed.** `test/suite_catalog.py` `_DURATION_SECONDS` was stale for two suites: knowledge
  `1.0` -> `3.64` (23 tests) and callback-contract `56.0` -> `69.1` (34 tests), the faster of two serial runs
  at load average 5.7 to 6.5. Callback-contract stays under `QUICK_MAX_SECONDS`.
- **The card and the script agree (S-3), fixed.** `UnverifiedWordingTests` now pins the `SKILL.md` paragraph (the
  four refusals, where the list prints, that completeness is not judged) and the `system-tests.md` clause;
  changing either fails it.
- **Duplication inside one packet, fixed.** The handoff packet stated "list each ... as unverified, with who reports
  what" twice (the duty and the printed list). The printed list now leads with a fact; a test counts the duty once.
- **Row label, fixed.** "who reports: <check>" read as a person; the row says "to settle: <check>".
- **Placeholder rule, fixed.** The gate refused only a field that was exactly one `<...>`; "<who> or <who else>"
  passed. It now refuses any text that starts with `<` and ends with `>` (the audit's own test), and a test keeps
  markup inside a sentence accepted. The first U1 message called the `SKILL.md` addition a "five-line paragraph"; it
  is six lines.
- **Not code, left to the owner.** The third statement of the case end states in `DUTIES["product-acceptance"]`
  against `CASE_END_STATES`, and W1(c); both stay under "Open owner decisions" below.


## Open owner decisions and follow-ups (status: exploratory)

1. **W1(c)**, above: needs the owner's yes; the existing text is already scoped to "operations already
   authorized for the current task and stage", which authorizes nothing at a plan review.
2. **`CASE_END_STATES` vs the product-acceptance duty (S-12, soft).** The shared constant says an unachievable
   case reports blocked; `DUTIES["system-test"]` says a person-only case does not make the result blocked;
   the new product-acceptance sentence lists and continues. Rewording the shared constant would be wrong for
   the inner stages (they cannot continue past a failing recorded command) and costs about 75 characters in five
   heads. The more specific outer-stage paragraph wins today; settle by an owner statement or by reconciling only
   the two outer rows.
3. The user-facing Achieved line and narrative are unchanged and still carry the model's headline; whether the
   narrative should carry a script-rendered "N unverified" count (S-15) is a small generic follow-up that the
   second run should decide.
4. Open items recorded at system-test or release-verify reach product-acceptance and handoff only through their
   results (the duty and the handoff line say to read them); if the second run loses them, allow the same key
   at those stages and accumulate.
5. Plan assumption dispositions never close; this build prints them and lets the model account for each, but
   changes no disposition.
6. A delivery-contract run whose result template exceeds 6000 characters falls back to a minimal template that
   omits `unverified`; the refusal still names the shape. Accepted limit of an opt-in mode.

## Verification record

Final tree (after the review fixes and the history rewrite), run from the worktree.

- Every `test/shiploop*.test.py` (61 files), one process each with `SHIPLOOP_PROGRESS=off` only: all 61 exit 0
  (`shiploop-chain-lifecycle` alone, 52 tests, 1485 s; the run was split because a background task is capped
  at ten minutes). An earlier hand run exported `GIT_CONFIG_*` to every suite and the four chain suites failed
  identically on a pristine clone: the product refuses Git context overrides, so that was the runner, not the
  change.
- `bash test/run-all.sh --group quick --changed-from origin/main`: PASS (35 suites, among them the three core
  baseline suites, the mock replay and the ShipLoop suites matching the changed files).
- The suites the group touched (knowledge 23 tests, packet-completeness 6, guidance 56, delegation 47,
  improve-schedule 27, rehydration 11, status-display 15, callback-contract 34, test-loop 81, full-runtime 2) and
  `test/test-groups.test.py` (21, the catalog pins) with `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL` pointing
  at a file that defines the git-lfs filter (clean, smudge, process, required): all exit 0, so the CI lesson of
  `abc47622` holds for them. The status-display kept-head window test is among them, so the heaviest packet is
  still inside 8000 after the review fixes.
- Fail first, for the review fixes: the "<who> or <who else>" refusal subtest failed (the field was accepted); the
  handoff row test failed on the "who reports:" label and then on the duty counted twice (2 != 1); the card pins
  (`SKILL.md` paragraph, `system-tests.md` clause) failed when either clause was changed.
- `python3 scripts/check-release-boundary.py --base origin/main`: OK. `git diff --check origin/main...HEAD`: clean.
- The rewritten tip has the same tree as the reviewed fixes commit except this file.
- Head size: `head-size.json`; the review fixes change only lines after the status block END.
