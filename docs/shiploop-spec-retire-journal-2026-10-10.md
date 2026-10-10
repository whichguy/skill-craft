# The spec retire step, the tree-derived feature list and the living spec's pin: journal (2026-10-10, batch 1012 task R)

Plan v5 step R, engine side. Base `b8c1680e`, branch `batch1012r-1bbefb`. The plan is
`docs/shiploop-commit-and-spec-lifecycle-plan-2026-10-10.md` (sections 0a to 0d). The design and its three audits (yagni, tenet, code lenses)
are kept whole in `docs/experiments/commit-spec-design-20261010/retire-design-and-audits.json`; the main session's task text
(`task-r.md`, its DECISIONS) overrides the design where they differ. Packet text, `render()`, `packet_head()`, `DUTIES`, `stage_lines`,
`_render_improve`, `_checked_line/_stage_gates` and `shiploop_prompts.py` belong to the packet owner and were not edited; what they need to
print is under "Lines for the packet owner" below. Evidence is under `docs/experiments/spec-retire-20261010/`.

## Question

At the final handoff, can ShipLoop retire the run's feature spec (owner decision D3) and write a list of the feature folders (D7) without
refusing a handoff, without a state change, without a message that is false when it prints, and without a second parser of any format?

## What was built

| Concern | Where |
|---|---|
| The ID check: every requirement ID the feature spec names against the living spec; one rule for every format; `None` when it cannot be judged | `knowledge_home._unmerged`, `_ids` (also read by `check()`: one reader of the ID syntax) |
| The retire: one commit that deletes the feature spec and rewrites the list; keeps the file, with a reason, in six cases; failure restores | `knowledge_home.retire`, `Retired` |
| The retire subject, its one matcher, its message, the planned record | `retire_subject`, `is_retire_subject`, `_retire_message`, `_planned_record`, `knowledge_subject` (also used by `commit()`) |
| The terminal close order and its messages | `navigator._knowledge_close(terminal=True)`: commit pending knowledge, retire, follow-up return, print |
| The route | `navigator._run_commits_reach_branch`, `workspace.return_kind` |
| The feature list | `knowledge_home.FEATURE_LIST`, `feature_list`, `write_feature_list` (called by `commit()` after its "home changed" test), `feature_list_notice`, `earlier_features` (not called yet) |
| The pin | `knowledge_home.spec_pin` (not called yet; no notice, no hook) |
| The progress row | `knowledge_home.retired_by`; `progress_data.build_snapshot` (feature-spec row, at the handoff and when done only); `progress_render._DOC_STATUS_LABELS` |
| The harness | `counters.history` classifies the retire commit through `knowledge_home.is_retire_subject`; S-11 amended |
| Tests | `test/shiploop-knowledge.test.py` (40 new), `test/shiploop-retire.test.py` (new suite, 17), `shiploop-workspace` (3), `shiploop-progress-data` (3), `-render` (1), `shiploop-e2e-commit-counters` (3), three assertions in `shiploop-full-runtime` |

Exact strings, because the packet owner and a reader of the log meet them:

- Retire subject: `docs(shiploop): retire <folder> spec: its requirement IDs are in the living spec`.
- Retire body: `Requirement IDs checked in docs/shiploop/spec.md: R-1, R-2.` (or `none (the feature spec names none).`), `Removed
  docs/shiploop/features/<folder>/spec.md. Its last version is in this commit's parent: git show <this commit>^:<path>`, and, when found,
  `Planned at <full sha> (the prepare close).` No `Learned-from:` line, no lessons.
- Printed at the terminal close (stdout, prefix `ShipLoop knowledge: `): `committed the removal of the feature spec <abs path> in <sha12> and
  returned it; its last version is in that commit's parent.` after the follow-up returned; `... in <sha12> on the run branch, not yet on your
  branch; ...` when the follow-up returned nothing or failed; `... in <sha12>; ...` for an own checkout; `kept the feature spec <abs path>:
  <reason>.` with the reason one of `the run's commits do not reach your branch (a working-tree or no-change return)`, `R-9, R-12 are not in the
  living spec <abs living spec path>`, `the living spec names no requirement ID, so the IDs cannot be checked`, `it has changes that are not
  committed`; `left <abs list path> as it is (<why>); the list of the feature folders is not written.` The follow-up failure goes to stderr:
  `the follow-up return was not made (<reason>); handoff will ask for it.`
- Progress row: status `retired`, label `Retired`, title `Feature specification (retired)`, summary `Retired at handoff by commit <short sha>: its
  requirement IDs were checked against docs/shiploop/spec.md.`

## Decisions of the task text, and what the audits found

| Decision or finding | Disposition |
|---|---|
| 1. No refusal at handoff for requirement IDs | Done. The gate (`check()`) is unchanged; `retire()` itself keeps the file and the notice names the IDs and both files by absolute path. 0 of 33 saved feature specs are kept for IDs (the survey below). Count the kept notices in the next live pair; if a refusal is wanted it goes at release-verify, never at handoff |
| 2. Close order, messages true when printed, no dead end | Done and tested (`TerminalCloseTests`, five CLI tests). One reading beyond the text, see Deviations 2 |
| 3. Route from `workspace.return_kind` on the newest receipt | Done. The design's claim "a follow-up keeps the first return's kind" is corrected in the docstring and pinned by a test: `_return_kind` keeps only a fast-forward and a working-tree route; after a no-change return the follow-up is worked out again, so the retire, which reads the kind before the follow-up, keeps the file in that case on purpose. The model does not see the same fact: the packet's "Current workspace return" comes from `completed_receipt_snapshot`, which is None while the receipt is stale |
| 4. Own commit, subject says what was checked, planned record in prose, one search | Done; no `Learned-from`, no second citation, one subject searched over the whole log |
| 5. FEATURE_LIST safety and header | Done: written only to an absent, empty or ShipLoop-marked regular file, never through a symlink, one notice otherwise; staged in the retire commit only when ShipLoop owns it and Git would take it (tracked or not ignored); lint-friendly header; the four commands run literally by a test |
| 6. `spec_pin` only | Done; `pin_notice`, `_PIN_LINE` and the prepare-close hook are not built; the harness can read the first line of `plan.md` from a finished repository |
| 7. Progress row at handoff or done only | Done: `retired_by` is called only when the run is at its handoff or done. A done run whose spec is absent shows `Retired` only for ShipLoop's own removal and `Missing` for a model's deletion: the audit's one-label-for-both alternative would call a model deletion a retire, and the one Git call at the handoff and after is what the decision allows |
| 8. Counters through `knowledge_home`, pin test, script class, no `knowledge_facts` fields | Done. The retire commit is a script commit and not a `knowledge` row, so the regrade's "share of knowledge records with lessons" is unchanged by it |
| 9. Fewer CLI tests, mutation record, durations | Five CLI tests in a suite of their own; the rest are unit tests. 60 mutants. Durations in `test/suite_catalog.py` |
| 10. Docs, SPEC amendment | `project-knowledge.md` (the table, the retire paragraph, the replan sentence, the squash sentence, "choose one authoritative home"), `workspace-lifecycle.md`, `SKILL.md`; S-11 in its own commit. `navigator.md` and `state-files.md` do not list the feature spec (grep), so they are not edited |
| 11. LEARNINGS entry | In this commit; `release.py` is not run |
| 12. Fork-owned text | Not edited; see below |
| audit-code: the list staged in the retire commit breaks when `.gitignore` ignores `README.md` | Fixed and tested both ways (untracked and ignored: left out; tracked and ignored: staged) |
| audit-code: `write_feature_list` replaced a hand-written file and wrote through a symlink | Fixed; tested |
| audit-code: `spec.unlink()` / list write could raise an uncaught `OSError` | Caught with `CommitError`; the refusal says `handoff remains pending` |
| audit-code: the header says "then removes that `spec.md`" unconditionally and the header text lint | Header rewritten (conditional, squash limit, lint-friendly) |
| audit-yagni: the widened early return of `check()` runs the credential screen on every clean-home handoff | `check()` is unchanged |
| audit-yagni: the progress branch runs Git on every snapshot from intake | Gated on the handoff or done; a test makes `retired_by` raise at the plan stage |
| audit-tenet: "removed" printed before the follow-up | Reordered; tested with the follow-up recording what existed when it ran |
| audit-tenet: relative paths in a packet line, the earlier-features clause in every packet | Absolute paths in every text below; the clause is for five stages only and has two states |
| audit-tenet: the Run Review exporter lists the removed spec | After the follow-up, `plan_return` holds the removed `spec.md` as a kept `history-only` row (`in_home`), so `delivered.files.knowledge` can list a file that is gone. Noted in the S-11 evidence row; no code change |
| audit: a retried handoff whose `evidence_refs` cite the removed spec is refused with "Write the file or remove the reference" | Not mitigated. 0 of 27 saved handoff results cite a feature spec (the design's count); the next live pair counts it |
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
   (`test_a_follow_up_that_fails_after_only_the_retire_commit_does_not_replace_the_guards_commands`, retry included).
3. **The CLI route tests are in a suite of their own, `test/shiploop-retire.test.py`**, registered in `test/suite_catalog.py` and pinned in
   `test-groups` (78 ShipLoop suites, 120 in all). Decision 9 allowed either; `shiploop-return-review` measured 104.6 s in the audit against the
   120 s quick ceiling and five more CLI tests would have pushed it over. Merging this series with another that adds a suite needs the two pins
   reconciled.
4. **The list is a nested bullet list**, one bullet per folder and one per markdown file, not one long line per folder: a folder with six files was
   a 400-character row. Every header line is at most 80 characters; the rows depend on the folder name.
5. **`earlier_features` and `spec_pin` exist but nothing calls them.** They are pure functions for the packet owner, tested, and cost nothing until
   used. The third `earlier_features` variant (a list not yet written) is cut: it states "Earlier features: ..." whenever a folder other than the
   run's own exists, which can precede the first list write by one stage in a home that predates the list.
6. **The retire commit in a saved run adds the list (A), in a run on this engine it modifies it (M).** The survey below counts both.
7. **Correction of a commit message.** `a79dc1e5` says "14 of 16 fail (the 3 that pass are labelled guards)". The file holds 17 tests: 14 fail
   against the base navigator and 3 pass (`docs/experiments/spec-retire-20261010/fail-first.txt`).

## Method and evidence

Fail-first: each new test was run before its code and failed for the intended reason (`fail-first.txt`: missing attributes for the new names;
`'missing' != 'retired'` for the progress row; the retire commit counted `other` by the counters). `test/shiploop-retire.test.py` against the
navigator of `b8c1680e` with every other file in place: 14 of 17 fail, 3 pass and are labelled guards.

Mutation (`mutants.json`, `mutation-record.jsonl`, `mutate.py`): 60 mutants over the series, 59 red and 1 equivalent (rewriting identical text
to the list). Three first-pass problems, each closed: a wrong pattern (the header's unconditional sentence) re-run red; a survivor that was a test
gap (the index is never reset after a failed commit, because the mock raised before anything was staged: the test now stages first) re-run red;
the fixture line `write_feature_list` in `test/shiploop_knowledge_support.py`, removed, turns the three tests the design named red in
`shiploop-lint`, `shiploop-quality` and `shiploop-test-loop`.

Saved runs (`survey.py`, read-only on `/Users/dadleet/e2e-runs`, retire run on clones; `survey-summary.json`, `survey-rows.json`):

| Measure | Result |
|---|---|
| Work repositories with a features folder; feature specs | 32; 33 (no folder is model-named, so none is skipped) |
| Specs the ID check judged; kept for IDs; not judged (living spec names no ID) | 33; 0; 0 |
| The planned record found by the prepare close's exact subject; equal to the final feature spec; also found by a path-limited log of the folder | 33 of 33; 33 of 33; 8 of 33 |
| Retired on a clone; kept | 33; 0 |
| Retire commits that delete the spec and add the list (the saved homes predate the list); that modify it | 33; 0 |
| Retire commits recognised by the subject matcher, `retired_by` and the `Planned at` line, with the file gone | 33 of 33 |
| A retry that made a second commit | 0 |
| List lines flagged by the credential screen | 0 |

The design's figures (32 specs, 31 repositories, 2 delta-heading specs, 13 ranges) were taken before more saved runs existed; these are today's.
The audits read 31 saved receipts and all were `fast-forward-merge` (not re-read here), so in practice the retire runs; the live pair is what shows a working-tree route.

## Findings

- **Firm.** The prepare close rarely touches the feature folder: the planned record is found by subject, never by path (33 of 33 against 8 of 33).
  Handoff is never refused for IDs, and a presence check cannot prove a merge, so it is not claimed to: the subject says what was checked.
  A message printed before it is true misleads (the first design printed "removed" and then the follow-up failed). An explicitly staged path that
  Git ignores is an error and would have failed every retry. A hand-written file at the list's path was lost silently by the first design.
- **Interim.** The retire's value in a live run is unmeasured: no live run has used it. Count in the first live pair: kept notices by reason,
  retire commits made, follow-up returns that failed after a retire commit, handoffs refused after a retire commit, and a grep of `README.md` and
  `SHIPLOOP.md` for `<folder>/spec.md` links (12 of 33 saved folders have one, the design's count).
- **Not verified here.** Linux git and GNU grep: the header's commands ran on macOS (BSD grep, git 2.54) and use POSIX ERE and `grep -w` only; OrbStack
  is stopped by the owner's standing decision and CI runs the test on Linux. A squash merge or rebase by the user after a fast-forward drops the
  removed file's history; the list's header and `project-knowledge.md` say so.

## Bump

`bump: minor` (`changes/shiploop/spec-retire-and-feature-list.md`). `changes/README.md` defines the kinds by effect on versions only, and ShipLoop
is at 0.59.0 with every behaviour change so far a minor. The retire removes a file that older runs' references link to (12 of 33 saved folders have a
README link to the file, the design's count, not re-measured here), but only the running run's own file, only when its commits reach the user's branch, and Git keeps every version. No state
key, no `STATE_VERSION` bump and no graph change: a run saved before its handoff simply retires at its handoff, and an old run resumes unharmed. A
major bump would say an installed run cannot continue, which is false.

## Lines for the packet owner

For the session that owns the packet text (`exp/step-slice-32c6ee`). Paths are absolute (`REPO` is the execution checkout, `str(repo / ...)`): a relative
path points at the wrong tree in a worktree run. Nothing below is printed by this series.

- **(a) The plan packet, first line, and a request that `plan.md` begin with it.** Only when `knowledge_home.spec_pin(state)` is not None (it is None
  outside a checkout, so the graph dry run runs no process, and while the living spec has no commit):
  `Begin REPO/docs/shiploop/features/<folder>/plan.md with this exact first line, which names the living-spec version this plan implements: Spec: docs/shiploop/spec.md @ <sha12>`
  The value after `Spec: ` is exactly `spec_pin(state)`. Nothing checks it (the notice was cut); the harness reads the first line of `plan.md` from a finished repository.
- **(b) The handoff packet, one line.** `At this handoff ShipLoop checks that every requirement ID in REPO/docs/shiploop/features/<folder>/spec.md is in REPO/docs/shiploop/spec.md and, when this run's commits reach your branch (an in-place run, or a fast-forward return), removes that feature spec in a commit of its own; it stays after a working-tree or no-change return, and the handoff is never refused for it.` Do not add a `Checked by` gate word for it: no refusal exists, so `GATE_WORDS` in `test/shiploop-packet-completeness.test.py` needs no entry. The packet's "Current workspace return" fact is not the route the retire reads (it is None while the receipt is stale), so the packet must not claim they agree.
- **(c) The plan and release-verify packets (the stages that write `docs/shiploop/README.md`).** `In REPO/docs/shiploop/README.md link the feature list, REPO/docs/shiploop/features/README.md, not a feature's spec.md: ShipLoop removes that file at handoff, so a link to it would dangle.`
- **(d) The earlier-features clause, for intake, discovery, research, spec and plan only.** Append `' ' + knowledge_home.earlier_features(state)` to the knowledge-home line (the first element of `stage_lines`). Its two states: `Earlier features: none yet.` and `Earlier features: REPO/docs/shiploop/features/README.md lists every feature folder and the commands that find a requirement ID in them.`

## Not built, with the trigger

| Not built | Trigger to build it |
|---|---|
| A refusal for IDs the living spec lacks | The count of kept notices in the live pair shows runs losing requirements; it goes at release-verify, never at handoff |
| Range expansion (`R-1 .. R-9` read by its ends only) | A run ships a range whose middle IDs are missing from the living spec |
| A check that the living spec says what the feature spec says | Same as the first row; the check is presence only |
| `pin_notice` | A counted run where `plan.md` rarely starts with the pin |
| A tolerance in `_check_submitted_evidence` for a retired spec's path | A counted retried handoff whose result cites the feature spec |
| Skipping the retire commit in `recent_commits` | A run whose intake look-back is filled by retire commits |
| Harness `knowledge_facts` fields for left specs and README links | A consumer for them |

## Commits

See `git log b8c1680e..HEAD` on the branch: the S-11 amendment (`0668a9bc`), the pure functions (`c99b48b1`), the feature list (`950c8f2b`), the retire and
terminal close (`a79dc1e5`), the progress row (`16311454`), the counters and catalog (`8d4dbfba`), then this commit.
