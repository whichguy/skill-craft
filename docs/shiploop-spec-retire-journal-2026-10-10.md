# The spec retire step, the tree-derived feature list and the living spec's pin: journal (2026-10-10, batch 1012 task R)

Plan v5 step R, engine side. Base `b8c1680e`, branch `batch1012r-1bbefb`. The plan is
`docs/shiploop-commit-and-spec-lifecycle-plan-2026-10-10.md` (sections 0a to 0d). The design and its three audits (yagni, tenet, code lenses)
are kept whole in `docs/experiments/commit-spec-design-20261010/retire-design-and-audits.json`; the main session's task text
(`task-r.md`, its DECISIONS) overrides the design where they differ. Packet text, `render()`, `packet_head()`, `DUTIES`, `stage_lines`,
`_render_improve`, `_checked_line/_stage_gates` and `shiploop_prompts.py` belong to the packet owner and were not edited; what they need to
print is under "Lines for the packet owner" below. Evidence is under `docs/experiments/spec-retire-20261010/`. The series was reviewed by two independent readers at head `4bdd5ef9` (18
findings, all minor or nit); the fix round that answers them is the section "Fix round after the reviews", and the text below was edited in place where a fix
changed it, so it describes the final tree.

## Question

At the final handoff, can ShipLoop retire the run's feature spec (owner decision D3) and write a list of the feature folders (D7) without
refusing a handoff, without a state change, without a message that is false when it prints, and without a second parser of any format?

## What was built

| Concern | Where |
|---|---|
| The ID check: every requirement ID the feature spec names against the living spec; one rule for every format; `None` when it cannot be judged | `knowledge_home._missing_ids` (named `_unmerged` before the fix round), `_ids` (also read by `check()`: one reader of the ID syntax) |
| The retire: one commit that deletes the feature spec and rewrites the list; keeps the file, with a reason, in six cases (the route, `KEPT_AFTER_ROUTE`; IDs missing; no ID in the living spec; never committed; uncommitted changes; a symbolic link); a failure is put back by a step that never raises over the real error | `knowledge_home.retire`, `Retired`, `KEPT_AFTER_ROUTE`, `_put_back` |
| The retire subject, its one matcher, its message, the planned record | `retire_subject`, `is_retire_subject`, `_retire_message`, `_planned_record`, `knowledge_subject` (also used by `commit()`) |
| The terminal close order and its messages | `navigator._knowledge_close(terminal=True)`: commit pending knowledge, retire, follow-up return, print |
| The route | `navigator._run_commits_reach_branch`, `workspace.return_kind` |
| The feature list | `knowledge_home.FEATURE_LIST`, `feature_list`, `write_feature_list` (called by `commit()` after its "home changed" test; an `OSError` becomes a `RuntimeError`), `feature_list_notice` (printed once, at the terminal close), `_list_is_shiploops`, `earlier_features` (not called yet) |
| A retried handoff may cite the retired spec | `knowledge_home.is_retired_spec` (shape `docs/shiploop/features/<folder>/spec.md` and `retired_by`), read by `navigator._check_submitted_evidence(result, own_receipt, repo)` |
| The pin | `knowledge_home.spec_pin` (not called yet; no notice, no hook) |
| The progress row | `knowledge_home.retired_by`; `progress_data.build_snapshot` (feature-spec row, at the handoff and when done only); `progress_render._DOC_STATUS_LABELS` |
| The harness | `counters.history` classifies the retire commit through `knowledge_home.is_retire_subject`; S-11 amended |
| Tests | `test/shiploop-knowledge.test.py` (47 new), `test/shiploop-retire.test.py` (new suite, 26), `shiploop-workspace` (4), `shiploop-progress-data` (3), `-render` (1), `shiploop-e2e-commit-counters` (3), three assertions in `shiploop-full-runtime` |

Exact strings, because the packet owner and a reader of the log meet them:

- Retire subject: `docs(shiploop): retire <folder> spec: checked its requirement IDs against the living spec` (it says what the script did, which is true
  when the feature spec names no ID; the first wording claimed the result and was vacuous in that case).
- Retire body: `Requirement IDs checked in docs/shiploop/spec.md: R-1, R-2.` (or `none (the feature spec names none).`), `Removed
  docs/shiploop/features/<folder>/spec.md. Its last version is in this commit's parent: git show <this commit>^:<path>`, and, when found,
  `Planned at <full sha> (the prepare close).` No `Learned-from:` line, no lessons.
- Printed at the terminal close (stdout, prefix `ShipLoop knowledge: `): `committed the removal of the feature spec <abs path> in <sha12> and
  returned it; its last version is in that commit's parent.` after the follow-up returned; `... in <sha12> on the run branch, not yet on your
  branch; ...` when the follow-up returned nothing or failed; `... in <sha12>; ...` for an own checkout; `kept the feature spec <abs path>:
  <reason>.` with the reason one of `the return made before this close did not put the run's commits on your branch (it was a working-tree return, or
  recorded no change)` (`KEPT_AFTER_ROUTE`: it speaks of the earlier return, because the follow-up return that comes after the retire may put the knowledge
  commits on the branch), `R-9, R-12 are not in the living spec <abs living spec path>`, `the living spec names no requirement ID, so the IDs cannot be
  checked`, `it was never committed`, `it has changes that are not committed`, `it is a symbolic link`; `left <abs list path> as it is (<why>); the list
  of the feature folders is not written.` (once, at the terminal close). The follow-up failure goes to stderr: `the follow-up return was not made
  (<reason>); handoff will ask for it.` A refusal of the terminal close reads `ShipLoop knowledge: cannot retire <abs spec path>: <reason on one line>
  (check for a Git index lock or a hook that refuses the commit); handoff remains pending. Fix that, then submit the same handoff result again.`; a list
  that cannot be written reads `cannot write <abs list path>: <reason> (check write permission on that file and the folder it is in)` with the same ending
  (before the terminal close it is a notice ending `; the next accepted stage commits it.`).
- `earlier_features` (for the packet owner), three answers that are true in every state: `Earlier features: none yet.`; `Earlier features: <abs list path>
  lists every feature folder and the commands that find a requirement ID in them.` (only for a regular file that begins with ShipLoop's mark);
  otherwise `Earlier features: the folders in <abs features dir>/ (ShipLoop has not written its list of them, <abs list path>, yet).` or `... (<abs list
  path> is not ShipLoop's list of them).`
- Progress row: status `retired`, label `Retired`, title `Feature specification (retired)`, summary `Retired at handoff by commit <short sha>: its
  requirement IDs were checked against docs/shiploop/spec.md.`

## Decisions of the task text, and what the audits found

| Decision or finding | Disposition |
|---|---|
| 1. No refusal at handoff for requirement IDs | Done. The gate (`check()`) is unchanged; `retire()` itself keeps the file and the notice names the IDs and both files by absolute path. 0 of 33 saved feature specs are kept for IDs (the survey below). Count the kept notices in the next live pair; if a refusal is wanted it goes at release-verify, never at handoff |
| 2. Close order, messages true when printed, no dead end | Done and tested (`TerminalCloseTests` and seven CLI tests). One reading beyond the text, see Deviations 2 |
| 3. Route from `workspace.return_kind` on the newest receipt | Done. The design's claim "a follow-up keeps the first return's kind" is corrected in the docstring and pinned by a test: `_return_kind` keeps only a fast-forward and a working-tree route; after a no-change return the follow-up is worked out again, so the retire, which reads the kind before the follow-up, keeps the file in that case on purpose. The model does not see the same fact: the packet's "Current workspace return" comes from `completed_receipt_snapshot`, which is None while the receipt is stale |
| 4. Own commit, subject says what was checked, planned record in prose, one search | Done; no `Learned-from`, no second citation, one subject searched over the whole log |
| 5. FEATURE_LIST safety and header | Done: written only to an absent, empty or ShipLoop-marked regular file, never through a symlink, one notice otherwise; staged in the retire commit only when ShipLoop owns it and Git would take it (tracked or not ignored); lint-friendly header; the four commands run literally by a test |
| 6. `spec_pin` only | Done; `pin_notice`, `_PIN_LINE` and the prepare-close hook are not built; the harness can read the first line of `plan.md` from a finished repository |
| 7. Progress row at handoff or done only | Done: `retired_by` is called only when the run is at its handoff or done. A done run whose spec is absent shows `Retired` only for ShipLoop's own removal and `Missing` for a model's deletion: the audit's one-label-for-both alternative would call a model deletion a retire, and the one Git call at the handoff and after is what the decision allows |
| 8. Counters through `knowledge_home`, pin test, script class, no `knowledge_facts` fields | Done. The retire commit is a script commit and not a `knowledge` row, so the regrade's "share of knowledge records with lessons" is unchanged by it |
| 9. Fewer CLI tests, mutation record, durations | CLI tests in a suite of their own (seven after the fix round: fast-forward, working-tree, no-change, before the return, guard refused then retried, a cited spec on the retry, source drift); the rest are unit tests. 85 mutants on the final tree (84 red, 1 equivalent). Durations in `test/suite_catalog.py` |
| 10. Docs, SPEC amendment | `project-knowledge.md` (the table, the retire paragraph, the replan sentence, the squash sentence, "choose one authoritative home"), `workspace-lifecycle.md`, `SKILL.md`; S-11 in its own commit. `navigator.md` and `state-files.md` do not list the feature spec (grep), so they are not edited |
| 11. LEARNINGS entry | In this commit; `release.py` is not run |
| 12. Fork-owned text | Not edited; see below |
| audit-code: the list staged in the retire commit breaks when `.gitignore` ignores `README.md` | Fixed and tested both ways (untracked and ignored: left out; tracked and ignored: staged) |
| audit-code: `write_feature_list` replaced a hand-written file and wrote through a symlink | Fixed; tested |
| audit-code: `spec.unlink()` / list write could raise an uncaught `OSError` | Caught with `CommitError`; the refusal says `handoff remains pending`. The fix round closed two more escapes of the same kind: the list write in `commit()`, and the restore inside the failure handler |
| audit-code: the header says "then removes that `spec.md`" unconditionally and the header text lint | Header rewritten (conditional, squash limit, lint-friendly) |
| audit-yagni: the widened early return of `check()` runs the credential screen on every clean-home handoff | `check()` is unchanged |
| audit-yagni: the progress branch runs Git on every snapshot from intake | Gated on the handoff or done; a test makes `retired_by` raise at the plan stage |
| audit-tenet: "removed" printed before the follow-up | Reordered; tested with the follow-up recording what existed when it ran |
| audit-tenet: relative paths in a packet line, the earlier-features clause in every packet | Absolute paths in every text below; the clause is for five stages only and has two states |
| audit-tenet: the Run Review exporter lists the removed spec | After the follow-up, `plan_return` holds the removed `spec.md` as a kept `history-only` row (`in_home`), so `delivered.files.knowledge` can list a file that is gone. Noted in the S-11 evidence row; no code change |
| audit: a retried handoff whose `evidence_refs` cite the removed spec is refused with "Write the file or remove the reference" | First not mitigated (0 of 27 saved handoff results cite a feature spec, the design's count). The review reproduced the refusal and the fix is one clause, so the fix round built it: `is_retired_spec` makes the evidence check count a spec that ShipLoop's retire removed as present |
| audit: a process killed between the removal and its commit | Committed later by the next knowledge commit under the generic subject with no body, so `retired_by` is "" and the progress view says `Missing`. Pinned by a test as a known limit. Safe: the gate-equivalent check already passed |
| audit: the intake look-back (`recent_commits(3)`) reads the 578-byte mechanical retire body | Not mitigated; the lessons-bearing release-verify commit is HEAD in 31 of 31 saved homes (an audit's count), so one commit on top leaves it inside the last three |
| audit: a spec-only feature folder leaves an empty directory after the unlink | The list still prints its row (a link to a folder with no markdown); a fresh clone drops the empty directory. Minor list instability, not mitigated |
| audit: `git log --grep` for the planned record scans the whole history when nothing matches | Unavoidable without an index; bounded only by the repository |

## Deviations from the task text

1. **The SPEC amendment is the first commit, not the sixth step.** `test/shiploop_e2e/SPEC.md` ("Evolving this spec") says to amend it first,
   in its own commit, before the change that needs the clause; the design's C0 says the same. The amendment is docs only, so every later commit is
   still green. The commit says that the counters pattern comes later in the series.
2. **A follow-up failure raises `NavigatorError` only when a knowledge commit was made at this handoff.** The decision says "must not raise when the
   only pending commit is the retire commit" and to keep today's fail-closed rule when a handoff-time knowledge commit exists. On the retry after
   a refused guard the retire commit exists and `retired.commit` is empty, so keying on `retired.commit` would raise on the retry and repeat the
   dead end. The rule is therefore `terminal and committed.commit`. This also changes one old case: a terminal retry with no new commit and a
   failing follow-up used to raise and now falls through to the guard, which refuses a stale return anyway and prints the commands. Tested
   (`test_a_follow_up_that_fails_after_only_the_retire_commit_does_not_replace_the_guards_commands`, retry included). The `_knowledge_close`
   docstring and `workspace-lifecycle.md` said "today's fail-closed rule" for that retry until the fix round; they now say which failures refuse and
   which do not.
3. **The CLI route tests are in a suite of their own, `test/shiploop-retire.test.py`**, registered in `test/suite_catalog.py` and pinned in
   `test-groups` (78 ShipLoop suites, 120 in all). Decision 9 allowed either; `shiploop-return-review` measured 104.6 s in the audit against the
   120 s quick ceiling and five more CLI tests would have pushed it over. **For the merge:** every sibling task that adds a suite conflicts on the
   `test-groups` pins (77 to 78, 119 to 120 here), so the main session reconciles the pins once; and pending `changes/shiploop/` notes must all use
   `bump:` or all use `version:` (`scripts/release.py` `plan()` refuses a mix of the two); they may differ in LEVEL, and the largest bump wins. This series says
   `minor`; the eight-stage inner loop's note says `major`, so shiploop will release as a major. (Corrected 2026-10-10 from "the same bump kind", which
   misread `changes/README.md`: checked against `plan()` and `plan_bundle()`.)
4. **The list is a nested bullet list**, one bullet per folder and one per markdown file, not one long line per folder: a folder with six files was
   a 400-character row. Every header line is at most 80 characters; the rows depend on the folder name.
5. **`earlier_features` and `spec_pin` exist but nothing calls them.** They are pure functions for the packet owner, tested, and cost nothing until
   used. The decision's two answers stay ("none yet" and where to look), and the second is worded to be true in every state: it names the list only
   when ShipLoop's list is there, and otherwise names the folders' directory and says that the list is not written yet, or is not ShipLoop's. (The
   first version promised the list in every state with an earlier folder, which was false for each existing repository at its first intake after the
   upgrade, and for a hand-written file at that path.) The third variant, "holds one folder", is cut.
6. **The retire commit in a saved run adds the list (A), in a run on this engine it modifies it (M).** The survey below counts both.
7. **Correction of a commit message.** `a79dc1e5` says "14 of 16 fail (the 3 that pass are labelled guards)". The file holds 17 tests: 14 fail
   against the base navigator and 3 pass (`docs/experiments/spec-retire-20261010/fail-first.txt`).

## Method and evidence

Fail-first: each new test was run before its code and failed for the intended reason (`fail-first.txt`: missing attributes for the new names;
`'missing' != 'retired'` for the progress row; the retire commit counted `other` by the counters). `test/shiploop-retire.test.py` against the
navigator of `b8c1680e` with every other file in place: 14 of 17 fail, 3 pass and are labelled guards.

Mutation (`mutants.json`, `mutation-record.jsonl`, `mutate.py`, the command in the evidence README): re-run on the final tree of the fix round, 85
mutants, one row each, 85 distinct (suite, mutant) pairs, **84 red and 1 equivalent** (rewriting identical text to the list), 5 rows re-run and
marked `first_run`. The first record counted 63 rows and 61 distinct pairs while this journal said 60 and the README 62 definitions; those figures
are superseded, and the first record is in `19c25538`. Problems closed on the way: a wrong pattern (the header's unconditional sentence) re-run red;
a survivor that was a test gap (the index is never reset after a failed commit: the test now stages first); in the fix round a mutant whose
definition was a syntax error (red for the wrong reason: a red mutant counts only when its first failure names a test), three mutants run in the
wrong suite, a symbolic-link case that linked to a file that was foreign anyway, and a folder-shape test whose path was excluded by its length alone
(both closed in `0ccb9233`). The fixture line `write_feature_list` in `test/shiploop_knowledge_support.py`, removed, turns the three tests the design
named red in `shiploop-lint`, `shiploop-quality` and `shiploop-test-loop`. The reviewer's mutant on `--diff-filter=D` in `retired_by` is left: the
function is called only when the spec is absent, so the newest commit touching the path is a deletion anyway (an equivalent mutant; its row is not in
the record).

Saved runs (`survey.py`, read-only on `/Users/dadleet/e2e-runs`, retire run on clones; `survey-summary.json`, `survey-rows.json`):

| Measure | Result |
|---|---|
| Work repositories with a features folder; feature specs | 32; 33 (no folder is model-named, so none is skipped). The first commit message of the series and the audits say "32 saved feature specs": that was the repository count at the design; the table is the count of specs |
| Specs the ID check judged; kept for IDs; not judged (living spec names no ID) | 33; 0; 0 |
| The planned record found by the prepare close's exact subject; equal to the final feature spec; also found by a path-limited log of the folder | 33 of 33; 33 of 33; 8 of 33 |
| Retired on a clone; kept | 33; 0 |
| Retire commits that delete the spec and add the list (the saved homes predate the list); that modify it | 33; 0 |
| Retire commits recognised by the subject matcher, `retired_by` and the `Planned at` line, with the file gone | 33 of 33 |
| A retry that made a second commit | 0 |
| List lines flagged by the credential screen | 0 |

The design's figures (32 specs, 31 repositories, 2 delta-heading specs, 13 ranges) were taken before more saved runs existed; these are today's.
The audits read 31 saved receipts and all were `fast-forward-merge` (not re-read here), so in practice the retire runs; the live pair is what shows a working-tree route.

## Verification of the final tree

First series: tree `19c25538` (the commands and results are kept below the fix round's). Fix round: tree `6496fe3d`, with `5d6784ab` (a docstring and a paragraph re-wrapped, no behaviour) and then this journal after it. Every command
ran with `SHIPLOOP_PROGRESS=off`; the exit codes are the process's own, captured before anything was piped. The machine was shared with other batch tasks
(load average 6 to 12), so the seconds are not the catalog's.

| Command (fix round) | Exit | Result |
|---|---|---|
| `python3 -B test/run_suites.py --group quick --changed-from b8c1680e --output <scratch>/quick-receipt-fix` | 1 | 45 suites selected and run: 44 passed, 1 failed (`shiploop-status-display`, below). Includes shiploop-retire (58.9 s in the run), -knowledge, -e2e family, -e2e-commit-counters, -progress, -progress-data, -progress-render, -test-loop, -lint, -quality, -navigator-contract/-v4/-dry-run, -packet-bounds/-completeness, -guidance, -keepalive, -cross-run, -run-review, test-groups, release-preflight, mock-replay |
| `python3 test/shiploop-status-display.test.py (this worktree, 94-character path)` | 1 | One dry-run packet check: `8004 not less than 8000`. Identical (`8004`, exit 1) on the pristine base `b8c1680e` extracted with `git archive` into a directory of the same 94-character path length. Packet text is not touched by this series |
| `python3 test/shiploop-retire.test.py` | 0 | 26 tests, 61.3 s (a second run 64.1 s) |
| `python3 test/shiploop-knowledge.test.py` | 0 | 96 tests (rerun after the docstring tidy: 96, exit 0) |
| `python3 test/shiploop-workspace.test.py` | 0 | 81 tests, 195 s. `test_return_projection_stays_current_across_terminal_cold_and_report_packets` passes at this worktree's 94-character path (the first series saw it fail in a 150-character copy path); nothing was rerun for it |
| `python3 test/shiploop-progress-data.test.py / shiploop-progress-render.test.py` | 0 | 11 and 12 tests |
| `python3 test/shiploop-return-review.test.py` | 0 | 24 tests, 113 s |
| `python3 test/shiploop-full-runtime.test.py` | 0 | 2 tests, 90 s |
| `python3 test/shiploop-callback-contract.test.py` | 0 | 42 tests, 93 s |
| `python3 test/shiploop-e2e-commit-counters.test.py` | 0 | 90 tests |
| `python3 test/test-groups.test.py` | 0 | 28 tests (the pins 78 and 120 are unchanged: no suite was added in the fix round) |
| `python3 test/shiploop-navigator-contract.test.py; python3 test/shiploop-e2e.test.py; python3 test/shiploop-rehydration.test.py` | 0 | 103, 404 and 12 tests; they read SPEC.md and the evidence gate, after the S-11 amendment and the evidence change |
| `docs/experiments/spec-retire-20261010/mutate.py, 20 chunks, each in the foreground` | 0 | 85 mutants: 84 red, 1 equivalent survivor; `git status` clean after every chunk (the record's README has the recompute command) |
| `python3 scripts/check-release-boundary.py --base b8c1680e --head HEAD` | 0 | OK |

Rerun policy: nothing was rerun for luck. Both path-length effects are deterministic: `shiploop-status-display` fails identically (8004 against a window of
8000) on the pristine base `b8c1680e` copied to a directory of the same path length (94 characters, `git archive` of the base), so it is not this series; the
`shiploop-workspace` path-length test passes at this worktree's path, as the full suite shows.

First series (tree `19c25538`):
Every command ran with `SHIPLOOP_PROGRESS=off`; the exit codes are the process's own,
captured before anything was piped. The machine was shared with other batch tasks (load average 8 to 17), so the seconds are not the catalog's.

| Command | Exit | Result |
|---|---|---|
| `python3 -B test/run_suites.py --group quick --changed-from b8c1680e --output <scratch>/quick-receipt` | 1 | 45 suites selected and run: 44 passed, 1 failed (`shiploop-status-display`, below). Includes shiploop-retire, -knowledge, -e2e family, -e2e-commit-counters, -progress, -progress-data, -progress-render, -test-loop, -lint, -quality, -navigator-contract/-v4/-dry-run, -packet-bounds/-completeness, -guidance, -keepalive, -cross-run, -run-review, test-groups, release-preflight, mock-replay |
| `python3 test/shiploop-status-display.test.py` | 1 | One dry-run packet check: the status block ends at 8032 against a 8000 window at this worktree's path length. The same failure, with the same number, on the pristine base `b8c1680e` placed at an equal path length (`cmpbase` against `cmphead` copies: 8032 and 8032). Packet text is not touched by this series |
| `python3 test/shiploop-return-review.test.py` (copy of the final tree) | 0 | 24 tests |
| `python3 test/shiploop-full-runtime.test.py` (copy) | 0 | 2 tests, with the new assertions |
| `python3 test/shiploop-callback-contract.test.py` (copy) | 0 | 42 tests |
| `python3 test/shiploop-workspace.test.py` (copy) | 1 | 79 of 80; the one failure, `test_return_projection_stays_current_across_terminal_cold_and_report_packets`, fails in a 150-character copy path (a packet longer than the shell-output limit moves its tail behind the file pointer) and passes in the worktree with the three new tests (`-k`, 5 tests, exit 0) |
| `python3 scripts/check-release-boundary.py --base b8c1680e --head HEAD` | 0 | OK |

Rerun policy: the two failures are deterministic path-length effects and were checked against the base or alone at the worktree path, not rerun for luck.

## Findings

- **Firm.** The prepare close rarely touches the feature folder: the planned record is found by subject, never by path (33 of 33 against 8 of 33).
  Handoff is never refused for IDs, and a presence check cannot prove a merge, so it is not claimed to: the subject says what was checked.
  A message printed before it is true misleads (the first design printed "removed" and then the follow-up failed). An explicitly staged path that
  Git ignores is an error and would have failed every retry. A hand-written file at the list's path was lost silently by the first design.
- **Interim.** The retire's value in a live run is unmeasured: no live run has used it. Count in the first live pair: kept notices by reason,
  retire commits made, follow-up returns that failed after a retire commit, handoffs refused after a retire commit, and a grep of `README.md` and
  `SHIPLOOP.md` for `<folder>/spec.md` links (12 of 33 saved folders have one, the design's count).
- **Not verified here.** Linux git and GNU grep: the header's commands ran on macOS (BSD grep, git 2.54) and use POSIX ERE and `grep -w` only; OrbStack
  is stopped by the owner's standing decision and CI runs the test on Linux. A squash merge of the branch by the user after a fast-forward drops the
  removed file's history (a rebase rewrites the commits and keeps it, which an earlier version of this line had wrong); the list's header,
  `project-knowledge.md` and the SPEC say so, and say that Git keeps the versions committed at a knowledge close, not every version.

## Bump

`bump: minor` (`changes/shiploop/spec-retire-and-feature-list.md`). `changes/README.md` defines the kinds by effect on versions only, and ShipLoop
is at 0.59.0 with every behaviour change so far a minor. The retire removes a file that older runs' references link to (12 of 33 saved folders have a
README link to the file, the design's count, not re-measured here), but only the running run's own file, only when its commits reach the user's branch, and Git keeps the versions committed at a knowledge close (a squash merge of the branch drops them). No state
key, no `STATE_VERSION` bump and no graph change: a run saved before its handoff simply retires at its handoff, and an old run resumes unharmed. A
major bump would say an installed run cannot continue, which is false.

## Lines for the packet owner

For the session that owns the packet text (`exp/step-slice-32c6ee`). Paths are absolute: `REPO` is `Path(str(state["repo"]))`, the execution checkout, and
`<folder>` is the feature folder as `REPO / knowledge_home.feature_dir(state)` (the symbol that yields it: `docs/shiploop/features/<slug>-<suffix>`); a
relative path points at the wrong tree in a worktree run. Nothing below is printed by this series.

- **(a) The plan packet, first line, and a request that `plan.md` begin with it.** Only when `knowledge_home.spec_pin(state)` is not None (it is None
  outside a checkout, so the graph dry run runs no process, and while the living spec has no commit):
  `Begin <folder>/plan.md with this exact first line, which names the living-spec version this plan implements: Spec: docs/shiploop/spec.md @ <sha12>`
  with `<folder>` = `str(REPO / knowledge_home.feature_dir(state))`. The value after `Spec: ` is exactly `spec_pin(state)`. Nothing checks it (the notice was
  cut); the harness reads the first line of `plan.md` from a finished repository.
- **(b) The handoff packet, one line.** `At this handoff ShipLoop checks that every requirement ID in <folder>/spec.md is in REPO/docs/shiploop/spec.md and, when this run's commits reach your branch (an in-place run, or a fast-forward return), removes that feature spec in a commit of its own; it stays after a working-tree return or a return that recorded no change, and the handoff is never refused for the IDs or the route. A removal that cannot be written or committed does leave the handoff pending, with the file's absolute path and the next step in the refusal.` (`<folder>` = `str(REPO / knowledge_home.feature_dir(state))`; the spec's path is that plus `/spec.md`.) Do not add a `Checked by` gate word for the IDs or the route: no refusal exists for them, so `GATE_WORDS` in `test/shiploop-packet-completeness.test.py` needs no entry. The packet's "Current workspace return" fact is not the route the retire reads (it is None while the receipt is stale), so the packet must not claim they agree.
- **(c) The stages that write `docs/shiploop/README.md`: intake, plan and release-verify** (derived: `[stage for stage, names in knowledge_home.STAGE_FILES.items() if "README.md" in names]`; `prepare` and `release-verify` are the closes that require it, and only release-verify also writes it). `In REPO/docs/shiploop/README.md link the feature list, REPO/docs/shiploop/features/README.md (str(REPO / knowledge_home.FEATURE_LIST)), not a feature's spec.md: ShipLoop removes that file at handoff, so a link to it would dangle.` At intake the model links earlier runs' folders; on a home written by the new engine those have no `spec.md`.
- **(d) The earlier-features clause, for intake, discovery, research, spec and plan only.** Append `' ' + knowledge_home.earlier_features(state)` to the knowledge-home line, which is `knowledge_home.stage_lines(state, stage)[1]` (index 0 is the empty string; the line begins `Repository knowledge home (committed, inherited by later runs): `). Its answers are listed under "Exact strings": none yet; the list's absolute path (only when ShipLoop's list is there); or the folders' absolute directory with the list's state.

## Fix round after the reviews (2026-10-10)

Two independent reviewers (lenses code and tenet) read head `4bdd5ef9` and sent 18 findings, all minor or nit (`r-findings.json` in the main session's
scratchpad; each finding reproduced by a script of the reviewer's). Every fix was written test first (red, then green; `fail-first.txt` items 8 to 14),
and the mutants were re-run on the final tree. Commits: `8f7fb62e`, `50121dc9`, `95e5a101`, `adf7ffc1`, `ed6d53e9`, `6e834e4b`, `ca9518b2`, `569cea71`, `ffcffaf0`,
`0ccb9233`, `6a80c112`, `6496fe3d`, `5d6784ab`, then this journal.

| # | Finding | Disposition |
|---|---|---|
| 1 | The kept notice after a no-change return says the commits do not reach the branch, false when it prints (the follow-up return recomputes the kind and returns them) | Fixed: `KEPT_AFTER_ROUTE` speaks of the return made before the close; the decision to keep stays conservative; new CLI test for the no-change route; project-knowledge, workspace-lifecycle, the change note and SPEC say the same (`8f7fb62e`, `6e834e4b`) |
| 2 | An unwritable list file escapes `commit()` and the retire's restore as a raw `PermissionError` | Fixed: `commit()` wraps the list write, `_put_back` never raises over the real error; line 1 of every failure starts with the absolute path and names the next step; the terminal refusal ends "Fix that, then submit the same handoff result again." (`50121dc9`) |
| 3 | `earlier_features` promises the list in states where it does not exist or is not ShipLoop's | Fixed: the two states of the decision stay; the second is true in every state (`95e5a101`) |
| 4 | The "left <list> as it is" notice prints at every knowledge commit | Fixed: once, at the terminal close, with no marker and no state key (`adf7ffc1`) |
| 5 | Claims that say more than the code: "Git keeps every version"; the subject "its requirement IDs are in the living spec" for a spec naming none; "never committed" reported as uncommitted changes; the journal's "or rebase"; the name `_unmerged` | Fixed: the header, the module docstring, the SPEC (own commit, `No-Change-Note`), this journal and the docs say "committed at a knowledge close"; the subject says what was done; `it was never committed` is its own reason; `_missing_ids` (`ed6d53e9`, `6e834e4b`) |
| 6 | A retried handoff whose result cites the retired spec is refused | Fixed: `is_retired_spec`; the "not mitigated" is removed (`ca9518b2`) |
| 7a | Nothing pins `return_kind`'s `status == "returned"` guard | Fixed: a test (passes on the code, red with the guard dropped; also pins the unknown-route guard) (`569cea71`) |
| 7b | The rollback for a list that did not exist is untested | Fixed: a test, plus its mutant (`50121dc9`) |
| 7c | A symbolic-link feature spec is re-created as a regular file by the rollback | Fixed instead of documented: a link is kept ("it is a symbolic link"), because a link's history holds the target path, not the text the message promises (`50121dc9`) |
| 7d | The mutation counts disagree (journal 60/59/1, evidence 63 rows / 61 distinct, README 62/60) | Fixed: the record re-run on the final tree, one consistent count (85 / 84 red / 1 equivalent), the README holds the command that recomputes it (`6a80c112`) |
| 8 | "Lines for the packet owner" not exact | Fixed: symbols named (`stage_lines(state, stage)[1]`, `feature_dir(state)`), (c) derived from `STAGE_FILES` (intake, plan, release-verify), (b) reworded to "never refused for the IDs or the route" |
| 9 | The module docstring and workspace-lifecycle.md still call the terminal retry "today's fail-closed rule"; the suite count and durations; every sibling task that adds a suite conflicts on the pins and all pending notes must have the same bump | Docs fixed (`ffcffaf0`); the duration of the suite is recorded in the catalog (`6496fe3d`; the registering commit `a79dc1e5` is history and was not rewritten); the pins and the bump kind are under Deviation 3 |
| 10 | `--diff-filter=D` in `retired_by` is redundant (a surviving mutant) | Left, an equivalent mutant: the function runs only when the spec is absent |
| 11 | On a refused handoff the follow-up note is stderr line 1 and the guard's refusal follows | Deferred (see "Not built"): the note is true, and moving it is an ordering decision outside this task |

Findings: **firm.** A sentence that is true in the common case and false in a rare one is found by running the route, not by reading the code: the no-change
probe printed the false line, the read-only list probe printed a traceback, and the symlink probe left a type change. A mutant is evidence only when its first
failure names a test, and a test that exercises a guard must fail when the guard is dropped (two tests here passed only because the other branch masked them, and
a path-shape test passed only because the length check excluded its path). **Interim.** None of the fixes has been seen in a live run.

## Not built, with the trigger

| Not built | Trigger to build it |
|---|---|
| A refusal for IDs the living spec lacks | The count of kept notices in the live pair shows runs losing requirements; it goes at release-verify, never at handoff |
| Range expansion (`R-1 .. R-9` read by its ends only) | A run ships a range whose middle IDs are missing from the living spec |
| A check that the living spec says what the feature spec says | Same as the first row; the check is presence only |
| `pin_notice` | A counted run where `plan.md` rarely starts with the pin |
| The stderr order of the follow-up note: on a refused handoff the note `the follow-up return was not made (...); handoff will ask for it.` is stderr line 1 and the guard's own refusal with its commands follows | A model that reads only the first stderr line fails to find the guard's commands. The note is true and says the handoff will ask; moving it after the guard, or onto stdout, is a packet and ordering decision for the packet owner |
| Skipping the retire commit in `recent_commits` | A run whose intake look-back is filled by retire commits |
| Harness `knowledge_facts` fields for left specs and README links | A consumer for them |

## Commits

See `git log b8c1680e..HEAD` on the branch: the S-11 amendment (`0668a9bc`), the pure functions (`c99b48b1`), the feature list (`950c8f2b`), the retire and
terminal close (`a79dc1e5`), the progress row (`16311454`), the counters and catalog (`8d4dbfba`), the change note, references, journal, survey and LEARNINGS entry
(`19c25538`), the docstring fix and verification table (`4bdd5ef9`); then the fix round listed in its section, ending with this journal.
