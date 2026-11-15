# Astra's review of the Phase 2 design (2026-11-15)

Read-only review by the Astra runner at max effort (`ask.sh astra review-plan --effort max --no-tools`) of
[phase2-design.md](../phase2-design.md) as committed in 7ea06fbcb64052f6a1fead788b8cbc6e3e2a57fd. Kept as returned.
**Its findings were not verified:** the owner closed Phase 2 the same day, before any finding was checked against
the code, so each one is the reviewer's claim, not a fact.

Runner metadata: `{"model_used": "gpt-6-astra", "fallback": false, "exit": 0, "profile": "ask", "persona": "codex-astra", "effort": "max", "sandbox": "read-only", "tool_restrictions": "web_search_disabled", "error": null}`

---

**Verdict: not ready.** The direction is sound, but the hold’s enforcement boundary, release transitions, and evidence-preservation rules need revision before implementation.

**1. Goal**

Preserve the owner’s deployed candidate and evidence during review, prevent unauthorized producers or cleanup, and report unavailable observations without weakening acceptance.

I reviewed the current checkout, the trial records, and the full messages of all four cited commits: `dcd91d4a9f75b50c90cf337f4d63734ee15f48cc`, `2d47ab820027535f5532284370b78071739abe2c`, `71fa298e44db73f6afa46217377ba0ea850de916`, and `b69bad199a677f5ff7ee6e09fea84aa8b64068c7`. No files changed, harness/tests ran, or `sf` commands executed.

**2. Material issues**

1. **Material — the path table does not yet define an enforceable hold.**

   Checking final cleanup and automatic resumption leaves several earlier or independent entrypoints open:

   | Route and evidence | Coverage and required placement |
   |---|---|
   | `_main` normal/resumed `platform_preflight`, `run.py:4322`; fresh `before`, `:4531` | Missing fresh checks. Check before wrapper/profile mutation and immediately before each platform command. |
   | First `session`, `run.py:4576`; `launch`, `:922` | Automatic resumption is covered; first launch is not. Check before opening/truncating event files and spawning the host. |
   | Ordinary final checks, `run.py:4707`; `product_at_stop`, `:4716` | The table names regrade checks. Apply the hold to ordinary endings too, including a hold arriving between individual checks in `run_checks`. |
   | `quality_gate` and `quality.measure` | Initial gating is insufficient. Check before deleting the old quality directory, before each child launch, and while children run. |
   | `owner_note.Watcher._watch`, `owner_note.py:87` | Missing. It can launch `shiploop note` and write run records during a hold. Stop/join it and check immediately before its write. |
   | Resume admission, `run.py:4232` | Refusal must precede **`stop_file.unlink` at `:4244`**, not merely cleanup/reap/leases. |
   | `--preflight-only`, `run.py:4045` | Separate early route. It currently continues platform preflight even after recording a lease refusal, and releases a successful probe lease before the hooks run. Refuse before platform access and retain protection across that access. |
   | `--continue-from`, `continue_from` | Copies `prior/work`, not the hold. A new destination does not inherit protection of the same remote target. |
   | Suites and `iterate.main` | Subject runs reach `run.main`, but use new output folders. Iteration also continues into review/improvement after a held result unless explicitly stopped. Define policy forwarding and held-result handling. |
   | Standalone UI/oracle/cleanup scripts | Direct invocation with the retained `E2E_PLATFORM_DIR` bypasses `run.main`. The UI registers an attempt and resets synthetic records; the oracle submits validation; the gym cleanup adapter is also the full Grok case’s cleanup command. |
   | `lifecycle.dispose` | Missing destructive boundary: its standalone CLI can delete `work`, `home`, `build`, `marketplace`, and `quality`. It is **not** automatic `_main` teardown. |
   | Fidelity and export | Fidelity analysis has no identified platform producer. Export writes and prunes derived files; it needs an explicit preservation policy. |
   | `review.review` / `judge.judge` | These start independent hosts and write assessment artifacts inside an existing run. A read-only reviewer model does not make the surrounding operation a pure reader. |

   Evidence: [run.py — admission and stop consumption][admission], [run.py — platform/first-session dispatch][dispatch], [run_checks][checks], [quality.measure][quality], [owner-note watcher][watcher], [lifecycle.dispose][dispose], [review.review][review].

   **Fix:** put the pure hold reader in a small shared module and enforce it at shared dispatch boundaries. Keep the case lock through authorized mutation and shutdown; acquire platform leases only after admission and retain them through platform work. Recheck after acquiring protection and immediately before execution.

   Also define scope explicitly. Slices and stage samples have their own regrade/oracle routes (`slice.regrade`, `stage_live.grade_sample`) but are separate sample types, not demonstrated routes into this trial. Exclude them explicitly from Phase 2 or cover them deliberately.

2. **Material — “stops nothing and names live processes” cannot satisfy “keeps producers quiescent.”**

   There is a concrete orphan case: SIGKILL removes the harness’s lock while its separately launched host survives. The repository already tests precisely that in [CrashAndRetryTest][real-crash].

   A held resume that merely prints that host’s PID leaves it able to deploy. Meanwhile, an invocation still running when the hold appears will not notice through the proposed unchanged teardown: [`launch` polls timeout, stop-file, termination and `stop_when`][launch], not hold state. `end_group` happens only after that loop ends.

   Crash cleanup is also narrower than normal cleanup: `PlatformGuard.finish` stops its tracked live hosts, while the normal path separately runs ledger cleanup and listener reaping.

   **Fix:** distinguish **hold requested** from **producer shutdown verified**. Poll holds during live sessions and make owned-process shutdown independent of whether platform cleanup is permitted. On recovery, stop positively identified surviving run producers under the case lock; preserve unrelated inspection processes. If identity cannot be verified, report quiescence as unverified and block further actions.

   I would not retain blanket “nothing stopped” semantics for an identity-verified orphan host. Conversely, I would not use broad listener matching to kill the owner’s viewer. This distinction should be an explicit owner decision.

3. **Material — release must authorize an action, not merely remove a boolean prohibition.**

   Three counterexamples invalidate the proposed reuse of ordinary resume/regrade:

   - **Continue a blocked run:** [`_main` classifies blocked/done runs as regrades][resume-state]. The motivating trial is blocked. A continuation release therefore does not inherently launch a host and can fall into cleanup arming.
   - **Release to cleanup:** because the held cleanup record is `ok:false`, the existing path reruns final checks and `product_at_stop` before cleanup. That authorizes additional producers.
   - **Persistent policy:** the blocked result still fails `keep_refusal`; without explicit precedence, `--hold-platform` can immediately hold it again instead of honoring cleanup authorization.

   **Fix:** specify separate dispatch rules:

   | Authorization | Permitted operation |
   |---|---|
   | Active hold | Inspect retained evidence; no new producer or platform cleanup |
   | Release to cleanup | Restate observations and perform the authorized cleanup attempt; no checks, quality, host, or keep override |
   | Release to continue | Continue only through a valid engine recovery/resume route; never silently unblock a blocked engine |

   Define when authorization is consumed, what survives a crash, and whether a failed cleanup requires another owner request. A permanent `released.to="continue"` must not skip preflight after a later cleanup.

   For this trial, continuation also cannot silently authorize cleanup at the next successful ending: the [owner’s instruction requires a new explicit cleanup request][trial-hold].

4. **Material — pending-record and concurrent-hold semantics are insufficiently durable.**

   `PENDING_CLEANUP` is the right precedent, but “a killed harness leaves the pending record” is conditional. [`write_cleanup_record` suppresses write errors][records]; commit `c265203473fa252401cc4bf76d974b81db41f2ea` explicitly warns that a failed pending publication can leave the previous successful record in place. Policy persistence also occurs after platform preflight, and the guard is armed only after `before`.

   Separately, [`run_platform_command`][platform-command] can already be executing cleanup when the hold appears. It has no hold polling, and a second Ctrl-C deliberately abandons it running. Such a cleanup cannot truthfully become `ran:false`.

   **Fix:**

   - Persist policy/operation identity before the first relevant external operation.
   - Treat an existing malformed/unreadable hold as a refusal, not “no hold.”
   - Publish hold/release records atomically; make `hold_state` a side-effect-free read.
   - Preserve cleanup-started and partial/unknown outcomes.
   - Define the acknowledgement boundary and handling of in-flight commands.
   - Never infer that stopping a local process cancelled a deployment already submitted remotely.

   The cited `2d47ab82…` message expressly records that cleanup does not poll deployments in flight.

5. **Material — writing a held record must not erase a previous failed cleanup or misdescribe the platform.**

   Replacing:

   ```json
   {"ran": true, "ok": false}
   ```

   with only:

   ```json
   {"ran": false, "ok": false, "held": true}
   ```

   loses whether cleanup had partially removed the candidate. Teaching `keep_blocker` to stop recognizing that failure would undermine the distinction established by `dcd91d4a…`.

   The trial failed at its first query, but the generic design covers failures after deletion too.

   There are two additional implementation traps:

   - [`note_platform` currently prefers an older result’s cleanup][note-source], even when `earlier_cleanup_record` supplied fresher state.
   - The [`grok-chat-salesforce-full` platform specification][full-case] has **no `resume_note_kept`**, so the promised message cannot be sent for this case as written.

   **Fix:** retain prior cleanup history and distinguish “preserved since the hold” from “unchanged since deployment.” Resolve cleanup and resume-note state from one authoritative record. Supply an accurate generic continuation note when the frozen case lacks one; do not invent a successful keep.

6. **Material — the activation rule differs from both “non-pass” and existing unfinished keep behavior.**

   [`keep_refusal`][keep] does not evaluate every final verdict: it omits committed delivery, invocation/plugin validity and release-slice gates. Therefore a run can fail overall while satisfying this predicate and still be cleaned.

   Conversely, with both flags, an unfinished run whose `keep_checks` passed satisfies `keep_decision`’s unfinished keep but fails `keep_refusal`. The proposed policy should therefore hold it rather than mark it kept.

   **Fix:** choose and name the predicate precisely. Either retain “not a finished delivery under `keep_refusal`” or define the intended pre-cleanup verdict; do not call them interchangeable. State precedence explicitly: active owner hold, action-specific release, launch hold policy, then ordinary keep/cleanup. Test both flags together for finished, unfinished-qualified, failed-check and stopped endings.

   Preserve the distinction between a declared policy and a policy already activated. For a known unfinished ending, decide whether activation precedes final producer checks; currently the design allows those checks before making its final hold decision.

7. **Material — held restatement needs missing-evidence behavior and an explicit write allowance.**

   [`restated` currently requires existing checks][post-checks]. A killed harness may have no `result.json`, or an older segment’s result. “Restate the run’s own records” must not fall back to executing checks or treating an absent check list as success.

   The blanket hash invariant is also impossible: the design itself replaces `platform/cleanup-record.json`; regrade writes metrics, results, transcript, flow and export. The exporter [prunes obsolete documents][export-writes]. Cleanup and continuation tests intentionally change state.

   **Fix:** retain available observations with provenance; represent missing observations as unavailable/nonpassing, keeping declared check denominators. Separate immutable candidate/snapshot/evidence bytes from permitted control and derived-report writes. Prefer a separate destination for held inspection outputs.

   Exclude the authority record from [`scrub_files`][scrub]: its root-directory sweep would otherwise rewrite purportedly verbatim hold words.

8. **Material — `ok:false` preserves the gate, but does not deliver truthful classification throughout the system.**

   The conservative non-pass choice is reasonable. It does not automatically communicate “held, not cleanup failure”:

   | Reader | Current consequence |
   |---|---|
   | Final verdict list | Cleanup `ok:false` forces non-pass; unexamined checks remain non-pass. |
   | `outcome_class` | A done engine with a held cleanup becomes `FAILED`; a new hold stopping phrase needs classification. Existing BLOCKED precedence should remain. |
   | Baselines | Passed/total counts remain conservative, but no hold policy/state is represented. A done held run can remain a counted failed attempt. |
   | Scorecards | Passed/total denominators remain conservative. |
   | Run Review | No platform-hold projection; `_product_at_stop` discards `unexamined` and recomputes it as failed. |
   | Iteration text | Nonpassing checks are described as failures; execution continues into review/improvement. |
   | Metrics/fidelity | No independent case-check classification consumer was found; do not unnecessarily change their counters. |

   Evidence: [outcome classification][outcome], [baseline_row][baseline], [scorecard.accuracy][scorecard], [Run Review projection][export-stop], [iterate.main][iterate].

   **Fix:** carry lifecycle reason and unexamined classification through the relevant projections without dropping checks from denominators or changing pass gates. Update exporter schema, facts, HTML and tests. That touches `skills/shiploop-run-review`, so the stated blanket `No-Change-Note` scope is no longer correct.

   **No verdict needs to loosen.** Baseline inclusion changes, if desired, are a separate comparability decision.

9. **Material — exit 77 plus a last line is workable, but the specified capture contract is unreliable.**

   [`run_checks`][checks] concatenates **all stdout followed by all stderr**, then keeps 2,000 characters. A marker printed last to stdout can be followed by an earlier stderr warning. A long reason can cut off `UNEXAMINED:`. Truncating before scrubbing can also remove a credential’s identifying key while retaining its value.

   **Fix:** define the marker stream and exact grammar; parse complete captured output before truncation, then scrub and bound stored output/reasons. Preserve `returncode=None` as timeout, regardless of partial output.

   Require controls for 77 without marker, marker with other exit codes, stderr diagnostics, CRLF/trailing whitespace, long output/reason, credential-shaped text and timeout. Treat this as an explicit checker protocol, not a generic interpretation of exit 77 or arbitrary “UNKNOWN” text.

10. **Material — the named script changes do not cover all quota paths safely.**

    The wrapper catch in `grok_chat_salesforce.main` is not the only route. [`chess_salesforce.do_tests`][sf-tests] can receive quota failure as parsed JSON with no summary and turn it into ordinary failure. The [full oracle catches failures internally][oracle] before, during and after validation. `gym_membership_salesforce.do_rules` queries identity before checking whether its phase is supported.

    Those catches also contain identity mismatches, source mismatches, collisions and genuine assertion failures.

    **Fix:** propagate a typed unavailable/quota condition through exception and JSON-result paths; check unsupported phases before platform access. Preserve observed product/safety failures when unavailable evidence occurs alongside them. Do not convert every `SfError` or `UNKNOWN` message into unexamined.

11. **Material — headroom delta cannot measure run consumption or attribute it to the model.**

    Salesforce’s allowance covers a **rolling 24-hour window**. Earlier usage can expire during the run, so remaining allowance can increase despite new requests. [Salesforce documentation](https://developer.salesforce.com/blogs/2024/11/api-limits-and-monitoring-your-api-usage).

    [`sf_guard.log_decision` and `log_end`][guard-log] count CLI invocations, not HTTP requests. One deployment/test command can make multiple requests; the ledger also includes local commands. Subtracting 203 commands from an allowance delta has incompatible units.

    **Fix:** retain raw snapshots and, where identities match, an explicitly named **net headroom change**. Keep model command counts separate and attribution unmeasured. State that the proposed interval excludes `before` and cleanup consumption.

    The trial counts themselves are supported: 406 ledger rows, 203 calls, 59 deployments and 56 Apex-test commands.

12. **Material — the limits hook needs operational semantics before it can be called “record only.”**

    Sampling after each host session is feasible at [`session`’s wrapper][session-wrapper]. But:

    - An active hold must suppress session/end sampling; otherwise the measurement violates the hold.
    - Failed/missing end observations must not be replaced by the last successful intermediate sample.
    - Samples need invocation/session identity so resumed intervals do not silently include pauses and unrelated activity.
    - Per-session calls consume time inside the existing deadline. With many sessions they can change whether the next session starts.
    - The current platform-command timeout is 900 seconds; inheriting that for telemetry would be consequential.
    - Failure, malformed JSON or publication errors must not mask the original ending or prevent required shutdown.

    Salesforce’s CLI currently makes one explicit `/limits` request, but that does not prove exactly one total network request including authentication/retry behavior. [Official CLI source](https://raw.githubusercontent.com/salesforcecli/plugin-limits/main/src/commands/org/list/limits.ts).

    **Fix:** specify best-effort, bounded sampling; record elapsed time and skipped/unmeasured reasons; parse full JSON before output clipping; pin the authorized org and use the harness-side adapter. Keep telemetry failure out of verdicts. Make deadline accounting explicit rather than silently changing it.

13. **Material — P2a is faithful for A only; the recommendation for B needs a different contract.**

    Keeping acceptance after the journey is right: [`live_request`][acceptance] needs a completed passing receipt and selects the six specific calls.

    But `71fa298e…` and `b69bad19…` deliberately separate B from inherited fixed interfaces, trace machinery and test quotas. The [scenario README expressly forbids seeding those contracts into its inputs/helpers][scenario]. Therefore “adopted unchanged,” “exact six-call binding,” and “recommended B” do not all fit.

    Existence alone is also insufficient readiness. The original P2 requires expiry and source/deployment/actor changes to force reassessment. For A, admission must precede [`_reset_synthetic_items`][ui-reset], not merely browser startup.

    **Fix:** say A adopts the existing contract; B adopts only the readiness-before-action principle through its independently qualified observer. Specify the readiness writer, reader, current binding, expiry/invalidation and restart rules now. Detailed schema can remain with the owning session.

14. **Material — several listed tests cannot prove their claims with `PlatformCase` unchanged.**

    Evidence: [PlatformCase and fake-host construction][fixture], [HardKillTest][fake-kill], [ProductAtStopTest][stop-fixture].

    | Tests | Required construction |
    |---|---|
    | 1: held blocked regrade | Add a real execution worktree and phase-aware sentinels. The existing blocked fake writes only state, so `product_at_stop` can return early. |
    | 2: between sessions | Use a deterministic barrier/fake-host event after session one; assert the exact launch count. |
    | 3: held resume | Assert the stop file survives and spy on cleanup, reap, leases and launch. Platform verbs alone cannot prove “nothing stopped.” |
    | 4: ending/crash/killed harness | Split these. `HardKillTest.killed` simulates omitted finish/result; use the lifecycle subprocess fixture for actual SIGKILL, orphan identity and decoy survival. |
    | 5: finished policy run | Existing done fixture is suitable; add the both-flags case. |
    | 6: cleanup release | Add sentinel checks, repeated regrade, failed cleanup and crash-after-dispatch cases. |
    | 6b: continuation release | Use active engine state and inspect the prompt; separately test blocked/done refusal, stale `result.json`, and a case without `resume_note_kept`. |
    | 7: regression control | Run the established suites; this is not one new fixture scenario. |
    | 8/8b/8c | Use checker processes for transport behavior; add a real worktree for `product_at_stop` and separate exporter/rendering tests. |
    | 9: `keep_blocker` | Best as a focused unit test plus dispatch coverage. |

    `PlatformCase.resume` discards `run.main`’s return code, so extend it or call `main` directly for exit assertions. Its mocked empty listener observation cannot establish real process shutdown.

    Add missing tests for malformed holds, failed hold/pending publication, holds during commands/quality, standalone disposal/checkers and held telemetry.

15. **Material — the owner decision list omits choices the design has already made.**

    The five proposed decisions are mostly appropriate. Missing direction-setting choices include:

    - run-scoped versus target-scoped protection;
    - verified orphan shutdown versus preserving potentially mutating processes;
    - in-flight cleanup handling and retry authorization;
    - whether continuation permits eventual automatic cleanup;
    - held-result treatment in comparisons;
    - whether B is a deferred integration dependency rather than this implementation’s target.

    A run-local file cannot protect the target from all new runs after its lease disappears. Existing [`epoch.target_launch_state`][epoch] already blocks reuse within an epoch without sealed successful cleanup; preserve that protection rather than introducing a competing scheduler.

    Finally, writing `run/hold.json` into this trial does **not** upgrade its frozen harness. [`resume_command` embeds the driver’s absolute path][resume-command]. The preserved driver lacks hold handling.

    **Fix:** name the guard-aware entrypoint and retain the prohibition on invoking the frozen driver. Keep the original trial and historical evaluator bytes intact. Approval to implement this design is not approval to resume, deploy into, or clean that trial.

**3. Minor nits**

16. **Minor — correct the readiness timing.** The window became ready about 1.276 seconds after the **last relevant provider response**, not after the entire journey ended; a later `getConversation` response exists. The six-call rejection remains justified. Evidence: the trial’s UI observation and `window-14/events.jsonl`, cited by P2/E04.

17. **Minor — retain the polling qualification.** “46 calls in about 56 minutes” is a heuristic over polling stretches, not measured exclusive waiting or a demonstrated 56-minute saving.

18. **Minor — tighten two descriptions.** The full oracle submits check-only deployment validation, rather than intentionally leaving a deployed test class. Also, “a platform that was not cleaned is not a pass” has an existing exception: a finished, deliberately kept delivery can pass.

The design is right to separate holds from qualified keeps, retain a persistent launch policy, distinguish unavailable inspection from product failure, preserve non-pass acceptance, avoid a reserve without an owner decision, and retain post-journey acceptance for A. The [P1/E20/E21 evidence][original-plan] strongly supports those changes.

**4. Open unknowns**

- Which external operator processes and already-submitted remote jobs must be included before claiming platform quiescence? The local ledger cannot establish that alone.
- What should a continuation release mean for an engine that remains blocked awaiting an answer?
- Which exact artifacts are immutable, and where may fresh inspection/reporting outputs be written?
- Does the owner want platform-wide enforcement across new runs, or a narrower run-bound guarantee?
- What are the actual latency and request overhead of the limits adapter in this environment? The trial did not measure them.

**5. If I were implementing tomorrow**

1. Resolve the action-specific release rules, protection scope and orphan/in-flight behavior with the owner; revise the design before coding.
2. Add a small shared, atomic, fail-closed hold-state implementation with preserved cleanup history and explicit authorization consumption.
3. Wire admission, live cancellation, individual command dispatch, shutdown and disposal boundaries; cover them with sentinel and real orphan-process fixtures.
4. Implement held restatement with missing-evidence handling and explicit permitted reporting writes.
5. Add the unexamined protocol, typed quota propagation and all reporting projections, preserving verdicts and denominators.
6. Add headroom snapshots with honest delta semantics, hold-aware sampling and measured overhead.
7. Hand readiness to the chosen scenario’s owner under the corrected A/B contract.
8. Run the focused established suites and independent review on synthetic runs. Leave the retained trial untouched until its separately authorized migration step.

[admission]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:4232
[dispatch]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:4522
[checks]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:1664
[quality]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/quality.py:923
[watcher]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/owner_note.py:87
[dispose]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/lifecycle.py:665
[review]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/review.py:576
[real-crash]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop-e2e-lifecycle.test.py:897
[launch]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:963
[resume-state]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:4130
[trial-hold]: /Users/Shared/Codex/shiploop-e2e/salesforce-grokbot-independent-20261114T161019Z/operator/owner-review-hold.json:4
[records]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:2414
[platform-command]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:2307
[note-source]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:4305
[full-case]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/cases.json:2275
[keep]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:2488
[post-checks]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:4700
[export-writes]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/skills/shiploop-run-review/scripts/export.py:3720
[scrub]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:1770
[outcome]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:3645
[baseline]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:2827
[scorecard]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/scorecard.py:282
[export-stop]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/skills/shiploop-run-review/scripts/export.py:1747
[iterate]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/iterate.py:391
[sf-tests]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/checks/chess_salesforce.py:782
[oracle]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/checks/grok_chat_full_salesforce.py:460
[guard-log]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/checks/sf_guard.py:858
[session-wrapper]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:4268
[acceptance]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/checks/grok_chat_full_quality.py:186
[scenario]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/scenarios/grok-chat-outcome/README.md:12
[ui-reset]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/checks/grok_chat_full_ui.py:1040
[fixture]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop-e2e-platform.test.py:180
[fake-kill]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop-e2e-platform.test.py:2310
[stop-fixture]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop-e2e-environment.test.py:93
[epoch]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/epoch.py:365
[resume-command]: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/3bdb4918-31ed-4ec0-9fce-c0ac0d903d01/scratchpad/wt-phase2-6209f4/test/shiploop_e2e/run.py:1177
[original-plan]: /Users/Shared/Codex/shiploop-e2e/salesforce-grokbot-independent-20261114T161019Z/operator/improvement-plan/improvement-plan.md:36
