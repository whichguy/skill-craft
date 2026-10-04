# ShipLoop graph engineering: comparison, measurements, and plan

**Date:** 2026-10-04. **Status:** A1–A3 **implemented**, then **adversarially reviewed** the same
day; A4 withdrawn. See [§5 Plan](#5-plan) for what each item does,
[§7 What landed](#7-what-landed) for the files and tests,
[§8](#8-change-admission-records-a1-a2-a3) for the change-admission records and
[§10](#10-review-of-the-landed-changes-and-what-is-not-fixed) for the review and the limits it
left. Evidence:
[docs/experiments/shiploop-a1a3-review-20261004/](experiments/shiploop-a1a3-review-20261004/README.md).

Three sources, with different weight:

- **ShipLoop facts** — read from the source in this checkout. Code is cited by symbol or section
  name, never by line number: the first version cited lines that were wrong in the merged tree
  (see the corrections).
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

*[Superseded 2026-10-04 after the merge: that Luna run ended `blocked` at `system-test` after 39
accepted actions and 19.3 h (`test/shiploop_e2e/LEARNINGS.md`, "Luna max battleship on 1.16.1,
final"). "In flight" below is the snapshot taken then. Likewise the "12 baseline" figures below
are not a row count: `baselines.jsonl` held 13 rows at A2's commit and holds 15 after the 1.19.0
verification rows.]*

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
(`_record_acceptance` in
[shiploop_navigator.py](../skills/shiploop/scripts/shiploop_navigator.py)), so no new recording is
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

The repo already diagnoses these runs. `test/shiploop_e2e/LEARNINGS.md`, "Batch 1003 — Luna max
battleship final result": *"10 repeat passes cost about 46 minutes of 291 (16%), and the stage's
first-pass work, not repeat passes, is the"* cost. Its "Batch 1003 — Luna max battleship, plan
stage: the Backchain loop cannot persist its first callback (F3)" entry records the blocked run's
cause as a hand-built Backchain loop contract that cannot persist its first callback.
**Review-pass count is ~16%, not the driver.**

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

1. **`error` is never persisted.** In `verify` (before A1), `OSError` set a local
   `status = "error"` with `code = None`, then the following `elif code is None` branch wrote
   `"failed"`. A spawn failure was recorded as a test failure and the `"error"` status never
   reached a record. **Fix this first**; any reclassification that matches on `"error"` would
   otherwise match nothing.
2. **Unavailable execution counts toward the failure cap.** `timeout` and `skipped` (the
   invocation budget ran out) collapsed into `"passed": all(...)` in `verify` (before A1), and
   `refused_runs()` counted any falsy `passed` toward `MAX_REFUSED_RUNS = 7`. Exclude attempts whose only non-passing results are unavailable
   execution. **Keep `passed: bool`** — it answers the acceptance question, and per-command
   statuses already explain why. **Define mixed attempts explicitly:** a real failing check plus a
   timeout stays a failure.
3. **Timeout is not a diagnosis.** A timeout can mean a product deadlock, a broken test, a slow
   valid suite, or an external dependency. It establishes incomplete verification, not who must
   repair it. Required verification must stay *unavailable* rather than pass (S-9), and must not
   assert a blocker.
4. **The recovery remedy is invalid at 2 of the 8 verify stages.** `revise` is attached only to
   stages between `test-spec` and `integration-verify` (`_finish` in
   [shiploop_stage_spec.py](../skills/shiploop/scripts/shiploop_stage_spec.py)); outer stages get
   `replan`. The gate text in `verify` still said "Report outcome revise" (before A1), which the
   navigator rejects at the outer `system-test` and `release-verify`. Generate guidance from the
   stage contract through **one helper**, and note that outer `replan` requires corrective
   `work_items` (`_canonical_result` in
   [shiploop_navigator.py](../skills/shiploop/scripts/shiploop_navigator.py)) — substituting the
   outcome word is not enough.

Unconditional `revise` guidance appeared at more sites than one before A1: two places in
`render_lines`, `check_terminal`, the gate text in `verify`, and SKILL.md ("Test loop" and "Tests
pass or the step stops"). Fix them together.

**Scope boundaries.** `check_terminal`'s `done`/`revise`/`blocked` restriction applies to the
test-loop stages, both INNER, where `revise` is legal; the outer verify stages take the rerun
path. *Confirm at implementation* — **this was not done** when A1 landed, and it is the check
that would have found the dead end §8.1 records: `check_terminal` lets `revise` through only after
`refused_runs` reaches the cap.

**Not in A1:**

- **No limit raise.** `COMMAND_TIMEOUT_SECONDS = 600` and `STAGE_BUDGET_SECONDS = 1800` apply per
  *verification invocation*, not cumulatively per stage — each call resets its deadline
  (`verify`'s `budget`). The 22.1-minute `regression` figure an earlier draft cited includes time
  the run sat dead before resumption (`LEARNINGS.md`, "hello + seat-reservations on Sonnet 5.5"),
  so it does not bear on a subprocess budget. A 6-hour allowance would also be inert under the
  harness's 3-hour host deadline (the `--timeout` default of 10800 in `parser()` in
  [run.py](../test/shiploop_e2e/run.py)). Raise only against
  measured command and batch durations plus documented headroom, kept inside the enclosing host
  deadline.
- **No second cap.** It would add another counter, reset policy, mixed-result policy and recovery
  route. A bounded subprocess already stops one command running forever, and a retry count does
  not prove a blocker. It also sits badly with S-10 (no iteration cap).
- **No `blocked_by: environment`.** Illegal: `BLOCKED_BY = ("user", "access", "external")`
  (`BLOCKED_BY` in the navigator), with the explicit rule
  that anything the run can fix itself is not blocked. A catch-all category would weaken that.

**Note on an existing tension, not introduced here:** the 7-refusal gate refuses before rerunning
checks, so a subsequently repaired candidate still cannot pass that action; and SKILL.md ("Revise:
back to the step plan") documents the end state deliberately — two revisions, then `blocked` with
`blocked_by: user`.
A1 narrows what reaches that path; it does not resolve the S-10 question of whether the path
should exist. Reconcile explicitly or leave it recorded.

### A2 — Correct per-stage attribution and its retention

Not a new reader. `metrics.stage_results()` already derived per-stage boundaries and
`metrics.per_stage()` already bucketed host turns between them. Six corrections:

1. **Join authoritative history to timestamps by action ID.** Use `history`'s own ordering, not
   timestamp sorting or a regex over result files. Today `stage_results()` sorts by `st_mtime` and
   regexes out `"stage"` while discarding the `outcome` in the same file.
2. **Treat `timeline.json` as advisory.** A missing timeline is recreated and missing historical
   stamps take the current time (`load_timeline` and `_updated_timeline` in the
   navigator), which is acceptable display recovery but can fabricate historical durations. Emit *unavailable*
   attribution, never a confident zero.
3. **Preserve unfinished work.** `per_stage()` emits windows only through accepted actions, so
   work after the last acceptance disappears — systematically excluding the stage where an active
   run stopped, which is the attrition under study. Add an explicit incomplete current-stage
   window or an unattributed remainder.
4. **Record *and compare* host, model and effort.** SPEC is explicit: "a baseline compares only
   with rows from the same host, model and effort" ("Rules for the harness itself", *The driver is
   a parameter, not a code path*). Before A2, `baselines.jsonl` recorded no `host` at all, and
   `previous_row()` in [run.py](../test/shiploop_e2e/run.py) matched only case and source. **This is an existing SPEC violation**, and adding a `host` field without fixing the
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
should not acquire host billing knowledge. Keep cross-run measurement in `test/shiploop_e2e`, with the harness's attribution in
`metrics.py` and the existing comparison path in `run.py`. *[Corrected 2026-10-04: this said
"**one** attribution implementation". After the merge there are two, with different rules: the
Run Review exporter computes its own accept-to-accept minutes. §8.2 states both and what each is
used for.]*

### A3 — Harness-side termination record

The question "why did those two runs stop?" is real. An engine-side event ledger cannot answer it:
`shiploop_protocol.main()` observes one CLI failure and returns an error. It cannot observe a
later host timeout, exhausted credits, a parent-task kill, or a decision not to resume. The
harness already owns process termination and resumption: it launches and reaps the host
(`launch` in [run.py](../test/shiploop_e2e/run.py), which returns `status`
`exited`/`failed`/`timeout` and the `returncode`), enforces the run deadline (the `--timeout`
handling in `launch` and the `run deadline spent` check in `main`'s resume loop), and already
collects `shiploop_failures` (`collect` in [metrics.py](../test/shiploop_e2e/metrics.py)).

Have the existing harness result and export preserve: observed process status, session stop
reason, final engine status and stage, and why the driver stopped resuming. **Retain `unknown`**
when the observer itself disappeared, and never infer that the last refusal caused termination.
Inspect and improve that existing path rather than adding a parallel one.

**The engine ledger is declined.** Beyond answering the wrong question, promoting
`shiploop_chain_ledger` is not mere reuse: its append performs its own publication and recovery
under an external lock, while `save()` uses the store transaction
(`transaction` in [shiploop_store.py](../skills/shiploop/scripts/shiploop_store.py), called from
`save` in the navigator) — combining them
requires crash-consistency and ordering decisions. Logging accepted state would duplicate
`history` (S-1/S-12), and fail-open refusal logging cannot promise complete evidence anyway.

### A4 — Withdrawn

A fourth item on planning cost was drafted and withdrawn. Its premise ("977 of ~1400 minutes sit
in planning") is confounded (§4.3), and the repo already contains the diagnosis: review passes are
~16% of elapsed time with first-pass work dominating, and the blocked run's cause is a recorded
Backchain contract failure (the two "Batch 1003 — Luna max battleship" entries in `LEARNINGS.md`,
cited in §4.3).

What remains is an experiment, not a change, and it is narrower than ablation:

1. Correct attribution (A2) and separate active execution from interruption gaps. *[Corrected
   2026-10-04: A2 does not do the second. Stage seconds are wall clock between two acceptance
   stamps, so a `--resume-run` gap, a credit stop or a sleep inside a stage is counted as that
   stage's time; see §10.]*
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
`test/shiploop_e2e/LEARNINGS.md` carries a short entry pointing here — including that the
existing baseline rows name no host/model/effort and so no longer serve as baselines. *[Corrected
2026-10-04: that entry and this paragraph said "12" rows; `baselines.jsonl` held 13 at A2's
commit and holds 15 now, none naming host, model or effort, so the two newest Claude hello rows
are not baselines either.]*

Checked against the recorded runs: the long Luna run reports `engine active with carry-forward
never accepted`, and its 8 verify records classify as 8 passed / 0 could-not-run, consistent with
§4.4. That run was still in flight, so its figures here are a snapshot, not a final result.
*[Superseded 2026-10-04: that run ended `blocked` at `system-test`; its unaccepted stage is
`system-test`, not `carry-forward` (§4, first note).]*

## 8. Change admission records (A1, A2, A3)

SPEC ("Change admission") requires, for **every** change to ShipLoop, to its skills and cards,
**or to this harness**, an adversarial evaluation with a disposition per consequence, an anchor, a
non-regression statement and evidence. It has no exemption for a change that only observes. The
first version of this section covered A1 and said A2 and A3 "change only the harness's own
observation" and "carry no behaviour anchor". Both halves were wrong: A2 and A3 change what a run
records, prints and is compared with, and both have anchors.

§8.2 and §8.3 were written afterwards, from the adversarial review of the landed changes (§10).
They are **retrospective** evaluations: the consequences a hostile reviewer would have raised
before the change, with the review's reproductions as evidence. §8.1 keeps the original A1
record and corrects it where the review showed it wrong.

Dispositions use the SPEC's words. **Mitigated by the review follow-up** names a fix made on one
of two implementer branches (skills; harness) that were not merged when this was written: confirm
each against the merged tests before relying on it. **Accepted** rows are the limits in §10.4.

### 8.1 A1 — test-run classification

**Anchor.** S-9 ("a check that ran nothing is not a pass") and S-14 (unattended by default).
Motivating evidence: `shiploop_test_loop.py` recorded a spawn failure as `failed`, and counted
unavailable execution toward `MAX_REFUSED_RUNS`, whose exhaustion forces the stage's remedy and
then `blocked_by: user` — a stop in an unattended run. §4.4 measured zero occurrences in 11 runs
and explains why the corpus cannot reach it.

**Adversarial evaluation.**

| Consequence sought | Finding | Disposition |
|---|---|---|
| Weakens S-9 by accepting unrun tests | No: `passed` stays false and the stage still refuses; only the *attribution* changes | **mitigated** by keeping the refusal, tested in `test_unavailable_attempts_never_reach_the_refused_run_cap` |
| Recovery dead end: a command that always hangs can never pass, its own hang is run-fixable so `blocked` is illegal, and the cap that would force the remedy never advances | **Real, and the first fix did not close it.** The evaluation found the dead end and made the refusal *name* the routes out (fix it here, or report the stage's remedy). The review (cluster A) showed the named `revise` is refused at `test-green`, `regression` and `static-checks`: `check_terminal` skips the packet check only when `refused_runs` has reached the cap, which could-not-run attempts never advance, and the quality loop's `check_terminal` has no bypass at all, so every outcome except the unreachable `done` is refused there. At `test-green` and `regression` the only accepted exit was `blocked` (illegal for a hang the run can fix, so the model had to misreport it) and the keepalive release below; at `static-checks` there was none | **not mitigated as first recorded.** Found by the review, not by this evaluation. **Mitigated by the review follow-up**, which makes the named route accepted at these stages; the earlier test only asserted that the refusal text contains the word `revise`; a test has to submit the named outcome through the navigator |
| Keepalive interplay (nobody searched for dependents of `MAX_REFUSED_RUNS`) | `STUCK_CONTINUATIONS` is `2 * MAX_REFUSED_RUNS` because the script was assumed to stop accepting test runs "well before" keepalive gives up. With could-not-run attempts uncounted that is false: the 14-continuation release is the only terminator, and its notice recommends `blocked` or `revise`, the refused outcomes. An unattended run ends *active* at that stage with no blocked or awaiting record (S-14). This is a second cap on could-not-run attempts, and the original non-regression text said no cap was added | **mitigated by the review follow-up** (comment and notice corrected to match the routes that are accepted). The caller search was on `test_loop.verify(`, so it missed this dependent of `MAX_REFUSED_RUNS`; the lesson is in the corrections |
| A slow but passing suite | Five commands that each pass in 500 s against the 1800 s invocation budget: the same tail is `skipped` on every attempt, so the attempt is `could-not-run` twelve times running and no counter advances. The budget is a script constant, so "its budget is itself wrong" has no action for the model | **mitigated by the review follow-up** |
| Gamed: a metric improves while behaviour worsens | A run could accumulate unavailable attempts invisibly | **mitigated**: `verifications()` reports `could_not_run`, surfaced in the run summary and the live progress line |
| Waits on a person in an unattended run (S-14) | The previous path ended at `blocked_by: user` after two revisions; A1 removes that for environment problems. For an always-unavailable command the review found the unattended path ends active (the dead-end and keepalive rows) | **accepted** as an improvement to S-14, once the two rows above are fixed |
| Breaks saved runs or existing callers | A verify record written before `disposition` existed still counts as a failure, which is what it meant. No test pinned it | **mitigated**, documented in `refused_runs()`; the review follow-up adds the missing test |
| Breaks an existing caller — **answered wrongly the first time** | `_remedy()` looked a stage's outcomes up by subscript, reasoning that "the stage always comes from the navigator, so it is valid". It does not: the navigator also calls `verify` with the pseudo-stage label `end-of-work review` (`_improve_change_gate` in the navigator), which is not in `STAGE_SPEC`, so the gate raised `KeyError` | **mitigated**: `_remedy()` returns no remedy for a label that is not a graph stage, with a regression test. Found only by `run-all.sh --group shiploop`, not by the change's own footprint suites. The review added that this label then has *no* route out after 7 product failures (the text names only `blocked`): **mitigated by the review follow-up** |
| Mixed results: a timeout erases a real failure | Would hide a product defect | **mitigated**: `_disposition` returns `failed` whenever any command failed on its own merits; tested |
| A timeout whose partial output already shows failing tests | `verify` records `timeout` without judging the partial output, so a runner that prints `FAILED (failures=3)` and then hangs on exit is `could-not-run` and spends none of the 7 | **accepted**: a timeout is not a diagnosis, and judging a half-written report reintroduces guessing (§10.4) |
| A command that cannot start | The runner is `/bin/sh -c`, so a missing binary exits 126 or 127 through `judge` and counts as a product failure. `cannot start` (status `error`) covers only a failed spawn or a missing repository directory | **accepted**: stated here and in §10.4 so the change note's "cannot start" is read as "could not be spawned" |
| Text accurate only for the stages it was written for | The outer rerun packet says the commands came from the step plan while naming `replan`; the `test-red` text contradicts itself; the skipped message names the wrong budget | **mitigated by the review follow-up** |
| Enlarges packet text | `rerun_lines` grows one clause; the refusal text replaces a line of similar length | **accepted**; the repo prefers raising a bound to trimming guidance |
| Breaks another host, style or language | The classification is status-based and platform-neutral | **accepted**, no scenario found |
| Costs more than it saves | Saves up to 21 refused runs' worth of budget on an environment problem | **accepted** |

**Non-regression.** `MAX_REFUSED_RUNS` still ends an action on 7 *product* failures, and the
remedy it names is unchanged at the six INNER verify stages. The lint gate, the Until Loop
contract and `PASSING` are untouched. `check_terminal`'s outcome restriction is also untouched —
and that is the defect: its `revise` bypass is keyed to `refused_runs`, which A1 stopped
advancing for could-not-run attempts, and the statement here that the restriction was not
affected did not ask whether anything *depended* on it. S-10 is not weakened by a new counter, but
the keepalive's stuck release (above) is a bound on continuation without progress that this
section's first version did not count.

**Evidence.** `test/shiploop-test-loop.test.py::UnavailableExecutionTests` (7 tests) and the
suites in §7. **Not yet confirmed live:** no E2E run has exercised these paths, because no case
has a slow or breakable suite (§4.4). That remains the open piece of this item's evidence.

### 8.2 A2 — per-stage attribution and baseline comparability (retrospective)

**Anchor.** SPEC "Rules for the harness itself": the harness measures the engine "through
ShipLoop's own records", and *the driver is a parameter*, so a baseline "compares only with rows
from the same host, model and effort". Also S-12 (one implementation of each mechanism) for the
attribution, and S-9 read for measurements: a figure that was not measured is unavailable, never
zero. Motivating evidence: the long Luna run's stage minutes, attributed from result-file mtimes,
were wrong (step-plan read 28.0 min in `metrics.json` against 163.9 min from the event stream;
plan 39.2 min against 196 min from accept stamps — `LEARNINGS.md`, "I2b prompt trim, built
locally" and the superseded mark on the plan stage), and `baselines.jsonl` carried no `host` at
all although SPEC forbids comparing across hosts (13 rows at A2's commit).

**Adversarial evaluation.**

| Consequence sought | Finding | Disposition |
|---|---|---|
| Fails silently: a host that reports no per-turn usage | Codex emits one `end` event with a turn count and no usage or assistant events, so every stage row gets `turns: 0` and `output_tokens: 0` as if measured. `stage_diff_lines` (which compares turns only) prints "no per-stage turn difference" for a plan stage that took 5× as long, and `summary_lines` ranks the "costliest stages" by turns, i.e. the first five. Reproduced on the recorded Luna run: 39 of 39 stage rows say 0 turns against 2,189 whole-run turns. §5's own A2 item 5 said this must never happen; every test stream was Grok-shaped | **mitigated by the review follow-up** |
| Fails silently: the `incomplete` row | It is built only from a newest *turn* event, so a host with no turn events never gets one, although tool calls and minutes followed the last acceptance. It is also absent when nothing was accepted, overstated after an unstamped last action, and shown for a stage the engine had accepted as `blocked` | **mitigated by the review follow-up** |
| Fails silently: Claude's per-call counters | `collect` reads Grok-shaped `tool_call` events only, so on the default host `tool_calls`, `model_glue`, `shiploop_failures`, cancelled calls and tmp writes are zero by construction and `output_tokens` is about 17× low. This pre-dates A2, but A2 commits the zeros into `result.json` stage rows | **mitigated by the review follow-up** (the integrator records whether the counters are now read or marked unmeasured) |
| Gamed or misleading comparison | `stage_diff_lines` ignores the `incomplete` marker the baseline commits, so an unfinished run is compared as a finished stage; a stage unmeasured on one side prints as "only now" or "only before"; coverage is stated for one side only | **mitigated by the review follow-up** |
| Breaks saved runs, callers, baselines | All 13 older rows (15 after the merge) lose their role as baselines: they carry no host, model or effort. That is what SPEC asks, and those rows mixed hosts. The review found the cost larger than recorded: the two newest Claude hello rows, committed by the 1.19.0 line, are in the same state, and a skipped comparison printed nothing | **accepted** for the old rows (SPEC). **Mitigated by the review follow-up** for the silence: the report says no comparable row exists |
| Publishes numbers that then mislead | The 1.19.0 hello per-stage figures in the journal were attributed from mtimes (carry-forward 4, 8, 18, 12 turns; spec 18, 24, 24, 36). Recomputed with A2's code on the same four runs: carry-forward 5, 8, 13, 12; spec 19, 30, 26, 40. Totals are unchanged | **mitigated here**: the journal marks both superseded (`LEARNINGS.md`) |
| Boundary precision | Engine stamps are whole seconds (`_utc_now`), so the turn that submits `shiploop complete` can land in the next stage | **accepted** (§10.4) |
| A recreated timeline | `_updated_timeline` recreates a lost `timeline.json` and stamps every historical action with the current time; the stamps are readable, so they pass as measured | **accepted** (§10.4) |
| Stamps that are not acceptance instants | A `--seed-at` run stamps its seeded stages before the host starts: the first seeded row gets negative seconds, the others measured zeros, and host start-up is billed to the first real stage | **mitigated by the review follow-up** |
| Time includes interruption gaps | Stage seconds are wall clock between two stamps, so a resume gap, credit stop or sleep is a stage's time. §5's A4 item 1 said A2 separates active execution from gaps; it does not | **accepted** (§10.4); the sentence in §5 is corrected |
| A second implementation (S-12) | The Run Review exporter computes its own accept-to-accept minutes (see below), contradicting the "one implementation" this document claimed | **accepted**, stated below; whether to unify is an owner decision |
| Stale documentation | README, the metrics docstring, the journal and this document still described mtime attribution, `cost_share_usd`, "same source" and the 12-row count | **mitigated here** for the README, journal and this document. The `metrics.py` module docstring, the `progress.py` comment, the `review.py` reviewer prompt and the `run.py` module docstring ("cost and time (per accepted stage)") are code: **mitigated by the review follow-up** |
| Costs more than it saves | Dropping `cost_share_usd` loses nothing: it was one total redistributed by turn count | **accepted** |

**Two attributions, and which is used for what.** `metrics.per_stage` (the harness) joins
`state.md` history to `timeline.json` by action id and buckets host turns between acceptances. It
feeds `metrics.json` `stages`, the baseline row, `progress.py` and `stage_diff_lines`, and reports
seconds and turns. The Run Review exporter (`build_run` in
[export.py](../skills/shiploop-e2e-audit/run-review/export.py)) computes accept-to-accept minutes
from the same two files for the review page and the committed `evidence/*.json`. Their rules
differ: the exporter sorts by stamp (history position only breaks ties), starts its first stage
at the engine's `started` stamp, and raises `ExportError` on an unreadable stamp; `per_stage` keeps
history order, starts its first stage at the first host event, and reports `unavailable`. On the
1.19.0 hello gate run the first stage is 16.0 s in the exporter and 21.3 s in `metrics.json`,
and the other 33 stages agree to within rounding, because both subtract adjacent acceptance
stamps. `run.py` runs both on every run, so the two views can differ for a stage. The exporter
ships inside the published `shiploop-e2e-audit` skill and `metrics.py` is test code, so sharing one
computation means moving one of them.

**Non-regression.** A2 changes what is recorded and printed, never a verdict: nothing in grading
reads `stages` or `termination` (`run.py` writes them into `result.json` and the baseline row and
prints them). The engine is untouched. S-12 is not met for attribution (above). The old rows stay
in `baselines.jsonl`, unused, rather than being deleted or shimmed.

**Evidence.** `StageAttributionTest` (8) and `BaselineComparabilityTest` (5) in
`test/shiploop-e2e.test.py`. They use Grok-shaped streams and whole-second times, so they could not
see the Codex shape, sub-second boundaries, a recreated timeline or an unfinished run on a host
without turn events; the review follow-up adds those cases. Not yet seen in a live run.

### 8.3 A3 — harness-side termination record (retrospective)

**Anchor.** S-14 (a run ending blocked or awaiting a person is "reported as such, never resumed as
if answered") and S-6 (runs survive session resumes): the question "why did those two runs stop?"
(§4.4) needs a record from the observer that owns the process. The anchor as first written named
"credit exhaustion, harness timeouts and background-task kills" for particular runs. **Corrected
2026-10-04** (it first said "three runs sit active with no recorded cause"; re-checking found
**two** abandoned with no cause and the third a live resume still in flight). Of the three causes,
the record is faithful for one: a harness timeout (`process_status` `timeout`, the return code,
`run deadline spent`). Credit exhaustion reads as `success` on Claude and as Grok's generic
`cancelled`. A background-task kill that takes the harness down leaves no record at all, because
the observer is dead: **accepted**, inherent to a harness-side record (§10.4).

**Adversarial evaluation.**

| Consequence sought | Finding | Disposition |
|---|---|---|
| Fails silently: a Claude session that ended on an API error | The stop reason is `stopReason or subtype`; Claude's result event has no `stopReason`, so a session that died on an API error (rate limit, credits, model access) is recorded as session stop `success`. Reproduced with `claude -p … --model not-a-real-model`: `subtype: "success"`, `is_error: true`, `terminal_reason: "api_error"`, exit 1. The host's own error fields are never read, and Codex's `turn.failed` loses its message | **mitigated by the review follow-up** |
| A fabricated observation | `--resume-run` on a run that finished while no harness watched starts no host, but `main` builds `process = {status: "exited", returncode: 0}` and `termination_facts` copies it: the record and the printed line say "host exited rc=0". The resume budget is also recorded as spent without re-reading the engine state after the last permitted session. The original `result.json` is replaced | **mitigated by the review follow-up** (a regrade or a resume is marked as not observed) |
| Not one entry per session | `session_stops` comes from sessions that wrote an end or result event, so a killed or crashed session is absent, and after `--resume-run` it spans sessions the counters beside it do not | **mitigated by the review follow-up** |
| Breaks saved runs (destructive) | `--resume-run` on a finished run with a different host, or whose recorded plugin directory is gone, takes the `elif args.source == "marketplace"` branch of the version gate; a gate problem there (for example unpublished local commits) writes `{pass: false, …}` over the finished run's passing `result.json` before any host starts | **mitigated by the review follow-up** |
| Misleading labels | A blocked run whose engine accepted the `blocked` result is reported as "stage never accepted"; a halted run reports the pseudo-stage `inner-loop` | **mitigated by the review follow-up** |
| Passes the tests while failing a live run | `TerminationRecordTest` (3) calls `termination_facts` with a fixed process dictionary and a `resume_stop` string the test supplies, so the five reasons `main`'s loop assigns and the wiring into `result.json`, the baseline row and the printed line are unpinned | **mitigated by the review follow-up** |
| Fails open | A non-string stop value would make the printed `stopped` line raise after `result.json` and the baseline were written (low likelihood) | **mitigated by the review follow-up** |

**Non-regression.** No verdict or exit code reads `termination` (§8.2). The engine ledger stays
declined (§5, A3). The record never reports a ShipLoop refusal as a cause; the review confirmed
that part holds.

**Evidence.** `TerminationRecordTest` (3), with the gap above. Not yet seen in a live run, and the
review's reproductions used the harness's fake hosts, not a real killed session.

## 9. Repository conventions for landing this

§8 holds one record each for A1, A2 and A3. The first version of this section said A2 and A3
"carry no behaviour anchor"; SPEC has no exemption for observation-only harness changes, and §8.2
and §8.3 give their anchors. Their scenarios — an unavailable or partial timeline,
incomplete-stage accounting, and an unmatched baseline identity that must not compare — are
covered by the tests named in §7, within the gaps §8 records.

- A1 ships with `changes/shiploop/test-run-could-not-run.md` (`bump: minor`), per
  [AGENTS.md](../AGENTS.md) ("Every skill change adds a note"). A2 and A3 touch only `test/`,
  which needs no note.
- `plugins/`, the catalogs, the README inventory and every `version:` field remain release-script
  output; none was touched.
- Land by merge or rebase, never squash.

## 10. Review of the landed changes, and what is not fixed

### 10.1 What was reviewed

A1 (`0d8d32f9`), A2 and A3 (`3c604304`) and this document (`e469f2a4`), merged onto the 1.19.x
release line as `9db0be37`. Four scopes (A1, A2, A3, the integration with what shipped meanwhile)
by three lenses (rules, adversarial, runtime), two skeptics per finding, 186 agents in all. 78
findings were confirmed (30 major, 48 minor), in 16 groups; 9 further candidates were rejected by
both skeptics. The compact export, the group table and the dispositions are in
[docs/experiments/shiploop-a1a3-review-20261004/](experiments/shiploop-a1a3-review-20261004/README.md).

The material findings: the route out that A1's refusal names (`revise`) is refused at
`test-green`, `regression` and `static-checks`; unmeasured counters are recorded as zero for Codex
and Claude, and the stage comparison then reports no difference; the termination record invents a
host exit on a regrade and records a Claude API error as success; and a regrade through the
marketplace branch overwrites a finished run's `result.json` with a failing stub.

### 10.2 What the review changed here

Records for A2 and A3 (§8.2, §8.3); the A1 dead-end row and non-regression text (§8.1); the
baseline row count (13 at A2's commit, 15 now) and the Luna run's end state; the attribution
claim (two implementations, §8.2); A4 item 1; and every line citation, replaced by a symbol or
section name. The journal marks the superseded figures (`test/shiploop_e2e/LEARNINGS.md`) and the
harness README describes the current record
([test/shiploop_e2e/README.md](../test/shiploop_e2e/README.md)).

### 10.3 Why admission missed it

The change-admission record covered only A1. The harness changes were admitted by their own
tests, which share one blind spot: every fixture is Grok-shaped, whole-second and complete. And
the change set was authored on a base that the release line then passed: merging it needed a
review of its interplay with what shipped meanwhile (the 1.19.0 baseline rows, the keepalive's
dependence on `MAX_REFUSED_RUNS`, the Run Review exporter). The footprint of a change to a shared
helper is its callers *and*, for a stale-base merge, what landed on the line since.

### 10.4 Not fixed (known limits)

- **Whole-second engine stamps.** The navigator stamps `%Y-%m-%dT%H:%M:%SZ`, truncated, so the
  turn that submits `shiploop complete` sometimes lands after its own stage's stamp and is counted
  in the next stage. About a third of boundaries on the four hello runs have a turn in the second
  after the stamp (my recount: 50 of 157), and the review found the closing turn after its stage's
  stamp at 3 of 13 and 4 of 15 boundaries on two runs and, against file times, at 7 of 26, 20 of 43
  and 8 of 26 on the three Claude hello runs. Read per-stage turns as ±1; identical runs can print a one-turn stage difference.
  The remedy is an engine change (sub-second stamps; `_epoch` already parses fractions) or a
  one-second allowance, and neither is made: `stage_diff_lines` gates nothing and only locates
  where a whole-run difference landed.
- **A recreated `timeline.json`.** The engine recreates a lost or unreadable timeline and stamps
  every historical action with the current time. The stamps are readable, so the harness cannot
  tell them from real ones and reports confident zero-length stages; "unavailable" covers only a
  stamp that cannot be read. Detecting it needs a marker from the engine; not added here. (Review
  findings 41, 46 and 55 are assigned to the harness follow-up; if it adds a check for equal
  stamps, narrow this bullet.)
- **A timeout whose partial output already shows failing tests** is `could-not-run`, not a
  product failure, and spends none of the 7 refused runs, so a suite with a hanging teardown
  retries without a cap. Judging half a report would reintroduce guessing; revisit if a run shows
  it.
- **A command that fails to start inside `/bin/sh -c`** (exit 126 or 127) counts as a product
  failure, so a missing test runner spends refused runs like a failing test. "Cannot start" means
  the process could not be spawned.
- A harness killed with its host (parent-task kill, background-task limit) writes no termination
  record; only the engine's own state survives (§8.3).

Other accepted limits are in §8: the exporter's second attribution (§8.2), stage seconds that
include interruption gaps, and `turns` counting assistant content blocks (about 1.7 × API calls,
`LEARNINGS.md`, "Hello cost analysis").

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
  (the module docstring of [shiploop_lint.py](../skills/shiploop/scripts/shiploop_lint.py)). The accurate claim is that ShipLoop
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
  cited above was re-verified here, and line numbers are this tree's. *[Superseded 2026-10-04:
  after the merge, the line numbers in this document pointed at unrelated code (the host launch,
  the run deadline, `stage_results` and the timeline recreation all cited lines that now hold
  something else). Every citation is now a symbol
  or a section name, which survives edits; a symbol citation is checked by finding the symbol, not
  by checking that the line exists.]*

- **"A2 and A3 carry no behaviour anchor"** and **"this record covers A1"** — withdrawn.
  SPEC's change admission covers harness changes, and both have anchors. §8.2 and §8.3 are
  retrospective records written from the review.
- **A1 recovery dead end "mitigated"** — wrong as recorded. The refusal named `revise`, which the
  navigator refuses at `test-green`, `regression` and `static-checks` (§8.1). The test pinned the
  wording of the refusal, not that the named outcome is accepted.
- **"`UnavailableExecutionTests` (6)"** — 7. §7 had it right; §8 did not.
- **"12 existing baseline rows"** — 13 at A2's commit, 15 after the merge; none names host, model
  or effort (§7, §8.2).
- **"One attribution implementation in `metrics.py`"** — two, after the merge (§8.2).
- **"Separate active execution from interruption gaps (A2)"** — A2 does not (§5, §10.4).
- **How the footprint was derived, again.** The caller search for A1 was `test_loop.verify(` and
  missed the dependents of `MAX_REFUSED_RUNS` (the keepalive's stuck bound) and of `check_terminal`'s
  `revise` bypass. Search for the *constants and restrictions* a change alters, not only the
  functions it edits.

## Provenance

Measurements: 11 protocol-4 run directories under `~/e2e-runs/20261003/` and two scratchpad trees,
read via `state.md` + `timeline.json` + `run/tests/*-verify*.md`. Review: Astra (`gpt-6-astra`,
xhigh, read-only) against checkout `3d2ab1da` plus the working tree, 2026-10-04 — it changed or
removed R1, R2 and R3 and found the `error`-persisted-as-`failed` bug.

Review of the landed changes (§10): 186 agents, 2026-10-04, against branch `a1a3-integ-7f216e`
(`9db0be37`); compact export and dispositions in
[docs/experiments/shiploop-a1a3-review-20261004/](experiments/shiploop-a1a3-review-20261004/README.md).
