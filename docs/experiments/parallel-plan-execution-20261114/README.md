# Parallel plan execution probes (2026-11-14)

Journal: [docs/shiploop-parallel-execution-journal.md](../../shiploop-parallel-execution-journal.md). Census: [census/](census/).
Status: **registered before any experiment trial and before the census report was read** (commit order is the proof).
No ShipLoop, skill, agent or catalog file is changed by this study; it lives only under this folder and in the journal.

## Why

The owner asked (2026-11-14) whether the dependency relationships a ShipLoop plan records could drive parallel work
through each harness's own agent framework: opt-in (never the default), decided at run time from the plan, the same on
Claude Code, Codex and Grok Build, a fresh agent context per task, only its outcome kept in the main context, and a
timing-ordered transaction log that shows what interleaved. The first step is experiments in pure isolation (synthetic
plans, no change to any code), run as subprocesses of each harness.

## What the repository already says (checked against the sources this session)

- **A plan carries dependencies at one level only.** A step plan records each step's `deps`; the navigator accepts
  only unique, earlier step IDs (the step-plan validator in `shiploop_navigator.py`, "step deps must name earlier
  steps"), so list order is always a valid topological order. Their readers are the progress and trace views and the
  per-step implement packet's "Depends on:" line. A step plan also records per-step `paths`. The work-item queue is an
  ordered list whose `follows` names requirements, not items; "The script visits queue order serially"
  (`references/navigator.md`) and "Queue execution stays serial; matching topics or files do not manufacture
  dependencies or parallel safety" (6116b91ee95143e8d8b387e8be84df338289c053). Backchain's `parallel_groups` is
  record-only and barred from a navigator result: "No second scheduler" (`references/backchain-planning.md`).
- **ShipLoop once ran independent steps in parallel and retired it.** The implementation chain (Plan Dispatcher with
  Ask Agent workers) was retired by ad30aa1c82665435c1e69771ef079d80d7b92079 after the owner's G1, 2026-10-29,
  "Adopt (a2)". The design commit 8eca9d64826e0073540b6029b6071fc91b553e8e gives the reason: the chain and the per-step
  iteration "conflict in four of the chain's own rules", and "Parallel build's gain was never measured: the live runs
  show overlap ... not a serial counterfactual. What the chain does demonstrably buy is isolation, and the unattended
  retry of a lost worker". The pilot that would measure the per-step ask-agent route was proposed and never run
  (f824adeb3f108e34f4acb5ebd9ca10eeed32128f). **[Wrong, found by the review: it ran later on 2026-10-29; see Amendment A2.]**
- **Earlier live evidence is overlap, on the heavy protocol.** `test/shiploop_e2e/fanout.py` (A and B in parallel, then
  J, 30 s sleeps, through Plan Dispatcher): Codex gpt-5.6-luna medium passed in 587 s, A and B overlapped 29.3 of 30 s,
  J started about 240 s after both ended (f810a78f38f996086f6beba9eceb54403052e8bc); Claude Sonnet 5.5 overlapped
  29.9 of 30 s (e0fb43667f4f9b2386962d46c38f288f56822809). The In Parallel skill's host evidence says unattended
  headless Claude coordination was deferred on 2.1.296 (coordinators returned before their workers, or did not exit)
  and that a Codex trial did not achieve three-worker overlap (`skills/in-parallel/references/hosts.md`). Nothing
  recorded compares a parallel run with a serial run of the same plan.
- **Owner rules that bind any proposal:** the inner loop shows one step at a time and each step is built, tested,
  documented, reviewed and committed before the next (owner 2026-10-18 and 2026-10-27); scripts own graph navigation
  and the model does one step (shiploop-purpose); every command a model runs must be a visible host tool call so hooks
  see it; no second scheduler; no iteration caps without asking; a packet restates its stage because context may clear
  between any two calls; a change needs a materially different outcome (2026-11-14); quality first, then tokens, then
  time (eval-decision-priority). A history digest produced by a subagent this session was checked against these
  sources before use; one of its claims (that no script validates step `deps`) was wrong and is corrected above.

## Questions

- **Q1 opportunity.** How much parallelism do recorded step plans expose, and what would perfect step-level parallelism
  save in recorded wall-clock? (E0, no model.)
- **Q2 mechanism.** Does each harness's native agent facility run independent steps at the same time, and only after
  their dependencies, when a harness-neutral text packet asks for it? (E1 to E3.)
- **Q3 counterfactual.** What does it cost and save against the serial run of the same plan in the same harness:
  makespan, tokens, the main context's growth? (E2, E3.)
- **Q4 who navigates.** Is it safer for the model to read the plan and decide what is ready (A2) or for a script to
  print the ready set (A3, the ShipLoop way)? (E3.)
- **Q5 dynamics.** When a step fails or runs long, do independent steps continue, dependents hold, and the final report
  stay true? (E4, designed here, not run in round 1.)
- **Q6 shared writes and outcome-only retention.** Which work can share one checkout (read-only analysis, writers with
  disjoint paths, writers that commit), and does a fresh context keep the parent's context small? (E5, E6, designed
  after E1 shows each host's event and usage fields; not run in round 1.)

| Experiment | Question | Model calls | Round 1 |
|---|---|---|---|
| E0 census of recorded step plans | Q1 | none | runs (by a read-only agent) |
| E1 probe: one step, one sub-agent, per host | event shapes, attribution, exit | 1 trial per host | runs |
| E2 fan4: four independent 30 s steps, serial vs parallel | Q2, Q3 | 2 arms per host | runs |
| E3 ragged6: six steps with a diamond and a late join, four arms | Q2, Q3, Q4 | 4 arms per host | runs as far as E2 supports |
| E4 failure injection | Q5 | A2, A3 per host | registered, not run |
| E5 shared checkout writers and commits | Q6 | A3 per host | registered, not run |
| E6 read-only fan-out and the parent's context | Q6 | A0, A1, A3 per host | question only |

## Subjects and conditions

- Hosts and profiles are the E2E harness's declared defaults at b777f69480d6e9457ccd67f02257c2bde6a4146b
  (`HOST_DEFAULTS`, `ROLE_DEFAULTS` in `test/shiploop_e2e/hosts.py`), not tuned: Claude Code 2.1.325 with
  `claude-sonnet-5-5`; Codex 0.169.0 with `gpt-6.1-sol` at `medium` (native workers pinned to the same model and effort
  by the argv `hosts.py` builds); Grok Build 1.0.77 with `grok-4.6` at `xhigh`. Versions are read from the launch and
  recorded per trial. One model per host: a result is about that host and model.
- No ShipLoop, plugin or skill is installed; the packet is plain text. Profiles come from `hosts.py` (a throwaway HOME
  linking only the Grok or Codex sign-in; Claude with project and local settings only, so the owner's plugins and hooks
  stay out). Permission mode `auto` as the E2E runner uses, plus an allow rule for the kit's command; Codex runs
  `danger-full-access` with approvals off as `hosts.py` does, inside a throwaway working directory.
- The trial runner builds each argv and environment through `hosts.host(name)` and adds one thing `hosts.run_agent`
  does not keep: a receive timestamp on every raw event line (and the raw Codex events, which `CodexTranslator` rewrites
  and thereby drops agent items). This is the one deviation from "drive the harness, don't hand-roll a runner"
  (use-the-codex-harness): that rule is about measuring ShipLoop through `run.py`, and this study has no ShipLoop.
- No judge: every measure is a script, so no judge model is involved. A trial has a wall-clock ceiling (a safety net
  that ends in a recorded `timeout`, never a verdict) and Claude trials carry a dollar ceiling.
- Load average and the machine's other work are recorded per trial; the steps are `sleep`s, so their duration does not
  depend on load, but model latency does. Trials of different hosts may run side by side; trials of one host do not.
- Trial folders live in the session scratchpad; compact evidence (ledger, score, invocation, packet, plan, trimmed
  events, timeline) is exported here under `evidence/` (never a folder called `results/`).

## The kit (apparatus, not ShipLoop code)

`dagkit.py` is a stdlib-only script every arm calls through the host's own shell tool, so each command is a visible
host tool call. It is the ground truth for when each step ran. Commands: `init` (the launcher runs it), `ready`
(prints one JSON line: `ready`, `claimed`, `running`, `done`, `failed`, `blocked`, `waiting`, `complete`; `--claim`
claims what it returns so a second call does not offer it again), `run --step ID` (refuses with exit 3 and a
`refused` event when a dependency has not ended OK or the step already started; otherwise logs `start`, sleeps the
step's declared seconds, writes `out/ID.json` whose hash chains the dependencies' hashes, logs `end` or, for an injected
fault, `fail`, and prints one line), `verify` (recomputes the chain and the ledger: every step ended exactly once, none
started before its dependencies ended, no step run twice; prints `VERIFY OK ...` or `VERIFY FAIL <reasons>`) and
`timeline`. Every call appends events to `ledger.jsonl` (one JSON object per line: `seq`, `ts` epoch seconds, `at` UTC
text, `kind`, `step`, `pid`, `ppid`, `detail`), under a file lock so `seq` is a total order. A step cannot be reported
done without its `end` event, and the final report is compared with the ledger, never trusted.

The guard refuses a premature start, which keeps a wrong model decision harmless; the refusal is the measure of that
decision (M4). The kit knows nothing about ShipLoop's stages: a "step" is a unit of synthetic work.

## Arms and packets (the files in `packets/`, templates with named slots)

- **A0 serial-main.** The parent runs every step itself, one at a time, in dependency order; no sub-agent, no
  background job. The status quo of one conversation doing one step at a time.
- **A1 serial-agents.** One fresh sub-agent per step, one at a time, the parent waiting for each. The per-agent
  overhead without any concurrency, so the benefit of overlap is not confused with the cost of a fresh context.
- **A2 parallel, model-navigated.** The packet names the plan file; the parent decides what is ready, starts every ready
  step as its own fresh sub-agent together and starts newly ready steps as soon as a sub-agent returns.
- **A3 parallel, script-navigated.** The packet does not show the plan. The parent calls `ready --claim`, starts one
  fresh sub-agent per returned id together, and calls `ready` again when any returns, until `complete`. The script
  owns dependency resolution, as ShipLoop's navigator does; the model only launches and collects.
- Packet wording is neutral: "your built-in facility for a fresh agent with its own context"; no host tool is named
  (**N**). A host that does not parallelize from N gets one more trial with a single host-specific sentence naming its
  facility (**H**); both are recorded. A packet forbids shell background jobs and parent-side execution in A1 to A3; a
  trial that uses them is classified `shell-parallel` or `parent-executed`, a different mechanism, and reported as such.
- Every packet ends the same way: run `verify`, then print one last line `FINAL ` followed by a JSON object listing
  the steps done, failed and not run.

## Fixtures (`plans/`, in ShipLoop's step shape: `id`, `task`, `deps`, `criteria`, `proof`, `paths`; the kit's `seconds`
and `fail` sit under `kit`)

| Fixture | Shape | Serial sum | Critical path | Ideal makespan with refill |
|---|---|---|---|---|
| `one1` | S1 (5 s) | 5 s | 5 s | 5 s |
| `fan4` | S1 to S4 independent, 30 s each | 120 s | 30 s | 30 s |
| `ragged6` | S1 40 s; S2 10 s; S3 10 s after S2; S4 20 s after S1 and S3; S5 30 s; S6 10 s after S4 and S5 | 120 s | 70 s (S1, S4, S6) | 70 s; 80 s if a step waits for the whole wave |
| `chain4` | S1 to S4 in a line, 20 s each (control: nothing to overlap) | 80 s | 80 s | 80 s |
| `fail5` (E4) | S1, S2 independent; S3 after S1 fails; S4 after S2; S5 after S3 and S4 | n/a | n/a | S5 must not run |

`ragged6` separates a refilling scheduler (S3 starts when S2 ends at 10 s) from a wave scheduler (S3 starts when S1 ends
at 40 s) by 10 s. Durations are short so a trial is cheap; a real step's iteration is minutes, so a longer round
follows if overlap is real.

## Measures (all by script, from `ledger.jsonl`, the host's raw events and the invocation record)

- **M1 makespan:** last `end` minus first `start`. **M2:** realized fraction of the ideal saving,
  (A0 makespan minus the arm's) divided by (A0 makespan minus the critical path), per host.
- **M3 overlap:** peak simultaneous steps from the ledger intervals; for each declared-independent pair, whether the
  intervals overlap by at least half of the shorter step.
- **M4 order:** refused attempts (a model started a step too early; the kit stopped it); starts before a dependency's
  `end` (must be 0 by construction, counted to prove the guard); steps started twice.
- **M5 integrity:** `verify` verdict, steps run exactly once, steps with no `end`.
- **M6 exit:** host process exit code, seconds from the last ledger event to process exit, `timeout` or not.
- **M7 report fidelity:** the `FINAL` object against the ledger (a step reported done that never ended is a false claim).
- **M8 tokens:** input, output and cache tokens as the host reports them, summed; the parent's peak input tokens in one
  call where reported. Hosts that do not report a figure are marked unknown, never zero.
- **M9 dispatch latency:** for each step with dependencies, `start` minus the latest dependency `end`.
- **M10 mechanism:** `native-agents`, `shell-parallel`, `parent-executed` or `serial`, from the raw events (which tool
  calls ran the kit's `run`, and in which agent context where the host attributes it) and the ledger. E1 establishes,
  per host, whether a tool call can be attributed to a sub-agent; where it cannot, the mechanism is classified from
  spawn and return events and the ledger's overlap, and that limit is stated.
- **M11 refill:** whether S3 of `ragged6` started before S1 ended (completion-driven) or after (wave).

## Predictions (registered; scored as written; a better reading goes on its own line, never a rescore)

E0 census (registered before the census report was read; "deps-complete" means every step of the plan has `deps`):
- **C1 (55%):** between 10% and 35% (inclusive) of deps-complete step plans with at least two steps have an independent
  pair (critical path shorter than the step count).
- **C2 (60%):** the time-weighted ideal saving, one minus the sum of critical-path times over the sum of serial times,
  is under 12% over the plans whose step times were recovered.
- **C3 (50%):** among step pairs that share a level and have `paths` recorded, at least 30% overlap.
- **C4 (65%):** step iteration times are recoverable for fewer than half of all step plans.
- **C5 (45%):** at least a quarter of all step plans carry no `deps` on any step.

E2 and E3 (round 1, one trial per cell, so each is about these trials, not a rate):
- **P1 (75% / 55% / 60%):** Claude / Codex / Grok reach peak concurrency of at least 3 on `fan4` in arm A2 with packet N.
- **P2 (90%):** arm A0 shows peak concurrency 1 and no refused attempt on all three hosts.
- **P3 (85%):** `verify` is OK in every trial that reaches peak concurrency of at least 2, on every host.
- **P4 (80%):** arm A3 has no refused attempt on any host; **P5 (35%):** arm A2 has at least one on at least one host.
- **P6 (40%):** on `ragged6`, at least one host shows refill (M11) in A3; **P7 (35%):** at least one in A2.
- **P8 (55% / 40% / 45%):** Claude / Codex / Grok: the best parallel arm's makespan is at least 20% under A0's.
- **P9 (75%):** on every host, total tokens in a parallel arm are at least 1.5 times A0's where tokens are reported.
- **P10 (60%):** every host process exits 0 within 60 s of its last ledger event in every trial.
- **P11 (40%):** every host parallelizes from the neutral packet N alone (no H trial needed).
- **P12 (15%):** at least one trial uses shell background jobs although the packet forbids them.

## Decision rules (registered)

- **R0, ordering only.** If the census's time-weighted ideal saving is under 10%, later rounds put read-only fan-out
  and context isolation (E6) first and treat the write DAG (E3 to E5) as mechanism knowledge; from 10% to 25%, an opt-in
  for plans that expose width at least 2 and disjoint `paths` (a predicate a script can compute from the plan); above
  25%, step-level parallelism becomes the main lever and integration the next unknown. These are my thresholds for
  ordering rounds, not product bars; a product change still needs the owner's materiality rule and quality, then
  tokens, then time.
- **R1 elicitation.** A host "parallelizes from the packet" when `fan4` A2 reaches peak 2 or more and at least one
  declared-independent pair of `ragged6` overlaps by half of the shorter step.
- **R2 safe.** A mechanism is "safe on a host" when none of its trials has a failed `verify`, a step run twice, or a
  start before a dependency's end; refused attempts are reported separately and do not fail it.
- **R3 efficiency.** Report the realized fraction (M2) beside the token ratio (M8); a mechanism pays only if the
  fraction is above zero and the token ratio is stated next to it. No bar is invented before there is spread to read.
- **R4 who navigates.** If A3 has fewer refused attempts or fewer false reports than A2 on a host, script-owned
  readiness is the design to carry forward on that host.

## Limits and contrary evidence, stated in advance

- Synthetic sleeping steps show orchestration, not step quality, and a fresh agent's start-up cost (about 86k tokens on
  a fresh Claude subagent, host-status-display-facts) looms larger against 30 s steps than against a step iteration of
  minutes; round 1 can show whether overlap is real, not whether it pays on real work.
- One trial per cell in round 1: exploratory. One model per host. The isolated profile has none of the owner's hooks,
  so hook visibility of sub-agent calls is untested (a later round, with a logging hook).
- Hosts differ in how a sub-agent's return reaches the parent (together or one at a time), so "refill" mixes the
  model's choice and the host's semantics.
- The ledger says when a step ran, not which agent ran it; attribution comes from each host's events and may be
  impossible on a host.
- The census population is E2E test cases: small, fully specified and often repeated, not the owner's projects.
- A write DAG in one checkout also needs isolation and integration (the chain's real value); E5 only probes the
  simplest case.

## Amendments (dated, each made before any trial, none changes a prediction)

- **A1 (2026-11-14): Codex's multi-agent feature differs between profiles.** `codex features list` in a throwaway
  `CODEX_HOME` that holds only the sign-in (the profile `hosts.CodexHost.env` builds) shows the deprecated `multi_agent`
  on and `multi_agent_v2` (stable) **off**; the owner's own profile has both on. Condition added: every Codex arm runs in
  the harness profile (v1 only) and, where it matters, again with `--enable multi_agent_v2` (the launcher's
  `--enable-feature`), the effective state recorded in each trial's invocation. P1, P2 and P8 are scored on the profile as
  run; a trial in the other profile is a separate cell and is never pooled with it.
- **A2 (2026-11-14, before any trial): corrections and framing, from Astra's max-effort review**
  ([evidence/astra-review.md](evidence/astra-review.md), verbatim; the weighing is in the journal, entry R1).
  - *Erratum.* "Proposed and never run" about the per-step pilot is wrong. It ran on 2026-10-29
    (eadad0c84f8a213287459bbf6252411ac0b90fce; Codex gpt-6.1-terra xhigh, case stand-in-parser, one run per arm, "indicative"):
    inline 5.3 min, 1 thread, 8.06 M input and 23.5 k output tokens; per-step ask-agent 21.6 min, 14 threads (13 fresh workers),
    23.11 M and 105.2 k; item-level ask-agent 17.3 min, 9 threads, 19.94 M and 85.1 k; all slice verdicts pass. Its workers ran one at a
    time, so it supplies no parallel-against-serial counterfactual, and the killed-worker question stayed unmeasured; it does give A1 a
    prior for the cost of a fresh context in real ShipLoop: about (21.6 - 5.3) / 13 = 1.25 min and 1.2 M input tokens per worker
    (four per step, one each for implement, test, document and the step's review). I read the commit that proposed the pilot and did
    not search forward for its result.
  - *Narrowed claim.* The navigator's accepted step-plan schema carries explicit step-to-step dependencies (`deps`), validated in form;
    an omitted `deps` means unknown, not independent; planning notes, expectations and Backchain hold other prerequisite information; neither
    valid `deps` nor disjoint `paths` proves semantic independence. "Dependencies at one level only" above reads that way.
  - *Translator wording.* `CodexTranslator` does not drop every agent item (its generic branch keeps other item types as synthesized tool
    calls); raw events are kept to preserve exact structure, timing and attribution, not to recover items it always discards.
  - *Profiles frozen.* Codex predictions P1, P2 and P8 are scored on the harness profile (multi_agent v1); `+v2` trials are exploratory
    cells. Each trial records the effective tool list from the host's init event and the model identity of every thread where the stream
    shows it; the roughly 86k-token start-up figure is a dated local observation, not a constant.
  - *Unit of work (the review's P0).* The synthetic units are generic parallel work units. Running ShipLoop steps concurrently would
    break the owner's per-step iteration (build, test, document, review and commit before the next), so a result here licenses a
    claim about a mechanism, not about concurrent ShipLoop steps, and E0's step-level saving is an upper bound that needs a separate
    owner decision. The bridge after the mechanism is parallel work inside one authorized stage (bounded investigations or reviews,
    one owner accepting them) with a context reset and a stale-state case; E6 and E7 are small and come forward (below).
  - *"True dynamic workflow"* means completion-driven execution under one authority: the script recomputes what is eligible when an
    outcome is accepted, a prerequisite fails or capacity changes; workers never choose successors or revise the graph. A2 (the model
    reads the plan) is a diagnostic of model scheduling and is not a candidate architecture; A3 is.
- **A3 (2026-11-14, before any trial): arms, variants and order.**
  - A new arm **A3s** is A3 at capacity one: the same readiness, worker and return contract, one sub-agent at a time, the matched
    serial control. A3 gains a capacity (default the plan's step count), a `release` for a claim whose launch failed and a `deferred`
    list (`ready --claim --capacity N`); the A3 packet's sha256 is now 882b30386126ef763041f9bb1e5c8106392cce2b568601fab59868167a91cf8e
    (A0, A1 and A2 are unchanged). A1 stays as the model-navigated serial control.
  - **N** (anonymous wording) is the experiment on spontaneous elicitation. **H** is the operational route: one small host binding
    taken from the repository's own recipes (`skills/ask-agent/references/host-capabilities.md`: Claude a fresh general-purpose
    `Agent` or `Task`; Codex native asynchronous spawn with `fork_turns` "none" and native wait; Grok a general-purpose `spawn_subagent`
    collected with `get_command_or_subagent_output`, never a restricted `explore` or `plan` worker). Each H sentence is written after
    E1 shows the host's real tool schema and is pinned by hash before its first use.
  - Round-1 order: E1 on Claude first, aimed at return and exit (the strongest known host-lifecycle uncertainty), then Codex (harness
    profile; `+v2` once) and Grok; then on each qualifying host fan4 A0, A3s and A3 (and A2 where P1 needs it), `ragged6` A3, then
    `fail5` and the small context fixtures. Timing trials run one at a time, arm order counterbalanced; trials are repeated only when the
    result could change the next decision; not every arm is multiplied across both Codex profiles.
- **A4 (2026-11-14, before any trial): measures, scoring clarifications, stop rules.** The registered predictions stand as written.
  - M1, M2: the makespan (first start to last end) is reported with launch to first start, launch to verified result and launch to
    process exit; a saving is credited only to a valid trial (the process exited, nothing scaled, no step started and never ended, the
    verdict the fixture expects, a parent report that names every step once and matches the ledger, no duplicate terminal event); `chain4`
    has no saving to credit.
  - M4, M5: refusals are counted by category (premature, duplicate, unknown, prerequisite-failed, input-invalid); verify requires exactly
    one start and one terminal event per started step, successful prerequisites, the plan unchanged since init and one consistent snapshot.
  - M6: three tails from the process's exit: since the last work terminal event, since the parent's final report, since the last collection
    return. P10 is scored as exit code 0 and a tail of at most 60 s since the final report.
  - M7: only the parent's last `FINAL` line counts. M8: as the host reports; whether its figure includes sub-agent threads and whether it
    is cumulative is settled in E1 and stated; unknown stays unknown; Codex cached input is `cached_input_tokens`.
  - M10: `native-agents` needs the kit's run calls attributed to child agents in the host's own stream (Claude's stream attributes; Codex
    and Grok are treated as unattributable until E1 shows otherwise and are then `native-agents-unattributed`); spawns beside parent-run
    steps are `parent-executed`; command text is classified in full.
  - P3, P4, P6: a host with no qualifying trial (peak at least 2 for P3, a completed A3 trial for P4, a valid A3 `ragged6` trial for P6)
    scores missed, never vacuously held. P8: the eligible arms are the valid A3 trials on `ragged6` on the host's scoring profile, compared
    with the valid A0 of that profile; none eligible scores missed. P9: "a parallel arm" is every valid A2 or A3 trial of that host;
    unreported tokens are not scored and say so. P11 and R1 are scored on packet N with A3 (and A2 for P1). P12 needs the calibrated detector.
  - R2 now reads "completed the guarded fixture correctly with attribution established" and keeps model refusals, guard correctness and
    task completion apart. R0 orders rounds only and a census average does not argue against an opt-in tail. R3: results are reported and
    no payoff is claimed from round 1 (quality, then tokens, then time). R4: script-owned readiness stays the design because it is an owner
    rule; A3 against A2 is reported, not a condition.
  - **Stop rules.** Stop a host and condition when attribution cannot be established where it is claimed, when the scorer would credit a
    known-invalid trace, when the host cannot return and exit reliably, or when work this trial started is still running after the process
    exits; record it as unqualified or censored, never as a general failure of the host. A loss on cost with 30 s tasks is a granularity
    result, not a stop. **R5 redirect:** if the only demonstrated benefit needs steps to run concurrently across the per-step lifecycle,
    redirect to bounded parallel work inside one stage unless the owner changes that constraint.
  - New predictions, registered before any trial: **P13 (70%):** on every host with valid A0 and A1 trials of `chain4`, A1's makespan
    exceeds A0's by 5 s to 60 s per fresh sub-agent ((A1 - A0) / 4). **P14 (75%):** A1's total input tokens are at least twice A0's
    wherever the host reports them (the pilot's real-ShipLoop ratio was 2.9).
  - **E6 and E7, small, brought forward (designs, run after the mechanism qualifies):** E6 outcome-only retention: a worker reads about
    20 KB of irrelevant material and returns a short result with an evidence locator; a fresh parent continuation must answer the next
    question from that result alone. E7 stale state: a worker starts against a state file at revision R1, the parent changes it to R2
    before the worker returns, and the parent must record a disposition for the stale result (accept, redo or ask) rather than accept it.

- **A5 (2026-11-14, after E1 and the owner's course correction, before any task trial): native agents doing real work.**
  - *The owner's message, mid-session:* "My hope was not actually to use bash calls as subagents. I was hoping to use the native agent
    infrastructure of the harnesses, but I'm not sure if it's possible or not. You don't necessarily have to reuse some of the things
    that I've previously created, but you can leverage it if you think it's valuable. Help me figure out what the right thing is to do here."
  - *What E1 showed.* The sub-agents in E1 were native on all three harnesses: Claude Code's `Agent` tool (a general-purpose,
    foreground, depth-1 agent; its Bash call attributed to it in the stream), Codex's `spawn_agent` with `fork_turns` "none" and `wait_agent`
    (a child thread with its own rollout file, naming its parent and depth), Grok's `spawn_subagent` (a general-purpose agent that inherits the
    parent's model; its command attributed to it by session id in `logs/unified.jsonl`). The shell command was only the payload, there to
    make timing measurable; but a sleep is the wrong payload for the question, because it exercises neither a fresh context doing work nor
    an outcome returned to a small parent context. E1 is kept as qualification, not as the result.
  - *The new design (ShipLoop-shaped).* The script prints the ready set and each task's instructions; a fresh native sub-agent does the
    task (real analysis of log files it reads itself) and reports its outcome through the script's callback (`begin`, then `complete`); the
    parent only launches children and collects one-line acknowledgements, never reading the evidence. Fixture **`analysis5`** (plans/):
    four independent log analyses T1 to T4 and T5, which depends on all four (the sum, read from the script, not from the logs). `evidence.py`
    generates the logs from a seed (default 20261114, 400 events each) and an independent oracle; the oracle sits beside `work/` in the trial
    folder and only the scorer reads it. Packets `task-A0.md` (the parent does every task itself, one context) and `task-A3.md` (script-owned
    ready set, up to four sub-agents at once; capacity one is A3s). The packet wording stays anonymous (N): E1 showed it suffices for one
    sub-agent on all three hosts. The kit's bash calls are the script interface (ShipLoop itself talks to its script by command), not the
    workers; the host's own record of its sub-agents (above) is read as the cross-check that the workers were native agents.
  - *Corrected premise.* In E1 both Codex profiles ran `multi_agent_version` v2 in the child rollouts although `codex features list` shows v2
    off in the harness profile, with the same tool names and the same overhead. A1's "harness profile = v1" is therefore dropped: the
    effective version is read from the rollouts, and `+v2` trials are not run unless a rollout shows v1.
  - *Measures added:* correctness (each answer and the final answer against the oracle; a trial with a wrong answer is not valid for a
    comparison, quality first), the host's own agent records (count, peak, intervals, kind, depth), tokens split into the parent's and the
    children's (the parent's total input tokens stand for the work done in its context), valid as before.
  - *Order (arm order counterbalanced across hosts; each host runs one trial at a time, the three hosts side by side):* Claude A3 then A0;
    Codex A0 then A3; Grok A3 then A0; one trial per cell. A3s is added on a host only if its A3 shows peak at least 2 and the cost needs separating.
  - *Predictions, registered before any task trial:* **P16 (70%):** Claude A3's ledger peak (begin to complete) is at least 3; **P17 (55%)** Codex;
    **P18 (50%)** Grok. **P19 (75%):** every task trial, every host and arm, answers all five tasks correctly. **P20 (70%):** on each host where A3
    has peak at least 3 and five correct answers, A3's makespan is below A0's. **P21 (70%):** on every host, A3's total input tokens (all contexts,
    cache included) are at least 1.3 times A0's. **P22 (80%):** on every host where the figure separates the parent, the parent's total input tokens
    in A3 are below A0's (Grok's is not scored if its figure's scope is unknown). **P23 (70%):** every host exits 0 with a tail of at most 60 s
    since its final report in every task trial. **P24 (40%):** at least one host's A3 shows an agent peak of 1 although the packet asks for the
    sub-agents together.
  - *Decision rule R6.* A host "runs native parallel fan-out and fan-in on real work" when its A3 trial is valid (five correct answers, verify
    OK, a faithful report, exit 0) and both the host's own agent records and the kit's ledger show a peak of at least 3. Time, tokens and parent
    context are reported as measured; one trial per cell supports no payoff claim and no rate.
  - *Limits:* one workload, read-only, no write conflict and no commit; one model per host; three hosts side by side; a later trial of a host
    may profit from prompt caches the earlier one warmed (order is counterbalanced, not removed).

- **A6 (2026-11-14, after the pilot began and before any high-effort Claude result was read): the owner's model profiles.** The owner said:
  "The models that we should be using to run tests with harnesses would be Sonnet at high, Grok 4.6 at extra high, or SOL-6.1 on medium", and
  "If you need to just test basics first, you can just use grok as your first basic test just to see if things are working." The profiles are
  Claude `claude-sonnet-5-5` with `--effort high`, Grok `grok-4.6` at `xhigh`, Codex `gpt-6.1-sol` at `medium`. The Grok and Codex trials already
  matched. The Claude trials that ran before the instruction (E1 `e1-claude` and the pilot's `r1-claude-a3` and `r1-claude-a0`) passed no `--effort`,
  so they ran at the CLI default: they are an exploratory cell labelled "default effort", never pooled with the high-effort cell (the comparison
  already keys the baseline on effort). The registered predictions for Claude are scored on the high-effort trials (`r1h-claude-a3`, `r1h-claude-a0`,
  `e1h-claude`), launched after the instruction. From here a new reader, packet or launcher change gets its first basic check on Grok before the other
  hosts; the registered cells still run on all three.

## Files

`README.md` (this registration), `census/` (E0: script, README, evidence, gated.py), `dagkit.py`, `plans/`, `packets/`,
`launch.py` (one trial), `score.py` (measures, text timeline, ASCII Gantt), `calibrate.py` (the scorer, the kit and the launcher
path against runs with known answers, run before any model call), `fakehost.py` (a stand-in host for that), `export.py`
(compact evidence into `evidence/`), `evidence/` (the Astra review and its question; trial evidence as it is exported).
