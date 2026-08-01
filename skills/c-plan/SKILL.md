---
name: c-plan
description: |
  Resolve ambiguous user prompts by choosing whether to answer now,
  answer with assumptions, ask 1–2 high-value clarification questions,
  replan, or stop. Use when the best response depends on hidden intent,
  audience, scope, constraints, risk, output format, or desired depth.
allowed-tools: all
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: prompt-only
---

> **skill-craft port** of the claude-craft planning-suite skill. Host-neutral: use repo-root search instead of Claude plugin paths. SoT: this package under whichguy/skill-craft.


# Bayesian Clarifier

## Purpose

Produce the best useful answer with the fewest clarifying questions.

Default mode is `normal`.

Do not turn ordinary prompts into discovery interviews. Run only the lightest process that improves the answer.

Core hierarchy:

```text
Possible meanings seed the search.
Families/facets allocate search breadth.
Questions compete on expected value.
Response plans decide action.
```

Core control law:

```text
Ask only when EVQ > best(answer now, answer with assumptions, compare top interpretations) + friction/delay/complexity cost.
```

Where:

```text
EVQ = expected value of question
ΔAnswer = how much the final answer changes if uncertainty is resolved
```

Information gain is useful, but it is only one input to EVQ. Do not ask a question merely because it is interesting or uncertainty remains.

## Four Gates

Use these gates in order.

```text
1. FASTPATH GATE
   Can I answer now?

2. EVQ GATE
   Is asking, researching, tool use, or agent delegation better than answering with assumptions?

3. REPLAN GATE
   Did new evidence change the task shape?

4. PLAN DELTA GATE
   If replanned, does the new response plan materially beat the incumbent?
```

Everything else supports these gates.

## Runtime Vocabulary

Use these symbols internally:

```text
H  = hypothesis / possible meaning
F  = family / facet / uncertainty axis
Q  = probe / candidate clarification question
B  = branch / possible answer to Q
E  = evidence / user answer or stated constraint
R  = response plan / answer strategy before final prose
T  = tombstone / ruled-out path with resurrection condition
TC = terminal condition / reason to stop asking
```

Runtime kernel:

```text
FASTPATH
  → if ambiguity matters: lightweight H sketch
  → F/facet breadth scan
  → family-weighted Q budget if needed
  → branch-simulate representative Qs
  → EVQ Gate
  → ask user / run selected agent(s) / use tools / answer with assumptions
  → E update
  → Replan Gate
  → Plan Delta Gate if replanned
  → T only if useful
  → choose R
  → TC
  → final answer
```

In normal mode, keep H/F/Q/B/E/R/T implicit unless needed. Think compactly; answer quickly.

## Modes

Use the lightest mode that can produce a good answer.

Escalate only for the current turn or unresolved fork. De-escalate immediately once enough evidence exists.

```text
normal:
  0–1 clarification round
  3–5 internal Q candidates only if needed
  no formal state

structured:
  0–1 clarification round
  7 internal Q candidates
  lightweight H/F/Q/B/R internally

deep:
  up to 2 clarification rounds
  13 internal Q candidates
  explicit H/F/Q/B/E/R/T if useful
  optional state file

discovery:
  up to 3 rounds only if the user asks for discovery/interview/requirements work
```

Deep mode requires explicit user request, high-stakes task, artifact-level output, complex multi-turn work, or materially ambiguous task where premature answering would likely produce the wrong result.

## Gate 1 — FASTPATH

Use FASTPATH when the prompt is clear enough, ambiguity is low-impact, or user momentum matters.

Behavior:

```text
Answer directly.
Optionally state one key assumption.
No state file.
No formal tables.
```

Escalate only if a missing fact would materially change the response.

## Gate 2 — EVQ: Expected Value of Next Action

Before asking or researching, compare actions:

```text
A1 answer now
A2 answer with assumptions
A3 compare top interpretations
A4 ask one Q
A5 ask two Qs
A6 run Explore for repo/codebase evidence
A7 run WebResearch for current external evidence
A8 run another selected agent whose description/tools fit the evidence gap
A9 run multiple selected agents in parallel when evidence streams are independent
A10 constrained / warning / refusal if risk boundary exists
```

Ask or research only if that action clearly beats answering or assumption-answering.

Use this practical EVQ judgment:

```text
EVQ =
  expected response-plan improvement
  + risk avoided
  + contrary/minority-rescue value
  + correctness/freshness gain if research is needed
  - friction/delay/complexity cost
  - token/tool cost
  - source reliability risk
```

Approximate question value:

```text
question_value =
    information_gain
    × ΔAnswer
    × risk_if_wrong
    ÷ user_friction
    + contrary_or_minority_rescue_bonus
```

Use qualitative bands in normal mode:

```text
high / medium / low
```

Ask only when:

```text
high ΔAnswer
and low enough friction
and answer would change R
```

Do not ask, research, or spawn agents because a field is blank.

## Research / Agent Assist Gate

Treat agents as evidence/action helpers inside EVQ, not as separate workflows.

Parent remains controller.

```text
Ask the user for intent/preference.
Ask Explore for repo/codebase truth.
Ask WebResearch for current external truth.
Ask any other suitable agent for its specialized evidence or review.
Parent decides the final answer.
```

Use research or agent delegation only when:

```text
Agent_EVQ > best(answer now, answer with assumptions, ask user, direct parent work) + friction/delay/complexity/tool cost
```

### Agent Action Selector

```text
Missing evidence / work type          Best action
------------------------------------------------------------------
User intent / preference              Ask user
Repo structure / code behavior        Explore
Current docs / external facts         WebResearch
Architecture / design critique        Architect / planner / reviewer agent if available
Security or risk review               Security reviewer agent if available
Test strategy / failure analysis      Test/debug agent if available
Docs / writing review                 Documentation agent if available
Repo + current docs                   Explore + WebResearch if independent
Low-impact uncertainty                Answer with assumptions
High-risk uncertainty                 Ask, research, or delegate before answering
```

### Use Explore When

```text
answer depends on existing code behavior
repo structure or conventions matter
implementation touches multiple files
file discovery or code search is needed
current parent context lacks code evidence
```

Explore should be read-only and return evidence, not final prose.

### Use WebResearch When

```text
answer depends on current docs or external facts
version behavior may have changed
API/library/product status matters
security advisories or release notes matter
market/pricing/recommendations matter
user asks to research, verify, latest, docs, Reddit/forums, or current information
```

Prefer official or primary sources first.

### Use Other Agents When

Use any available agent when its description, tool access, and specialization match a material evidence gap better than the parent can handle directly.

Examples:

```text
architect/planner agent:
  compare response plans, architecture options, tradeoffs

security reviewer agent:
  identify threat/risk/compliance concerns

test/debug agent:
  inspect failure paths, logs, repro strategy

docs/writer agent:
  improve docs, examples, user-facing clarity

code reviewer agent:
  review implementation quality, maintainability, regressions
```

Do not delegate just because an agent exists. Delegate only when the agent has higher EVQ than direct parent work.

**In this repo:** `Explore` is built-in. `code-reviewer` (review-suite) covers code review and security-adjacent work. `system-architect` (planning-suite) covers planner/architect work. `qa-analyst` (planning-suite) covers test/debug strategy. There is no dedicated `WebResearch`/`web-researcher`, `security-reviewer`, or `docs-writer` agent — treat references to those as capability descriptions, not literal agent names. Use `WebSearch`/`WebFetch` tools directly for external research instead of spawning a `web-researcher` subagent.

### Parallel Agent Work

Run multiple agents in parallel only when their evidence streams are independent and each has a distinct question.

Good:

```text
Explore: how this repo currently handles auth
WebResearch: current docs/best practices for the auth library version
Security reviewer: risks in the proposed auth change
```

Bad:

```text
multiple agents reading the same files without distinct questions
multiple agents producing final answers independently
agents launched because they are available, not because EVQ warrants them
```

### Agent Evidence Packet Contract

Agents return compact evidence packets only:

```text
1. direct finding
2. sources: file paths/line refs or URLs
3. confidence: high / medium / low
4. conflicts, uncertainty, or staleness
5. impact on R
6. recommended next action
7. open questions, if any
```

Agents must not:

```text
write the final answer unless explicitly assigned
edit files unless explicitly authorized by parent/user
ask the user unless explicitly authorized
return raw scratch work
keep browsing/exploring after evidence is sufficient
expand scope beyond assigned question
```

### Agent Selection Rules

Use the most specific suitable agent available.

Prefer:

```text
read-only agents for research/review
specialized agents over general-purpose agents when fit is clear
general-purpose only when no specific agent fits
parallel agents only for independent evidence streams
```

When selecting an agent, check:

```text
description matches the task
tools are appropriate and not excessive
agent can return compact evidence
expected value exceeds overhead
```

Use built-in Explore for codebase research.

Use or create a custom `web-researcher` agent for web research:

```text
name: web-researcher
purpose: current external evidence
allowed tools: WebSearch, WebFetch
output: evidence packet only
sources: official/primary first
```

If using forked skill execution, the skill body must contain an explicit task. Passive guidelines alone are not enough for a useful forked run.

## Possible Meanings / Hypotheses

Use H as lightweight scaffolding, not ceremony.

H answers:

```text
What materially different meanings could this prompt have?
```

Relationship:

```text
H = possible worlds
F = axes where those worlds differ
Q = probes that test the highest-value differences
R = action chosen after evidence
```

If the prompt is clear, skip explicit H and answer.

If ambiguity matters:

```text
normal: infer 2–4 likely Hs silently
structured: sketch 3–5 Hs if needed
deep: generate 3–7 explicit Hs
```

Each H must imply a different answer. Avoid trivial variants.

For each meaningful H, know just enough:

```text
label
answer implication
what would confirm it
what would disconfirm it
```

Use H only to seed F and R. If F/Q generation already makes the possible meanings obvious, do not separately materialize H.

Preserve plausible minority Hs until a disconfirming Q has been considered.

## Families / Facets

Use F to define breadth, not final judgment.

F is an uncertainty axis separating Hs.

Useful F examples:

```text
audience / user type
scope / ambition
job-to-be-done
maturity level
output format
implementation target
risk / compliance / safety
data / integration
cost or time constraint
```

Rule:

```text
Use F to allocate candidate-Q budget.
Use Q scoring to choose actual Qs.
Use R scoring to decide action.
```

Do not deeply score F. Do not let one F consume all candidate budget. Do not sum redundant Qs inside one F.

Lightly rate F only enough to allocate exploration:

```text
ΔAnswer: high / medium / low
Risk-if-wrong: high / medium / low
Answerability: high / medium / low
Friction: high / medium / low
Minority-rescue value: yes / no
Redundancy: high / medium / low
```

Ignore F with low ΔAnswer and low risk unless it has strong minority-rescue value.

## Family-Weighted Q Budget

Use formal family-weighted allocation only in structured/deep mode, or when normal FASTPATH is clearly insufficient.

Normal mode usually does not need formal allocation. Think of 3–5 ad hoc Q candidates, then ask only if EVQ beats assumption-answering.

Budgets:

```text
normal:      3–5 ad hoc internal Q candidates, no formal allocation unless needed
structured:  7 internal Q candidates weighted across F/facets
deep:        13 internal Q candidates weighted across F/facets
```

Allocation heuristic:

```text
High-value F:    2–3 Q candidates
Medium-value F:  1–2 Q candidates
Low-value F:     0–1 Q candidates
Ignored F:       0 Q candidates
```

Caps/floors:

```text
max 3 Qs per F
min 1 Q for high-value F
min 1 Q for strong minority-rescue F
0 Q for low ΔAnswer + low risk F
```

Optional deep-mode approximate weight:

```text
F_weight ≈
    ΔAnswer
    × Risk-if-wrong
    × Answerability
    ÷ Friction
    - Redundancy
    + Minority-rescue bonus
```

Use H/M/L bands by default. Numeric-looking weights are only rough ordering aids, not calibrated scores.

Question funnel:

```text
Generate broad F set.
Allocate Q candidates across F.
Generate Qs inside each F.
Dedupe near-equivalent Qs.
Keep best representative Q per useful F.
Branch-simulate representatives.
Deep-score top 3–7 representative Qs.
Ask top 0–2 non-redundant Qs.
```

Operating principle:

```text
Generate many lightly.
Score few deeply.
Ask almost none.
```

## Candidate Questions

Every Q must pass this test:

```text
Would different answers produce meaningfully different final responses?
```

If not, discard the Q.

For each serious Q, know:

```text
question text
F
answer choices
what each answer changes in R
which H/R each answer supports
which H/R each answer weakens
friction
whether it disconfirms current top H/R
whether it rescues a plausible minority H/R
```

Prefer world-splitting Qs over detail-tuning Qs.

Bad early Q:

```text
Do you want dark mode?
```

Good early Q:

```text
Is this mainly for personal use, a team workflow, or integration into another product?
```

## Counterfactual Branches

Before asking a serious Q, simulate B branches.

Do not ask Q unless at least one B would materially disconfirm the current plan or rescue a plausible minority plan.

Use four B types:

```text
Expected B:
  answer most likely under current top H/R

Contrary B:
  answer that weakens or disproves current top H/R

Minority-rescue B:
  answer that makes a low-probability H/R important

Ambiguous B:
  answer such as "not sure", "both", or "it depends"
```

For each B, estimate qualitatively:

```text
which H/R gains
which H/R loses
what answer path changes
what gets tombstoned
what could be resurrected
```

Use likelihood-style thinking when helpful:

```text
Estimate P(answer | hypothesis), then update belief from prior × likelihood.
```

Do not pretend probabilities are calibrated. Use qualitative movement in normal mode.

## IG as EVQ Input

Use information gain as an input to EVQ, not as the final decision.

Deep-mode approximation:

```text
IG(Q) = prior_entropy - weighted_expected_posterior_entropy
```

Where:

```text
weighted_expected_posterior_entropy =
  sum over B: P(B) × entropy(posterior after B)
```

Contrary branch value:

```text
contrary_branch_score =
    P(contrary B)
    × drop in current top H/R if contrary B occurs
    × risk avoided if current top H/R was wrong
```

Minority-rescue value:

```text
minority_rescue_score =
    plausibility
    × risk_if_missed
    × response_plan_delta
```

A strong Q usually has:

```text
high ΔAnswer
high contrary or minority-rescue value
low friction
```

A Q that only confirms the current favorite is usually refinement, not clarification.

## Evidence Update

After the user answers:

```text
record E
update H/R confidence
reduce contradicted H/R
check T resurrection
run Replan Gate
refresh R
run Plan Delta Gate if replanned
check TC
answer unless another Q clearly wins EVQ
```

Do not loop just because uncertainty remains.

## Gate 3 — Replan

Every E updates state. Not every E triggers replan.

Replan only when E changes the task shape.

Replan triggers:

```text
current top H/R is contradicted
new high-impact constraint appears
T path is resurrected
new hybrid path appears
risk / privacy / compliance boundary appears
current R no longer dominates
current Q set is obsolete
user changes desired output or success criteria
```

Replan levels:

```text
Level 0: no replan; update E only
Level 1: local replan; adjust R only
Level 2: regenerate F/Q because new uncertainty axis appeared
Level 3: regenerate H/F/Q/B/T/R because task meaning changed
```

Use the lightest replan level that restores a good answer path.

## Gate 4 — Plan Delta

After replanning, do not automatically follow the new plan.

Compare incumbent R vs best new R.

Qualitative gate:

```text
materially better → switch
slightly better → hybridize/caveat
not better → keep incumbent
close + high ΔAnswer/risk → ask one plan-separating Q
```

Deep-mode conceptual test:

```text
plan_delta =
    best_new_R_score
    - incumbent_R_score
    - switching_cost
```

Switching cost includes:

```text
lost momentum
extra complexity
extra user friction
more verbose answer
risk of overfitting to one ambiguous answer
implementation burden
```

After replanning, score Q by plan separation:

```text
post_replan_question_value =
    plan_separation
    × ΔAnswer
    × risk_if_wrong
    ÷ user_friction
```

A good post-replan Q separates top R plans, not merely top Hs.

## Tombstones

Use T mostly in structured/deep or multi-turn work.

T records a discarded path without forgetting how to revive it.

Format:

```text
item
type: hypothesis | family | question | assumption | response_plan
reason ruled out
confidence
resurrection condition
```

Example:

```text
Item: Team accountability SaaS
Reason: User said this is for personal use.
Resurrection: user later mentions managers, teams, shared progress, roles, or reporting.
```

Tombstones are reversible.

## State File

Only create state for deep, complex, high-stakes, artifact-level, or multi-turn work.

Preferred path:

```text
<host-data-dir>/c-plan/<slug>/state.md
```

Record only useful state:

```text
original prompt
current objective
H
F
Q/B considered
questions asked
E
T
R
TC
final assumptions
```

State files are for durable decisions, not transient exploration.

State files should summarize decisions, not store raw reasoning, scratch work, or long candidate lists.

Do not persist secrets, credentials, or sensitive private data unless necessary and appropriate.

## LLM Leverage Techniques

Use only when they improve quality without making the interaction heavy.

### Skeptic Pass

Ask:

```text
What assumption could be wrong?
What user answer would invalidate current R?
What minority H/R am I underweighting?
```

Use to generate contrary B and prevent premature convergence.

### Branch Simulation

Before asking Q:

```text
If user says A → answer path 1
If user says B → answer path 2
If user says "both/not sure" → assumption or comparison path
```

Discard Q if B outcomes do not materially change R.

### Pairwise Plan Comparison

When R plans are close, compare pairwise:

```text
Which R better fits E?
Which R has lower risk if wrong?
Which R preserves momentum?
What one fact would decide between them?
```

Prefer this over global ranking.

Advanced techniques — self-consistency sampling, red-team review, assumption ledger, decision journal, compression-before-return — belong in companion docs or deep mode, not normal runtime.

## Subagents / Forked Context

Use any available subagent or forked context only when its EVQ beats direct parent work.

Default rule:

```text
normal mode: avoid subagents unless evidence/action gap is clearly material
structured mode: use selected agents when evidence gaps are material
deep mode: use selected agents/forked context for noisy independent work
```

Useful delegations:

```text
Explore: repo/file/codebase research
WebResearch: current external evidence
planner/architect: architecture and tradeoff review
security reviewer: threat/risk/compliance review
test/debug agent: failure analysis and test strategy
docs/writer agent: docs clarity and examples
skeptic reviewer: hidden assumptions and contrary branches
question generator: family/facet discovery and Q candidates
response-plan reviewer: pairwise R comparison
```

Parent remains controller.

Subagents return evidence packets or compact summaries only.

The parent should merge results, resolve conflicts, update R, and produce the final answer.

Do not use subagents for tiny decisions where delegation overhead exceeds value.

## Terminal Conditions

Stop asking and answer when any TC is true:

```text
TC1: one R clearly dominates
TC2: best remaining Q/research action has low ΔAnswer / low EVQ
TC3: top Hs lead to substantially the same answer
TC4: friction/delay/complexity cost exceeds expected improvement
TC5: loop budget reached
TC6: user says proceed / best guess / good enough
TC7: safety or policy boundary requires constrained answer
TC8: user answer is partial but sufficient for useful response
TC9: evidence packet is sufficient; stop researching/delegating
```

Never keep asking just to fill blanks.

Some uncertainty is acceptable.

## Final Answer Pattern

When assumptions matter:

```text
I’ll assume <primary assumption>.
If <alternate interpretation>, the main change would be <delta>.
Under that assumption...
```

When prior clarification ruled out branches:

```text
Given your answer, I’m treating <branch> as out of scope unless you later mention <resurrection condition>.
```

Keep the final answer focused on the user’s task, not this machinery.

## Quality Bar

A successful run should:

```text
answer simple prompts directly
use H as lightweight scaffolding
use F/facets for breadth, not over-analysis
use EVQ, not raw IG, to decide asking
ask fewer but better questions
avoid premature convergence
avoid endless clarification
preserve momentum
state assumptions when useful
produce a better final response than guessing
```

## Minimal Invocation

Default mode is normal.

Normal use:

```text
Use c-plan. FASTPATH first; ask/research/delegate only if EVQ beats assumption-answering; otherwise answer.
```

Structured use:

```text
Use c-plan in structured mode. Generate 7 internal Q candidates weighted across F/facets, branch-score representatives, ask at most two non-redundant Qs, then answer.
```

Deep use:

```text
Use c-plan in deep mode. Generate 13 internal Q candidates weighted across family/facet space, maintain H/F/Q/B/E/R/T state only if useful, use EVQ and counterfactual branch scoring, run selected agents for material evidence gaps, replan only when task shape changes, run Plan Delta Gate after replanning, and stop when a terminal condition fires.
```
