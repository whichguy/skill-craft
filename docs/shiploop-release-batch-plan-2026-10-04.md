# Plan: release the queued batch after the Luna run ends, then verify it

Planned 2026-10-04 by a three-lens workflow (draft, three adversarial reviews, revise). `[M]` marks a claim its author measured in the repo or on disk; `[I]` marks an inference. Paths under `/private/tmp/claude-501/` are scratch and will not survive; the evidence a plan needs is exported into the repo by its own steps. Index and sequencing: `docs/shiploop-planned-improvements-2026-10-04.md`.

Status: concluded; the premises are corrected below and every version, SHA and count is re-read at execution (it moved twice today).
Blocks starting: nothing for local steps 1-8; the push (step 12) waits for the Luna run to end (kill about 11:56 PDT, inferred) or an owner go; I2b is not built, so its seeded run is conditional.

## Goal and evidence
Goal: one release (budget text 112b239c, Backchain graph check, Run Review exporter, I2b only if built) cut from a clean worktree, pushed once after the live run, refreshed on the three hosts, verified once. Rules: batch discipline; SPEC "Publish, then refresh, then run" and "Choose the verification runs from a coverage map"; KISS.
- Measured: origin/main is 4f237af4 (docs, CI success) on b97c3a0a (1.18.0; ShipLoop 0.50.0, e2e-audit 0.5.4, backchain 0.6.2, plan-dispatcher 0.6.1); b97c3a0a's full-tier run is still `in_progress` (gh, 16:51Z). `changes/` on origin/main holds only README.md. Claude, Codex and Grok all list 1.18.0.
- Measured: the local branch is ahead 16, behind 9, with a modified `baselines.jsonl`. The validator is already on it: `git cherry -v HEAD worktree-agent-a05edeeaa883c2c09` prints `-` for e0d83377 and a762605c (= 931c53e2, 6a997a02). So are the exporter commits; `worktree-agent-af41c2912efab94c7` is stale (80b48e4d `+`). No I2b branch exists. Correction: the draft's "merge the validator" was wrong.
- Measured (`git merge-tree`, three-way): merging origin/main into the branch conflicts in two hunks only. LEARNINGS.md: keep both sides. run.py: the import block; keep `import importlib.util` (used by `review_export`). The export call merges cleanly, so the draft's "re-add the export call" was wrong.
- Measured: Luna harness pid 63861 (cwd harness-298850) runs `--resume-run ... --timeout 36000` since 01:55:58; `version_gate` is called only at launch or resume, so it is past it. result.json (01:54) is the first process's timeout: stale. Correction: a resumed run writes no baseline row (`baseline_file = args.baseline if not (resumed or seeded) else None`), so nothing is carried from harness-298850; the 01:54:32 row (process false, turns 0) in the f3 worktree is the first process's timeout row.
- Measured: a launch is refused on CI failure, any note under changes/ on origin/main, or local HEAD ahead of origin/main (behind is allowed: `local_behind_main`); pending CI passes. `release-push.py` pushes `<url> <head>:refs/heads/main`, which does not move refs/remotes/origin/main: fetch before building the harness worktree.
- Inferred (confirm with `release.py --dry-run`, not run here): notes are budget-every-backchain-loop (patch), backchain-check (minor), run-review-page (minor), backchain-check-verb (patch), so skill-craft 1.19.0, ShipLoop 0.51.0, shiploop-e2e-audit 0.6.0; backchain and plan-dispatcher unchanged.
- Measured: a range with a release commit runs the full CI tier, 18.75 min for 1ff8c841 (gh, 15:50:17Z to 16:09:02Z) against about 4.4 min for ordinary pushes.
- Coverage map (SPEC): budget text and refusal sizes, hermetic only (live proof needs a looped Luna run, next batch); backchain-check, hermetic (corpus pinned to lib.js) plus Sonnet hello for no regression; exporter and run.py wiring, hermetic plus the hello run's `review-export/`; release payload, preflight and CI; I2b, the seeded Luna step-plan run.

## Changes
| File | Edit | Before to after |
| --- | --- | --- |
| catalog/skill-craft-plugin.json, CHANGELOG.md, plugins/skill-craft/**, host catalogs, README inventory, `version:` fields | Written only by `scripts/release.py` (one commit, `Skill-Craft-Release:` trailer) | skill-craft 1.18.0, shiploop 0.50.0, e2e-audit 0.5.4 to 1.19.0, 0.51.0, 0.6.0 (inferred); backchain 0.6.3 only if I2b edits skills/backchain |
| changes/shiploop/*, changes/shiploop-e2e-audit/* | Consumed and deleted by release.py | four pending notes to none; plus I2b (patch) and a backchain note only if built |
| test/shiploop_e2e/run.py | Merge resolution | one conflicting import hunk to the union (`import importlib.util` kept) |
| test/shiploop_e2e/LEARNINGS.md | Merge resolution, then the Luna 1.16.1 entry and the verification entry | both sides kept in date order; entries add run paths, status, S-clauses |
| test/test-groups.test.py, test/suite_catalog.py | Already on the branch; recount only if I2b or another suite lands | 65 / 38 / 105 (SHIPLOOP, core, total) |
| skills/shiploop/scripts/shiploop_prompts.py `_backchain_guidance` | Conflict rule if I2b merges | keep BACKCHAIN_CHECK once per Backchain stage and the budget line; I2b only trims the resource list and loop text |
| test/shiploop_e2e/baselines.jsonl | Not edited here | the f3 worktree's 01:54:32 row stays uncommitted; hello rows stay uncommitted in $H until the batch ends |
| docs/shiploop-backchain-validator-comparison-plan-2026-10-04.md | Mark I1, I2 (and I2b) in section 5 after verification | "run now" to verified, refuted or deferred, with run paths |

## Keep
- The hold on the push until the Luna run ends: it is the owner's batch rule (and keeps the gate clean for the verification runs). It protects the live run less than assumed (its profile's Codex marketplace is already the GitHub git remote, config.toml measured, with 1.17.0 and 1.18.0 published and its cache still on 1.16.1; so a new session there would already sync: inferred); state that, do not oversell it.
- Merge `--no-ff`, never squash or rebase (AGENTS.md); explicit pathspecs; `python3 -B` everywhere; rc captured, never `cmd | tail` as a gate.
- The budget text (112b239c), the check line, the audit route and the S-14 text: justified obligations; any I2b trim keeps them (S-6, S-7).
- Optimistic CI (SPEC): hello and preflight use throwaway profiles and do not wait for CI; only the real-host refresh waits for green.

## Tests
- Each, rc 0, from `$W`: `test/shiploop-backchain-check.test.py`, `test/shiploop-navigator-contract.test.py`, `test/shiploop-guidance.test.py`, `test/shiploop-packet-bounds.test.py`, `test/shiploop-navigator-dry-run.test.py`, `test/shiploop-actual-improve-cli.test.py` (budget refusal sizes), `test/shiploop-e2e.test.py`, `skills/shiploop-e2e-audit/harness/check_suite.py --suite harness`, `test/test-groups.test.py`.
- `bash $W/test/run-all.sh --group quick --changed-from origin/main --output $SP/quick-$RAND` (new directory, outside the checkout). The full tier is not run locally: CI runs it on the release commit.
- No new test file in this plan; a new top-level file (I2b) goes in test/suite_catalog.py.

## Notes and commit message
- Notes exist (list above). A note must name a leaf with `skills/<leaf>/SKILL.md`; never mix `bump:` and `version:`; I2b's notes are read as an installer would (one or two lines).
- Admission gate before the cut (SPEC "Change admission"): each commit in `origin/main..integ` that touches skills/ or agents/ names its record: 112b239c message; validator, plan section 6; exporter, run-review README and LEARNINGS (inferred, confirm); I2b, its own plan row with adversarial scenarios. A missing record blocks that commit.
- Journal commit (test/docs only, no note): `docs(shiploop-e2e): Luna max battleship on 1.16.1 ended <status>` with body: key learning, evidence paths (/Users/dadleet/e2e-runs/20261003/v1161-battleship-luna: result.json, metrics.json), "no baseline row: resumed run", related 112b239c, 6a997a02, 180a1b48, 04af25ba; trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Verification commit, after the runs: `docs(shiploop-e2e): verification of skill-craft <ver>` with the preflight lines, CI minutes, hello verdicts, turns and cost against 143 turns and $3.295 (1.16.1) and 155 and $3.6865 (1.16.0), seeded facts if run, refuted claims, S-clauses, run paths, related <release sha>.

## Steps and order
Parallel now (during the live run, all local): 1 to 8. Waits on the Luna end or an owner go: 9 to 12. Waits on the release push: 13 to 17. Never touch the live run's directory, `harness-298850`, or canonical `/Users/dadleet/src/skill-craft` (read-only there).
1. Snapshot in parallel: `git -C $C fetch origin`; ORIGIN, catalog version, `git -C $C ls-tree -r --name-only origin/main changes/`, `gh run list --repo whichguy/skill-craft --commit $ORIGIN --json status,conclusion` (failure stops, pending continues), `git -C $C status --porcelain=v1 --untracked-files=all`, `pgrep -fl 'run.py .*--resume-run .*v1161-battleship-luna'`, and the f3 branch tip SHA with `git log --format=%h origin/main..<tip>`. Fold what the other session needs to know into the one status message to the owner.
2. `RAND=$(openssl rand -hex 3)`; `W=$C/.claude/worktrees/integ-$RAND`; `git -C $C worktree add $W -b integ/batch-$RAND <recorded tip SHA>` (committed state only, so the dirty row stays out).
3. `git -C $W merge --no-ff origin/main`; resolve the two hunks; `git -C $W add` the two files; `commit --no-edit`; `grep -n '^import importlib.util' $W/test/shiploop_e2e/run.py`; run `test/shiploop-e2e.test.py`.
4. `git -C $W cherry -v HEAD worktree-agent-a05edeeaa883c2c09` must print only `-`; a `+` is a new validator commit: merge it `--no-ff` once its tests pass. Never merge `worktree-agent-af41c2912efab94c7`.
5. I2b: merge only if committed with green tests and its admission row; resolve `_backchain_guidance` per Changes. Not ready at the Luna end or 11:56 PDT: release without it (no second wait).
6. Admission and notes gate: `git -C $W diff --name-status origin/main..HEAD -- changes`; read each note; `python3 -B $W/scripts/check-release-boundary.py --base origin/main` prints OK.
7. Footprint tests (Tests), in parallel, rc captured.
8. Rehearsal cut in a disposable worktree: `R=$C/.claude/worktrees/rel-$RAND-1`; `git -C $C worktree add $R -b rel/batch-$RAND-1 integ/batch-$RAND`; `release.py --dry-run`, then `release.py`; run Verification 1-3. Tell the owner: versions, tests green, held. This also checks the computed versions.
9. Luna ended = harness `pgrep` empty and result.json rewritten after 01:56 (or killed at the deadline). Read result.json and metrics.json; do not use the 01:54 row.
10. Journal the Luna result on `integ/batch-$RAND` (explicit paths, no note). The journal lives on integ so a recut cannot lose it.
11. Freeze and final cut: `git -C $C fetch origin`; if origin/main moved, merge it into integ (step 3 rules; re-check its CI); re-snapshot `git -C $W log origin/main..<f3 tip>` and merge new green commits; drop the rehearsal (`worktree remove`, `branch -D`, ours only); cut `rel-$RAND-2` as in step 8; `HEAD`, `TREE` (`HEAD^{tree}`), `BASE` (`git ls-remote origin refs/heads/main`), `merge-base --is-ancestor $BASE $HEAD`, tree clean.
12. Push (owner rule met or owner go; standing authority: memory push-updates-marketplace): `python3 -B $R/scripts/release-push.py --repo $R --expected-head $HEAD --expected-tree $TREE --expected-base $BASE --check '["bash","scripts/sync-plugin-views.sh","--check"]' --check '["python3","-B","scripts/check-marketplace-packages.py"]' --check "[\"python3\",\"-B\",\"scripts/check-release-boundary.py\",\"--base\",\"$BASE\"]" > $SP/push.json 2> $SP/push.err; echo rc=$?`. It refuses Git env overrides itself and fails safe; rerun under `env -u <named var>` if it does.
13. In parallel after the push: `git -C $C fetch origin`; CI watch every 3.5 min (`gh run list ... --commit $HEAD`); `H=$C/.claude/worktrees/harness-$RAND`, `git -C $C worktree add --detach $H origin/main`, then require `git -C $H merge-base --is-ancestor $HEAD HEAD`; hosts after CI is green, Codex last (docs/distribution.md "Updating"): `claude plugin marketplace update whichguy && claude plugin update skill-craft@whichguy`; Grok `plugin marketplace update`, `plugin update skill-craft`; Codex `plugin marketplace upgrade whichguy && plugin add skill-craft@whichguy` only if `pgrep -fl codex` lists nothing but ChatGPT.app's app-server and exec-server, else skip and tell the owner.
14. Preflight: `python3 -B $H/test/shiploop_e2e/run.py --preflight-only --host all --output $SP/preflight-$RAND`; a REFUSED host gets no run.
15. Hello gate, alone: `python3 -B $H/test/shiploop_e2e/run.py --case hello --host claude --output /Users/dadleet/e2e-runs/$(date +%Y%m%d)/v<ver>-hello-sonnet` as a Desktop background task; killed at 18-30 min: relaunch with `--resume-run <dir>`; watch with `progress.py` every 3.5 min.
16. Only if I2b shipped: `run.py --case temperature-report --host codex --model gpt-6-luna --effort xhigh --seed-at step-plan --timeout 14400 --quiet --output .../v<ver>-seeded-luna-step-plan` (no push or note-bearing commit while it runs; a Codex resume across a release is refused).
17. Journal in $H, commit the hello row and entry with explicit paths and push at once (test-only, CI quick) so $H is not left ahead; mark I1, I2 (and I2b) in the master plan table; canonical: fast-forward to origin/main only if clean and on main (`git -C $C merge --ff-only origin/main`), else leave it and tell the owner.

## Risks
- origin/main moves again (twice today): mitigated; step 11 refetches and recuts, `--expected-base` refuses a moved remote.
- Push while the live run exists: accepted; the hold is the owner's rule, and the Codex-sync exposure already exists (inferred).
- A note-bearing push by the other session blocks launches: mitigated by the freeze merge (its note ships in our release) and by launching only from $H; otherwise fix forward.
- HEAD ahead of origin/main blocks the next launch: mitigated; hello rows and journal stay uncommitted in $H until step 17; never launch from $W or $R.
- release.py or release-push refuses (dirty tree, reused leaf@version, moved remote, env): mitigated by the disposable worktree, the rehearsal and rc capture.
- Red CI (b97c3a0a's full tier is unfinished): mitigated by a check at step 1 and 11; fix forward, cancel runs in flight, tell the owner.
- Wrong conflict resolution in run.py or `_backchain_guidance`: mitigated by the grep, `shiploop-e2e.test.py` and the navigator-contract check-line test.
- Codex refresh prunes the old version under a real-profile session: mitigated by the guard, Codex last and after green CI; the guard cannot see the app's own session (accepted).
- Seeded run at xhigh shows no loop: accepted as screening; no numeric comparator (the 135.8-minute loop was Luna max battleship).
- Luna killed at 11:56 unfinished: accepted; journal as interim, release regardless.
- I2b missing: mitigated; ship without; the journal says budget and check are hermetic-only.
- Hello fails on variance: mitigated; read the failing commands first, rerun once alone, two failures stop and the owner decides.
- Journal lost on recut: mitigated by design (step 10 on integ).

## Verification
1. `git -C $R show -s --format='%(trailers:key=Skill-Craft-Release,valueonly)' HEAD` names skill-craft, shiploop, shiploop-e2e-audit at the versions the dry-run printed (no unintended leaf).
2. `git -C $R status --porcelain=v1 --untracked-files=all | wc -l` is 0 and `python3 -B $R/scripts/check-release-boundary.py --base origin/main` prints OK.
3. `bash $R/scripts/sync-plugin-views.sh --check` and `python3 -B $R/scripts/check-marketplace-packages.py` both rc 0.
4. Step 7 commands rc 0; the quick receipt lists every selected suite passed (an "unclassified" error means an unregistered test).
5. `cat $SP/push.json` shows status pushed with head $HEAD; after `git -C $C fetch origin`, `git -C $C rev-parse origin/main` equals $HEAD (or a descendant).
6. `gh run list --repo whichguy/skill-craft --commit $HEAD --json status,conclusion,createdAt,updatedAt` ends `success` in about 19 min with `full / ...` jobs (a quick tier means the release commit was not in range).
7. `claude plugin list | grep -A2 skill-craft@whichguy`, `codex plugin list --marketplace whichguy | grep skill-craft` and the Grok cache `plugin.json` version (`/Users/dadleet/.grok/marketplace-cache/ae3129dcfeba6f1c/plugins/skill-craft/.claude-plugin/plugin.json`) all show the new version.
8. Preflight rc 0 and one line per host `origin/main <sha8> publishes skill-craft <new> / ShipLoop <new>; ... unreleased notes: 0 ... OK`; any `REFUSED` refutes.
9. Hello `result.json`: pass true, all five verdicts true, checks 2/2; `metrics.json` shiploop_failures 0 and model_glue 0; `<out>/review-export/` non-empty and the printed `review export:` line; turns and cost near 143-155 and $3.3-3.7 (inferred band).
10. Luna ended: pgrep empty, result.json rewritten after 01:56 (not the 36001.4 s first-process timeout). Live run unharmed: `ls /Users/dadleet/e2e-runs/20261003/v1161-battleship-luna/home/.codex/plugins/cache/whichguy/skill-craft/` still lists only 1.16.1 (measured now).
11. Seeded (I2b only): scratch has no `backchain-` contract naming draft or stage plan at step-plan; any contract file is at most 9,216 bytes (`wc -c`; CONTRACT_BUDGET in shiploop_loop_contract.py); no packet after plan prints the six-file resource list (string re-read once I2b exists). Screening only at xhigh.

## Rollback
- Before the push: `git -C $C worktree remove $R` and `git -C $C branch -D rel/batch-$RAND-N`, ours only; keep integ. Nothing else changed.
- After the push: never revert the release commit; `git revert` the offending source commit, add a patch note, release again; fix forward unless fatal. Hosts only move forward (one supported version); a bad Codex refresh is repaired by the next release.

## Open questions
- Seeded run effort: xhigh (owner's 2026-09-27 exception, recommended) or max (harness default, a stronger test of the trim, hours)?
- Wait for I2b? Recommended: only until the Luna end or 11:56 PDT.
- Do the other session's A1-A3 (a minor note; its dirty diff fails `git apply --check` on run.py and LEARNINGS.md and applies to the other eight files, measured) ship in this batch, or after verification?
- Discard the 01:54:32 baseline row, or keep it as a journaled interrupted row (not a verdict)?
- Does the push at the Luna end need a fresh owner yes, or does push-updates-marketplace cover it?
- Does `grok plugin update` accept `skill-craft` (its help shows an optional NAME), or only the id `skill-craft-b923f37c`?
