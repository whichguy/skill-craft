# Batch 1010, worktree K, group G7: journal (packet text: A2, A3, A4)

Living journal for the three packet-text candidates of the round-2 analysis, built from the audited designs
(`G7-packet-text.json`, design plus audit; the audit's corrections override the design). One section per candidate, written
in that candidate's own commit. Basis: origin/main b73c30ba (skill-craft 1.25.0, ShipLoop 0.57.0; release commit ea6ce8ce).
Round-2 evidence: the Battleship and Checkers Sonnet runs under `/Users/dadleet/e2e-runs/20261008/` (`r2-battleship-sonnet`,
`r2-checkers-sonnet`; round 1 in the `r1-*` folders). Purpose: each change makes ShipLoop more faithful to its stages, to
`test/shiploop_e2e/SPEC.md` and to the main tenet, and names no sample app.

Status words: firm (hermetic test through the real gate plus a recorded measure), interim, exploratory, superseded.

## A2: the route sentence says plan-return commits the leftovers (2026-10-08)

**Built (status: firm that the sentence now matches the script; interim that it stops the hand commit).** The return-route
sentence every worktree packet prints (`shiploop_workspace.route_sentence`) said the fast-forward needs "the candidate is
committed" and that a plan which "leaves a file uncommitted" falls back to the working tree. It never said that
`workspace plan-return` first commits every uncommitted file that is not protected, caller-excluded or credential-like
(`commit_leftovers`, called from the plan-return branch of `shiploop_protocol`). That is a packet statement the script
contradicts (S-3), and it fits the recorded behaviour: in the Battleship round-2 run the model ran `git add test/system.test.js`
and `git commit` itself (events.jsonl lines 462 to 463 of `r2-battleship-sonnet`; commit 6bba9a6 by the user's identity among
ShipLoop's own commits), with the message "outside the step plan's committed paths ... after the workspace return". Its
`release-plan.md` paraphrases the route sentence and its `outcome.md` kept the false rule "commit them before the return so
clean-copy checks pass". The return was a fast-forward, so the hand commit changed nothing but cost calls and recorded a wrong
rule for the next run.

What changed (text only, one source). `_LEFTOVERS_CLAUSE` is printed straight after the first sentence of the route, in both
the clean-start and the dirty-start sentence: "plan-return commits files left uncommitted, so commit nothing for the return
except a file it reports as not committed." 120 characters per worktree packet (clause and one space), in the full packet file
after the status block, so the kept head is untouched. The clause starts at character 70 of the printed line and ends at 189.

Corrections the audit made to the design, all applied.
- *Early.* The design's sentence was 247 characters and its instruction began at character 281. The Battleship model read this
  line through `cut -c1-300` (events line 372) and `cut -c1-250` (line 388), so it would have been cut off. The clause leads, and
  a test pins that it ends inside 250 characters.
- *"Files", not "product files".* `commit_leftovers` commits everything not protected, excluded or credential-like, so generated
  output is committed too. The integrate row's "delete generated output" still has to be followed; the clause says nothing that
  weakens it.
- *No absolute.* For a file plan-return skips as credential-like, `shiploop_git.skipped_notice` tells the model to replace the
  value and then commit the file, so "you do not commit for the return" would have contradicted the script it describes. The
  clause names that one exception in the words of the notice ("Not committed, ...").
- *Both routes.* plan-return commits leftovers on a dirty start too, and the hazard does not depend on the route.
- *Evidence attribution.* The design said round 1 hand-committed with no sentence in context. Read as events: r1 Battleship event
  464 was a no-op after ShipLoop's own chore commit (the trigger was the old plan-return line "Committed files left uncommitted
  in the candidate", reworded in e39160ae), r1 Checkers event 326 committed README.md because the integrate notice says "Commit
  the ones the product needs", and only r1 Checkers event 362 is a leftover commit nothing instructed. So the sentence is one
  possible source, not the only one, and the integrate row's Develop line and that notice compete with it.

Test, fail first: `ReturnRouteTests.test_the_route_sentence_says_plan_return_commits_files_left_uncommitted_and_plan_return_does_exactly_that`
in `test/shiploop-return-review.test.py` (isolated Git configuration, real CLI). It failed on the two sentence assertions (clean
and dirty start: the clause absent from the printed line) and passed the real-verb subtests at base. Those subtests are the proof
that the sentence is true: plan-return commits `late.js`, prints "Not committed, they look like they hold a credential:
settings.env", leaves run evidence and the credential-like file out of the branch; with that file left the expected return is
`working-tree-return`; committing only that file by hand with the value replaced (as the notice says) restores
`fast-forward-merge`. The first draft of that last subtest committed with `git add -A` and stayed working-tree: it also took the
untracked `.shiploop-improve` run evidence into history, which an excluded path in history turns into a working-tree return. A
hand commit with `add -A` is therefore also harmful, not only redundant.

Margin (measured, not a regression at the real path). `test_return_projection_stays_current_across_terminal_cold_and_report_packets`
in `test/shiploop-workspace.test.py` keeps a terminal packet under `PRINT_LIMIT` (16,000); every embedded path counts. Run from
copies of the tree at fixed checkout path lengths: the base passes up to 126 characters and fails at 128; with the clause it
passes at 120 and fails at 122. This worktree's path is 62 characters. The head window of the heaviest packet is likewise
checkout-path dependent (the audit measured 8024 against the 8000 limit on unmodified code at a 115-character path); it is 7971
at a 62-character path and A2 does not move it.

Suite time (measured, registered value left alone). `test/shiploop-return-review.test.py` ran 24 tests in 74.5 s alone at
load average 2.3 to 2.7; its registered 85.9 s was measured at load 4.6 to 5.1 with 23 tests, so it stays the heavier-load
bound and stays under `QUICK_MAX_SECONDS`.

Not verified, and how to settle it. Whether the sentence stops the hand commit: the model's thinking blocks are redacted, n is 1
per cell, and round 2 showed both models the sentence yet one still committed (it saw it only through a `grep -iE commit` at
integrate and carry-forward, truncated by `cut`; at release-plan it never displayed it). Settle with the next Sonnet pair: any
`git add` or `git commit` by the model after the corrected sentence, and `git log --format=%an` of the returned product showing
only ShipLoop Workspace. If it still commits, add a head-visible `develop` line to the system-test-author row (about 170
characters; the design measured that packet's status end at 5863) and consider scoping the integrate row's "commit the ones the product needs" to
files written during the work item. Whether leaving files uncommitted leaks generated output: `commit_leftovers` already commits
every non-forbidden file, so the behaviour is unchanged; read `git ls-files` of the next returned products.

Related commits: 8eb93c21 (the route sentence, placed after the status block), 313e06ce (commit leftovers before the return),
e39160ae (the plan-return notice reworded), 1f5006e7. Change note: `changes/shiploop/return-route-states-leftover-commit.md`
(patch).

## A3: the directory of the Improve opening file exists where its path is named (2026-10-08)

**Built (status: firm; hermetic through the real CLI).** After `improve-bind` the packet prints "start the bound Improve child
after writing its opening file `<path>`", and the directory that path lands in (`.shiploop-improve/<run>/<action>/`, beside the
runtime receipt) did not exist. `improve-start` then refused with "write the opening file first". Both round-2 Sonnet runs met
it (r2 Checkers events 99 to 103: `ls` of the directory fails with "No such file or directory", then `mkdir -p` and the write
succeed and event 103 starts the child); both then put `mkdir -p` in their
`start.sh` wrapper. That is a step the packet never told them to take, and S-4 and S-5 name directory creation as script work.
The same pattern was fixed for `notes/` in 4fc3b3b8 (emit creates it).

What changed (`shiploop_navigator.emit`, beside the `scratch/` and `notes/` mkdirs). When the state is active and its
`active_improve` child is bound (`skill` is not None), emit makes `improve_opening_path(child).parent` with `parents=True,
exist_ok=True`, inside `try/except OSError`. The condition mirrors `_first_callback_lines`, which is what prints the opening line.
`improve-bind` ends with `emit`, so the directory exists as soon as the bind packet prints; `render` stays pure (graph-dry-run
renders a simulated repository path and never calls emit). A run bound before this change gets the directory on its next `next`
(one supported version: no migration). Not created: `reviews/`, which `_improve_start` makes and nothing writes before start.
`improve-start` keeps its "write the opening file first" refusal, so a missing file is still caught.

Audit points kept. The design proposed a `reviews/` mkdir too; it is unnecessary and left out. Two hand mkdirs in
`test/shiploop-actual-improve-cli.test.py` (before each direct `improve-start` through the bridge binding) stay on purpose: those
tests never pass through `emit`, so they are not compensating for this defect.

Test, fail first: `RefusalRouteTests.test_the_opening_file_the_improve_bind_packet_names_is_written_without_making_its_directory`
in `test/shiploop-callback-contract.test.py` drives the real CLI for the `spec` and `test-strategy` stages: after the printed bind
command the opening path's directory exists and the file does not; `improve-start` still refuses with "write the opening file
first"; deleting the directory and running `next` restores it (a run bound earlier); four filled sections written with no
`mkdir` are accepted. It failed on the directory assertion at base for both stages. The three hand `mkdir` lines that compensated
for the defect (the renamed-heading test, the empty-section test and `OpeningAllowanceTests.at_improve_start`) were removed in
the same commit and failed at base with `FileNotFoundError`, so the whole opening route is now proven without model glue.

Observed after the change: callback-contract 37 tests OK (72.5 s with eleven other suites running; registered 69.1 s alone),
actual-improve-cli 33, delegation 47, full-runtime 2, improve-schedule 33, keepalive 57, navigator-contract 102, navigator-v4 17,
quality 18, status-display 15, packet-completeness 6 and rehydration 12, all OK. Packet text is unchanged, so no packet size,
head window or reference card moves.

Risk accepted: a failing mkdir is swallowed (the refusal path stays intact); in an in-place run an empty
`.shiploop-improve/<run>/<action>/` appears at bind instead of at start (Git lists no empty directory and `.shiploop-improve` is a
protected runtime path). Related commits: 4fc3b3b8 (the same fix for `notes/`). Change note:
`changes/shiploop/improve-opening-directory-created-at-emit.md` (patch).
