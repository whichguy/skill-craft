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

## Results (2026-11-14, scored as registered)

**The run.** Before it, every nested `claude -p` failed ("this login reached its time limit and cannot be renewed"):
the Claude CLI's stored sign-in had expired. The owner signed in again and the registered route then ran unchanged.
64 judge calls, every reply parsed on its first attempt, no call touched anything outside its directory; 330,745 input
and 42,384 output tokens, 157 seconds at 6 parallel calls. Retest: 10 calls, 53,717 input and 7,232 output tokens.

**Labels** (376 rows in 64 plans; `scores.json`, `labelled-rows.jsonl`):

| Label | Rows | Share |
|---|---|---|
| requested | 274 | 72.9% |
| implied | 92 | 24.5% |
| beyond | 8 | 2.1% |
| unclear | 2 | 0.5% |

- Plans holding a beyond row: 6 of 64 (9.4%). Mean beyond share per family, each of the 41 families weighted once: 2.1%.
- Implied is the majority only in concurrency (27 of 37 rows); about half in accessibility (11 of 22) and
  observability (12 of 23, with 4 beyond); a third in security (13 of 41); api (60 of 61) and ui (22 of 22) are
  almost all requested.
- Grounding check (`quote-check.json`): 267 of the 274 requested labels quote words that occur in the request
  (fragments around an ellipsis, case and whitespace folded); the other 7 are near-verbatim.
- Retest: 68 of 71 re-judged rows got the same label (95.8%, Cohen's kappa 0.90). The 3 changes were implied to
  requested (2) and implied to unclear (1); no beyond label changed.

**Predictions, as written:**

| # | Outcome |
|---|---|
| P1 | Held: beyond rows are 2.1% of rows |
| P2 | Missed as written: 9.4% of plans hold a beyond row, not 20% or more |
| P3 | Missed as written: 92 implied rows against 274 requested |
| P4 | Held as written: 6 of 8 beyond rows are observability (4) or messaging (2). Reading: all 6 are one case family's reuse of an existing outbox and audit log (below), so this says nothing about the concern type |
| P5 | Held: 95.8% agreement, kappa 0.90 |
| P6 | Held as written, by 3 points: requested in 76% of the 103 R-<n>-anchored rows against 73% of the 224 file-or-text rows. Reading: the anchor kind does not tell requested rows apart |
| P7 | Held: 0.5% unclear |

**The beyond rows** (`beyond-rows.md`; a reading, not a rescoring; the registered rule asks for this audit only in
its second branch):

- 6 of the 8, in 4 plans, are the ticket service's notification outbox and worker, and audit entries. The service's
  base commit already holds `src/outbox.js`, `src/notifier.js`, `src/backoff.js` and `src/audit.js` (case repository
  root commits 2e416e91118338a32979ff152d67afadf09f861f and d507f964237b016624448004ac6d7ba70ad8bd46): the plans
  reused the service's own notification and audit convention. The judge saw only the request, so it read reuse as
  addition. These are not scope beyond the ask.
- 1 is a genuine small addition: a hello run (DeepSeek flash pilot, 2026-10-26) planned and delivered a `.gitignore`
  for `__pycache__/` and `*.pyc` as its own step (case commit 194e797, "feat(W1/S2)").
- 1 is a safeguard: a Battleship run (Sonnet, 2026-10-26) bounded its in-memory game store by count (1,000) and idle
  time (one hour) in `game.js`. Under the request-only rule it is beyond; it is also the abuse limit on anonymous input
  that plan duty 8 asks for at every placement, so it is an implied safeguard the plan did not mark as one.

So the clear additions beyond the ask in this sample are 1 row of 376, or 2 counting the safeguard.

**Decision (the registered rule's first branch).** Beyond rows are 2.1% of rows (at most 5%) and 9.4% of plans (at most
15%): a basis field built as a scope guard would change almost no plan in these runs, so it is not built. The implied
rows, 92 of 376 (about 1.4 per plan, mostly concurrency, observability, security, state and accessibility), are what a
basis field would ask the plan to mark; whether to mark them for visibility alone is the owner's decision.

**Contrary evidence and unknowns.**

- These requests spell out their behaviour, which is why requested dominates; a vague request may draw more additions.
  Not measured.
- The judge saw only the request. A judge with the repository would not have flagged the 6 reuse rows, but might flag
  others.
- Only applicable rows were judged. Rows marked "no" were not, so the other half of the owner's rule, a material
  implied requirement the plan missed, is unmeasured here.
- The release and migration points are barely in the corpus: switchover, migrate-before and migrate-after apply in 11,
  9 and 1 of 416 work items (2 and 1 rows in the sample), so this study says nothing about them.
