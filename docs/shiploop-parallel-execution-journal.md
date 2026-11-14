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

## Findings

| # | Finding | Status | Entry |
|---|---|---|---|
| F1 | A step plan records each step's `deps`, validated as unique earlier step IDs (so list order is a topological order); readers are the progress and trace views and the per-step packet's "Depends on:" line, and the plan also records per-step `paths`. The work-item queue is an ordered list with no dependency field and is visited serially | firm (source reading) | R0 |
| F2 | ShipLoop's parallel route (the implementation chain) was retired on the owner's G1 because it conflicted with the per-step iteration in four of its rules, and its speed gain "was never measured": the live runs show overlap, not a serial counterfactual. What it bought was isolation and the unattended retry of a lost worker | firm (commit text: 8eca9d64826e0073540b6029b6071fc91b553e8e, fb4b284368ffb8c0d32d175915e299849ed8a8b8, ad30aa1c82665435c1e69771ef079d80d7b92079) | R0 |
| F3 | On the heavy Plan Dispatcher protocol a 60 s ideal fan-out took 587 s on Codex (J started about 240 s after A and B ended); overlap itself was real on Codex (29.3 of 30 s) and Claude (29.9 of 30 s) | interim (one run each; test/shiploop_e2e/LEARNINGS.md, f810a78f38f996086f6beba9eceb54403052e8bc, e0fb43667f4f9b2386962d46c38f288f56822809) | R0 |
| F4 | The history digest said no script validates step `deps`; that is wrong: the navigator rejects non-list, duplicate, unknown, self and forward dependencies. What no script proves is that a recorded `deps` is the true set (a missing or a forced dependency) | firm (source reading) | R0 |
| F5 | The three CLIs on this machine can all run headless with a native sub-agent facility present: Claude Code 2.1.325 (`--agents`, `stream-json`), Codex 0.169.0 (`multi_agent_v2` stable; `enable_fanout` removed), Grok Build 1.0.77 (subagents on by default, `--no-subagents`, `streaming-json`). Presence is not behaviour; that is what E1 to E3 test | firm (CLI reading) | R0 |
| F6 | Codex's native multi-agent feature depends on the profile: in the throwaway `CODEX_HOME` the E2E harness builds (sign-in only) `multi_agent_v2` is off and the deprecated `multi_agent` is on, while the owner's own profile has both on. A harness result on Codex is therefore a result for one profile; "Codex can do it" needs both | firm (`codex features list` in each profile, 0.169.0) | R0 |
| F7 | Planning reliably records dependencies: 922 of 928 recorded step plans (99.4%) have `deps` on every step, none names a later or unknown step, and the 6 without are legacy | firm (census, re-extracted independently) | E0 |
| F8 | Most recorded plans have nothing to overlap: 600 of 922 are single-step (65%), 218 are pure chains (24%); 92 (10.0%) have an independent pair, 28.6% of the 322 multi-step plans; 28 plans have width 3 or more | firm for these runs (E2E cases) | E0 |
| F9 | The ideal wall-clock saving from step-level parallelism is 11.6% of recorded step time over the 323 timed plans (20.8% over the 75 multi-step ones; per-plan median 0; 21 plans save anything; family-weighted 1.6%); with overlapping-path steps kept in order, 9.9% (17.7%). It is concentrated in a few families and is an upper bound (unlimited workers, no merge cost, per-step stages assumed able to overlap) | interim (75 timed multi-step plans) | E0 |
| F10 | "Independent by `deps`" often means "shares files": 51% of same-level pairs and 61% of all independent pairs (with paths) overlap on declared paths; hand-read cases show an undeclared order (Apex chess S2 to S5, Battleship S2 and S3). A path-disjointness gate computed from the plan removes 61% of the independent pairs that have paths (192 of 314) but only about 15% of the ideal saving (11.6% to 9.9%), because the plans that save most have disjoint pairs | firm (census), anecdotal (the cases) | E0 |
| F11 | A recorded step iteration (implement, test, document, Improve review, commit) has median 154 s (p25 116 s, p75 212 s, max 1,866 s; 476 steps), so round 1's 30 s synthetic steps are about five times shorter than a real step and overstate the fixed cost of a fresh agent | firm for these runs | E0 |
| F12 | Step times can be recovered for only 323 of 922 plans (35%): runs before 2026-10-25 have no `trace.jsonl`, seeded runs omit the plan action from the trace, and single-step plans have no implement window | firm (census) | E0 |
| F13 | The per-step pilot ran (2026-10-29, `eadad0c84f8a213287459bbf6252411ac0b90fce`, Codex gpt-6.1-terra xhigh, case stand-in-parser, one run per arm): serial fresh workers cost 4.1 times the inline control's time (21.6 against 5.3 min), 2.9 times its input tokens (23.11 M against 8.06 M) and 4.5 times its output tokens, with 13 fresh workers (four per step plus five for the item), about 1.25 min and 1.2 M input tokens each; all slice verdicts passed. It measured no parallel run, so the unmeasured quantity (parallel against serial) stands; it is the prior for what a fresh context costs in real ShipLoop | interim (one case, one run per arm) | R1 |
| F14 | The first no-model calibration (75 cells, 0 off) could not see six pre-trial defects in the apparatus: a launcher that crashed on Codex and Grok before creating its directory, a mechanism detector that credited unrelated spawns and truncated commands, a report check that accepted a child's FINAL and an omitted running step, a Codex token key that read unknown, a claim that could strand a run, and a comparison that overwrote one Codex profile with the other. Each was reproduced as a failing cell (23 of 26 failed) before the fix (3c8e1cb6c42b5f4f17890a6959b9116640f21565); a dry run alone had hidden the first | firm (fail-first cells, then 104 cells 0 off) | R1 |
| F15 | A synthetic DAG that runs concurrently proves a mechanism, not a route: ShipLoop's step lifecycle (build, test, document, review, commit before the next) and its commit stage conflict with concurrent steps, which is why the chain was retired. E0's step-level saving is an upper bound that needs an owner decision to relax that lifecycle; the next bridge is parallel work inside one stage | firm as framing; the owner decision is open | R1 |
