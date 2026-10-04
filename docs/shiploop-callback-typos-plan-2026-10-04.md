# Callback typos: measure first, then decide (final plan, 2026-10-04)

Planned 2026-10-04 by a three-lens workflow (draft, three adversarial reviews, revise). `[M]` marks a claim its author measured in the repo or on disk; `[I]` marks an inference. Paths under `/private/tmp/claude-501/` are scratch and will not survive; the evidence a plan needs is exported into the repo by its own steps. Index and sequencing: `docs/shiploop-planned-improvements-2026-10-04.md`.

Status: concluded on the decision (defer the engine change, make the evidence durable, fix the Claude failure metric as its own item). Not concluded on the cause (run name versus resumed-session age), which one run cannot settle.
Blocks starting: nothing blocks steps 1-3 (docs and journal only) except where they land. Local branch f3-budget-all-backchain-stages-f05ed2 is 16 commits ahead of and 9 behind origin/main 4f237af4, with conflicts in LEARNINGS.md and run.py. Step 4 waits for the Luna run to end. M1 waits for the A2 merge. Item C waits for a trigger and the batch release.

## Goal and evidence

Goal: decide whether ShipLoop should change how a callback is printed or parsed, without touching the engine while the Luna run is live (batch discipline). Keep the evidence in the repo (owner journal rule). Say what would reopen the decision.
[M] = measured by me at about 10:00 PDT from /Users/dadleet/e2e-runs/20261003 (9 run dirs: 7 Claude Sonnet 5.5; Luna max battleship-luna on 1.16.0 and v1161-battleship-luna on 1.16.1; no Grok run). [I] = inferred. The 1.16.1 events.jsonl grew from 6,752 to 6,769 lines in minutes (codex pid 63880 live), so every count can rise.

1. [M] 41 failed ShipLoop or Until Loop commands (exit-code based; scratch scripts `callback-typos/{collect,classify,recovery,typed_paths,table}.py`, re-run in a copy):
   - 4 inserted-space paths (3 `complete`, 1 `until_loop next`).
   - 7 Until Loop script paths with `until-loop/scripts/` dropped (U1).
   - 7 bare `shiploop next` (exit 127) plus 4 older-cache refusals (the Claude resume prompt, fixed by 7c1f1014).
   - At most 15 refused on content (text match; seat-reservations #29 is a model script exiting 1 after a normal packet).
   - 4 other.
   - By host: Claude 15 (0 path typos), Luna 1.16.0 7, Luna 1.16.1 19.
2. [M] All 6 inserted-space paths are in v1161-battleship-luna session 2 (codex resume at +10.04 h; events line index 3999, 4285, 4857, 4982, 5526, 5975; +11.7 h to +16.5 h).
   - Session 1: 41 ShipLoop callbacks, 1,469 typed paths, 0 typos.
   - Session 2: 47 callbacks, 1,442 typed paths, 3 callback typos (6.4%), 4 broken commands.
   - battleship-luna: 26 callbacks, 749 paths, 0 typos.
   - Claude assembles callbacks from variables (141 of 149 recognised `complete` commands use `$R`, 8 literal; 98 of 247 `complete --action` commands are not recognised by the CLI pattern). Its 0 says nothing about copying the printed path.
   - The at-risk population is Luna: 3 of 114 callbacks.
3. [M] The run-name explanation (`/20261003/ v1161-`) is contradicted. Session 1 typed that boundary 1,467 times with 0 errors. v1161-hello (178 clean) is a Claude run and does not test it. Session age (a resumed codex exec, context 10 h old) is the only measured separator [I]. Compactions are not visible in the Codex stream, so context age is unmeasured. 6 of 1,442 against 0 of 1,469 typings has p=0.017; 3 of 47 against 0 of 41 callbacks has p=0.15 [I; consecutive typos are not independent].
4. [M] Correct typings between consecutive typos: 334 (from resume), 155, 246, 30, 249, 194. Each error was repaired correctly. "About one independent event" is unsupported: the readings run from 1 (contamination) to 6 events [I].
5. [M] Recovery: 10 of 11 path-class failures were repaired by the next call, one by +2 (until-loop #1461, 22.6 s). Total 110.2 s (0.17% of the 18.1 h run so far); the 3 failed callbacks cost 22.7 s, the 4 spaced commands 28.4 s.
   - No state change: a mistyped run dir exits before `run_lock` ("no ShipLoop run directory"), an unknown flag exits in argparse, a bad script path never runs.
   - No stray `/20261003/ v1161-battleship-luna` exists.
6. [M] `_callback` is the one builder. `--result`, `--opening` and `--message` are parser-required and refused unless equal to the derived path (`_submitted_result`, improve-commit, improve-start and improve-reconcile checks), so they carry no information. `run_dir_from_arg` (in scripts/shiploop) walks up for `.shiploop` only, so `--run-dir` cannot be inferred for workspace runs. The printed result path is 131-157 chars in all nine runs. A typical layout prints 111, and a 355-char callback (234 without `--result`) [I: assumed layout].
7. [M] The failure metric is blind for Claude. `metrics.collect` reads only ACP `tool_call_update` events. metrics.json has `shiploop_failures=[]` for all 7 Claude runs, against 15 failing commands plus about 30 refusals behind exit 0 (line-anchored pattern; the reviewer counted 33). LEARNINGS "Batch 1003 - Sonnet 5.5 results" says "0, 0" for four rows holding 13 failures. Claude counts are lower bounds. The exporter already reads `metrics.shiploop_failures`, so the one classifier home is `metrics.collect`.

Decision: defer Item C.
- Grounds: KISS (no break beyond a recoverable one-call cost) and Change admission's "cost more than it saves". Item C costs a release plus 18 test and fixture files to save about 28 s in an 18 h Luna run.
- Accepted exception to S-4/S-5 (a derivable path stays model-copied), stated with its cost.
- Also batch discipline: no engine change while a run is live, one release.

Reopen Item C when either of these happens, on ShipLoop callbacks only (Until Loop paths excluded; they are vendored argv):
- R1: a path typo in any run other than v1161-battleship-luna (any host, model, session or path length).
- R2: a callback typo not repaired by the next ShipLoop command, or a run ending blocked because of one.

The item stays monitored, never closed. A clean run is uninformative unless a resumed session types at least 1,442 paths with 0 typos (0.3% if the session-2 rate held) [I].

## Changes

| File | Edit | Before to after |
|---|---|---|
| docs/experiments/shiploop-callback-failures-20261004/callback_failures.py | New, about 150 lines, frozen one-time analysis (no model call): `--root`, `--cutoffs failures.json`, `--out`; classes keyed on line-anchored refusal text; header says superseded by `metrics.collect` after M1 | scratch scripts only to one command that reproduces the table |
| docs/experiments/shiploop-callback-failures-20261004/failures.json | New compact export: row per failed command (run, event index, verb, class, recovery calls, seconds, last 80 chars of path), per-run summary with events cutoff, callback and typed-path counts, Luna session split; denominators from events, not `callback-attempts` | none to 41 rows, 9 summaries |
| test/shiploop_e2e/LEARNINGS.md | New section `callback path typos across the 1003 batch (2026-10-04)`: status "firm for the counts; independence and cause inferred; engine change deferred", items 1-7, the decision and R1/R2, evidence path | earlier text kept |
| test/shiploop_e2e/metrics.py (M1, own admission, own commit) | `collect()` also reads Claude `tool_use`/`tool_result`; a command counts when it invokes the ShipLoop CLI (verb plus `--action` or `--run-dir`, variable-form included); failure = nonzero exit or a refusal line at a line start | Claude rows always `[]` to real failures |
| test/shiploop-e2e.test.py (M1) | one Claude-shaped fixture: nonzero exit, exit 0 with a refusal in a pipe, a source `cat` containing refusal text not counted | one ACP-only case to three |
| [IF TRIGGERED] skills/shiploop/scripts/shiploop_protocol.py | drop `--opening`, `--message`, `--result` (improve-start, improve-commit, complete, improve-reconcile) | 3 required derivable flags to none |
| [IF TRIGGERED] skills/shiploop/scripts/shiploop_navigator.py | the four checks use `_result_input_path`, `improve_opening_path`, `improve_commit_message_path` and the reconcile inbox path directly; `_callback` stops passing the path at 6 sites (complete x2, improve-start x2, improve-commit, improve-reconcile) | callback 473 to 316 chars (Luna), 355 to 234 (typical) |
| [IF TRIGGERED] 10 pinning tests, 4 audit-harness tests, 4 fixtures, README.md, commands/shiploop-complete.md, references/navigator.md | update to flagless callbacks (list from `git grep`; SKILL.md has no `--result` text) | footprint measured by `git grep` on origin/main |

## Keep

- The refusal for a missing run dir before `run_lock` (no stray directory from a typo) and the `--action` stale-action guard (S-1). Item C keeps both.
- Absolute printed paths in every packet (S-6: packets stand alone; claude resets cwd between commands, codex runs from `<out>/work`).
- Earlier LEARNINGS text and baselines.jsonl rows. The "0, 0" Claude cells are corrected only by edit-with-reason, under M1.
- Until Loop argv as vendored (whichguy/until-loop 0.7.0, 80e6caca). U1 is a separate item.

## Tests

- Steps 1-3: no hermetic test (docs and journal). The check is reproducing failures.json at its recorded cutoffs (Verification 2). There is no new top-level test file, so nothing to register in test/suite_catalog.py.
- M1: the fixture above in test/shiploop-e2e.test.py (an existing, catalogued suite), then `python3 test/run_suites.py --group quick --changed-from origin/main`.
- Item C: a callback without the flags completes; a stale `--result` exits 2 and names the flag; no printed packet head contains `--result=`, `--opening=` or `--message=`. Update the other pinning files, then run the quick tier.

## Notes and commit message

- Notes: docs and test/ only, so no `changes/<leaf>` note and no No-Change-Note trailer (check-release-boundary requires one only for `skills/<leaf>/` or `agents/<leaf>.md`). Item C needs `changes/shiploop/callback-derived-paths.md` (bump: minor) and `changes/shiploop-e2e-audit/<slug>.md` (bump: patch; its harness tests sit under that leaf).
- Commit with `git -C /Users/dadleet/src/skill-craft/.claude/worktrees/next-batch-eb98fc add <the three paths>` (never `-A`).
- Corrections to the brief and draft:
  - origin/main is 4f237af4 (b97c3a0a plus one docs commit), not 1ff8c841.
  - The validator (931c53e2, 6a997a02) and exporter (31fdb23d, 180a1b48, 04af25ba) are already commits on the local branch.
  - v1161-hello is Claude.
  - Appending to LEARNINGS.md is not a trivial merge (f3 +80/-1, origin +104/-0 since 213dc8dc).
  - The old-callback refusal does not say "reprint with next" (plain argparse).
  - The name explanation, "about one independent event", the close-out rule and the rename step are dropped.
- Accepted from the three reviews, each checked against code or data:
  - E2 is already met by #1461 (+2).
  - The name is contradicted by session 1.
  - Pooled rate and exit-0 masking (30 here, 33 theirs).
  - One classifier home.
  - The false "reprint" claim.
  - Naming the clause for the accepted disposition.
  - M1 split out with an A2 dependency.
  - Cutoff-pinned verification.
  - Symbols over line numbers.
  - Figures: 28.4 s is four rows, 5 of 7 Until Loop errors are in session 1, the event index is 0-based, the content class has a false positive.
- Rejected findings:
  - A standing rate threshold (invented thresholds).
  - A rename as control (the name is not isolable from session age).
  - Dropping the script entirely (kept frozen; evidence-in-repo rule and docs/experiments precedent).

```
docs(shiploop-e2e): callback failures across the 1003 batch: 6 inserted-space paths, all in one resumed Luna session

Key learning: of 41 failed ShipLoop or Until Loop commands in 9 runs, 11 were a harness Claude resume prompt naming a bare `shiploop` (fixed by 7c1f1014), 11 were path errors (4 inserted spaces, 7 dropped Until Loop script segments), at most 15 content refusals, 4 other. All 6 inserted-space paths sit in session 2 of v1161-battleship-luna (3 of 47 callbacks; session 1: 0 of 41, same run name), so the run-name explanation is contradicted and session age is the leading, unproven cause. Every error was repaired by the next call (10 of 11; one by +2), 110 s in 18 h, no state change. Claude counts are lower bounds: metrics.collect cannot see Claude failures. Engine change deferred (S-4/S-5 exception, cost stated); reopen on R1/R2. Evidence: docs/experiments/shiploop-callback-failures-20261004/failures.json; /Users/dadleet/e2e-runs/20261003. Related: 7c1f1014, b97c3a0a.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
```

## Steps and order

1. Parallel now: write the frozen script and failures.json (cutoffs = current events line counts); write the LEARNINGS section.
2. Run Verification 2, then commit locally. Either on the batch branch after f3 is merged with origin/main by hand (so the journal needs no second conflict resolution), or on f3 now, accepting one more hunk in an already conflicting file. Owner choice.
3. Push with the batch. A docs push is safe during the live run (the gate runs only at launch). Pushing f3 puts unreleased change notes on origin/main (four on f3 today), so the next Luna launch waits for the batch release.
4. When the Luna run ends: rerun the script at the new cutoffs into failures-final.json (never overwrite). Update the section by edit (counts, whether a typo followed session 2's last), then commit.
5. M1, in parallel with step 4, after the A2 session's metrics.py merges (not after the Luna run).
   - Own admission: anchor S-1/S-2 (SPEC "How the harness checks the clauses" row), evidence item 7, non-regression, adversarial table.
   - Own commit. Afterwards correct the Claude "0" cells by edit-with-reason and mark pre-M1 Claude rows unmeasured.
6. After every later long run: scan `shiploop_failures` lines for `unrecognized arguments`, `no ShipLoop run directory` and `can't open file`, and test R1 and R2. Nothing waits on the owner.
7. [IF R1 or R2] Item C: admit it (anchor S-4/S-5 plus the new run), edit protocol and navigator, update the footprint, add both notes. Do one release after the batch's live runs end, then one verification run (Luna max, a resumed session of 1,442+ typings), and journal it. The merge with the validator's protocol.py hunk (backchain-check, near the parser) is textually clean.

## Risks

| Scenario | Disposition |
|---|---|
| The journal rate is read as a normal-run rate or as proof of a harness artifact | Mitigated: per-host and per-session table, no pooled 0.6%, status "firm for counts; independence and cause inferred" |
| Another long Luna run repeats about 4 failing commands (about 28 s in 18 h) | Accepted: S-4/S-5 exception, cost measured; R1/R2 reopen it |
| R1/R2 unreachable or already met (the +2 case is an Until Loop path) | Mitigated: scoped to ShipLoop callbacks, the +2 case named and excluded (vendored argv, U1); R1 fires on any replication |
| Renaming the run directory improves the numbers without changing behaviour | Rejected: no rename step; a clean run is uninformative unless it meets the typing volume |
| The frozen script drifts from `metrics.collect` or mislabels a class | Mitigated: one-time, header says superseded; classes keyed on line-anchored text; Claude exit-0 refusals accepted as a stated lower bound |
| M1 counts a source `cat` of navigator text, or Claude rows jump from 0 to real counts and read as a regression | Mitigated: anchoring plus the fixture's third case; the journal marks pre-M1 Claude rows unmeasured, baselines.jsonl is not rewritten |
| LEARNINGS.md, run.py and 4 more files already conflict between f3 and origin/main | Accepted: one hand-resolved merge for the batch; the new section goes in after it |
| [Item C] a pre-upgrade callback in context or on disk meets argparse "unrecognized arguments" with no hint | Accepted: the old packet's Recovery line (`next`, no flags) still works; no shim (one supported version); tested by the stale-flag test |
| [Item C] only the derivable flags go; `--run-dir` stays typed (1 of the 3 callback typos) | Accepted: it reduces occurrences, it does not remove them |
| Option: shorter or relative paths | Rejected: S-6 standalone packets; breaks saved runs |
| Option: env var, alias or command file | Rejected: a fresh login shell per codex command makes a variable another typed path; a fixed-name file loses the `--action` guard (S-1) |
| Option: infer the run dir | Rejected: workspace runs are not found by walk-up, runs left active break "exactly one" (S-1) |
| U1 Until Loop script paths (7 of 62 commands, 5 in session 1, each repaired next call, one +2) | Accepted: vendored argv, outside Item C |

## Verification

1. `cd /private/tmp/claude-501/-Users-dadleet-src-skill-craft/f7d9360d-b88d-417b-8773-fc5b3eee6419/scratchpad/final-plan && python3 collect.py 2>/dev/null; echo collect=$?; python3 classify.py > classify.out; echo classify=$?; grep -E '^TOTAL|path-typo|bare CLI|wrong install|content|other' classify.out`
   - Confirming result: `collect=0`, `classify=0`, `TOTAL 41`, and classes 4/7/7/4/15/4.
   - collect.py writes the records.json that classify.py reads. Any rise is a finding.
2. After step 1: `python3 /Users/dadleet/src/skill-craft/.claude/worktrees/next-batch-eb98fc/docs/experiments/shiploop-callback-failures-20261004/callback_failures.py --root /Users/dadleet/e2e-runs --cutoffs <dir>/failures.json --out <scratch>/again.json; echo rc=$?; cmp <dir>/failures.json <scratch>/again.json; echo cmp=$?`
   - Confirming result: `rc=0`, `cmp=0`.
3. `grep -c '20261003/ v1161' /Users/dadleet/e2e-runs/20261003/v1161-battleship-luna/events.jsonl`
   - Confirming result: 15 (09:57 snapshot).
   - For each other run's events.jsonl, `grep -c '20261003/ '` gives 0. A non-zero count refutes "one run only".
4. `python3 -c "import json;print([len(json.load(open(f'/Users/dadleet/e2e-runs/20261003/{d}/metrics.json'))['shiploop_failures']) for d in ['hello','seat-reservations','v1161-hello','batch-sonnet/hello','batch-sonnet/seat-reservations','batch-sonnet/battleship','batch-sonnet/battleship-scoring']])"; echo rc=$?`
   - Confirming result: `[0, 0, 0, 0, 0, 0, 0]` and `rc=0`, against 15 failing Claude commands (the blind spot).
5. `git -C /Users/dadleet/src/skill-craft/.claude/worktrees/next-batch-eb98fc grep -n -e '--result' -e '--opening' -e '--message' origin/main -- skills/shiploop/scripts/shiploop_protocol.py` shows the three required flags (item 6). `git -C /Users/dadleet/src/skill-craft/.claude/worktrees/next-batch-eb98fc show origin/main:test/shiploop_e2e/hosts.py` shows `ClaudeHost.plugin_cli` (the 7c1f1014 fix).
6. M1, from the worktree root: `python3 test/shiploop-e2e.test.py; echo rc=$?` gives `rc=0` with the new case. Then `python3 test/run_suites.py --group quick --changed-from origin/main; echo rc=$?` gives `rc=0` (capture the code before any filter). Live confirmation: the next Claude run's metrics.json lists its real refusals.

## Rollback

Steps 1-4: `git -C <repo> revert <sha>`; the journal section is edited with a reason, never deleted. M1: revert its commit; Claude rows go back to unmeasured and the journal says so. Item C: revert the source commits and release again. No shim is kept, so runs started on the changed version finish on it.

## Open questions

1. Build Item C on S-4/S-5 hygiene alone, without R1/R2? The plan assumes not (cost against about 28 s per long run). Owner call.
2. An Until Loop wrapper verb (S-5) for the 7 of 62 script-path errors: not planned; wanted?
3. Land the journal commit before or after the f3 merge with origin/main (step 2)?
4. Does baselines.jsonl need an explicit "failures unmeasured" marker for pre-M1 Claude rows? Decide at M1 admission.
