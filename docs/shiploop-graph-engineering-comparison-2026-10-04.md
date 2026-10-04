# ShipLoop graph engineering: comparison, measurements, and plan

**Date:** 2026-10-04. **Status:** A1–A3 **implemented**; A4 withdrawn. See
[§5 Plan](#5-plan) for what each item does and
[§7 What landed](#7-what-landed) for the files and tests.

Three sources, with different weight:

- **ShipLoop facts** — read from the source in this checkout. Line references were verified here.
- **External comparison** — web search plus page summaries by a small model. Not read past
  abstract/README level. Treat as directions.
- **Measurements** — derived from 11 protocol-4 run directories (`state.md` `history` +
  `timeline.json` + `run/tests/*-verify*.md`). Small sample, mixed conditions, no repetition per
  condition.

A first draft of this document proposed a different plan (C1–C8). It was revised twice: once by
measurement, once by an Astra review. Both revisions removed more than they added. The
[corrections](#corrections-to-this-document) section records what was withdrawn and why; the
superseded sections are not retained, to avoid stale operative text.

---

## 1. What ShipLoop is, structurally

A **passive** engine. A Python script owns a fixed 34-stage graph, persists it as Markdown
(`state.md`, one `shiploop-state` JSON fence, no writable JSON mirror), and hands the host model
one packet at a time. The engine never calls a model; the model performs one step and runs a
printed callback.

- **Context loss is a design input.** Packets are self-contained, `next` rereads without
  advancing, recovery is a printed command, and a changed prompt or repo is refused rather than
  silently becoming a new run.
- **Script-run verification is an acceptance edge.** The engine reruns the step plan's recorded
  test commands itself and requires exit 0, at 8 stages: `test-green` and `regression` (the
  Until Loop test loop) plus `test-refine`, `static-checks`, `verify`, `integration-verify`,
  `system-test` and `release-verify` (rerun on `done`). A lint gate guards `implement`,
  `test-green` and `regression`.
- **A nested review child** (Improve on Until Loop) converges on consecutive trivial passes and
  is imported once by receipt; the parent keeps no second counter.
- **Whole-delivery scope:** release, consumer verification, delivery authority, guarded workspace
  return with receipts, cross-run knowledge.

Architecture detail: [docs/ARCHITECTURE.md](ARCHITECTURE.md),
[skills/shiploop/references/navigator.md](../skills/shiploop/references/navigator.md).

## 2. Comparison with other graph and harness engineering

| System | Closest to ShipLoop on | Differs |
|---|---|---|
| [Blueprint First, Model Second](https://arxiv.org/abs/2508.02721) | Same thesis: code owns the path, the LLM does bounded sub-tasks. 35.56% vs 18.00% on one backbone | Narrow benchmark, not an SDLC |
| [StateFlow](https://arxiv.org/abs/2403.11322) | FSM with state-specific instructions ≈ a packet per stage. +13%/+28% over ReAct at 5×/3× lower cost | Research paradigm, not a durable harness |
| [Agentless](https://arxiv.org/html/2604.03515v2) (via scaffold taxonomy) | Fixed pipeline, no feedback loop, competitive and cheap ($0.34/bug) | Different output contract: patch a bug, not ship a product |
| [Archon](https://github.com/coleam00/Archon) | Deterministic bash/test nodes beside AI nodes, worktree per run, approval gates, `until` loops, `fresh_context`, resume | Engine runs the model; graphs are user-authored YAML |
| [heddle](https://github.com/DJRHails/heddle) | "Control flow is code, only leaves are model-driven" | Engine calls models; content-addressed journal replay; hard call cap; **three-outcome verdicts** |
| [LangGraph](https://www.langchain.com/resources/langgraph-vs-temporal) | Graph plus persisted state | Per-node checkpoints, `interrupt()`, time travel, `Send` fan-out, tracing |
| Temporal ([comparison](https://medium.com/data-science-collective/inngest-vs-temporal-vs-dbos-vs-langgraph-7d0557ff6c53)) | Recovery, idempotent replay | Event history, deterministic replay, crash detection, retries, sagas |
| [MS Agent Framework](https://learn.microsoft.com/en-us/agent-framework/workflows/workflows) | Fan-out with joins | Pregel supersteps; checkpoint per superstep |
| [Burr](https://github.com/apache/burr) | State machine of actions | Tracking UI, persisters, rewind-and-fork |
| [Ralph loop](https://www.agentpatterns.ai/loop-engineering/ralph-wiggum-loop/) | State on disk, not in context | Fresh context every iteration; ShipLoop measured packet-text clears at 0/2 and chose same-context plus compaction |
| [Anthropic long-running harness](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | Progress file, git, one feature per session | Feature list in **JSON because models edit Markdown too freely** — see §6 |
| [Superpowers](https://github.com/pcvelz/superpowers) | Plan, per-task isolation, two-stage review | Convention in prompts, no script-owned graph |
| [Spec Kit / OpenSpec / Kiro](https://dabase.com/blog/2026/sdd-framework-comparison/) | Spec-driven phases; OpenSpec deltas resemble preserve/add/modify/retire | Stop at implement; no release or consumer verification |
| [Gas Town + Beads](https://ianbull.com/posts/beads/) | Durable multi-agent state | Git-backed JSONL issue DB as control plane; merge-queue agent |
| [CAAF](https://arxiv.org/abs/2604.17025) | Harness as an asset; context firewalls | Machine-readable invariant registry; state locking |
| [Looping Is Not Reliability](https://arxiv.org/abs/2607.24604) | Evidence tied to code state | Stale verifier traces: 34/135 failures vs 4/135; best-checkpoint preservation |
| [Safe to Resume?](https://arxiv.org/abs/2608.29381) | Refuses to replay uncertain external effects | Shows LangGraph, Cline and others restoring state inconsistent with external effects |
| [Diagrid on checkpointing](https://www.diagrid.io/blog/still-not-durable-how-microsoft-agent-framework-and-strands-agents-repeat-the-same-mistake) | Idempotent replay of accepted callbacks | "Checkpointing is a storage operation, not a reliability guarantee" |
| [TraceCompiler](https://arxiv.org/abs/2608.02680) | Shrinking the LLM share of a workflow | Mines traces into mostly deterministic workflows; classifies each binding |

### Not found elsewhere in this survey

1. **Inverted control.** The engine never calls a model; the host pulls packets and reports via an
   action-bound callback. This is why one skill runs on Claude, Codex, Grok, Cursor and OpenCode.
   The cost is honest and stated: the script cannot force execution (hence keepalive hooks) and
   cannot verify who executed a step.
2. **Script-run verification as an acceptance edge** rather than trusting a model's report,
   combined with a nested convergence loop it imports but never re-implements.
3. **Delivery honesty** — release, consumer-behaviour verification, delivery authority and guarded
   return with receipts, each kept separate from "tests passed".
4. **A written spec for the harness itself** (`test/shiploop_e2e/SPEC.md`, S-1..S-15) that every
   change is judged against.

### Found elsewhere, absent here

Per-step traces with a UI (LangGraph, Burr); replay and fork from a recorded point (heddle, Burr,
Temporal); declarative user-authored graphs (Archon); machine-checkable invariants (CAAF);
preserving the best verified checkpoint across failed revisions; three-outcome verdicts that keep
infrastructure failure apart from a finding (heddle); trace mining to move recurring LLM decisions
into code (TraceCompiler).

## 3. What the survey contributed

Asked directly: **one plan item is a genuine import.** The survey's value was validation and
elimination, not generation.

| Surveyed | Became | Strength |
|---|---|---|
| heddle's three-outcome discipline — "infrastructure failure must not read as a finding" | **A1** | Direct; the one real import |
| Blueprint-First, StateFlow | nothing | **Validation** — ShipLoop's own thesis, with numbers |
| heddle journal / Temporal event history / MS supersteps | **declined** | Converged on A3's harness-side record instead |
| Burr/LangGraph tracking, Agentless JSONL stages | A2 | Weak; A2 is a correction to existing code |
| Temporal crash detection, exactly-once, sagas | nothing | Inapplicable: the engine never runs the model, so it cannot observe a crashed host |
| LangGraph `interrupt()`, time travel, `Send` | nothing | Already met by pause/resume, the `revisions` counter, chains |
| Ralph fresh context | nothing | Closed with evidence (packet-text clears 0/2) |
| Archon YAML, CAAF registry, Beads control plane | nothing | Declined; conflict with a fixed tested graph, "no new formal schema", and `state.md` |
| "Looping Is Not Reliability" state-bound evidence | **withdrawn** | The engine reruns its own checks, so its staleness window is tiny |
| Superpowers two-stage review | not assessed | May inform Improve's internal review structure; out of scope |
| TraceCompiler | **future** | The downstream use of better refusal data plus the existing S-4/S-5 glue metric: deciding which model-written glue becomes script-owned |

## 4. Measurements

11 protocol-4 runs (the only supported protocol; 40 other surviving `state.md` files are v1–v3,
which the code refuses to load). All 12 baseline output directories still exist, though 10 under
`/private/tmp` have lost their top-level `metrics.json` and `result.json`.

**These are measurements of a live tree, so they are perishable.** One of the 11 was still being
written while this document was drafted — a `--resume-run` of the Luna `battleship` case that had
been going since 01:55. Its totals below are a snapshot. Figures were taken ~09:00 and the
composition re-checked at 09:39; a later reading will differ.

### 4.1 Outcomes

341 accepted actions: **336 carried `done`**, 1 `blocked`, 2 `revise`, 1 `repeat`, 1 `replan`.
Branching fired 5 times across 11 runs, at only 4 stages (`plan`, `implement`, `test-refine`,
`system-test`).

**This is not a 98.5% first-pass rate**, as an earlier draft claimed. The denominator is *accepted
actions*; a refused callback never becomes an action, so it is excluded. Separately, 6
test-verification refusals appear across 84 verify records, with a maximum of 1 per action. Other
refusal kinds (malformed result, stale action) are recorded nowhere, so the true first-pass rate
is **unknown**.

The usable conclusion is narrower: the graph's branching machinery rarely fires, and `history`
already records `{stage, outcome, workitem, action}` for every accepted action
([navigator.py:985](../skills/shiploop/scripts/shiploop_navigator.py:985)), so no new recording is
needed to see it.

### 4.2 Completion

Runs reaching each phase: 11 intake→`test-strategy`, 10 `prepare`, 9 `step-plan`→`test-red`,
8 `implement`→`skill-validate`, 7 `static-checks`→`handoff`. **7 of 11 reached `handoff`.** The
other four, re-checked 2026-10-04 09:39: one `blocked` at `plan` with its reason recorded, **one
still in flight** (a live `--resume-run` of the Luna battleship case, started 01:55 and writing
state 20 minutes earlier), and **two abandoned mid-run** at 8 and 13 accepted actions, untouched
for ~24 h, with no recorded cause. An earlier version of this section counted all three
non-blocked ones as attrition; the in-flight run is not attrition. A complete run is ~35 accepted actions
(`implement` averages 4, one per planned step).

### 4.3 Time, and the confound that invalidates the obvious reading

Two runs hold 1290 of 1444 total minutes (89%) and 945 of 994 planning minutes (95%):

| Run | Host / case | Total | Planning | Improve children | End state |
|---|---|---|---|---|---|
| `work-…-225401-173a04` | Luna / `battleship` | 1002 min+ | 688 min (69%) | 7 | `active` at inner-loop, **still in flight** — its totals keep growing |
| `work-…-171500-4913b1` | Luna / `battleship` | 287 min | 257 min (90%) | 3 | `blocked` at `plan`, never reached `implement` |
| other 9 | Sonnet, `hello`, `seat-reservations` | 155 min | 49 min (32%) | 62 | 7 done |

**Both outliers are the Luna (Codex GPT-6, xhigh) runs, and both are `battleship`.** Every fast
run is Sonnet or a trivial case. The only protocol-4 `battleship` runs are those two, so **host
and case complexity are perfectly confounded** and no generic planning-cost claim is supportable.
For the other 9 runs planning is 32% of a ~17-minute run — unremarkable for a harness that
deliberately front-loads spec, strategy and plan.

The repo already diagnoses these runs. `test/shiploop_e2e/LEARNINGS.md:583`: *"10 repeat passes
cost about 46 minutes of 291 (16%), and the stage's first-pass work, not repeat passes, is the"*
cost. `LEARNINGS.md:552` records the blocked run's cause as a hand-built Backchain loop contract
that cannot persist its first callback. **Review-pass count is ~16%, not the driver.**

### 4.4 What is genuinely unrecorded

1. **Why a run stopped.** Two runs sit `active` with no cause (a third is still in flight). The engine cannot record this: it
   is not running when the host dies, exhausts credits, or is killed.
2. **Non-verification refusals.** Test verification *does* leave records before the gate raises —
   that is why 84 exist. Malformed results and stale actions leave nothing.
3. **Measured cost and tokens per action.** Only pro-rata; 2 of 12 baseline rows report `$0`
   because the host never reported cost.

## 5. Plan

Ranked. **No item changes what a passing run does today.** A1 is correctness; A2 is measurement
hygiene; A3 replaces an engine feature with a harness one.

### A1 — Test-loop classification and recovery guidance

Four defects in one code path, none observed in the 11 runs (223 command runs: 199 `passed`,
17 `red`, 6 `ids-missing`, 1 `uncounted`, and **zero** `timeout`/`skipped`/`error`). The corpus
cannot observe them: its products are `hello`, `csv-report` and `battleship`, whose suites finish
in seconds. That is itself a finding about the corpus under S-13 — no case exercises a slow or
broken suite.

1. **`error` is never persisted.** `OSError` sets a local `status = "error"` with `code = None`
   ([test_loop.py:600](../skills/shiploop/scripts/shiploop_test_loop.py:600)), then the following
   `elif code is None` branch writes `"failed"`. A spawn failure is recorded as a test failure and
   the `"error"` status never reaches a record. **Fix this first**; any reclassification that
   matches on `"error"` would otherwise match nothing.
2. **Unavailable execution counts toward the failure cap.** `timeout` and `skipped` (the
   invocation budget ran out) collapse into `"passed": all(...)`
   ([:510](../skills/shiploop/scripts/shiploop_test_loop.py:510)), and `refused_runs()`
   ([:442](../skills/shiploop/scripts/shiploop_test_loop.py:529)) counts any falsy `passed`
   toward `MAX_REFUSED_RUNS = 7`. Exclude attempts whose only non-passing results are unavailable
   execution. **Keep `passed: bool`** — it answers the acceptance question, and per-command
   statuses already explain why. **Define mixed attempts explicitly:** a real failing check plus a
   timeout stays a failure.
3. **Timeout is not a diagnosis.** A timeout can mean a product deadlock, a broken test, a slow
   valid suite, or an external dependency. It establishes incomplete verification, not who must
   repair it. Required verification must stay *unavailable* rather than pass (S-9), and must not
   assert a blocker.
4. **The recovery remedy is invalid at 2 of the 8 verify stages.** `revise` is attached only to
   stages between `test-spec` and `integration-verify`
   ([stage_spec.py:539](../skills/shiploop/scripts/shiploop_stage_spec.py:539)); outer stages get
   `replan`. The gate text still says "Report outcome revise"
   ([test_loop.py:508](../skills/shiploop/scripts/shiploop_test_loop.py:508)), which the navigator
   rejects at the outer `system-test` and `release-verify`. Generate guidance from the stage
   contract through **one helper**, and note that outer `replan` requires corrective `work_items`
   ([navigator.py:484](../skills/shiploop/scripts/shiploop_navigator.py:484)) — substituting the
   outcome word is not enough.

Unconditional `revise` guidance appears at more sites than one:
[test_loop.py:282](../skills/shiploop/scripts/shiploop_test_loop.py:282),
[:319](../skills/shiploop/scripts/shiploop_test_loop.py:319),
[:362](../skills/shiploop/scripts/shiploop_test_loop.py:362),
[:508](../skills/shiploop/scripts/shiploop_test_loop.py:508), and
`SKILL.md:488`, `:531`. Fix them together.

**Scope boundaries.** `check_terminal`'s `done`/`revise`/`blocked` restriction
([test_loop.py:368](../skills/shiploop/scripts/shiploop_test_loop.py:368)) applies to the test-loop
stages, both INNER, where `revise` is legal; the outer verify stages take the rerun path. Confirm
at implementation.

**Not in A1:**

- **No limit raise.** `COMMAND_TIMEOUT_SECONDS = 600` and `STAGE_BUDGET_SECONDS = 1800` apply per
  *verification invocation*, not cumulatively per stage — each call resets its deadline
  ([:515](../skills/shiploop/scripts/shiploop_test_loop.py:515)). The 22.1-minute `regression`
  figure an earlier draft cited includes time the run sat dead before resumption
  (`LEARNINGS.md:428`), so it does not bear on a subprocess budget. A 6-hour allowance would also
  be inert under the harness's 3-hour host deadline
  ([run.py:899](../test/shiploop_e2e/run.py:899), `--timeout` default 10800). Raise only against
  measured command and batch durations plus documented headroom, kept inside the enclosing host
  deadline.
- **No second cap.** It would add another counter, reset policy, mixed-result policy and recovery
  route. A bounded subprocess already stops one command running forever, and a retry count does
  not prove a blocker. It also sits badly with S-10 (no iteration cap).
- **No `blocked_by: environment`.** Illegal: `BLOCKED_BY = ("user", "access", "external")`
  ([navigator.py:66](../skills/shiploop/scripts/shiploop_navigator.py:66)), with the explicit rule
  that anything the run can fix itself is not blocked. A catch-all category would weaken that.

**Note on an existing tension, not introduced here:** the 7-refusal gate refuses before rerunning
checks, so a subsequently repaired candidate still cannot pass that action; and `SKILL.md:531`
documents the end state deliberately — two revisions, then `blocked` with `blocked_by: user`.
A1 narrows what reaches that path; it does not resolve the S-10 question of whether the path
should exist. Reconcile explicitly or leave it recorded.

### A2 — Correct per-stage attribution and its retention

Not a new reader. `metrics.stage_results()`
([metrics.py:121](../test/shiploop_e2e/metrics.py:121)) already derives per-stage boundaries and
`per_stage()` ([metrics.py:425](../test/shiploop_e2e/metrics.py:425)) already buckets host turns between
them. Six corrections:

1. **Join authoritative history to timestamps by action ID.** Use `history`'s own ordering, not
   timestamp sorting or a regex over result files. Today `stage_results()` sorts by `st_mtime` and
   regexes out `"stage"` while discarding the `outcome` in the same file.
2. **Treat `timeline.json` as advisory.** A missing timeline is recreated and missing historical
   stamps take the current time ([navigator.py:3765](../skills/shiploop/scripts/shiploop_navigator.py:3765)),
   which is acceptable display recovery but can fabricate historical durations. Emit *unavailable*
   attribution, never a confident zero.
3. **Preserve unfinished work.** `per_stage()` emits windows only through accepted actions, so
   work after the last acceptance disappears — systematically excluding the stage where an active
   run stopped, which is the attrition under study. Add an explicit incomplete current-stage
   window or an unattributed remainder.
4. **Record *and compare* host, model and effort.** SPEC is explicit: "a baseline compares only
   with rows from the same host, model and effort"
   ([SPEC.md:316](../test/shiploop_e2e/SPEC.md:316)). Today `baselines.jsonl` records no `host` at
   all, and `previous_row()` ([run.py:946](../test/shiploop_e2e/run.py:946)) matches only case and
   source. **This is an existing SPEC violation**, and adding a `host` field without fixing the
   comparison does not fix it.
5. **Drop `cost_share_usd`.** It was total cost redistributed by turn count
   (`cost * len(window) / total_turns`, since removed), so a price change or expensive work
   elsewhere moves a stage's dollars with no change in that stage. Keep measured total cost and
   attributable turns/tokens; leave unavailable measurements null. Cross-host availability differs
   — the Codex adapter reports completed-item counts at session end rather than per-call usage, so
   zero stage turns must never be exported as measured.
6. **Implement the consumer.** Baseline comparison currently prints whole-run differences and
   suite success follows run verdicts; a `stages` field alone creates no regression detection.
   Extend the existing comparison output first, without a new threshold gate until it is
   calibrated.

**Retention.** An earlier draft said to let the scratch directories expire *and* keep outcome and
duration derivable from the engine's records — a contradiction, since `state.md` and
`timeline.json` live in those directories. Either retain the compact aggregate (per-stage outcome,
duration, completion funnel) or explicitly abandon those questions. "Only keep what the harness
alone knows" is the wrong rule for an archival summary. Exporting a derived aggregate is not a
second writable workflow state.

**Deduplication, resolved.** The four existing views are not redundant: `status.md`, the report
HTML and `progress.html` describe one run for its owner; the harness combines engine events with
host usage across runs. Consolidating them would be false deduplication, and engine display code
should not acquire host billing knowledge. Keep cross-run measurement in `test/shiploop_e2e`, with
**one** attribution implementation in `metrics.py` and the existing comparison path in `run.py`.

### A3 — Harness-side termination record

The question "why did those two runs stop?" is real. An engine-side event ledger cannot answer it:
`shiploop_protocol.main()` observes one CLI failure and returns an error. It cannot observe a
later host timeout, exhausted credits, a parent-task kill, or a decision not to resume. The
harness already owns process termination and resumption: it launches and reaps the host
([run.py:318](../test/shiploop_e2e/run.py:318), returning `status` `exited`/`failed` and the
`returncode` at [:384](../test/shiploop_e2e/run.py:384)), enforces the run deadline
([:1173](../test/shiploop_e2e/run.py:1173)), and already collects `shiploop_failures`
([metrics.py:227](../test/shiploop_e2e/metrics.py:227)).

Have the existing harness result and export preserve: observed process status, session stop
reason, final engine status and stage, and why the driver stopped resuming. **Retain `unknown`**
when the observer itself disappeared, and never infer that the last refusal caused termination.
Inspect and improve that existing path rather than adding a parallel one.

**The engine ledger is declined.** Beyond answering the wrong question, promoting
`shiploop_chain_ledger` is not mere reuse: its append performs its own publication and recovery
under an external lock, while `save()` uses the store transaction
([store.py:438](../skills/shiploop/scripts/shiploop_store.py:438),
[navigator.py:3793](../skills/shiploop/scripts/shiploop_navigator.py:3793)) — combining them
requires crash-consistency and ordering decisions. Logging accepted state would duplicate
`history` (S-1/S-12), and fail-open refusal logging cannot promise complete evidence anyway.

### A4 — Withdrawn

A fourth item on planning cost was drafted and withdrawn. Its premise ("977 of ~1400 minutes sit
in planning") is confounded (§4.3), and the repo already contains the diagnosis: review passes are
~16% of elapsed time with first-pass work dominating, and the blocked run's cause is a recorded
Backchain contract failure (`LEARNINGS.md:552`, `:583`).

What remains is an experiment, not a change, and it is narrower than ablation:

1. Correct attribution and separate active execution from interruption gaps (A2).
2. Compare the same case, host, model, effort and launch conditions — one matched `battleship` run
   on a second host.
3. Inspect which planning outputs or reads repeat without changing a decision.
4. Test one simplification, retaining the same quality evaluation.

Contrary evidence to respect: later Improve passes found real issues. A blanket "read less" or
"remove review" change would contradict the recorded learnings. The concrete S-4/S-5 mechanical-work
(glue) gap deserves priority over speculative instrumentation.

### On the ablation question

34 stages at ~$30/run with branching that rarely fires looks like gates that seldom bind. But
branch rate is the wrong value criterion — `spec` never branches and still produces the spec — and
low branching does not imply low corrective work, since work inside Improve and the test loops is
outside that denominator. Deciding requires removing a stage and comparing product quality through
the rubric, against an 11-run baseline, by the repo's eval-priority rule (material quality first,
then tokens).

## 6. Open questions

- **Markdown versus JSON for state.** Anthropic's long-running-agent harness stores its feature
  list as JSON *specifically because models edit Markdown too freely*. ShipLoop is
  Markdown-authoritative by design. Nothing in this plan answers that. It deserves an experiment —
  does a model ever edit `state.md`'s fence when it should not? — not a change.
- **Which hosts can attach measured cost per action.** Two of 12 baseline rows report `$0`.
- Can the three `active` runs be mapped to documented causes? The existing learnings give causes
  for particular runs, not a verified mapping to that subset, and the 10 `/private/tmp` outputs
  have lost their top-level result files.

## 7. What landed

Implemented 2026-10-04. No behaviour changes for a run whose commands pass.

**A1 — `skills/shiploop/scripts/shiploop_test_loop.py`** (+ `SKILL.md`,
`references/navigator.md`, change note `changes/shiploop/test-run-could-not-run.md`)

- `UNAVAILABLE = ("timeout", "skipped", "error")`, and `_disposition()` returning
  `passed` / `failed` / `could-not-run`. The record keeps `passed: bool` and gains
  `disposition`.
- The `error` bug is fixed: `if status in UNAVAILABLE` now keeps the runner's own status before
  the `code is None` branch can rewrite a spawn failure as `failed`.
- `refused_runs()` skips `could-not-run` attempts, so they refuse their stage without spending
  one of the 7. A record predating the field still counts as a failure, which is what it meant.
- `_remedy()` / `_remedy_sentence()` read `stage_spec.STAGE_SPEC[stage].outcomes`, so the gate,
  the `attempts` line and `rerun_lines()` name `revise` at the 6 INNER verify stages and `replan`
  with corrective `work_items` at the outer `system-test` and `release-verify`.
- `_explain()` reports a timeout and a spawn failure as reaching no verdict, not as product
  failures.
- Because the gate cannot fire on `could-not-run` attempts, the refusal names the routes out: a
  hang in the item's own code, test or fixture is run-fixable and is not a blocker; a wrong
  recorded command or budget takes the stage's remedy; `blocked` is only for what the user, an
  access grant or an outside dependency must supply. Without this a command that always hangs
  would have no legitimate exit (found by §8's evaluation, not by the review).

**A2 — `test/shiploop_e2e/metrics.py`, `run.py`, `progress.py`**

- New `engine_state()`, `acceptance_stamps()`, `_epoch()`. `stage_results()` now joins `state.md`
  history to `timeline.json` by action id and carries `outcome`; result-file mtimes are gone.
- `per_stage()` emits `timing: "unavailable"` instead of a fabricated zero, appends an
  `incomplete` row for the stage an unfinished run never accepted (via `pending_stage()`,
  which resolves an active inner loop to the item's own stage), and no longer apportions cost.
  A measured stage immediately after an unstamped one is also reported unavailable, because its
  window covers both actions; attribution resumes at the next known boundary. `stage_diff_lines()`
  states how many stages a partial comparison covers rather than presenting a subset as the whole.
- `baseline_row()` records `host`, `model`, `effort`, `termination` and, through `baseline_stages()`,
  the stage fields a comparison actually reads (`stage`, `outcome`, `seconds`, `turns`, plus the
  `timing`/`incomplete` markers); the full rows stay in the run's disposable `metrics.json`.
  `previous_row()` requires all three identity fields to match, as SPEC requires;
  `stage_diff_lines()` locates a regression per stage and reports "not comparable" rather than
  treating missing timing as zero.
- `verifications()` adds `could_not_run`, so the harness can observe A1's new disposition.

**A3 — `test/shiploop_e2e/run.py`**

- The resume loop records why it stopped (`host is not resumable`, `ShipLoop run is <status>`,
  `no host session id to resume`, `run deadline spent`, `resume budget spent (N)`).
- `termination_facts()` records process status and return code, each session's own stop reason,
  the engine's status, and the stage it never accepted — keeping `unknown` rather than guessing,
  and never treating a refusal as a cause. It is in `result.json`, the baseline row, and a
  `stopped` line in the printed report.

`_remedy()` tolerates a label that is not a graph stage (the navigator's `end-of-work review`
gate), returning no remedy rather than raising.

**Tests** (+23). `test/shiploop-test-loop.test.py::UnavailableExecutionTests` (7): spawn error,
repeated unavailable attempts never reaching the cap, the routes out of an always-unavailable
command, a real failure beside a timeout staying a failure, the per-stage remedy across all 8
`VERIFY_STAGES`, the non-graph label having no remedy, and the rerun packet's wording.
`test/shiploop-e2e.test.py` adds `StageAttributionTest` (8), `BaselineComparabilityTest` (5) and
`TerminationRecordTest` (3). Suites: test-loop **31 OK** (was 24), harness **100 OK** (was 84),
and the caller set derived by grep — `shiploop-improve-changes` (4) and `shiploop-confirmation`
(5), the latter never run until the caller search surfaced it. `run-all.sh --group shiploop`
is green end to end: **63 suites OK, 0 failed, exit 0**. The run before the pseudo-stage fix was
63 OK / 1 failed, and that one failure was this change's own regression.

The next run's operator needs to know the baseline and metric contract changed, so
`test/shiploop_e2e/LEARNINGS.md` carries a short entry pointing here — including that the 12
existing baseline rows name no host/model/effort and so no longer serve as baselines.

Checked against the recorded runs: the long Luna run reports `engine active with carry-forward
never accepted`, and its 8 verify records classify as 8 passed / 0 could-not-run, consistent with
§4.4. That run is still in flight, so its figures here are a snapshot, not a final result.

## 8. Change admission record (A1)

`SPEC.md:135` requires an adversarial evaluation with a disposition per consequence, an anchor, a
non-regression statement and evidence. A2 and A3 change only the harness's own observation, so
this record covers A1, the one behaviour change.

**A3's anchor, corrected.** A3 was argued partly from "three runs sit active with no recorded
cause". Re-checking on 2026-10-04 found that **two** are abandoned with no cause; the third is a
live resume still in flight. A3 still holds — the engine cannot record a cause it is not running
to observe, and `LEARNINGS.md` documents credit exhaustion, harness timeouts and background-task
kills for particular runs — but on two runs, not three.

**Anchor.** S-9 ("a check that ran nothing is not a pass") and S-14 (unattended by default).
Motivating evidence: `shiploop_test_loop.py` recorded a spawn failure as `failed`, and counted
unavailable execution toward `MAX_REFUSED_RUNS`, whose exhaustion forces the stage's remedy and
then `blocked_by: user` — a stop in an unattended run. §4.4 measured zero occurrences in 11 runs
and explains why the corpus cannot reach it.

**Adversarial evaluation.**

| Consequence sought | Finding | Disposition |
|---|---|---|
| Weakens S-9 by accepting unrun tests | No: `passed` stays false and the stage still refuses; only the *attribution* changes | **mitigated** by keeping the refusal, tested in `test_unavailable_attempts_never_reach_the_refused_run_cap` |
| Recovery dead end: a command that always hangs can never pass, its own hang is run-fixable so `blocked` is illegal, and the cap that would force the remedy never advances | **Real.** Found by this evaluation, not by the earlier review | **mitigated**: the refusal now names both routes out — fix it here, or report the stage's remedy if the recorded command or budget is wrong. Tested in `test_an_always_unavailable_command_is_given_routes_out_not_a_dead_end` |
| Gamed: a metric improves while behaviour worsens | A run could accumulate unavailable attempts invisibly | **mitigated**: `verifications()` reports `could_not_run`, surfaced in the run summary and the live progress line |
| Waits on a person in an unattended run (S-14) | The opposite: the previous path ended at `blocked_by: user` after two revisions. A1 removes that for environment problems | **accepted** as an improvement to S-14 |
| Breaks saved runs or existing callers | A verify record written before `disposition` existed still counts as a failure, which is what it meant | **mitigated**, documented in `refused_runs()` |
| Breaks an existing caller — **answered wrongly the first time** | `_remedy()` looked a stage's outcomes up by subscript, reasoning that "the stage always comes from the navigator, so it is valid". It does not: the navigator also calls `verify` with the pseudo-stage label `end-of-work review` ([navigator.py:2242](../skills/shiploop/scripts/shiploop_navigator.py:2242)), which is not in `STAGE_SPEC`, so the gate raised `KeyError` | **mitigated**: `_remedy()` returns no remedy for a label that is not a graph stage, with a regression test. Found only by `run-all.sh --group shiploop`, not by the change's own footprint suites |
| Mixed results: a timeout erases a real failure | Would hide a product defect | **mitigated**: `_disposition` returns `failed` whenever any command failed on its own merits; tested |
| Enlarges packet text | `rerun_lines` grows one clause; the refusal text replaces a line of similar length | **accepted**; the repo prefers raising a bound to trimming guidance |
| Breaks another host, style or language | The classification is status-based and platform-neutral | **accepted**, no scenario found |
| Costs more than it saves | Saves up to 21 refused runs' worth of budget on an environment problem | **accepted** |

**Non-regression.** `MAX_REFUSED_RUNS` still ends an action on 7 *product* failures, and the
remedy it names is unchanged at the six INNER verify stages. `check_terminal`'s outcome
restriction, the lint gate, the Until Loop contract and `PASSING` are untouched. S-10 is not
weakened: no cap is added, and an unbounded sequence of unavailable attempts ends on its
condition, a true blocker or a user stop, exactly as the clause says.

**Evidence.** `test/shiploop-test-loop.test.py::UnavailableExecutionTests` (6) and the suites in
§7. **Not yet confirmed live:** no E2E run has exercised these paths, because no case has a slow
or breakable suite (§4.4). That remains the one open piece of this item's evidence.

## 9. Repository conventions for landing this

A1's own evaluation and evidence are in §8; A2 and A3 change only the harness's observation of a
run, so they carry no behaviour anchor. Their scenarios — an unavailable or partial timeline,
incomplete-stage accounting, and an unmatched baseline identity that must not compare — are
covered by the tests named in §7.

- A1 ships with `changes/shiploop/test-run-could-not-run.md` (`bump: minor`), per
  [AGENTS.md:37](../AGENTS.md:37). A2 and A3 touch only `test/`, which needs no note.
- `plugins/`, the catalogs, the README inventory and every `version:` field remain release-script
  output; none was touched.
- Land by merge or rebase, never squash.

## Corrections to this document

- **`events.jsonl` design** — withdrawn. `store.transaction()` takes whole-file text and cannot
  append.
- **"Per-edge outcome statistics" as the headline** — withdrawn. `history` already carries the
  outcome and it rarely varies.
- **OTel GenAI export** — withdrawn. The conventions are marked Development, and a passive engine
  that makes no model calls would emit spans with nothing inside them.
- **"98.5% first-pass"** — withdrawn. The denominator is accepted actions; refusals are excluded.
  See §4.1.
- **"Infrastructure failure is a live defect"** — demoted. Zero timeouts, skipped or errored
  commands in 84 verify records, max 1 refusal against a cap of 7. It is a latent cliff, invisible
  to this corpus by construction (A1).
- **How the footprint was derived** — the error was mine, not the rule's. The suites I picked
  (test-loop, lint, navigator-contract, stage-spec, revise, reference-routing, harness — 282
  tests, all green) missed a regression this change introduced: `_remedy()` raised `KeyError` on
  the navigator's `end-of-work review` pseudo-stage. The footprint of a change to a shared helper
  is **its callers**, found by searching — not the stages the change was written for. One
  `git grep "test_loop.verify("` prints that call with its literal `"end-of-work review"`
  argument. I reasoned the case away instead of searching, which is the step that failed. Running
  the whole group is not the lesson; deriving the caller set is.
- **"Three runs sit active with no recorded cause"** — withdrawn. Re-checked 2026-10-04 09:39:
  two are abandoned with no cause; the third is a live `--resume-run` still in flight, which is
  not attrition. A3's anchor is corrected in §8, and §4.3's figures for that run are a snapshot
  of a run still going. A measurement of a live tree is perishable.
- **"Ablate the planning chain"** — withdrawn. 95% of that time is two Luna `battleship` runs;
  host and case are confounded (§4.3).
- **"Preserve the run directories"** — withdrawn as framed (it contradicts disposable-probe
  design), but the retention question it raised is real and is answered in A2.
- **Tree-hash binding per test run** — withdrawn. No consumer, since the engine reruns its checks.
- **A dry-run converter from recorded runs** — withdrawn. At this branching rate the 11 runs
  collapse to roughly one happy path.
- **Engine event ledger (C6/R3)** — replaced by A3, which can actually observe host termination.
- **"Lint never gates"** — false. The gate "refuses the submission once after applying a fix and
  while a new finding on a line the item changed has no waiver"
  ([lint.py:4](../skills/shiploop/scripts/shiploop_lint.py:4)). The accurate claim is that ShipLoop
  never gates on lint's *exit code*. The uniformity argument built on it is withdrawn: integer CLI
  exit codes and a persisted acceptance boolean are different interfaces, and the mechanism worth
  sharing — `lint.run_argv`, including process-group timeout cleanup — is **already** shared by the
  test loop.
- **"600 → 3600 is 10×"** — it is 6×. The stage figure is 12×. Both raises are withdrawn (A1).
- **Blast radius "one function, one assertion, one sentence"** — understated; see A1's site list.
- **A subagent audit reported the E2E source directories were gone.** Verified otherwise: all 12
  exist, which is how §4 was measured. Their top-level result files are partly missing.
- **`references/navigator.md`'s rerun-stage list** ("`test-green`, `test-refine`, `regression`,
  `static-checks`, `integration-verify`") is short of the code, which also includes `verify`,
  `system-test` and `release-verify`. Worth reconciling.
- **Astra's line references drift** by a few lines against this checkout; every substantive claim
  cited above was re-verified here, and line numbers are this tree's.

## Provenance

Measurements: 11 protocol-4 run directories under `~/e2e-runs/20261003/` and two scratchpad trees,
read via `state.md` + `timeline.json` + `run/tests/*-verify*.md`. Review: Astra (`gpt-6-astra`,
xhigh, read-only) against checkout `3d2ab1da` plus the working tree, 2026-10-04 — it changed or
removed R1, R2 and R3 and found the `error`-persisted-as-`failed` bug.
