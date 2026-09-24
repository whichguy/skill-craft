# Ask Agent cross-harness conformance cases

Uniform behavior means the same observable task contract with each host's native
facilities. It does not require identical tool names, arguments, startup cwd, or
permission interfaces. These are test cases, not a new runtime dispatcher.

## Qualification boundary

The managed v2 verifier consumes operator-normalized public records. It checks
identity, chronology, actual recorded cwd/root, immutable Git receipts, delivery,
and archived bytes. It does **not** parse native launch arguments or authenticate
raw log locators: a nonempty tool name is not proof of a native call, and an
operator-invented cwd is not a context observation. The operator must inspect
retained public launch inputs/results and child tool output before normalization.
Do not populate operation evidence from worker prose, `git -C`, or a requested
path. A later raw-export adapter needs its own provenance and adversarial tests;
the synthetic host matrix does not claim to provide one.

Record executable/version, host surface, selected package digest, effective
process-scoped flags/permissions/hooks, native tool schema, and raw event
locators for every live case. Keep default-profile and control results separate.
Frozen-package qualification does not qualify the installed skill entrypoint.
Task lifecycle completion and parent final-response completion are separate
outcomes. Missing observation remains UNOBSERVED, even if a process exits zero.

## Common cases

| ID | Setup and action | Required evidence / negative control | Coverage |
| --- | --- | --- | --- |
| C01 Package activation | Invoke the installed skill entrypoint where exposed, then repeat with an explicitly frozen package | Record the actually loaded root/digest and native skill invocation; a stale installation cannot inherit a newer frozen-package pass | Live activation case; package tampering checked offline |
| C02 Dirty caller inheritance | Start from a feature branch in a linked worktree, with staged and unstaged edits on one file, additions, deletion and untracked input; delegate again from the first worker worktree | Each child matches its immediate caller's HEAD and both patch layers; binary/untracked bytes and ancestor raw indexes stay unchanged; returned patch contains only the newest contribution | Workspace suite, including two-generation real-Git regression; repeat in each live host |
| C03 Native fresh background dispatch | Launch two distinct general-purpose workers with complete inline assignments; perform useful parent work after confirmation | Retain actual native request/result; fresh context, no resume/inherited fork, background capability, distinct handles and helper receipts; shell-launched model, fabricated ID or synchronous fallback cannot pass | Live route inspection; synthetic lifecycle ordering covers all five hosts |
| C04 Actual operation directory | Run check-context, relative shell work, a second independent shell call, and an absolute file edit in each assigned worktree | Raw child tool results establish cwd/root for each operation; caller cwd with `git -C`, worker prose alone, a second host-created worktree, or cross-worker root fails | Helper context tests and cross-host normalized negative controls; raw proof live |
| C05 Async return | Parent continues useful work; collect both native results in the same live parent | Distinguish automatic callback, native join, and after-exit resume; missing/duplicate return and work outside launch/return interval fail; record parent final response separately | Five-host normalized return matrix; actual notification/join live |
| C06 Delivery policy | Dirty caller uses patch; clean caller uses a complete committed range; audit worker uses report-only | Apply only worker contribution; reject inherited changes committed as output, dirty commit delivery, or report-only input edits | Real-Git workspace/delivery suites; live managed fixture covers patch and report-only |
| C07 Caller/profile hygiene | Repeat with ordinary host hooks and an explicitly recorded process-scoped control when diagnosing pollution | Compare caller HEAD/branch, path set, file bytes, both Git layers and raw index; even an unrelated hook-created file fails preservation | Managed caller-pollution regression; profile attribution requires live evidence |
| C08 Timeout and cancellation | Use a bounded native worker, request native stop if exposed, then inspect current execution | A parent timeout is not cancellation; cancelled requires confirmed native cancellation; if unconfirmed retain worktree and report UNKNOWN/pending; never close from file existence | Helper stop/retention checks and cancellation/retry coherence regression; interruption itself live |
| C09 Failure and fresh retry | Retain a failed/cancelled attempt, then launch a new fresh attempt | New native identity, receipt and worktree; old failure remains recorded; contradictory cancellation, reused ID, duplicate return/acceptance cannot become success | Managed retry and identity regressions; duplicate-notification behavior in real parent remains live |
| C10 Durable result and cleanup | Read reports, verify contribution, record acceptance, archive artifacts, close eligible worktree | Reports survive removal; corrupted/missing report, changed worker after inspection, or missing acceptance blocks close; repeat close is idempotent | Workspace, delivery and managed suites |
| C11 Live parent steering | While workers remain pending, send a new user instruction; continue collection | Parent answers the instruction without losing earlier pending jobs; actual native callbacks still reach the original parent | Live only; do not infer from a headless process exit |
| C12 Test command validity | Render the helper inspection command into the parent prompt and execute the same argument builder against the real helper | Both patch and report-only inspections declare two --artifact arguments; parser rejects accidental --report | Executable managed regression, before spending another live model run |
| C13 Self-contained caller handoff | Return completed patch, commits and report-only jobs; give a fresh consumer only the final handoff, not helper receipts or baseline JSON | Outcome, actual worktree/branch, exact patch or ordered SHAs, target checkout/revision, checks, integration state and next directive are usable inline; a later integration decision keeps code worktrees; removed worktrees link surviving reports; consumer transfers only the contribution | Real-Git delivery mechanics offline; native producer/consumer forward case for response behavior |

## Host-specific controls

Use current exposed schemas; these controls refer to the routes investigated in
September 2026, not permanent API compatibility guarantees.

| Harness / surface | Additional case | Existing evidence and remaining gap |
| --- | --- | --- |
| Grok Build | Native spawn_subagent background/cwd, omit resume_from; native join after parent work | Full managed lifecycle passed. Record the selected coding model separately; Grok Code in this harness is not a separate Grok Bot route |
| Claude Code | Agent/Task background, no second isolation:worktree; every Bash call scopes cwd; compare normal profile with process-scoped hooks control | Binding/return passed; normal-profile caller pollution failed, hooks control passed. Native creation-hook bridge remains a separate pilot, including concurrent workspaces and cleanup lifetime |
| Codex CLI / desktop | Fresh native spawn, fork_turns=none where exposed, explicit operation workdir when spawn lacks cwd | Full CLI fixture timed out; narrow final-package probe returned but had a test-command error. Rerun the corrected full case; CLI evidence does not qualify a distinct desktop schema |
| Cursor CLI / IDE | Native Task, prepared cwd or explicit operation directories, store outside managed cleanup roots | CLI return/delivery passed but raw child cwd evidence was absent. Obtain public child tool evidence; qualify IDE separately |
| OpenCode persistent TUI | Process-local background flag enabled, native task(background=true), omit task_id, retain narrow permission decisions | Managed lifecycle passed; parent final response stalled. Flag-off and one-shot negative controls, live steering, and native cancellation remain distinct cases |

See the [recorded routing results](../../../docs/ask-agent-routing-results-2026-09-20.md)
for versioned evidence and limitations. The additions here do not rerun or upgrade
those historical results.

## Execution, isolation and teardown

- **Focused offline:** run `python3 -B test/ask-agent-managed-harness.test.py` after
  changing the apparatus. It runs disposable real Git fixtures and synthetic
  event mutations, without model processes or installed settings.
- **Related regression:** also run `python3 -B test/ask-agent-workspace.test.py`
  and `python3 -B test/ask-agent-delivery.test.py`. These already belong to
  `bash test/run-all.sh --group core`; no second suite registry is needed.
- **Live smoke:** for one explicit host/profile, prepare a fresh managed fixture
  and run its existing two-worker assignment. Qualify C02–C05, patch/report-only
  delivery, C07 and C10, plus the selected host control. Apply an operator deadline
  and record unfinished work without inventing native stop confirmation.
- **Full live qualification:** run every common case and applicable host control
  independently for each claimed host/surface/profile. C01, C08, C11, C13 and native
  workspace-creation bridges are extra cases, not implied by smoke completion.

Use a new external owned run directory, frozen package, disposable Git repository
and linked caller for every mutating case/profile. Independent evidence mutations
may share already-frozen offline receipts only while those receipts are never
changed. Do not share live caller/worker workspaces across cases. Record setup,
commands, deadline and exit, normalization provenance, verdicts, and teardown.
Read/archive reports before cleanup; remove only owned worktrees after native
stop and accepted helper close. Retain failed or unconfirmed attempts and report
why. Keep all logs, prompts and operator files outside caller checkouts. No
persistent permissions, hooks, skill links, integrations or model launches are
added to the Ask Agent runtime by this test plan.
