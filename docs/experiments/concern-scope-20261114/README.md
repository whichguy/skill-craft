# Concern-scope study (2026-11-14)

Journal: E23 in [docs/shiploop-question-driven-planning-journal.md](../../shiploop-question-driven-planning-journal.md).
Script: [concern_scope.py](concern_scope.py). Evidence: [evidence/](evidence/).

## Why

The owner asked (2026-11-14) for planning to check a fixed set of points before it exits, in one question per gate,
and added a scope rule: the plan must not go beyond what the request asks "unless it was material and identified as
an unanticipated or missed implicit requirement". Most of that already exists as ShipLoop's concern map
([shiploop_concerns.py](../../../skills/shiploop/scripts/shiploop_concerns.py), built in
fff7fa13fd537d7152e9d71a476b716e4f5e6839, delivered to its owning stages in e0c9a19cd5e4ec1588a340b32b7cf7d58fca98bc):
the plan writes one row per concern per work item in one result, a row that applies carries a decision, an anchor and
an owner stage, a row that does not carries a reason, and the step plan maps each owned row to its steps.

What the map does not record is *why* a row applies: whether the request asked for it, or the plan added it. A
first census (this study's `census.json`) found 71% of applicable rows anchored to a whole file or free text rather
than a requirement or decision ID, so the row alone does not show it. The owner chose to measure before changing
anything ("Yes, measure first"), following the 2026-11-14 rule that a change must alter an outcome, not only a name.

## Question

In the recorded ShipLoop plans, which applicable concern rows (`applies: yes`) does the request ask for (**requested**),
which does a requested outcome need although the request does not say so (**implied**), and which add something
the request does not need (**beyond**)? How often does a plan carry at least one beyond row?

## Design (registered before any judge call)

- **Population.** Every plan result under `~/e2e-runs*` (18 roots) whose result holds a plan-shaped `concerns` map,
  once per action id: 392 plans, 416 work items, 1,503 applicable rows, 56 request families. A family is the
  request text without a leading `$skill-craft:shiploop `. These are E2E test requests: small, fully specified,
  often repeated cases (hello, report.py, ticket service, chess and Battleship on Salesforce, and others).
- **Sample.** For each family with at least one applicable row, up to 2 plans, drawn with `random.Random(20261114)`
  over the family's plans sorted by action id: 64 plans from 41 families, 376 rows. Retest: 10 of those plans drawn
  with `random.Random(20261115)`, judged a second time by the same judge.
- **Rule.** rubric-eval architecture-v4's scope criterion P3 and its overbuilt anchor
  (abb0d23861d53b6aa85e66210e386412f0fdcae5; the rigour-versus-capability split of
  e18cbce9ec577a61a8cdea353c6794804b09f1d9), split into the owner's three cases. Rigour on requested work
  (validation, concurrency, error handling, tests, accessible and polished requested interfaces) is requested or
  implied, never beyond. The judge sees the request verbatim, the plan's work items (context cut to 400 characters)
  and the rows, and returns one label per row with a one-sentence reason. Prompt `PROMPT_V1` in the script; every
  prompt as sent is in `evidence/prompts/`.
- **Judge.** One judge for the study: rubric-eval `model_call` alias `opus` (claude-opus-5-5, effort medium), an
  isolated call with no tools, no MCP servers and no user settings, one call per plan. A reply that does not parse is
  retried once; a plan whose second reply does not parse counts as missing. A call whose audit lists anything outside
  its directory is reported.
- **Scoring.** `concern_scope.py score`: label counts over all judged rows, beyond rows per concern, plans with at
  least one beyond row, the mean beyond share per family (each family weighted once), labels by anchor kind, and
  retest agreement (share and Cohen's kappa).

## Predictions (registered; scored as written)

| # | Prediction | My probability |
|---|---|---|
| P1 | Beyond rows are at most 10% of judged rows | 65% |
| P2 | At least 20% of judged plans hold a beyond row | 55% |
| P3 | Implied rows outnumber requested rows | 60% |
| P4 | At least half the beyond rows fall in observability, scale, performance, platform-services or messaging | 55% |
| P5 | Retest agreement is at least 85% of re-judged rows | 70% |
| P6 | Rows whose anchor names an R-<n> are labelled requested more often than rows anchored to a file or text | 70% |
| P7 | Unclear rows are at most 5% of judged rows | 60% |

## Decision rule (registered)

- **If beyond rows are at most 5% of rows and at most 15% of plans hold one,** a basis field would change almost no
  plan in these runs: do not build it as a scope guard. Whether the owner wants implied rows marked for visibility
  alone is the owner's decision, stated as such.
- **Otherwise,** read every beyond row, and for up to 10 of them check whether the delivered product carried the extra
  (the run's worktree or step commits). If the extra reached the product, propose the basis field (`requested` with
  the request's words, or `implied` with the outcome that needs it) with a registered A/B of the plan stage that
  scores beyond rows and delivery; if it did not, the scope gap is in the plan text only and the proposal says so.
- **Either way,** the implied share is the number of rows a basis field would ask the plan to mark.

## Limits

The labels are one model's judgment, not a script-run test. The corpus is E2E test requests, which state their scope
in detail, so it may understate how often a vaguer real request draws extra scope. A plan row is a decision, not the
built product; the decision rule's second branch checks the product only for beyond rows.
