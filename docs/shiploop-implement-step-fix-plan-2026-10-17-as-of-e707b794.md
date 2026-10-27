Execute: ask

# Implement-step improvement plan — refreshed 2026-10-25

**Most of the original step-proof and packet repairs have landed. The next correctness fix is the candidate
judge accepting failed test output when the command exits zero.** Keep acceptance-procedure and obligation
continuity ahead of further prompt shortening.

This is the current version of the existing plan. It supersedes its
[2026-10-18 snapshot](shiploop-implement-step-fix-plan-2026-10-17-as-of-2026-10-18.md), while retaining the same
22 recommendation IDs, eight considerations, fourteen Code craft rules and 52 qualification IDs. Historical
Chess/Battleship outcomes remain attributed to their runs; they do not qualify this main revision.

## 1. Baseline and what changed

Fetched main is `e707b794de0a0bd802988ca68dac8e29ac0b3315`. The requested
`git -C /Users/dadleet/src/skill-craft rebase --autostash origin/main` succeeded. This advanced the checkout from
`6ed817622426dcfde4840a4b5bac945bc64f151a` by 29 commits. The previous plan's `17ddec369f49` baseline is 218 commits
behind this revision, including merged history. This is a source comparison, not 218 independent improvements.

Seven unrelated tracked experiment edits were restored without conflicts. Their added/removed lines were identical
before and after the rebase; all 148 initially untracked files were byte-identical immediately afterward. One edited
E2E test also gained upstream changes. The audit uses committed source via `git show`/`git archive`, excluding those
local experiments. [Preservation evidence](shiploop-implement-prompt-audit-evidence/rebase-preservation-2026-10-25.json).

The [29 newly fetched commits](shiploop-implement-prompt-audit-evidence/rebased-commits-2026-10-25.json) notably add
test-layer/criterion-confirmation gates, lower-layer evidence for unverified primary outcomes, explicit command
targets and remote-test exclusions, current glossary terms, and platform-card dependency/reporter guidance.
Step Proof, the shared Step block and Improve re-proof already existed at the starting checkout; they landed
earlier in the longer interval since the saved plan. The table below compares that saved plan with current main.

| Area | Previous plan baseline | Current main | Plan consequence |
|---|---|---|---|
| Inline step proof | Missing; item-wide checks requested in prose | Required `proof`, script execution, action/step/command/tree-bound receipt and Improve re-proof | Retain and qualify; do not reimplement |
| Assignment surfaces | Full-only step summary | Shared Step block in head/full/Improve, plus review base | Close the missing-renderer work |
| Procedure and access | Partial guidance | Shared procedure walk, intended actor/entry prerequisites, person-reply protocol | Focus on inherited procedures and obligation continuity |
| Additional evidence forms | Proposed `criterion_evidence`/eight-key form | Owner selected a lean guide-by-reference port with no extra fields/gate | Superseded; do not resurrect |
| Code craft | Nine-rule constant | Fourteen-rule constant and compact producer rubric; static consideration guide | Preserve selected wording; exact earlier expanded prose was not adopted |
| Loop wording/policy | Full printed argument; Improve gate two | Conditions on disk; producer gate zero, Improve first trivial review | Update examples and remove obsolete two-pass requirements |
| Test boundaries | Weak check/reporter/target facts | Test layers, criterion `confirm`, primary-outcome gate and per-command target rules | Keep semantic and consumer-observation limits explicit |
| Reuse | Missing on old main | Candidate/step receipt reuse; base/mutation reuse still deferred | Keep measured deferral; qualify external-state invalidation |
| Vocabulary/state | State v6, `HOME`, step `check`, `revise` | State v9, `KNOWLEDGE`, `proof`, `settle`, `due_stage`/`due_item`, `send-back`/`add-work` | Use current schemas; no migration from the old plan's guessed version |

Exact producers, consumers and enforcement points are in the
[current code map](shiploop-implement-prompt-audit-evidence/reference-code-map-2026-10-25.md).
The earlier [main map](shiploop-implement-prompt-audit-evidence/reference-code-map-2026-10-18.md) and
[integration map](shiploop-implement-prompt-audit-evidence/integration-c70a33f4/reference-code-map-2026-10-18.md)
remain historical evidence.

### Decisions carried forward

The lifecycle remains generic: project commands, platforms and domain rules enter through accepted records and
cards. Inline execution handles one step and its Improve review at a time; the ask-agent route handles the whole
plan. Each step proves only its assigned criteria, keeps other requirements intact, starts no later step and leaves
permanent test authoring with the test stage. Script-owned state, callbacks and observations remain authoritative.

Later committed owner decisions supersede the old proposal: the lean A0 port omits new per-step assessment fields;
Improve stops at its first trivial pass; the knowledge symbol and outcome vocabulary changed; and base/mutation
reuse was deferred after examining representative run costs. These are verified source decisions, not new
permissions inferred from this audit. `Execute: ask` still applies to implementing this plan in this chat.

## 2. Recommendation disposition

**Implemented** means the mechanism is present in committed source, with qualification limits shown below.
**Partial** means a specific remaining change or acceptance question remains. **Superseded** identifies a later
recorded design choice. **Deferred/conditional** is outside the immediate implementation queue.

| ID | Recommendation | Current disposition | Remaining work |
|---|---|---|---|
| R01 | Step-specific executable checks | implemented | Retain the mechanism. Qualify whether each command actually proves its assigned behavior; do not add a per-step gate to the whole-plan route. |
| R02 | One assignment on every surface | implemented | Retain the shared assignment. Test emitted surfaces under current bounds; do not restore the older full printed loop argument. |
| R03 | Criterion evidence and changed-candidate proof | superseded | Keep re-proof and existing observations/notes. Retire the proposed evidence-row schema; acceptance correctness is still required without adding that form. |
| R04 | Static method, cards, match and Code craft | partial; structural rewrite superseded | Preserve the lean guide and retire the extra forms/extraction. Earlier CC3 complex-unit, CC6 resource-release and CC9 composable-unit expansions remain absent; the lean-port record does not explicitly resolve them. Retain these as low-priority wording proposals. |
| R05 | Valid procedures through final review and person ask | partial | Extend only the missing inherited review/person boundary after a fixture shows where an invalid carried procedure survives. Keep valid setup and actual observation separate. |
| R06 | Early actor/access prerequisites | implemented | Retain early checks and qualify actor/entry evidence on the actual target. No new permission mechanism is needed. |
| R07 | Required acceptance and partial/declined replies | partial | Prove requirement-to-case-to-obligation continuity across partial replies, stage changes and omitted obligations. A required consumer observation must remain open; add enforcement only for a reproduced omission. |
| R08 | Observe the intended copy and reporter outcomes | outstanding | Reject recognized failed/error/cancelled outcomes when a wrapper masks the exit. Add real callback and primary passed-ID fixtures, positive controls for titles containing FAILED, and a deliberate policy for negated checks. Invalidate or rejudge receipts created under changed judging semantics; do not match failure words indiscriminately. |
| R09 | Mutation restoration and interrupted recovery | conditional | Do not build remote restoration machinery for the excluded route. If an authorized remote mutation path is introduced, require effect tracking, accepted-candidate restoration and interrupted recovery before enabling it. |
| R10 | Mutation check-only reuse | deferred | Keep the measured deferral. Reopen only when representative command cost justifies the identity/invalidation risk; do not remove mutation from check-only merely to shorten it. |
| R11 | Narrow revisions and unchanged prefix reuse | deferred | Treat prefix reuse as a separate optimization pilot. Preserve exact definitions and reopen actual product repair; no empty-diff shortcut. |
| R12 | Compact, valid result and callback contracts | implemented | Update examples to the current contracts and keep their validator checks. The old inline-notes and two-review policies are obsolete. |
| R13 | Resolvable references and essential facts | partial | Qualify locator resolution and essential command/target facts at the actual emitted head and installed path lengths. No demonstrated need for a second packet format or new symbol DSL. |
| R14 | Evidence-based Improve and relevant history | implemented | Retain current history selection and first-trivial review policy; qualify relevant evidence instead of adding a review quota. |
| R15 | Same scoped probe authority for implement and Improve | partial | For a genuinely authorized test route, make the opening and review permissions consistent with that route and its target/limits. Do not infer a release grant or introduce new authority. |
| R16 | Actual release state, not invented absence | outstanding | Repair release-plan, release-check and both reference copies to record observed current state and the remaining delta. One observation cannot prove present/absent discrimination; do not manufacture absence. |
| R17 | Product/test/tool-state classification and source return | partial | Fix the misleading no-action-needed message and qualify one unignored-tool-state fixture through review/return. Preserve required keep/exclude decisions and product configuration; do not add a classification taxonomy without demonstrating a bypass. |
| R18 | Harness keep, terminal state and reporting | implemented | Retain these distinctions. Qualify done-but-uncommitted, host exit and cleanup with harness integration fixtures; do not claim a fresh live platform outcome from this refresh. |
| R19 | Run-owned loop state and recovery | outstanding | Use a run-owned backing-state directory and preserve active receipt next_argv recovery. Validate fresh-context resume and missing-state failure without inferring success or overwriting receipts. |
| R20 | Applicable guidance across software packages | implemented | Preserve applicability across library, CLI, service, UI, data/config/docs and empty-repository cases. Card tests are not proof of every package type. |
| R21 | Avoid redundant system-stage executions | partial | Qualify reuse on stateful/remote commands before broadening it. A changed relevant external state must invalidate or bypass reuse; keep the broader system-stage optimization a measured pilot. |
| R22 | One directive with distinct production and Improve phases | optional | Optional wording-only cleanup: remove the repeated completion clause from WORK_STEP while preserving scope, all acceptance/continuation conditions and recovery. Do not restore the two-pass rule, extra nested loops or the old printed argument. |

The [code map](shiploop-implement-prompt-audit-evidence/reference-code-map-2026-10-25.md) gives the current behavior,
exact source spans and corresponding qualification IDs for every row. It also maps every consideration and Code
craft rule individually. A source anchor locates the implementation; it does not establish behavior by itself.

## 3. Remaining work, in priority order

### P1 — close the demonstrated false acceptance (R08 / T37)

The candidate judge reads exit code, count and ID presence, but does not reject a recognized failed tally or named
failure when the wrapper returns zero. A committed-source probe produced:

```text
Input: test_config.py::test_value[CASE-1] FAILED
       ================ 1 failed in 0.01s ================
Exit: 0
Parsed: ran=1, failed=1; CASE-1=failed
Current focused verdict: passed
Current check-suite verdict: passed
Required verdict after repair: failed
```

This is a reproduced **helper-boundary defect**, not a claim that a new live run accepted it. The
[probe](shiploop-implement-prompt-audit-evidence/probe-judge-zero-exit.py) loads the pinned committed scripts;
[its result](shiploop-implement-prompt-audit-evidence/judge-zero-exit-probe-2026-10-25.json) retains the full input and
verdict. Next implementation should first add a failing real-callback fixture, then make the smallest judge change.
Keep zero-tests, missing IDs, skipped/cancelled outcomes and legitimate source-only checks distinct. Add controls
for a passing test whose title contains FAILED, pytest setup/collection errors, and intentional negated checks.
Use recognized reporter semantics rather than a word match. The same judge supplies step Proof, verification and
outer-stage runs; a false passed ID can then feed the primary lower-layer gate. Reused old verdicts also need
invalidation or rejudging when the rule changes. Do not redesign the runner merely to fix this decision.

T37's other clauses remain explicit: there is no general script binding to a deployed revision; qualify the intended
copy separately. Mutation currently treats a nonzero command exit as a kill, including setup/build failures; a
behavioral-only kill rule would be a separate design change. Neither remote exclusions nor an ordinary kill is
proof of the stronger original T37 claim.

[Candidate judge](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:556); [existing per-ID outcome parser](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:599).


### P1 — establish valid acceptance and safe reuse boundaries (R05/R07/R21)

The procedure walk is now present where plans and cases are written. Carry-forward's code focus still lacks an
explicit check of inherited procedures. Add a narrow fixture in which an earlier accepted procedure becomes
impossible after a setup change; verify the last responsible review sends it back before a person is asked.

Required delivery contracts already block due stages, and partial replies have regression coverage. What remains
is end-to-end continuity from the original requirement through case, open-item and delivery-obligation records.
Use a required interaction that receives only a partial reply, then a revision that omits its obligation. If the
current gate already rejects it, retain that evidence and close the work; if it accepts, repair the omission path.
Do not add a second evidence form. The new primary-requirement validator requires a passed lower-layer test for an
unverified primary outcome; that row remains unverified and does not waive an actual required consumer observation.

Candidate receipt reuse is bounded by action/stage/item, command records, source tree and floors. A stateful target
can change while those values remain equal. Qualify that boundary with an isolated fixture; changed relevant target
or fixture state must invalidate reuse or force a fresh execution. This is a correctness check of existing reuse,
not authorization for a broader system-stage cache.

[Inherited review focus](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2011); [delivery transition gate](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1140); [primary lower-layer gate](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1269); [reuse identity](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:629).


### P2 — align scope, state and return handling (R15/R16/R17/R19)

| Change | Concrete acceptance procedure |
|---|---|
| Render consistent already-authorized probe authority in producer and Improve | Given one permitted isolated test route, both surfaces carry its target and limits; a release effect still requires its own authority. No new grant is inferred from a command string. |
| Describe actual release state | Start with an authorized candidate already staged. Update release-plan, release-check and both reference copies. Report present state and remaining delta; one observation cannot prove both positive and negative discrimination. Never delete resources to create absence. |
| Make residual review explicit | Leave one product configuration and one unignored tool-state file after the last item. Confirm plan-return may commit them locally but still requires keep/exclude decisions; the message must not say no action is needed while review is pending. An excluded path cannot enter the target unnoticed. |
| Place stage-loop backing state under its run | Start a loop, resume from a fresh context using the receipt, and check that its backing state is under RUN. Missing state remains incomplete; it cannot be reconstructed as success or overwritten by a replacement start. |

The stage start's explicit `--receipt` selects the isolated runtime branch. Without `--directory`, that branch uses
a temporary backing file. This is the actual invoked path; automatic host-session storage does not apply to that
call. No observed production loss is claimed by this source inspection.

[Improve authority](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2126); [release-check wording](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2100); [leftover commit](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1454); [pending review message](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2731); [required return review](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2760); [stage start](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1568); [runtime dispatch](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2437).


### P3 — resolve remaining wording proposals and measure replay changes (R04/R10/R11/R13/R22)

All fourteen Code craft rules are present, but three earlier proposed expansions are absent: CC3's complex-unit
contract/tombstone, CC6's release of acquired resources on every exit, and CC9's narrow interface/pure-core/side-effect
design. The lean-port record chooses the guide and one-line rules 10–14; it does not explicitly reject those three
expansions. Keep them as separate wording proposals after acceptance correctness, with current rules unchanged.
The [individual rule map](shiploop-implement-prompt-audit-evidence/reference-code-map-2026-10-25.md) distinguishes
their existing source from the missing additions.

Preserve the later base/mutation reuse deferral: the retained study found small savings and a new stale-acceptance
risk. Its timings are historical measurements, not current benchmark results. Cross-plan prefix reuse and broader
outer-stage reuse remain pilots. Preserve an unchanged-prefix rule if a pilot is authorized; an empty diff alone
cannot establish equivalent plans or valid evidence.

Further prompt work should test essential content at the emitted head and actual source reads, not optimize only
packet characters. Current constants distinguish the 16,000-character full-print switch, 19,500 required-content
boundary and 20,000 head limit. Do not restore the old plan's 16,000 head target or claim token/latency savings.

Work-field deduplication is an optional proposal, not required backlog. The current phrase is explicitly pinned as
the owner’s D4 wording; any later implementation must reconcile that choice with the requested direction. The
proposed shortening preserves stage sequencing, acceptance, continuation, callbacks and the first-trivial Improve policy.

[Later reuse decision](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2503); [current rendering bounds](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2664); [current Work wording](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2298).


## 4. Before and after: generic inner-loop prompts

### Direction and completion

The current architecture is already close to the requested directive-plus-condition structure:

```mermaid
flowchart TD
  A[Accepted step and criteria] --> B[Producer Until Loop]
  B --> C{Current proof and gates hold}
  C -->|No, justified work remains| B
  C -->|Yes| D[Improve review and repair]
  D --> E{Trivial review and valid candidate}
  E -->|No, repair remains| D
  E -->|Yes| F[ShipLoop rechecks and advances]
```

The producer establishes the step; Improve reviews it; ShipLoop accepts it. Both loops already exist. No extra loop
inside an Improve pass is proposed. A real blocker takes the existing blocked/send-back route rather than an endless
retry. A later-owned delivery item stays later-owned.

**Current Work template, excerpt** (the exact source is linked below):

```text
Implement all of step {step} ... anchored in ... ({criteria}{serving}) ... ({decisions}),
until each criterion assigned to this step is satisfied and none of the others is broken.
Do duty items {items} of {run}/packets/{action}.md. Write no tests and start no later step.
```

**Optional replacement Work field**, illustrated with a configuration parser and frozen accepted IDs:

```text
Implement S1's assigned criteria (C1, C2), serving R-1 and following AD-1, by executing
its duty items in /absolute/run/packets/A17.md. Keep other requirements and unassigned criteria intact.
Write no tests; start no later step.
```

The existing generated `exit_condition` and `repeat_condition` stay unchanged. They remain in the contract and are
printed by the runtime; the caller does not repeat them in a second argument. Generate the IDs and locator from the
accepted step plan as now. “Above” is not a recovery locator. “All delivery items anchored” is too broad for one step,
and a file location alone is not an observation.

[Current Work](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2298); [frozen C/R/AD bindings](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:1633); [contract-on-disk invocation](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2351); [first-trivial Improve policy](/Users/dadleet/src/skill-craft/docs/shiploop-implement-prompt-audit-evidence/reference-code-excerpts-2026-10-25.md:2377).


### Proof and inherited acceptance

**Earlier problematic request:**

```text
Implement S1, then run every item check, including the CLI that S2 will add.
Review the files and say whether delivery is complete.
```

**Current intended generic contract:**

```text
S1: configuration parser. C1: valid input returns the specified normalized result.
C2: invalid input returns the specified error without changing the input.
proof: the accepted parser check, using only S1 and accepted dependencies.
Later: S2 owns CLI process behavior.
Review this candidate from its recorded step-entry base. Run the same proof after a repair.
```

Proof execution, scoped assignment and re-proof are now implemented. The remaining acceptance review must inspect
what the output demonstrates, not merely whether a command exited zero.

**Remaining procedure improvement:**

```text
Before asking for confirmation, replay the inherited procedure from its actual starting state.
For every action, name the observable result and the actor who can observe it.
If the sequence cannot occur, send it back to its owner. If a required observation is unanswered,
leave it unverified; record exactly what the person's reply did establish.
```

These are illustrative prompt fragments, not literal runnable packets. Actual callbacks and result fields come from
the script. Package type changes the accepted check/actor/boundary, not this lifecycle.

## 5. Qualification catalogue

T1–T52 are stable plan references, not 52 newly implemented or passing tests. “Covered mechanism” means relevant
source/test machinery exists; it does not certify every original assertion or a live workflow. The specific six-suite
execution is reported in §7. Historical formulations and decisions remain in the archived plan.

| ID | Current acceptance target | Disposition |
|---|---|---|
| T1 | Missing step proof is refused by the real step-plan gate. | Covered mechanism; uses proof, not check. |
| T2 | Proof can run using only the current step and accepted dependencies; semantic vacuity is challenged. | Execution landed; semantic qualification remains. |
| T3 | Skills/cards resolve without a new cards_na form. | Old mandatory form superseded by lean port. |
| T4 | Reuse the correct example/design context without a new match field. | Old mandatory form superseded by lean port. |
| T5 | Per-step paths stay optional; item scope still applies. | Covered mechanism. |
| T6 | A failing inline proof refuses complete and produces an action-bound record. | Covered mechanism; selected suite passed. |
| T7 | Current evidence remains reviewable through summary/notes and proof receipts. | criterion_evidence gate superseded. |
| T8 | Head/full/Improve share step identity, proof and review base. | Covered mechanism; packet suite passed. |
| T9 | Only this step’s criteria and cases are quoted. | Covered mechanism; retain scoped-render tests. |
| T10 | Required assignment and the current loop-start route survive emission. | Old full-argument/last-block wording superseded. |
| T11 | Frozen criteria, served requirements and AD directions bind Work. | Covered mechanism; loop suite passed. |
| T12 | Contract rebuild and receipt recovery preserve the accepted assignment. | Covered mechanism; loop suite passed. |
| T13 | Code-only rubric/lint guidance follows actual applicability. | Retain applicability qualification. |
| T14 | Two relevant non-bookkeeping commits appear in the inline look-back. | Mechanism landed; no new history quota. |
| T15 | Library, CLI, service, UI, data/config/docs share a generic lifecycle. | Cross-package qualification remains. |
| T16 | Capture actual emit with long/multibyte fields under current bounds. | Use 19,500/20,000 head contract, not old 16,000 head target. |
| T17 | Current state-v9 requirements fail clearly on incompatible saved state. | Retain current migration/refusal contract. |
| T18 | Every required locator/ID resolves at the referenced revision. | Resolution and installed-path qualification. |
| T19 | One authoritative assignment per surface; no extra anchor form. | Covered shared-block design. |
| T20 | Consideration guide remains static and referenced by implement. | Old inline four-section extraction superseded. |
| T21 | Preserve the current shared Code craft rubric and its consumers. | Mandatory code-craft.md extraction superseded. |
| T22 | The actual duty/guide locator resolves; no invented Method heading. | Use existing resolver, not a new static_text API. |
| T23 | Built package contains the selected referenced guide. | No second reference file required by this plan. |
| T24 | All fourteen current rules reach applicable reviews; evaluate the three absent expansions separately. | Current rules implemented; CC3/CC6/CC9 expansion proposals unresolved. |
| T25 | Invalid transitions and invisible observations are rejected by the responsible reviewer. | Semantic review pilot remains. |
| T26 | A later-owned check may remain planned; a current required observation stays open. | Acceptance-boundary qualification. |
| T27 | Exact proof runs on the final candidate; wrong receipt cannot satisfy it. | Covered mechanism; semantic false positives separate. |
| T28 | Actor/entry/runner gaps retain their owner and due stage. | Preparation guidance landed; real-target qualification remains. |
| T29 | Changed procedure setup invalidates inherited observation claims. | Outstanding inherited-procedure fixture. |
| T30 | Return, target commits, lifecycle and review receipts remain separate claims. | Harness/source-return qualification. |
| T31 | Whole-plan ask-agent route keeps item checks without per-step proof. | Intentional and tested; not a missing mechanism. |
| T32 | Paired runs preserve quality before measuring reads, tokens and latency. | Deferred live comparative pilot. |
| T33 | Improve repair that breaks proof refuses import; unchanged receipt may be reused. | Covered mechanism; selected suite passed. |
| T34 | Inherited procedure review reaches final review/person ask without expanding case schema. | Outstanding narrow procedure work. |
| T35 | All surfaces honor the same granted probe route, target and limits. | Outstanding authority wording consistency. |
| T36 | Behavioral stub/source search cannot establish an executed behavior claim. | New confirm/test-layer gates help; semantic qualification remains. |
| T37 | Reject masked runner failures; qualify the deployed copy; distinguish the current nonzero-kill convention from behavioral proof. | Reporter defect reproduced. Target-copy qualification open; stronger kill classification is a separate design change. |
| T38 | A future remote mutation path restores accepted state on every ending. | Conditional: current local mutation excludes remote commands. |
| T39 | Reuse base/mutation verdicts only with complete identity and measured value. | Explicitly deferred by later cost/risk decision. |
| T40 | Unchanged-prefix reuse requires exact definitions and fresh relevant proof. | Deferred optimization; no empty-diff shortcut. |
| T41 | A revisited step names its own prior result/commit and narrow repair. | Per-step locator repair landed. |
| T42 | Rendered examples use proof/settle/due_stage, current callbacks and --notes FILE. | Update old examples; retain actual schema tests. |
| T43 | Required command/target facts survive locator-based heads; measure total reads. | Content/installation qualification remains. |
| T44 | Partial/no reply cannot silently remove a required consumer obligation. | Existing partial-reply tests; omission/continuity fixture still needed. |
| T45 | Claimed passes cite accepted runs, with distinct criterion/case/runner IDs. | Retain qualification; R08 can corrupt downstream pass evidence. |
| T46 | Already-staged candidate is reported present; no artificial absence. | Outstanding release-state wording and fixture. |
| T47 | Pending keep/exclude review remains explicit after a leftover commit; unignored tool state cannot silently return. | Ignore and return gates landed; wording fix and one adversarial fixture remain. |
| T48 | Keep policy, host terminal evidence and cleanup report their actual outcomes. | Current keep logic landed; live/harness qualification separate. |
| T49 | Stage backing state is run-owned and receipt recovery remains exact. | Outstanding directory argument and recovery fixture. |
| T50 | Guidance follows accepted package/runtime/surface facts. | Conditional module/platform guidance landed; diverse fixtures remain. |
| T51 | Changed relevant target/fixture/authority state invalidates existing reuse. | Qualification of existing reuse; broader cache remains a pilot. |
| T52 | Producer completion and first-trivial Improve remain distinct bound phases. | Use current gate zero versus one, not old gate two. |

## 6. Implementation sequence and boundaries

1. Add the failing T37 callback case and repair the candidate judge; verify it cannot feed false passed IDs into
   primary-outcome acceptance.
2. Run the narrow T29/T34/T44/T51 adversarial fixtures. Repair only the continuity, procedure or reuse boundaries
   they show are missing; close a recommendation when current enforcement already satisfies it.
3. Address the concrete P2 source deltas with their paired before/after acceptance procedures.
4. Measure optional Work shortening and replay optimization only after these correctness checks. Quality comes
   first, then actual token consumption, then latency.

Do not port the old integration branch wholesale, introduce a domain-specific lifecycle branch, create another
ledger, add a review quota, or reintroduce the rejected mandatory evidence forms. A later code change needs its
normal change note and relevant fail-first checks. This refresh authorizes no new live platform trial, release,
installation, commit or push.

## 7. Evidence and verification

The [current map](shiploop-implement-prompt-audit-evidence/reference-code-map-2026-10-25.md) and
[machine-readable map](shiploop-implement-prompt-audit-evidence/reference-code-map-2026-10-25.json) bind every
recommendation/consideration/rule to committed source. All 58 Chess and 91 Battleship gap entries remain mapped in
the [Chess index](shiploop-implement-prompt-audit-evidence/chess-analysis-disposition-2026-10-25.json) and
[Battleship index](shiploop-implement-prompt-audit-evidence/battleship-analysis-disposition-2026-10-25.json), with the
eight ranked Chess fixes retained. Repeated entries are not independent defects.

Six existing suites ran in the recorded working tree, with its pre-existing experiment edits, and completed with
exit zero: test-loop 165, step-packets 10, Improve changes 4, consumer delivery 32,
loops 56 and packet completeness 62: **329 tests**. All 5,715 tracked file hashes and the source revision stayed
unchanged during the suite run. The worker correctly returned **INCOMPLETE** for its broader workspace-output contract because nine
undeclared non-exempt experiment-sync files appeared during execution. Those files are outside the selected suite
and audit outputs; no attribution to the tests is asserted. The tests' successful results and this limit are both
retained in [the test receipt](shiploop-implement-prompt-audit-evidence/checks-2026-10-25/result.json).

A later local edit to `skills/shiploop/scripts/shiploop_lint.py` appeared during the documentation refresh. It was
preserved and is outside this committed-source audit and the completed suite evidence; the test receipt does not
qualify that newer working-tree change.

The focused suites do not contain the new zero-exit/failed-output scenario; the separate probe demonstrates the
remaining gap. No full suite, CI refresh, installed-host verification, live consumer acceptance or controlled
performance comparison was performed. Source/excerpt hashes, links, IDs and report mappings are checked by the
[reference validator](shiploop-implement-prompt-audit-evidence/validate-reference-map.py). Its
[result](shiploop-implement-prompt-audit-evidence/reference-validation-2026-10-25.json) is document/provenance evidence.
Visual rendering was not inspected; the earlier browser-policy denial was not bypassed.

The [independent Opus review](shiploop-implement-prompt-audit-evidence/opus-main-refresh-2026-10-25.md) completed
successfully as verified `claude-opus-5-5`, xhigh, no fallback. Adopted: the wider judge/primary/reuse impact,
release wording across all copies, optional status for Work shortening, and the narrower return-message fixture.
The legacy label on `--directory` does not by itself forbid the supported option on an already isolated receipt
call; test the actual route and retain fail-closed recovery rather than adding an automatic reset.
The coordinator owns the final classifications above; agent suggestions were corrected where they confused missing
code with unexecuted qualification, overlooked the actual primary gate, or proposed fields the lean port rejected.
