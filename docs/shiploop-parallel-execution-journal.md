# Parallel plan execution: journal

Living journal for the owner's 2026-11-14 question: do the dependency relationships ShipLoop records when it plans
let independent work run in parallel through each harness's own agent framework (Claude Code, Codex, Grok Build),
as an opt-in that is decided at run time from the plan and is the same on every harness? The first step is experiments in
pure isolation, with synthetic plans and no change to any skill, agent or catalog file. Registration, apparatus and
evidence: [docs/experiments/parallel-plan-execution-20261114/](experiments/parallel-plan-execution-20261114/README.md).

Statuses: **firm** (measured, replicated or by construction), **interim** (measured once, small n), **exploratory**
(a pilot or a reading), **superseded** (kept, with the date and reason).

## Entries

### R0 — 2026-11-14: grounding and registration (reading and registration, no experiment trial)

- Question: what do the plans record today, what did ShipLoop already do with it, and what is unmeasured?
- Method: read the step-plan validator and the packet builders in `skills/shiploop/scripts/shiploop_navigator.py`,
  `references/execution-planning.md`, `navigator.md`, `backchain-planning.md`, `inner-loop.md`, the Plan Dispatcher and
  In Parallel skill cards and their host references, `test/shiploop_e2e/fanout.py` and its LEARNINGS entries, and the
  full messages of the commits cited in the registration. A read-only subagent (Opus) produced a cited digest of the
  parallel-execution history; every claim used was checked against its source, and one was wrong (below).
- Result: findings F1 to F5. The registration, the apparatus plan and the predictions are in the experiment README,
  committed before any trial and before the E0 census report was read.
- Decisions (routine under AGENTS.md "Decisions"; what, why, evidence):
  - R0-D1. Profiles and models are the E2E harness's declared defaults (`HOST_DEFAULTS`, `ROLE_DEFAULTS` in
    `test/shiploop_e2e/hosts.py` at b777f69480d6e9457ccd67f02257c2bde6a4146b), so no new model choice is made here.
    The trial runner builds argv and environment through `hosts.host(name)` and adds receive timestamps and raw Codex
    events, which `hosts.run_agent` and `CodexTranslator` do not keep. Why: the timeline is the point of the study.
    This is the one deviation from use-the-codex-harness, whose reason (comparability of ShipLoop runs) does not apply
    to a study with no ShipLoop.
  - R0-D2. Arm A1 (one fresh agent per step, one at a time) is included beside the serial and parallel arms, because
    the retired chain's gain was never measured against a serial counterfactual (8eca9d64826e0073540b6029b6071fc91b553e8e)
    and a fresh context has a cost of its own (about 86k tokens on a fresh Claude subagent).
  - R0-D3. The kit refuses a premature start and logs the refusal, so a wrong model decision stays harmless and is still
    counted. Why: measuring violations by letting data corrupt would make the later outputs unreadable.
  - R0-D4. No ShipLoop or skill is installed in any probe profile; packets are plain text. Why: the question is about
    the harnesses' agent frameworks and a neutral packet, and a plugin would add hooks and instructions of its own.
  - R0-D5. The E0 census is delegated to a read-only Opus agent writing only under `census/`; my predictions for it
    were committed first. Why: it is long, mechanical, independent of the apparatus, and ShipLoop analysis goes to Opus
    under the agent-routing rule in experiments-use-sonnet.
  - R0-D6. Commits are local and docs-only; nothing is pushed. Why: no skill changes, so no release is involved, and a
    push to main is the owner's routine only for a finished unit.
  - R0-D7. Astra at max effort reviews the intention and plan before the first trial (astra-max-for-deep-design, missed
    three times before); its verbatim answer and my weighing of it are recorded in R1.
  - R0-D8. Codex runs in two profiles, the harness's (multi_agent v1) and the harness's plus `--enable multi_agent_v2`
    (the owner's own profile), each recorded and never pooled (README Amendment A1). Why: F6, found while checking the
    launcher with no model call.

### E0 — 2026-11-14: census of recorded step plans (offline, no model)

- Question (Q1): how much parallelism do the recorded step plans' `deps` expose, and what would perfect step-level
  parallelism save in recorded wall-clock?
- Method: [census/census.py](experiments/parallel-plan-execution-20261114/census/README.md), written and run by a read-only
  Opus agent, over all 19 `~/e2e-runs*` roots (hidden `.shiploop-runs/` included): one row per step-plan action id, shape
  from `deps`, write-set overlap from the plan's declared `paths`, and per-step iteration time from `trace.jsonl` (the
  first implement packet after the plan's acceptance to the `complete` that accepts the step's `document` stage, so it
  holds implement, test, document, the Improve review and any send-back; cross-checked against the commit ledger, 459 of 459
  checkable steps agree). I re-extracted the structure independently with my own walk and definitions: the same 322
  multi-step plans, 92 with an independent pair, 218 chains, 90 mixed, 12 ordered non-chains and 2 all-independent (my stricter
  filter keeps 921 plans, dropping the 6 legacy plans and 1 single-step plan). [census/gated.py](experiments/parallel-plan-execution-20261114/census/gated.py)
  (mine) adds a conflict-aware bound: independent steps whose declared paths overlap run in list order.
- Result (denominators named; all in evidence/census.json, summary.txt, gated.txt): 928 step plans from 787 work items, 750
  runs and 75 request families, dated 2026-10-03 to 2026-11-14. `deps` on every step in 922, on none in 6 (legacy), on some in 0;
  none names a later or unknown step. Of the 922: 600 single-step, 218 chain, 90 mixed, 12 ordered non-chain, 2
  all-independent. An independent pair exists in 92 (10.0% of 922; 28.6% of the 322 with two or more steps); width 3 in 23
  plans and 4 or more in 5. Of 203 same-level pairs, 90 overlap on declared paths, 86 are disjoint, 27 have no paths (51% of
  the 176 with paths overlap); of all 351 independent pairs, 61% of the 314 with paths overlap. A step iteration has median 154 s
  (p25 116, p75 212, max 1,866; 476 steps). Times exist for 323 of the 922 plans (243 predate `trace.jsonl`, 155 are seeded runs
  absent from the trace, 49 have fewer windows than steps, 152 are single-step with no implement packet in their window).
  Time-weighted ideal saving, 1 minus the sum of critical paths over the sum of serial times: 11.6% over the 323 timed plans
  (92,522 of 104,645 s), 20.8% over the 75 timed plans with two or more steps; per plan with two or more steps the median is 0 and
  the maximum 0.55, and only 21 of the 323 save anything; family-weighted (56 timed families) 1.6%, concentrated in ticket-service
  extensions, Battleship and chess. With overlapping-path steps kept in list order: 9.9% (17.7% for multi-step plans); the 21
  plans with a disjoint independent pair hold 32% of all timed time and, inside them, a gated saving of about 31% (the only plans
  that save anything). All timed
  plans have `paths`, so the strict and free readings of a missing `paths` agree.
- Predictions scored as registered (README, E0): **C1 held** (28.6% is within 10% to 35%); **C2 held as written** (11.6% is
  under 12%, by 0.4 points); **C3 held** (51% of pairs with paths overlap, at least 30%); **C4 held** (323 of 928, 35%, timed,
  fewer than half); **C5 missed** (6 of 928, 0.6% carry no `deps`, against at least a quarter predicted). Four of five held
  against probabilities of 55%, 60%, 50%, 65% and 45%.
- Readings, each on its own line, none a rescore: (a) C2's population includes 248 single-step plans, which dilute; over
  the 75 timed multi-step plans the saving is 20.8%. (b) R0 as registered turns on the ideal saving, 11.6%, which is in the band
  10% to 25%: "an opt-in for plans that expose width at least 2 and disjoint paths, a predicate a script can compute from the
  plan". The gated 9.9% was computed after the agent's numbers were in; it sits at the band's lower edge and does not move the
  outcome, because that band's action already includes the disjoint-paths gate.
- Contrary evidence and limits: the population is E2E test cases (small, specified, repeated); the time rests on 75 timed
  multi-step plans from a few families; the bound assumes unlimited workers, unchanged step times, no merge cost and that a step's
  test, document, review and commit could run beside another step's, which design T's per-step iteration and commit stage do not
  allow without isolation; `paths` are declared, not the files changed. A true dependency the plan failed to declare would make a
  pair look independent: the three hand-read cases (Apex chess S2 to S5, Battleship S2 and S3, a Node chess step that names S2
  without depending on it) are anecdotes, not a rate.

### R1 — 2026-11-14: Astra max-effort review of the registration, before any trial

- Question: is the intention understood, are the premises true, will the design and the apparatus measure what they claim, and what
  should run first? Asked as the owner's rule requires (astra-max-for-deep-design, missed three times before): `ask.sh astra --json
  --effort max --profile consult`, read-only, no fallback, over the canonical checkout; the question is
  [evidence/astra-question.txt](experiments/parallel-plan-execution-20261114/evidence/astra-question.txt) and the answer is
  [evidence/astra-review.md](experiments/parallel-plan-execution-20261114/evidence/astra-review.md), verbatim. It read the registration,
  the commits the registration cites and, while it ran, the apparatus I committed.
- Verified before weighing: its factual correction (the per-step pilot did run, `eadad0c8`, read in full), its launcher bug (reproduced
  with a fake host), and every scorer and kit defect it listed (each written as a failing calibration cell first: 23 of 26 failed on the
  unfixed code; two it reported from in-memory checks, the unrelated-spawn and the pathname cases, errored on the new signature and are
  covered by passing cells). I found no claim of its that was wrong. I did not check its statements about Claude's documented nesting
  and concurrency defaults or about Codex's and Grok's public documentation; E1 qualifies the live tool schemas.
- Weighing, point by point (decisions routine under AGENTS.md "Decisions"):
  - **Adopted, framing (P0):** the synthetic units are a mechanism test, not permission for concurrent ShipLoop steps; the bridge is
    parallel work inside one stage with one owner; "true dynamic workflow" is completion-driven execution under one authority (README A2).
    The owner's own rule makes this binding: a step is built, tested, documented, reviewed and committed before the next.
  - **Adopted, intention (P0, P1):** outcome-only retention and stale-state interaction come forward as small E6 and E7 designs (README A4);
    a planning fan-out test (independent agents inspect separate supplied evidence, one owner builds or audits the dependency plan, edges scored
    against a hidden oracle) is recorded as design E8 for round 2, not built.
  - **Adopted, premises:** the pilot erratum, the narrowed dependency claim, the translator wording, the frozen Codex profile, effective
    capabilities and child model identities recorded per trial (README A2). The pilot (F13) changes the prior for A1's overhead.
  - **Adopted, design:** A3s as the matched serial control; capacity recorded; the measure corrections (launch-to-verified and
    launch-to-exit beside the makespan, tails kept apart, valid-trial-only savings, categorized refusals, an exactly-one-terminal verify,
    parent-only report, attribution-gated mechanism); mechanical scoring clarifications for P3, P4, P6, P8, P9, P11, R1; R2 renamed; R0,
    R3, R4 narrowed; stop rules and the R5 redirect; N kept as an elicitation experiment and H (a small host binding from the repository's
    own recipes) as the operational route (README A3, A4).
  - **Adopted, apparatus (P0, P1):** all six P0 blockers and the kit-contract items, fixed in 3c8e1cb6c42b5f4f17890a6959b9116640f21565.
  - **Adopted, order and spend:** no-model qualification first (done), then Claude E1 aimed at return and exit, Codex and Grok next, fan4 A0,
    A3s and A3, then `ragged6` A3, then failure and context; timing trials one at a time with arm order counterbalanced; Codex's two profiles
    not multiplied across every arm (README A3).
  - **Adapted:** "run A2 later": A2 stays on `fan4` because P1 is registered on A2 and "did not apply" is not a registered outcome; it is dropped
    from the later fixtures. "Freeze which profile scores a prediction": the harness profile scores, `+v2` is exploratory.
  - **Deferred, with a rule to revisit:** a full claimed, launch-confirmed, running, returned, accepted state machine. Capacity-limited claims,
    release, claim ages and a stranded-claim measure answer this study's question (does a host launch and return); the full machine would
    rebuild the retired Plan Dispatcher. Revisit if a trial strands a claim. The shell-yield and native-observation timeout classes are
    recorded only when E1 events show them; the runner records the outer deadline.
- Process lesson, recorded because it cost a wrong sentence in a committed registration: I read the commit that proposed the pilot
  (f824adeb) and did not search forward for its result, and the history digest repeated "never run". The owner's rule is to search older
  history for the affected behaviour; for a commit that says "proposed" or "not run", the search is for its sequel.
- Design E8 (not built): planning fan-out. Hidden oracle: a fixture request whose true dependency edges are known; arms: one agent plans, or
  several agents each inspect a separate slice of supplied evidence and one owner assembles the plan; measures: omitted edges, invented
  edges, wall-clock, tokens. It answers the owner's "when we do the planning" directly and needs no write isolation.

### E1 — 2026-11-14: one fresh native sub-agent per host, headless (the qualification probe)

- Question: can each harness's own agent infrastructure be driven headless from a neutral text packet, with the sub-agent's work attributable
  to it and a clean exit? Method: arm A1 on `one1` (one 5 s step), packet N, one trial per condition: Claude Code 2.1.325 (`claude-sonnet-5-5`),
  Codex 0.169.0 (`gpt-6.1-sol` medium) in the harness profile and with `--enable multi_agent_v2`, Grok Build 1.0.77 (`grok-4.6` xhigh); the
  four ran side by side (a qualification, not a timing comparison). The registered arms and predictions of E2 and E3 are not run (superseded
  by R2). Evidence: the trial folders were scored with the registered scorer after the reader fixes in
  3c8e1cb6c42b5f4f17890a6959b9116640f21565.
- Result: all four trials completed with the step run once and `verify` OK, exit 0 and no lingering process. **Claude:** the parent read the plan,
  spawned an `Agent` (`subagent_type` general-purpose, `is_backgrounded` false, `spawn_depth` 1); the sub-agent ran the command (attributed
  by `parent_tool_use_id`) and returned through a `SubagentHandback` call; 19.6 s elapsed for the 5 s step, process exit 2.9 s after the final
  report, $0.137, input tokens 188,154 including cache (parent 135,698, children 52,456; the child's own context 27,229 tokens). **Codex:**
  the parent called `spawn_agent` (`task_name`, `fork_turns` "none", message encrypted) and `wait_agent`; a child thread with its own rollout
  file ran the command (depth 1); `exec --json` showed only the `wait` and none of the child's events; 34.5 s elapsed in both profiles; input
  tokens 117,447 (parent 80,783, child 36,664). In both profiles the child's `multi_agent_version` is v2. **Grok:** the parent called
  `spawn_subagent` (general-purpose, `background` false, model inherited from the parent); the child's call appears in the stream and
  `unified.jsonl` gives each call's session id, so it is exactly attributable; 31.5 s elapsed, 93,251 input tokens in the end usage (whether
  that figure includes the sub-agent is not established), $0.087. Grok's first scoring said `final=none` because its closing message streams
  as 123 text deltas; the reader now joins the trailing deltas.
- Reading: native sub-agents work headless on all three, one at a time, from a neutral packet, and each host keeps its own account of them (Claude
  in the stream, Codex in rollout files, Grok in its log), so attribution needs no hooks. The Claude headless failure documented on 2.1.296
  (a coordinator returning before its workers, or not exiting) did not occur here; this was one foreground sub-agent, not a nested coordinator or a
  background worker, so it is not a general qualification. Parallel launch, completion-driven refill and real work are untested.

### R2 — 2026-11-14: the owner's course correction, and the pivot to native agents doing real work

- The owner's words (mid-session): "My hope was not actually to use bash calls as subagents. I was hoping to use the native agent
  infrastructure of the harnesses, but I'm not sure if it's possible or not. You don't necessarily have to reuse some of the things that I've
  previously created, but you can leverage it if you think it's valuable. Help me figure out what the right thing is to do here."
- Reading: E1's sub-agents were native, but the payload (a sleeping shell command) tests neither a fresh context doing work nor an outcome
  returned to a small parent; the design should not look as if a bash call were the agent. Decision (routine; direction-setting parts are put to
  the owner in the closing message): keep E1 as qualification; replace the payload with real analysis work done by the fresh sub-agent; keep the
  script as the single authority for readiness, instructions and recorded outcomes (the ShipLoop shape: print the step, the model does it,
  the model calls back), because ShipLoop talks to its script by command anyway; cross-check that the workers were native agents with each
  host's own record. README Amendment A5 registers the design and predictions P16 to P24 before any task trial. Not reused: Plan Dispatcher and
  In Parallel (their protocol is the heavy one: 587 s for a 60 s ideal in the Codex fan-out; a script-owned ready set tests the same idea with
  the least machinery), kept as the comparison if the light route works.

### R3 — 2026-11-14: the owner's model profiles

- The owner (mid-session): "The models that we should be using to run tests with harnesses would be Sonnet at high, Grok 4.6 at extra high, or
  SOL-6.1 on medium", then "If you need to just test basics first, you can just use grok as your first basic test just to see if things are working."
- What was wrong: my Claude trials (E1 and the first two pilot trials) went through `test/shiploop_e2e/hosts.py`, whose Claude host has no effort,
  so no `--effort` was passed and they ran at the CLI default. Grok (xhigh) and Codex (Sol medium) already matched. Decision (routine; I did not change
  `hosts.py`, whose defaults are a comparability question for the owner): rerun the Claude cells with `--effort high` (`r1h-claude-a3`, `r1h-claude-a0`,
  `e1h-claude`), keep the default-effort Claude trials as a separate exploratory cell, score the Claude predictions on the high-effort cell, and
  check anything new on Grok first (README Amendment A6, committed before any high-effort result was read). Saved to memory as
  harness-test-model-profiles-2026-11-14.

### E9 — 2026-11-14: native agents on real work, per harness (the pilot; fixture analysis5)

- Question: with the script printing the ready set and each task's instructions, can each harness's native sub-agents do real analysis in fresh contexts,
  in parallel, from one anonymous packet, and what does that cost against the parent doing every task itself? Method as registered (README A5, committed in
  1b4fa27287692c242c2f52c98762509b8bde3203; the profiles in A6, 6d574c9fc8f0385304496caa395e069483b8a14d): fixture `analysis5` (four independent log analyses,
  then their sum, 400 events per log, seed 20261114, oracle outside the agents' directory), arms A0 (one context does all five) and A3 (script-owned ready set,
  fresh native sub-agents, capacity five), one trial per cell, arm order counterbalanced (Claude A3 then A0, Codex A0 then A3, Grok A3 then A0), three hosts side
  by side. Profiles: Claude Code 2.1.325 `claude-sonnet-5-5` at `--effort high`, Grok Build 1.0.77 `grok-4.6` xhigh, Codex 0.169.0 `gpt-6.1-sol` medium. The
  first Claude pair ran at the CLI default effort before the owner's instruction (journal R3) and is an exploratory, unpooled cell; the high-effort pair was
  launched after it and read after A6 was committed. Evidence: `evidence/r1h-claude-*`, `r1-grok-*`, `r1-codex-*`, `r1-claude-*`, `e1h-claude`, the pages
  `evidence/pilot-timeline.html` and `e1-timeline.html`, and `pilot_table.py`, which prints the table below from the score files.
- Result (seconds; tokens include cache; "parent" is the parent's own input tokens): every task trial, nine in all counting the exploratory pair and E1 at high,
  completed with verify OK, a faithful report, exit 0 and nothing left running; all eight task trials answered all five tasks correctly.

  | host, effort | task makespan A0 / A3 | launch to first task | wait before T5 | whole run A0 / A3 | input tokens A0 / A3 (parent in A3) | cost A0 / A3 | agents, peak |
  |---|---|---|---|---|---|---|---|
  | Claude Sonnet 5.5, high | 27.7 / 21.9 | 4.4 / 12.3 | 2.3 / 6.7 | 35.4 / 43.2 | 555,668 / 932,405 (404,872; first read as 133,640, superseded: see the correction below) | $0.152 / $0.363 | 5, 4 |
  | Grok 4.6, xhigh | 65.3 / 50.4 | 7.6 / 33.0 | 3.8 / 15.8 | 81.4 / 96.1 | 867,154 / 659,155 (the whole run, children included; the parent's own 185,909 is in `context.json`; first reported as scope unknown) | $0.593 / $0.630 | 5, 4 |
  | Codex Sol 6.1, medium | 75.7 / 70.4 | 10.6 / 22.1 | 6.9 / 19.8 | 100.3 / 109.9 | 449,485 / 706,535 (328,246) | not reported | 5, 3 |
  | Claude, default effort (exploratory) | 29.8 / 20.3 | 4.5 / 12.2 | 1.9 / 7.4 | 37.5 / 39.9 | 524,909 / 875,481 (352,846; first read as 87,811, superseded) | $0.162 / $0.516 | 5, 4 |

  **Correction (2026-11-14, journal R4; supersedes the parent figures above and reading (c) below).** In `-p` mode Claude emits one `result` event per
  parent turn (a background sub-agent's completion re-enters the parent as a new turn: three result events in each Claude A3 trial), each result's `usage`
  covers its own turn only, and `modelUsage` and the cost are cumulative. The scorer read only the last result, so the parent's input in Claude A3 was
  understated (133,640 and 87,811). The sum over all result events is 404,872 and 352,846, and the per-call record (`context.py`, the stream's assistant
  messages) gives the same parent figure and the same all-contexts total on all six Claude trials. The corrected ratio of the parent's input in A3 to A0 is
  0.73 (Claude high, 404,872 / 555,668) and 0.67 (Claude default), not 0.24 and 0.17. The all-contexts totals, costs, times and every other figure in this
  entry were never affected. The defect was reproduced as a failing calibration cell before the fix.

  A3 against A0: task makespan 0.79, 0.77 and 0.93 times (Claude high, Grok, Codex); whole run 1.22, 1.18 and 1.10 times; input tokens 1.68, 0.76 and 1.57 times.
  The task phase shortened by 5.7 s, 14.9 s and 5.3 s, and the cost outside the task phase (the parent planning and spawning, the children starting, the join, the
  tail) rose by 13.6 s, 29.6 s and 14.9 s, so the whole run was 7.8 s, 14.7 s and 9.6 s longer. How each host launched: Claude spawned in background mode (four
  `Agent` calls over about 5 s, from 4.8 s to 10.2 s; the stream does not show whether they came in one message or several; the sub-agent type was chosen by the model: general-purpose in all but one trial, where it chose `claude`); Grok spawned four
  background `spawn_subagent` calls over 11 s to 25 s and waited on all four with `get_command_or_subagent_output`; Codex spawned three (`spawn_agent`, `fork_turns` "none"),
  waited with `wait_agent` in 10 s slices and **released the fourth claim** because its tool description says "There are 4 available concurrency slots, meaning that up to 4
  agents can be active at once, including you", then launched T4 after the first wave. On Claude and Grok the children began together when the parent yielded its turn,
  not when each spawn was issued. A3's `ready` line was consistent in every trial: no refused attempt, no duplicate start; the release path (added after the review) was used once.
- Predictions scored as registered (README A5): **P16 held** (Claude high peak 4); **P17 held** (Codex peak 3); **P18 held** (Grok peak 4); **P19 held** (all eight task
  trials answered 5 of 5); **P20 held** on all three hosts, by task makespan; **P21 missed as written** (Claude 1.68 and Codex 1.57 times, Grok 0.76); **P22 held** where the
  figure separates the parent (Claude 404,872 against 555,668, first read as 133,640; Codex 328,246 against 449,485; Grok first not scored, scored 2026-11-14 from its per-call log, parent 185,909 against 867,154, held); **P23 held** (every exit 0, tails 0.4 s to 2.5 s since the final
  report); **P24 missed** (no host's agent peak was 1). Seven of nine held against 70%, 55%, 50%, 75%, 70%, 70%, 80%, 70% and 40% (about 5.8 expected). Decision rule **R6**: all three
  hosts satisfy it (valid A3 trial, five correct answers, a faithful report, exit 0, peak at least 3 in both the host's own agent record and the ledger). The synthetic predictions
  P1 to P15 registered for E2 and E3 were never tested: those trials were superseded by this design (A5) before they ran.
- Readings, each on its own line, none a rescore: (a) P20 holds by the registered measure while the whole run is longer on every host (above). (b) ~~P21's miss rests on Grok's figure,
  whose scope is unknown (Claude's `usage` was the parent only and `modelUsage` the whole run; if Grok's end usage also leaves out its children, its 0.76 understates A3).~~
  Resolved 2026-11-14 (R4): Grok's end usage covers its sub-agent sessions (659,155 = the parent's 185,909 + five children, 473,246, from its per-call log), so 0.76 is the whole run:
  Grok's A3 used fewer input tokens than its A0 (its single context grew from 14,417 to 43,759 tokens over 24 calls) although it cost 1.06 times as much. (c) ~~In A3 the
  parent's own input tokens fall to 0.24 (Claude) and 0.73 (Codex) times A0's: the outcome-only retention the owner described holds, strongly on Claude, modestly on Codex.~~
  Superseded 2026-11-14 (R4, the correction above): the parent's own input in A3 is 0.73 times A0's on both Claude and Codex, so outcome-only retention holds, modestly, on both.
- Limits: one trial per cell, so no rate and no claim that a difference of a few seconds is real; one read-only workload with 5 s to 24 s tasks (short against the fixed cost); no
  write conflict, no commit, no isolation; three hosts ran side by side and a later trial may have profited from caches an earlier one warmed (order counterbalanced, not removed);
  load average 5 to 8 on the machine; Grok's and Codex's agent types and models were the hosts' defaults (Grok inherited its model, Codex pinned the child to Sol medium).

### R4 — 2026-11-14: where the pilot's time and tokens went, and how to read a 5 s to 24 s result (analysis of the nine pilot trials; no new trial)

- The owner's questions (mid-session): "Dig deeper on the timeline analysis as well as the costs for things, and make sure that we're not over-pivoting on small tasks and small measurements.
  If the startup, shutdown, and merging are all excessive relative to much more lengthy runs, this could be problematic. If we use just small test cases where the amount of work was so small that
  the actual startup and merging time of multiple agents was actually material, that might be a different story. Help me understand how we should review and think about this." And: "my intention
  is to introduce a skill layer that abstracts shiploop from the mechanics ... We would be able to differentiate, in the skill, which harness we're running in, and then make the appropriate call on
  how to dispatch and merge the agent." Reading: the pilot's tasks (5 s to 24 s) show the fixed costs of fan-out; the owner's doubt is exactly whether those costs stay fixed or look large only
  because the work was small. The second message sets the product shape: a skill layer with a contract (what ShipLoop asks) and per-harness bindings (how each host dispatches and collects).
- Method: `phases.py` splits each trial, from the ledger and the host's own agent record, into orient (launch to the first `ready`), spawn (first `ready` to the last spawn of the first round), start (last spawn
  to the first task `begin`), work (first `begin` to the last independent task's end), join (that end to the dependent task's `begin`), integrate (the dependent task) and tail (its end to the process exit).
  `context.py` reads every model call's context size per thread from each host's own record. A correction that came out of reading both is in E9 and in the commit a80d73d4072571484e397624b48ac01cca17fb20.
- The phases (seconds from launch; n = 1 per cell, so these locate costs and do not size them):

  | trial | orient | spawn | start | work | join | integrate | tail | whole |
  |---|---|---|---|---|---|---|---|---|
  | Claude A0 / A3 | 2.3 / 2.4 | 0 / 7.9 | 2.2 / 2.0 | 21.1 / 7.5 | 2.3 / 6.7 | 4.2 / 7.8 | 3.3 / 9.0 | 35.4 / 43.2 |
  | Grok A0 / A3 | 4.0 / 3.4 | 0 / 22.0 | 3.6 / 7.5 | 52.3 / 24.1 | 3.8 / 15.8 | 9.2 / 10.5 | 8.5 / 12.7 | 81.4 / 96.1 |
  | Codex A0 / A3 | 7.5 / 8.9 | 0 / 12.9 | 3.1 / 0.4 | 58.0 / 41.0 | 6.9 / 19.8 | 10.7 / 9.6 | 14.0 / 17.4 | 100.3 / 109.9 |

- What each cost scales with. Per agent (serial parent turns): spawn, 7.9 s, 22.0 s and 12.9 s for four, four and three spawns (Claude issued its four `Agent` calls in one assistant message about 1.9 s apart, consistent with the model
  writing each child's prompt in turn; Grok's four `spawn_subagent` calls came 4.3, 5.6 and 3.5 s apart and Codex's three `spawn_agent` calls 6.8 and 5.6 s apart, so they look like separate model turns
  but the streams do not prove it, which is what E11 tests). Per round: the join (+4.4, +12.0, +12.9 s: the parent notices the return, asks `ready`, spawns the dependent task, the child starts; Codex also polls
  `wait_agent` in 10 s slices) and the tail (+5.7, +4.2, +3.4 s). Proportional to the work: the work phase (21.1 to 7.5 s on Claude and so on), and, in A0, the growth of the single context. Not scaling with
  anything measured: orient and start are the same in both arms to within a few seconds (orient 0.1, -0.6 and 1.4 s; start -0.2, 3.9 and -2.7 s).
- Break-even from these cells. Outside the work phase A3 added 21.4 s (Claude), 43.0 s (Grok) and 26.6 s (Codex) (from the unrounded ledger by `scaling_table.py`; the displayed phases sum to 21.5, 42.8 and 26.8) and took 13.6 s, 28.2 s and 17.0 s off the work phase, net +7.8 s, +14.7 s and +9.6 s. If every task
  took S seconds longer, A0's work phase would grow by 4S and A3's by S (Claude, Grok: four children at once) or 2S (Codex: three children, the fourth in a second wave), so the saving grows 3S (Claude, Grok) and 2S
  (Codex). The whole run then breaks even at S = (21.4 - 13.6) / 3 = 2.6 s (Claude), (43.0 - 28.2) / 3 = 4.9 s (Grok) and (26.6 - 17.0) / 2 = 4.8 s (Codex) more per task than the pilot's: the pilot's tasks were
  about 5 s, 13 s and 15 s each in A0, so the fan-out pays from roughly 8 s, 18 s and 19 s a task. The pilot sat 3 s to 5 s per task short of break-even on every host. Its verdict (the whole run was longer) is true and
  is mostly a statement about how short the tasks were. The model's whole-run predictions, registered before E12 runs (A0 = pilot + 5S; A3 = pilot + 2S on Claude and Grok, + 3S on Codex, whose three slots run
  T1 to T3, then T4, then T5): S = 30: Claude 185 / 103 s (ratio 0.56), Grok 231 / 156 (0.67), Codex 250 / 200 (0.80); S = 90: Claude 485 / 223 (0.46), Grok 531 / 276 (0.52), Codex 550 / 380 (0.69).
- Where the model can be wrong (a cost that is not fixed): the join waits for the slowest of four, so spread among the children grows with S (the expected maximum of four draws is about one standard deviation
  above their mean); a parent that polls turns waiting into model calls; four simultaneous model calls can meet a rate limit that one does not; a long command can be cut or backgrounded by the host; and for writes
  there is a merge or an integration check the read-only fixture does not have (unmeasured). E12 tests the first four; the last needs a write fixture.
- Tokens: a different shape, and a model, not a measurement. Per-call context (context.json): A0's single context grows 495 (Claude), 1,276 (Grok) and 342 (Codex) tokens a call; a fresh child starts at 24,152,
  9,948 and 18,234 tokens against the parent's 33,316, 14,417 and 15,847. At the pilot's three to five calls a task, a child costs about what a task costs inside A0 (Claude: about 105.5k against 111k), so A3's extra
  tokens on Claude and Codex are the parent's orchestration turns (Claude 10 calls and 404,872 tokens against A0's whole 555,668; Codex 18 calls and 328,246 against 449,485), and on Grok A3 is cheaper outright
  (children 473,246 plus the parent's 185,909 = 659,155 against 867,154). A0's total is quadratic in the work (the sum of a growing context over all calls); each child's is quadratic only in its own task. Fitted to the
  measured start, slope and parent constant, with n = A0 calls per task and children one call longer: Claude A0(n) = 165,343 n + 6,188 n^2 and A3(n) = 1,238 n^2 + 121,998 n + 525,632 (the fit gives 551,715 and 902,762
  at n = 3 against the measured 555,668 and 932,405), equal at n = 6.8 calls a task and 0.50 at n = 30 and 0.32 at n = 100; the same fit on Codex gives equal at about n = 12; Grok's A3 is already below A0 at the pilot's
  n = 5. Assumptions: linear growth per call (compaction would reset it), a parent constant that does not grow with task length (a polling parent breaks it), no cache pricing (dollar cost counts cache reads at a
  tenth). It says the pilot's "more tokens" is a small-task effect, not that long tasks are cheaper; the settle dial adds time, not calls, so it cannot test this: that needs a second dial (tasks with many more calls).
- How to read a result like the pilot's (the owner asked): (1) split each cost by what it scales with (per run, per agent, per round, per unit of work) before judging a total; a total at one task length hides which
  part moves. (2) Compare with the real unit: a recorded ShipLoop step iteration has median 154 s (F11), 20 to 30 times the pilot's tasks. (3) Report a cost curve, here a break-even task length per host, not
  a win or a loss at one point. (4) List the costs that are not fixed and test those. (5) With one trial per cell, differences of a few seconds are noise; read shapes and orders of magnitude. (6) Keep the owner's order,
  quality then tokens then time: both the fan-out's time and its token cost depend on the task length, in opposite directions for tokens in A0. (7) The pilot is silent on merging, isolation and write conflicts: for
  read-only work the integration is one cheap outcome read; for writes that is the part most likely to be fixed-cost-heavy or not fixed at all, and it needs its own fixture before any claim.
- Next, registered in README A7 before it runs: E10 (can the skill tell its harness, in the parent and in a sub-agent), E11 (does host-specific wording beat the anonymous packet), E12 (the settle dial: the same
  two arms at S = 30 and S = 90 on all three hosts). The skill-layer contract follows them. Nothing here changes a skill, an agent card or a default.

### E10 — 2026-11-14: can a skill tell its harness, in the parent and in a native sub-agent? (the identity probe; one trial per host)

- Question and method (README A7, committed in 7e68c9f03ddb5d7ef4d53926c207e43f5083a4a6 before any trial): the parent runs `whoami.py`, starts one fresh native sub-agent that runs it too, and
  reports both lines and the names of the tools each has for starting or waiting for another agent. `whoami.py` prints what the repository's own `detect_host`
  (skills/shiploop/scripts/shiploop_grants.py, imported read-only) says, the marker names (never values), the last six characters of thread and session ids and the process ancestry. Profiles as the owner
  set them: Grok 4.6 xhigh, Claude Sonnet 5.5 `--effort high`, Codex Sol 6.1 medium; Grok first, then the other two side by side. Evidence: `evidence/e10-{grok,claude,codex}/` (`identity.json`, the
  trimmed events, the host's own sub-agent record).
- Result:

  | host | parent detects | sub-agent detects | id variable, parent / sub-agent | parent's native-agent tool | sub-agent lists an agent tool | native agents (host record) | seconds |
  |---|---|---|---|---|---|---|---|
  | Grok 1.0.77 | grok | grok | GROK_SESSION_ID 11e0cf / ec62f4 | `spawn_subagent` | no (it lists `run_terminal_command`, `get_command_or_subagent_output`, `wait_commands_or_subagents`, `monitor`, `scheduler_create`) | 1 (general-purpose) | 52.6 |
  | Claude Code 2.1.325 | claude | claude | CLAUDE_CODE_SESSION_ID 8476b5 / 8476b5 (the same) | `Agent` (the init event lists it as `Task`) | yes, `Agent` | 1 (general-purpose, depth 1) | 30.5 |
  | Codex 0.169.0 | codex | codex | CODEX_THREAD_ID 3585e8 / bc3ab5 | `collaboration.spawn_agent` | yes, `collaboration.spawn_agent` | 1 (depth 1, multi-agent v2) | 35.3 |

- Predictions scored as registered (README A7): **P25 held** (the parent's `detect_host` named the launched host on all three); **P26 held** (so did the sub-agent's); **P27 held** (the sub-agent's
  thread or session id differed on two hosts, Grok and Codex; on Claude the session id is the same); **P28 held** (each parent reported its native tool; Codex's name carries a `collaboration.` namespace,
  Claude's init event calls it `Task`); **P29 missed** (the Claude and Codex sub-agents reported a tool for starting another agent; only Grok's did not). Four of five against 85%, 75%, 60%, 75%, 65% (about 3.6 expected).
- Readings, each on its own line: (a) The environment detection the repository already has works in both contexts on all three hosts, from the environment alone. (b) The environment also carries the
  launching session's markers into the host: `CODEX_COMPANION_SESSION_ID` and `CODEX_COMPANION_TRANSCRIPT_PATH` (a Codex plugin's variables, set by the Claude session that ran the harness) appear in the Grok and
  Claude environments, and `OPENAI_API_KEY`, `XAI_API_KEY` and `ANTHROPIC_BASE_URL` names in all three: a detector that matched the prefix `CODEX` would call Grok and Claude "codex" here. `detect_host`
  checks exact names (`CODEX_SANDBOX`, `CODEX_THREAD_ID`, `GROK_AGENT`, `GROK_SESSION_ID`, `GROK_SANDBOX`, `CLAUDECODE`), innermost first; the contract must keep that. (c) Process ancestry shows the nearest
  host binary (`grok`, `claude`, `codex`), but under Grok the chain continues through the launching Claude session (`zsh, grok, Python, zsh, claude, ...`), so ancestry is usable only as "the nearest host
  ancestor" and is weaker than the exact markers. (d) A sub-agent cannot tell that it is one from its environment on Claude (same session id) and has no depth marker on any host; "you are a worker, do not start
  agents" has to be in its instruction, and the script's `begin` lease is the guard. (e) Children on Claude and Codex list an agent tool: nesting is offered; whether a grandchild would run was not tested (Codex
  child rollouts record depth 1).
- Limits: one trial per host; the environment was built by the E2E harness's host adapters from the launching session's (so the owner's own interactive sessions may carry other markers); a model's list
  of its tools is a report, not the schema (the schema is in the host's own records: Grok's `tool_definitions.json`, Claude's init event); host-in-host nesting, and a skill running inside another host's
  sub-agent, were not tested.

### E11 — 2026-11-14: does host-specific wording beat the anonymous packet? (Grok: N twice, H twice; Claude and Codex H are exploratory, README A8)

- Question and method (README A7, committed in 7e68c9f03ddb5d7ef4d53926c207e43f5083a4a6): the A3 packet N against N plus a one-paragraph host binding H (`packets/H-grok.txt`, sha256 7e4abaf82094c6530bd052d756fea58f15a521d80a5bdb3838e1abbcc6f2a8a6: all spawn
  calls for the ready ids in one response, a long wait). Grok Build 1.0.77, `grok-4.6` xhigh, fixture `analysis5` at S = 0, the pilot's `r1-grok-a3` as the first N and `e11-grok-n2` as the second, `e11-grok-h1` and `e11-grok-h2` as H, run one at a time in the order H, N, H.
  Evidence: `evidence/e11-grok-*`; `python3 scaling_table.py --e11` prints the table.
- Result (seconds from launch; the pilot's trial first):

  | trial | spawn | start | work | join | whole run | parent model calls | spawn calls per parent model call | valid |
  |---|---|---|---|---|---|---|---|---|
  | r1-grok-a3 (N) | 22.0 | 7.5 | 24.1 | 15.8 | 96.1 | 9 | [4, 1] | yes |
  | e11-grok-n2 (N) | 21.7 | 6.7 | 27.5 | 15.2 | 99.3 | 9 | [4, 1] | yes |
  | e11-grok-h1 (H) | 19.6 | 8.3 | 27.1 | 14.8 | 93.4 | 9 | [4, 1] | yes |
  | e11-grok-h2 (H) | 24.4 | 6.0 | 36.5 | 13.6 | 104.2 | 9 | [4, 1] | yes |

  Means: spawn phase N 21.9 s, H 22.0 s; whole run N 97.7 s, H 98.8 s. All four answered 5 of 5 with verify OK, no refused attempt, peak 4.
- Predictions scored as registered (README A7): **P30 missed** (H shortened the spawn phase by -0.2 s, the bar was 8 s); **P31 held** (both H trials valid, no refused attempt); **P32 missed** (-1.1 s against an 8 s bar). P33 and P34 were gated on P30 and are
  addressed in A8.
- Reading: the motivating guess was wrong, and the logs show why. In every Grok trial, N included, the parent issued all four `spawn_subagent` calls in **one** model call (`shell.tool.exec_done` ids share one prefix with suffixes -1 to -4; the parent made 9 model calls
  in all four trials). The stagger between the spawns in the stream (3.4 s to 5.6 s) and the 18 s to 19 s between that model call's end and its tool batch's return are the host starting each child in turn: each call's own execution is 7 ms. So the N packet's "all together in the
  same turn" already gets what H asks for, and the per-agent spawn cost on Grok is the host's. The same reading of the other two hosts' pilot records (`context.py` `parent_turns`): Claude issued its four `Agent` calls in one model call, about 1.9 s apart (consistent with the model
  writing each child's prompt in turn), and Codex spent one model call on each `spawn_agent` (five calls, 5.6 s to 6.8 s apart): the three hosts pay their per-agent cost in three different places.
- Noise: two trials of the same condition differ by 3.2 s (N: 96.1, 99.3) and 10.8 s (H: 93.4, 104.2), and the work phase varied from 24.1 s to 36.5 s, so a difference between single trials of under about 10 s is not a signal.
- Decision (R8, as registered): H does not enter the contract for Grok; the bindings table carries the measured per-agent cost instead. A8, registered before the trials, runs H once on Codex (where wording has a mechanism) and once on Claude, as exploratory cells.
- Limits: four trials, one host, one fixture at S = 0; the effect of a wording could differ at other task lengths; the same-condition spread is two pairs.
- Exploratory cells (README A8 and A9, registered before they ran, never pooled with the registered cells; one trial each): **Claude H at S = 0** (`e11-claude-h1`, `--effort high`): the parent again issued its four `Agent` calls in one model call ([4, 1]); the whole run 39.6 s against the pilot's N 43.2 s,
  so **P33 held** (within 5 s, +3.6 s). **Codex H at S = 0** (`e11-codex-h1`, capacity 3): the parent still spent one model call on each `spawn_agent` ([1, 1, 1, 1, 1], so **P41 missed**), 16 parent model calls against 18, `wait_agent` 3 times against 5, the whole run 107.5 s against 109.9 s (**P42 missed**, the bar was 8 s). **Codex H at S = 30**
  (`e11-codex-h30`, against `e12-codex-s30-a3`): the parent made 3 `wait_agent` calls against 12 (**P43 held**, the bar was at most 6), 15 parent model calls against 25, total input tokens 874,388 against 987,549 (-11.5%), the whole run 220.3 s against 215.2 s (**P44 held**, within 10 s, +5.1 s). Predictions A8 and A9: three of five held against 65%, 55%, 65% and
  (missed) 60%, 50% (about 2.95 expected).
- Reading of the exploratory cells: wording does not change how a host issues spawns (Codex keeps one `spawn_agent` per model call, Claude keeps one call with four `Agent` blocks, Grok one call with four `spawn_subagent`), but a sentence asking for one long wait cut Codex's parent polling fourfold at S = 30 at no cost in time, and the total token saving was only 11.5%
  because the workers poll their own long commands too (one child made 10 model calls where the others made 5): the polling cost has two homes, the parent waiting for its children, which wording fixes, and each worker waiting for its own long command, which would need wording in the worker's instruction. The contract carries the long-wait sentence for Codex and nothing else.

### E12 — 2026-11-14: how the whole run scales with task length (the settle dial; twelve registered trials)

- Question: do the fan-out's startup, join and shutdown costs stay fixed against longer tasks (the owner's doubt: "we're not over-pivoting on small tasks and small measurements")? Method (README A7, committed in 7e68c9f03ddb5d7ef4d53926c207e43f5083a4a6; the settle dial in
  a80d73d4072571484e397624b48ac01cca17fb20): A0 (one context does every task) and A3 (script-owned ready set, fresh native sub-agents, packet N, as the pilot) on `analysis5` with every task running a verification of S seconds before it reports, S = 30 and 90, one trial per cell, on the
  owner's profiles (Claude Sonnet 5.5 `--effort high`, Grok 4.6 xhigh, Codex Sol 6.1 medium); S = 0 is the pilot. Grok's S = 30 A3 ran first as the basic check (the 30 s command ran in the foreground on all hosts, nothing was cut). One trial at a time per host, hosts side by side; order S = 30: Claude and Grok
  A3 then A0, Codex A0 then A3; S = 90: Claude and Grok A0 then A3, Codex A3 then A0. Evidence: `evidence/e12-*`, `python3 scaling_table.py`, `python3 phases.py`.
- Result (whole run in seconds, launch to exit; "model" is the registered prediction A0 = pilot + 5 S, A3 = pilot + 2 S or, on Codex, + 3 S; outside work is A3 minus A0 over orient, spawn, start, join, integrate and tail; calls and tokens are over all contexts):

  | host | S | A0 | A3 | A3 / A0 | model | outside work | model calls A0 / A3 | input tokens A0 / A3 | cost A0 / A3 |
  |---|---|---|---|---|---|---|---|---|---|
  | Claude | 0 (pilot) | 35.4 | 43.2 | 1.22 | 1.22 | 21.4 | 15 / 30 | 555,668 / 932,405 | $0.152 / $0.363 |
  | Claude | 30 | 188.2 | 103.9 | 0.55 | 0.56 | 19.4 | 14 / 29 | 523,390 / 890,719 | $0.152 / $0.537 |
  | Claude | 90 | 507.3 | 223.5 | 0.44 | 0.46 | 15.1 | 16 / 28 | 616,592 / 845,799 | $0.191 / $0.536 |
  | Grok | 0 (pilot) | 81.4 | 96.1 | 1.18 | 1.18 | 43.0 | 24 / 35 | 867,154 / 659,155 | $0.593 / $0.630 |
  | Grok | 30 | 258.6 | 164.2 | 0.63 | 0.67 | 37.9 | 29 / 33 | 1,098,025 / 601,482 | $0.711 / $0.609 |
  | Grok | 90 | 543.6 | 281.1 | 0.52 | 0.52 | 34.5 | 25 / 35 | 949,267 / 695,148 | $0.581 / $0.801 |
  | Codex | 0 (pilot) | 100.3 | 109.9 | 1.10 | 1.10 | 26.6 | 23 / 38 | 449,485 / 706,535 | not reported |
  | Codex | 30 | 288.8 | 215.2 | 0.75 | 0.80 | 22.5 | 29 / 52 | 611,566 / 987,549 | not reported |
  | Codex | 90 | 581.0 | 401.7 | 0.69 | 0.69 | 30.5 | 49 / 88 | 1,064,296 / 1,708,874 | not reported |

  All twelve trials: five of five answers correct, verify OK, a faithful report, exit 0, every task settled, no refused attempt, A0 never overlapped two tasks (0 of 6 independent pairs), A3 peak 4 (Claude, Grok) and 3 (Codex).
- Predictions scored as registered (README A7): **P35 held** (all twelve valid); **P36 held** (A3 below A0 at S = 30 on all three; the registered odds were 90%, 85% and 65%); **P37 held** (at S = 90 on all three); **P38 held** (the cost outside the work phase changed by 4.3 s, 3.4 s and
  8.0 s from S = 30 to S = 90, against a 15 s bar); **P39 held** (the ratio fell on every host, 0.55 to 0.44, 0.63 to 0.52, 0.75 to 0.69, and is below 0.6 on Claude and Grok at S = 90); **P40 missed** (Codex's model calls at S = 90 are 49 and 88 against the pilot's 23 and 38, +113% and +132%;
  Claude's and Grok's are within 25%). Five of six held against 85%, 80%, 85%, 60%, 65% and 55% (about 4.3 expected).
- Readings, each on its own line: (a) The owner's doubt was right, in the specific form the model gave: the fixed costs stayed fixed (outside work 21.4, 19.4, 15.1 s on Claude; 43.0, 37.9, 34.5 s on Grok; 26.6, 22.5, 30.5 s on Codex; spawn, join and tail are flat across S in the phase split, e.g. Claude spawn
  7.9, 7.0, 7.2 s and join 6.7, 6.5, 6.1 s) while the saving grew with the task: at S = 90 the whole run fell by 283.8 s (56%), 262.5 s (48%) and 179.3 s (31%). The pilot's "fan-out lost" was a statement about 5 s to 15 s tasks. (b) Break-even per-task time, from the arithmetic the data confirms
  (the fan-out replaces four serial tasks by one, or on Codex by two rounds, at a fixed cost): overhead / (independent tasks minus rounds) = 21.4 / 3 = 7.1 s (Claude), 43.0 / 3 = 14.3 s (Grok) and 26.6 / 2 = 13.3 s (Codex); the pilot's A0 tasks (5.3, 13.1 and 14.5 s) were at or just under it. The registered least-squares
  S* from three points (3.1, 2.5 and 0.5 s more than the pilot) is dominated by the long cells and is reported with that limit (R7). (c) The A3 whole run matched the registered model closely (223.5 against 223.2 s on Claude at S = 90; 281.1 against 276.1 s on Grok; 401.7 against 379.9 s on Codex); A0 ran longer
  than modelled (+21.9, +12.2 and +30.7 s at S = 90): a single context's long commands carry more per-command overhead than the model assumed. (d) The straggler spread is small: the four independent tasks took 97 s to 99 s on Claude and 104 s to 106 s on Codex at S = 90, and 97 s to 121 s on Grok. (e) What does scale with the task is
  the Codex parent's polling: model calls A0 23, 29, 49 and A3 parent 18, 25, 31 (`wait_agent` 5, 12, 17 in 10 s slices; at S = 90 the A0 parent also called `wait` 10 times), input tokens A0 449k, 612k, 1.06M and A3 707k, 988k, 1.71M, so on Codex the token cost grows with the length of the commands waited for and the
  fan-out/A0 token ratio stays about 1.6; Claude's and Grok's calls and tokens did not grow with S. (f) Dollars (Claude, Grok): the fan-out cost $0.363, $0.537 and $0.536 against $0.152, $0.152 and $0.191 on Claude (2.4, 3.5 and 2.8 times; at S = 90 an extra $0.345 for 283.8 s saved) and $0.630, $0.609 and $0.801 against $0.593, $0.711
  and $0.581 on Grok (1.06, 0.86 and 1.38 times). The registered dial adds time, not calls, on Claude and Grok, so it says nothing about the token curve with many more calls a task (the fit in R4 stands as a model).
- Limits: one trial per cell (the Grok N and H pairs of E11 show a 3 s to 11 s spread between trials of one condition, so differences of under about 10 s are noise); one read-only workload; the settle is a sleep, so the 90 s tasks are not 90 s of model work; the dial does not test merging, isolation, rate limits at wider fan-out, or a task whose duration varies by more than a few seconds;
  three hosts side by side, machine load not recorded per minute.

### R5 — 2026-11-14: what the study now supports, what it does not, and what I recommend (closing entry for E9 to E12)

- Answers to the owner's questions, each with its evidence. (1) Can native agent contexts be used the same way on every harness, with only the outcome kept in the parent? Yes, on Claude Code 2.1.325, Codex 0.169.0 and Grok Build 1.0.77, when a script owns readiness, instructions and recorded outcomes: every one of the 26 `analysis5` task trials (the pilot's eight, E11's three and three exploratory, E12's twelve; counted from the score files) answered all five analyses correctly,
  was valid, exited 0, had no refused attempt and left nothing running (F16, F20, F24, F25); the parent's own input in A3 is 0.73 times A0's on Claude and Codex (F22, F28). (2) Are we over-pivoting on small tasks? The pilot's verdict, that the fan-out lengthened the whole run, was true for 5 s to 15 s tasks and mostly says how short they were: the fixed costs (spawn, join, tail: 21.4 s, 43.0 s, 26.6 s) stayed fixed
  to 90 s more per task while the saving grew, so at 30 s to 90 s per task the whole run fell by 25% to 56% (F34 to F36). (3) What does it cost? Time falls, and tokens and dollars rise on Claude (1.4 to 1.7 times the input tokens, 2.4 to 3.5 times the dollars), fall on Grok (0.55 to 0.76 times the tokens, 0.86 to 1.38 times the dollars) and rise about 1.6 times on Codex, where the
  parent's polling makes the token cost grow with the wait on both arms (F37). (4) Can a skill layer detect the harness? Yes: the repository's `detect_host`, exact names innermost first, named the right host in the parent and in a sub-agent on all three; a prefix match would not have (F30). A worker cannot tell it is a worker (F31). (5) Does host-specific wording help? Not for spawning on any host
  (F33, F38); one sentence helps on Codex: a long wait instead of short polls (F38).
- What the study does not support: ~~nothing about writes, merging, isolation or conflicts (the owner named merging; no trial wrote a file in a shared checkout)~~ (superseded 2026-11-14 by E13 for writing files, merging and a same-file conflict in a toy package; still nothing about real ShipLoop steps or large repositories); nothing about a real ShipLoop stage (the workload is five log analyses and a sum); nothing about wider fan-out, rate limits or tasks whose durations differ widely; one trial per cell, so the numbers are shapes, with a 3 s to 11 s
  spread between trials of one condition; the token curve for tasks of many calls is a fit (R4), untested.
- Where it would pay in ShipLoop: 90% of recorded plans have no independent pair (F8), and recorded step iterations are about 154 s (F11), so the saving lives where width and length coincide: bounded investigations or reviews inside one stage, not parallel build steps (the per-step lifecycle decision, F15, is still the owner's).
- Recommendation (mine; the placement is the owner's call, `skill-layer-contract.md` section 9). First, option C: put detection and the measured bindings into Ask Agent as data (exact markers, the native tool per host, capacity, the long-wait sentence for Codex, the accounting rules) so every existing native delegation, including ShipLoop's, stops depending on a model reading prose to
  pick a host section. Second, if the owner wants fan-out inside a stage, option B's shape for read-only work (the minimal script-owned ready set, claim and capacity, a worker instruction that forbids spawning), added to In Parallel's helper rather than as a fourth skill, behind the predicate (opt-in, width at least 2, estimated task time of 20 s or more, a qualified host) and
  the conformance fixture. Third, no write fan-out until the write fixture below exists.
- Next measurements, in order of what changes a decision: (a) a write fixture (disjoint edits in a shared checkout, the same with isolated worktrees and a scripted merge, one conflicting edit) to price merging; (b) a second dial for tokens (tasks with many calls) to test the fit; (c) a read-only fan-out inside a real stage (a planning or review step against a hidden oracle); (d) three trials per key cell to put a spread on
  the ratios; (e) eight independent tasks to meet the host's concurrency and rate limits; (f) a skill running inside another host's sub-agent and a grandchild spawn (E10's untested cases).

### E13 — 2026-11-14: what merging costs (the write fixture; fifteen registered trials, two flawed trials kept)

- Question (the owner's, named in R4 and listed first in R5; asked whether to price merging next, the owner said "Yes, build it"): does giving each worker its own checkout and merging the results keep the fan-out's win, and what does it cost when the plan missed a file two tasks both change? Method (README A10, committed with the fixture in
  00aafed413268a85213af6a68a4eb93b32d8d268; the owner's profiles: Claude Sonnet 5.5 `--effort high`, Grok 4.6 xhigh, Codex Sol 6.1 medium, capacity 3): a small Python package, four independent tasks that each write a module and its tests and a dependent integration task, a hidden oracle (about thirteen cases a function, four exports, the test counts of every file and
  of the suite), at S = 30 (the settle dial standing for a slow test suite). Per host: write5 with one context (A0, shared checkout), write5 fan-out in the shared checkout (A3s), write5 fan-out with a git worktree per attempt and a scripted merge in completion order (A3i), and overlap5, in which W3 and W4 also append to `pkg/__init__.py`, a shared file the plan does not declare, with fan-out shared (Os)
  and isolated (Oi, where a conflict is aborted, logged and the task retried from the updated main). One trial per cell, one at a time per host, hosts side by side. Evidence: `evidence/e13-*` (each with `repo.txt`, the history, and `final-tree/`, the code the workers wrote), `python3 merge_table.py`, `python3 phases.py`.
- Apparatus fault, fixed and rerun (9da1df846b7ff109f3f638e81c5fd29bf68b89eb): the first Claude and Grok Oi trials skipped the retried task's verification, because the kit counted one `settled` event per step, not per attempt. Fail-first cells reproduced it (three off), the fix made the settle per attempt, and both trials were rerun once with the fixed kit; the flawed pair is kept as `evidence/e13-claude-o5-a3i-flawed` and `e13-grok-o5-a3i-flawed` and is not scored.
  The flawed whole runs were 139.6 s and 211.6 s; the reruns, which are the registered cells, 161.9 s and 240.4 s: the fault understated the conflict's cost by 22.3 s and 28.8 s.
- Result (whole run in seconds, launch to exit; work is the first task start to the last independent task's end; kit is the kit's own time opening workspaces, committing and merging; calls and tokens over all contexts):

  | host | cell | whole | work | kit s | merges, conflicts | calls | input tokens | cost |
  |---|---|---|---|---|---|---|---|---|
  | Claude | write5 A0 shared | 214.9 | 164.2 | 0 | 0, 0 | 23 | 988,397 | $0.279 |
  | Claude | write5 A3 shared | 107.8 | 42.8 | 0 | 0, 0 | 38 | 1,193,665 | $0.437 |
  | Claude | write5 A3 isolated | 107.7 | 42.9 | 0.80 | 5, 0 | 36 | 1,125,919 | $0.615 |
  | Claude | overlap5 A3 shared | 113.3 | 42.9 | 0 | 0, 0 | 36 | 1,102,307 | $0.435 |
  | Claude | overlap5 A3 isolated | 161.9 | 92.2 | 0.85 | 5, 1 (W3, retried) | 45 | 1,426,472 | $0.486 |
  | Grok | write5 A0 shared | 250.4 | 192.4 | 0 | 0, 0 | 35 | 920,295 | $0.615 |
  | Grok | write5 A3 shared | 173.7 | 69.1 | 0 | 0, 0 | 49 | 721,521 | $0.625 |
  | Grok | write5 A3 isolated | 179.9 | 70.4 | 0.84 | 5, 0 | 50 | 723,289 | $0.651 |
  | Grok | overlap5 A3 shared | 180.4 | 67.0 | 0 | 0, 0 | 49 | 699,394 | $0.691 |
  | Grok | overlap5 A3 isolated | 240.4 | 136.1 | 0.82 | 5, 1 (retried) | 59 | 878,273 | $0.826 |
  | Codex | write5 A0 shared | 298.8 | 230.3 | 0 | 0, 0 | 22 | 492,094 | not reported |
  | Codex | write5 A3 shared | 245.7 | 142.2 | 0 | 0, 0 | 64 | 1,262,823 | not reported |
  | Codex | write5 A3 isolated | 256.3 | 143.6 | 1.14 | 5, 0 | 63 | 1,227,819 | not reported |
  | Codex | overlap5 A3 shared | 252.3 | 136.8 | 0 | 0, 0 | 71 | 1,394,875 | not reported |
  | Codex | overlap5 A3 isolated | 240.1 | 136.4 | 0.80 | 5, 0 | 61 | 1,197,795 | not reported |

  All fifteen: the oracle passed (four hidden suites, four exports, every reported count equal to the tree's, the suite green), verify OK, a faithful report, exit 0; no scope note in any isolated trial except the planted ones (Oi: W3 and W4, `pkg/__init__.py`, as designed); no refused attempt in the scored cells. The workers wrote 5 to 12 tests a module.
- Predictions scored as registered (README A10): **P46 held** (all nine write5 trials valid); **P47 held** (no scope note in a write5 isolated trial); **P48 held** (fan-out isolated below A0 on all three: 107.7 against 214.9 s, 179.9 against 250.4 s, 256.3 against 298.8 s); **P49 held** (isolated minus shared: -0.1 s, +6.2 s, +10.6 s, against a 15 s bar);
  **P50 missed** (Claude and Grok logged exactly one conflict on `pkg/__init__.py`, one retry, and ended valid; Codex logged none: see reading d); **P51 missed as written** (the conflict cost 1.27 task rounds on Claude and 0.86 on Grok, both inside 0.6 to 2.0, and -0.11 on Codex, which had no conflict); **P52 missed** (no overlap5 shared trial was invalid: all three concurrent appends survived);
  **P53 held** (isolated input tokens 0.94, 1.00 and 0.97 times shared). Five of eight held against 80%, 85%, 75%, 65%, 80%, 70%, 25% and 60% (about 5.4 expected). Decision rule R10: isolation and scripted merging are not material at 30 s tasks (under 15 s on every host). R11: a conflict costs about one task round. R12 asked that the contract carry the rule "disjoint declared paths, a scripted merge in completion order, a retry from the
  updated main" only if P46 and P50 hold, and otherwise say what failed: P50 failed as written, for a reason that is not the mechanism's (reading d), so the contract carries the rule as exercised on two of three hosts and says so.
- Readings, each on its own line, none a rescore: (a) Merging is cheap. Opening five workspaces, five commits and five merges took 0.80 s, 0.84 s and 1.14 s of the kit's time, the whole-run difference against the shared checkout (-0.1 s, +6.2 s, +10.6 s) is inside the 3 s to 11 s spread between trials of one condition (E11), calls were equal (36 against 38, 50 against 49, 63 against 64) and tokens within 6%: at 30 s tasks isolation and
  the scripted merge are not material. What it does not buy is a cheaper merge when the files are large or the conflicts semantic: the fixture's files are a few hundred bytes. (b) The fan-out's win survives writing: A3 isolated against A0, 0.50, 0.72 and 0.86 times (saving 107.2 s, 70.5 s and 42.5 s; 0.55, 0.63 and 0.75 in E12's read-only tasks at the same S), with Codex's smaller win from its three slots (two waves of about 70 s) and its parent's polling. (c) A conflict costs about one task round plus
  a few seconds: +54.2 s on Claude (1.27 times its 42.9 s work phase) and +60.5 s on Grok (0.86 times 70.4 s) over the same host's conflict-free isolated trial; the kit aborted the merge, logged the path, and offered the loser again from the updated main with a note saying why; the retry saw the winner's import in its workspace and merged at attempt 2; both trials ended valid. In the Claude trial W4, W1 and W2 merged and W3 lost; the retry began 5.8 s after the conflict and ended 42 s later (its
  verification included), and the merge came 4.5 s after that. (d) Whether two tasks conflict depends on scheduling, not only on the plan: Codex's three slots ran W4 after W1 to W3 had merged, so W4's workspace already held W3's import and nothing conflicted (no cost); a capacity limit can hide a planning defect (an undeclared shared file) and a larger capacity would have exposed it. (e) The shared checkout took three concurrent appends to the undeclared file without a lost update (all three valid; Codex's even reordered the lines),
  but the integration task in this fixture also repairs the registry, so a lost import would have been fixed by W5 and the race is masked; the shared arm has no scope check and no conflict detection at all, which is the reason isolation exists, not a measured cost. (f) The merge waits for the parent: the script merges at the next `ready`, so a task's end to its merge was 2.0 s to 4.7 s on Claude, up to 16.7 s on Grok (its parent waits for all four children before it calls `ready`) and up to 7.8 s on Codex.
  (g) Tokens and dollars repeat the pattern of E12 for writes: fan-out shared against A0 used 1.21 times the input tokens on Claude, 0.78 times on Grok and 2.57 times on Codex (64 model calls against 22: parent and workers poll long commands) and cost 1.57 times on Claude and 1.02 times on Grok; Claude's A3 cost ranged $0.435 to $0.615 across four near-identical cells, so a dollar difference of under about 40% is noise.
- Limits: one workload (four toy functions, files of a few hundred bytes), so the cost of git operations on a real repository and of a real conflict (large, semantic) is not measured; the settle is a sleep standing for a test suite; one trial per cell (shape, not rate); the merge is into a scratch main, so ShipLoop's clean-checkout identity and its commit stage (F15) are not modelled and nothing here says that concurrent steps are wanted; the integration task repairs the registry, which
  masks a shared-checkout race; capacity 3 on Codex changed which tasks ran together; the kit's own git commands run inside the script (no model-written command runs in it).
- Disclosure found after the trials: an orphaned process from my first, interrupted mutation check (a mutated kit's `ready` looped forever, and the harness's timeout killed its parent but not it) ran at about 84% of one core from before the smoke trials until I found and stopped it, after E13 (pid 11108, 39 minutes, its parent launchd). It overlaps every E13 trial and the smoke trials. The trials are bound by model latency, not by this machine's CPU, and the machine's load average was already 5 to 8 in the pilot, so I judge the effect on the timings small, but I did not measure it; E12's trials ran before it started.

### R6 — 2026-11-14: the recommendation after E13 (an update to R5, which stays as written)

- What E13 changed. The owner's doubt named startup, shutdown and merging. The first two are E12's fixed costs (15 s to 43 s a round, flat as tasks lengthen); merging, now priced for a toy package, is about 1 s of script time and 0 to 11 s of whole run when every task has its own worktree, and about one task round (+54 s to +61 s at 30 s tasks) when two tasks change the same file and a conflict forces a retry (F39, F41). At 30 s a task none of the three is material, and at 90 s
  the fixed ones are a small part of the saving; the doubt was right, and the pilot's loss was a small-task effect. The owner's rule of quality, then tokens, then time still decides: time falls, and tokens and dollars rise on Claude and Codex (F37, F45).
- The recommendation, updated. First, as in R5: option C, detection and the measured bindings as data in Ask Agent, which gives every native delegation harness independence without any new scheduler. Second, if the owner wants fan-out inside a stage, the measured shape is now complete for both kinds of work: a script-owned ready set (claim, capacity, release, outcome-only callbacks) for read-only tasks, and for writes a worktree per attempt,
  a scripted merge in completion order, an abort and retry on a conflict and a verification that runs again on a retry (F44), added to In Parallel's helper rather than as a fourth skill, behind the predicate (opt-in, width at least 2, disjoint declared paths for writes, an estimated 20 s or more a task, a qualified host) and the conformance fixtures (`analysis5` arm A3, `write5` and `overlap5` isolated). R5's "no write fan-out until a write fixture exists" is
  superseded: the fixture exists and the shape held on two hosts and was never exercised on the third (F42).
- Before write fan-out touches real ShipLoop steps, still unmeasured: a real repository and a real, semantic conflict; the interplay with ShipLoop's commit stage and clean-checkout identity, which is the per-step lifecycle decision that is still the owner's (F15); eight workers and the hosts' rate limits; the unattended recovery of a lost worker that the retired chain provided; and three trials of the key cells to put a spread on the ratios.
- Open owner decisions, unchanged: whether concurrent work belongs inside one stage or across build steps; where the layer lives (R5's pick: C now, B's shape for in-stage fan-out added to In Parallel); whether to build the next measurements above.

## Findings

| # | Finding | Status | Entry |
|---|---|---|---|
| F1 | A step plan records each step's `deps`, validated as unique earlier step IDs (so list order is a topological order); readers are the progress and trace views and the per-step packet's "Depends on:" line, and the plan also records per-step `paths`. The work-item queue is an ordered list with no dependency field and is visited serially | firm (source reading) | R0 |
| F2 | ShipLoop's parallel route (the implementation chain) was retired on the owner's G1 because it conflicted with the per-step iteration in four of its rules, and its speed gain "was never measured": the live runs show overlap, not a serial counterfactual. What it bought was isolation and the unattended retry of a lost worker | firm (commit text: 8eca9d64826e0073540b6029b6071fc91b553e8e, fb4b284368ffb8c0d32d175915e299849ed8a8b8, ad30aa1c82665435c1e69771ef079d80d7b92079) | R0 |
| F3 | On the heavy Plan Dispatcher protocol a 60 s ideal fan-out took 587 s on Codex (J started about 240 s after A and B ended); overlap itself was real on Codex (29.3 of 30 s) and Claude (29.9 of 30 s) | interim (one run each; test/shiploop_e2e/LEARNINGS.md, f810a78f38f996086f6beba9eceb54403052e8bc, e0fb43667f4f9b2386962d46c38f288f56822809) | R0 |
| F4 | The history digest said no script validates step `deps`; that is wrong: the navigator rejects non-list, duplicate, unknown, self and forward dependencies. What no script proves is that a recorded `deps` is the true set (a missing or a forced dependency) | firm (source reading) | R0 |
| F5 | The three CLIs on this machine can all run headless with a native sub-agent facility present: Claude Code 2.1.325 (`--agents`, `stream-json`), Codex 0.169.0 (`multi_agent_v2` stable; `enable_fanout` removed), Grok Build 1.0.77 (subagents on by default, `--no-subagents`, `streaming-json`). Presence is not behaviour; that is what E1 to E3 test | firm (CLI reading) | R0 |
| F6 | Codex's native multi-agent feature depends on the profile: in the throwaway `CODEX_HOME` the E2E harness builds (sign-in only) `multi_agent_v2` is off and the deprecated `multi_agent` is on, while the owner's own profile has both on. A harness result on Codex is therefore a result for one profile; "Codex can do it" needs both | firm for the configured state; superseded as to effective behaviour by F18 (2026-11-14) | R0 |
| F7 | Planning reliably records dependencies: 922 of 928 recorded step plans (99.4%) have `deps` on every step, none names a later or unknown step, and the 6 without are legacy | firm (census, re-extracted independently) | E0 |
| F8 | Most recorded plans have nothing to overlap: 600 of 922 are single-step (65%), 218 are pure chains (24%); 92 (10.0%) have an independent pair, 28.6% of the 322 multi-step plans; 28 plans have width 3 or more | firm for these runs (E2E cases) | E0 |
| F9 | The ideal wall-clock saving from step-level parallelism is 11.6% of recorded step time over the 323 timed plans (20.8% over the 75 multi-step ones; per-plan median 0; 21 plans save anything; family-weighted 1.6%); with overlapping-path steps kept in order, 9.9% (17.7%). It is concentrated in a few families and is an upper bound (unlimited workers, no merge cost, per-step stages assumed able to overlap) | interim (75 timed multi-step plans) | E0 |
| F10 | "Independent by `deps`" often means "shares files": 51% of same-level pairs and 61% of all independent pairs (with paths) overlap on declared paths; hand-read cases show an undeclared order (Apex chess S2 to S5, Battleship S2 and S3). A path-disjointness gate computed from the plan removes 61% of the independent pairs that have paths (192 of 314) but only about 15% of the ideal saving (11.6% to 9.9%), because the plans that save most have disjoint pairs | firm (census), anecdotal (the cases) | E0 |
| F11 | A recorded step iteration (implement, test, document, Improve review, commit) has median 154 s (p25 116 s, p75 212 s, max 1,866 s; 476 steps), so round 1's 30 s synthetic steps are about five times shorter than a real step and overstate the fixed cost of a fresh agent | firm for these runs | E0 |
| F12 | Step times can be recovered for only 323 of 922 plans (35%): runs before 2026-10-25 have no `trace.jsonl`, seeded runs omit the plan action from the trace, and single-step plans have no implement window | firm (census) | E0 |
| F13 | The per-step pilot ran (2026-10-29, `eadad0c84f8a213287459bbf6252411ac0b90fce`, Codex gpt-6.1-terra xhigh, case stand-in-parser, one run per arm): serial fresh workers cost 4.1 times the inline control's time (21.6 against 5.3 min), 2.9 times its input tokens (23.11 M against 8.06 M) and 4.5 times its output tokens, with 13 fresh workers (four per step plus five for the item), about 1.25 min and 1.2 M input tokens each; all slice verdicts passed. It measured no parallel run, so the unmeasured quantity (parallel against serial) stands; it is the prior for what a fresh context costs in real ShipLoop | interim (one case, one run per arm) | R1 |
| F14 | The first no-model calibration (75 cells, 0 off) could not see six pre-trial defects in the apparatus: a launcher that crashed on Codex and Grok before creating its directory, a mechanism detector that credited unrelated spawns and truncated commands, a report check that accepted a child's FINAL and an omitted running step, a Codex token key that read unknown, a claim that could strand a run, and a comparison that overwrote one Codex profile with the other. Each was reproduced as a failing cell (23 of 26 failed) before the fix (3c8e1cb6c42b5f4f17890a6959b9116640f21565); a dry run alone had hidden the first | firm (fail-first cells, then 104 cells 0 off) | R1 |
| F15 | A synthetic DAG that runs concurrently proves a mechanism, not a route: ShipLoop's step lifecycle (build, test, document, review, commit before the next) and its commit stage conflict with concurrent steps, which is why the chain was retired. E0's step-level saving is an upper bound that needs an owner decision to relax that lifecycle; the next bridge is parallel work inside one stage | firm as framing; the owner decision is open | R1 |
| F16 | Native sub-agents work headless on all three harnesses from a neutral packet, one foreground general-purpose sub-agent each, the step run once in the child, verify OK and a clean exit 0: Claude's `Agent` tool, Codex's `spawn_agent` (`fork_turns` "none") with `wait_agent`, Grok's `spawn_subagent` | interim (E1, one trial per host) | E1 |
| F17 | One hand-off of a 5 s step costs, bare: Claude 19.6 s, 188k input tokens (parent 136k, child 52k; the child's own context 27k), $0.137; Codex 34.5 s, 117k tokens (parent 81k, child 37k); Grok 31.5 s, 93k tokens, $0.087. The roughly 86k-token start-up figure for a fresh Claude sub-agent does not hold for a clean profile (27k) | interim (n = 1 per host; Codex and Grok at their medium and xhigh latency) | E1 |
| F18 | Codex's effective multi-agent version was v2 in both profiles (each child rollout says so, with the same tool names and the same overhead) although `codex features list` shows v2 off in the harness profile: the feature list is not the effective state, and A1's premise (v1 in the harness profile) is dropped | interim (one trial per profile) | E1 |
| F19 | Each host keeps its own record of its sub-agents: Claude's stream (`task_started` with `subagent_type`, `task_progress` tokens, `parent_tool_use_id` on every call), Codex's rollout files (one per thread, naming parent and depth; its `exec --json` stream shows neither the spawn nor the child's commands), Grok's `logs/unified.jsonl` (a session id on every tool call and a lifecycle line per sub-agent). Attribution therefore needs no hooks, and a host-neutral timeline needs three small readers | firm (shapes read from real runs) | E1 |
| F20 | Native fan-out and fan-in works on all three harnesses from one anonymous packet when a script owns readiness, instructions and recorded outcomes: eight of eight task trials answered all five analyses correctly, the parent's report matched the ledger, every exit was 0 and nothing was left running; agent peaks 4 (Claude), 4 (Grok), 3 (Codex), each in both the host's own record and the ledger | interim (one trial per cell) | E9 |
| F21 | For these 5 s to 24 s tasks parallelism shortened the task phase (0.77 to 0.93 times) but lengthened the whole run (1.10 to 1.22 times): the cost outside the task phase rose by 13.6 s (Claude), 29.6 s (Grok) and 14.9 s (Codex) while the task phase fell by 5.7 s, 14.9 s and 5.3 s. Only independent work longer than about those figures, times four thirds, can pay on these hosts; a ShipLoop step iteration (median 154 s, F11) is far longer, but 90% of recorded plans have no independent pair (F8) | interim (n = 1 per host; the arithmetic is derived from three trials) | E9 |
| F22 | Fresh contexts cost tokens and money: A3 used 1.68 times (Claude) and 1.57 times (Codex) the input tokens of A0 and 2.39 times the cost on Claude; the parent's own input fell to ~~0.24 times (Claude) and~~ 0.73 times (Codex and, corrected 2026-11-14 from 0.24, Claude: the first reading took the last of three result events) of A0's, so outcome-only retention holds, modestly. Grok's A3 figure (0.76 times) covers the whole run, children included (resolved 2026-11-14, R4): on Grok the fan-out used fewer input tokens, and cost 1.06 times | interim | E9, R4 |
| F23 | Host differences a portable route must absorb: Codex allows four concurrency slots including the parent (three children; its parent released the fourth claim itself); Claude and Grok spawn in background mode and their children begin together when the parent yields, not at each spawn; Claude picks the sub-agent type itself (general-purpose, once `claude`); the waits differ (`wait_agent` in slices, `get_command_or_subagent_output`, Claude's notifications); usage figures differ in scope (Claude `usage` is the parent's and `modelUsage` the whole run) | interim | E9 |
| F24 | A script-owned ready set with a claim, a capacity and a release was reliable on all three hosts: no refused attempt, no duplicate start, no stranded claim, one release used by Codex's parent when its host's slots ran out | interim | E9 |
| F25 | The sub-agents in every trial were native by each host's own account (Claude's task events, Codex's rollout threads at depth 1, Grok's log with a session id per tool call), and the timeline page `evidence/pilot-timeline.html` shows the interleaving: a staircase of tasks in A0 and overlapping agent lifetimes in A3 | firm (read from the real runs) | E9 |
| F26 | In the pilot the whole-run cost of fan-out outside the work phase was 21.4 s (Claude), 43.0 s (Grok) and 26.6 s (Codex): per agent (spawn: 7.9, 22.0, 12.9 s), per round (join +4.4, +12.0, +12.9 s; tail +5.7, +4.2, +3.4 s); orient and start were the same in both arms to within a few seconds. The work phase fell 13.6, 28.2 and 17.0 s | interim (n = 1 per cell; phases.py) | R4 |
| F27 | The pilot's tasks were 3 s to 5 s of per-task time short of break-even on every host: with S seconds more per task the saving grows 3S (Claude, Grok) or 2S (Codex, three slots), so the fan-out pays from about 8 s, 18 s and 19 s a task; the model predicts a whole-run ratio A3/A0 of 0.56, 0.67 and 0.80 at S = 30 and 0.46, 0.52 and 0.69 at S = 90 (to be tested by E12) | interim (a model from n = 1 cells) | R4 |
| F28 | The pilot's token accounting had two defects, both mine and both reproduced as failing cells: Claude `-p` emits one result event per parent turn (the scorer read the last), so the parent's input in Claude A3 is 404,872 (0.73 times A0), not 133,640; Grok's end usage covers its sub-agents (659,155 = parent 185,909 + children 473,246), so Grok's A3 used 0.76 times A0's input. Times, costs, answers and all-contexts totals were unaffected | firm (two independent sources agree on all six Claude trials) | R4 |
| F29 | A single context's input grows with the work, quadratically in total (495, 1,276 and 342 tokens a call on Claude, Grok and Codex), while a fresh child restarts from 24,152, 9,948 and 18,234 tokens; at the pilot's three to five calls a task the two are close and A3's extra tokens are the parent's orchestration turns. A fit says A3 uses fewer input tokens than A0 from about 7 calls a task on Claude and about 12 on Codex, and Grok already does at 5 | exploratory (a fit to n = 1 cells; linear growth, no compaction, no cache pricing) | R4 |
| F30 | The repository's `detect_host` (exact markers, innermost first) names the right host in the parent and in a native sub-agent on all three hosts, from the environment alone; the environment also carries the launching session's markers (`CODEX_COMPANION_*`, API-key names), so prefix matching would misdetect and the exact-name rule must stay | interim (one trial per host, E10) | E10 |
| F31 | A sub-agent cannot tell from its environment that it is one (Claude's session id is shared with the parent; no host sets a depth marker), and the Claude and Codex sub-agents list a tool for starting further agents; the contract therefore tells every worker, in its instruction, that it is a worker and must not start agents, and relies on the script's lease for the rest | interim (one trial per host; a model's tool list is a report) | E10 |
| F32 | The per-agent spawn cost sits in a different place on each host: Claude issues its four `Agent` calls in one model call, about 1.9 s apart (the model writing each prompt); Grok issues four `spawn_subagent` calls in one model call and the host then starts each child in turn, 3.4 s to 5.6 s apart (each call's own execution is 7 ms, and the batch returns 18 s to 19 s after the model call ended); Codex spends one model call on each `spawn_agent`, 5.6 s to 6.8 s apart | interim (read from the pilot's and E11's parent records) | E11 |
| F33 | Host-specific wording did not help on Grok: the anonymous packet already produced one model call with four spawns, the spawn phase was 21.9 s (N, two trials) against 22.0 s (H, two trials) and the whole run 97.7 s against 98.8 s; two trials of one condition differ by 3 s to 11 s, so differences of under about 10 s between single trials are noise | interim (two trials per condition) | E11 |
| F34 | The fan-out's fixed costs stay fixed as tasks lengthen: the cost outside the work phase (A3 minus A0) was 21.4, 19.4 and 15.1 s on Claude, 43.0, 37.9 and 34.5 s on Grok and 26.6, 22.5 and 30.5 s on Codex at S = 0, 30 and 90 (spawn, join and tail are flat across S), within 8 s, and the saving grows with the task | interim (twelve registered trials, n = 1 per cell) | E12 |
| F35 | A3 / A0 whole-run ratios fell from 1.22, 1.18 and 1.10 (the pilot) to 0.55, 0.63 and 0.75 at S = 30 and 0.44, 0.52 and 0.69 at S = 90: the whole run is shorter by 283.8 s (56%), 262.5 s (48%) and 179.3 s (31%) at S = 90; the registered model predicted the A3 whole run within 1 s (Claude), 5 s (Grok) and 22 s (Codex) | interim | E12 |
| F36 | Break-even per-task time is overhead / (independent tasks minus rounds): 7.1 s (Claude), 14.3 s (Grok), 13.3 s (Codex, three slots); the pilot's tasks (5.3, 13.1, 14.5 s) were at or just under it, so "small tasks" explains the pilot's loss | interim (arithmetic confirmed by the S = 30 and 90 trials) | E12 |
| F37 | Costs that scale with the task: the Codex parent polls (A0 model calls 23, 29, 49; A3 parent `wait_agent` 5, 12, 17 in 10 s slices), so Codex input tokens grow with S on both arms (A0 449k, 612k, 1.06M; A3 707k, 988k, 1.71M); Claude's and Grok's did not. Claude's fan-out costs 2.4 to 3.5 times A0's dollars, Grok's 0.86 to 1.38 times | interim | E12 |
| F38 | Wording does not change how a host issues spawns (Claude: one model call with four `Agent` blocks, Grok: one call with four `spawn_subagent`, Codex: one `spawn_agent` per model call, with and without H), but on Codex a sentence asking for one long wait cut the parent's `wait_agent` calls from 12 to 3 and its model calls from 25 to 15 at S = 30 with the whole run within 5 s; the total input tokens fell only 11.5% because the workers poll their own long commands too | interim (one exploratory trial per cell, A8 and A9) | E11 |
| F39 | Isolation (a git worktree per attempt) plus a scripted merge in completion order cost 0 to 11 s of whole run at 30 s tasks (isolated minus shared: -0.1 s, +6.2 s, +10.6 s, inside the 3 s to 11 s same-condition spread) and about 1 s of the kit's own time (0.80 s, 0.84 s, 1.14 s for five workspaces, five commits and five merges), with equal model calls and input tokens within 6%: merging is not material at 30 s tasks | interim (one trial per cell; toy files) | E13 |
| F40 | The fan-out's win survives writing code: whole run, fan-out isolated against one context, 0.50, 0.72 and 0.86 times on Claude, Grok and Codex (a saving of 107.2 s, 70.5 s and 42.5 s); all fifteen registered write trials passed a hidden oracle | interim | E13 |
| F41 | A merge conflict costs about one task round plus a few seconds: +54.2 s (1.27 times the work phase) on Claude and +60.5 s (0.86 times) on Grok over the same host's conflict-free trial; the kit aborted the merge, logged the path, retried the loser from the updated main and every such trial ended valid | interim (two trials) | E13 |
| F42 | Whether two tasks conflict depends on scheduling as well as on the plan: Codex's three slots ran the second registering task after the first had merged, so an undeclared shared file never conflicted; a capacity limit can hide a planning defect | interim (one trial) | E13 |
| F43 | A shared checkout survived three concurrent appends to an undeclared file with no lost update, but the integration task repairs the registry, so a race would be masked, and the shared arm has neither a scope check nor conflict detection | interim | E13 |
| F44 | A retried task must run its verification again: the first two overlap-isolated trials counted the first attempt's settle for the retry and understated a conflict's cost by 22.3 s (Claude) and 28.8 s (Grok); fixed fail-first and rerun (9da1df846b7ff109f3f638e81c5fd29bf68b89eb) | firm (fail-first cells, reruns) | E13 |
| F45 | For write tasks fan-out in the shared checkout used 1.21, 0.78 and 2.57 times A0's input tokens on Claude, Grok and Codex (Codex: 64 model calls against 22) and 1.57 and 1.02 times the dollars on Claude and Grok; Claude's A3 cost varied $0.435 to $0.615 across near-identical cells | interim | E13 |
