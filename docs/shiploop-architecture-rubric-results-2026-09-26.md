# Architecture rubric results — 2026-09-26

First runs against the [architecture rubric](shiploop-architecture-rubric.md):
a 14-scenario pilot on the hosted runtimes, and a platform-card experiment on
four general deployments. Harness, fact sheets and every verdict:
[experiments/shiploop-architecture-rubric](experiments/shiploop-architecture-rubric/).

Sonnet for trials and judge; blind grading, one plan at a time; scores are
met = 1, partial = 0.5, missed or overbuilt = 0, averaged over applicable
criteria. Small samples (two trials per scenario, runtime and variant): read
differences under about 0.1 as noise unless they repeat across experiments.

## Pilot: shipped text against a proportion-and-channels candidate

14 scenarios × 2 of {Apps Script, Salesforce, Cloudflare Workers} × 2 variants ×
2 trials = 112 plans (111 graded; one stayed a stub after three reruns and was
excluded). The **shipped** variant is ShipLoop 0.35.0's interaction-design
block. The **candidate**
([text](experiments/shiploop-architecture-rubric/candidate_interaction_design.txt))
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
([variants.py](experiments/shiploop-architecture-rubric/round2/variants.py);
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

Full per-criterion table: [final_analysis.txt](experiments/shiploop-architecture-rubric/round2/final_analysis.txt).

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
documentation ([gas_facts.md](experiments/shiploop-architecture-rubric/research/gas_facts.md)):
executions run concurrently up to a per-user cap; properties are not documented
as atomic, so a read-modify-write needs a LockService lock; `google.script.run`
is asynchronous; and `Session.getActiveUser()` returns a blank email wherever
the script runs without that user's authorization, including a web app that
executes as the developer. Google publishes no full table of `getActiveUser()`
results for every deployment and account type, so the card says to probe it.

## Harness: judge v2

A research pass ([prompt_research.md](experiments/shiploop-architecture-rubric/research/prompt_research.md))
on LLM-as-a-judge reliability and on prompting for architecture decisions
recommended per-grade anchors, an evidence quote before every grade
(G-Eval-style form filling, evidence before verdict), criteria placed both
before and after the plan (long-context position effects), and paired bootstrap
confidence intervals. [judge2.py](experiments/shiploop-architecture-rubric/judge2.py)
implements the first three; [round3/analyze.py](experiments/shiploop-architecture-rubric/round3/analyze.py)
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
([run_grok.sh](experiments/shiploop-architecture-rubric/run_grok.sh)) is
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
  see ([focus_safeguards.txt](experiments/shiploop-architecture-rubric/round3/focus_safeguards.txt)).
- **prune**: safeguards plus a fourth bullet, "anything the plan adds that the
  request does not need (a feature, a store, sign-in, a live channel, a debug
  path, a higher placement tier): remove it", and the instruction to meet a
  finding by changing or removing what exists before adding anything, returning
  the plan unchanged when nothing needs fixing
  ([example prompt](experiments/shiploop-architecture-rubric/round3/example_prompt_prune.txt)).

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
of life also up. Full table: [round3/final_analysis.txt](experiments/shiploop-architecture-rubric/round3/final_analysis.txt).

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
