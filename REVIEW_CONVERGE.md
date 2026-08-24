# Review Converge: ShipLoop survey-before-spec

**Target paths:** `skills/shiploop/`, `docs/LOOP-ENGINEERING.md`, `skills/devloop/references/loop-engineering.md`, `test/shiploop.test.sh`, `test/fixtures/shiploop/`, `plugins/shiploop/`, `REVIEW_CONVERGE.md`
**Test command:** `bash test/shiploop.test.sh && node test/skill-frontmatter.test.js && bash scripts/sync-plugin-views.sh --check shiploop`
**Started:** 2026-08-23          **Status:** active
**Round counter:** 1
**Consecutive clean rounds:** 1
**Known test-artifact paths:**
**Plan contract:** `/Users/dadleet/.cursor/plans/survey_before_spec_519f76f6.plan.md`
**Plan hash:** `23749fe13921550b97f5e495f120fd331b7f7e40901be4f2e15fdb32be493083`
**Base ref:** `428aa59a3dc837320f91b1a25461e2a2cbc44f9a`

## Stop-condition tracking
- consecutive-no-progress: 0
- consecutive-same-error: 0 (signature: none)

## Log
### Round 1 — 2026-08-23
**Review:** 0 material, 1 minor (new)
**Material findings:**
- none
**Deferred (minor/P2):**
- [ ] P2: `forward_dest`'s `residual` branch has a dead conditional — `if plan_waiver(state): return "done"` is immediately followed by an unconditional `return "done"`, so the waiver check changes nothing about the returned destination (the real done-gate is still enforced downstream by `residual_gaps` / `recap_gaps` via `missing_for`) [skills/shiploop/scripts/shiploop:forward_dest] — code
**Git-history check:** Read the last 10 subjects (`a717382` gate brownfield survey + leftover spec.json pair-hash, `d78d7e2` document full workflow/state files, `b27a57c` require practice research + HTML recap, `a3cdb3c` ShipLoop 0.7.0 survey-before-spec, `428aa59` Steer→ShipLoop rename, `fca1cca`/`5834c11`/`a4e6c5a` prior steer residual×2, `29b86d1` ship steer 0.2.0, `5f93840` compose overlays around DevLoop). Those teach: one controller per session, no second COMPLETE, scripts check keys not policy, fail-closed hashes, and (from the immediately-prior steer residual×2) worktree isolation must copy DevLoop habits without copying auto-merge. This round's target (`skills/shiploop`) is the renamed+extended leaf; `a717382`'s own residual anchors (A1–A27, F19–F25) are the forward spec for this cycle. HEAD already equals `a717382` — nothing further to land forward of the ship SHA. Reverse-diffed `428aa59..HEAD` (40 files, +3068/-597) for the four ship commits: script (763 lines), README (335), test suite (680), new activities/references (survey.md, state-files.md), fixtures (existing-app, missing-prompt.json, cycle/linear/two-root updates). No debug leftovers, no secret-shaped strings, no stray `/speckit` in new files. `diff -q docs/LOOP-ENGINEERING.md skills/devloop/references/loop-engineering.md` and the plugin-view tree (`skills/shiploop` vs `plugins/shiploop/skills/shiploop`, script + all references) both match exactly (pycache diffs excluded, gitignored). Baseline `bash test/shiploop.test.sh && node test/skill-frontmatter.test.js && bash scripts/sync-plugin-views.sh --check shiploop` run independently before this review: 75 hermetic layers PASS, skill-frontmatter PASS 17 skills, plugin-view CHECK OK. Per plan F25, the prior foreign ledger (bound to `steer_backchain_dag_14e32013`, terminal `complete` at `fca1cca`) was archived before opening this campaign, never re-opened.
**Plan:** n/a (clean)
**Plan review:** n/a
**Implementation:** none
**Lint:** skipped (none configured)
**Test result:** N/A (clean round)
**Outcome:** clean
**Error signature:** none
**Learnings:** A round run immediately after a well-tested ship (75 hermetic layers, all 27 spec anchors already marked `verified` in the plan) can honestly be clean on its first pass — forcing a manufactured material finding here would just be theater. The one real thing found was a harmless dead branch in `forward_dest`'s `residual` case: the waiver check and the fallthrough both return `"done"`, so the conditional has no observable effect (the actual done/halted gate lives in `residual_gaps`/`recap_gaps`, called separately via `missing_for`) — parked as P2, not material, since nothing behavioral regresses. Confirmed the plan's own "leave alone unless newly material" list (TAB/CONTROL_RE, `{{KEY}}` nesting, dead `/devloop` lstrip, empty `inputs: []` inv-7) is still present verbatim in the renamed script but none of it is newly material for this survey-before-spec increment, so none of it is re-raised here.
**Anchor evidence:**
- A1 → `validate-spec.md` + `survey.md` still order survey → practice research → spec; script's `load_environment`/`load_spec` gate on that shape
- A9 → `diff -q docs/LOOP-ENGINEERING.md skills/devloop/references/loop-engineering.md` exit 0
- A16/A18/A22 → `test/shiploop.test.sh` inject-step layer (add/refuse-running/refuse-drift/drained) PASS
- A21 → `LAYER: leftover spec.json pair-hash OK` PASS
- A25/A27 → missing-prompt and uncited-reference layers both exit 2 with the expected message; once cited, `next` reprints the reference path verbatim
- plugin views → `skills/shiploop` vs `plugins/shiploop/skills/shiploop` diff clean (script + references), `sync-plugin-views.sh --check shiploop` OK
**Consecutive clean rounds after this entry:** 1
**Committed:** yes
**Notes:** Fresh ledger opened for this plan (`survey_before_spec_519f76f6`) bound to Base ref `428aa59` (the ShipLoop rename SHA — ship SHA `a717382` is already HEAD). Prior foreign terminal ledger (`steer_backchain_dag_14e32013`, Status `complete` at `fca1cca`) archived to `REVIEW_CONVERGE.archived-steer-backchain-20260823.md` per plan F25 and the hard constraint against committing `REVIEW_CONVERGE.archived-*.md` — that file is intentionally left untracked, matching the existing pattern of the three other archived ledgers already sitting untracked at repo root. First of two consecutive cleans; per Phase 2, the suite is deferred to the second clean round (recorded here as `N/A (clean round)`) even though it was independently confirmed green as part of this round's own diligence. Pathspec-only commit under Target paths; no `git add -A`.
