# ShipLoop improvements planned while the Luna run is live (2026-10-04)

Execute: inline

Status: three plans concluded and revised after adversarial review; execution is local until the Luna run ends and the batch is released (batch discipline). Governed by `test/shiploop_e2e/SPEC.md`. Sequencing below is the completeness critic's output, verbatim apart from this heading; its "premises corrected" section supersedes the premises of the plans it names.

## The plans

| Plan | First-round review verdicts (rules, reality, runtime) | File |
| --- | --- | --- |
| I2b: trim the planning prompts | needs-changes (2 blockers, 4 majors); needs-changes (0 blockers, 6 majors); needs-changes (1 blockers, 4 majors) | shiploop-i2b-trim-planning-prompts-plan-2026-10-04.md |
| Release the queued fixes and verify them after the Luna run ends | needs-changes (2 blockers, 4 majors); needs-changes (0 blockers, 4 majors); needs-changes (0 blockers, 4 majors) | shiploop-release-batch-plan-2026-10-04.md |
| Callback typos: measure first, then decide | needs-changes (0 blockers, 5 majors); needs-changes (0 blockers, 5 majors); needs-changes (0 blockers, 3 majors) | shiploop-callback-typos-plan-2026-10-04.md |

The reviews' blockers and majors were accepted or rejected inside each plan; the revised plans are the files above.

## Decisions taken without waiting for the owner (defaults, reversible)

- **Callbacks:** defer the engine change (Item C); keep the evidence in the repo; reopen on R1 or R2 in the plan.
- **Prompt trim (I2b):** build and test locally on the budget and check branch; claim only measured size and a consistent gate, not a loop fix (see the superseded finding in the journal).
- **Release:** rehearse locally in a disposable worktree from the merged tip; no push before the Luna run ends or the owner says go.
- **Open owner calls, left open:** whether the other session's A1 to A3 ship in this batch; whether Item C is built on hygiene alone; the seeded-run effort; whether a push at the Luna end needs a fresh yes.

## Execution sequence, collisions and release bundle (completeness critic)

Evidence labels: [M] means I read it in the repo or on disk just now. [I] means I inferred it.

## Premises corrected
- [M] The validator (931c53e2, 6a997a02) and the exporter commits are already on the local branch f3 (a96f8a0e, 17 ahead and 9 behind origin/main 4f237af4). They are not separate branches to wait for. `git merge-tree` of HEAD with origin/main conflicts only in `test/shiploop_e2e/LEARNINGS.md` and `test/shiploop_e2e/run.py`. `shiploop_navigator.py`, `SKILL.md`, `README.md` and `test/shiploop-e2e.test.py` auto-merge.
- [M] Luna harness pid 63861 is alive, resumed with `--timeout 36000`. That puts the deadline at about 11:56 PDT [I].
- [M] A1 (the other session) already has an untracked note, `changes/shiploop/test-run-could-not-run.md`, `bump: minor`. The release plan's note list omits it.
- [M] The release plan names a seeded xhigh `temperature-report` run (step 16) as I2b verification. I2b's revised plan says a seeded run cannot confirm anything and names the unseeded Luna max battleship run (V2) as the check. The master plan's I2b row still says "seeded Luna run ... starts no whole loop". These three disagree (see section 5).
- [M] `test/shiploop_e2e/README.md` and the memory rule say Luna E2E runs at xhigh. The prompt-trim plan says the live run is max, from `invocation.json`.

## 1. One execution sequence
**Parallel now (local only, no push, no engine change on origin/main):**
- I2b: worktree `i2b-<rand>` from a96f8a0e; apply the patch, E1-E5 and tests; one local commit. It touches the prompts, navigator and guide only.
- I2c planning (own admission).
- Callbacks steps 1-3: `callback_failures.py`, `failures.json` and the LEARNINGS section. These are docs only.
- A1-A3 (other session): finish and commit locally.
- Release step 1-8 on `integ/batch-<rand>`: merge origin/main, resolve the two hunks, and do a rehearsal cut. Step 5 of the release plan says to merge I2b only if it is green and admitted.
- Prompt-trim V1: Sonnet hello with `--source checkout`. This is ungated, but it runs from a worktree that is ahead of origin/main. It must not be launched from the harness checkout used for the Luna gate.

**Waits for the live Luna run to end (or an owner go):**
- Callbacks step 4 (`failures-final.json`) and the Luna entry in LEARNINGS.
- Release steps 9-12: journal the Luna result, freeze, final cut, push.
- No baseline row exists for the resumed run. The 01:54 row is the first process's timeout [M, release plan].

**Waits for the release push:**
- Marketplace refresh on Claude, Grok and Codex, then preflight, then hello (release steps 13-15).
- Prompt-trim V2 (unseeded Luna max battleship, 12 h or more).
- Callbacks M1 (Claude failure metric). It needs A2 merged first and its own admission, so it can land in the batch only if A2 does.
- Journal commit, master plan table and Run Review page updates.

**Not before a trigger:** callbacks Item C (R1 or R2) and the Luna rerun after it.

## 2. File collisions and merge order
Merge order: origin/main into integ first, then f3 tip (validator and exporter), then A1-A3, then I2b, then callbacks docs and M1.

| File | Who touches it | Resolution |
| --- | --- | --- |
| `test/shiploop_e2e/LEARNINGS.md` | origin/main (+104), f3 (+80), A-session (dirty, +31), I2b, callbacks, release journal | Conflicts today [M]. Keep every appended section. Resolve once at the integ merge. Later appenders go after it. |
| `test/shiploop_e2e/run.py` | origin/main, f3 (exporter), A-session (dirty, 147 lines) | Conflicts today [M]. The release plan says to keep the union and `import importlib.util`. The A-session diff fails `git apply --check` on run.py [release plan, not rerun here]. Apply A on top of integ after the merge. |
| `test/shiploop-e2e.test.py` | origin/main, f3, A-session (dirty, +209), callbacks M1 | Auto-merges today [M]. Add M1's case after A. |
| `test/shiploop_e2e/metrics.py` | origin/main (also changed), A2 (dirty, 174 lines), callbacks M1 | M1 waits for A2, as the callbacks plan says. |
| `skills/shiploop/SKILL.md` | origin/main, f3, A-session (dirty, 20 lines) | Auto-merges with f3 [M]. Check A-session against integ. I2b leaves SKILL.md alone. |
| `skills/shiploop/scripts/shiploop_prompts.py` | validator line, budget text (112b239c), I2b | Keep `BACKCHAIN_CHECK` and the budget paragraph. I2b trims around them. I2b is built on a96f8a0e, so it applies cleanly. |
| `skills/shiploop/scripts/shiploop_navigator.py` | origin/main (chain), I2b render block, Item C (if triggered) | Auto-merges with f3 [M]. Rerun the contract and dry-run tests after the merge. Item C's `_callback` edits touch the same file as I2b, so merge I2b first. |
| `skills/shiploop/scripts/shiploop_protocol.py` | validator verb, Item C | Textually clean per the callbacks plan [I]. |
| `skills/shiploop/references/navigator.md` | A-session (dirty) | I2b edits `backchain-planning.md` instead, so there is no collision [M]. |
| `docs/shiploop-backchain-validator-comparison-plan-2026-10-04.md` | I2b Part C row, release (mark I1, I2, I2b) | Edit once, after verification. |
| `test/shiploop_e2e/baselines.jsonl` | dirty row in the f3 worktree | Leave uncommitted. Commit hello rows only after the batch. |
| `test/suite_catalog.py`, `test/test-groups.test.py` | f3 already registers `backchain-check`. | I2b adds no new top-level file. The A-session tests already exist and are registered [M]. Recount only if a new suite lands. |

## 3. Release bundle
Notes: `changes/shiploop/budget-every-backchain-loop.md` (patch), `backchain-check.md` (minor), `test-run-could-not-run.md` (minor, A1, not yet in the release plan's list), I2b `trim-planning-prompts.md` (patch), `changes/shiploop-e2e-audit/run-review-page.md` (minor) and `backchain-check-verb.md` (patch).
- Expected result [I; confirm with `release.py --dry-run`]: ShipLoop 0.50.0 to 0.51.0, e2e-audit 0.5.4 to 0.6.0, skill-craft 1.18.0 to 1.19.0. Backchain and plan-dispatcher stay unchanged, because I2b's patch excludes `skills/backchain/*`.
- Metrics, progress, harness and docs changes need no note, because `check-release-boundary` only requires notes under `skills/` and `agents/`. Item C would add a shiploop minor and an e2e-audit patch.

**The verification run must confirm** (one run after the push, Luna max battleship, unseeded; hello on Sonnet first):
1. Preflight shows "unreleased notes: 0 ... OK" on every host.
2. Hello passes with turns near 143-155 and cost near $3.3-3.7, `review-export/` non-empty, and failures 0.
3. Planning packets after `plan` print no "Selected Backchain and Until Loop resources" block (I2b signal a). This is a text-presence check on packets and is the only hard check.
4. No `plan draft shiploop:step-plan` scratch contract exists (signal b). This is observational. A recurrence refutes the claim that the trim fixes it.
5. Step-plan minutes against 163.9 (signal c), plus `check_suite --suite harness` and the full CI tier green on the release commit.
6. For A1-A3: a `could-not-run` disposition and per-stage attribution appear in `metrics.json`.

## 4. Not yet concluded, so not planned
| Item | Deciding question | Evidence that settles it |
| --- | --- | --- |
| a02, a script-written Backchain loop contract | Can a script write the contract within the 9,216 B budget for every stage without losing a justified obligation (S-5, S-10)? | A second Luna run on the released build showing whether the step-plan whole loop recurs, plus a hermetic contract-writer prototype. |
| a04, generate the per-criterion verification steps from the spec | Do the generated steps match what a model writes at step-plan, with no loss on S-3 exit criteria? | Compare generated and Luna-written steps on the battleship spec, and check each against its exit criterion. |
| a05, what the plan graph is for | Does any consumer (ShipLoop, plan-dispatcher, the validator) need the graph beyond the invariant check? | Read what `shiploop_backchain_graph.py` and plan-dispatcher actually consume, then compare a Backchain-on and Backchain-off run. |
| Screen the 42 lenses once per loop (I2c) | Is a single screen per loop as rigorous as re-screening each pass? Lens screens are 41% of plan-loop record bytes [M per plan]. | An eval on the Backchain harness, plus the sha check on the cited screen file (record 2's cited sha no longer matches the file, per the plan). |
| Length of Improve review loops (31% of planning time) | What is the marginal finding rate per extra Improve pass at plan and step-plan? | Per-pass change and finding counts from the Luna records. With no cap (S-10), the lever is to remove passes that never change a plan, not to add a limit. |
| Callbacks Item C | Did R1 or R2 occur? | The next resumed Luna session with 1,442 or more typed paths and zero typos is the only informative clean result. |

## 5. Missing from the three plans
- **Spec conflict on the verification run.** Choose one design. Either V2 unseeded (I2b) or the seeded xhigh run (release step 16). Update the master plan's I2b row and expected-result column to match, since the row still claims a seeded run settles the question.
- **Effort wording.** Say in `README.md` and the journal that the Luna E2E default is now max, or correct the plan. The README still says xhigh.
- **SPEC amendments.**
  - Record the S-4/S-5 exception for model-copied paths, with R1 and R2 as reopen triggers.
  - Record that Claude failure counts are lower bounds until M1.
  - Record the step-plan minutes method (head line to complete line via `timeline.jsonl`). The helper script lives only in the scratchpad.
  - Clause S-6 gets a one-line note that audit stages print a status line instead of the loop list.
- **Admission record for I2b.** The plan lists risks with dispositions but needs the table form the SPEC requires. Name the S-n anchors, the run evidence (Luna events 2178-2181) and the named adversarial scenarios.
- **A1's note and A2/A3.** Add A1's minor note to the bundle. Decide whether A1-A3 ship in this batch, which is open in the release plan.
- **Journal entries.** The release plan journals the Luna result and the verification. I2b writes its own section, and callbacks writes one. Mark the "0, 0" Claude cells (callbacks) and the old `metrics.json` minutes as superseded with date and reason, not deleted.
- **Scratchpad evidence to export into the repo** (owner rule: evidence stays in the repo). The I2b patch, the `step_plan_minutes.py` helper, and the callbacks scripts (kept in the repo only as `callback_failures.py`) must all be committed or referenced by path in the journal.
- **Page updates.** The Run Review page needs the I2b row and the release-verification row. The release plan mentions the page only for I2b.
- **Unattended-run hygiene.** Confirm that no worktree launches the next Luna run while the integ branch is ahead of origin/main. The gate refuses HEAD ahead of origin/main, and hello rows must stay uncommitted in the harness worktree until the batch ends.
