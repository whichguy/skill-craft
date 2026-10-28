# Astra review: design v2

Run 2026-10-27 through the `ask` agent: model_used `gpt-6-astra`, persona `codex-astra`, effort `max`, fallback `False`, exit `0`. Read-only request; no files changed in the repository. Code citations are Astra's own and were checked as recorded in [the journal](../shiploop-owed-outcome-journal.md).

## Question

Use MAX reasoning effort. Follow-up design review of the same ShipLoop question you reviewed earlier, now design v2. Repository: the skill-craft repository (read-only; do not edit anything). Read the code you need; cite file and symbol for every code claim and mark each claim verified (you read it) or inferred. Keep the answer under 1,300 words.

The owner reframed the problem after your first review. Read the section "Design v2: one `done`, three edges" in docs/shiploop-owed-outcome-journal.md, and findings F8 and F9 in the same file. Your first review is recorded there under "Review: Astra at max effort on the owed-outcome draft (2026-10-27)".

Summary of v2: every inner stage stops running a bound Until Loop. One ShipLoop command per iteration, `shiploop done`, reads a result whose `edge` is:
- exit: all exit conditions hold; the script runs the stage's gates; any failing gate makes the script take retry itself, with the failures as the gap;
- intervene: a person must act; `awaiting` as today;
- retry: `gap` plus `plan`; the next packet restates the goal and exit conditions and gives the gap and plan by value; optional target step | plan (today's send-back) | work (today's add-work).
A malformed report stays an input error. A stuck rule replaces the GENUINE_FIX_ATTEMPTS count: two retries in a row with the same gap and no tree change leave only retry->plan or intervene. Verify's clean final pass becomes "the final iteration changed no file", checked via Git. The Improve child stays as is for now.

Questions (answer each, numbered):
1. Does v2 keep every strictness property in the journal's "Strictness kept" table? Which, if any, gets weaker, and what is the smallest fix?
2. Turning a failed exit claim into a script-taken retry instead of a refusal: what is lost (for example `complete --check-only`, idempotent retries, the refusal text the model fixes from)?
3. Is the stuck rule sound? Consider oscillating gaps, gaps caused outside the tree (services, environment), and gap wording that changes while the failure is the same. What fingerprint should define "same gap"?
4. Three edges with retry targets, versus keeping send-back and add-work as separate edges: which is clearer for the model and safer for the graph?
5. What else in the inner stages or the stop hook could be removed without losing a feature the owner relies on?
6. Phasing and risk under the owner's one-supported-version rule (old saved runs are refused).

End with your single strongest recommendation on v2.

## Answer, verbatim

V2 is viable, but its replay contract and stuck rule need revision. **Verified** means I read the source; **inferred** identifies design judgments. No files changed or tests run.

1. **Strictness is preservable, but equivalence needs explicit conditions.**

   **Verified:** F8 holds: stage contracts omit `exit_checks`. Receipt validation binds workspace, work, conditions and context, then checks the final assessment. The runtime also requires a recovery handoff containing completed facts and evidence locations. Sources: [shiploop_loop_contract.py — contract](skills/shiploop/scripts/shiploop_loop_contract.py:17), [shiploop_loops.py — check_loop_packet](skills/shiploop/scripts/shiploop_loops.py:724), [until_loop_ephemeral.py — _report_schema](skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:642).

   | Property | Inferred requirement for equivalence |
   |---|---|
   | Frozen exits | Bind criteria, scope and authority to the action/plan revision; retry cannot rewrite them. |
   | Counted iterations | Count accepted reports once; exclude previews, malformed input and replay. |
   | Conditions restated | Use identical frozen criteria in initial, retry and recovered packets. |
   | Script-checked exit | Preserve gates, ordering and evidence requirements. |
   | Recorded exit checks | No stage feature lost; F8 holds. |
   | Verify’s final pass | Retain complete review **and** unchanged candidate content. |
   | Recovery | Preserve completed facts and evidence locations alongside gap/plan. |
   | No caps | Do not forbid justified work using an unreliable stuck heuristic. |

   **Inferred:** Persist Verify’s baseline when issuing the iteration; `next` must not reset it. Compare after gates, including their edits. Missing snapshots mean unknown, never unchanged. Equal endpoints prove no **net** change, not that no file was touched or a review occurred. [Git’s diff documentation](https://git-scm.com/docs/git-diff)

   **Verified:** The existing snapshot includes untracked files and excludes runtime metadata. Reuse that mechanism. [shiploop_lint.py — snapshot_tree/_excludes](skills/shiploop/scripts/shiploop_lint.py:413)

   **Inferred:** These are the smallest fixes for potential weakening of freezing, recovery and review semantics. Requiring zero changes also tightens the former allowance for trivial edits.

2. **Automatic retry need not weaken exit safety, but changes submission semantics.**

   **Verified:** `--check-only` avoids accepting the action or counting test attempts, although it writes diagnostics; successful preview tests can be reused. Accepted-result replay is already idempotent and conflict-sensitive. Sources: [shiploop_navigator.py — dispatch](skills/shiploop/scripts/shiploop_navigator.py:9264), [shiploop_test_loop.py — _reused](skills/shiploop/scripts/shiploop_test_loop.py:1131), [shiploop_navigator.py — apply](skills/shiploop/scripts/shiploop_navigator.py:3865).

   **Inferred:** Keep `done --check-only` as an optional preview. “One command per iteration” should describe the normal path.

   Give each iteration a fresh callback token and immutable input. Atomically record the submitted edge, taken edge, report digest, counter and successor. Duplicate submissions return the recorded decision without recounting or rerunning completed gates; conflicting submissions fail. This follows established [request-token idempotency practice](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/).

   Preserve concrete refusal diagnostics, evidence locations and repair restrictions in the retry packet. A failed `exit` supplied no `plan`: generate an explicit repair instruction from gate findings. Return `requested_edge=exit, taken_edge=retry` prominently; command success must not imply stage completion.

   Convert typed semantic gate failures only. Malformed input, stale identities, authority violations and storage faults remain errors. The loss otherwise is useful separation between “repair the work” and “repair the submission/system.”

3. **The stuck rule is unsound as a mandatory routing restriction.**

   **Inferred:** A/B/A oscillation evades consecutive equality; paraphrasing defeats text equality; unrelated edits defeat tree equality. Conversely, service recovery, environment investigation and inbox-only planning can progress without product-tree changes.

   **Verified:** Improve already fingerprints result blocks separately because those artifacts can change outside the candidate tree. The seven-attempt rule is currently prompt-only. Sources: [shiploop_improve_changes.py — result_identity](skills/shiploop/scripts/shiploop_improve_changes.py:92), [shiploop_stage_spec.py — GENUINE_FIX_ATTEMPTS](skills/shiploop/scripts/shiploop_stage_spec.py:94).

   **Inferred:** Fingerprint **stage/item scope + contract revision + criterion/gate ID + check identity + failing test/resource identity + normalized failure class**. Sort failure sets; exclude prose, timestamps and incidental output. Track recurring obligations across intervening reports, including oscillation.

   Keep progress evidence separate: relevant candidate/result changes and observed external-state changes. Exclude retry narration and unrelated edits. Uninstrumented semantic gaps cannot support reliable forced escalation.

   Pilot this as a warning requiring a revised strategy or evidence-backed continuation. Never force human intervention while useful autonomous work remains.

4. **Prefer three public families with distinct internal transitions.**

   **Inferred:** Keep `retry.step`, `retry.plan` and `retry.work` separately validated. These are five transitions under three families. Print only legal targets and their required payloads; the stuck rule must not offer forbidden targets.

   **Verified:** Plan destinations are stage-specific; corrective work requires new IDs. Sources: [shiploop_stage_spec.py — send_back_target/_finish](skills/shiploop/scripts/shiploop_stage_spec.py:76), [shiploop_navigator.py — _apply_result](skills/shiploop/scripts/shiploop_navigator.py:3785).

   **Inferred:** Preserve those constraints, history and downstream invalidation. Separate internal handlers are safer than a generic cursor-jump implementation; separate public edges add little once target schemas are explicit.

   **Verified:** `awaiting` supports `answer`, `present` and `service`; service waits resume through `--observed`. V2’s person-only wording would remove that feature. [shiploop_navigator.py — _normalise_awaiting](skills/shiploop/scripts/shiploop_navigator.py:620), [control](skills/shiploop/scripts/shiploop_navigator.py:4094)

5. **Remove adapters and duplicated bookkeeping, while retaining their substantive responsibilities.**

   **Inferred:** Remove stage receipts, receipt-citation normalization, restart prose and receipt-specific send-back exceptions. Replace callback-attempt progress with accepted-report progress; preserve hook memory across `next`. Remove the blanket background-task exemption from no-progress release: a watcher does not establish progress.

   **Verified:** Those hook behaviors reside in [shiploop_keepalive.py — observe](skills/shiploop/scripts/shiploop_keepalive.py:296) and [_decide](skills/shiploop/scripts/shiploop_keepalive.py:484).

   **Verified:** Improve retains its runtime and parent-return ownership. Therefore, the owed report cannot always be ShipLoop `done`; child reporting and worker collection remain distinct. [shiploop_navigator.py — improve_start_contract](skills/shiploop/scripts/shiploop_navigator.py:8303)

   **Verified:** The loop layer also provisions Verify’s rubric and supports review scheduling; Improve uses `loop_contract`. **Inferred:** Relocate these before deletion; F9 gives gross, not net, savings. [shiploop_loops.py — contract_writes](skills/shiploop/scripts/shiploop_loops.py:539), [shiploop_navigator.py — _wide_item](skills/shiploop/scripts/shiploop_navigator.py:7467)

   **Inferred:** Separately replace the driver’s session ceiling with the permitted time/dollar policy. **Verified:** [_drive_sessions](skills/shiploop/scripts/shiploop_keepalive.py:945) currently stops at `max_sessions`.

6. **Phase implementation, then release one coherent protocol.**

   **Verified:** State validation rejects unsupported versions. [shiploop_navigator.py — _validate_current_state](skills/shiploop/scripts/shiploop_navigator.py:1476)

   **Inferred:** Use one new schema, no migration or dual runtime, and clear old-run refusal. Specify transitions and failure categories first; build iteration persistence and rendering in reviewable commits; cut over CLI, packets, hook recognition and consumers together.

   If phase 0 ships independently, also add stage-iteration progress while old loops remain. **Verified:** [shiploop_protocol.py — hook_status](skills/shiploop/scripts/shiploop_protocol.py:442) currently observes Improve passes, not stage iterations.

   **Inferred:** Require crash/replay tests, lost-output callbacks, malformed reports, legal/illegal targets, invalidation, Verify edits/commits/untracked files, external-only progress, oscillation, compaction and delegated ownership; then E2E before release. Defer redesigning Improve.

**Strongest recommendation:** Adopt v2 around a durable, idempotent iteration record; establish and test that contract before deleting the stage-loop machinery.
