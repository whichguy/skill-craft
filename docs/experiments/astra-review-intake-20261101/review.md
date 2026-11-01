<!-- Astra's review of ShipLoop's prompt enrichment, 2026-11-01. Verbatim model text. model_used=gpt-6-astra fallback=False effort=max profile=consult sandbox=read-only persona=codex-astra exit=0. The brief it was given is brief.txt. Nothing below was edited; README.md says what was verified. -->

1. **Measure K12’s effect on delivered behavior using requests that actually require lookup; keep the shipped design meanwhile.**
2. **Carry evidence, defaults and unresolved questions forward by Q-ID so enrichment cannot silently become an invented requirement.**
3. **Make term resolution sensitive to context: finding an installed skill with the same name does not establish that the user meant it.**
4. **Clarify question relevance, applicability and person routing; reduce redundant questions through meaning, without word caps.**
5. **Strengthen the evaluation with request-blocked comparisons, independently justified answers and whole-pipeline cost.**

I inspected the shipped implementation, registrations, journals, score files, selected outputs and relevant commit messages. I also recomputed selected statistics from saved results in memory. I changed no files and called no models. Below, **verified** means supported by those files; **inference** and proposed experiments are identified separately.

**(a) Review of the enrichment**

The catalog-plus-ledger is a sensible design worth retaining. Its strongest demonstrated benefit is **making consequential omissions visible**, with some evidence that those decisions reach the spec. Evidence that K12 improves actual deliveries remains missing. The next improvement should address that distinction before expanding the prompt.

Your numerical summary is substantially accurate, with four qualifications:

- **0.47 to 0.92–0.96 is a comparison across arms**, not successive improvements. The shipped ledger scored approximately 0.935; 0.958 belongs to the fixed statement bank.
- “The wording does not matter” is too categorical. On the fixed bank, statements scored 3.7 percentage points higher in recall, while questions cost 7% fewer output tokens. Those effects missed the registered *practical-size* thresholds; they were not zero.
- “Agreement with the real request” means agreement with a **withheld, author-written full specification**, not independently recovered user intent.
- The judge’s observed batch shifts support using common judging blocks. They do not establish that every within-call comparison is valid or that every cross-call comparison is invalid.

These distinctions are visible in [question-bank README — Measures, Rules, QB1 and QB3 results](/Users/dadleet/src/skill-craft/docs/experiments/question-bank-20261031/README.md).

The duty’s strongest parts are its sentence coverage, explicit scope boundaries, requirement that a question name what it changes, and separation of information sources from human decisions. Its weakest part is the connection between **raising a question, obtaining an answer, and making that answer authoritative downstream**.

The categories themselves are mostly well chosen:

| Category | Assessment |
|---|---|
| K1 Outcome and consumer | Strong anchor. The observable outcome matters more than merely identifying an actor. |
| K2 Scope and preserved behavior | Essential protection against enrichment expanding the task. |
| K3 Interfaces and contracts | Productive, but “exact” names and shapes should remain open choices when neither request nor evidence determines them. |
| K4 Rules and edge cases | Strong. Should expose consequences of existing rules, without manufacturing exhaustive hypothetical cases. |
| K5 State and data | Valuable cross-cutting coverage: ownership, lifetime, visibility, concurrency and restart. Scale its application to the request. |
| K6 Runtime and dependencies | Useful discovery questions. Avoid prematurely choosing versions or dependencies as requirements. |
| K7 Structure | Most likely to turn intake into premature design. Identify consequential seams or constraints; leave module selection to planning. |
| K8 Verification | Keep the real-boundary observation. Framework and command questions belong only where they are genuinely unsettled. |
| K9 Delivery | Keep. Its low score in contract-heavy exercises is not evidence of low practical importance. |
| K10 Quality attributes | Keep, with observable consequences. Do not invent numerical bounds or additional product ambitions. |
| K11 Risks | Useful prioritization, but vulnerable to generic restatement of K2–K10. A risk should identify a specific failure and early observation. |
| K12 Terms and references | Addresses a demonstrated weakness. Needs stronger distinction between discovering a candidate meaning and establishing the meaning intended here. |

This assesses the current wording in [shiploop_prompts.py — `DUTIES["intake"]`](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py), rather than proposing a wholesale rewrite.

**The ledger is useful, but it mixes several kinds of information.**

A row contains a question, consequence, route, fallback answer and blocking condition. That is substantially better than an unstructured list of doubts. However:

- `route` can describe a proposed investigation, not an investigation performed.
- `default` can contain a hypothetical answer, a chosen policy, an observed fact, or a mixture.
- `blocks` can combine current prerequisites, eventual verification and a statement that work proceeds.
- There is no dedicated requirement to distinguish a settled answer from an unresolved question in the row itself.

This is observable in saved outputs. For example, `users-Bk-s1` puts a Node version and port **fact** together with an **assumption** in Q8’s `default`; several rows ask discovery to inspect material that the exercise already read. `records-Bk-s1` asks whether “usual whitespace” means existing behavior even though the request explicitly requires preserving string behavior. These are understandable outputs under the current contract, but create repetition and ambiguous handoffs. [QB5 intake — users-Bk-s1](/Users/dadleet/src/skill-craft/docs/experiments/terms-line-confirmation-20261031/intake/users-Bk-s1.json), [records-Bk-s1](/Users/dadleet/src/skill-craft/docs/experiments/terms-line-confirmation-20261031/intake/records-Bk-s1.json).

**The shape check is intentionally limited—and narrower than its error text suggests.**

Verified in `_check_intake_questions`:

- The entire ledger is optional.
- The category list, when supplied, must contain K1–K12 once.
- Questions need a unique Q-shaped ID, a nonempty question and an allowed route.
- The function does **not** require `category`, `changes`, `default` or `blocks`.
- It does not check that a question’s category exists, that both ledger fields appear together, or that applicability agrees with the questions.
- It establishes neither evidence quality nor successful lookup.

By static inspection, a question containing only `id`, `question` and `route` satisfies this function’s question checks. I did not submit such a result to the navigator.

This is a contract gap, but not evidence that stricter gates would improve normal runs. The history explicitly records why compulsory ledgers were rejected: the model had written them, canonicalization discarded them, and requiring them addressed the wrong fault. Preserve that lesson. [shiploop_navigator.py — `_check_intake_questions`, `_canonical_result`, `QUESTION_ROW`](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py); commit `e7e0bc3c0e347845e8ee4f99ee318175d280c9db`.

**The routing policy has good priorities but ambiguous boundaries.**

“Look, then default, then ask” fits the owner’s goal. Two refinements matter:

1. “Only when two readings remain that lead to different work” is an insufficient description of when human input is necessary. Almost every design choice has multiple consequential readings. Conversely, a missing authorization or production value may require a person without presenting two neat interpretations.
2. “No evidence can answer it” is stronger than “the available evidence has not settled it.” An unavailable fact should not become a discretionary preference merely because its source is inaccessible.

The global unattended rule already supplies the right governing behavior: record defaults, continue independent work, and block only when nothing can proceed, with `no_default`. The local K12 wording should clearly subordinate itself to that rule. A `person` row should record dependency on a person; it should not itself instruct intake to stop. [shiploop_prompts.py — unattended rules and intake duty 9](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_prompts.py).

The research framing also needs updating. It repeatedly says real intake leaves repository reading to discovery. The **current shipped intake explicitly instructs lookup**, and I found no blanket prohibition on its read-only inspection. The real distinction is that broad baseline discovery belongs to later stages, while the exercise permits extensive inspection immediately. That division should be stated explicitly rather than described as “real intake does not read.”

**Downstream transfer is supported by architecture, but incompletely measured.**

The script stores the ledger whole and supplies earlier-result locators according to the stage table:

| Consumer | How enrichment reaches it |
|---|---|
| Discovery | Reads intake; must answer open questions with sources or preserve unknowns with owners. |
| Research | Reads intake and discovery; develops evidence and load-bearing assumptions. |
| Spec | Reads intake, discovery and research; establishes requirements, bases and open gaps. |
| Test strategy | Reads spec and research; it does not directly depend on intake. |
| Plan | Reads all those stages; allocates work and assumptions. |
| Step plan | Reads spec, strategy, plan and preparation; depends on earlier translation preserving meaning. |

[shiploop_stage_spec.py — stage `reads` declarations](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_stage_spec.py); [shiploop_navigator.py — `_builds_on_lines`](/Users/dadleet/src/skill-craft/skills/shiploop/scripts/shiploop_navigator.py).

The architecture therefore has a plausible failure mode: a provisional default becomes a requirement, then tests faithfully verify it, without anyone preserving its provisional status. Passing tests would establish conformance to the chosen default, not agreement with user intent.

X2b gives useful evidence against complete loss: decision carriage rose from 0.776 to 0.897. But acceptance-line coverage rose only from 0.643 to 0.665 and was not significant. It did not test the full spec → strategy → plan → step-plan → delivery chain. [question-driven planning journal — E9](/Users/dadleet/src/skill-craft/docs/shiploop-question-driven-planning-journal.md).

**Cost is modest in absolute intake terms, but “cheap” needs the correct denominator.**

QB1’s ledger used about **3.4 times** the old statement intake’s output tokens: 2,153 versus 636. Covered decisions per 1,000 output tokens actually fell. The benefit was greater completeness, not better local token efficiency.

For QB5, I independently reproduced:

- Items right: **0.5198 → 0.6744**.
- Output tokens: **+8.1%**.
- Uncached input tokens: **+16.3%**.
- Silent assertions: **0.667 → 0.200 per output**.

The additional reading matters. Total processed live tokens also include repeated context and caching effects, so they should not be presented as dollar cost. Optimize successful delivery per unit of total effort, while avoiding unsupported attribution of downstream savings to intake.

**(b) Recommendations, ranked by expected value**

**1. Pilot a delivery-benefit experiment before further enrichment expansion.**

Keep the present product while testing whether evidence-based term resolution changes what gets delivered.

Use experiment-specific variants of existing cases:

- **`hello` unchanged:** a negative control for unnecessary questions, searches and scope expansion.
- **`shared-expenses`:** replace a few explicit definitions with references to supplied, authoritative project documentation. Preserve the product contract and independent checks.
- **`user-listing`:** use a dictated request whose “usual” behavior is discoverable, including the existing short-final-page defect.

For genuine preferences omitted from the request, either accept multiple legitimate defaults or provide an answer through an authorized source. Do not require the model to guess a hidden arbitrary specification.

The smallest useful live screen is one `hello` run per arm and two runs per arm for each consequential case: **10 runs total**. This is a mechanism screen, not a reliable noninferiority trial. First use the existing intake-to-spec exercise machinery to eliminate candidates that already lose the resolved information.

Measure the chain:

> Relevant source was opened → meaning was recorded accurately → requirement retained it → independent product check observed it.

Run pinned arms on Codex Terra high with the same harness configuration. Keep experiment variants separate from existing baseline identities. A concrete harness caution: `run.py --prompt` creates a **custom** case; it does not inherit the named case’s fixture and quality metadata. [run.py — `load_case`](/Users/dadleet/src/skill-craft/test/shiploop_e2e/run.py).

**Evidence:** Both live studies explicitly acknowledge that fully specified requests cannot demonstrate benefit.  
**Risk/cost:** Live runs are expensive; constructing discoverable requests can contaminate the oracle. Independently define the expected behavior before authoring the prompt variant.  
**Confirmation/refutation:** If the candidate resolves more terms but neither changes requirements nor improves checks, it has not demonstrated delivery value. If both arms succeed, the result may be a ceiling rather than evidence of equivalence. [live A/B README — What this cannot settle](/Users/dadleet/src/skill-craft/docs/experiments/terms-line-live-ab-20261101/README.md), [R3 README — What this cannot settle](/Users/dadleet/src/skill-craft/docs/experiments/send-back-replication-r3-20261101/README.md).

**2. Pilot explicit provenance and Q-ID carry-forward using existing artifacts.**

Do this through a small producer/consumer wording change before adding fields or another ledger.

Proposed intake wording:

> “For each consequential reading, distinguish what the request states, what an opened source establishes, and what the run assumes. Cite its request sentence and source where available. A default is provisional; say what evidence or decision would change it.”

Replace discovery’s current “Answer each intake open question…” sentence with:

> “Account for each intake Q-ID in the summary: answer with its source, retain an explicit default and its reason, or leave it open with its owner and first affected work. Preserve that disposition when carrying the answer forward.”

Add to spec’s basis instruction:

> “Do not turn an intake assumption into a user requirement or an observed fact. Retain its basis and any unresolved condition under the requirement or decision it affects.”

Use existing summaries, source locators and plan assumptions. The navigator continues owning position and transitions.

**Evidence:** The ledger is preserved correctly, but the consumption duties do not require Q-ID accounting. X2b’s carriage gain is stronger than its acceptance-line gain. The saved outputs demonstrate mixed fact/default fields.

**Risk/cost:** More references can become repetitive bureaucracy. Carry concise dispositions, without copying entire rows into every stage.

**Smallest experiment:** Reuse saved intakes in an X2b-style cold-context spec comparison. Include cases where later evidence **contradicts an earlier default**, cases where it confirms it, and unresolved preferences. Four paired cases are enough to expose a systematic failure, though not establish a general rate. Score correction, retained uncertainty, invented requirements and tokens—not merely mention of the Q-ID.

This tests something the existing studies largely do not: **whether enrichment can retract a wrong interpretation successfully**.

**3. Pilot context-sensitive term resolution, including collisions and real search.**

Suggested replacement for the lookup sentence:

> “Resolve consequential terms and references by checking the host’s listed skills and commands, then the repository and its documents, then an appropriate search; stop when relevant evidence settles the meaning. A matching name is a candidate meaning, not proof of intent. Distinguish instructions about how to do the work from behavior the delivered product must provide. Record the source and reading, or the best reading and what remains uncertain.”

Also make the stage boundary explicit: focused read-only term lookup can happen at intake; baseline discovery and experiments remain with their existing stages. A planned `research` route is not a completed search.

**Evidence:** QB5 `meter` items M1 and M2 reward interpreting “schedule” and “loop” as installed skills. Yet `meter-Bk-s1` reasonably says similarly named skills do not establish a production scheduler or monitor; the judge gives this only partial credit. [QB5 cases.py — meter M1/M2](/Users/dadleet/src/skill-craft/docs/experiments/terms-line-confirmation-20261031/cases.py), [meter-Bk-s1](/Users/dadleet/src/skill-craft/docs/experiments/terms-line-confirmation-20261031/intake/meter-Bk-s1.json), [meter-s1 judge](/Users/dadleet/src/skill-craft/docs/experiments/terms-line-confirmation-20261031/judge/qb5-meter-s1.out.json).

**Risk/cost:** Overqualification could make obvious skill invocations hesitant. Preserve decisive handling of explicit invocations. Apply the existing rule keeping private context out of public searches; reuse it rather than inventing a separate intake policy.

**Smallest experiment:** Three contrast pairs, two arms, one sample each—12 intake calls initially:

- Explicit host-skill invocation versus the same word describing product behavior.
- The same reference with two different authoritative repository definitions.
- A public term requiring a real search versus an unresolved internal name.

Score correct source selection, actual tool use, unwarranted skill invocation and unnecessary searches. Expand only if this screen is promising. This tests **specificity**, which the current skill-heavy positive examples barely measure.

**4. Pilot clearer relevance and stopping semantics; defer additional gates.**

Proposed addition to duty 9:

> “Write questions only for unresolved distinctions whose answers change named work. Put an answer already explicit in the request in the summary instead of asking it again. One question may cover overlapping concerns; do not repeat it to fill categories. An applicable category may have no open question.”

Clarify applicability:

> “`applies: no` means the concern cannot affect this request’s outcome; it does not mean the answer is known, the source is unavailable, or the concern has been deferred.”

Align person routing:

> “Use `person` when the remaining decision or action requires that person and no justified default permits the dependent work. Continue independent work; report blocked only under the run’s unattended rule.”

This preserves the existing policy rather than creating an attended intake.

**Evidence:** The same `hello` request produces K12 “yes” and “no,” including “no” reasons meaning that terms are already clear. R3 produces ten K12 “yes” rows with no K12 questions. Neither behavior measures useful enrichment. [live A/B scores — K12 rows](/Users/dadleet/src/skill-craft/docs/experiments/terms-line-live-ab-20261101/scores.json), [R3 README — What these runs show](/Users/dadleet/src/skill-craft/docs/experiments/send-back-replication-r3-20261101/README.md).

**Risk/cost:** Aggressive pruning could miss implied requirements, including the repeatedly missed seat-reservation read contract. “Unresolved” must include consequential implications, not only explicit question marks.

**Smallest experiment:** Pair fully specified `hello` and `user-listing` with vague `seat-reservations` and `csv-report` exercises. Compare redundant questions, omitted consequential decisions and tokens. Include one decision with a legitimate default and one genuinely person-dependent boundary.

Audit missing fields and inconsistent categories in saved ledgers first. If real failures appear, enforce only the minimal existing shape. Do not add semantic gates that try to determine whether a question is wise or a confidence statement is truthful.

**5. Adopt a more decision-relevant evaluation contract for future studies.**

Use three separately reported outcomes:

1. **Discovery:** Did the run establish the relevant fact or identify the legitimate decision?
2. **Transfer:** Did later stages preserve the answer, its basis and uncertainty?
3. **Delivery:** Did the product satisfy the resulting authorized contract?

For statistics, preserve request and judge-call blocks. Report per-request effects and uncertainty. Treat fresh-request generalization separately from repeated samples of the same request.

For cost, include output/reasoning, cached and uncached input, tools, elapsed time and subsequent rework. Avoid replacing these with one processed-token ratio.

For decision rules, predeclare:

- What happens when the primary benefit passes but a secondary safety condition is inconclusive.
- What size of harm is unacceptable.
- How missing runs and retries count.
- Which comparisons are confirmatory.
- What triggers further sampling.

**Evidence:** QB5’s decision rules omitted the observed C3-only-failure branch; the scores pool heterogeneous requests despite common judge blocks; live cost comparisons were unbalanced by case.

**Risk/cost:** Overengineering the analysis would defeat KISS. The existing `sign_flip_p`, mappings and saved results already supply most of the needed machinery.

**Smallest experiment:** No new model calls. Reanalyze saved scores, audit a small sample against actual tool evidence, and manually assess disputed skill interpretations without arm labels. This is the cheapest recommendation to execute first.

**(c) Weak points in the study**

**“The shipped ledger paid off downstream (0 of 6 proof-order send-backs against 4 of 6).”**

This claim in journal §0 is not supported as an attribution to the ledger. The live treatment included a **proof-order refusal**, the ledger and another prompt change. The refusal replay identified exactly the four problematic control plans. Two early treatment runs even lost their ledgers during canonicalization.

The earlier journal correctly states that the ledger’s downstream product effect was not measurable on those fully specified requests. Attribute the send-back improvement to the measured gate intervention, while reporting the ledger’s compatibility separately. [question-bank journal — §0 and §6](/Users/dadleet/src/skill-craft/docs/shiploop-intake-question-bank-journal.md), [question-driven journal — E10](/Users/dadleet/src/skill-craft/docs/shiploop-question-driven-planning-journal.md); commits `ffea29563ecab5415de88e68f9cb9b3e2f0b555f` and `45f9752eee7d4fe3450b9ac88843cc1da0fbb980`.

**“What lifted coverage … was an explicit list … however it was worded.”**

Directionally supported, but the intervention is a bundle: catalog, ledger, more explicit obligations and substantially longer output. Earlier arm C helps distinguish ledger from catalog, but does not isolate every mechanism.

The defensible conclusion is: **the tested catalog-and-ledger bundle substantially improves this coverage measure on Terra; grammatical form is a smaller lever.** The fixed-bank wording effect remains real within the study, even below its practical threshold.

**“Agreement with the full request.”**

This is a useful benchmark score but an imperfect proxy for good unattended judgment. The vague user-listing request does not reveal the withheld page-size choice of 10; the vague game request does not establish exact endpoint names. A defensible alternative can therefore be marked a conflict.

Measure separately:

- Contradiction of supplied instructions.
- Unsupported assertion about the environment.
- Reasonable default differing from the hidden reference.
- Failure to expose a consequential choice.

[Original exercise cases — `ground_truth`](/Users/dadleet/src/skill-craft/docs/experiments/key-questions-intake-20261030/cases.json), [judge_build.py — `default_matches`](/Users/dadleet/src/skill-craft/docs/experiments/key-questions-intake-20261030/judge_build.py).

**“Exact one-sided p 0.0083.”**

I reproduced the underlying QB5 arm means. However, `qb5.py` sends all 15 control and 15 treatment values to an unrestricted permutation test, despite grouping by three requests and shared judge calls. The test does not preserve those blocks.

As a **post hoc sensitivity analysis**, pairing B and Bk within their 15 judge calls gives:

| Measure | Registered pooled test | Supplementary paired sign-flip |
|---|---:|---:|
| Items right, Bk higher | 0.00826 | 0.000122 |
| Silent assertions, Bk lower | 0.115 | 0.125 |

Thus the main gain does not disappear under this alternative; the silent-assertion result remains inconclusive. But three positive request-level effects provide only three units of task diversity: a three-request sign-flip gives 0.125. That illustrates why a very small conditional p-value is not strong evidence about new request families.

I checked 400 covered-item quotations across the saved B/Bk outputs using the scorer’s normalization; all matched. That verifies quote presence, not correctness of interpretation. [qb5.py — `collect`, `p_higher`, `p_lower`](/Users/dadleet/src/skill-craft/docs/experiments/terms-line-confirmation-20261031/qb5.py), [stats.py — permutation and sign-flip tests](/Users/dadleet/src/skill-craft/docs/experiments/question-bank-20261031/stats.py). The distinction between independent and paired permutations is also explicit in [SciPy’s primary documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html).

**“Only comparisons inside one judge call are valid.”**

Too absolute. Recomputing the shared-output means gives shifts of approximately **2.64 and 4.72 percentage points**, consistent with the reported scale. Common-call judging helps control that variation.

It does not eliminate presentation, position or comparative-context bias. Arm labels are hidden, but bank and ledger formats remain recognizable. Conversely, cross-call comparisons can be usable with appropriate calibration, blocking and replication. Known position and verbosity biases make a small blinded human audit worthwhile. [QB1/QB3 score files](/Users/dadleet/src/skill-craft/docs/experiments/question-bank-20261031/scores.json), [QB3 scores](/Users/dadleet/src/skill-craft/docs/experiments/question-bank-20261031/scores-qb3.json), [LLM-as-judge study](https://arxiv.org/abs/2306.05685).

**“The terms line replicates on three new repositories.”**

Correct within the constructed exercise, but those are three new requests authored by the same session using the same design vocabulary and rubric assumptions. They are not an independent sample of owner requests.

The schedule/loop examples show why this matters: the rubric can reward a preferred interpretation of ambiguity. Also, the “environment” route grade describes what an output **says** the environment establishes; the judge does not receive the shell transcript to verify the claim. The unknown-name examples primarily test admitting absence, while internet slang is handled from model knowledge because web search was unavailable.

Future claims should distinguish **recognition, source-backed resolution, and appropriate nonresolution**.

**“Confirmed on the exercise.”**

The study correctly says it was **not** confirmed under all four registered rules. Your summary correctly acknowledges C3’s miss. The owner’s subsequent approval is a legitimate product decision under uncertainty; it does not retroactively make C3 pass.

For future studies, requiring statistically significant improvement on a rare secondary failure measure may be a poor adoption rule. Predefine a safety margin and an inconclusive outcome rather than leaving a missing branch. [QB5 README — Rules and Results](/Users/dadleet/src/skill-craft/docs/experiments/terms-line-confirmation-20261031/README.md).

**“What it shows is that B was not worse here.”**

Acceptable only as a description of the observed send-back count. R3 does not establish noninferiority. With A at 4/10, the registered significance rule needed B at 9/10 or 10/10; substantial harm could remain undetected.

R3 also changes the case and product version. It is a current-product test, not an exact replication explaining the earlier imbalance. The README largely acknowledges this; the short journal summary should preserve those qualifications. [R3 README — Rules, power and Results](/Users/dadleet/src/skill-craft/docs/experiments/send-back-replication-r3-20261101/README.md).

**“Intake asked one question per output, the same one every time.”**

Journal §0 overstates QB4. There were **six person-routed rows across eight outputs**; two outputs asked none. All six concerned the weekly-report window. Moreover, “no default is safe” was a manual interpretation, not an experimentally established property. No answers were supplied and no downstream outcomes measured.

QB4 tests which questions one restrictive prompt emits. It does not establish the optimal asking policy or the cost of under-asking. [question-bank README — QB4 setup and results](/Users/dadleet/src/skill-craft/docs/experiments/question-bank-20261031/README.md).

Finally, the broad harness/literature survey should remain hypothesis-generating. The journal candidly says many mechanisms were agent summaries, while verification established existence, dates or abstracts. Those checks cannot support universal statements about what every vendor does or the transferability of reported gains.

**(d) What should not change**

- **Keep the catalog and model-written ledger.** The tested fixed bank failed its replacement criteria and produced more conflicting defaults.
- **Keep K12 while measuring its missing benefit.** The exercise gain is credible enough to justify the current modest addition; there is no evidence-backed reason for immediate removal.
- **Keep unattended operation and scoped blocking.** Neither QB4 nor zero-ask live results justify a routine interview stage.
- **Keep unrestricted substantive answers.** The tested 12-word cap lost meaningful coverage. Reduce repetition rather than truncating necessary distinctions.
- **Do not drop K1, K9, K10 or K11 because they scored little here.** The benchmark emphasizes testable interface contracts and underrepresents delivery, usability and operational risk.
- **Do not add K13, compulsory probes or another reviewing model on this evidence.** The conflict-category benefit was not demonstrated; XI’s proposed probing mechanism mostly did not execute. [question-driven journal — E12–E14](/Users/dadleet/src/skill-craft/docs/shiploop-question-driven-planning-journal.md).
- **Keep scripts responsible for state and stage selection.** Provenance is task evidence, not a second model-maintained navigation system.
- **Do not reopen proof-order gates as an intake improvement.** The side study found recoverable loops and false positives in candidate rules. Its latest addendum separately authorizes an F31 wording experiment; that is distinct from this enrichment review. [implement-send-back study — Decision and addendum](/Users/dadleet/src/skill-craft/docs/experiments/implement-send-back-class-20261101/README.md).

**(e) Unknowns to resolve first, cheapest first**

1. **Are the strongest conclusions accurately attributed?** Correct the ledger/gate attribution, QB4 count and noninferiority language using existing records.
2. **What survives between stages today?** Audit saved runs for a few consequential Q-IDs: source, assumption status, spec basis, test and delivery observation.
3. **Does the rubric reward the right behavior?** Blindly review disputed skill matches, defaults and silent assertions against request and tool evidence.
4. **Can a later stage correct an earlier default?** Run the small cold-context contradiction/confirmation exercise before a full delivery study.
5. **Does lookup distinguish meanings rather than merely recognize names?** Test skill-name collisions, changed repository definitions, absent references and one real public search.
6. **Does enrichment improve delivery on an underdetermined but answerable request?** Run the small live study with unchanged `hello` as a negative control and consequential service/brownfield variants.
7. **How broadly does any gain transfer?** Only then spend on independently sourced owner requests, larger repositories, other domains or model/effort settings. Keep existing baseline settings intact and distinguish requested from actually observed served-model identity.
