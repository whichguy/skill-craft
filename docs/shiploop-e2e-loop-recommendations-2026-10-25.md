---
Status: final verdict received (Astra at max, the owner's arbiter, 2026-10-25); cross-checked by DeepSeek Flash at max
Builds on: docs/shiploop-e2e-self-improving-loop-design-2026-10-25.md
---

# E2E loop recommendations, merged with their sources (2026-10-25)

**Sources:**
- **AM**: GPT-6 Astra at max effort, the answer that counts.
- **AX**: Astra at xhigh, two earlier answers, superseded by AM.
- **DM**: DeepSeek v4.1 Flash at max.
- **DH**: DeepSeek Flash at high.
- **IL**: the inner-loop session, from live notes on chess runs 5a and 5b.
- **ME**: this session's runner review (findings D1, E1-E5, S1-S6).

**V** means this session checked the claim against the code or records, and the note says what it found. **Lean** is this
session's provisional view, before the final verdict.

## A. The objective and the scorecard

**R1. Quality gains must be promotable.** Epoch step 7 promotes only when "floors hold and the target improves". That
rejects a slower change that finally delivers correct code.
- Separate the established regression requirements from capability cases still being improved.
- Promote demonstrated quality gains with their costs stated; compare tokens, then time, only when quality is equal.
- First step: three decision examples (a slower correctness fix, a faster regression, an inconclusive optimisation),
  where the rule accepts only the first.

Sources: AM1, AX2. V: design "The loop", step 7. Lean: accept.

**R2. Missing evidence never passes.**
- Mark each part required, not applicable, unobserved, pass or fail. Missing required evidence means no promotion
  decision.
- Use an expected-slice manifest, so `arms.py` cannot silently compare only the common slices.
- Amend SPEC's "record, never a verdict" policy before quality or fidelity gate a promotion.

Sources: AM2, AX3. V: `accuracy.floor` is true when acceptance is unobserved; `comparable` is true when validity is
unobserved; `arms.decide` uses `set(control) & set(candidate)`. Lean: accept.

**R3. Split validity into correctness, attribution and timing.**
- Overlap and resume void timing only.
- Mixed builds void attribution.
- A check that mutated the product voids the affected verdicts and the mutation measure.

Sources: AM2 and AM18, AX, DM1, DH3. V: one `comparable` flag today. Lean: accept.

**R4. Take refusals and Improve children out of the efficiency target.**
- They are quality mechanisms, and minimising them rewards reviewing less.
- The target becomes cost (tokens where measured) per passing case, compared within a case.
- Add tokens: the scorecard has none.

Sources: DH (section 2), AM8. V: `efficiency` includes `refusals` and `improve_children`; no `tokens` field. Lean: accept.

**R5. Mutation in the accuracy floor where a case declares it.** It is a non-regression against the control or base
ratio, never an invented absolute. A timeout counts as unobserved, not as a failure. Sources: DM4, DH4, AM3 (keep the
timeout caveats). V: mutation is descriptive. Lean: accept.

**R6. Record delivery identity at delivery, before any check.** Record the commit, a content hash, and the grader and
case versions. Checking `git status` afterwards misses a later committed alteration and cannot be repeated after teardown.
Sources: AM6, AX3. V: `scorecard.work_tree_after` reads the live tree. Lean: accept.

## B. Oracles and the corpus

**R7. Calibrate oracles before expanding the corpus.** Each oracle keeps:
- a known-correct implementation;
- targeted broken variants (missing authorisation, malformed CSV, lost persistence, incorrect concurrency);
- valid alternative implementations, which must pass.

"Accepts the saved real deliveries" (E2b) is not enough, because a saved delivery can be wrong. Hide test instances, not
requirements.

Sources: AM3, AX1, DM4, DH1. V: the E2b method used saved deliveries only. Lean: accept; redo E2b with a reference and
broken variants.

**R8. Every release gate includes at least one oracle-strong case.** hello, seat-reservations and csv-report declare no
quality block. Sources: DH1. V: there is no `quality` key on those three. Lean: accept (DH's "only" is too strict).

**R9. Harness self-tests.** Planted bad deliveries per suite must fail, and every reader has a fixture test. Sources:
DH10. ME: E2, E4, the stale `improve_reviews` reader. Lean: accept.

**R10. Brownfield pilot on three bases.**
- The existing `node-base`: extend user filtering and pagination; check API compatibility and boundary inputs.
- A new human-authored Python CLI: streaming CSV transformation; check golden outputs, malformed input, exit codes and
  bounded memory.
- The pinned Flask tutorial (pallets/flask examples/tutorial): owner-only export, and separately a schema migration; check
  cross-user denial, quoting, the existing tests, and an upgrade of a populated database.

Grade fail-to-pass and pass-to-pass, SWE-bench style. The base's pristine tests run independently of the candidate's
test edits. Rubric items are commands: clean install, actual CI execution, lint and types, restart persistence,
migration data preservation, documented commands. Report the limitation; claim no universal enterprise readiness.

Sources: AM4, AX4, DM8, DH (section 3). Lean: accept, one Node case first.

**R11. Generalisation is independent coverage, not three pool names.**
- Split by repository or task family.
- The canary is a dev regression subset, and it is the existing batch gate.
- Move inspected holdout failures into dev, and replenish by exposure count, not quarterly.
- Correct the design's claim: `held_out_seen=0` does not prove there was no leak.

Sources: AM5, AX5, DM5. V: `quality.py`'s note says "0 is not proof". Lean: accept, and fix the design text.

**R12. Do not make the share of requirements marked `primary`, or the presence of commit-message lines, a target.**
They reward relabelling and paperwork. Sources: AM3, AX10. Lean: accept; scorecard/2 records them as diagnostics only.

## C. Promotion, the epoch and the improver

**R13. Freeze the evaluator separately from the candidate.**
- `iterate.py` allows all of `test/`. Use explicit permitted paths: `skills/shiploop/`, its tests, `changes/shiploop/`.
- Record the evaluator, oracle, case and candidate hashes.
- Harness and oracle changes are separate experiments.

Sources: AM7, DM6, AX10. V: `ALLOWED_PREFIXES = ("skills/shiploop/", "changes/shiploop/", "test/")`. Lean: accept.

**R14. The control arm is the last released commit, built the same way as the candidate.** Sources: DM2. Lean: accept.

**R15. Staged evidence, not blanket n=2 and A/A.**
- Screen with a replay or one affected slice. Repeat promising or ambiguous candidates in serial, alternating order.
- Count every launched attempt toward cost, including stops and resumes.
- A failing batch needs dev-side ablation.
- A/A is a warning about variability, not confidence.

Sources: AM8, AX8, DM3, DH (section 2). V: `arms.py` decides on bytes, never time. Lean: accept.

**R16. One pre-registered promotion rule and primary metric per candidate.** It ends as promote, drop or undecided.
Sources: DM3, DH. Lean: accept, together with R1, R2 and R15.

**R17. Build one usable epoch before reviving the automated campaign.**
- One manifest per epoch: finding → hypothesis → experiment → candidate → post-change result → disposition.
- One maintained controller.
- Separate checkout qualification before publication from marketplace verification after it.
- Defer P4. Its admission needs evaluator independence and a bad candidate it rejects, not "two hand-picked winners".

Sources: AM9, AX10. V: `iterate.py` stops on two clean reviews, and can end on an improvement only the quick tier saw.
Lean: accept.

**R18. Replace `iterate.py`'s "two clean reviews" stop with script-decided outcomes.** Sources: DM (section 2), AM9.
Lean: accept, folded into R17.

## D. Setup and teardown

**R19. Separate process cleanup from evidence disposal.**
- Stop owned processes at termination, by recorded owned groups, never by process name.
- Record owned ports, data directories and platform resources.
- Keep the delivery's identity, logs and a recoverable archive.
- Delete heavy artifacts asynchronously after inspection.

Sources: AM6, AX6, DM9. ME: the run-5 orphan watcher. Lean: accept.

**R20. Preflight reserves conflicting ports, platform state and exclusive timing resources, and refuses orphans and a low
disk.** Timing isolation covers shared machine and provider contention, not only identical drivers. Sources: AM6, AX6,
DM9, DM (section 4: under 10 GB). ME: E1. Lean: accept.

## E. Live triage

**R21. Compute live facts every 60 s in shadow mode first.** The facts: incremental events, accepted transitions,
normalised refusal and action identities, relevant tree changes, active tool deadlines, owned process identity, session
recovery, remaining budget. Missing records mean unknown. Replace the `events.jsonl` mtime signal. Emit
`{action, reason, evidence_refs, invalid_dimensions}`, replayable, and never run product checks as monitoring. Sources:
AM15, AX (section 7, item 1), DH (section 7: 60 s). Lean: accept.

**R22. Stop immediately only on established fatal conditions:**
- a required prerequisite is demonstrably unavailable, with no permitted in-run recovery (IL: Grok auto mode refused the
  deploy);
- the host has exited and the existing recovery failed (IL: after the laptop sleep);
- the harness cannot preserve evidence;
- SPEC's CI or earlier-gate cancellation applies.

A denied platform action is not automatically a defective guard. Sources: AM16, AX, IL. Lean: accept.

**R23. Text and silence thresholds trigger WATCH, not a kill.** Three repeated refusals for the same action, input and
state, or 15 minutes without events, mean WATCH. At 30 minutes, inspect the pending tool deadlines and the recovery
state. Stop only on a confirmed expired operation, or an unchanged cycle that persists after a documented recovery
opportunity. Sources: AM17, AX, DM (section 4). It conflicts with IL, which treats three identical refusals and 15 min
silence as fatal. Lean: AM, provisional until a replay.

**R24. A version change.** An on-disk change is not fatal; establish whether the running process changed. Mixed actual
builds void attribution. An interpreter swap that will crash the harness itself is fatal (IL: run 5a). Sources: AM18,
AX, DM (section 4), IL. Lean: accept, keeping IL's harness-crash case.

**R25. Finish when useful endpoints survive, and invalidate only the affected claims.**
- Fixed refusals, send-backs and converging reviews finish.
- Sunk cost never enters the decision.
- Keep the authorised cap; capped runs are recorded failures to complete.

Sources: AM18, AX, DM (section 7), DH (section 7). Lean: accept.

**R26. Fresh runs for changed execution behaviour; resume unchanged runs for recovery evidence.**
- Reader-only repairs may reprocess preserved records at once.
- Engine, packet, oracle or execution-affecting harness fixes need a fresh confirmation.
- Record before and after identities for every intervention.

Sources: AM19, AX, DM, DH. Lean: accept; it refines the 09-27 batch rule's "certain not to affect planning".

## F. The judge (Opus, rubric-eval)

**R27. The judge is an adviser with three consumers:**
- triage, for borderline WATCH incidents only;
- the findings list, after runs;
- find and rank, for mechanisms, evidence and the cheapest refuting experiment.

Its output is `finding, evidence, uncertainty, suggested_check`. It never decides pass, a floor, a stop or a promotion. A
model score processed by Python is still model judgement under S-9. Sources: AM11, AX, DM (section 6), DH (section 6).
Lean: accept.

**R28. Model judgement only for semantics that remain unspecified:** architectural appropriateness, unnecessary
complexity, and requirement-to-evidence relevance. Mechanise test execution, component identity, freshness and declared
permission failures. Turn semantic findings into checks where possible. Sources: AM13. Lean: accept.

**R29. Calibrate truth separately from repeatability.**
- Label 30-50 criterion judgements: false passes, false failures, honest blockers, unsupported claims.
- Blind them, swap the pair order, and include identical artifacts and formatting-only variants.
- Recalibrate whenever the model, prompt or effort changes.

The draft's κ=0.914 measures repeatability, not truth. Sources: AM14, AX, DH. Lean: accept.

**R30. Repair the draft judge suite's evidence provenance before trusting its scores.** This is another session's
uncommitted `skills/rubric-eval/suites/shiploop-run/`.
- Label script observations versus model assertions.
- Include bounded cited contents.
- Pair by run and replicate identity, not by position.

Sources: AM12, AX. Lean: accept, but it is the owning session's to make; send it there.

## G. Cost, cadence and driver

**R31. Footprint-based cadence:**
- replay and targeted checks per change;
- smoke plus the affected slices per candidate;
- marketplace breadth and follow-on per behavioural release;
- other-host smoke on host or protocol changes, on a rotating schedule;
- full chess only for relevant cross-item or hosted changes, or scheduled coverage.

Sources: AM10, AX9, DM10, DH (section 5). Lean: accept.

**R32. Pilot Sonnet as the economical development driver.** The "10× faster" claim is not established, because the runs
overlapped. Sonnet results cannot establish Grok behaviour. Sources: AM10, AX9, DM10. Lean: accept the pilot. The owner
now directs Grok 4.7 medium for the current runs.

**R33. Cap gate runs by minutes, stopping at a stage boundary as a budget stop, and slice the long hosted case.**
Sources: DH6. Lean: an owner decision.

**R34. A live hello run as a blocking step in `release.py`.** Sources: DH5. Lean: reject. It conflicts with "proceed
optimistically" and the release flow; the release-gate line plus practice covers it.

**R35. A failure taxonomy (packet, script, model, environment, case or oracle, harness) for every non-pass, as a script
first, with the model only for the residue.** Sources: DH7. Lean: defer until P3 has one epoch.

## H. From inner-loop, kept as scorecard/2 diagnostics

**R36.** Prepare's harness_runs evidence shows a test result line. Sources: IL. Lean: accept, as a check.

**R37.** Send-backs per item and their rework minutes; Improve passes per review, now that 2.9.1 fixed the reader.
Sources: IL. Lean: accept, as diagnostics.

**R38.** Active against wall time, interpreter swaps and sleep gaps, in validity. Sources: IL, AM18. Lean: accept, with
R24.

## Final verdict (Astra at max, 2026-10-25)

The arbiter was GPT-6 Astra at max effort (`model_used: gpt-6-astra`, profile consult, read-only, fallback false). It ran
read-only probes and changed no files. The cross-check was DeepSeek v4.1 Flash at max. The tally: 10 ACCEPT, 27 MODIFY,
1 REJECT.

| Item | Verdict | The amendment, in Astra's words, condensed |
|---|---|---|
| R1 | ACCEPT | Promote demonstrated quality gains without established regressions; keep the authorised budgets, then compare tokens and time. |
| R2 | MODIFY | Separate case-owned requiredness and applicability from pass, fail or unobserved; require every registered slice **and required field**, validity included. |
| R3 | MODIFY | Separate the dimensions, but overlap can also corrupt shared state, and changed resume inputs can void attribution or correctness. |
| R4 | MODIFY | Refusal and review counts are diagnostics; remove the refusal hard gate in `arms.py` too; measure all-attempt tokens per successful case. |
| R5 | MODIFY | Gate only comparable, calibrated fault sets; infrastructure timeouts and incomplete coverage are unknown; a confirmed mutant-specific hang may count as a kill. |
| R6 | ACCEPT | Capture delivery content and evaluation identities before checks, so grading reproduces after teardown. |
| R7 | MODIFY | Extend E2b with independently correct implementations, alternatives and targeted defects. It already has a negative control. |
| R8 | MODIFY | Require calibrated coverage of the affected requirements and styles; one unrelated strong oracle cannot qualify a release. |
| R9 | MODIFY | Fixtures first for decision-bearing readers and planted failures; other readers when touched, not a blanket campaign. |
| R10 | ACCEPT | Node first; keep the pristine regressions, and require the feature's failures to become passes. |
| R11 | MODIFY | Count all holdout feedback, aggregate decisions included, as exposure; partition by repository or family; retire inspected cases. |
| R12 | ACCEPT | Relabelling and commit-message presence are diagnostics, never targets. |
| R13 | MODIFY | Freeze grading outside the candidate's control: evaluator tests out of edit permissions, holdout data out of model access. |
| R14 | MODIFY | Pin the epoch's release baseline; compare an incremental edit with its qualified parent, and the final batch with that baseline. |
| R15 | ACCEPT | Stage the evidence, keep every attempt, and confirm promising changes; A/A differences are descriptive variability. |
| R16 | MODIFY | Pre-register quality-equivalence criteria, the primary target, the required coverage and the stopping rule; one metric cannot override quality. |
| R17 | ACCEPT | One complete, auditable epoch before automation; rejecting a bad candidate is essential admission evidence. |
| R18 | ACCEPT | Inside R17's single controller; every final candidate needs a post-change evaluation. |
| R19 | MODIFY | Record process creation identity beside the groups; make cleanup idempotent; keep restorable evidence before disposal. |
| R20 | MODIFY | Lease controlled resources atomically; observe provider contention rather than claim exclusivity; size the disk headroom to the workload. |
| R21 | ACCEPT | Passive, incremental facts and replayable shadow decisions. |
| R22 | ACCEPT | Confirmed unrecoverable conditions justify a stop; a permission denial alone does not establish a harness defect. |
| R23 | MODIFY | **WATCH, not a kill.** Three refusals or 15 minutes of silence trigger WATCH and an immediate inspection. An expired tool alone is not enough: stop needs exhausted recovery or an authorised deadline. |
| R24 | ACCEPT | Actual execution identity governs attribution; an established unrecoverable harness failure permits termination. |
| R25 | ACCEPT | Keep usable endpoints; capped attempts stay recorded as non-completions, with their costs included. |
| R26 | MODIFY | After a reader or post-delivery oracle repair, regrade both sealed arms; regenerate only when execution or generation was affected. |
| R27 | ACCEPT | Judge findings propose checks; executed evidence decides acceptance, stopping and promotion. |
| R28 | MODIFY | Model advice for non-mechanisable semantics, specified or not; ambiguity cannot silently redefine requirements. |
| R29 | MODIFY | 30-50 independently labelled examples are a pilot; report error counts and keep order and style controls. |
| R30 | MODIFY | Get the owning session's artifacts before verifying the alleged defects; fix provenance and identity pairing before using scores. |
| R31 | MODIFY | Test every affected host or protocol at once; rotate unaffected coverage; keep scheduled full-case probes. |
| R32 | MODIFY | **Defer the Sonnet pilot; use the owner's Grok 4.7 medium now**, then evaluate drivers in matched quality and token trials. |
| R33 | MODIFY | Keep the authorised hard deadline; graceful stage-boundary stops fit inside it; slices cannot certify full completion. |
| R34 | REJECT | Keep live execution outside `release.py`; the controller owns qualification and post-publication verification. |
| R35 | MODIFY | Minimal script-observed failure-layer and unknown tags now; defer causal attribution, allowing several contributors. |
| R36 | MODIFY | Script-executed receipts bound to the expected component and revision; a test-result string alone proves nothing. |
| R37 | MODIFY | Keep the diagnostics, but verify the claimed reader fix on fixtures, and don't double-count nested review and rework time. |
| R38 | MODIFY | "Active" means measured session time; record suspend gaps and the clock basis separately, without inferring productivity. |

### Corrections to the merge, checked by this session

- **R7's "V" was wrong** (Astra, DeepSeek). The method already had negative controls:
  - E2b rejected the audit server;
  - `BattleshipGameCheckTest` has a correct stub and seven broken ones;
  - Checkers has `reference_checkers.py --defect`.

  Missing: independently correct alternative implementations, plus oracles for csv-report and seat-reservations.
- **R2 and R4 understate the defects** (Astra). Its probes reproduced a candidate win with a missing slice and missing gate
  fields, and a rejection caused solely by one extra refusal (`arms.py` gates).
- **R5 changes measurement semantics** (Astra, DeepSeek). `quality.py` counts a mutant timeout as killed (checked:
  `killed += 1`, then `if result["timeout"]: timeouts += 1`). A phase ceiling can leave a partial ratio, and equal
  operator ids do not mean equal mutant populations. So it needs a new operator id.
- **R8 is bigger than stated** (DeepSeek). 10 of 12 cases carry no quality block, including the batch gate `hello`.
- **R23's fatal-three rule would contradict SPEC** (Astra). SPEC allows eleven refused check runs before revision or
  blocking.
- **R29 and R30 are one item** (DeepSeek). κ=0.914 exists only in another session's uncommitted `judges.json` (checked).
- **R17 and R18 merge, and R16 merges into R1 and R15** (both). **R33 splits** into budget policy and case slicing
  (Astra). R7 and R9 share calibration fixtures (Astra).
- **R4 should reuse the existing token readers** (DeepSeek, checked: `metrics.context_tokens`, `metrics.planning_tokens`).
- **R22 amends the design's triage row 6** (guard denied → fatal) and should say so (DeepSeek).
- **DeepSeek errors, checked and rejected:**
  - "2.9.1 does not exist": it read a pre-release worktree, and origin/main is 2.9.1 then 2.9.2.
  - "`quality.py` never says 0 is not proof": its note does say so, beside a docstring that says "0 is a measured none".
- **Attribution:** Astra notes that the source tags cannot be authenticated without the original response envelopes. The
  raw replies are kept in this session's scratchpad (`astra-*.json`, `deepseek-flash-*.json`).

### Omissions

- **Astra:**
  1. Freeze the mapping from user requirements to independent checks before generation, so candidate-authored specs cannot
     shrink success.
  2. Bind qualification to the exact published artifact digest. Later edits void it, and a failed post-publication
     verification needs a recorded withdrawal or fix.
  3. A longitudinal brownfield holdout: successive features over populated data, including upgrade and recovery.
- **DeepSeek:**
  4. A promotion path when no A/A spread exists: `arms.decide` exits 3.
  5. Oracle read access, not only edit access. The improver's worktree can read `checks/`.
  6. An epoch spend ledger.

### Build order (Astra; "done" means a recorded script-run check)

| Step | Deliverable | Depends on | Done when |
|---|---|---|---|
| 1 | R1/R16: the promotion contract and its SPEC amendment (**built 2026-10-25**: `promotion.py`, SPEC "The promotion contract") | — | A slower correctness fix promotes; a faster regression drops; an inconclusive optimisation stays undecided |
| 2 | R2/R3: required evidence and separate validity dimensions | 1 | A missing slice or field blocks promotion; timing contamination keeps independently valid correctness evidence |
| 3 | R13: the evaluator boundary | 2 | A candidate cannot modify grader inputs or read protected holdout instances; the hashes stay unchanged |
| 4 | R6: the delivery snapshot | 3 | A later committed alteration is detected; an archived delivery reproduces grading after teardown |
| 5 | R7/R9: calibrate one existing oracle | 4 | Correct and alternative implementations pass; each targeted broken variant fails |
| 6 | R10: one Node brownfield case | 5 | The base fails the new-feature checks; the reference passes them and the pristine regression suite |
| 7 | R19/R20: the minimal resource lifecycle | 4 | A conflicting lease is refused; crash-and-retry cleanup works without touching unrelated processes; evidence survives |
| 8 | R4/R15: attempt and token accounting | 2, 4 | Totals reconcile stops and resumes; unknown tokens cannot produce a claimed token win |
| 9 | R8/R11: the coverage and exposure manifest | 3, 5, 6 | Missing affected coverage blocks qualification; inspected holdouts move to dev; families stay separated |
| 10 | R17/R18/R35: one epoch in one controller | 1-9 | A known-bad candidate is rejected; the final candidate is evaluated; disposition, failure evidence and publication status are recorded |

Then shadow triage (R21-R23). Judge expansion (R27-R30) and P4 wait.

**Astra's summary:** "The amended design can produce measurable self-improvement for greenfield and brownfield work, with
credible evidence of transfer across the families actually tested. Enterprise generalisation remains an empirical claim
requiring broader and longitudinal coverage. The biggest remaining risk is optimising incomplete oracles: a perfectly
deterministic controller can repeatedly promote software that passes its checks while missing the user's real
requirements."

