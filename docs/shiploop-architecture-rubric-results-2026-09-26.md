# Architecture rubric results — 2026-09-26

First runs against the [architecture rubric](shiploop-architecture-rubric.md):
a 14-scenario pilot on the hosted runtimes, and a platform-card experiment on
four general deployments. Harness, fact sheets and every verdict:
[experiments/shiploop-architecture-rubric](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/).

Sonnet for trials and judge; blind grading, one plan at a time; scores are
met = 1, partial = 0.5, missed or overbuilt = 0, averaged over applicable
criteria. Small samples (two trials per scenario, runtime and variant): read
differences under about 0.1 as noise unless they repeat across experiments.

## Pilot: shipped text against a proportion-and-channels candidate

14 scenarios × 2 of {Apps Script, Salesforce, Cloudflare Workers} × 2 variants ×
2 trials = 112 plans (111 graded; one stayed a stub after three reruns and was
excluded). The **shipped** variant is ShipLoop 0.35.0's interaction-design
block. The **candidate**
([text](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/candidate_interaction_design.txt))
narrows the hidden-information clause to information one user must not see of
another's, adds "choose the simplest placement that meets the request", and adds
the channel ladder and caching rules.

| | Shipped | Candidate |
| --- | --- | --- |
| Overall score | 0.87 | 0.89 |
| P1 Proportion | 0.86 | 0.96 |
| Overbuilt proportion grades (P1) | 4 | 1 |
| C1 Channel choice | 0.87 | 1.00 |
| C4 Offline | 0.75 | 1.00 |
| C5 Channel cost | 0.67 | 0.90 |
| K1 Cache use | 0.80 | 0.94 |
| K2 Freshness | 0.90 | 1.00 |
| R2 Limits | 0.62 | 0.82 |
| O1 Failure visibility | 0.77 | 0.86 |
| **D1 Personal data** | **0.79** | **0.57** |
| **I4 Untrusted callers** | **0.88** | **0.75** |
| **D3 Logs** | **0.78** | **0.69** |
| P3 Scope (overbuilt grades) | 3 | 5 |

The candidate does what it was written for. The single-player game stops moving
server-side to "hide the computer's fleet". The judge's overbuild notes on the
shipped plans name exactly that pattern: CacheService or Platform Cache game
state and anti-cheat for a player with no opponent. Channels, caching and
limits are chosen and costed. But personal data, abuse controls and log
hygiene fall. That is consistent with attention displacement: more text about
channels and caching, less about privacy. **Do not ship the candidate as
written.** The next variant should keep its proportion and channel lines while
putting personal data and untrusted callers back in view, and should be rerun
on this catalog before shipping.

Tier choice by scenario (plans that chose the expected tier, shipped then
candidate): solo game 2/4 then 3/4; receipts upload 2/4 then 4/4; AI summarizer
1/4 then 3/4; all others 3/4 to 4/4 in both.

## Platform cards on general deployments

8 scenarios × 2 of {Vercel, AWS serverless, Google Cloud Run, Node/Express} ×
{no card, card} × 2 trials = 64 plans. Four scenarios name a UI framework
(Bootstrap or Material Design) and add U1–U3. The card variant links the
environment's new platform card (and the UI-frameworks card when a framework is
named); it read them in every trial. The control ran with the same Read tool
from a directory without access to the cards.

| | No card | Card |
| --- | --- | --- |
| Overall score | 0.88 | 0.86 |
| U3 Host fit | 0.59 | 0.91 |
| R3 Accuracy (platform errors) | 0.91 (6) | 0.95 (4) |
| I3 Sharing model | 0.90 | 1.00 |
| I2 Authorization | 0.88 | 0.95 |
| **D1 Personal data** | **0.88** | **0.58** |
| K1 Cache use | 1.00 | 0.80 |
| C5 Channel cost | 0.65 | 0.53 |
| R2 Limits | 0.68 | 0.54 |

Sonnet already plans these mainstream environments well without a card: every
plan chose the expected tier in both variants except the solo game (3/4 each).
The cards improve what they are specific about: fitting a UI framework to its
host, accurate platform claims and native access models. They cost what they
crowd out, and personal data drops again. The pattern matches E7, where a card
entry was the only thing that surfaced a layer's hidden property (0/15 to 3/3):
**cards earn their place through specific, checkable facts ("Claims to check",
host constraints, layer trust properties), not through general architecture
advice the model already has.** A leaner card that keeps only those sections is
the next thing to test.

The first control run could read the cards and did so in 22 of 32 trials; it
was discarded and rerun without access.

## Harness fixes found in this round

- Headless trials were starting every configured MCP server, including a
  Chrome DevTools server that opened a browser per trial. All runs now pass
  `--strict-mcp-config --mcp-config '{"mcpServers":{}}'`.
- 20 of the first 112 pilot plans were stubs ("I'll quickly check the project
  state…") from trials with no tools. Graded as written, they had deflated the
  scores to 0.67 and 0.74. Stubs are now rerun with the same prompt and excluded
  if they persist.

## Round 2: why the candidate lost privacy, and wording that keeps it

The first pilot's candidate improved proportion and connectivity but lowered
personal data (D1), untrusted callers (I4) and logs (D3). Four hypotheses, one
variant each, all built on the shipped block's first paragraph
([variants.py](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/round2/variants.py);
the exact blocks are the `block_*.txt` files next to it):

| Variant | Hypothesis | Change | Words |
| --- | --- | --- | --- |
| shipped | — | ShipLoop 0.36.0 | 258 |
| v1 | — | the first pilot's candidate (proportion, channel ladder, caching) | 416 |
| v2 | "Simplest" reads as permission to drop safeguards | v1 plus a floor: "Simplicity removes machinery, never safeguards" | 451 |
| v3 | Privacy is buried in one dense paragraph | a seven-item numbered decision list, safeguards as their own item | 569 |
| v4 | Length crowds concerns out | v3's content in fewer words | 377 |
| v5 | Failure visibility dropped in every variant | v2's floor plus "a record of every background failure that reaches whoever must act" | 464 |
| v6 | Synthesis of the leaders | v4 plus the floor, end-of-life and failure clauses | 418 |

Design: 19 scenarios (the 14 above plus a Docs sidebar, a record-page panel,
multi-tenant booking, oversell-proof registration and a payment webhook), each on
two of seven environments: 52 scenario-runtime cells. Every variant ran under one
condition: a Read tool from an empty directory, no MCP servers, and stubs rerun
with the same prompt. Shipped, v2, v4, v5 and v6 had two trials per cell (104
plans each); v1 and v3 had one (52 each). That makes 624 plans, all graded blind.
Judge reliability, from 40 plans graded twice: 91% of criterion grades agree, 39
of 40 tier calls agree, and a plan's score moves 0.04 on average.

| | shipped | v1 | v2 | v3 | v4 | v5 | v6 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Overall | 0.88 | 0.89 | 0.90 | 0.91 | 0.91 | 0.91 | 0.90 |
| Cells won / lost against shipped | — | 25 / 18 | 57 / 29 | 25 / 18 | 60 / 27 | 60 / 30 | 58 / 33 |
| Proportion | 0.92 | 0.95 | 0.96 | 0.97 | 0.97 | 0.97 | 0.97 |
| Solo tier (P1) | 0.67 | 0.75 | 0.83 | 0.83 | 0.92 | 0.83 | 1.00 |
| Overbuilt placement grades | 9 | 1 | 3 | 1 | 1 | 3 | 0 |
| Safeguards (D1–D4, I2, I4) | 0.85 | **0.78** | 0.88 | 0.81 | 0.87 | 0.85 | 0.86 |
| Connectivity | 0.79 | 0.88 | 0.84 | 0.95 | 0.87 | 0.86 | 0.88 |
| Caching | 0.93 | 1.00 | 1.00 | 1.00 | 0.99 | 0.98 | 0.92 |
| Failure visibility (O1) | 0.82 | 0.72 | 0.78 | 0.72 | 0.75 | 0.95 | 0.87 |
| Retention (D2) | 0.85 | 0.85 | 0.88 | 0.48 | 0.69 | 0.89 | 0.72 |
| Logs (D3) | 0.84 | 0.75 | 0.88 | 0.81 | 0.72 | 0.77 | 0.73 |
| Criteria 0.1 or more below shipped | — | 4 | 2 | 3 | 4 | **1** | 3 |

Full per-criterion table: [final_analysis.txt](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/round2/final_analysis.txt).

### What the evidence shows

1. **The privacy drop was a permission effect, and a floor fixes it.** v1
   reproduced the drop under the new condition: safeguards 0.85 to 0.78, with 19
   cells lost and 9 won. Adding one sentence to the same text (v2) raised
   safeguards to 0.88 and turned the paired result to 57 cells won and 29 lost.
   "Choose the simplest placement" is read as licence to simplify safeguards
   unless the text says otherwise. This is the same lesson as Code craft's
   "small, not thin" rule.
2. **Wording moves decisions; it plateaus on details.** Placement, tier and
   channel choice respond strongly and consistently. v6 put every one of its 104
   plans in the expected tier except three, with no overbuilt placement, and the
   solo game stays in the browser. Detail-level safeguards (retention, logs,
   runtime limits, UI interaction states) plateau around 0.6 to 0.9 however
   explicitly they are named: v6 names retention and scores 0.72; v2 does not
   and scores 0.88.
3. **Attention is roughly zero-sum at this length.** Every added emphasis gained
   its own criterion and cost a neighbour. v5's failure clause raised O1 from
   0.78 to 0.95 and lowered personal data. v3's structure raised idempotency to
   0.92 and dropped retention to 0.48; its "one sentence can do" permission made
   plans terse exactly where detail matters. The long structured list did not
   beat the prose.
4. **The leaders are statistically tied overall** (0.90 to 0.91, each winning
   about twice as many cells as it loses against shipped). Choose among them by
   which regressions are acceptable.
5. **Platform accuracy is a knowledge problem, not a wording problem.** Wrong
   claims ran from 2 (v3, 52 plans) to 15 (v2, 104 plans) without tracking any
   wording change.
   The Apps Script errors cluster on the same facts: that a script-properties
   update is not atomic without LockService, what `Session.getActiveUser()`
   returns under each deployment, and that executions run concurrently. Those
   facts belong in the Apps Script card.

### Recommendation

- **Ship v5** as the interaction-design block. It has the fewest regressions:
  only personal data falls by 0.1 (0.85 to 0.75), while failure visibility,
  untrusted callers, channel cost, runtime limits and proportion all rise.
  v6 is the alternative if proportion is the priority (solo tier 1.00, no
  overbuilt placement), accepting lower retention, logs and offline handling.
- **Check detail-level safeguards after planning, not by longer prompts.** Add
  the rubric's safeguard criteria (D1–D3, R2, O1) to the planning review focus,
  which reads the finished plan with nothing else to attend to. This is the next
  experiment: E6b showed the review stage catches what the plan stage misses
  (0/15 to 10/15 for platform claims).
- **Add the recurring Apps Script facts to its card**: LockService around
  properties read-modify-write, `getActiveUser()` behaviour per deployment
  setting, and concurrent executions.

## Shipped after round 2

ShipLoop 0.40.0 (skill-craft 1.7.0) ships v5 as the interaction-design block,
with one change from the tested text: the example "an opponent's fleet" became
"an opponent's hidden game state", to keep the packet generic. The Apps Script
card gained the facts plans kept getting wrong, each verified against Google's
documentation ([gas_facts.md](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/research/gas_facts.md)):
executions run concurrently up to a per-user cap; properties are not documented
as atomic, so a read-modify-write needs a LockService lock; `google.script.run`
is asynchronous; and `Session.getActiveUser()` returns a blank email wherever
the script runs without that user's authorization, including a web app that
executes as the developer. Google publishes no full table of `getActiveUser()`
results for every deployment and account type, so the card says to probe it.

## Harness: judge v2

A research pass ([prompt_research.md](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/research/prompt_research.md))
on LLM-as-a-judge reliability and on prompting for architecture decisions
recommended per-grade anchors, an evidence quote before every grade
(G-Eval-style form filling, evidence before verdict), criteria placed both
before and after the plan (long-context position effects), and paired bootstrap
confidence intervals. [judge2.py](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/judge2.py)
implements the first three; [round3/analyze.py](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/round3/analyze.py)
the fourth. Each judge call now times out after five minutes, retries up to
three times and logs a final failure instead of dropping it (a hung call had
stalled grading for fifteen minutes).

| | Judge v1 | Judge v2 |
| --- | --- | --- |
| Same grade when a plan is re-graded | 91% (40 plans) | 92% (30 plans) |
| Same tier when re-graded | 39/40 | 30/30 |
| Mean change in a plan's score when re-graded | 0.041 | 0.017 |
| Largest change | 0.25 | 0.068 |
| Mean score on the same 75 v5 plans | 0.910 | 0.909 |

Judge v2 is no stricter on average, so the earlier rounds stand, but a plan's
score is about 2.4 times steadier, which is what paired comparisons need.
Human calibration labels and a second judge family remain open.

The subject model in every round so far is Sonnet. ShipLoop's real host is Grok
(`grok-4.7`, medium effort); an isolated Grok runner
([run_grok.sh](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/run_grok.sh)) is
included but not yet validated, so no result here has been reproduced on Grok.

## Round 3: a planning review for detail safeguards

Round 2 found that wording plateaus on detail safeguards (retention, logs,
runtime limits, failure visibility). Round 3 tests checking them after planning
instead. The inputs are the 104 v5 plans from round 2 (52 cells, two trials).
Each was reviewed three ways, and each revised plan graded by judge v2 against
the unreviewed plan:

- **current**: ShipLoop's planning review focus as shipped (including the
  platform-claim bullet).
- **safeguards**: the current focus plus three bullets: personal data without a
  retention period, removal path or log exclusion; a runtime quota the design
  depends on but does not name; a background failure nobody who can act will
  see ([focus_safeguards.txt](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/round3/focus_safeguards.txt)).
- **prune**: safeguards plus a fourth bullet, "anything the plan adds that the
  request does not need (a feature, a store, sign-in, a live channel, a debug
  path, a higher placement tier): remove it", and the instruction to meet a
  finding by changing or removing what exists before adding anything, returning
  the plan unchanged when nothing needs fixing
  ([example prompt](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/round3/example_prompt_prune.txt)).

Every arm also had "change only what a finding requires; do not add features,
infrastructure or a higher placement tier". 415 of 416 plans were graded.

| | No review | current | safeguards | **prune** |
| --- | --- | --- | --- | --- |
| Overall | 0.911 | 0.904 | 0.937 | **0.944** |
| Change against no review (95% CI) | — | −0.007 [−0.022, +0.006] | +0.026 [+0.012, +0.039] | **+0.033 [+0.018, +0.047]** |
| Cells won / lost | — | 36 / 35 | 61 / 18 | **60 / 15** |
| Safeguards (D1–D4, I2, I4) | 0.83 | 0.83 | 0.98 | 0.95 |
| Detail targets (D1–D3, R2, O1) | 0.76 | 0.78 | 0.97 | 0.94 |
| Proportion (P1–P3) | 0.966 | 0.938 | 0.933 | **0.976** |
| Unrequested scope (P3 overbuilt grades) | 7 | 17 | 17 | **7** |
| State (S1–S4) | 0.93 | 0.93 | 0.95 | 0.96 |
| Platform errors | 3 | 8 | 5 | 6 |

Per criterion, the prune review raised personal data from 0.74 to 0.97, logs
from 0.77 to 1.00 and runtime limits from 0.68 to 0.92, with retention and end
of life also up. Full table: [round3/final_analysis.txt](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/round3/final_analysis.txt).

### What round 3 shows

1. **Checking after planning fixes what prompting could not.** Detail safeguards
   that plateaued around 0.75 under every wording rise to 0.94–0.97 when a
   review names them. The review reads a finished plan with nothing else to
   attend to, as E6b found for platform claims.
2. **A review adds scope unless told to remove it.** Both reviews without the
   pruning bullet more than doubled unrequested-scope grades (7 to 17) despite
   the "change only what a finding requires" guard, and grew plans by about
   half. A reviewer asked to find gaps treats adding as success. Naming removal
   as a finding, and preferring change over addition, brought scope back to
   the unreviewed level at almost no safeguard cost.
3. **The current review focus does not earn its cost on these criteria.** It
   leaves safeguards unchanged, lowers proportion (−0.029, significant) and
   more than doubles platform errors. Its value lies in the planning checks it
   was written for (replayable examples, weak checks, dropped requirements),
   which this rubric does not grade.
4. **Reviews introduce some platform errors** (3 to 5–8 across 104 plans). The
   claim-check bullet catches errors in the plan it reviews, not the ones it
   writes.

### Recommendation

Add the prune arm's four bullets and its "change or remove before adding"
instruction to ShipLoop's planning review focus. It is the only arm that
improves safeguards, state and overall score while leaving proportion and scope
where they were.

## Next

1. Ship the prune bullets in the planning review focus, then rerun this round's
   prune arm against the shipped text to confirm.
2. Validate the Grok runner and reproduce the v5 and prune results on Grok 4.7
   at medium effort, ShipLoop's real host.
3. A second judge family and a small human-labelled set, per criterion, for
   calibration.
4. Lean cards against full cards; more scenarios (mobile push, large exports,
   scheduled report email, audited admin console, feature-flag rollout).

## Scoring scale and decision rule (from 2026-09-27)

The evaluation harness spec ([skills/rubric-eval/SPEC.md](../skills/rubric-eval/SPEC.md),
sections 6–8) changed the scoring scale and the ship decision after round 3.
Round 4 and round 5 below report against the new rule; rounds 1–5 above stand
as written, on the old 0–1 scale, and none of them recorded tokens or time.

- **Scale.** Each criterion is graded met, partial or missed as before, now
  scored met = 2, partial = 1, missed or overbuilt = 0. A plan's score is the
  percentage of available points it earned over its applicable criteria — the
  same grades, the old 0–1 average times 100.
- **Paired comparison.** Arms are compared on the same scenario-runtime-trial
  cells: a 95% bootstrap interval (4,000 resamples, clustered by scenario, so
  a scenario's own runtimes and trials are not counted as independent) and a
  Wilcoxon signed-rank test over per-scenario means. Both must agree before a
  quality call is made either way.
- **Equivalence** means the whole interval sits within plus or minus the
  judge's own measured noise (its test-retest change, next table): a
  difference the judge cannot reliably tell from its own regrade is treated as
  no difference, not as a small win. Anything that is neither clearly better,
  clearly worse nor equivalent is inconclusive — the answer is more scenarios
  or trials, not a decision.
- **Priority.** A material quality difference decides the arm regardless of
  its cost. Only once quality is equivalent does token use decide between
  arms; only once tokens are equivalent too does wall-clock time decide. A tie
  at every level keeps the baseline — a change has to earn its place.

Judge reliability (SPEC section 7, test-retest on at least 30 plans each):

| Judge | Kappa | Band | Noise | Measured on |
| --- | --- | --- | --- | --- |
| Opus 5.5, medium | 0.835 | almost perfect | 2.07 points | 30 round-4 reviews |
| Sonnet | 0.759 | substantial | 1.69 points | 30 round-3 plans |
| Opus vs Sonnet | 0.443 | moderate | 7.3 points apart | same 30 round-4 reviews |

Each judge agrees with itself far more than it agrees with the other family,
which is why a round never mixes judges.

## Round 4: review pass wording, exploratory

Sonnet subject, Sonnet judge (exploratory, not a confirmation run). Suite:
[architecture](../skills/rubric-eval/suites/architecture), `review-bare` frame.
19 scenarios, 2 trials, 3 reviewed arms × 104 plans each (312 reviews); the
baseline **none** is the unreviewed round-2 v5 plan for each cell, an input
that costs nothing this round. Scores are the new points scale.

Each arm is a planning-review focus text:

- **current**: ShipLoop's shipped review focus — replayability, weak checks,
  dropped requirements, platform claims — unchanged from round 3.
- **design**: current, plus a second, separate review pass, judged against
  the request and spec, that checks personal data, an unnamed runtime limit,
  failure visibility and unrequested scope (round 3's "safeguards" and
  "prune" checks, but as their own pass rather than folded into the first).
- **prune3**: current's bullets and the design pass's four checks merged into
  a single review in one pass — round 3's "prune" arm, rerun here.

| vs the unreviewed plan (baseline 90.0 overall / 83.9 safeguards / 94.7 proportion / 92.8 state) | current | design | **prune3** |
| --- | --- | --- | --- |
| Overall | −0.9 [−3.3, +1.0] | +2.7 [+1.2, +4.0] | **+4.2 [+2.6, +5.7]** |
| Wilcoxon p | 0.687 | 0.0026 | **0.0022** |
| Cells won / lost | 41 / 41 | 54 / 26 | **64 / 19** |
| Safeguards | −0.4 [−3.4, +2.3] | +6.2 [+1.5, +10.7] | **+11.6 [+7.4, +16.0]** |
| Proportion | −3.7 [−7.3, −0.2] | +1.1 [−1.9, +3.9] | +0.6 [−1.7, +2.9] |
| State | +1.6 [−0.7, +3.6] | −1.4 [−3.3, +0.5] | +1.6 [+0.1, +3.1] |
| Overbuilt-scope grades (baseline 15) | 25 | 11 | 13 |
| Platform errors (baseline 8) | 6 | 4 | 4 |
| Decision | inconclusive; proportion guardrail regressed | ship: quality better | **ship: quality better** |

Headline: **prune3** raises overall by 4.2 points and safeguards by 11.6, the
largest safeguard gain of any arm tried against this baseline so far.
**design** also ships, at +2.7 overall. **current** — the shipped review as it
stands — is inconclusive on overall and regresses the proportion guardrail
(its interval lies wholly below zero), and both current and design more than
doubled unrequested-scope grades against the unreviewed baseline (15 → 25 and
15 → 11), the same "a reviewer treats adding as success" pattern round 3
found; prune3 keeps it closer to baseline (13).

### Diff check: does the review keep to the plan it was handed

A separate pass compared each arm's revised plan against the original v5
plan for four kinds of drift: dropping something the request needed
(`removed_required`), adding something it did not ask for
(`added_unrequested`), contradicting the original plan, and inventing a
number — a limit, a period, a count — with no source in the plan, the request
or a primary source. Complete: all 312 reviews (104 per arm), Sonnet judge.

| Per review | current | design | **prune3** |
| --- | --- | --- | --- |
| Removed required | 0.05 | 0.07 | 0.05 |
| Added unrequested | 0.50 | 1.01 | 1.14 |
| Contradictions | 0.22 | 0.18 | 0.15 |
| Invented numbers | 1.92 | 1.55 | 2.13 |

No arm is clean on this check. Prune3 removes what was required and
contradicts the original least often of the three, but it also adds the most
unrequested items and invents the most numbers per review (1.14 and 2.13);
design invents fewest (1.55) despite also gaining quality. Buying safeguards
and overall score with a review pass currently costs some invented specifics
and added scope, whichever of these three texts does the reviewing.

### Round 4 under the Opus judge

Opus 5.5 (medium effort) re-graded all 416 round-4 verdicts (312 reviews plus
the 104 unreviewed baseline plans), and a quote check — downgrade a met or
partial grade whose evidence quote is not an actual substring of the plan —
was applied on top. Same points scale, same baseline (the unreviewed plan):

| vs the unreviewed plan, Opus + quote check | current | design | **prune3** |
| --- | --- | --- | --- |
| Overall | +0.4 [−0.4, +1.2] | +2.8 [+1.3, +4.3] | **+4.1 [+2.2, +5.8]** |
| Wilcoxon p | 0.51 | 0.0016 | **0.0011** |
| Cells won / lost | 44 / 36 | 60 / 21 | **69 / 20** |
| Safeguards | −1.2 [−3.0, +1.0] | +8.0 [+3.7, +12.0] | **+14.3 [+9.1, +18.7]** |
| Proportion | +0.8 | +1.3 | +1.6 |
| Decision | near-identical to no review (within the judge's noise, ±2.07); tie keeps the baseline | materially better, but **blocked**: platform errors rose (+0.20/plan, 95% [+0.01, +0.40]; 97 vs 76 total) | **materially better** |

Judge acceptance: Opus test-retest kappa 0.835 (almost perfect, noise 2.07
points), Opus-vs-Sonnet kappa 0.443 (moderate). Against the Sonnet-judged
table, prune3 and current land on the same decision (win; no win); design
flips from a win under Sonnet to blocked under Opus, on the same quality
verdict: a stricter reading of its platform claims, not a disagreement about
whether the text helps. The owner kept Opus as the round's judge; the flip is
recorded rather than resolved by picking whichever judge agrees with the
wording under review.

**Quote check, corrected.** A first version of the quote check matched quotes
after collapsing only whitespace and markdown. It flagged 5.2% of Sonnet's met
or partial grades as unsupported (prune3 6.9%, unreviewed plans 3.5%) and cut
prune3's lead under Sonnet to +2.7 points. The adversarial review of the check
(F4) pointed out that curly apostrophes, dashes and commas would fail a true
quote. With every non-alphanumeric character normalised, the check lowers 17
of Sonnet's grades and 11 of Opus's across 416 verdicts each, and prune3 stays
at +4.1 points under both judges. The earlier 5.2% was a matching artifact;
both judges quote the plan accurately.

**Conclusion for round 4.** Prune3's gain holds across two judge families and
the quote check, but it is also the arm that invents the most
unsourced numbers and adds the most unrequested items. The next candidate
(v3) keeps prune3's wording and adds a number-sourcing check and a
no-unrequested-additions check, to be confirmed in round 6 (Grok subject,
Opus judge, quote check, tokens and time recorded).

## Adversarial review of the scoring change (2026-09-27)

The standard scale, the quality > tokens > time rule, the quote check and the
Grok tool lockdown were reviewed by Grok 4.7, a different family from their
author. Grok had its tools locked down for this review; an earlier pass started
before the lockdown was stopped and discarded. Eight findings, six high:

| Finding | Held? | Experiment or reason | Change |
| --- | --- | --- | --- |
| F1 A significant difference inside the judge's noise won on quality | Held | Fixture: +0.8 [+0.2, +1.5], p = 0.01, noise 2.07, fewer tokens → was a quality win | Near-identical is checked first; wins need the rank test on the same side |
| F2 Cost wins and blockers used the bootstrap alone | Partly | Cost wins now need both tests | Harm blockers keep the interval alone, a stated asymmetry |
| F3 The `na` z-test treated grades as independent | Held | Grades nest in plans and scenarios | Stub and `na` rates compared paired per output |
| F4 The quote check failed on punctuation and left `criteria[c].grade` stale | Held | Full normalisation: lowered grades fell from 329 to 17 (Sonnet), 44 to 11 (Opus); prune3 back to +4.1 | Normaliser fixed; both grade fields updated |
| F5 `reliability` compared unchecked with checked grades | Held | Would bias future noise figures | Both sides checked before comparing |
| F6 Grok isolation checked only against a mock | Tested | Live: no shell, no file reads, no state across calls; `list_dir` can list other directories by name | Limit recorded |
| F7 Missing usage stored as 0 | Held | Would count a missing report as free | Stored as unknown and excluded |
| F8 "won" read backwards for costs; blocked reasons led with "better" | Held | Wording | `arm_higher`/`arm_lower`; blocks listed first |

Round 4's decisions are unchanged under the corrected rule, under both judges.

## Round 5: design-thinking arms, exploratory

Sonnet subject, Sonnet judge; exploratory. Suite:
[architecture-v2](../skills/rubric-eval/suites/architecture-v2) — adds T1
threat model, L1 load and X1 cross-runtime integration to the rubric — `plan`
frame, 13 scenario-runtime cells (including three cross-runtime scenarios), 3
trials. Baseline **base** is the shipped interaction-design block; the other
four arms each add a design-thinking step on top of the previous one:

- **expand**: base plus an interaction-and-threat-model paragraph — map every
  hop between actors and runtimes, derive the load it implies and a threat
  per hop — with no pruning step.
- **expprune**: expand plus a prune-against-the-request-and-spec paragraph
  (KISS/YAGNI: remove what no stated requirement, load or threat needs; keep
  the safeguards and every control a threat needs).
- **outcome**: expprune, framed by an intent-and-outcome statement up front
  and an outcome-grading pass at the end (met/partial/missed per outcome).
- **negative**: outcome plus explicit non-goals and "wrong turns" to avoid,
  checked again at the end.

| vs base (guardrails: proportion, safeguards) | expand | expprune | outcome | negative |
| --- | --- | --- | --- | --- |
| Overall | −0.00 [−0.03, +0.03] | +0.00 [−0.02, +0.03] | +0.00 [−0.03, +0.03] | +0.02 [−0.01, +0.07] |
| Safeguards (guardrail) | −0.03 [−0.10, +0.04] | −0.04 [−0.10, +0.03] | −0.03 [−0.09, +0.02] | **−0.10 [−0.21, −0.01]** |
| Won / lost, safeguards | 7 / 8 | 6 / 14 | 7 / 14 | **4 / 15** |
| Proportion (guardrail) | −0.03 [−0.08, +0.01] | +0.01 [−0.02, +0.05] | −0.00 [−0.04, +0.04] | +0.04 [−0.00, +0.10] |
| Threat (T1) | +0.33 [+0.24, +0.43] | +0.32 [+0.21, +0.42] | +0.35 [+0.26, +0.43] | +0.24 [+0.13, +0.35] |
| Load (L1) | +0.09 [−0.06, +0.26] | +0.16 [+0.04, +0.32] | +0.13 [+0.04, +0.25] | +0.17 [+0.04, +0.30] |
| Integration (X1, n=8–9) | +0.11 [0.00, +0.17] | −0.11 [−0.50, +0.17] | +0.13 [0.00, +0.17] | +0.00 [−0.33, +0.17] |
| Overbuilt-scope grades (base 5) | 8 | 3 | 5 | 0 |
| Decision | not ship: overall not established; both guardrails soft; overbuilt rose 5→8 | not ship: overall not established; safeguards guardrail soft | not ship: overall not established; safeguards guardrail soft | not ship: overall not established; safeguards guardrail soft |

Threat-modeling gains are large and consistent — +0.24 to +0.35 on the old
0–1 scale — in every arm that adds the threat-model paragraph. Load gains are
smaller and noisier (+0.09 to +0.17; expand's interval still crosses zero).
Integration has too few applicable cells (8–9) to read: expprune's interval
alone spans −0.50 to +0.17. Safeguards drop in every design-thinking arm,
worst in **negative** (−0.096, 4 cells won against 15 lost) — the arm with
the most added text and the most explicit "name what should not happen"
framing. Overall stays flat in all four; every overall interval straddles
zero.

**Conclusion.** Added reasoning about threats and load displaces concrete
safeguards unless it is grounded in the request and checked for side effects
against it — the same displacement round 2 found between channel/caching
detail and privacy, now showing up one level higher, in a reasoning step
rather than a wording change.

## Learnings so far

- Wording moves the big decisions — placement, tier, channel — far more than
  it moves the details; detail-level safeguards plateau under every wording
  tried in rounds 2–3.
- A check applied after drafting beats an instruction added while drafting:
  round 3's reviews fixed detail safeguards that no round-2 wording reached.
- A step written to "find what's wrong" adds scope unless removal is named
  explicitly: round 3's current and safeguards arms doubled unrequested-scope
  grades, and round 4's diff check shows every review arm still adding
  unrequested content.
- More text competes for the same attention: an emphasis added to one concern
  costs a neighbouring one (round 2's zero-sum result; round 5's
  design-thinking arms trading safeguards for threat and load coverage).
- The judge rewards a specific, unsourced number over a vaguer, correct one —
  round 4's diff check found every review arm inventing numbers per review,
  most often the arm (prune3) that otherwise scores best.
- Expand-then-prune works — round 4's prune3, round 5's expprune both beat
  their less-pruned neighbours — while a negative framing ("what should not
  happen") over-prunes safeguards instead, as round 5's negative arm shows.
- Two judges each agree with themselves far better than with each other
  (Opus kappa 0.835, Sonnet kappa 0.759, Opus-vs-Sonnet kappa 0.443): never
  mix judges within a round, and expect a close decision to move when the
  judge changes even when the quality verdict does not.

## Rounds 6 and 7: design review checks for plan and step-plan reviews (shipped in ShipLoop 0.47.0)

The detailed journal and evidence are in the private research repository
[shiploop-prompt-lab](https://github.com/whichguy/shiploop-prompt-lab/blob/main/journal.md). The method is in
[skills/rubric-eval/SPEC.md](../skills/rubric-eval/SPEC.md).

**Change.** `DESIGN_REVIEW_CHECKS` is attached to plan and step-plan Improve
reviews after `PLANNING_REVIEW_FOCUS`. It checks personal data, quotas,
background failures and unrequested additions. It ends with a self-check that
keeps a change only when it serves a named request, spec clause or directive,
and that never removes or weakens a safeguard. A number without a source is
marked as an assumption.

**Round 6** (grok:grok-4.7@medium reviews of Grok plans, reference files
open, Opus judge in 3 passes, 16–17 scenarios per arm):
- The grounding self-check made reviews help: v3 scored **+3.8** [+0.4, +7.1]
  against the unreviewed plan (p = 0.044).
- A lean checklist without the self-check leaned worse than no review
  (−3.3, and it failed the proportion guardrail).
- Every review arm cut about 2 valuable items per review. The value audit
  found this; it led to v4's removal rule.

**Round 7** is the confirmation, run inside the real ShipLoop plan-stage
packet: its 29 reference locators and the verbatim plan-stage Improve prompt.
- **Condition:** codex:gpt-6-luna@max reviews of the same 23 plans; Opus judge
  in 3 passes (noise 2.2 per pass); suite architecture-v4.
- **v4 against the wording ShipLoop shipped before:**
  - overall **+5.1** [+3.0, +7.2], Wilcoxon p = 0.0006, 17 won / 3 lost;
  - safeguards **+9.4**; proportion +2.9; grounding +8.3;
  - **1.09 fewer valuable items removed per review** (p = 0.008).
- **The previous wording** was no better than no review (−0.4) and cost
  safeguards (−12.7).
- **Naming the runtime's platform card on top of v4** made no difference
  (+0.2), so it did not ship.
- **Evidence:** [rounds/round7](https://github.com/whichguy/shiploop-prompt-lab/blob/main/rounds/round7/).

**Measurement lessons** (all now in the SPEC):
- a single grading pass is too noisy for long outputs;
- every host needs audited isolation;
- rigour is judged against an enterprise standard, and only unrequested
  product scope counts as overbuilding;
- quality decides first, and tokens only between near-identical arms.
