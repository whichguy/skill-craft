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

## Next

1. Candidate v2: keep proportion and channels, restore personal data and
   untrusted callers; rerun the pilot catalog.
2. Lean cards: only current facts, claims to check and host or layer
   constraints; rerun the card experiment.
3. New scenarios listed in the rubric: an add-on sidebar bound to one
   document, a record-page component, multi-tenant SaaS, capacity-limited
   registration, and a payment webhook receiver.
