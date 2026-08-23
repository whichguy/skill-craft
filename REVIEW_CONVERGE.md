# Review Converge: steer backchain DAG residual×2

**Target paths:** `skills/steer`, `plugins/steer`, `skills/steer-next`, `plugins/steer-next`, `test/steer.test.sh`, `test/steer-next.test.sh`, `test/fixtures/steer`, `test/run-all.sh`, `docs/LOOP-ENGINEERING.md`, `skills/devloop/references/loop-engineering.md`
**Test command:** `bash test/steer.test.sh && bash test/steer-next.test.sh && bash test/devloop-run.test.sh && bash test/review-coverage.test.sh && node test/skill-frontmatter.test.js && bash scripts/sync-plugin-views.sh --check`
**Started:** 2026-08-23          **Status:** active
**Round counter:** 1
**Consecutive clean rounds:** 0
**Known test-artifact paths:**
**Plan contract:** `/Users/dadleet/.cursor/plans/steer_backchain_dag_14e32013.plan.md`
**Plan hash:** `c4d9793cbcce7858d729063dd88fa3fc2f69e11920531ca1c14cc92f1a3bf248`
**Base ref:** `5f938400b0dbcac5c25e263d54150195e8c321b2`

## Stop-condition tracking
- consecutive-no-progress: 0
- consecutive-same-error: 0 (signature: none)

## Log
### Round 1 — 2026-08-23
**Review:** 7 material, 6 minor
**Material findings:**
- Frozen-hash compare skipped when spec/plan files were missing, so a bound run could `next` / `complete-step` after delete [skills/steer/scripts/steer:check_frozen_hashes] — code
- `blocked → validate-spec` still compared `plan_sha256`, so dual drift wedged the prescribed spec rebind [skills/steer/scripts/steer:check_frozen_hashes] — logic-flow
- `--to implement` (`need=plan`) did not require `checkable:true`, so `blocked → plan` could walk an uncheckable spec [skills/steer/scripts/steer:missing_for] — logic-flow
- Non-string `backchain.goal` skipped A18 equality; newline/`/devloop` in `statement` was accepted at `--to implement` then claimed before `goal_line` died [skills/steer/scripts/steer:dag_gaps] — code
- Six `grep -qv` absence checks could never fail; symlink fixture used `|| true`; mid-graph `--to residual` was never invoked [test/steer.test.sh] — tests
- A4/A8/A15/A23/A24/A35 coverage holes (checkable implement, supplier-not-ready, resume jump, stale `step_ids`, residual-after-clear, spec.json + complete-step drift) [test/steer.test.sh] — tests
- `test/run-all.sh` had been about to absorb review-plan/advisors registrations (stripped on the product land) [test/run-all.sh] — docs
**Deferred (minor/P2):**
- [ ] P2: TAB (`\x09`) is omitted from `CONTROL_RE` — packet-only, no behavioral gate miss beyond A33's named newline/`/devloop` cases — corner-case
- [ ] P2: `interpolate` can substitute a value that itself contains a later `{{KEY}}` — packet text only — corner-case
- [ ] P2: `objective.lstrip().startswith("/devloop")` never fires because the objective is prefixed with `step ` — `goal_field` already rejects `/devloop` in parts — code
- [ ] P2: `turn-packet.md` lists step status `blocked` but `classify_steps` emits done/running/ready/todo — docs
- [ ] P2: `--to halted` accepts header `stopped` without latest-round landed proof (A37 is explicit for `--to done`) — logic-flow
- [ ] P2: empty `inputs: []` is treated as a root and skips inv-7 — corner-case
**Git-history check:** Prior ledgers archived (`REVIEW_CONVERGE.archived-*-20260823.md` / 20260801) were Status complete for other plans. Product land `29b86d1` shipped the uncommitted v1+increment tree (U6: residual base stays `5f93840`). Last 10 subjects: compose overlays / keep `/goal` out of the build loop; one product name; dest-contract generic; Grok `/devloop` owned in-repo; three-step handshake; interpolate-print-exec. Those commits teach: one controller per session, no second COMPLETE, scripts check keys not policy. This round applies the same fail-closed habit to missing frozen files, uncheckable implement, and vacuous tests. Foreign dirty trees (devloop/review-coverage/advisors) left unstaged.
**Plan:**
- P0: fail closed when a bound spec/plan file is missing; skip plan-hash compare on `--to validate-spec` so dual-drift rebind works
- P0: require `checkable:true` on `need=plan`; require nonempty string `goal` equal to `done_sentence`; sanitize `statement` in `dag_gaps`; validate `/goal` before `claim_ready`
- P1: replace `grep -qv` with `assert_absent`; assert symlink; invoke mid-graph `--to residual`; add checkable-implement, missing-files, supplier/hash-mismatch, stale `step_ids`, residual-after-clear, spec.json+complete-step drift, `blocked → residual` after drain, validate-spec/plan `/goal` absence, heading order
**Plan review:** native — keep pathspec to steer leaves + tests; do not absorb `.gitignore` or foreign plugin sync; do not add a second COMPLETE / `verify_cmd` (U4).
**Implementation:** `skills/steer/scripts/steer`, `plugins/steer/skills/steer/scripts/steer`, `test/steer.test.sh`, `test/steer-next.test.sh`, `test/fixtures/steer/goal-not-string.json` via native
**Lint:** skipped (none configured)
**Test result:** PASS
**Outcome:** fixed
**Error signature:** none
**Learnings:** Fail-closed hashes that only compare when files exist are fail-open deletes. A rebind edge that still compares the *other* artifact's hash deadlocks the hatch the plan named (`blocked → validate-spec`). `grep -qv` on a multi-line packet is not an absence proof — it passes if any line does not match. Claiming ready ids before interpolating `/goal` turns a print-time reject into a wedged `running` receipt; the DAG gate has to refuse the statement at `--to implement`. DevLoop history still applies: do not invent a second COMPLETE, and do not let tests claim an anchor they cannot fail.
**Anchor evidence:**
- A1 → `assert_headings` order walk in `test/steer.test.sh`; six H2s on steer-next intake/implement/temp HOME
- A2 → implement packet `frozen`; `assert_absent` refine/body dump
- A3 → empty spec.json / labeled mismatch layers
- A4 → checkable false → blocked; new `checkable false implement refuse` layer
- A5 → devloop init exit 2; drained residual without capture
- A6 → thin plan reject
- A7 → linear S2 todo; two-root two `/goal` lines
- A8 → planted S2 running → suppliers; hash-mismatch receipt; symlink DAG; concurrent receipts on disk
- A9 → mid-graph `--to residual` exit 2; foreign/unlanded/false-landed/stopped
- A10 → `test/steer-next.test.sh` refuse + missing STEER_ROOT
- A11 → SKILL.md Never-invoke grep; LOOP copies `diff -q`; compose graph no c-plan
- A12 → `scripts/sync-plugin-views.sh --check` PASS
- A13 → package-root refuse; symlink `backchain/plan.json` exit 2
- A14 → missing backchain + isolated steer-next
- A15 → blocked validate-spec ↛ implement; blocked residual → residual after drain
- A16 → this round's Test command PASS
- A17 → `emits a `/goal`` grep + identical copies
- A18 → goal-mismatch + goal-not-string fixtures; replan clears S1
- A19 → plan → blocked `resume_to=plan`
- A20 → unresolved/empty/cycle rejects
- A21 → drained residual, no AFTER
- A22 → skill-frontmatter PASS (steer 0.2.0 / steer-next 0.1.0)
- A23 → stale wrapper `step_ids=["S1"]` still claims S2
- A24 → clear S1 drops S2; `--to residual` then exit 2
- A25 → steer-next temp HOME prints all six H2s
- A26 → validate-spec/plan `assert_absent '/goal '`; implement has `/goal` + test/run/fix
- A27 → `assert_absent` refine
- A28 → plan.md prep / intermediate deploy / cleanup
- A29 → `--id S1` When done; mid-graph residual absent + CLI exit 2
- A30 → organic two-root claim / in-flight / double start
- A31 → backchain missing + refresh
- A32 → temp HOME without DevLoop
- A33 → injection refused at `--to implement`
- A34 → implement blocked reclaim; residual → blocked → residual
- A35 → spec.md, spec.json, DAG statement; complete-step on spec.json drift
- A36 → force wipe + implement/complete-step exit 2
- A37 → false-landed Round 2
- A38 → capture fail-closed
- A39 → clear S2 + next re-claim
- A40 → `assert_absent` VALIDATE_SPEC_PATH / dep_roots.devloop
**Consecutive clean rounds after this entry:** 0
**Committed:** yes
**Notes:** Product land `29b86d1` preceded this round so Phase 0 dirty-tree could start. Pathspec only. post-PASS hygiene: considered docs + repo cleanup; no extra product edits.
