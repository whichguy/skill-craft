# Astra review: step boundaries for ShipLoop's ask-agent route (2026-10-28)

Model `gpt-6-astra`, persona `codex-astra`, effort `max`, fallback `False`, exit `0`, profile `consult`, sandbox `read-only`. Asked through the `ask` skill (`ask.sh astra ask --json --profile consult --effort max --cwd <worktree>`) from a branch at the tip of feat/per-step-iteration-6adde0 after 2b-5 (`bb32139c`), for design T §9.1 step 2c (owner decision G1). The question and the answer are verbatim; the answer is the JSON envelope's `text`.

## Question

Adversarial design review, read-only: do not edit any file. Recommend one option for ShipLoop's ask-agent route
under the per-step iteration, and attack every option, mine included.

Repository (read freely): /Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5 (branch based on
feat/per-step-iteration-6adde0 at bb32139c, 2b-5 done).

Read:
- docs/shiploop-review-after-tests-design-2026-10-27.md: §8 (the per-step iteration), §9 (Astra's earlier review; rows
  2 and 3 say the ask-agent route gets the same step boundaries, G1), §9.1 (2a to 2b-5, built), §9.2 (G1).
- skills/shiploop/references/navigator.md: "Step commits" and "The commit stage"; "Recover one existing run" and
  "Context boundaries" (what ask-agent means for producers).
- skills/shiploop/references/chain-route.md and parallel-chain.md ("Join and return", "Serial execution in the main
  context", "Done means accepted").
- skills/shiploop/scripts/shiploop_iteration.py (whole file: Iteration, start, invalidated, ends_iteration,
  pending_record, commit_decision).
- skills/shiploop/scripts/shiploop_navigator.py: step_view, _next_step_follows, _between_steps, implement_progress,
  _iteration_entry, current_iteration, _iteration_base, _step_entry, _commit_stage, _item_commit_stage, _ask_agent,
  look_back_lines, _step_proof_gate, _transition.
- skills/shiploop/scripts/shiploop_loops.py implement_scope (all_steps); shiploop_test_loop.py step_number, new_ids.
- skills/shiploop/scripts/shiploop_chain.py: _bind, _require_bindable, guard_completion, _per_step_expected_target,
  _per_step_integrate; shiploop_chain_git.py target_identity, _assert_clean, fast_forward.
- skills/shiploop/scripts/shiploop_stage_spec.py _finish (send-back from test-spec through document goes to step-plan).
- test/shiploop_e2e/LEARNINGS.md entries "chain-seeded — 2026-10-03" and "chain-full — 2026-10-03".

## What is built (inline route)

Per step, in plan order: implement -> test -> document (its Improve review is document's child) -> ShipLoop's commit
stage, then the next step's implement. The step's ledger row (RUN/iterations/<item>.json) holds its number, base (a
full commit ID, HEAD at the end of the call that entered the step), commit, and a pending record written before the
commit. `iteration.commit_decision` commits on the base, recognises a commit that already landed, and refuses a HEAD
anything else moved inside the step ("only the commit stage commits inside an iteration"). Lint, RED (the step's new
cases must fail in a checkout of the iteration base), mutation, document's left-out rule and the review diff read the
step's base, recaptured by _iteration_base when document hands over to the next implement. A send-back from test-spec
through document goes to step-plan, which ends the iteration (`iteration.ends_iteration`); committed steps stay
committed and the next plan revision starts from HEAD, with any uncommitted edits counting as its first change.

## The ask-agent route today

- `loops.implement_scope` gives one implement action with `all_steps`. Its packet's duty 7 (Chain) binds a Plan
  Dispatcher chain on a reviewed execution graph (parallel by default, serial only on an explicit limit), or one writer
  in the execution checkout when the plan says no chain.
- The chain: `_bind` freezes the graph and the target identity (including HEAD); workers build in sibling worktrees and
  commit there; `done` performs a guarded `merge --ff-only` into the invoking checkout (`_per_step_integrate`,
  `fast_forward`); `_per_step_expected_target` advances the target "only through recorded integrations";
  `target_identity` requires a clean checkout; `guard_completion` refuses implement's complete until the chain's finish
  receipt exists.
- Then one item-level test stage (`test_loop.step_number` is None, so every case is new and RED runs against the item
  base), one document, one review (a fresh worker), and `_item_commit_stage`: `feat: <item> <title>`, no pending record,
  no ledger row. The code itself is already in the workers' commits and the "ShipLoop chain prepared" merges.
- Other producers on ask-agent: the packet prefix "Execute the prompt in a fresh context" (a fresh native worker where
  usable). navigator.md: "The setting selects packet text; no script verifies who executed an assignment."

## Evidence

- Owner, 2026-10-27: "To be very clear, I want to build one step, then test, improve, and document, and then build step
  number two, then test it, improve it, document it, and so forth and so forth. The goal is not to just do one
  monolithic build of all the steps."
- The only live ShipLoop chain runs (Sonnet 5.5, 2026-10-03, temperature-report, graph S1 || S2 -> S3):
  - chain-seeded: S1 and S2 launched 16:26:22, settled 16:28:34 and 16:28:50; S3 launched 16:29:18. Implement 5.2 min
    of a 22-minute run.
  - chain-full: S1 and S2 launched 17:02:10, settled 17:05:08 and 17:05:28; S3 launched 17:06:02. Implement 6.4 min.
  - So parallel build saved about one step's build, 2 to 3 minutes per item. Every full E2E run since uses inline (the
    default); ask-agent is opt-in, and the E2E harness keeps seeded chain cases (`run.py --seed-at step-plan`).
- §8.4: per step, the iteration adds a test, a document and a review stage; on Sonnet a step review is about 1 minute.
- ShipLoop's chain is 7,710 lines in four modules (shiploop_chain, _git, _handoff, _ledger) with seven test files.
- Standing rules: one supported version (no shims or second lifecycles), KISS, quality first then tokens then time,
  scale ceremony to measured gain.

## The options I drafted

(a) Serialise; the route keeps its fresh-context producers.
- (a1) Each step's implement binds a one-step chain. Cost I see: the chain's `done` fast-forwards a worker commit inside
  the iteration, which `commit_decision` refuses; so either the commit stage squashes the chain's recorded return onto
  the base, or the chain gains an integration that leaves the change uncommitted. A one-node graph must be derived from
  the reviewed graph per step, and each step pays about nine chain callbacks (bind, claim, start, launched,
  import-handoff, prepare, done, cleanup, finish).
- (a2) No chain: the ask-agent route issues one implement action per step exactly as inline, executed by a fresh
  native worker in the execution checkout (the context boundary every other ask-agent producer already has). Ledger,
  pending record, commit stage and send-back are inline's, unchanged. The route-specific code goes (all_steps,
  _item_commit_stage, the INLINE checks in step_view and friends, the ask-agent implement and step-plan duty variants,
  their head pins). Lost: parallel build. ShipLoop's chain is then unused, so under one supported version it would be
  removed (an owner decision).

(b) Keep the parallel build, then iterate test, document, review and commit per step in plan order over the integrated
result. Problems I see:
- the iteration base for S1 would already hold every step's code, so RED needs a second base per step (the chain's
  recorded start revision for that step), and GREEN runs on a tree with later steps' code;
- "this step's changed lines" for lint and mutation become the contribution's diff mapped through prepare merges;
- the step review's diff since its base shows tests and docs but not the step's code, which is in chain commits below
  the base;
- each step commit holds only tests, docs and review edits; the code commits are the workers'; and paths cannot be split
  per step when steps share files;
- a send-back at step k goes to step-plan with steps k+1..n's untested, unreviewed code already committed into the next
  plan's base, the vanishing §9 row 5 forbids;
- it is the monolithic build the owner ruled out.
Ledger: base = the previous step's commit (S1: the chain's finish commit) plus a red_base field; pending record as now.

(c) Keep the route item-level (§9.2's alternative). A second lifecycle: no iteration identity, no ledger row, no pending
record, no "only the commit stage commits" (worker commits are allowed), RED against the item base, one review. Every
later lifecycle change (2d's test tiers, F9 skills per stage, Run Review's per-step view) is decided twice. 2b-4c found
the chain, send-back and improve-route suites had drifted, since --changed-from never selected them.

(d) Build ahead (my addition): while step k iterates, the next steps whose dependencies are committed build in sibling
worktrees; at step k+1's entry ShipLoop integrates its contribution as an uncommitted change onto step k's commit, and
the iteration runs as inline. It needs chain changes: the target must advance through ShipLoop's commits (today
`_per_step_expected_target` refuses, "prepared target is stale"), integration must not commit (today ff-only), and the
clean-target check holds only at the iteration's entry. A send-back or a review change wastes the speculative builds.
Gain: up to one build per independent step hidden behind the previous step's test, document and review.

My recommendation: (a2), with the chain's removal from ShipLoop as the owner's decision that comes with it.

## Answer

1. Verdict and the option you recommend (or a better one), with reasons.
2. For each option: its real cost, its risk, how it keeps one supported lifecycle, what happens to the iteration ledger
   and the commit stage's pending record, and how a send-back mid-item behaves. Correct me where I am wrong.
3. Findings against my claims, each with a severity (P1, P2, nit) and the file and symbol that shows it. Check the code;
   say when a claim is unverified.
4. What (a2) loses that matters, and whether anything must be kept from the chain (for example its per-step
   verification, worker isolation, or recovery after a host loss).
5. The one decision the owner must make, stated as a choice.
6. Open unknowns a pilot should measure.
Be concrete and cite files and symbols, not line numbers.

## Answer

**Recommend (a2): one serial per-step lifecycle, with `ask-agent` selecting the execution context.** Pilot it before release. Retiring ShipLoop’s chain is a reasonable consequence, but the owner must understand that this also removes a demonstrated isolation and recovery capability—not merely parallel build speed.

I checked the checkout at `bb32139ced324c149d016851e0bb720142ed99ae`. No files were changed. This is a source review plus an in-memory probe of `commit_decision`; I did not run the test suites or independently regrade the live runs.

Your central argument holds: (a2) follows the owner’s requested order with the fewest additional mechanisms. However, “inline’s ledger, pending record and send-back, unchanged” overstates how complete those guarantees currently are.

The findings that materially change the decision are:

1. **P1 — A2 loses safe replacement of an implementation worker whose stoppage cannot be established.**

   Today, `shiploop_chain._parse_retry` explicitly accepts `confirmed_stopped: false, native_status: "unavailable"`. `_retry` preserves the old workspace; subsequent operations reject the obsolete attempt. A replacement can therefore proceed without sharing working files with the possibly surviving worker.

   With a2, both attempts would write the execution checkout. Rejecting an obsolete callback cannot prevent its filesystem writes. The iteration ledger is not a worker ownership or fencing mechanism.

   This capability has live evidence: the journal’s **“Batch B decisions”** records the owner’s “retry without proof” decision, and **“group C verification”** records two successful kill-and-resume runs. The lifecycle test also exercises this contract. A2 must either establish stoppage through the host or leave replacement pending; it cannot claim equivalent recovery.

   Sources: [shiploop_chain.py — `_parse_retry`, `_retry`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_chain.py), [shiploop-chain-lifecycle.test.py — `test_lost_native_worker_is_retried_without_a_confirmed_stop_and_finish_keeps_it`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/test/shiploop-chain-lifecycle.test.py), [LEARNINGS.md — Batch B decisions and group C verification](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/test/shiploop_e2e/LEARNINGS.md).

2. **P1 — The existing commit recovery has an uncovered crash window.**

   `_commit_stage` records `commit=…` and drops `pending` **before** `dispatch` calls `save` for the advanced navigator state. If the process stops between those operations, recovery sees the old document action, HEAD at the completed commit, and no pending record. `_commit_stage` ignores the recorded `commit` when calling `commit_decision`, so the retry refuses its own commit.

   The in-memory probe returned:

   ```text
   HEAD at base:                                      commit
   HEAD at landed commit, pending retained:            done
   HEAD at landed commit, pending dropped before save: refuse
   ```

   The existing retry test interrupts **before the commit is recorded**, so it covers the preceding window, not this one.

   There is another entry window: `_iteration_entry` runs after navigator `save`. A crash there can leave the new implement action without its iteration row; `_commit_stage` currently skips committing when that row is absent.

   Keep the ledger format if useful, but make ledger and navigator transitions recover together before claiming full idempotency. These are source-confirmed gaps; I did not inject process crashes through the CLI.

   Sources: [shiploop_navigator.py — `_commit_stage`, `_iteration_entry`, `dispatch`, `save`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_navigator.py), [shiploop_iteration.py — `commit_decision`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_iteration.py).

3. **P1 — “RED and mutation read the iteration base” is not universally true in this implementation.**

   `_test_loop_gate` passes the item’s `preparatory_base` into RED and mutation on every step. Both readers replace the captured lint base with that commit when supplied. Consequently, after a preparatory fix and a committed S1, S2 can still run RED and mutation against the preparatory commit rather than S1’s commit.

   More generally, the commit ledger’s `Iteration.base` and the verification base are separate records. `lint.capture_base` records a working-tree snapshot; `_review_base_line` reads its `tree`. `_iteration_base` refreshes that record on document→implement, while re-entry through planning keeps it. A full commit ID in the ledger does not by itself prove that every gate uses that commit.

   This does not favor retaining the chain. It means a2 should reuse **one corrected implementation**, rather than inherit these assumptions unchecked.

   Sources: [shiploop_navigator.py — `_test_loop_gate`, `_iteration_base`, `_review_base_line`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_navigator.py), [shiploop_test_loop.py — `_base_run`, `_at_commit`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_test_loop.py), [shiploop_mutation.py — `_check`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_mutation.py), [shiploop_lint.py — `capture_base`, `on_transition`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_lint.py).

4. **P1 — D requires changing chain lifetime and completion authority, beyond the three integration changes listed.**

   `_require_bindable` permits binding only the current implement action. `_current_binding` rejects mutations through a previous action. `guard_completion` requires the entire bound chain to finish before the producer can complete. Thus today’s chain cannot remain operational while its parent advances through test, document and the next implement.

   D needs a cross-stage speculative-work owner, or separate contribution machinery. It must also distinguish “worker contribution ready” from “step accepted after its iteration commit”; current `_per_step_done` releases dependencies immediately after integration.

   A related problem affects a1: navigator `dispatch` invokes `guard_completion` before examining the submitted outcome. An unfinished bound chain therefore blocks an implement **send-back**, too. A worker discovering an impossible plan needs a safe abandonment-to-planning path; successful `finish` cannot be its prerequisite.

   Source: [shiploop_chain.py — `_require_bindable`, `_current_binding`, `guard_completion`, `_per_step_done`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_chain.py), and navigator `dispatch`.

5. **P2 — “The only live chain runs” is contradicted by the journal; the time saving is inferred.**

   Besides the two temperature-report runs, Batch B records four-wide and depth-three graphs, retries, and additional completed runs. Group C records the two recovery successes above.

   The quoted launch/settlement times demonstrate overlap. They do not measure the counterfactual serial duration, distinguish worker build time from collection/preparation/verification, or establish net savings after orchestration. “About 2–3 minutes” is a plausible estimate for those examples, not a measured effect.

   I did not verify the blanket claim that every later full E2E used inline. I did verify that `run.seed_run` still defaults ordinary seeded runs to ask-agent. The 7,710-line count and seven principal chain test files are correct.

   Sources: [LEARNINGS.md — chain-seeded, chain-full, Batch B, group C](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/test/shiploop_e2e/LEARNINGS.md), [run.py — `seed_run`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/test/shiploop_e2e/run.py).

6. **P2 — A2’s removal inventory needs to include consumers and distinguish context policy from lifecycle policy.**

   Besides the named navigator predicates, `test_loop.step_command` independently disables the Proof on ask-agent; `step_number` disables due-case projection. Run Review’s `work_items` explicitly treats ask-agent visits as unassignable to individual steps. The shared-checkout implement duty also cannot simply reuse `_IMPLEMENT_INLINE`, which says to execute in this conversation and dispatch no worker.

   Remove route distinctions from step semantics while retaining the distinctions governing worker context, ownership and parent-only callbacks. Account for incompatible saved item-level histories explicitly; do not reinterpret an old all-steps implement receipt as S1. Historical rendering is not a second executable lifecycle.

   Sources: [shiploop_test_loop.py — `step_command`, `step_number`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_test_loop.py), [shiploop_prompts.py — `_IMPLEMENT_INLINE`, `SERIAL_INNER_CONTEXT`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_prompts.py), [Run Review export.py — `work_items`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop-run-review/scripts/export.py).

Here is how I assess every option.

| Option | Owner’s strict build order | One shared acceptance lifecycle | Recommendation |
|---|---|---|---|
| a1: one-step chains | Yes | Possible after redesigning return semantics | Reserve for required isolation |
| a2: fresh worker in execution checkout | Yes | Yes | **Pilot and adopt** |
| b: build all, verify per step | No | Different evidence and commit semantics | Reject |
| c: item-level ask-agent | No | No, as drafted | Reject |
| d: speculative build-ahead | No, literally | Possible for acceptance, with another execution mechanism | Defer |

**A1 preserves isolation, but buys no parallelism between planned steps.** Its legitimate value is isolated failure, retained attempts and safe replacement—not speed.

Use an uncommitted contribution transfer **before** the iteration’s gates, leaving target HEAD at the iteration base. Fast-forwarding first and squashing at commit time makes the chain’s recorded ancestry and the iteration’s history disagree. Also, adding `--no-commit` to the existing fast-forward is insufficient: Git documents that fast-forwards still move HEAD. `--squash` can leave changes uncommitted, but it supplies none of ShipLoop’s receipt, recovery or ownership semantics. [Git merge documentation](https://git-scm.com/docs/git-merge).

The existing chain’s `finish` requires a committed target and accepted integration ancestry; `guard_completion` checks that ancestry again. Therefore an uncommitted return changes prepare/done/finish, not just `fast_forward`. The iteration ledger and commit pending record can retain their existing meaning, but contribution application needs its own recoverable intent: the later commit pending record cannot detect a half-applied or already-applied return.

A one-node graph also needs to preserve the reviewed step’s criteria and evidence that dependencies are already committed. Your callback estimate is illustrative: parallel mode has `launched`; serial mode does not. **Serial chain mode currently executes in the main conversation**, so preserving fresh execution requires one-worker parallel mode or another executor change.

On send-back, accepted earlier iterations remain committed. Current-step edits must remain uncommitted, and stopped/superseded workspaces remain evidence. The clean-target requirement also needs an explicit answer for edits retained from a previous send-back.

Sources: [parallel-chain.md — Serial execution, Done means accepted, Join and return](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/references/parallel-chain.md), [shiploop_chain.py — `_per_step_finish`, `guard_completion`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_chain.py), [shiploop_chain_git.py — `target_identity`, `fast_forward`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_chain_git.py).

**A2 has the lowest ongoing complexity, but its safety depends on exclusive writer ownership.** A fresh worker performs one bounded assignment, returns, and stops; the parent verifies and submits the callback. Test, document and Improve then follow the same iteration machinery. The shared ledger and pending record need no route-specific schema.

The worker must not commit, advance ShipLoop, start a later step or leave delegates writing during verification. Those rules already belong to the generic producer boundary, but the scripts do not prove who executed the assignment. Fresh-context execution is a host behavior to observe, including its permitted fallback—not a guarantee obtained by changing `delegation`.

On send-back, the revision changes; earlier commits remain; the current edits remain visible against the new iteration’s committed base. No future step has already contaminated that base. This is the cleanest explanation of the owner’s intended behavior.

Its real costs are more serial worker launches, repeated grounding, and reduced handoff continuity compared with inline; its real operational loss is the unavailable-worker recovery described above. Neither total token savings nor faster completion is established.

Source: [navigator.md — Recover one existing run and Context boundaries](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/references/navigator.md).

**B fails on evidence attribution even if its ledger can be made mechanically consistent.** Your principal objections are correct.

With all code below S1’s iteration base, the ordinary review diff omits that code. A `red_base` field only changes RED’s checkout; it cannot make GREEN prove S1 independently of later implementation. A worker’s original base can also omit earlier steps that should now be accepted, causing RED for the wrong reason.

The pending record would reliably describe a tests/docs/fixes commit, not the requested whole-step commit. Send-back carries later unaccepted implementation into the next plan’s committed baseline. Fixing that requires reconstructing and admitting contributions sequentially, which abandons B’s “already integrated result” premise.

**Nit:** shared files do not make splitting changes intrinsically impossible—ordered commits can modify the same file. The problem is reconstructing valid contribution boundaries and their dependencies after combined preparation, not filenames themselves.

**C has the lowest immediate migration cost and the clearest permanent semantic split.** It preserves existing chain performance and recovery, but maintains different answers to “what is accepted?”, “what does RED compare against?”, “who may commit?” and “what can send-back retain?”

As drafted, there is no iteration ledger or pending record; chain integration recovery does not supply idempotent recovery for the later item commit. Adding those records would improve C, but would not establish the requested step boundaries. Calling the whole item one iteration would merely rename the monolithic build.

After an item-level test or document send-back, already integrated worker commits remain. Replanning must acknowledge those retained implementations rather than suggest that only accepted step iterations form the base.

Your drift evidence is relevant, although it also indicts test selection: a second lifecycle is not the sole cause of suites being omitted. The design document explicitly records the affected suites and the broader verification used to recover them. [Design document — §9.1, 2b-4c](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/docs/shiploop-review-after-tests-design-2026-10-27.md).

**D is the strongest future performance option and the largest new design.** It can preserve a single acceptance lifecycle: enter step k on the previous committed step, apply only k’s contribution without moving HEAD, then run all ordinary gates and commit. The iteration ledger needs no `red_base`; the speculative contribution separately records where it was built.

But it requires recoverable contribution application, cross-stage ownership, dependency validity against committed results, and invalidation of obsolete attempts and evidence. Clean textual application is insufficient after an earlier review changes an interface or assumption. A send-back must invalidate old-plan speculative work, reject late returns and preserve its workspaces; only the current accepted-prefix checkout proceeds.

It also contradicts the literal instruction to finish one step before building the next, even when the future code stays elsewhere. That requires an explicit relaxation of the product contract.

Do not dismiss D merely because reviews now take time: longer test/document/review stages create **more opportunity to hide independent builds**. The objections are the prescribed order, unmeasured net benefit and substantial recovery machinery.

What a2 should retain from the chain is the useful obligation, not necessarily its mechanism:

- **Independent acceptance.** Preserve parent verification, executable step Proof, cumulative GREEN, step-specific RED and mutation, and the subsequent review. The chain bridge does not itself rerun every `contract.done` confirmation; much of that verification is a parent duty. Do not count its receipts as stronger automated testing than they provide.
- **Complete assignment context and evidence.** Preserve action/plan/step identity, required planning references, selected skills, worker findings and durable return evidence. A launch packet that only names “S2” is insufficient.
- **Ownership and interruption discipline.** Preserve parent-only callbacks and reconciliation of an existing worker before replacement. The unavailable-worker retry capability cannot be preserved merely by retaining an attempt ID in a shared checkout.
- **Meaningful integration work.** Keep an actual cross-component join or interface check as an ordinary planned step where required. The branch-gathering ceremony can disappear.
- **Historical evidence.** Preserve old receipts, workspaces, reports and recorded experiment outcomes. Removing the ShipLoop executor does not authorize deleting standalone Ask Agent/Plan Dispatcher capabilities or somebody else’s runs.

Sources: [parallel-chain.md — Step exit criteria and Join and return](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/references/parallel-chain.md), [shiploop_navigator.py — `_step_proof_gate`](/Users/dadleet/src/skill-craft/.claude/worktrees/amazing-almeida-10ffc5/skills/shiploop/scripts/shiploop_navigator.py).

**The owner’s decision is a choice of recovery capability:**

> Adopt a2 and retire ShipLoop’s chain, accepting that an unavailable worker writing the shared checkout may require establishing stoppage before continuing; **or** require isolated implementation attempts and fund a serial, uncommitted-return design such as revised a1.

I recommend the first choice. The approval should explicitly include the recovery trade-off; “remove parallel build” alone does not describe it accurately.

The pilot should resolve these unknowns:

- **Lifecycle correctness:** two or more steps, shared files, a spanning case, a docs-only step, and a step whose obligations are already satisfied. Verify actual action order and commits, not packet wording.
- **Base correctness:** a preparatory fix followed by multiple steps; send-back after a committed step with retained edits. Compare every RED, mutation and review base with the ledger’s intended commit.
- **Crash recovery:** interrupt before commit, after Git commits, after the ledger records it but before navigator save, and after save but before iteration entry. Verify no duplicate, skipped or falsely refused commit.
- **Worker ownership:** interrupt during implementation and test a late return. Observe whether the actual host can establish stoppage and whether any old writer survives replacement.
- **Context fidelity:** record native execution identity, freshness, fallback, missing planning context and accidental worker commits. The setting alone proves none of these.
- **Quality and cost:** attribute caught defects and rework by stage; measure total worker-plus-parent tokens, launches and non-overlapping wall time. Keep host/model/case settings fixed. Treat comparisons with the historical chain lifecycle as historical comparisons, not controlled measurements of parallelism.
- **Evidence consumers:** verify Run Review’s ask-agent step grouping and commit attribution. Existing chain cases explicitly request parallel execution; create or revise expectations transparently rather than count their changed behavior as unchanged coverage.
