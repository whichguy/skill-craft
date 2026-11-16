I would fix the leakage audit, timeout classification, and scoring predicates before launching. The core matched-state replay looks coherent; the main risks are that contaminated or unsuccessful trials could support stronger conclusions than their evidence warrants.

I reviewed the current worktree, including the timeout-classification and launcher edits added during this review. Findings are ranked by their effect on interpretation.

1. **The seeded ledger exposes a route to E17’s later solution outside the frozen bundle.**

   Evidence: [replay.py — `seed`](/Users/dadleet/src/skill-craft/.claude/worktrees/e18-60f85c/docs/experiments/parallel-plan-execution-20261114/replay.py) rewrites structured repository and workspace paths, but leaves source paths embedded in diagnostic strings. Codex’s `ledger.prefix.jsonl`, events 16, 18, 25 and 27, retain paths under `/Users/dadleet/e17-runs-20261115/e17-codex-qp/work/repo/`. That live repository now contains the later repaired solution. A worker could read or copy its files without running Git, escaping `worker_git` and R20c.

   This is an available leakage route, not evidence that any worker has used it. The bundle restriction itself does not close it.

   **Before launch:** recursively sanitize source-root paths in the agent-visible seeded ledger, preserving the frozen original prefix unchanged. Prevent access to the old solution directories, or record and adjudicate reads outside the assigned workspace.

2. **R20c can miss ordinary access to the failed implementation, and its disagreement does not produce one qualified overall conclusion.**

   Evidence: [score.py — `score_trial`](/Users/dadleet/src/skill-craft/.claude/worktrees/e18-60f85c/docs/experiments/parallel-plan-execution-20261114/score.py) stores only the first 200 characters of each Git-containing child call. [replay_table.py — `PEEK`, `load`, `rules`](/Users/dadleet/src/skill-craft/.claude/worktrees/e18-60f85c/docs/experiments/parallel-plan-execution-20261114/replay_table.py) then classifies that truncated text. In-memory checks confirmed that both of these escape the flag:

   ```text
   git diff bcb16dc05254f8e8ed8820804e18ed2eeabcaa71 HEAD -- src/store.js
   git --no-pager show bcb16dc05254f8e8ed8820804e18ed2eeabcaa71:src/store.js
   ```

   A recognized command appearing after character 200 also escapes. Parent-mediated access is outside this child-only audit.

   Separately, `rules` can return `first_attempt_s.overall = "redo costs more"` while R20c disagrees and prints “inconclusive.”

   **Before launch:** classify complete call arguments before truncation; cover revision-qualified diffs and Git global options; preserve sufficient raw arguments for manual audit, including parent access. Retain raw R20 results, but emit a separate, explicit sensitivity-qualified conclusion. An unflagged trial should mean “no access detected,” not “access ruled out.”

3. **The new blanket classification of kit re-test timeouts as apparatus faults can remove treatment-caused failures.**

   Evidence: [README.md — A15, “Oracle and classes”](/Users/dadleet/src/skill-craft/.claude/worktrees/e18-60f85c/docs/experiments/parallel-plan-execution-20261114/README.md) now says a 300-second re-test timeout causes a retry “the recovery rule did not cause,” so the draw is replaced. But [e17-flake-check.txt — “Limits”](/Users/dadleet/src/skill-craft/.claude/worktrees/e18-60f85c/docs/experiments/parallel-plan-execution-20261114/evidence/e17-flake-check.txt) explicitly leaves the cause unresolved: worker-added tests, base tests under load, or Node itself. Either recovery rule could produce code or tests that hang.

   Replacing the entire draw generates a different implementation. If one arm produces more hangs, this policy can preferentially improve its observed validity, retries and recovery time. Preregistration makes that selection transparent; it does not eliminate it.

   **Before launch:** classify these as “timeout, cause undetermined.” Freeze the candidate and permit bounded diagnostic reruns of that same tree, retaining the original timeout and timing. Reserve primary-draw replacement for independently established apparatus faults. Record original/replacement linkage explicitly.

   The current `hang_retest` flag only prints a warning; exclusion occurs through the operator’s rename/replacement procedure, not automatically in `usable`.

4. **Rounding can change registered decisions and predictions.**

   Evidence: `replay_table.py::ratio` rounds ratios to two decimals before `band` and `predictions` use them. In-memory probes demonstrated:

   - Four ratios of `1.496` become “redo costs more,” although their unrounded median is below 1.5.
   - Four ratios of `0.666` lose “fix costs more” after rounding to `0.67`.
   - Ratios just above 1 can round to 1 and lose the required three directional pairs.

   **Before launch:** retain full precision through durations, ratios, medians and predicates; round only presentation values. Add boundary cases to `selfcheck`.

5. **P87 can hold when no recovery integrates—or even starts.**

   Evidence: `replay_table.py::predictions` counts `retries == 0`. A synthetic dataset of 24 failed, noncompliant, never-started, never-merged trials returned **P87 HELD**.

   This matches the literal zero-event condition, but contradicts A15’s explanation that “the recovery attempt integrates at its first try.” Refused completions also do not emit `retry`.

   **Before launch:** decide which outcome is intended. For first-try integration, require a post-seed merge of the first recovery attempt with no intervening integration failure. Keep zero-retry counts as a separate diagnostic. Print refused-completion counts by category.

6. **The hang-policy change alters unseeded scoring, and auxiliary scoring can still lose a completed trial.**

   Evidence: [ticketfix.py — `run_checks`, `suite_passed`, `evaluate`](/Users/dadleet/src/skill-craft/.claude/worktrees/e18-60f85c/docs/experiments/parallel-plan-execution-20261114/ticketfix.py) applies `HANG` globally. It is not conditional on a replay seed. An in-memory probe confirmed that an ordinary unseeded check now passes after a hang followed by success, where the earlier policy would have stopped at the hang. Saved E17 evidence remains unchanged, but rescoring and future unseeded behavior have changed.

   Also, `evaluate` separately calls `suite_passed`, which runs another `npm test --silent` with an uncaught 300-second `TimeoutExpired`. Thus an auxiliary count can abort scoring after the substantive checks have completed. [score_replay.sh — scoring loop](/Users/dadleet/src/skill-craft/.claude/worktrees/e18-60f85c/docs/experiments/parallel-plan-execution-20261114/real-repo/score_replay.sh) skips export on that failure, prints an error, and can still exit successfully.

   **Before launch:** make the new hang policy explicit and opt-in for E18 if unseeded behavior is meant to remain unchanged. Obtain the suite count from an already completed check, or make that auxiliary measurement nonfatal. Require explicit scoring completion, reject deferred scores as final evidence, and make batch scoring exit nonzero on failures. Rescore the retained tree without rerunning the model.

   The fresh standard failure path produces missing exported evidence, rather than automatically exporting the deferred invalid verdict.

7. **R20 and especially R20b describe surviving observations, not unconditional recovery burden.**

   Evidence: `replay_table.py::usable`, `load`, and `host_ratios` exclude noncompliant or unfinished first attempts. `recovery_s` additionally requires a successful merge, so R20b uses pairs in which both recoveries integrated.

   That is a legitimate conditional estimand. It can nevertheless favor an arm whose difficult runs time out or never merge, while its surviving runs finish quickly.

   **Before launch:** put denominators and exclusion reasons beside each band. Label R20 as completed-attempt timing under the compliance conditions, and R20b as timing among successful recoveries. Show all launched-run times and failure outcomes alongside them. Keep completed but oracle-invalid products in the timing analysis, as registered; adding validity gating would create another selection.

8. **R22 cannot assign the remaining E17 workflow gap to main moving.**

   Evidence: `README.md::A15/R22` proposes saying how much of E17’s Qr−Qp difference would be left for main moving after considering the replay difference. E17 also differed in initial implementations, finish orders, affected features, failure counts and critical paths. Replaying one selected final failure does not identify those contributions.

   Calling this a “reading, not a computation” does not establish the residual attribution.

   **Before launch:** retain the comparison of magnitudes, but leave the unexplained workflow gap unexplained. Say whether the local replay result is consistent with repair being cheaper on these states. A causal remainder attributed to main movement would require another controlled experiment.

9. **The new `PermissionError` handling can defeat the registered trial timeout.**

   Evidence: [launch.py — `end_group`, `run_host`](/Users/dadleet/src/skill-craft/.claude/worktrees/e18-60f85c/docs/experiments/parallel-plan-execution-20261114/launch.py) now returns immediately on `PermissionError` from `killpg`. `run_host` subsequently calls `proc.wait()` without a timeout. Permission failure alone does not establish that the process exited; if it remains alive, the 1,800-second trial limit no longer bounds execution.

   **Before launch:** check process termination and bound the subsequent wait. Preserve the benign already-exited case, but record unresolved termination failure as an apparatus error.

10. **Two labels overstate what the measurements isolate, and launch load alone misses exposure during the attempt.**

   Evidence: `replay_table.py::load` defines `spawn_s` as claim-to-`start`; [dagkit.py — `cmd_begin`](/Users/dadleet/src/skill-craft/.claude/worktrees/e18-60f85c/docs/experiments/parallel-plan-execution-20261114/dagkit.py) logs `start` after workspace construction. The interval includes dispatch, initial worker activity and rule-dependent workspace setup.

   Likewise, [export.py — `export_real`](/Users/dadleet/src/skill-craft/.claude/worktrees/e18-60f85c/docs/experiments/parallel-plan-execution-20261114/export.py) measures a fix attempt’s diff against main. Its `+/-` counts include the preserved feature implementation, not just edits performed by the repair worker.

   Side-by-side hosts also finish at different speeds, changing competition during later pairs; one launch-load sample cannot describe that exposure.

   **Before launch:** label these as claim-to-begin time and delivered patch size. Use native spawn timestamps and workspace seconds for decomposition. Add timestamped load observations during attempts and annotate overlap using other trials’ existing timestamps. A begin-time workspace snapshot would preserve evidence of actual repair edits if that later matters.

On the predictions, E17’s pooled redo/fix medians imply ratios of roughly **2.15 Claude, 3.81 Codex and 3.11 Grok**, so P85’s direction has a reasonable basis. They do not establish its 75% all-host probability. Using each selected state’s known repair time gives illustrative ratios of **2.86, 2.04 and 7.83**, respectively; Codex is particularly close to P86’s 2.0 threshold, and those numerators still come from different tasks and launches. I would treat P86 cautiously.

P88–P90 are conditional on this favorable state selection. P90 can hold with zero valid trials in both arms because equality satisfies it; that is literally correct and supplies no positive reliability evidence. P93 and P94 are falsifiable absolute-speed forecasts, but can miss or hold because of provider latency and machine load without identifying a recovery-rule effect. Apart from P87’s operational mismatch, I found no prediction that is inherently unfalsifiable. The ten correlated forecasts should not be treated as ten independent confirmations.

The cheapest evidence protection is to retain **complete relevant tool arguments, immutable candidate identities, and structured scoring/fault status**. Those let you investigate contamination or rescore an expensive timed draw without generating a replacement implementation.

Checks that held:

- All three bundle/prefix hashes and frozen plan hashes match their manifests.
- The frozen plan still matches the live three E2E requests exactly.
- `seed` verifies both unpacked main and failed-branch commit IDs.
- Treatment changes both runtime metadata and the final retry event’s mode.
- The final prefix retry clears its earlier claim/start state; recovery timing starts from new events.
- Earlier landing and merge events prevent relanding or rerunning the other two features.
- Attempt numbering persists equally within each pair: Claude/Grok have two recovery slots left; Codex has three.
- Reconstructed outputs retain recorded results and hashes; historical T3 reporting for Claude/Grok follows the packet deliberately.
- Refused completions leave the attempt open, so their elapsed work remains inside its eventual duration.
- `merged` is logged after the green re-test, so `recovery_s` includes that re-test.
- Red re-test accounting separates merge, reset and test time without the suspected double-counting.
- Exported attempt diffs and replay timing/retry calculations filter strictly after `replay_seed`.
- Alternating pair order, capacity one, and deferred oracle scoring agree with A15.
- The three-valued every-host logic correctly lets one usable counterexample settle a prediction.
- The retained E17 ratios and attempt medians quoted in A15 match `e17-tables.txt`.
- The existing one-state-per-host and repairable-state limitations are disclosed adequately for the narrow question.

Verification: the current table self-check passed all **18 assertions**. The counterexamples above were exercised in memory. `replay.py check` was blocked because this read-only sandbox has no writable temporary directory, so I did not independently reproduce its runtime checks or rerun the 175/55/17 calibrations. I changed no files and launched no host CLIs.