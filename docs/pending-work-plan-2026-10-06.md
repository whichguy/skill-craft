# Pending work and issue plan, 2026-10-06

Status: **interim**. The plan below is the output of a read-only workflow (seven classifiers of branches, worktrees and the canonical
dirty tree, five issue planners, one synthesis, three adversarial reviews with different lenses and one revision; one planner's output
failed to parse, so the housekeeping section rests on the classifiers and the reviewers' own re-checks). It was written at origin/main
85d8358b. Nothing in it has been executed except where the addendum says so. Evidence: `docs/experiments/pending-work-plan-20261006/`
(the reviewers' findings, the six decisions and the twelve merge steps as the workflow returned them).

## Addendum A: what happened after the plan was written (same day)

1. **The E2E run the plan calls "purpose unknown" was this session's.** `/Users/dadleet/e2e-runs/20261006/v1220-battleship-sonnet`
   (case `battleship`, the Node.js web-service case, Claude Sonnet 5.5, `--source checkout`, ShipLoop 0.54.0) was started on the owner's
   request. Result: invoked, plugin, process, shiploop, committed and all four product checks pass; 1059.8 s, $6.5405, 238 turns
   counted from events (134 reported by the host), 18 commits, 18 `node --test` tests. Planning, intake to the first test-spec accept,
   took about 7 minutes with all five planning Improve children run (stage mode, the default), against the 30-minute ceiling. The run
   left one baseline row in worktree `plrev-d354b1`; the plan's section 2d item 2 applies to it.
2. **Finding (engine, not yet fixed): `node --test` is uncounted.** `skills/shiploop/scripts/shiploop_test_counts.py` parses jest,
   vitest, pytest, unittest, mocha, cargo, go and dotnet, not node:test. In the run, work item W1's `test-refine` verification
   (`run/tests/nav-4964e120cef043bda1bce0dcb834ddc4-verify1.md` in the run directory) recorded the regression command `node --test`
   as `uncounted` (counts null, minimum 12) although it printed `ℹ tests 13`, `ℹ pass 13`, `ℹ fail 0`, so the verification failed
   (script verifications 14 of 15 passed) and the step plan was revised after implementation; the second pass through step-plan,
   test-spec and the build stages cost about two minutes. The 1.22.0 test-author probe refuses an uncounted run too, so a node:test
   project whose focused command lists no test IDs would be refused there as well. Smallest fix: a `_node_test` reader for the spec
   reporter's `ℹ` summary and TAP's `# pass`/`# fail`, with a fail-first test on this captured output; `skills/shiploop` patch note.
   Per the batch rule it waits for the batch of runs to end and rides the next release (Wave 1).
3. **Finding (audit apparatus, fixed locally): the `shiploop-e2e-audit` freshness gate could never pass.** `freshness.py` still looked
   for `plugins/shiploop` and `plugins/improve` and a catalog row per skill; since the one-plugin layout (7370ff6b) the package is
   `plugins/skill-craft/skills/<leaf>`, so every live audit case, including the Google Apps Script Battleship create case
   (`battleship-create`), was refused with `required-package-tree-is-missing`. The hermetic tests used the old layout and stayed green.
   Fix `c27081e5` on branch `freshfix-4abb58`: 19 tests (all 19 failed first), real `run.py check` now `ready: true`. Pending note
   `changes/shiploop-e2e-audit/freshness-one-plugin-layout.md` (patch).
4. **The Google Apps Script one-shot case is the audit harness's `battleship-create`** (the main harness has no GAS case; its `battleship`
   is Node). It drives the Grok CLI with the literal `/shiploop Create a Google Apps Script web app for Battleship...`, needs the
   configured `mcp-gas-deploy` MCP (present in Grok's profile) and a real deployment for a full verdict, and has a 7200 s per-case
   allowance, shorter than the 73 minutes of planning plus build a Grok medium run took on the Node case; a Desktop background task
   is also killed at about 120 minutes. The owner authorized the deployment and the spend; the launch waits for the owner to see this.
5. **Corrections to the plan's own text:** the pending release notes are now five once `freshness-one-plugin-layout.md` is pushed (four
   `shiploop-run-review`, one `shiploop-e2e-audit`); `plrev-d354b1` is the harness checkout of the v1220 run and must stay until its
   baseline row is committed.

---

## The plan (final, after review; origin/main 85d8358b when last read, re-read before each step)

## 0. Corrections to the brief (verified)

- **origin/main is 85d8358b, not 3b246328.** `git ls-remote origin refs/heads/main` equals the local ref. The fork pushed R17/R18 (f31095ce..219c1de6, 7 commits), then 25d1d93d and 81e0502f, then the Specify amendment (d48a0630, 4b4c2561, merge 85d8358b). `rr17-a0486a` and `p1amend-565711` are both at 85d8358b. The fork's "land rr17" handoff is done; what remains for it is a release of its notes, a page republish and worktree cleanup.
- **CI is green** on 45f163d0, 3b246328, 219c1de6, 81e0502f and 85d8358b (`gh run list`). Nothing below waits on CI.
- **The live E2E run has ended.** `/Users/dadleet/e2e-runs/20261006/v1220-battleship-sonnet/result.json`: pass true, process exited returncode 0, 1059.8 s, 0 resumes, source checkout, plugin 1.22.0, shiploop 0.54.0, local_head 81e0502f. No `shiploop_e2e/run.py` process remains. It was started from this session's process tree (parent chain ends at pid 7084); its purpose is unknown to me. Because it used the default baseline, `plrev-d354b1` is now dirty: one new row in `test/shiploop_e2e/baselines.jsonl` (battleship, claude-sonnet-5-5, 2026-10-06T08:23:04). So: no hold on the release or host refresh any more; `plrev-d354b1` must not be removed with `--force` until that row is disposed of (section 2d).
- The housekeeping planner returned nothing; sections 1-2 rest on seven classifiers, two review passes and my own re-checks above.

## 1. State of main and the marketplace

- **Released:** 1.22.0 = 45f163d0 (skill-craft 1.22.0, shiploop 0.54.0, shiploop-e2e-audit 0.7.0); `catalog/skill-craft-plugin.json` = 1.22.0; it has `--planning-review stage|none` (default stage, constant `DEFAULT_PLANNING_REVIEW` in `skills/shiploop/scripts/shiploop_stage_spec.py`) and the test-author probe e11b86ef. shiploop-run-review is 0.1.1.
- **Hosts (read from disk):** Claude `installed_plugins.json` 1.22.0 at 45f163d0; Codex cache `whichguy/skill-craft/1.22.0` (a single version dir: Codex deletes old files, Claude keeps 34); Grok `installed-plugins/skill-craft-b923f37c` 1.22.0. **Cursor: a local copy `~/.cursor/plugins/local/skill-craft`, version 1.21.0 (`.marketplace-origin`, shiploop 0.53.0); it needs a manual refresh after the release.** **OpenCode: `~/.config/opencode/skills/*` are symlinks into `/Users/dadleet/src/skill-craft/skills/` (the stale canonical tree) and move only with the canonical fast-forward (W0-4).**
- **Pending on main, unreleased:** four patch notes, all `changes/shiploop-run-review/`: `plan-and-packets-export.md`, `plan-panel-and-packet-box.md`, `planning-review-option.md`, `phase-1-planning-review-modes.md`. Skill source touched since 1.22.0 is only `skills/shiploop-run-review` (5 files); `skills/shiploop` is untouched (`git diff --stat 45f163d0 origin/main -- skills agents catalog`). A reviewer's `release.py --dry-run` on a copy of 85d8358b printed shiploop-run-review 0.1.1 to 0.1.2 and skill-craft 1.22.0 to 1.22.1; the real dry run in W0-3 decides.
- **Why the release is on the critical path:** `version_gate` in `test/shiploop_e2e/run.py` refuses `--source marketplace` while origin/main has unreleased notes ("origin/main has unreleased changes"); a `--source checkout` run builds its own plugin and does not gate. PT-2 uses the marketplace source, so it waits for this release.
- **Canonical checkout** `/Users/dadleet/src/skill-craft`: HEAD 1ff8c841, 215 behind origin/main, 12 dirty paths (10 modified, 2 untracked), stash empty; every dirty file is byte-identical to a blob in main's history (2a). Two Claude sessions have a cwd there (pid 7013 unidentified, pid 7084 this session).
- **1.22.0 flake:** one `shiploop-progress` flake (`test_duplicate_start_and_cooperative_stop_then_restart`), rerun green. The race path is CI-1.

## 2. Pending work: merge decisions

### 2a. Disposition table

| Item | Disposition | Reason | Route |
|---|---|---|---|
| Canonical dirty tree, 12 paths | **preserve-then-drop** | Blobs equal 0d8d32f9 (test_loop, SKILL.md, navigator.md, test-loop test, could-not-run note), 3c604304 (run.py, metrics.py, progress.py, e2e test, LEARNINGS.md), 67db96c6 (plan rev 6, byte-identical to main), e469f2a4 (comparison draft); main superseded each; the untracked note was consumed by 7aff70aa. `merge --ff-only` refuses over 11 of the 12 and `release.py` refuses a dirty checkout. | W0-4: local preservation branch, then ff. Port nothing. |
| rr17-a0486a, p1amend-565711 | **landed** | Both at 85d8358b. | Fork removes worktrees, `branch -d`. |
| rr8-af090e, rrx-b71bca, rr-e0fcf3 (rr-move-e0fcf3), rr16-a04384 | **delete** (fork acks) | Ancestors of main, clean. | `worktree remove`, `branch -d`. |
| rr14-98a6ad, rr9-e0c0c4, rrt-466f9b, rrh-3d4174, **rrr-edc892**, worktree-agent-af41c2912efab94c7 | **delete** (fork acks; rrr is rr-prefixed, so fork-owned) | All nine "incorporated" branches in this and the next row are NOT ancestors of origin/main (checked: 9 of 9); each commit has a main counterpart with the same changed lines, released by 1.21.x. | Tag first (W0-2), then `worktree remove`, `branch -D`. |
| a1a3-integ-7f216e, nextrel-evalskills-0001ba, worktree-agent-a05edeeaa883c2c09 | **delete** (engine side; owner ack in batch) | a1a3-integ merge-tree equals main's tree; nextrel = evalskills Step A (1.21.1); a05e = backchain-check (1.19.0). | Tag first, then remove, `branch -D`. |
| 12 clean merged worktrees: evalskills-52b2ee, orchestrator-validation-ebde33, chainB-845fe5, chainCD-f91b0e, chainA-bc6944, chainE-61d366, pick-ce1e7d, rel-51f07e, fastplan-1f1dd3, rel2-aa2e70, jrnl-17620c, cifix-ece1d3 | **delete** | Ancestors, clean, no process cwd (about 495 MiB). | Engine session; tell the fork first; `branch -d`. |
| harness-298850, harness-b6fa4c, metric-fix-10c8b8, review-snap-800a5d, shiploop-audit-refresh (Codex), harness-af8532 | **delete** (fork ack) | Detached at commits on main, clean. harness-af8532 is dirty with one baseline row equal to main's 1c84470a. | `worktree remove`; the dirty one needs `--force` only after its diff is copied (W0-2). |
| a13-33dbfd (dirty: 6 modified + untracked `changes/shiploop/system-test-open-item.md`) | **preserve, then delete** | Draft of c7ee64ba (merged 916850b0); carries an unfilled `__QUICK_EXIT__` placeholder. `--force` is irreversible. | W0-2 preservation (diff plus the untracked file, applied-check), then `--force`. |
| e2e-hosts-b66343 (dirty, 2 stale rows 1.12.2/1.13.0, cost 0 = unmeasured) | **delete, fork decides** | Output dirs gone. | Diff copied (W0-2), fork approves `--force`. |
| next-batch-eb98fc *worktree* (branch f3-budget-all-backchain-stages-f05ed2, dirty +1 Luna 1.16.1 row, turns 0, cost null) | **fork decides** | Regrade with `--resume-run` or discard. **Trap:** a different branch is named `next-batch-eb98fc`; never `worktree remove` that directory for it. | Fork. |
| repo-distill-fe584c worktree (dirty +1 mdkit row) and branch exp/repo-distill-fe584c (48 commits) | **preserve-then-drop; do not merge** | Row is not in the lab's `e2e-baseline-rows.jsonl`; branch has 8 conflicting files, exploratory. Tag `keep/repo-distill-c75d630a` = c75d630a already exists. The lab (`/Users/dadleet/src/repo-distill-lab`, no remote) resolves `SKILL_CRAFT_ROOT` or a sibling skill-craft and exits otherwise, and round-3 grading is pending. | Append the row to the lab's rows file with "turns 0, cost null: unmeasured; cause unknown" and commit in the lab; `git worktree add <path> keep/repo-distill-c75d630a` as the lab's `SKILL_CRAFT_ROOT`; add a lab README line; then remove the old worktree and `branch -D`. Owner approval batch (decision 4). |
| codex/shiploop-finalize, -release, -cleanup | **preserve-then-drop** | One chain; `keep/codex-shiploop-finalize` = bfb2ccaa holds all three tips. Whole-branch merge: 12 conflicts. Contents: lifecycle stack (below), e4dd88d7, and patches already on main. | Remove the release worktree and the three branches after the bundle. |
| codex/shiploop-e2e-evidence (6e22f287) | **archive via tag** | The reconciliation doc says do not merge wholesale; 11 conflicts. `archive/codex-shiploop-e2e-evidence` exists. Battleship checker and fixtures stay as ready material (trigger: a returned broken Battleship passes all four checks). | Remove worktree and branch. |
| codex/shiploop-progress-view, codex/shiploop-companions (Codex worktrees) | **delete** (owner ack) | Merged, clean, about 250 commits behind. The dir `shiploop-finalize` holds branch `codex/shiploop-companions`, not the orphan `codex/shiploop-finalize`. Unknown whether the Codex app has a thread on them. | `worktree remove`, `branch -d`. |
| Lifecycle stack 3533706e, 8d75b3e4, 4244b359 | **defer (owner decides)** | Applies cleanly; fail-first 24 failures and 12 errors on main vs 39/39 with it. But d0b2b0be deferred it, it is a design change with evidence n=2, one case, live qualification unknown, and it changes the S-11 retention rule. 722037f8 is the same idea: take the codex stack, not 722037f8. | If yes: fresh worktree on origin/main, `git cherry-pick 3533706e 8d75b3e4 4244b359` (source `keep/codex-shiploop-finalize`), tests, notes, release, one live follow-on case (credits). |
| e4dd88d7 (resume refuses a different candidate) | **drop** | No observed failure; its payload-digest idea has a named trigger (reconciliation D7/D8). It is current-only by design and fine under one-supported-version; dropped for KISS, not for resume volume. | Material stays on `keep/codex-shiploop-finalize`. |
| bold-albattani-5f4c79 (host write-grant probe) | **keep on tag, do not land** | `keep/bold-albattani-dab387b5`. One conflict (suite counts). It loosens the Ask Agent git-context refusal and fixes only Claude-Bash-sandbox use; no normal E2E host hits it. Classifier said land; I disagree. | If wanted: cherry-pick 8d7efd52, e5352442, dab387b5 (skip merge 8e712b92). |
| chain-split-caa8c4 (test-only, d2c8511a) | **rebase then merge (Wave 2)** | Real gap: `shiploop-chain` (191 s) and `shiploop-chain-lifecycle` (803 s) never run in quick when `shiploop_chain.py` changes. Two conflicts: `test/test-groups.test.py` counts and `test/shiploop-chain.test.py` (helper `assert_context_boundary_preserves_chain_mode` belongs in `_ChainIntegrationCase`). | After CI-5. `No-Change-Note`. |
| feat/shiploop-stage-spec-5d1cfb, feat/shiploop-0.20-140a7b, skills/platform-card-pointer-b6a76b, shiploop-fixes-ac4358, next-batch-eb98fc (branch) | **archive via tag, then delete** | stage-spec and fixes: patch-equivalent on main; 0.20 contradicts the current CI policy; platform-card measured +0.2 and did not ship; next-batch's notes are consumed. **Three of these are checked out:** stage-spec-5d1cfb, platform-card-pointer-b6a76b and the out-of-tree `/Users/dadleet/src/skill-craft-shiploop-audit-fixes-529567` (0.20); all clean. | Tag, remove the three worktrees (including the out-of-tree path), then `branch -D`. |
| Step B "v4 design review checks" (abb0d238, 72732860; already in main's history, text in the retired `shiploop_navigator_v3_prompts.py`) | **port later (Wave 3)** | Round 7: +5.1 points [+3.0, +7.2], Wilcoxon p = 0.0006, measured on an older packet; the plan Improve prompt changed since. Moot if the default flips to none. | Port to `shiploop_prompts.py` next to `PLANNING_REVIEW_FOCUS`, own note, own release, re-run the comparison first (credits). |
| `/Users/dadleet/tmp/shiploop-e2e-verify-kkd4mVW5` (962 MiB) | **keep** | Only record of the three calibration attempts (design obsolete). | Copy the 5 small files (about 60 KB) to `/Users/dadleet/src-archive/2026-10-06/`. |
| `/Users/dadleet/e2e-runs` | **keep** | 12 of 15 run dirs cited by main. The uncited `preflight-codex`, `preflight-grok` are the fork's call (`seat-reservations` is a case name, so unverified). | none |
| plrev-d354b1 | **keep until last** | Dirty with the new baseline row (section 0); remove only after the row is disposed, never `--force`. | Last delete. |

### 2b. Ordered sequence

Every step uses `git -C <repo>` with explicit pathspecs; never `git add -A`; never `cd` to run git. `C=/Users/dadleet/src/skill-craft`. Each guard runs immediately before its step; the release and the canonical ff need the owner present because the permission classifier may prompt for `release.py` and `release-push.py` (a reviewer's `release.py --dry-run` was denied).

**W0-1 Guards (read-only).**
```
git -C $C ls-remote origin refs/heads/main ; git -C $C rev-parse origin/main        # equal; record
git -C $C status --short --untracked-files=all                                       # canonical: exactly the 12 paths
pgrep -fl 'shiploop_e2e/run.py'                                                      # active E2E runs
find ~/.codex/sessions -name '*.jsonl' -mmin -90                                     # recent Codex rollouts; ask the owner about Codex app threads
```
`ps | grep 'codex exec'` is the wrong instrument (Codex app helpers match permanently); use the two lines above and re-run them immediately before the release push and before the Codex host upgrade (pass the check as a `--check` argv to `release-push.py`).

**W0-2 Preservation (non-destructive; precedes every delete, not necessarily the release).**
```
# tags for every branch whose tip is not an ancestor of origin/main (14 branches)
for p in 9acf6ba7:shiploop-stage-spec-5d1cfb 8e842a0b:shiploop-0.20-140a7b 3e14e613:platform-card-pointer-b6a76b 2e595588:shiploop-fixes-ac4358 7c2a27be:next-batch-eb98fc; do git -C $C tag "archive/${p#*:}-20261006" "${p%%:*}"; done
for b in rr14-98a6ad rr9-e0c0c4 rrt-466f9b rrh-3d4174 rrr-edc892 a1a3-integ-7f216e nextrel-evalskills-0001ba worktree-agent-af41c2912efab94c7 worktree-agent-a05edeeaa883c2c09; do git -C $C tag "archive/$b-20261006" "$b"; done
# the fork journal's eight pre-rebase SHAs (held only by worktree reflogs today)
for s in d897fe06 721c8212 c439244f 442bd572 cd631edb b2e879a6 defaeb12 4b09f959; do git -C $C tag "archive/fork-prerebase-$s" $s; done
mkdir -p /Users/dadleet/src-archive/2026-10-06
git -C $C for-each-ref --format='%(refname:short) %(objectname)' refs/tags/archive refs/tags/keep > /Users/dadleet/src-archive/2026-10-06/tips.txt
git -C $C bundle create /Users/dadleet/src-archive/2026-10-06/skill-craft-tags-20261006.bundle $(git -C $C tag -l 'archive/*' 'keep/*')
git -C $C bundle verify /Users/dadleet/src-archive/2026-10-06/skill-craft-tags-20261006.bundle   # read the exit code on its own, no pipe
```
The reflog is not a backup: `branch -D` and `worktree remove` delete it. Every later `branch -D` is gated on `git -C $C rev-parse --verify archive/<name>-20261006` (or the existing `keep/*` tag) succeeding. Then the file-level preservation, each verified non-empty before the matching `--force`:
- a13-33dbfd: `git -C <a13> diff HEAD --binary > .../a13_dirty.patch` plus `cp` of the untracked `changes/shiploop/system-test-open-item.md`; verify with `git apply --check` in a throwaway worktree at a13's HEAD, then remove it.
- Baseline-row diffs from plrev-d354b1, harness-af8532, e2e-hosts-b66343 and next-batch-eb98fc worktrees: `git -C <wt> diff -- test/shiploop_e2e/baselines.jsonl > .../<name>.baseline.diff`.
- The 5 calibration files from `/Users/dadleet/tmp/shiploop-e2e-verify-kkd4mVW5`: `cp` to the archive dir.
- The mdkit row to the lab (decision 4 batch).

**W0-3 Release the pending notes (the user asked for merge, push and marketplace update; owner present).** Preconditions: W0-1 shows no live E2E run and no recent Codex rollout; the fork confirms its four notes are final and asks for a **push freeze to origin/main** from the `git fetch` below until `release-push.py` prints `pushed` (the push aborts if remote main moves: `remote branch moved or differs from --expected-base`). Irreversible once pushed: roll forward, never revert a release commit.
```
RAND=$(openssl rand -hex 3); R=$C/.claude/worktrees/rel3-$RAND
git -C $C fetch origin
git -C $C worktree add "$R" -b "rel/batch-$RAND" origin/main
python3 "$R/scripts/release.py" --dry-run     # expect run-review 0.1.1 to 0.1.2, skill-craft 1.22.0 to 1.22.1; read for surprises
python3 "$R/scripts/release.py"               # resolves its repo from its own path (ROOT = parents[1]); makes its own commit; no cwd needed
git -C $R rev-parse HEAD 'HEAD^{tree}' ; git -C $R status --short --untracked-files=all   # record; must be empty
```
Qualify on those exact bytes (read each exit code on its own): `python3 scripts/check-release-boundary.py --base origin/main --head HEAD`, `bash scripts/sync-plugin-views.sh --check`, `python3 scripts/check-marketplace-packages.py`, `bash test/run-all.sh --group quick --changed-from origin/main`. Then re-run `git -C $R status --short --untracked-files=all` (an untracked test artifact blocks the push) and `git -C $C ls-remote origin refs/heads/main`, and publish:
```
python3 $R/scripts/release-push.py --repo $R --expected-head <commit> --expected-tree <tree> --expected-base <origin/main sha> \
  --check '["bash","scripts/sync-plugin-views.sh","--check"]' --check '["python3","scripts/check-marketplace-packages.py"]'
```
**Recovery if it aborts because main moved:** remove `$R` and `rel/batch-$RAND`, recreate from the new origin/main and redo release.py and the qualification; never rebase or reuse the release commit. CI runs the full tier on the release commit (about 19 min); do not wait on it.

**W0-4 Refresh canonical after the release** (checklist and AGENTS.md; this is also what OpenCode reads). Only when the owner confirms pid 7013 is idle. Preservation branch first, because the ff would overwrite 11 of 12 dirty paths and reset/clean/autostash are forbidden.
```
F=(docs/shiploop-e2e-plan-2026-09-27.md skills/shiploop/SKILL.md skills/shiploop/references/navigator.md skills/shiploop/scripts/shiploop_test_loop.py test/shiploop-e2e.test.py test/shiploop-test-loop.test.py test/shiploop_e2e/LEARNINGS.md test/shiploop_e2e/metrics.py test/shiploop_e2e/progress.py test/shiploop_e2e/run.py changes/shiploop/test-run-could-not-run.md docs/shiploop-graph-engineering-comparison-2026-10-04.md)
git -C $C rev-parse HEAD ; git -C $C stash list                                       # 1ff8c841..., empty
for f in "${F[@]}"; do git -C $C log origin/main --find-object=$(git -C $C hash-object "$C/$f") --format=%h -1 -- "$f"; done   # every line prints a sha, else stop
git -C $C switch -c preserve/canonical-dirty-20261006-$(openssl rand -hex 3)
git -C $C add -- "${F[@]}" ; git -C $C diff --cached --name-only | wc -l              # 12
git -C $C commit -F <message>      # "not for merge; never push"; trailers: No-Change-Note: preservation snapshot of already-landed work; Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
git -C $C switch main ; git -C $C status --short                                      # empty
git -C $C fetch origin ; git -C $C merge --ff-only origin/main
git -C $C rev-parse HEAD origin/main ; ls $C/changes                                  # equal; README.md only
```
The preservation branch stays local and is never pushed (its `skills/shiploop` text would re-release 0.52.0 prose if ever merged); delete it once the owner agrees.

**W0-5 Refresh the hosts.**
- Claude: `claude plugin marketplace update whichguy`; Codex: `codex plugin marketplace upgrade whichguy` (re-run the W0-1 Codex-activity check first: Codex deletes the old version's files, Claude keeps them); Grok: `grok plugin marketplace update`; **Cursor: re-copy `plugins/skill-craft` from the released commit over `~/.cursor/plugins/local/skill-craft` (or use the import UI) per `docs/distribution.md`**.
- Verify by disk read, not by command exit: `installed_plugins.json` (Claude), the Codex cache dir name, the Grok registry/`plugin.json`, `.marketplace-origin` (Cursor) all show 1.22.1 and the release commit. If a host's version does not move, `distribution.md` names no further command; record it as unknown and ask the owner. OpenCode follows W0-4.
- Run Review page republish: the change notes (`planning-review-option.md`, `plan-panel-and-packet-box.md`) say the page needs one republish; the fork republishes after the owner reviews the draft.

**W0-6 Housekeeping journal and cleanup (separate optional step, after W0-5, owner go per batch in decision 4).** First one docs-only commit in a fresh worktree on origin/main: `docs/repo-housekeeping-journal-2026-10.md` with every deleted tip, every tag name and sha, each tag's trigger and the bundle path (explicit pathspec, push; docs need no note); push before any PT-2 launch so the launch checkout has no local-only commits. Then, with canonical at origin/main (so `branch -d` works), in this order: the fork's own list (fork runs it), the engine-line list (this session), the three out-of-tree and tagged worktrees, Codex worktrees after owner ack, the release worktree `$R` and `rel/batch-$RAND` (`branch -d`, ancestor after the push), `plrev-d354b1` last. Each removal: `git -C $C worktree remove <path>` (no `--force`; stop if it refuses), then `git -C $C branch -d|-D <branch>` (`-D` only with a verified tag). Immediately before: `lsof -d cwd | grep -E '\.claude/worktrees/|skill-craft-shiploop-audit-fixes'`. Finish with `git -C $C worktree prune; git -C $C worktree list`.

### 2c. Test footprint and notes per push

| Push | Run before | Note or release |
|---|---|---|
| Release commit (W0-3) | the four checks; CI full tier after | produced by `release.py`; consumes the four run-review notes |
| Housekeeping journal | none (docs) | none |
| CI-1 (progress read race) | `python3 test/shiploop-progress.test.py` (17 tests; the new test fails on main first) plus quick tier for the range | `skills/shiploop` source: `No-Change-Note: viewer-only read race; hermetic race reproduction, no live run (viewer-only path)`. Ships with the next release at 0.54.0; marketplace runs before then do not carry it (accepted: viewer-only). |
| CI-2 (docs) | `skill-frontmatter`, `shiploop-guidance`, `test-groups`, `ci-policy` | none |
| CI-3, CI-4, CI-5, chain-split | `test/test-groups.test.py`, `ci-policy`, touched suites in both halves | none (test-only) |
| C2 exporter half, C1, CI-6, PT-5, lifecycle stack, bold-albattani, Step B (skill-source items) | per-skill suites | each needs `changes/<leaf>/<slug>.md` (patch/minor, named in section 3) or a trailer; batch them into one release after PT-2 |

**Landing order:** release (W0-3) first, because the user asked for it and it unblocks PT-2; then the journal; then only test-only/docs commits while PT-2 runs; then CI-1 and every note-carrying item together, then one release.

### 2d. Handoff to the E2E (fork) session (recommendations only; I change none of its branches)

1. Your R17/R18/p1amend commits are on main. Cut or approve the release in W0-3 (this session runs it, the owner present; you asked for a push freeze); republish the live page after the owner's OK. Your journal cites pre-rebase SHAs (d897fe06, 721c8212, c439244f, 442bd572, cd631edb, b2e879a6, defaeb12, 4b09f959): they are now tagged `archive/fork-prerebase-*`; add a mapping in one docs commit (edit, do not delete). This is a follow-up, not a precondition for removing worktrees.
2. **The v1220 battleship run left one new baseline row in `plrev-d354b1` (`test/shiploop_e2e/baselines.jsonl`, claude-sonnet-5-5 on 1.22.0, pass true, 1059.8 s).** It is real evidence. Recommend you land it with your next test commit; I copy its diff to the archive first (W0-2) and remove `plrev-d354b1` only after that.
3. After the release: remove `rr17-a0486a`, `p1amend-565711` and the ack-list worktrees in 2a; regrade or discard the three stale rows (next-batch worktree, e2e-hosts-b66343, harness-af8532); decide the two uncited run dirs.
4. Next harness work, in this order: RC1 (clean stop and export), then RC2/RC3 only if probes repeat. Nothing from the canonical dirty tree or the codex branches needs porting.

## 3. Issue plan

Alternatives are never summed. `[I]` = my inference or planner estimate; dollar figures are estimates from older Grok runs ($0.31-0.34 per Grok minute), Grok balance unknown (memory: credits ran out 2026-10-03).

**Overlaps resolved.** Landing R17/R18: done on main; only release, republish and cleanup remain. Run options for a none cell (`--run-option` prompt sentence, `--start-run`): one item, harness-started `--start-run` preferred, but PT-2 does not wait for it (it uses the zero-code `--prompt` route and an external watcher, labelled as such). Planning window in the export: one item, owned by the exporter (C2); PT-2 uses a throwaway reader in `docs/experiments/` until it lands. Definition clash to fix first: Grok Improve minutes are 42.4 (receipt vs start mtimes, in LEARNINGS and the plan) vs 45.9 (exporter, bind to accept). Stop point: harness-only and conditional; engine stays design-only. Cheaper revise (L17): not built; measure revises from the export first. Retry-class packet heads (L14): done in 1.21.1/1.21.2.

### Wave 0: merges and housekeeping (no credits)

| ID | Item | Who | Effort | Depends | Fail-first test | SPEC / note |
|---|---|---|---|---|---|---|
| W0-1..6 | Section 2b sequence | me (release, canonical, cleanup); fork (its worktrees) | M | owner go for the release | the release gate checks | none |
| CI-2 | Fix two misleading CI instructions: step 3 of `docs/skill-release-checklist.md` still starts with `--changed-from origin/main` (a merge-sized range selects 68-80 suites, about 10 min); `test/README.md` says hubs "select every light ShipLoop suite" (code: the fixed nine in `_HUB_SUITE_IDS`) and omits that skill/readme/changelog/license/plan/review/spec names select nothing | me | S | none | prose; the 14 doc checks stay green | none |

### Wave 1

| ID | Item | Who | Effort | Depends | Fail-first test | SPEC / note | Credits |
|---|---|---|---|---|---|---|---|
| PT-1 | Decision record (prose, no new pin): what the 30-minute ceiling binds and the pre-registered flip rule (decision 1). Written by me in `docs/experiments/shiploop-planning-time-20261005/` (engine side); the fork adds a one-line pointer in `test/shiploop_e2e/LEARNINGS.md` in its own commit (one writer per harness file). | me; fork pointer | S | none | none (a wording pin would add to the design tax the CI audit names; the real test is PT-5's default-parity test if built) | S-10 carve-out 2026-10-05; fork writes any SPEC row | none |
| RC1 | Clean stop and export (harness only): one `stop_reason()` (a `<output>/STOP` file plus SIGTERM/SIGINT setting a flag, never grading in the handler); a stopped host is never relaunched; metrics.json, result.json and the Run Review export are written; `--resume-run X --regrade` for any status; README "18-30 minutes" corrected to the measured 120.3 min (recorded in the ledger account; whether it still holds is unknown) | fork | M | none | pin today's relaunch-after-kill, then: STOP ends the fake host with label `stopped`, exactly one session, records written; SIGTERM does the same; `--regrade` on an active run starts no host and does not read as pass; `--interrupt-at chain-launched` unchanged; no baseline row | harness rules; S-14 | none |
| PT-2 | **M1-lite, Grok medium, n=2**, `--source marketplace`, planning only to the first test-red, `planning_review none`, prompt-started, external watcher on a persistent fact (a done row in state.md history), harness killed before the host. Zero-cost first: `python3 test/shiploop_e2e/run.py --preflight-only --host grok` (also before the second probe). **Bounds (owner approves the cap, not just the estimate):** launched as a Desktop background task from a dedicated worktree pinned at origin/main (not fast-forwarded during the window, no local-only commits); `--timeout 5400` and `--max-resumes 2` (verify in `run.py` whether `--timeout` is per run or per session: unknown); Grok has no spend cap (`--max-budget-usd` is Claude-only) and a killed session reports no cost, so the true spend is unknown. Worst case about $45 per probe, $90 for two [I], including one replayed resume (interrupt runs c1/c2 cost $25.85 vs $8.60-11.20 uninterrupted). The window is computed from timeline/state stamps, so a kill-to-resume gap does not void it. If the 90-minute cap hits before the first test-red, that is a result, not a failure. Read: wide and narrow windows with their clock, stage minutes, Improve children (expect 0), per-stage authoring minutes against 4.0/5.5/6.2/2.7/1.5, document bytes against 19,151/20,880/11,162, model-written script counts, Backchain minutes at plan (baseline about 4.3), compactions, whether the first test-red revises. Stage control only if the none windows are not separable from 72.7. | me | M | PT-1, W0-3; RC1 improves it (watcher touches STOP) | before trusting the reader it must reproduce the 1.21.0 Grok figures (72.7 wide, 42.4 children, 26 passes, 13.3 first-pass); the watcher replayed on the stored timeline must fire on the test-spec accept although baseline was accepted 32 s later; post-run assertions: `planning_review none` in state.md and no Improve child in the window | S-10 carve-out (its Basis is this unmeasured claim), S-11, S-14 | **Owner's go** (decision 3) |

**PT-2 window rule:** from launch until both probes end (including resumes) no release, no commit with a `changes/` note, no commit touching `skills/`, and no fast-forward of the launch worktree; only test-only and docs commits land (the gate also refuses a resume on a red CI or a local HEAD ahead of origin/main). The fork is told before launch.

### Wave 2 (test-only or docs while PT-2 runs; skill-source items after it)

| ID | Item | Who | Effort | Fail-first test | Note |
|---|---|---|---|---|---|
| PT-3 | Quality proxy for unreviewed planning documents, **expressed as a rubric-eval frame and scenario set** (the sanctioned route: arms, one blind evidence-first judge, quality then tokens then time): five items (request-to-criterion-to-test mapping; oracle independence; a real loadable module and a step creating it; platform claims verified; no contradiction), judged blind to mode, plus the free classification of the 26 historical Grok review commits. Runs only if PT-2 meets (a) and (b). Call cap stated in the ask: at most 8 Opus 5.5 medium calls (2 PT-2 sets, the reviewed 1.21.0 set, 2 planted copies, 1 unmodified copy, 2 spare); cost unmeasured | me | M | plant two defects in a copy of the reviewed 1.21.0 set (delete the loadable-module sentence; delete one criterion mapping); the scoring exits non-zero if either is missed or the unmodified copy is flagged | none; **owner's go after PT-2** |
| C2 | Planning block in the Run Review export (merged with `planningWindow`): `{clock, windowMin, improveMin, otherMin, outputTokens, reasoningTokens, compactions, truncatedOutputs, toolSearches}` from `rollouts.py` (dedupe by `response_id`); Claude and Grok give null with a reason, never 0; two clocks side by side | fork | M | exporter on the committed v1210 docs reproduces Luna 375.0/203.4/171.6 and Grok 72.0/45.9/26.1; a synthetic rollout (4 records, one repeated id, 2 truncated outputs, 3 tool searches) yields 3, 2, 3 | `skills/shiploop-run-review` source: patch note; after PT-2 |
| RC5-1 | One sentence in `resume_prompt` ("the packet is complete; do not read the skill card or planning documents first") | fork | S | each host's resume prompt contains the sentence and the exact `next --run-dir` command | none (harness) |
| CI-3 | Print per-suite seconds in `test/run_suites.py` (`OK <id> (12.3s)`, flushed), then refill `_DURATION_SECONDS` in `test/suite_catalog.py` from GitHub seconds (shiploop-e2e 61.0 is wrong; 46 of 108 suites have no entry, 17 of the 69 selected by a merge-sized range, and `_light()` reads a missing entry as 0.0 s: unmeasured is read as zero). No `::warning` feature | me | S-M | after the table refill, a test over suites in quick fails on main because quick-selected suites lack a measured duration | none |
| CI-4 | Add `experiments-shiploop-chain-native-pilot` (72.5 s) to `_HUB_SUITE_IDS` | me | S | new must-select rows in `test_quick_reaches_the_consumers_of_shared_shiploop_sources` fail on main | none |
| CI-5 | Replace the three absolute count pins in `test/test-groups.test.py` (67, 39, 108) with an explicit list of the 8 nested-experiment and apparatus entries | me | M | patch `SUITES` to drop one nested entry and the list assertion fails; adding a top-level entry needs no number bump | none |
| chain-split | Land d2c8511a replayed on current main | me | S-M | class-union guard in `test-groups`; both halves of the three chain suites; a quick run for a `shiploop_chain.py` change selects the fast halves and no slow half | none |
| CI-1 | In `_read_json` (`skills/shiploop/scripts/shiploop_progress.py`) change `st_nlink != 1` to `st_nlink > 1`; hard links stay refused by the `_regular()` lstat check. Fixes a demonstrated race; **whether it caused the 1.22.0 flake is unknown** (scratch trials: 2 of about 1,700 hit it, 0 of 600 with the fix). If the flake recurs with empty CLI stderr, 3b246328's output shows which other path (1.0 s start deadline, observer lock) applies | me | S (about 1 h) | patch `progress.os.open` so `store.atomic_write_text` lands right after the open and assert `_read_json` returns the old record (raises `ValueError` on main); a guard that a 2-link file is still refused; commit probe scripts and output under `docs/experiments/ci-audit-20261005/` | `No-Change-Note` (S-15 admission: hermetic only, no live run because the path is viewer-only); lands after PT-2 |
| RC4-0 | Journal entry plus short `docs/shiploop-stop-point-design-2026-10-05.md`: designed, not built, the four open decisions, evidence path (86ae257f), the trigger; commit cites 86ae257f | me | S | none (docs) | none |

### Wave 3: conditional or owner-driven (build only on the stated trigger)

| ID | Item | Trigger | Who | Effort | Note |
|---|---|---|---|---|---|
| C1 | Replace "read it with a file-reading tool" in `packet_head`, `emit`, the Improve-card sentences and SKILL.md "Follow the current packet" by script-computed read parts plus a `sed -n "A,Bp"` fallback; keep the `Full packet:` line byte-identical (8 suites parse it); put the parts in the packet file, not the head | a host actually fails or truncates the read. Value is small (5.5 of 375.9 min search span; about 1 min of a 30-min window); no S-n anchor today (S-7 anchors a short head); a size-based chunk contradicts the dropped L5 | me | S | `skills/shiploop` patch note; anchor S-7 and write the adversarial evaluation first; live check rides a Codex run, not a dedicated one |
| RC2 + RC3 | `--start-run` / `--run-option` and `--stop-after STAGE` (0.5 s tick, persistent history row, `stop` verdict, no baseline row); SPEC amendment dated first | planning probes become routine after PT-2/PT-3 | fork | M + M | harness |
| RC5-2 | `--resume-run` passes the old session id for Grok and Codex; one Codex hello smoke | a multi-hour Codex run is planned | fork | S + smoke | **owner's go** (Luna credits) |
| Lifecycle stack | cherry-pick plus journal, release, one live follow-on case | owner says yes (decision 5) | me | M + live run | minor note; **owner's go** |
| Step B design-review checks | port to `shiploop_prompts.py`; re-run the round-7 comparison on the current packet first | default stays stage | me | S + rubric-eval round | patch note; **owner's go** (Luna, Opus) |
| CI-6 | Regenerate `skills/rubric-eval/suites/architecture-v4/frames/review-packet.txt`; make `make_packet_frame.py` deterministic (three runs gave three hashes of a random temp path) and pin `planning_review='stage'` (it fails under none) | before the next `--frame review-packet` use, or in the PT-5 commit | me | S | `skills/rubric-eval` patch note |
| bold-albattani | cherry-pick the three commits | a sandboxed chain run is planned | me | S | ask-agent minor + shiploop patch notes |
| Battleship checker, payload digest | copy from the tags | a returned broken Battleship passes all four checks; or a run resumed across a release breaks | fork | S | harness |

### Wave 4: conditional on Waves 1-2

- **PT-5 flip the default to none** (one constant `DEFAULT_PLANNING_REVIEW` in `skills/shiploop/scripts/shiploop_stage_spec.py`; pin stage in 17 schedule-sensitive suites, `make_packet_frame.py` and `references/graph-dry-run-scenario.json` in the same commit; decide whether `--improve-skill` stays required on every start; dated SPEC statement first, written by the fork; default-parity test). Only if the pre-registered rule from decision 1 is met; skip entirely under option A. Fail-first: the 17 suites fail for the right reason when the constant changes. Shiploop minor note; one release.
- **RC4 engine stop point** (state key, `stop-at` verb, held packet; about 280 engine lines, 400 test lines, SPEC S-16): only if RC3's live runs show an overrun of at least one stage, or a killed session cannot be continued by `--resume-run`, or the owner wants a script-owned stop. Then: SPEC S-16 (fork), engine (me, own note), release, harness arming (fork).

### Dropped under KISS or one-supported-version

- Decision-1 options C and D are presented once, as owner options (not also here): the Luna xhigh floor is **unmeasured, estimated at least 115 min [I]** (only the 171.6 min "other" window, which includes the Backchain loops, is measured); no effort below xhigh has ever been run.
- Levers L2, L3, L4, L12 (moot under none; under stage Grok stays at 43.6 min, above 30, and needs an S-10 amendment). L13 as a default, L11 (only 13 of 162 model-written scripts were document checkers, 7.5 min), L17, L5, L6, L7, L8, L10/L18, per-stage effort or model: each has a measured re-open trigger in the planner outputs; PT-2 produces those readings for Grok at no extra credits.
- C5 script-derived Improve opening (depends on an undecided default). CI-7 (release tier 18-19 min to about 10-11 min [I]) and O7-O13: nobody waits on the release tier. Compat shims, aliases and migrations anywhere: none proposed; e4dd88d7 and the two unselected branch-level designs are dropped, not adapted.

## 4. Decisions needed from the owner

Six decisions need an answer; the rest are recorded defaults (below) that proceed unless you object.

1. **What the 30-minute ceiling gates (PT-1).** A) gate E2E planning probes on Grok medium and Sonnet, report Luna xhigh, pass `none` per run, default stays stage (recommended: no engine change). B) A plus flip the default to none (PT-5). C) probe Luna below xhigh (pin exception, cost unknown). D) planning-lite profile. Flip rule to confirm: (a) both Grok none wide windows at most 30 min; (b) no revise at the first test-red and the probe stayed silent; (d) Sonnet hosts accept losing the b1e196d catch for about 2 of 4.7 min. The PT-3 quality finding (c) is **advisory** (a model-judged result does not gate the flip; you read the documents).
2. **Release now.** A) cut one patch release now (recommended; the user asked for it and it unblocks PT-2). B) wait for more fork work. Also: this session runs `release.py` with you present (the fork was denied it by the permission classifier; expect prompts for `release.py` and `release-push.py`), and the fork agrees to the push freeze in W0-3.
3. **PT-2 credits.** Go for two Grok medium none probes with the bounds in the PT-2 row (`--timeout 5400`, `--max-resumes 2`, worst case about $45 each, $90 for two [I]); concurrent (contention confound, shorter) or serial (recommended if the balance is tight). Preflight first (free).
4. **Cleanup approval, in batches (W0-6, after the release).** Fork-owned list (fork runs it); engine-line list including the three out-of-tree and tagged worktrees (me); Codex worktrees (you); `--force` removals of a13-33dbfd and e2e-hosts-b66343 after their diffs exist; the repo-distill branch and the write to the remote-less lab repo (with `keep/repo-distill-c75d630a` checked out as its `SKILL_CRAFT_ROOT`). Recommend yes to all, with W0-2 first. The housekeeping journal commit (every tag and sha, in the repo) precedes all deletes.
5. **Lifecycle stack.** A) defer and record the defect as backlog candidate 14, with the design on `keep/repo-distill-c75d630a` (recommended). B) cherry-pick the three codex commits now; if so confirm the 2026-09-27 owner decision still stands (cited only in 722037f8 and the 3533706e docstring; no memory entry). C) drop.
6. **Where the archive lives.** Journal in the repo plus local tags plus the bundle in `/Users/dadleet/src-archive/2026-10-06/` is the default. Also push the three tags that name live triggers (`keep/codex-shiploop-finalize`, `archive/codex-shiploop-e2e-evidence`, `keep/bold-albattani-dab387b5`) to origin so the designs survive a lost machine (recommend yes; pushing tags is publishing, so it is your call).

**Defaults recorded (proceed unless you object):** bold-albattani stays on its tag; CI-4 lands (about +72 s on 23% of pushes; the 09-24 miss is the evidence); CI-1 uses `No-Change-Note`; the 5 calibration files go to the archive dir, not the repo; the engine stop point is design-only (RC1 plus the watcher cover the need); the SPEC amendment is dated only if RC3 or PT-5 is built (fork writes it); PT-3's judge spend is asked again after PT-2 with measured numbers; the preservation branch is deleted once you agree.

## 5. Risks and what is deliberately not planned

**Risks**
- **Everything moves.** origin/main changed three times in three hours and the fork's worktrees changed under the classifiers. Re-read `origin/main` and run the W0-1 guards before every step; the release push aborts if main moves, hence the freeze and the recovery step in W0-3.
- **Release is irreversible** (roll forward with a note). Codex deletes the old plugin version's files, so a Codex ShipLoop run cannot resume across a release or a Codex host upgrade; the guard checks run dirs and recent rollouts, but Codex app threads need the owner's word. Whether a push alone triggers a Codex sync is unknown.
- **Canonical refresh** switches branches under pid 7013 (unidentified): only when idle. The preservation commit touches `skills/shiploop`, so it stays local.
- **Branch `-D`** loses commits except through tags/bundle; tags and the bundle are single-machine copies (and the lab has no remote) until decision 6 or the journal. The reflog is not protection.
- **Note-carrying landings gate marketplace runs.** Any `changes/` note on main makes `version_gate` refuse `--source marketplace` until the next release; the PT-2 window rule and batching exist for that.
- **Disagreements:** bold-albattani (classifier: land; me: keep); run-option mechanism (resolved to `--start-run`, PT-2 on the zero-code route); classifier 7 listed fork worktrees as "not to touch" while classifier 6 proved them incorporated (resolved: fork confirms, then `-D` with a tag); classifier 4's new archive tag is unnecessary because `keep/repo-distill-c75d630a` exists.
- **Unknown, not assumed:** whether the Codex app holds threads on its worktrees; whether `--timeout` is per run or per session; the platform task limit today (README says 18-30 min, ledger says 120.3); Grok credit balance and price; the a26 tick (stated only in a commit message); Luna below xhigh; escape rate with review off; whether Cursor has a refresh command beyond re-copying; every dollar figure marked `[I]`. The brief's "26 min Grok to test-strategy" is not in any file I found (the probe measured 44.8).

**Deliberately not planned:** the engine stop point now, the Luna none run (unmeasured, estimated at least 115 min), M3 to-green runs, the default flip without the decision-1 rule, the mdkit case and repo-distill skills release, the e2e-evidence calibration design, the platform-card pointer, the 0.20 CI branch, e4dd88d7, a script-owned document-check lint, a cheaper revise path, size caps, the packet-rules file split, and any compatibility or migration path for older runs or notes. All spending steps (PT-2, PT-3, RC5-2, the lifecycle live case, the Step B round) wait for your explicit go.