# ShipLoop E2E-driven fixes: validation — 2026-09-17

Implementation and verification are complete. The isolated live smoke passed
its intake boundary, and the receipt-path clarification it exposed passed its
focused regressions afterward. Test claims below distinguish the frozen live
candidate from the final wording and concurrent shared-checkout changes.

## Implemented production changes

- Empty initial commits can enter a workspace without a README workaround.
  [shiploop_workspace.py — `_snapshot_tree`: copied-index capture uses `git add -u`](../skills/shiploop/scripts/shiploop_workspace.py).
- Identical prompt text does not authorize recovering an old request. Direct
  init and public workspace-start tests cover separate active v2/v3 runs and
  non-mutating explicit recovery.
  [SKILL.md — entry identity: new request versus recovery](../skills/shiploop/SKILL.md).
- Packets distinguish requested runtime requirements from assumptions, permit
  target-compatible local evidence, and preserve unresolved compatibility gaps.
  [shiploop_navigator_v3_prompts.py — COMMON: runtime fidelity](../skills/shiploop/scripts/shiploop_navigator_v3_prompts.py).
- Verification and handoff packets reconcile selected cases as passed, failed,
  blocked, not-run, or justified N/A. Structural source/HTTP/DOM evidence cannot
  substitute for a selected rendered interaction.
  [shiploop_navigator_v3_prompts.py — selected-case reconciliation](../skills/shiploop/scripts/shiploop_navigator_v3_prompts.py).
- Actual Improve handoffs request compact candidate/scope, reviewer availability,
  reused-evidence applicability, findings, checks, limits, and recovery locators.
  Cold-recovery tests retain those duties and the selected child binding.
  [shiploop_navigator_v3_prompts.py — `improve_prompt`: review notes](../skills/shiploop/scripts/shiploop_navigator_v3_prompts.py).

The DAG, callback schema, and actual Improve ownership were not changed by this
fix slice. Prompt tests prove rendered instructions and recovery continuity;
they do not prove model adherence or game correctness.

## Provenance and checks

The source baseline was
`9a983ab4c32e5841f1cfe13b39908fd687ab56a520faac1808867d708f82080b`.
The production candidate is
`b6cec732ec4941b6b10783da1f983ce9b7f1678d13cbfefcefb4a2141fb702dd`.
The before-copy and scoped production diff are retained under
external/private retained artifact (not included in this repository). Existing unrelated dirty work
was preserved. Generated ShipLoop plugin files were synchronized from source.

After that aggregate finished, concurrent work changed seven package files in
the shared checkout. Independent review found our fixes retained; focused v2/v3
navigator and actual Improve CLI tests passed again. The aggregate result is
still scoped to `b6cec732…`. The fresh smoke uses an exact copy of that tested
package in a disposable Grok profile, verified by `grok inspect`; it does not
freeze, revert, or validate all later shared-checkout changes. Its selection
receipt is retained in `isolated-skill-probe.json` under the artifact root.

| Check | Result |
| --- | --- |
| Real-Git before/after empty initial commit | Old snapshot fails with `cannot capture working tree with git add -u`; patched snapshot succeeds. Neither changes source HEAD/index or adds a file. |
| Focused regressions | Workspace 29; cross-run 8; navigator v3 9; navigator v2 34; actual Improve CLI 3 passed. |
| Full `bash test/run-all.sh` | Passed all 24 top-level suites in 2,081.8 seconds. Log reports 873 Python unittest cases plus shell/Node checks. |
| Ruff and plugin parity | Passed. |
| Fast mock suite on the production candidate | 32 tests passed in 2.92 seconds. |
| DAG replay | All ten scenarios passed their expected outcomes, including the intentional wrong-edge rejection. |
| Original observer apparatus | 187 tests passed in 94.80 seconds on Python 3.14.7; superseded observer verification is recorded below. |
| Final observer apparatus | 201 tests passed in 141.65 seconds; zero failures, errors, skips, or expected failures. |
| Final receipt-path clarification | Red-first current/cold rendered packet regression; navigator v3 9 and actual Improve CLI 4 passed after final wording. Ruff and diff checks passed. |
| Final fast mock suite | 32 tests passed in 2.60 seconds. |
| Historical parser corpus | All five fixture shapes preserved their attribution expectations; only the revalidated parser digest changed. Historical event/provenance hashes were retained. |
| Actual contamination replay | The new detector identifies both control-file calls at native event lines 205 and 247 in the original capture. |

The first aggregate attempt was intentionally interrupted to fix a review wording
issue before restarting. The first apparatus attempt selected Apple's Python
3.9 through PATH and failed on `zip(strict=True)`; the retained retry explicitly
uses existing Python 3.14.7. No Python or system Git installation was changed.
The E2E README now documents its Python requirement.

## First candidate live smoke: contaminated, retained

The unchanged Checkers creation prompt launched with `grok-4.6`, requested
`xhigh`, a 7,200-second cap, and an initially empty actual product CWD.
Grok selected the candidate package and successfully started a protocol-3
workspace, but it first created and committed a README. This only proves
ordinary nonempty-baseline startup; the separate real-Git regression proves the
empty-initial-commit fix.

The native capture proves successful reads of campaign `suite-manifest.json`
(event lines 205/211) and trial `manifest.json` (247/254), exposing the intake
stop boundary. Root stopped that exact private Grok process group with SIGTERM
at 21:42:38 UTC. No repair prompt or callback was supplied. The original runner
result remains `partial-smoke-failed`; the independent workflow audit marks it
invalid due to observed benchmark exposure. No stage was accepted before stop.

Retained evidence:

- `workflow-audit.json — observed control reads and claim limits` (external/private retained artifact; not included in this repository)
- `intervention.json — exact operator stop and reason` (external/private retained artifact; not included in this repository)
- `result.json — original trial outcome` (external/private retained artifact; not included in this repository)

## Observer correction and fresh smoke

The implementation moves default suite products outside campaign controls and
retains an opaque physical repo mapping for feature lineage. Direct and suite
nesting guards compare resolved paths, including symlink ancestors.
[run.py — `_new_suite_product_parent`: separate durable products](../test/experiments/shiploop_e2e/run.py).

Structured model tool inputs referencing campaign/trial controls or observer
source invalidate partial, full, and later grades. Absolute symlink aliases and
quoted shell paths are covered; model prose and tool output are excluded.
Missing/malformed control metadata or empty/malformed captured stdout cannot
establish clean observation.
[grok_adapter.py — `observe_control_input_references`: bounded access observation](../test/experiments/shiploop_e2e/grok_adapter.py).

Late grading also re-fingerprints the process-owned observer root against the
frozen identity and retained snapshot. An edited observer cannot promote an old
trial to a pass; prior invalidity remains invalid. Independent review found the
reported defects resolved.
[run.py — `_refresh_late_grade_observer_identity`: grade-time drift rejection](../test/experiments/shiploop_e2e/run.py).

The final observer identity is
`d4d57e9ea263118781c4827a7556da2579a4d52fb063415dd08796556b79e93a`.
Its observation is deliberately bounded: it is not an OS sandbox or proof of
absence of relative, encoded, or unreported access. Native read completion without
a numeric exit code is retained conservatively; the automatic invalidation uses
the observed input reference, not a claim that every attempted read succeeded.

The new `live-launch-isolated` smoke started at 22:26:20 UTC with the original
Checkers prompt, `grok-4.6`, requested `xhigh`, 7,200 seconds, and 1,000 turns.
The suite created a genuinely empty `p-*` CWD in a separate temporary product
parent, recorded in `suite-execution.json`. The selected package is the exact
tested `b6cec732…` snapshot in the disposable profile. It finished with
`partial-smoke-passed`: intake was accepted through its actual Improve child,
the next stage was discovery, and no later stage was accepted. The observer
stopped the private process group at that boundary. Model time was 732.50
seconds; total runner time was 771.38 seconds. Both source and observer stayed
stable, no capture was truncated, and no control-path reference was observed.

The run independently demonstrates actual selection/read/invocation of the
tested skill, workspace startup, producer submission, actual Improve runtime
and review activity, and the accepted child import. Other profile skills,
including Improve, were links to existing roots, not copied frozen packages.
Disposable authentication entries were removed after model exit; the frozen
ShipLoop source and all trial evidence remain available.

## Additional live finding: receipt path instructions

The first `improve-complete` at native event 2866 failed at 2870 with
`check reference escapes its expected root`. Its check evidence was under the
sibling `run/notes` directory. The importer correctly requires evidence files
inside the bound execution workspace. However, the packet said “absolute local
file references” and showed generic absolute examples without stating that root.

Within the same one-shot session, Grok inspected the rule, copied the evidence
under `worktree/.until-loop/reviews`, rewrote the receipt, and retried at
3039/3043 successfully. No observer prompt or callback was supplied. This
successful recovery is retained, including the original failure. The final
prompt clarification names the existing containment rule and workspace-rooted
examples; a current/cold-render regression checks it. The importer and its
path guards remain unchanged. The packet now names regular single-link,
non-symlink evidence files beneath the displayed execution workspace and uses
workspace-rooted examples. Current and save/load cold packets retain that rule.
This additional wording was written after the
passing smoke and is not claimed to have received a new live model run.
[shiploop_navigator.py — `_render_improve`: receipt containment instructions](../skills/shiploop/scripts/shiploop_navigator.py).

The trace contains 119 tool calls, including 26 terminal calls. Five reported
failures consist of four absent-file probes (intendedness unknown) and the
recovered receipt-path rejection. Terminal inputs contain 13 literal help flags
(seven for ShipLoop, six for Improve), including seven before child initialization.
This is an overhead pattern worth a future controlled prompt experiment; this run
alone does not establish that removing them would improve quality or duration.
No terminal token total is available from this intentionally interrupted prefix.

Retained evidence:

- `workflow-audit.json — full trace patterns, failure classification, and claim limits` (external/private retained artifact; not included in this repository)
- `result.json — accepted intake prefix and stable identities` (external/private retained artifact; not included in this repository)
- `control-input-replay.json — original contamination detected by the new observer` (external/private retained artifact; not included in this repository)
- `apparatus result.json — 201 no-model tests passed` (external/private retained artifact; not included in this repository)

Full generated-game behavior, complete fresh feature chains, and hosted delivery
remain separate efficacy experiments. A passing intake smoke cannot establish
them. See [fixes plan — scope, regressions, and follow-on experiments](shiploop-e2e-fixes-plan-2026-09-17.md).

The descriptive final shared-checkout package receipt is `f1ce283be453756078f1b71a5a172abbd4f1ce07dabe8ef8ada89931be0a067d`.
It includes concurrent work; the earlier aggregate result is not reassigned to
that revision. Changes remained uncommitted at that snapshot; the subsequent
standalone Improve review is recorded below.

## Standalone Improve review

The review freezes the 129-file E2E candidate at repository HEAD `0beaa6c` in an external/private retained artifact (not included in this repository). It preserves the
separate active Improve run and unrelated edits in the shared checkout.
Three pre-existing Ruff cache files in that initial inventory are excluded from
the commit and product return; the delivery scope contains 126 files.

The first review identified and repaired six additional harness defects:

- Successful protocol-3 `improve-complete` callbacks against a prior run now
  fail fresh-request isolation, including an idempotent callback alongside a
  new matching run.
- Candidate snapshots include ignored application source. Conventional runtime
  exclusions are explicit; tracked inputs, ordinary files sharing cache names,
  and symlink identities remain included. Copies report their omissions, and
  late grading rejects a changed ignored application file.
- Read-only Git evidence commands disable optional index refreshes. An
  index-byte preservation regression exposed the old `git status` side effect.
- Creating an excluded runtime cache is reported without changing candidate
  or verifier source identity. Application changes still change both hashes.
- Retained-trace fixtures require the exporter's actual provenance and v2
  shape, instead of accepting an empty provenance dictionary. Original prompt
  content stays omitted; schema validation does not authenticate local fixtures.
- Behavior capture recognizes the catalog's `refine` scenario kind, retaining
  the closed allowlist for unknown text.

The external adapter remains trusted test code. Endpoint hashes detect
persistent source drift, but cannot detect source changed and restored within
one invocation or authenticate semantic observations. That limit is now explicit;
no OS sandbox or new workflow engine was added.

Two independent reviewers supplied the first-cycle findings. Implementation
workers subsequently hit a model quota limit; root finished their saved edits
and retained that limitation in the review notebook. The original four defects
are reproduced against the frozen pre-review modules in
`cycle1-regression-red.log`. The current production check receipts cover 156
passing cases in eight suites; source/test byte hashes are retained before and
after those checks. Full apparatus and static-check outcomes are retained in
`cycle1-apparatus/result.json` (207 cases before the cache-presence correction),
`cycle1-apparatus-final/result.json`, and `cycle1-static-final.json` under the
artifact root. The cache-presence false failures are retained separately.
The actual Until Loop notebook records subsequent reviews, commit/return
receipts, and the evidence used for its final assessment.

These checks improve the test apparatus and preserve the earlier local live
observations. They are not new live Grok runs, complete game/feature campaigns,
or hosted-delivery evidence.

The second distinct review found an additional evidence-attribution defect:
a required failed check could override a stale binding or invalid artifact and
label the current product as failed. Invalid receipts now remain errors and
invalidate the trial; their original failed declarations remain available for
diagnosis. Existing trial invalidity also takes precedence over product failure.
Malformed receipt JSON invalidates a previously saved pass, while a corrected
receipt can still be graded against an otherwise intact trial.
The targeted red/green receipts are under `cycle2-receipt/`; the current affected
suite and candidate-applicability receipts are retained in the same artifact root.

The review considered, and declined, requiring an independent reviewer when none
is available: the bound Improve policy permits a disclosed self-review fallback.
The workflow assessment validates that declared evidence contract; it does not
establish independent semantic truth. This does not relax independent product
verification or permit a missing reviewer-availability record.

The third review tightened negative-evidence completeness: both passing and
failing checks now require a nonempty set of valid pinned artifacts, including
incremental review failures. Bare failure declarations no longer establish an
attributable product failure. The earlier permissive behavior is preserved in
red regression evidence under `cycle3-failure-evidence/`. Blocked and unverified
results can still record an unavailable observation. The documented fast mock
entrypoint separately passed 35 checks in 2.92 seconds on the preceding committed
candidate; current full-suite evidence covers the final receipt rules.
