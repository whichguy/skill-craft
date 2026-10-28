# Astra review: owed-outcome draft

Run 2026-10-27 through the `ask` agent: model_used `gpt-6-astra`, persona `codex-astra`, effort `max`, fallback `False`, exit `0`. Read-only request; no files changed in the repository. Code citations are Astra's own and were checked as recorded in [the journal](../shiploop-owed-outcome-journal.md).

## Question

Use MAX reasoning effort. This is a deep design review for the ShipLoop skill in the skill-craft repository (read-only; do not edit anything). Read the code you need; cite file and symbol for every code claim and mark each claim verified (you read it) or inferred.

## Problem
ShipLoop (skills/shiploop/scripts/) gives the model one packet per graph node ("action"). The model does the work, writes RUN/inbox/<action>.md with an `outcome`, and runs the printed callback `shiploop complete --run-dir R --action A`. The script picks the successor from the outcome. Outcomes: done, blocked, send-back, add-work (shiploop_stage_spec.OUTCOMES; inner stages allow subsets, e.g. verify: done|blocked|send-back). Inner stages also run a bound Until Loop (skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py): the model runs `start --receipt`, then each iteration `done_argv` with a JSON report {classification, exit_assessment, continuation_assessment, evidence, handoff}; the runtime maps the report to repeat / complete / stopped and rewrites the receipt (loops/<action>-terminal.json). ShipLoop's `complete` refuses unless that receipt is terminal and matches the contract rebuilt from state (shiploop_loops.check_terminal, check_loop_packet).

The owner's worry: the model executes the prompt's work and then never reports (never runs `done_argv` or `complete`). Owner's own framing, verbatim: "the context only matters. It doesn't need to know what step or stage it's in. I basically need to know: if it didn't call `done` with the appropriate condition, then I think that would be a problem. In reality, it's the edge state in a graph. It's like path A, B, or C: `done` would sort of default to A, which would mean next step and so forth."

## Verified facts (from this session)
- If no callback arrives, the script sees nothing. Only the host Stop hook catches it: shiploop_keepalive.stop -> _decide -> run_status (shiploop_protocol.hook_status). It blocks the turn end while the run is active and `progress` (revision.callback_attempts.improve_pass) changed since the last block; otherwise it allows ("no progress"). The block text (_continue_reason) is one generic sentence: run `shiploop next` and follow the packet.
- Stage Until Loop iterations are not in `progress` (only the Improve child's receipt is read, shiploop_protocol._improve_pass).
- keepalive.observe rewrites the whole binding on every ShipLoop driving command (next/complete/improve-*), dropping last_block_progress and turn_blocks; reproduced with recorded Claude payloads: block, then `shiploop next`, then stop -> block again; a loop-runtime command between stops does not reset, so the second stop is released.
- The runtime's `next` returns a byte-identical instruction before and after the iteration's work was done; its instruction is execute-then-report with a "recheck artifacts, do not reapply" guard. There is no report-only state.
- In an 18,317-character verify packet (graph-dry-run --scenario delivery --format markdown) the callback is stated at 5% and mentioned 7 times, all in the first 57%; the last 43% is references.
- Claude, Codex, Grok stop hooks can block with a reason; Cursor uses followup_message; headless Cursor/OpenCode never fire stop and need scripts/shiploop-drive; Grok caps 8 continuations per turn. Stop payloads carry last_assistant_message on Claude, Codex, Grok, not Cursor.

## Owner constraints
Scripts own navigation; the model does one step and reports, never holds graph state. One supported version: no compatibility modes or migrations. KISS: fix what breaks a normal run, no adversarial guards. Every command the model triggers must be a visible host tool call (no runtime subprocess running model commands). Context can be cleared between any two stages. No run or iteration caps, but a release valve for a model that ignores the hook is acceptable. Prompts concise.

## Draft design to critique ("owed outcome")
1. Invariant: after a packet prints, exactly one outcome is owed until accepted. The owed outcome is the innermost pending one: an active loop receipt owes an iteration report; otherwise a current action not yet accepted owes a stage outcome. Script-observable; the hook needs no stage knowledge.
2. hook-status returns owed: null or {level, prompt}; the navigator renders the prompt from state and the receipt (exit and repeat words, the exact command, the choices with done listed first). The hook only relays text.
3. Release valve keyed on outcome activity (revision, callback attempts, receipt action_number); observe stops wiping block memory. Two unanswered asks release the turn.
4. No script-side default edge; "default A" is only the order of choices in the prompt.
5. Collapsing the loop's terminal report and the stage `complete` into one edge looks blocked: the contract deliberately names no install path, and stage results carry stage-specific fields.

## Questions (answer each, numbered)
Q1. Is "owed outcome" the right minimal abstraction? Is there a simpler formulation that fits the owner's edge framing?
Q2. Which failure modes does the design miss (waiting on a person, ask-agent delegated workers, nested loops, compaction, hosts without a stop hook, a callback whose output was piped or backgrounded)?
Q3. Should the script ever take the default edge (done) without a model command? Give the strongest case each way, given that `done` needs evidence and gates.
Q4. Should the two levels collapse into one edge? If yes, the smallest mechanism within the constraints; if no, why.
Q5. Is "two unanswered asks, then release" right? Alternatives that keep no caps but cannot loop forever.
Q6. What to measure to prove the change works: metrics and a probe design.
Keep the answer under 1,300 words. End with your single strongest recommendation.

## Answer, verbatim

**Pilot the state-derived reporting prompt, while keeping both reporting boundaries.** No edits or tests executed. **V** means verified by reading source; **I** means inference or design recommendation.

1. **Q1. Is “owed outcome” minimal?**

   **I:** Yes, expressed as **“the next report this owner must submit.”** Derive it from authoritative state; avoid a separate debt ledger. The invariant should be *one actionable reporting obligation per owner*, with parent obligations suspended behind children. Packet printing should not create obligations: output can be lost or repeatedly requested.

   **V:** `next` emits the existing state; the runtime also regenerates its instruction without observing whether the work happened. [shiploop_navigator.py::dispatch](skills/shiploop/scripts/shiploop_navigator.py:9097), [until_loop_ephemeral.py::next_packet](skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:996).

   **I:** Therefore, say: “If this iteration is finished, report its actual findings; otherwise finish what remains. Recheck artifacts before changing them.” Include the exact command, conditions, schema and evidence locator. Missing prerequisites should produce start/recovery instructions.

   **V:** Loop reports use classification and assessments, not ShipLoop’s outcome enumeration. [until_loop_ephemeral.py::_report_schema](skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:642). **I:** “Done first” applies only to stage choices; the loop’s `done` command does not mean success.

2. **Q2. What failure modes are missing?**

   - **Waiting on a person. V:** Recorded waiting requires a blocked run and accepted `awaiting`; keepalive releases non-active runs. [shiploop_navigator.py::awaiting](skills/shiploop/scripts/shiploop_navigator.py:687), [shiploop_keepalive.py::_decide](skills/shiploop/scripts/shiploop_keepalive.py:492). **I:** Return no actionable report after that recorded wait. Before recording it, prompt for the blocked report. Do not infer waiting or success from `last_assistant_message`.

   - **Delegated workers. V:** The generated Improve handoff reserves completion for the parent after collection and receipt verification. [shiploop_navigator.py::_improve_handoff_top](skills/shiploop/scripts/shiploop_navigator.py:7306). **I:** Resolve the active Improve child before the producer. Tell its parent to collect the worker; do not hand the parent the worker’s iteration callback. Receipt terminality alone does not establish collection.

   - **Nested loops. V:** Explicit `--receipt` starts bypass automatic session-stack routing; session loops independently select their top frame. [until_loop_ephemeral.py::main](skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:1283), [until_loop_session.py::_active](skills/improve/runtime/until-loop/scripts/until_loop_session.py:239). **I:** “Innermost” needs recorded ownership/bindings; scanning for the newest active receipt cannot establish it.

   - **Compaction. V:** Recovery explicitly acknowledges that unsaved partial-action facts cannot be reconstructed. [until_loop_recover.py::packet_context](skills/improve/runtime/until-loop/scripts/until_loop_recover.py:72). **I:** Preserve context/evidence locators and regenerate commands. An unknown assessment must remain unresolved; context recovery must not manufacture completion.

   - **No Stop hook. V:** The driver compares only parent revisions and has a `max_sessions` ceiling. [shiploop_keepalive.py::_drive_sessions](skills/shiploop/scripts/shiploop_keepalive.py:945). **I:** Share the pending-report resolver and stall policy with the driver. Replace the absolute session ceiling to satisfy the owner’s no-cap constraint.

   - **Piped/backgrounded callbacks. V:** Observation can bind from command text when the output marker is absent; terminal loop completion persists its receipt before returning. [shiploop_keepalive.py::observe](skills/shiploop/scripts/shiploop_keepalive.py:313), [until_loop_ephemeral.py::done](skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:1127). **I:** Require collecting the command’s result and rereading state before retrying: it may already have succeeded. Shell return or missing output cannot identify the pending edge.

3. **Q3. Should silence take the default `done` edge?**

   **I:** No.

   The strongest case **for** automatic advancement is a terminal receipt plus a complete, explicitly chosen stage result: automation could deliver that result through every existing gate, eliminating a forgotten transport step.

   The strongest case **against** is that file presence does not establish submission intent or semantic readiness. **V:** `--check-only` deliberately validates drafts without accepting the action; real completion separately checks loop receipts and stage gates. [shiploop_navigator.py::dispatch](skills/shiploop/scripts/shiploop_navigator.py:9264).

   **I:** Automatic delivery would need an explicit readiness signal—effectively another callback. Silence supplies none. List condition-qualified `done` first without treating it as an omitted-value default.

4. **Q4. Should the levels collapse?**

   **I:** Keep them separate for this fix.

   **V:** A completed loop supports `done`, while a blocked loop supports either `blocked` or `send-back`; stage results additionally carry fields owned by particular stages and outcomes. [shiploop_loops.py::check_loop_packet](skills/shiploop/scripts/shiploop_loops.py:724), [shiploop_navigator.py::_canonical_result](skills/shiploop/scripts/shiploop_navigator.py:1015).

   **I:** These are different decisions: iteration convergence and graph transition. Portable install paths are not a fundamental obstacle to fusion: a ShipLoop-owned submission command could accept both payloads and perform deterministic library operations. But it would need recovery when loop acceptance succeeds and stage validation fails. That exceeds the missing-callback fix. A concise parent-return instruction preserves visible tool calls with much less machinery.

5. **Q5. Is “two unanswered asks, then release” right?**

   **I:** It is a reasonable pilot threshold for recovery reminders, not an empirically established optimum.

   **V:** `observe` replaces retry memory; callback attempts count regardless of acceptance; terminal receipts retain the finishing action number. [shiploop_keepalive.py::observe](skills/shiploop/scripts/shiploop_keepalive.py:330), [shiploop_protocol.py::_count_callback_attempt](skills/shiploop/scripts/shiploop_protocol.py:421), [until_loop_ephemeral.py::_transition](skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py:1065).

   **I:** Preserve reminder counts across rereads. Key obligations by action/child identity, runtime identity, action number **and status**. Reset on accepted reporting progress; raw callback attempts must not continually replenish reminders. An unchanged background-task flag must not exempt the run forever.

   Release automation with an explicit pending-report notice, leaving the run resumable. Automatic driver restarts must not erase that release. One reminder is simpler; two offers another recovery opportunity—measure both.

   **Verified documentation:** Claude’s current continuation cap resets after tool calls, so it cannot supply this guarantee. [Claude Stop documentation](https://code.claude.com/docs/en/hooks#stop).

   **I:** Unlimited accepted iterations necessarily permit indefinite execution. Promise bounded *unanswered recovery*, not universal termination.

6. **Q6. What would demonstrate improvement?**

   **I:** Compare baseline, corrected retry memory alone, and corrected memory plus the targeted prompt, using paired host/model trials.

   Inject stops after work but before loop reporting, after terminal receipt but before stage completion, and after accepted completion with discarded output. Include rereads, repeated refusals, compaction, worker collection, human waits and headless driving.

   Measure accepted-report recovery rate, false success/advancement, duplicate work, premature parent submission, false stalls, reminder count, tokens and recovery latency. Separate injected omissions from naturally occurring omissions.

   Assert deterministic safety cases first; then report live trial denominators and confidence intervals. Include a long sequence of valid iterations proving reminders do not become a run cap. Test that repeated unchanged refusals and rereads exhaust reminders without clearing the obligation.

**Strongest recommendation: replace generic “run next” nudges with the exact reporting instruction owed by the current owner, derived from authoritative state.**
