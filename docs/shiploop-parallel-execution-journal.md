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

## Findings

| # | Finding | Status | Entry |
|---|---|---|---|
| F1 | A step plan records each step's `deps`, validated as unique earlier step IDs (so list order is a topological order); readers are the progress and trace views and the per-step packet's "Depends on:" line, and the plan also records per-step `paths`. The work-item queue is an ordered list with no dependency field and is visited serially | firm (source reading) | R0 |
| F2 | ShipLoop's parallel route (the implementation chain) was retired on the owner's G1 because it conflicted with the per-step iteration in four of its rules, and its speed gain "was never measured": the live runs show overlap, not a serial counterfactual. What it bought was isolation and the unattended retry of a lost worker | firm (commit text: 8eca9d64826e0073540b6029b6071fc91b553e8e, fb4b284368ffb8c0d32d175915e299849ed8a8b8, ad30aa1c82665435c1e69771ef079d80d7b92079) | R0 |
| F3 | On the heavy Plan Dispatcher protocol a 60 s ideal fan-out took 587 s on Codex (J started about 240 s after A and B ended); overlap itself was real on Codex (29.3 of 30 s) and Claude (29.9 of 30 s) | interim (one run each; test/shiploop_e2e/LEARNINGS.md, f810a78f38f996086f6beba9eceb54403052e8bc, e0fb43667f4f9b2386962d46c38f288f56822809) | R0 |
| F4 | The history digest said no script validates step `deps`; that is wrong: the navigator rejects non-list, duplicate, unknown, self and forward dependencies. What no script proves is that a recorded `deps` is the true set (a missing or a forced dependency) | firm (source reading) | R0 |
| F5 | The three CLIs on this machine can all run headless with a native sub-agent facility present: Claude Code 2.1.325 (`--agents`, `stream-json`), Codex 0.169.0 (`multi_agent_v2` stable and on; `enable_fanout` removed), Grok Build 1.0.77 (subagents on by default, `--no-subagents`, `streaming-json`). Presence is not behaviour; that is what E1 to E3 test | firm (CLI reading) | R0 |
