# Batch 1009, group G3 (acceptance): journal (K1, W1, I2, U1)

Living journal for the four audited candidates of group G3, built in worktree `b1009g-aaa47e` on the base
`847fa64e` (skill-craft 1.24.0 and the round-1 analysis). One section per candidate, each landing in its own
commit (a section's heading says "this commit" in the commit that adds it and names the commit after).
Each entry gives the status of its findings (firm, interim, exploratory, superseded), the evidence, and what
stays unmeasured. Evidence: `docs/experiments/batch-1009-round1-analysis-20261008/analysis.json` (why the
candidates exist), `docs/experiments/batch-1009-g3-acceptance-20261008/design-audit.json` (the audited design
and its audit, the acceptance criteria: verdict approve-with-corrections; every correction it required is
applied and listed in "Audit corrections").

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

## I2: the Improve parent packet restates the goal and Done-when (this commit; status: firm that the packet carries them, unmeasured that reviews improve)

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
