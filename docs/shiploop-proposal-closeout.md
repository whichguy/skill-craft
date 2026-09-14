# ShipLoop proposal disposition and historical closeout

Baseline: `8b98d57`, 2026-09-13. Scope: previously proposed ShipLoop work,
not a new architecture or live deployment. Unrelated Review Coverage changes
are excluded. Status: completed in `b391c74`; both remaining packet clarifications
were implemented. The validation below is that increment's historical evidence,
not a fresh verification claim for every later revision.

**User clarification during closeout:** total packet character counts are
readability guidelines, not hard limits. That supersedes the earlier size-gate
assumption in this audit and the older packet-orientation audit. Required
context, clear language and safety take priority over hitting a count.

## How to read the completed proposal records

Disposition review baseline: `42f815d`. Use the
[operator README](../skills/shiploop/README.md) for current workflow instructions.
The records below retain the original decisions, rejected alternatives, failures,
test counts and limitations. Original "Adopt", "implement" and "proposed" wording
inside a completed record is historical, not an instruction to repeat the work.
Source line offsets and temporary evidence paths belong to the recorded revision;
they are not maintained current-tree pointers or a promise that temporary files
still exist. Named source symbols and current operator guidance are the way to
investigate present behavior.

| Record | Completion or maintained purpose |
|---|---|
| [Initial 0.9 validation](shiploop-0.9-validation.md) | `68324cf`: original Markdown/evidence-gated protocol validation. |
| [Single-action objective plan](shiploop-universal-plan.md) and [HTML implementation summary](shiploop-implementation-report.html) | `0591ce0`: completed design and historical verification, not a live run certificate. |
| [Task-local test refinement](shiploop-test-refinement-plan.md) | `7e4211e`: test planning and post-code refinement duties. |
| [Local microplans](shiploop-local-microplan-plan.md) | `3f79978`: local execution breakdown and bounded prerequisite review. |
| [Remaining recommendations](shiploop-remaining-recommendations-plan.md) | `f47dcfa`: R1–R6/R10–R11 completed; R7–R8 preserved; R9 not adopted. |
| [Quality corrections](shiploop-quality-review-plan.md) | `2153514`: Q1–Q7 completed. |
| [Simplicity plan](shiploop-simplicity-plan.md) and [quality closeout](shiploop-quality-review-closeout.md) | `c548bc9` / `ac6cb43`: constitution and follow-up recovery/regression work. |
| [System context and artifact plan](shiploop-system-context-and-artifact-plan.md) | `414b3e9`: context, artifact readers, observations and outer-work/handoff gates. |
| [Until-Loop refresh](shiploop-until-refresh-plan.md) | `82dbfe2`: selective, validated safeguards; not automatic upstream synchronization. |
| [Packet orientation audit](shiploop-packet-orientation-audit.md) | `73933af` / `115240e`: orientation and complete phase-reference routing; pilot limitations retained. |
| [Packet teach-back guide](shiploop-packet-teachback.md) | `291e0e5`: implemented maintainer probe and reusable instructions. Its pilot remains exploratory, not universal semantic certification. |
| [System-test sequencing](shiploop-system-test-plan.md) | `8b98d57`: catalog, prerequisite ordering and final evidence closure. |
| This closeout | `b391c74`: local-loop/terminal distinction, historical reader placement and advisory packet counts. |
| [Script-enforcement map](../skills/shiploop/README.md#script-enforced-state-machine) | `42f815d`: documentation and real-CLI traversal proof, with 100 targeted passing tests at that increment. No runtime rewrite. |
| [Research-pilot fixes](shiploop-research-pilot-closeout.md) | Implemented follow-up to the two-scenario pilot: version-correct research packets, safe system-context enum errors and decision guidance. Retains the experimental wording and live-target replication as deferred. |
| [Recursive discovery and iteration handoff](shiploop-recursive-discovery-plan.md) | `eca2d3c`: recursive discovery, safe question continuation, and the per-Improve documentation/reuse action; implemented and validated without a live target claim. |

Do not reopen completed proposals merely because their historical filename ends
in `-plan.md`. Deferred ideas in the ledger below remain deferred; new findings
need current evidence and their own scoped decision. Compatibility/migration
paths and regression fixtures are still consumers of completed work, not
disposable proposal scaffolding.

## Disposition ledger

| Proposal group | Current disposition and evidence |
|---|---|
| One-action interface, Markdown authority, HTML completion report | Implemented: `shiploop_delivery.py:220`, `shiploop-action-walk.test.py:2077`. |
| Ready/Done, local microplans, nested and product Until cycles | Implemented: README local-microplan section; `shiploop-step-planning.test.py:268`. No second scheduler needed. |
| Seven full Git bodies, learned-plan traceability, hostile-history handling | Implemented: `shiploop_history.py:208`, `shiploop-history-pages.test.py:71` and `:430`. |
| Generic platform/environment discovery, security/fuzz and maintenance decisions | Implemented: `shiploop_discovery.py:256`, `shiploop_risk.py:334`. Actual scheduled maintenance needs a selected product and authorized producer; no generic updater is installed. |
| Historical quality review and merge/migration recovery | Implemented/superseded: `shiploop-quality-review-closeout.md`; `shiploop-merge-recovery.test.py:167`, `shiploop-migration-prompt.test.py:129`. |
| KISS/YAGNI constitution and test-plan/refinement duties | Implemented: README current-controls section; `testing-and-documentation.md:19` and `:65`. A universal handler refactor remains deliberately deferred without a demonstrated need. |
| System context, artifact readers, observations and outer-work journal | Implemented: README artifact inventory; `shiploop_system_context.py:198`, `shiploop-system-context.test.py:290`. |
| Global system-test requirements, prerequisite ordering and evidence closure | Implemented in `8b98d57`: `shiploop_system_tests.py:181`, `shiploop-system-tests-protocol.test.py:333`. |
| Validated Until-Loop safeguards | Implemented: `shiploop-until-refresh-plan.md`; exact prompt, literal transport, filesystem and cold-context regressions. No standalone runtime or second authority. |
| Original orientation audit and reference routing | Implemented in `73933af`/`115240e`; their audit closeouts distinguish historical findings from current behavior. |
| Teach-back: loop exit versus whole-run completion | **Closed here:** the owning-loop label and adjacent terminal/report boundary now appear in converging packets. See `shiploop-loop-scope.test.py`. |
| Teach-back: historical-quality reader placement | **Closed here:** the existing reader precedes the quality summary and explicitly says to read it first, without promoting history to current proof. See `shiploop-loop-scope.test.py`. |
| Packet character counts | **New clarification applied here:** total-packet size checks are advisory diagnostics. Paging, input validation and sensitive-data projection limits remain enforced. |
| Script-enforced traversal | Completed in `42f815d`: explicit README gate/branch map, cold resumes, invalid callback refusal and history-backed end-to-end traversal assertions. |
| Universal semantic oracle, legacy-history reconstruction, vendor integrations, live-host certification | Intentionally deferred/rejected, not unfinished approved features. Missing evidence stays unknown; external operations require specific targets and authority. |

## Prompt audit and decisions

### Q1 — Does satisfying Until finish the delivery?

**Info-gain: 0.95.** This resolves the most consequential observed confusion.
At baseline, the shared cycle said “current stage only” and the renderer
presented an unqualified `Until` predicate.
The skill card correctly reserves success for a terminal message with report.
The original pilot and a new baseline plan response conflate those levels.

**Answer:** label the cycle's owning loop, qualify its local exit, and put the
whole-run terminal condition immediately beside it. Preserve every transition,
callback, convergence gate and permission boundary. Do not make the host predict
future stages or treat an example terminal phrase as an actual terminal response.

### Q2 — Should prior quality evidence be mandatory current proof?

**Info-gain: 0.90.** The existing reader is correct but was omitted by another
fresh review reader. At baseline, `_quality_orientation_lines` placed a passive
reader label after the summary. Its availability is already origin-bound.

**Answer:** move the existing bounded reader before that summary and explicitly
say to read it first. Preserve its historical-only status and omit it when no
initial locator exists. Do not invent missing assessments, add read receipts,
or load complete histories into the packet.

## Remediation and validation plan

| Priority | Change | Evidence required |
|---|---|---|
| HIGH | Distinguish local Until from terminal delivery next to the loop predicate. | All converging families retain exact callback/state behavior and explicit terminal/report authority. |
| HIGH | Move the available historical reader before the quality summary. | Real CLI reader works, unavailable provenance stays unavailable, no cursor advance, no blocked callback. |
| MEDIUM | Reconcile this ledger and the teach-back guide with current status. | Retain old observations as historical; document new evidence without claiming general model reliability. |

The approved plan was to write failing regressions, apply the smallest
renderer/helper edits, measure packet size, synchronize the derived plugin and
review. Native Python suites were selected rather than illustrative npm commands
(this repo has no npm test package). ShipLoop was the contract under maintenance,
not a self-modifying delivery run. The validation below records execution and
the later change from strict packet counts to advisory guidance.

The teach-back wrapper and seven-criterion rubric were held fixed for the pilot.
Real baseline/candidate packets, fresh readers, repeated active cases and a
paused hold-out supplied supplemental evidence. Answers were graded, never
executed; these trials did not replace deterministic runtime safety tests.

## Evidence-first and interoperability decision

Adopt these two inexpensive presentation changes: local tests and the pilot's
two target criteria support them. They address reproduced navigation/completion confusion
without a new state model, provider, dependency or permission. The contrary
risks are packet growth, over-reading old evidence, and overfitting the rubric.
Treat total-packet size as guidance, retain actual safety/paging limits, and
preserve UNKNOWN for missing evidence.

Primary guidance supports repeated trials, calibrated graders, and separating
reported intent from observed outcomes: [Anthropic evaluation guidance](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
Selective references with useful metadata support the small-context approach:
[Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).
Neither source proves these exact packets work; local traces are decisive.

ShipLoop remains script-backed and host-neutral: one CLI, script-selected
transitions and Markdown state, thin skill card, canonical package plus derived
plugin. Grok/Codex paths were verified as canonical symlinks. No other host
installation or runtime was certified, refreshed, or silently substituted.

## Validation closeout

### Runtime and packaging

The production runtime changes are presentation-only. They change neither `decide`, state
schemas, transactions, callbacks, permissions nor convergence ownership. The
embedded Until policy still requires verified, uniquely audited completed
passes; the renderer clarifies that readiness is not terminal delivery.

The first immutable snapshot (`d660eaa`) passed 123 targeted tests but failed
the actual cold-planning packet bound at 7,042 characters. Redundant wording
was shortened, not the limit. Snapshot `4a3f091` passed 125 distinct tests:

| Suite or selector | Passed methods |
|---|---:|
| Protocol | 34 |
| Packets | 36 |
| Until policy | 10 |
| New loop-scope regressions | 3 |
| Orientation | 14 |
| Historical quality context | 8 |
| Public-CLI orientation integration | 4 |
| Phase reference routing | 5 |
| Teach-back probe | 9 |
| Actual cold planning / legacy repair selector | 1 |
| Actual cold nested step-planning selector | 1 |
| **Total** | **125** |

Independent review then found that the synthetic long-path orientation test
stubbed out the lifecycle. Its new assertion failed before the helper was
corrected; the strengthened test then caught a 7,081-character nested-plan
packet. Shortening redundant nested/legacy wording restored the same 7,000
limit in the primary checkout. Snapshot `0f79126` then exposed that the synthetic
fixture's installation path grew with the checkout directory (7,211 characters),
while both actual cold CLI selectors passed. Fixing only the synthetic package
path made its layout independent of the checkout. Snapshot `7dbdd24` passed all
125 targeted methods.

The final review also requested restoring explicit open findings in the
continuation line, rather than relying on “proof is incomplete” plus adjacent
Until gates. The added assertion failed for all five tested converging families
before the wording was fixed. Snapshot `3b2e8f1` passed 124 methods but its
cold-planning size gate failed at 7,010 characters. Snapshot `b1e3c0b` passed all
125 after further wording reductions. These size failures and reductions are
historical diagnostics, not the desired long-term quality policy.

The user then clarified that character counts should be guidelines. Total
packet/prose size assertions now emit non-failing diagnostics, while bounded
data projections, history/context pages and validation safeguards remain hard
checks. Full, readable planning/legacy descriptions were restored. The final
continuation wording explicitly says that open findings or missing required
proof keep the loop active; only the actual terminal response with achievement
report ends the run. The tests retain all semantic and callback assertions.
Final immutable snapshot `963af51` passed **126 distinct targeted methods**:
the same suite/selector inventory above, with orientation increased from 14 to
15 by the direct oversized-advisory regression. Both actual CLI selectors pass:
cold behavior planning measured 7,139 characters against a 7,000 guideline,
and cold nested planning measured 14,044 against 14,000. Those are diagnostic
measurements, not failures; all semantic and evidence assertions still run.
The additional ten-method history-paging suite also passed on that snapshot,
bringing final targeted coverage to **136 distinct passing methods**. This
separately verifies the preserved enforced paging behavior.

Independent final review found no actionable issue in the runtime, advisory
helper, retained hard bounds, or canonical/package parity. The final commit
differs from this tested snapshot only in audit closeout prose.

This is targeted regression coverage, not a full-suite, live-host execution or
deployment certification. Suggested packet sizes are not runtime caps, token
counts, or substitutes for semantic review. A packet above a suggestion can be
correct; a short packet missing context or safety instructions is not better.

Scoped Ruff, native metadata validation for 17 skills, shell syntax, 127 local
link destinations across five Markdown files, balanced fences, scoped plugin
parity and diff checks passed. No changed diagram required rendering.
The generic skill validator could not start because PyYAML is unavailable.
No dependency was installed to conceal that limitation.

### Fresh-context comprehension pilot

The existing wrapper and seven-criterion rubric were held fixed. Real public-CLI
packets were captured at baseline and after the two proposed changes, with no
edited packet fixtures. This candidate precedes the final explicit open-findings
clarification and readability/advisory-size edits; those final adjustments
have deterministic and code-review coverage, not another fresh-reader trial.
Nine fresh, isolated readers each received only one prompt: two
baseline trials, three candidate review trials, three candidate planning trials,
and one paused candidate hold-out. Replies were not executed. All nine passed
mechanical identifier/path/callback checks; that result remains
`NEEDS_SEMANTIC_REVIEW`, not semantic success.

An independent grader assessed every applicable rubric criterion:

| Case | Historical reader | Whole-run terminal authority | Full rubric result |
|---|---|---|---|
| Baseline review | FAIL: omitted reader | PASS | Not a pass; quality-cycle explanation UNKNOWN |
| Baseline plan | PASS | UNKNOWN: described local gates | Not a pass; quality-cycle explanation UNKNOWN |
| Candidate review, 3 trials | PASS in all 3 | PASS in all 3 | Not passes; quality-cycle explanation UNKNOWN |
| Candidate plan, 3 trials | PASS in all 3 | PASS in all 3 | Not passes; quality-cycle explanation UNKNOWN |
| Candidate paused, 1 trial | Correct recovery-only reads | No completion while paused | PASS on all applicable criteria |

For example, candidate review 3 states that its callback “does not by itself
complete the objective loop or delivery.” Candidate readers consistently label
the quality baseline historical and not current proof. However, all six active
candidate answers omit part of the full script-owned review/plan/apply/check/
learning-commit explanation. That residual uncertainty is explicit: the pilot
supports these two narrow changes, not general model reliability or a fully
successful workflow. It does not justify a new scheduler or weaker gates.

One separately saved answer accidentally duplicated `.shiploop` in a callback.
Comparison with the original trial response identified an archival transcription
error. The bad saved copy is retained separately; the exact original was
restored and graded. It is not counted as another trial or a model correction.

Temporary evidence is retained under
`/tmp/shiploop-proposal-closeout.M2reUD` (baseline/candidate prompts, separate
oracles, original answer copies, and `semantic-review.md`). The durable table
above preserves the verdicts if those temporary files are later removed.
These are same-model, small-sample observations with no recorded model-version
or temperature controls, statistical claim, cross-host claim, or provider
integration. Missing explanations remain UNKNOWN; no semantic oracle is added.

### Completion boundaries

All approved unfinished proposals found in the audit are now implemented.
Deliberate deferrals in the ledger remain deferrals: no production operation,
push, new service, scheduled updater, host certification or external permission
change was performed. The skill card remains thin; its existing Until adaptation
and Markdown-authoritative state remain the only delivery control path.
