# Harness batch 2026-10-09: measuring what the E2E runs are for

Status: **designed and adversarially audited (ten agents: one designer and one auditor per group); implementation in four worktrees.**
Owner question (2026-10-09): based on what the SDLC runs taught, what remains to think about, consider, measure differently or evaluate by
changing the harness; make the changes, then run the test. The Battleship, Checkers and chess builds are examples of the ShipLoop SDLC, so a
harness change is judged by whether it lets the run say something true about ShipLoop (SPEC S-1..S-14, the main tenet), never about one app.
Evidence: `docs/experiments/batch-1011-harness-design-audit-20261009/design-audit.json` (every design with its audit). Basis: origin/main
`923a3bd6` plus the shared reader `test/shiploop_e2e/runrecord.py` (this commit). Harness-only: no skill, so no release.

## What the nine saved round runs showed the harness cannot yet say

1. Whether each stage's declared check really ran, and whether it ran anything (null test counts passed as evidence for two releases).
2. Whether the packet alone re-orients a model with a cleared context (S-6 gates every future packet shortening; no probe was ever run on purpose;
   the two recorded "fresh starts" were accidents, and one re-read five product files and ran `node --test` three times).
3. Whether two numbers are comparable at all: build, plugin tree and host build were unrecorded, a blocked run was a baseline, a regrade looked like
   a resume, and a run that two hosts worked on (r2 Grok, finished by Claude) carried one host's label.
4. Whether the environment or the process caused a failure (Chrome over loopback fails in the Grok host only; overlapping runs were inferred, not recorded).
5. Whether the delivered product is good (tests that pass beside a mutation survival ratio and a hand-written acceptance that the model never saw).

## Dispositions (design verdict / audit verdict, then what is built)

Every audit approved with corrections; the audit's `safer_alternative` is the scope. The common correction is the owner's rule *unmeasured is
unknown, never zero or pass*, and the SPEC rule that a scorecard row is a record and not a verdict until a style has a baseline.

| Group | Verdict | What is built | What is deferred, and why |
|---|---|---|---|
| G1 fidelity record (F1) | implement / approve with corrections | `fidelity.py`, a record-only block in `metrics.json` only (not `result.json`): evidence class per accepted action with a `note` split and a records list; the verify-record audit (a focused or regression row with `counts: null` is *unmeasured with the reason*, never pass); script-owned edits and name-pattern kills as listed facts (new detectors unwrap `sh/bash/zsh -c/-lc`); refusals with a full-line repeat flag; end-state fields (`blocked_by`, `awaiting`, `unverified`). Every part fails open (an incompatible or missing stage table is recorded in `unmeasured`); heuristic rows need tool calls seen > 0. At most 5 printed lines, from `run._main`. | The eight-row pass/fail clauses table (S-10 false-fails 2 of 11 runs, S-9 passes null counts, S-4 passes beside wrapper glue, S-15 contradicts the SPEC); producer-packet scoring (the exporter already records `carried`); the authors histogram; the result.json copy. Added later in found/none-found vocabulary. |
| G2 clear-context re-orientation (F2) | implement / approve with corrections | Phase 1 only: `sessions.jsonl` (start and end rows, `told:{cli, run_dir}` as values, engine revision and last accepted action at each end); `ToolLog.feed` extraction; pure `metrics.reorientation` (calls, seconds, first grounding call, calls before it, exact or mistyped by resolved path, window failures, `rewrote` labelled a lower bound); passive `fresh_starts[]` in `metrics.json` for every fresh start and every Grok/Codex compaction; `per_stage` emits no `context` for a stage with no events and counts Grok calls; a README watcher recipe that creates `<out>/stop` at a stage boundary. | `--clear-at` and its kill logic (decide from the first live probes whether the watcher's up to 2.25 s overshoot matters; this reverses a deferral recorded in README/LEARNINGS only if built); the redo measure (after three live probes); a verdict named anything but `continuity` (it cannot fail on a live run, so it never stands in for S-6). |
| G3 identity and variance (F3) | implement-smaller / approve with corrections | Optional identity fields on row and result (`plugin_sha256`, `prompt_sha256`, `host_build`: Claude from its init event, Grok and Codex from the first stdout line of `--version` probed once at launch and written on the launch record, never at report time, so null for old Grok/Codex runs; G4's per-launch `environments` read it from there, `started`/`ended`, `planning_seconds`, `local_head`); one `matching_rows` behind `scan_baseline` and `previous_row`; a subject run that did not reach `done` is never compared; the existing `baseline vs` line annotated with facts (plugin tree same/different, host build change, `n` rows on `k` builds); read-only `--baseline-report [--runs DIR ...] [--json]` that unions file and folders and classifies by `versions.regraded`, observed process, `earlier_terminations` and `runrecord.mixed_host`; `docs/experiments/baseline-spread-20261009/runs.json` generated by that command; the Grok `available_commands` start count fixed as its own change. | The `spread` block in `result.json` and the `_main` reorder (no reader yet), `--repeat` (a shell loop is sequential), `harness_sha256`, and any within/above/below claim or `MIN_EARLIER_ROWS` (the floor was wrongly attributed to the owner; at n=3 a new run falls outside the range 2 times in 4). |
| G4 environment and product at stop (F4) | implement-smaller / approve with corrections | `product_at_stop` (replaces `shiploop.worktree_checks`; fixes the dropped returncode); a process-free `environment` block (node/python3/git versions, cpus and load at start and end, `display_hold`, `hosts_used` and per-launch `environments` from `runrecord`, end-of-run `overlap` read from sibling folders' `timeline.jsonl`); a browser capability record only when a case or `--need` declares it (`--browser-bin` for tests; success is the page title on stdout, the group is killed after the title plus a short grace; record only); `outcome_class` limited to PASS, FAILED, BLOCKED, STOPPED, null (paused and halted defined) derived from `termination_facts` plus the blocked detail; `--resume-run` defaults host, model and effort from the run's own record and refuses a silent host change. | The ENVIRONMENT-SUSPECT overlay (no recorded run can be suspect; a correct probe passes on the three runs that motivate it); `unverified`; a start-time `other_harnesses_alive`. Probe the real browser 10 times from Terminal and from a Desktop task and journal the rates before deciding on any overlay. |
| G5 delivered quality (F5) | implement-smaller / approve with corrections | `planning_review` and the improve-skill path as a first-class option on named cases (the `none` runs were case `custom`, so they would get no quality block); `quality.py`: JS mutation on a copy under `<out>/quality` (one documented time ceiling, round-robin file order, baseline gate with test count, groups in `LIVE_HOST_GROUPS`, `TERMINATION` checked between mutants, getpgid guard, per-file site counts) and Checkers-only held-out acceptance with an off-board item and a calibrated hermetic reference server, kept out of argv; `result.json` written first and updated; the phase runs only on a finished, committed delivery; hosts taken from the run's sessions; a Claude memory-write detector computed from `events.jsonl`. | The UI observation (until it can click through CDP), the Battleship acceptance set (5 of 5 pass: no information), port-serialising leases and `CLAUDE_CODE_DISABLE_AUTO_MEMORY` (owner decisions), the argv exec scrub (document only), a second overlap record and a second kill-by-name count (G4 and G1 own them). |

## Rules for every group

- SPEC edits in the group's own earlier commit, dated 2026-10-09, with the change-admission anchor, the non-regression statement and dispositions.
  Cite SPEC rows as the audits corrected them: `environment` to S-12 and "Concurrency must not change a verdict", `product_at_stop` to S-11,
  `outcome_class` to S-14, a model's account of a blocked result is a judgement S-9 excludes as evidence.
- A failing hermetic test before each behaviour; real-git tests isolate Git config (`isolate_git`); no test touches the machine's real listeners or
  processes other than its own child groups; no test pins a live `baselines.jsonl`; pin the committed extracts only. Hand-run tests need
  `SHIPLOOP_PROGRESS=off`.
- Do **not** add tests to `test/shiploop-e2e.test.py`: it measures 118 s locally against `QUICK_MAX_SECONDS` 120. New tests go in the group's own
  `test/shiploop-e2e-<topic>.test.py`, registered in `test/suite_catalog.py` (suite list, duration) with the pinned counts in
  `test/test-groups.test.py` raised to match (a new top-level test file that is not registered fails every CI group).
- Shared reader: `test/shiploop_e2e/runrecord.py` (`launches`, `hosts_used`, `mixed_host`). A mixed-host run is named the same way everywhere and kept
  out of every baseline cell. No second implementation.
- Unmeasured is unknown, not zero: a field is null (with the reason) when its source is missing; `[]` only when measured and empty.
- Hosts: Claude, Grok, Codex runs on disk are replay fixtures (reduce to compact extracts under `test/fixtures/`); Hermes never.
- Process safety: no kill by name pattern; never signal a process the test did not start; a run that starts a child registers its group.
- Commits on prompts: none here (the harness has no packet text). Each commit message states the evidence (run, count, file) and the audit item it fixes.
- Journal each group's result in `test/shiploop_e2e/LEARNINGS.md` in the same commit as the result; hand result shapes to the Run Review session
  (`outcome_class`, `hosts_used`, `environments`, `overlap`, `product_at_stop`, `fidelity`, `fresh_starts`, `quality`, mixed-host and lower-bound markers).

## Order, tests, verification

Worktrees from the plan commit: **m** G1, **n** G2, **q** G3, **o** G4, **p** G5, implemented in parallel and merged one at a time. Per group: SPEC commit, fail-first tests,
implementation, adversarial review, fixes, reverify. Merge m, n, o, p into one branch (conflicts are expected in `suite_catalog.py`,
`test-groups.test.py`, `SPEC.md`, `LEARNINGS.md`, `run.py` and `metrics.py`; keep both sides), quick and full tier, push (no release).
Then the new harness runs on a real case: the S-6 pair (a cleared context after a stage boundary, and inside a stage) on a cheap case, one run at
a time, then one Checkers and one Battleship run to read the fidelity, identity, environment and quality records. Results go to the journal and to the
Run Review session.
