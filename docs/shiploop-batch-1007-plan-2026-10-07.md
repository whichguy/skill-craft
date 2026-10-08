# Batch plan 2026-10-07: correctness, stage clarity, read-back audit, run-review cards

Status: **audited 2026-10-07 (three reviewers: blast radius, feasibility, tenet/owner rules); revised below**. Process (owner): plan every change, audit it, resolve the unknowns, build the whole batch, then test.
Live verification runs are launched without asking (owner, 2026-10-07). Every change is judged by the main tenet (README top, SPEC S-6):
a model holding only the next packet knows what to do, how it is checked and where the run stands; repetition between packets stays.
Scripts navigate the graph from the ledger (`state.md` is the single authority); nothing here moves that to the model.
Evidence: `docs/lifecycle-review-2026-10-07.md`, `docs/planning-time-analysis-2026-10-06.md`, `docs/experiments/grok-none-battleship-20261006/`,
`docs/experiments/gas-battleship-audit-20261006/`, fixtures `docs/experiments/batch-1007-fixtures/` (real `node --test` output by reporter).

## Items

| Id | Change | Why (evidence) | Files | Fail-first test |
|---|---|---|---|---|
| B1 | Test counter reads `node --test`: the spec/default reporter (`ℹ tests/pass/fail/skipped/todo`), TAP (`# tests ...`), ANSI stripped; the `dot` reporter and junit have no countable summary and are refused as uncounted with the remedy "use the spec or tap reporter". Skip detection by runner syntax (leading skip glyph `﹣`/`○`/`-`, trailing `# SKIP`/`# TODO`, summary lines), never by a word in a title. | `counts: null` for `node --test` in every Grok record; `min_tests` never enforced; a passing test titled "pending cell" counted as missing and refused `complete` at system-test (run 20261006 Grok). | `skills/shiploop/scripts/shiploop_test_counts.py`, `test/shiploop-test-counts*.test.py` | Real outputs from the fixtures: spec, tap, dot, a title containing pending/skip/todo on a passing line is `shown`; a `﹣ ... # reason` line stays missing; ANSI-wrapped output counts the same. |
| B2 | Suite-membership drift: an id declared by a system command appears in the output of an inner or regression command; record it and refuse `complete` at system-test with the remedy to guard or move the file. | The delivered repo's plain `node --test` ran the two Chrome cases and needs macOS Chrome; three review passes and every gate passed it. | `shiploop_test_loop.py` (verify records), packet text for system-test | A fixture where a regression run prints a system id is refused; the same id in its own system command passes; a focused id legitimately repeated in regression passes. |
| B3 | `release-verify` runs the consumer checks in the returned source checkout for a source-return release. | `tests/*verify1.md` cwd is the work area, so the script proof does not observe the product the user receives. | workspace return and release-verify code (to locate in audit) | A return fixture where the check passes in the work area and fails in the returned checkout is refused. |
| B4 | Docs and prompt corrections. README: `skill-assess` described as the reuse/update/create decision (not "captures learnings"); the opening paragraph no longer says the conversation clears at `select-work` (the prompt says do not clear); the default one-pass Backchain loop and `--backchain-passes`; supported test runners incl. node:test and the skip rule. SKILL.md: the "iteration 4 that still fails stops it" sentence removed (the loop has no iteration limit); runner list. | Verified contradictions (lifecycle review, README audit). | `skills/shiploop/README.md`, `skills/shiploop/SKILL.md` | Existing doc-pin suites stay green; a new check that SKILL.md and the loop contract do not both state a limit and no limit. |
| B5 | Rename stage `select-work` to `get-next-work-item` (identifier, packet text, status and report labels, docs, tests, exporter, audit-harness replay). Saved runs recorded with the old name are refused with a clear message (one supported version). Historical committed evidence keeps the old name. | Owner request; the name should say what the stage does. | engine: `shiploop_stage_spec.py`, `shiploop_prompts.py`, `shiploop_navigator.py`, `shiploop_planning_context.py`, `shiploop_navigator_dry_run.py`, `references/*`; tests (about 10 files); `skills/shiploop-run-review/scripts/export.py` + `template/index.html`; `skills/shiploop-e2e-audit/harness/{dag_replay,behavior_capture}.py` | The stage list, the dry-run graph and every packet use the new id; loading a saved run with `select-work` is refused with the message. |
| B6 | Skill stages (option C): when the item touches no skill surface, the script writes the concrete N/A disposition for `skill-assess` and `skill-validate` with no model turn; when it does, both run as today. Skill surface is defined once in `path-classes.json`: `SKILL.md`, files under a `skills/` or `agents/` directory, and the repo's skill index files. | 5 of 5 item-runs were model-written N/A; README requires a recorded N/A, never a missing stage. | `shiploop_navigator.py`, `references/path-classes.json`, prompts for the two stages | An item with no skill path advances both stages by script with the N/A recorded in the ledger; an item with `skills/x/SKILL.md` in its paths gets the model packets. |
| B7 | Settled-fact lines: `plan` states each item's module format and loadable seam; `test-strategy` names and probes the tool for every host-browser case and states which commands may print which ids. | Plan said ESM with no package.json; browser tool unprobed (Luna escapes 165.9 and 123.4 min). | `shiploop_prompts.py` (plan, test-strategy) | Packet text contains the lines; the packet-completeness test (B12) stays green. |
| B8 | Record the retry loop's state path in the ledger when the loop starts. | A fresh agent cannot find the loop after a clear (S-6 gap). | `shiploop_navigator.py` / test-loop start | After start the ledger names the path; a resume fixture reads it. |
| B9 | Plan-shape measure (record only): work items, requirement ids and declared files per item, shown in status and the export; a warning, not a refusal, when one item owns every requirement and more than one file. | Sonnet planned one item holding rules, server, page and tests; Grok planned two. No threshold is invented. | `shiploop_navigator.py` (plan accept), export | A one-item plan with several files records the warning; a two-item plan does not. |
| B10 | Record register and read-back audit: `references/record-contract.json` lists every record kind with its writer, its readers (script function or stage) and whether it is authoritative or derived; `shiploop audit-records --run-dir` (record only) reports kinds that have files but no declared reader, and with a host events file the model reads per kind. The exporter includes the result. | Notes written 9 times and never read; 88 lint files with no model read; the owner's rule that nothing is written and abandoned. | new `shiploop_record_audit.py`, `references/record-contract.json`, export | A fixture run with an orphan kind is flagged; the real three runs are audited and each finding is fixed or the reader declared. |
| B11 | Run Review stage cards (handoff to the Run Review session): for each stage visit, the stage purpose and exit-check kind, the packet sent (head, size, link), the output written back (result summary, file, size), time, refusals and the read-back state. | Owner request; the page already has the packet box (R17). | `skills/shiploop-run-review/*` (fork) | Fork's tests. |
| B12 | Packet-completeness test (hermetic, no model): every stage's packet states its purpose, how the stage operates, how the result is checked or reviewed, what it must produce and the recovery command. | The tenet; no automated check exists. | new test in `test/` | Fails today if any stage packet lacks one of the five. |

## Not in this batch
Merging test-red, integrate, release-check; script-first test-green and regression (S-10 decision); packet or ledger de-duplication that moves
grounding out of a packet (withdrawn under the tenet); the Backchain pass itself; the default planning-review flip.

## Unknowns, with state
Resolved by read-only probes: (U1) no clear mechanism depends on the stage name `select-work`; only 5 code uses (stage list, two navigator
conditionals, packet text, display group); (U2) `path-classes.json` has no skill class, so B6 adds one; (U3) `node --test` prints
`ℹ tests/pass/fail/skipped/todo` by default when piped and `# tests ...` in TAP on Node 25.9, `dot` prints only dots; skipped lines start
with `﹣` and end `# reason`, todo lines end `# TODO`; (U5) stage names live also in the Run Review exporter and template and the audit
harness replay code; historical evidence rows keep the old name.
Open (the audit and the build must settle each): (O1) older Node versions (only 25.9 installed) may print different summaries, so the reader
must refuse what it cannot read; (O2) whether a protocol-version bump is needed or a refused unknown stage is enough for B5; (O3) where the
returned checkout path is available to release-verify (B3); (O4) whether a stage can be script-completed today (B6) or needs new engine
support; (O5) whether the vendored Until Loop runtime prints its state path at start (B8); (O6) whether the requirement-id to item mapping is
machine-readable in the plan (B9); (O7) script-side reads cannot be measured from host events, so B10 declares them from source and the
declaration can be wrong; (O8) the hard-coded names in committed baselines and evidence when the rename lands.

## Order, tests, verification
Build in one worktree with a failing test first for each item and one change note per skill touched: B1+B4 counter and docs, B2, B3, B5,
B6, B7, B8, B9, B10, B12, then B11 by the Run Review session. Test: the quick tier on every group of commits, the full tier before the
release; then live runs, launched without asking: Sonnet (checks on) and Grok (checks off) on the Node Battleship case from the build
(checkout source), the Grok run with the host killed once at a stage boundary and once inside a stage (the harness resumes it with a fresh
context, which is the clear-the-context probe). Expected: no `uncounted` or title-word refusal, stage name `get-next-work-item` in the
ledger and the export, the two skill stages script-completed, the read-back audit with no orphan kind, planning near 22 minutes (Grok, checks
off), the delivered repo's plain `node --test` independent of Chrome. A release is the owner's decision; after it, the same runs by the
marketplace route.

## Audit outcome (2026-10-07): what changed in the plan

Three read-only reviewers (blast radius a0be366b, feasibility a553ffdb, tenet and owner rules abb29bce) checked every item against the
code and the records. Dispositions, each with its reason:

| Item | Disposition | Reason (evidence) |
|---|---|---|
| B1, B4 | **Built** (c38f6887) | TAP double-counted through the Go reader; the plan's "leading dash" rule would have matched Go `--- PASS:`; a load failure printed `tests 1 / fail 1` and read as a test that ran; the regression command with no ids still passes uncounted, so "dot is refused" holds only for focused commands. |
| B2 | **Deferred; replaced by B7 guidance** | System ids are declared at `system-test-author`, after the inner runs, so the check can only live at `system-test`; verify records keep a 6000-character tail; no field separates a host-dependent case from a legitimate repeat in the regression suite, so "id in regression output" would refuse repos whose default runner includes integration tests. Needs a declared marker (schema change): an owner decision, not a quiet add. |
| B3 | **Deferred, owner decision** (superseded 2026-10-08: built as a clean copy of the returned result, see "B3 built" at the end) | Release-verify may run before the return (`workspace return` is allowed only at release or handoff); checks would run in the user's real tree; nothing broke in a normal run. |
| B5 | Keep, atomic with the Run Review exporter alias; retired-stage message in `retired_run_reason`; no protocol bump | 56 files, 156 hits, 15 test files; the exporter's `PHASES`, `template/index.html`, `dag_replay`, `behavior_capture` and the dry-run WORK3 literal also carry the name. Saved runs are already refused with a bare "unknown navigator stage". |
| B6 | **Deferred** | `skill-assess` also decides create/update/helper/MCP/library cases, so a skill-path predicate silently drops them; a new path class must sit before `docs` and be non-behavioural; evidence is 5 of 5 N/A on one product (about 1.6 minutes per item). Revisit with a second product. |
| B7 | Keep: module-format/seam line and a host-dependent-case line (name and probe the tool; state which commands may print which ids) | The seam line is supported by the 165.9-minute missing-module escape; the browser-tool half rests on the Chrome-dependent `node --test`. Guidance only; no script check. |
| B8 | **Replaced** by correcting the stale packet text that tells the model to save each packet to a "printed latest-packet path" that is not printed | The Until Loop runtime already writes every packet, with `state_file`, to the printed `--receipt` path; the engine never starts the loop, so a ledger write has no hook. |
| B9 | **Dropped** | Work items carry only id, title and context; requirement ids and paths exist later, per item, at step-plan; the threshold rested on two plans. |
| B10 | **Shrunk** to a one-time register document with verified readers, no CLI verb, no exporter change | A declared-from-source audit passes by declaring a reader; the notes it would flag are the recovery aids the tenet wants. |
| B11 | Fork owns it; after B5 | Must handle visits with no packet and run the exporter privacy screen. |
| B12 | Keep, widened | Improve-phase packets (release-plan, system-test-author, planning stages under `--planning-review stage`, carry-forward on the last item) lack Goal, Done-when and a Result template; "how checked" is missing or generic in 13 to 22 of 34 stages. The test fails first, then the prompts are completed. |

## B3 built 2026-10-08 (batch 1008, worktree b1008b): release-verify observes the returned result

**Question.** Release-verify's done-when is "observed where consumers use it", but `test_loop.verify` ran the recorded consumer checks with the
work area as cwd. A check could pass on files the return excluded, on an ignored file or on a later commit while the user received something
else (the 2026-10-07 deferral above). The owner's literal wording was "the returned source checkout".

**Evidence (status firm unless marked).**
- All 10 recorded runs that have a `return-receipt.md` under `/Users/dadleet/e2e-runs/*/*/.shiploop-runs/*/` are `fast-forward-merge` from
  `start_clean: true` (scripted count, 2026-10-08). Their release-verify test records have cwd the work area (the audit read all ten; the batch
  plan cited four). 5 of the 10 wrote the source's absolute path into `consumer_checks` (20261003 hello and seat-reservations, 20261004
  v1190-hello-sonnet and -2, v1200-hello-sonnet; recounted by script 2026-10-08), so those commands ran in the user's tree whatever cwd
  `verify` used. This is natural model behaviour, not adversarial; it is documented, not blocked, because blocking the path would also block
  legitimate read-only checks such as `git -C <source> cat-file -e HEAD:<file>`.
- In the 3 recent completed runs the return was made at `release`, so release-verify ran after it and each model then observed the returned
  checkout by hand; a hand observation is not script evidence (S-9).
- The user's tree cannot be the place the checks run: `_source_result_matches` demands an empty `git status --porcelain=v1
  --untracked-files=all` in the source for a fast-forward receipt, so any file a check writes there (cache, log, build directory) makes the
  receipt non-current, `follow_up_knowledge_return` and `execute_return` refuse the source as drifted, and the lifecycle card forbids deleting the
  user's files to clear it. The work area has a route out; the user's tree has none. (Corrected statement: after a fast-forward receipt a
  follow-up return needs a clean candidate, so pollution of the work area is removed from it, not excluded; the conclusion holds because the work
  area is the run's own to clean.)

**What was built (this commit; baseline origin/main 8a198cdd; related earlier work ba908889 B2, 49e7779b, 2cb2a9e4, bf958708, 44427a98).**
`workspace.returned_result` reads the newest receipt (no write; a manifest or receipt it cannot read raises) and `workspace.export_returned_result`
writes `<workspace root>/consumer-check` from the receipt's tree (`expected_source.tree` for a fast-forward, `.working_tree` for the other two
kinds) with `git read-tree` into a private index and `git checkout-index --prefix`, run from the execution worktree (shared object database).
`test_loop.observation` decides where release-verify's commands run: `returned-result` (the copy; cwd the copy and `GIT_CEILING_DIRECTORIES` the
workspace root, so a parent repository is not found), `work-area` (no completed return: unchanged behaviour, labelled, never refused, because
`workspace return` is allowed only at release and handoff), `in-place`, or `unknown` (the return state cannot be read: every command is
`could-not-run` with the error, an existing exit, never a silent fall back to the work area). The record gains an optional `observed` key and the
handoff packet renders one line from it, so a cleared handoff model can report it (the audit's required correction: the handoff duty pointed at a
record the packet never named).

**Rejected.** The user's real tree (above). Refusing done when no receipt exists (a dead end: the stage cannot return). Allowing return at
release-verify (changes the return gate for a case 3 of 3 runs avoided). Running in the work area after checking it equals the receipt (cannot see
an excluded or untracked file the check needs). `DUTIES['release']` edit (no evidence of need: all 10 receipts were made at `release` unprompted,
and it sits against the "do not return early" text). A per-check work-area marker and a record-only flag for commands that name the checkout by
absolute path (add only if a live run shows false refusals or the escape matters).

**Measured.** Export recipe on this repository's HEAD (8a198cdd, 3,922 files, 35.1 MB), 2026-10-08: `read-tree` 0.01 s plus `checkout-index`
0.34 s, total 0.36 s, `git status` unchanged. One point on one machine; large repositories are unmeasured and stay unknown. The export runs before
the stage budget clock starts and each git call is bounded by `SHIPLOOP_GIT_TIMEOUT` (45 s).

**Tests (all hermetic, real git in temporary directories; fail-first against the unchanged tree).** `test/shiploop-workspace.test.py`: the B3
fixture (a file the return excluded makes the check pass in the work area and fail on the result), no-return labelling for three phases, the
safety test (a check writing `polluted.txt`, `run.log`, `__pycache__`, `out/` leaves the source's index, HEAD, status and files, the object database,
the work area and its private index byte-identical and the receipt current), the export for each return kind (fast-forward, working-tree, clean and
dirty no-change) against `git ls-tree -r` with modes and symlinks, read-only export with `export-ignore` ignored and `eol=crlf` applied as in a normal
checkout, replacement of its own copy and refusal of a symlink or file at that path, export failure and corrupt receipt and absent manifest as
could-not-run (display never raises), retry with done for a cause that is not the delivery, an ignored file a check needs, a workspace under a
parent repository, the newest receipt after the knowledge follow-up, and a commit after the return. `test/shiploop-test-loop.test.py`:
`ReleaseVerifyReturnedResultTests` drives the real `dispatch` (real Until Loop, knowledge gate, return): refusal with the copy text, then `replan` with
a work item accepted through the same gate, and the handoff packet line for a returned and an unreturned run. `test/shiploop-guidance.test.py`:
`ConsumerCheckLocationTests`.

**Open, with status.**
- False refusals from checks that depend on unmanaged files (installed dependencies, build output, `.venv`, `node_modules`, `.sf`/`.clasp` local
  config, git metadata): **interim, unverified.** A live dependency-bearing run is *unachievable now* because no E2E case has dependencies; a
  replay over the 10 recorded runs can only show no regression, because every recorded product is zero-dependency or names the source path. It
  leaves the false-refusal rate unknown. Hermetic fixtures prove the refusal names the cause and that a check which brings the file passes. The exit
  for a dependency-bearing product is `replan` with a check that brings its own install, which costs a corrective work item (cost unmeasured).
  Trigger for the per-check work-area marker: one false refusal in a live run, not before.
- Return kinds: only `fast-forward-merge` has a live run (every recorded receipt); `working-tree-return` and `no-change-return` are validated
  another way (real-git fixtures). A live `working-tree-return` is reachable (an excluded untracked file in a clean start forces it, per
  `test_ordinary_untracked_output_prevents_committed_candidate_fast_forward`), so the case is not closed until one E2E case leaves such a file.
- After a replan the receipt is stale until `release` returns again; the refusal and the replan context say so, and nothing makes the script
  ensure the model re-returns. Whether models do is for the live run to show.
- Whether models keep observing by hand inside the user's checkout and leave files there: the release-verify duty asks them not to; the live
  Sonnet run must show an empty `git status --porcelain --untracked-files=all` in the source after release-verify and a completed handoff.
- The Run Review session may want `observed` on the stage card; the key is additive and optional (nothing under `skills/shiploop-run-review`).

**Owner decisions this needs.** (1) Accept "a clean copy of the returned result" as the reading of "the returned source checkout". (2) Accept
label-only (no refusal, no handoff re-run) when release-verify precedes the return. (3) Whether a re-observation at handoff (B3b) is wanted later: it
would add handoff to the rerun stages when the release-verify record says work-area.
