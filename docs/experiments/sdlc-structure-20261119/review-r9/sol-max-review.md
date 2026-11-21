model requested: gpt-6.1-sol; effort: max; fallback: False
(Codex does not report the model actually served. The reviewer is Sol 6.1: the review runner's `sol` target pins gpt-6.1-sol.)

**Ship A1, A2 and A3. Pilot B after narrowing its wording. E1 and E2 are appropriate cheap instruments for specific decisions; neither establishes whole-delivery quality or reliability.**

I reviewed the requested sources and the twelve saved due-times specs. They show the reported seven/five split. One provenance detail: this checkout’s Ratchet journal ends at section 19; I read section 20 from local Git object `1ef1ee5b30d173bf349a882149bf7643404cc2aa`, which the spec journal cites. No files changed; no ShipLoop, E2E or test suites ran.

**1. Design and enforcement**

| Priority | Change | Recommendation |
|---|---|---|
| **P0** | A2: process ownership | Adopt the text now. Treat it as an instruction, with any prevention mechanism assessed separately. |
| **P1** | A1: planning-review choice | Adopt the clarification. Keep `stage` as the default and preserve explicitly requested `none`. |
| **P1** | B: added refusals/manual prerequisites | Trial a rule aimed at those decisions. The current bounds wording does not clearly address them. |
| **P2** | A3: spec storage location | Correct the stale sentence directly. No behavioral experiment is needed. |

**A1 is a good correction, but its causal explanation remains a hypothesis.** `stage` already is the runtime default, and the run-options reference already states it. The omission is in the card’s prominent instructions. Thus this is primarily a clarification of how the host should choose, rather than a repair to default selection in code. See [`DEFAULT_PLANNING_REVIEW`](skills/shiploop/scripts/shiploop_stage_spec.py:697) and [run-options.md](skills/shiploop/references/run-options.md:80).

I would **not ship the experimental one-line pin** that silently converts every request to `stage`: it also overrides legitimate user requests for `none`.

Nor would I add a navigator refusal claiming to detect *unasked* `none` from the present inputs. [`new_state()`](skills/shiploop/scripts/shiploop_navigator.py:1457) receives the prompt and selected option, but no independently authenticated record of who authorized that option. A user’s standing instruction can also live outside the product request passed through `--prompt`. Another model-supplied “user requested it” flag merely adds another assertion.

The existing check can establish something narrower: [`_require_card_for_unreviewed_planning()`](skills/shiploop/scripts/shiploop_protocol.py:76) verifies the necessary Improve card. It cannot establish user intent. Strong enforcement would need a trusted configuration or authorization source outside the model’s own choice. That exceeds this small text correction.

**A2 addresses an observed failure with substantial collateral effects.** Put it in the rules printed in stage packets, because implementation, tests, research probes and release checks can all start processes. An implementation-only reference would miss several of those readers.

A shell hook could additionally prevent recognizable name-based kills before execution. The existing [`fidelity.name_kills()`](test/shiploop_e2e/fidelity.py:244) supplies a useful detector, but it is an analysis instrument, not a prevention boundary. Promoting it into enforcement requires checking host coverage, delegated calls, quoting and indirect commands. A post-command warning arrives too late.

Also, **PID targeting and complete cleanup are different properties**. Ratchet section 18 documents stopping the parent by PID while its test workers survived for hours. Retain script-owned process-group cleanup for script-launched commands; A2 alone does not prove descendants are reaped. [Ratchet §18](docs/ratchet-pilot-journal.md:1091)

**A3 is an unequivocal consistency fix.** The guide says result `body`; `DUTIES["spec"]` consistently assigns the model to `KNOWLEDGE/spec.md`. Change the guide’s locator and retain the existing result/evidence contract. [Stale instruction](skills/shiploop/references/behavioral-requirements.md:362), [`DUTIES["spec"]`](skills/shiploop/scripts/shiploop_prompts.py:1003)

**B belongs at duty 4’s decision point, but the pending wording is not yet B as described here.** Sections 24–25 concern whether a functional limit should exist, choosing its value, and recording defaults. A writer could follow that wording and still decide that an offline migration plus startup refusal is necessary for safety. The manual prerequisite needs to be addressed expressly. [Proposed duty-4 replacement](docs/spec-elaboration-journal.md:1745)

The smallest useful candidate should:

- distinguish a restriction required by the request or preserved contract from one the writer introduces;
- question a new refusal or mandatory operator step when a compatible successful path is available;
- preserve refusals justified by actual correctness or safety requirements.

Do not turn F28 into “never introduce an unstated refusal.” Its counts support scrutiny, not that prohibition.

The Ratchet lesson about script-run checks applies where scripts possess an independently checkable obligation and observe the action. It does not make scripts capable of deciding user intent or product semantics from an option or a word such as “refuse.”

**2. E1 and E2: validity, misleading results and sample size**

**E1 is valid for the option a fresh session chooses when starting this case.** Use the existing [`run.py --stop-after-start`](test/shiploop_e2e/run.py:2776), whose [`StartWatcher`](test/shiploop_e2e/start_route.py:60) uses the harness’s stop path.

The endpoint should be the **first successful initialization**, with its persisted `planning_review`. Also retain the first attempted initialization command. Otherwise, a rejected attempt at `none` followed by a successful `stage` start can conceal the original choice. A literal “first ShipLoop command” is ambiguous because it could be `--help`.

For a valid comparison:

- Use fresh sessions and fresh run directories, with the ordinary delivery instructions. Keep the early stop invisible to the subject.
- Randomize or interleave the two arms; freeze the model, effort, skill exposure, input, repository baseline and package source.
- Apply only A1’s card changes. Neither arm should pin planning reviews or receive a harness instruction selecting an option.
- Count no-start, clarification requests and invalid starts separately. They are not successful avoidance of `none`.
- Verify that explicitly requested `none` remains supported.

Ten samples per arm are reasonable for a **large-effect screening comparison**. The historical 3/5 medium count establishes that the problem occurs; it is not a precise or case-specific probability.

**E2 is valid for a narrower claim: whether the wording changes the accepted spec’s startup contract in the actual upstream context.** That is much better targeted than another whole-delivery batch or another standalone elaboration checklist.

Preserve intake, discovery, research and the normal spec review. Under `stage`, stop after the spec review finishes and the navigator advances beyond spec. Archive both the producer spec and the reviewed version, so you can see whether the writer or reviewer changed the decision. A file existing on disk is insufficient evidence of acceptance.

The twelve historical specs are useful for **calibrating the classification and motivating the trial**. They should not be the sole experimental control: they mix medium/high effort, planning-review modes and experimental conditions. All also ran with the recorded skills exposure. [R75–R77](docs/shiploop-sdlc-structure-journal.md:2242)

Use a fresh control alongside the candidate, holding the review mode constant. Classify each spec into at least:

1. An explicit successful startup path that prepares valid legacy data.
2. A mandatory manual preparation step with startup refusal until completed.
3. Unresolved, contradictory or insufficiently specified behavior.
4. No accepted spec.

An optional offline tool should not count as a mandatory prerequisite if startup still supplies the required successful path. Require a quoted acceptance clause for each label. Also inspect for newly weakened safeguards: accepting corrupt data or serving after failed persistence would be a regression even if the manual-step count fell.

Eight to twelve samples **per arm** are honest for screening a large change on this case. Eight to twelve candidate samples against the old twelve are a historical comparison.

The precision limits are substantial:

| Candidate result | One-sided 95% upper bound on the failure probability* |
|---|---:|
| 0/8 failures | 31% |
| 0/10 | 26% |
| 0/12 | 22% |

\*Assuming independent draws from a stable condition.

For scale, 6/10 control failures versus 0/10 candidate failures is strong evidence of a large difference under a valid randomized comparison; 3/10 versus 0/10 remains inconclusive. Neither establishes elimination.

Predeclare the sample count and promotion criteria. Early rejection for an obvious regression is sensible. Repeatedly extending a favorable-looking arm until it passes a threshold is not. A null small experiment supports “no useful effect demonstrated here,” rather than equivalence.

**3. What is missing, wrong or overreaching**

**P1 — The yardstick ambiguity needs to remain explicit.** R62 says the request permits the operator-step interpretation while the probes require startup preparation. The probes directly start the enabled release over legacy data. That measures a particular deployment contract. [R62](docs/shiploop-sdlc-structure-journal.md:1811), [`due_times_probe.py`](test/shiploop_e2e/checks/due_times_probe.py:20)

You can use E2 to measure movement toward that contract without changing the historical request or probes. Calling the movement *better fulfillment of customer intent* additionally requires an explicit basis for preferring it. More model samples cannot resolve that ambiguity.

**P1 — F28 is an association between generated clauses and reference-test disagreement.** The 28/46 combines `choice` and `implied`; explicit `choice` alone is 18/27. These are clustered clauses from six runs on three cases, with a rough word-list mark and one reference per case. Some failures reflect differing configuration names between otherwise acceptable implementations. The result justifies auditing added restrictions; it does not estimate a general production failure rate or prove that each restriction is unwanted. [F28 and its limits, as received](docs/spec-elaboration-journal.md:1645)

**P1 — The spec endpoint is a useful surrogate, with a practical limit.** The observed spec/product correspondence makes E2 credible for this decision. It cannot verify persistence, rollback, implementation compliance or unrelated regressions. A favorable result earns the usual delivery verification; it does not replace it.

**P2 — A2/A3 do not need separate model experiments.** Incident evidence and the contradictory locator already justify them. Packet checks can verify that the instruction reaches the intended readers. They cannot prove future obedience. One ordinary release E2E round after the accepted changes is reasonable.

With no further runs, I would conclude:

- The unasked option choice, collateral process kill and stale locator are established.
- A1/A2/A3 are justified small corrections.
- The due-times specs identify a consequential decision worth targeting in duty 4.
- The pending seven-sentence bounds replacement is unproven and does not clearly target that decision.

I would refuse to conclude that A1 eliminates unasked `none`, A2 guarantees process safety, B improves delivery quality, higher effort cannot help, or planning reviews can generally be removed.

The proposed 36-delivery trial is unnecessary as the **first** decision. E2 can reject an ineffective or harmful wording cheaply. Conversely, a null on the repository-free bounds filter does not establish a null on this manual-prerequisite problem; those are different endpoints. [Filter registration](docs/spec-elaboration-journal.md:1785)

**4. Exact A1 and A2 text**

**A1 — In the existing run-options paragraph in SKILL.md:**

> `--planning-review stage|none` (default `stage`; pass `none` only when the user asks to run without planning reviews).

Replace the initialization comment with:

```text
# Optional: select the exact actual Improve skill at initialization; required when the user asks to run without planning reviews.
```

Put the same user-choice condition in `references/run-options.md` beside its existing default description. An established user instruction counts; this wording should not generate another confirmation question. [Card locations](skills/shiploop/SKILL.md:164)

**A2 — Ship these sentences:**

> Record the PID when you start a background process. Stop it using that recorded PID, after confirming it still belongs to this run. Never select processes to stop by name or pattern (`pkill`, `killall`, or a name search piped to `kill`): unrelated work on this machine can match.

Put this alongside the scratch-directory rule in [`STAGE_RULES`](skills/shiploop/scripts/shiploop_prompts.py:500), and keep the corresponding long-form rule in `COMMON` consistent. [`_prompt_parts()`](skills/shiploop/scripts/shiploop_prompts.py:2232) appends `STAGE_RULES` to producer packets on both delegation routes. Putting it only in `COMMON`, SKILL.md or `implement-guidance.md` would give weaker exposure.

For A3, the minimal replacement is:

> Store the proposed product behavior in `KNOWLEDGE/spec.md`:

**5. Claims in Round 7 or Round 8 that need correction or qualification**

The journal already records important limits and withdraws the contaminated timing comparison. The following live wording still exceeds its evidence:

- **P1 — F53’s causal “why,” and recommendation 2’s “would stop.”** The records establish an unasked choice immediately following the card read. They do not isolate the missing default, the comment, or another influence as its cause. Say “the card makes this choice available without stating its default or user-choice condition; clarifying it is a candidate remedy.” [F53 and recommendation 2](docs/shiploop-sdlc-structure-journal.md:2164)

- **P1 — F42’s “removing them buys nothing” and implied ceiling on savings.** Zero edits in 21 reviewed stages is established. No readable saving in these small cells is established. Those observations do not bound the possible total effect of removing reviews: removal can alter later planning, checking and implementation. “No saving demonstrated in this round” is supported. [F42](docs/shiploop-sdlc-structure-journal.md:1877)

- **P1 — F44’s “what lean would buy” estimate.** Four to five minutes is an accounting estimate after the registered total-time measure was compromised. It is not an identified counterfactual saving. Also, the different work-item count might be an effect of the review treatment; it cannot automatically be discounted as an extraneous explanation for the milestone difference. [F44](docs/shiploop-sdlc-structure-journal.md:1888)

- **P1 — F51’s “Higher effort is not what moves it.”** The counts show no improvement demonstrated, including after the redo. Three failures in six versus four in six cannot establish that effort has no useful effect on the rate. Likewise, the tested reviews and elaboration forms do not exhaust those interventions. [F51](docs/shiploop-sdlc-structure-journal.md:2159)

- **P2 — “Earn their place” needs its registered meaning attached.** F43 establishes substantive editing, and the registered rule labels that sufficient. F45 correctly says delivery benefit was not shown. Present this as passing the study’s edit-yield criterion, rather than measured prevention of customer defects. [F43–F45](docs/shiploop-sdlc-structure-journal.md:1882)

- **P2 — F48’s four-run limit is a precaution, not a measured threshold.** The incidents justify reducing interference. No comparison establishes four as safe or optimal, and a broad name kill can damage unrelated work with only one delivery running. [F48 and recommendation 7](docs/shiploop-sdlc-structure-journal.md:1904)

- **P2 — F50 does not justify weakening late checks.** The extra item explains much of the observed duration. Whether it was necessary remains unestablished, as the journal acknowledges. Passing the held-out checks beforehand cannot settle that. [F50](docs/shiploop-sdlc-structure-journal.md:1967)

- **P2 — The final timing recommendation has a denominator error.** For shared-expenses, medium at 11.1 minutes versus high’s mean 15.4 is approximately **28% less time**, not “a third or more.” High takes approximately 38% more. For due-times, medium takes approximately 40% less. Keep the reported high-over-medium percentages or calculate the inverse explicitly. [R74 and final recommendation](docs/shiploop-sdlc-structure-journal.md:2231)

These qualifications leave the small corrections intact. They principally change what the studies can claim about causes, absence of effects and general delivery value.
