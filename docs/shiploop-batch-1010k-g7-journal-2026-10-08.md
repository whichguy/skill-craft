# Batch 1010, worktree K, group G7: journal (packet text: A2, A3, A4)

Living journal for the three packet-text candidates of the round-2 analysis, built from audited designs (the audit's
corrections override the design and are listed in each section). One section per candidate, written in that candidate's own
commit, then a section for the review of the first build and its fixes. Basis: origin/main b73c30ba (skill-craft 1.25.0,
ShipLoop 0.57.0; release commit ea6ce8ce). Evidence export (events quoted, grep counts, base-versus-tree packet sizes):
`docs/experiments/batch-1010k-g7-packet-text-20261008/evidence.json`; the line numbers cited below are lines of the
`events.jsonl` of each run.
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
after the status block, so the kept head is untouched. The clause starts at character 70 of the printed line and ends at 189. The
review added one word to the clean-start tail, "or still leaves a file uncommitted" (6 characters), so the fallback reads as what
remains after plan-return's commit and not as a contradiction of the clause.

Corrections the audit made to the design, all applied.
- *Early.* The design's sentence was 247 characters and its instruction began at character 281. The Battleship model saw the old
  sentence in six tool results (events 25, 58, 373, 389, 475, 507; `evidence.json`), always cut at 246 to 382 characters by the Read
  tool, `cut -c1-300` or `cut -c1-250`, and the cut always fell in the second half of the sentence (the longest display ends "...
  leaves a file uncommitted, it applie"). An instruction that began at character 281 would have been cut off. The clause leads,
  and a test pins that it ends inside 250 characters. (The first version of this entry named `cut -c1-250` at line 388; that line
  is a 300-character cut, and the 250-character cuts are lines 475 and 507. Corrected on review.)
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

Test, fail first: `ReturnRouteTests.test_route_sentence_says_plan_return_commits_leftovers_and_it_does`
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
copies of the tree at fixed checkout path lengths, in one environment, bisecting the longest checkout path at which it passes:
the base passes up to 118 characters, the first build (clause) up to 112, and the tree after the review fixes up to 112 (the
review's six extra characters, "still ", move it by well under one character of path). The implementer's earlier figures (126
and 120) came from another environment: the limit depends on the temporary path the test itself uses as well as the checkout
path, so only same-environment figures compare. This worktree's path is 62 characters. The head window of the heaviest packet is
likewise checkout-path dependent (the audit measured 8024 against the 8000 limit on unmodified code at a 115-character path); it
is 7971 at a 62-character path (measured again after the review fixes) and A2 does not move it.

Suite time (measured, registered value left alone). `test/shiploop-return-review.test.py` ran 24 tests in 74.5 s alone at
load average 2.3 to 2.7; its registered 85.9 s was measured at load 4.6 to 5.1 with 23 tests, so it stays the heavier-load
bound and stays under `QUICK_MAX_SECONDS`.

Not verified, and how to settle it. Whether the sentence stops the hand commit: the model's thinking blocks are redacted, n is 1
per cell, and round 2 showed the model the old sentence four times before its hand commit (events 25, 58, 373, 389), each time cut
inside its second half so that what the plan then does was never shown; it never displayed the sentence at release-plan). That
fits the sentence as one source but does not prove it. Settle with the next Sonnet pair: any
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
runtime receipt) did not exist. `improve-start` then refused with "write the opening file first". Round-2 Checkers met it
(events 99 to 103: `ls` of the directory fails with "No such file or directory", `improve-start` says "write the opening file
first", then `mkdir -p` and the write succeed and event 103 starts the child) and kept `mkdir -p` in its `start.sh` wrapper
(event 187). Round-2 Battleship wrote `mkdir -p $D` into its `start.sh` wrapper at event 141 and none of its tool results holds
the refusal (0 hits), so it took the step without meeting the refusal. (The first version of this entry said both runs met the
refusal; corrected on review against the events, see `evidence.json`.) Either way it is a step the packet never told them to
take, and S-4 and S-5 name directory creation as script work.
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

Risk accepted: a failing mkdir is swallowed (the refusal path stays intact, and since the review a test holds it); in an in-place run an empty
`.shiploop-improve/<run>/<action>/` appears at bind instead of at start (Git lists no empty directory and `.shiploop-improve` is a
protected runtime path). Related commits: 4fc3b3b8 (the same fix for `notes/`). Change note:
`changes/shiploop/improve-opening-directory-created-at-emit.md` (patch).

## A4: the test-strategy Done-when asks for a probe of each host tool (2026-10-08)

**Built (status: interim; the condition is model-judged, so whether it changes probing is unmeasured).** The test-strategy duty
(`shiploop_prompts.DUTIES['test-strategy']`, commits 482fff76 and earlier) tells the model to probe a host-dependent case's tool
now by doing the case's first step, against a stand-in while the product does not exist, and to record a failed probe as the access
gap. The paragraph sits deep in a long packet. Neither round-2 Sonnet run read it: no tool result of either run holds "probed now
by doing" or "stand-in" (checked against both `events.jsonl` files), both read only the head (Battleship `sed -n 3,14p`, Checkers
one grep), Checkers' first browser tool use was event 648 against the test-strategy head at events 175 to 183, and Battleship
never ran a command naming Chrome. Done-when is the text every run displays, and the Improve parent packet and the Improve contract
repeat it (`loop_contract.stage_exit`), so the obligation goes there and the how stays in the duty.

What changed (`shiploop_stage_spec._ROWS`, the `test-strategy` row, one fourth `done_when` entry, 307 characters on one line):
"each case that needs a host tool (a browser, a device, an account, a service) names it and cites the output of probing it now by
doing the case's first step, against a stand-in while the product does not exist, and only a failed probe is recorded as the access
gap, with the requirement it leaves unobserved". No change to the duty, to `_COMMON_GATES` or to `GATE_WORDS`. (The first build had
"exist; only a failed probe", 303 characters; the review found that `loop_contract.stage_exit` joins the entries with "; ", so the
Improve contract's exit condition read that entry as two conditions. The only entry in the spec with a semicolon, now none: a
test in `test/shiploop-stage-spec.test.py` pins it for every stage.)

Two audit corrections shaped the wording, both from the designed text's defects.
- *Not a free exit.* The design said "either cites the output of probing it ... or records the access gap". Both round-2 runs
  already wrote an access-gap line (Battleship: "no browser tool may be available"; Checkers: "optional, recorded as unverified
  if not run"), so each would have satisfied that condition unchanged while the head grew. The gap is now only the result of a
  failed probe, which is also what the duty says.
- *The stand-in clause travels with it.* 482fff76 exists because "do the case's first step" at test-strategy, with no product to
  run, sent a Grok run to the product's own address (connection refused, "no browser"). Leaving the stand-in in the unread
  duty paragraph would repeat that wording in the only text the models read.

Honest limit, stated where the check is. ShipLoop machine-checks only the form: a cited absolute `evidence_refs` path must exist.
The `Checked by` line is unchanged and says the model confirms each Done-when condition; nothing checks the probe itself. Where
`planning_review` is `stage` the test-strategy Improve child judges the condition; under `none` only the model's own check
applies, as for the stage's other conditions (S-9). A script-run or script-recorded probe field would be the stronger option; it
is a new mechanism and is deferred, not built.

Measured (graph-dry-run packets, base b73c30ba against this tree, equal tree path lengths so only the change differs; 574 packets,
24 change). Re-measured after the review fix, three trees at equal path lengths (`evidence.json`, `packet_sizes_dry_run`): each
changed packet grows by 310 characters (the entry, its "- " and the newline; the first build's 303-character entry grew them by
306): the test-strategy producer's status block ends at 4832 (base), 5138 (first build) and 5142 (now), and its full file is 33,035,
33,341 and 33,345 characters (inline delivery; ask-agent 33,069, 33,375, 33,379); its Improve parent packet's status block ends at
2973, 3279 and 3283 and the file is 18,183, 18,489 and 18,493. These absolute values are at the scratch path of the measurement;
the growth does not depend on the path. The largest status end of any packet, which sets the kept-head window (the ask-agent revise
packet of the step plan), is 7971 of 8000 at this worktree's 62-character path, measured again after the review fixes, and does
not move. The test-strategy Improve-opening allowance, probed through the refusal's own "may use about N bytes in all" at equal
paths, is 4,706 (base), 4,401 (first build) and 4,397 (now), a fall of 309 bytes; the spec stage's 4,668 does not change. The
design reported the largest opening in five runs at 1,719 bytes. The design's smaller figures (+241) were for its shorter,
defective wording.

Test, fail first: `RefusalRouteTests.test_test_strategy_done_when_asks_a_probe_of_each_host_tool`
in `test/shiploop-callback-contract.test.py`, through the real CLI. It reads the printed head's Done-when (before `Checked by`)
and asserts the four clauses (the stand-in clause with the access-gap rule in one run of text) and that "probing" appears once; the `Checked by` line still says the model confirms each condition
and names no probe; a result citing a probe-output path that does not exist is refused with "evidence_refs cite files that do not
exist" and the same command is accepted once the file exists. It failed at base on the first clause (AssertionError: not found).

Observed after the change (SHIPLOOP_PROGRESS=off, isolated Git configuration): status-display 15 (the head-window test),
packet-completeness 6 (its Improve-packet check asserts every done_when line, so the new entry is covered), stage-spec 9,
rehydration, guidance, packet-bounds, navigator-contract 102, delegation 47, revise, improve-schedule and navigator-v4, all OK.

Not verified, and how to settle it. (1) Whether the line changes probing: read the next paired runs for a tool call that opens a
stand-in page or lists the host tools before test-strategy is accepted, or an access-gap line in `test-strategy.md` that names
the requirement it leaves unobserved and cites the failed probe's output. (2) Cost: a revalidating run re-probes every host tool,
and under `planning_review: stage` the Improve child may send back results with no cited probe (S-10 leaves iterations
uncapped); read the stage-level call counts in the next pairs, no threshold is invented here. (3) A Chrome-flag iteration at
test-strategy is a possible time sink; the duty already says a failing probe is a gap to record.

Related commits: 482fff76 (the stand-in duty), 1f5006e7 (the Improve parent packet restates the Done-when), 62b6ac89 and 1b9918ab
(A2 and A3, this group). Change note: `changes/shiploop/test-strategy-done-when-host-tool-probe.md` (patch).

## Review of the first build, and its fixes (2026-10-08)

An adversarial review of 6b20f6a2 found no blocker and no major defect, and six minor findings. It re-ran the suites, ran ten
mutants (eight killed) and reproduced the packet growth. What each finding led to, one commit per candidate on top of 6b20f6a2.

1. *A3: the guard around the mkdir was untested* (a mutant that replaced `except OSError` survived). **Fixed** in bd3785cb:
   `RefusalRouteTests.test_a_directory_that_cannot_be_made_does_not_stop_the_bind_packet` plants a regular file where
   `.shiploop-improve` belongs, accepts the bind, and requires the printed start command and the "write the opening file first"
   refusal. Mutation check on this worktree: with `except ZeroDivisionError` in its place the test fails at the bind step with
   "ShipLoop blocked: [Errno 20] Not a directory"; the source was restored byte for byte. Not a fail-first test (the guard existed);
   the test is the missing holder of it. The other survivor, dropping the `status == "active"` condition, is equivalent in
   practice and left alone.
2. *A4: the entry held a "; " of its own* and `loop_contract.stage_exit` joins entries with "; ", so the Improve contract read it
   as two conditions. **Fixed** in 2419b331: "exist; only" became "exist, and only" (307 characters). Held for every stage by one
   assertion in `StageTableTest.test_every_row_states_a_goal_and_how_it_is_confirmed` (no ";" inside any `done_when` entry); it
   failed before the change for test-strategy alone, on the assertion. The A4 callback test's clause pinning follows the joined text.
   Costs, re-measured: each changed packet grows by 310 characters (was 306), the test-strategy opening allowance falls by 309 bytes.
3. *The evidence lived only under `e2e-runs` and a session scratchpad.* **Fixed**: `docs/experiments/batch-1010k-g7-packet-text-20261008/
   evidence.json` (the pattern of the 1009f export) holds the quoted events, the grep counts and the base, first-build and
   review-fix packet sizes, built from the event logs by a script, not typed. Building it corrected three statements of the first
   journal, each marked where it was made: (a) Round-2 Battleship never met the "write the opening file first" refusal; it put
   `mkdir -p` in its wrapper at event 141 (A3); (b) the 250-character cuts are events 475 and 507, line 388 is a 300-character cut,
   and the old route sentence reached the Battleship model in six tool results, four before its hand commit, always cut inside
   its second half (A2); (c) the bare scratchpad file name in the header is gone, replaced by the corrections themselves.
4. *A2: the tail "or leaves a file uncommitted" looked contradictory after the clause, and the dirty-start half was asserted
   only as text.* **Fixed** in 6049ae17: the tail reads "or still leaves a file uncommitted" (+6 characters; failed first on the
   assertion), and the test runs plan-return on a dirty-start workspace with the user's source edit kept in place, because a moved
   source blocks plan-return (the dirty root's `late.js` is committed by it). That second check verifies a true claim and did not
   fail first. The dirty-start sentence was left as it is: "it is not a Git merge or commit" follows "The return applies only
   the kept files", not the clause.
5. *Registered durations and the "34 tests" comment in `test/suite_catalog.py`.* **Kept, deliberately.** The comment is the record
   of a past measurement at that test count, not a claim about today's count. Measured now: callback-contract 39 tests in 81 s
   and return-review 24 tests in 90 s with five suites running in parallel on a loaded machine (registered 69.1 s and 85.9 s),
   each far under `QUICK_MAX_SECONDS`. No new top-level test file, so no suite registration or pinned count changes.
6. *Style.* **Fixed**: one blank line before the new return-review method (it had two, which made the class look closed) and
   shorter test names (the 129- and 133-character names are now 66 and 59 characters).

## Verification of the group (2026-10-08)

Run on the final tree (HEAD e25da2e4, three commits over b73c30ba), all green:
- `bash test/run-all.sh --group quick --changed-from origin/main` with only `SHIPLOOP_PROGRESS=off` set: exit 0 in 529 s, 31 suites
  OK, including shiploop-return-review, shiploop-callback-contract, shiploop-chain-async, shiploop-status-display (the head-window
  test), shiploop-packet-completeness, shiploop-stage-spec, shiploop-keepalive and shiploop-actual-improve-cli.
- Each touched suite in full, hand-run with `SHIPLOOP_PROGRESS=off`: shiploop-return-review 24 tests, shiploop-callback-contract 38,
  shiploop-workspace 77 (above `QUICK_MAX_SECONDS`, so the quick tier does not select it), shiploop-stage-spec 9,
  shiploop-status-display 15, shiploop-packet-completeness 6.
- The three new tests also pass under a CI-like global Git configuration that defines `[filter "lfs"]` clean, smudge, process and
  required (the outer `GIT_CONFIG_GLOBAL` and `HOME` pointed at it): the tests isolate Git configuration themselves.

Lesson from the first quick-tier attempt. It was started with `GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null` exported in the
outer shell, and `shiploop-chain-async` failed three tests with "prepare refuses Git context environment overrides:
GIT_CONFIG_GLOBAL, GIT_CONFIG_NOSYSTEM". That was my environment, not the change: the chain suites refuse an outer override and
isolate Git themselves, so the quick tier is run with the outer Git variables unset (the suites that need isolation set it per
test). The same three tests passed on the rerun. The registered durations in `test/suite_catalog.py` are unchanged: the added
tests do not move any suite near `QUICK_MAX_SECONDS`, and the new timings (return-review 74.5 s alone, callback-contract
72 to 78 s under load) are inside the noise of the registered 85.9 s and 69.1 s.

## Verification after the review fixes (2026-10-08)

Run on the tree of 7196f216 (four commits over 6b20f6a2; the three fix commits touch the same files the suites below cover).
- `bash test/run-all.sh --group quick --changed-from origin/main` with only `SHIPLOOP_PROGRESS=off` set (the outer shell held no
  `GIT_CONFIG_*` variables): `run-all.sh: PASS`, exit 0 in 526 s, 32 suites started, including shiploop-callback-contract,
  shiploop-return-review, shiploop-stage-spec, shiploop-status-display (the head-window test), shiploop-packet-completeness,
  shiploop-chain-async, shiploop-keepalive and shiploop-actual-improve-cli.
- Every touched or reached suite in full, hand-run with `SHIPLOOP_PROGRESS=off` (five at a time, so the times are loaded): callback-contract 39
  tests, return-review 24, stage-spec 9, workspace 77 (147 s; above `QUICK_MAX_SECONDS`, so the quick tier does not select it),
  status-display 15, packet-completeness 6, guidance 57, rehydration 12, packet-bounds 9, navigator-contract 102, delegation 47,
  revise 14, improve-schedule 33, navigator-v4 17, actual-improve-cli 33, full-runtime 2, keepalive 57, quality 18,
  standalone-improve 10, navigator-dry-run 32, test-groups 21: all OK.
- The changed and new tests (the A3 guard test, the A4 test, the route test, the stage-spec table test) also pass under a CI-like
  global Git configuration defining `[filter "lfs"]` clean, smudge, process and required (`HOME` and `GIT_CONFIG_GLOBAL` pointed
  at it); the tests isolate Git configuration themselves.
- `python3 scripts/check-release-boundary.py --base origin/main`: OK.
- Measurements named above (packet growth, opening allowance, terminal-packet path limit, heaviest status end 7971 at the
  62-character path) were taken from copies of the trees under the session scratchpad and a temporary directory, removed
  afterwards; nothing was left running.
