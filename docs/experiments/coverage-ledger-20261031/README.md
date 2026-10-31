---
Status: measured 2026-10-31; firm for these archived runs at requirement granularity; no ShipLoop change made or proposed for adoption.
Consumer: the owner, deciding whether ShipLoop needs an end-of-run step that re-anchors the tests on the spec (a new phase, or a final work item the plan schedules). Later: anyone who proposes such a step or a coverage gate, and needs the base rate it must beat.
Journal: docs/shiploop-test-stage-prompt-design-2026-10-30.md §10 (the test topic's journal).
---

# Coverage ledger: do the step tests, taken together, cover what the spec defined? — 2026-10-31

Owner, 2026-10-31: "I'm trying to figure out if we need some sort of elaboration of the testing phase to make sure
that tests themselves are actually built effectively and well, and re-anchored on the original spec that was defined.
[...] Do we need a dedicated phase at the end, or maybe a change in the prompt for the planning when we plan all the
steps?" The answer given in the session: ShipLoop already has the end phase (`system-test-author`, `system-test`,
`product-acceptance`); its re-anchoring is model-judged except for the primary requirements; a script-built ledger
would be the structural fix, but only if existing runs show a gap. Owner: "Yes, measure first." This is that
measurement.

## 1. The answer

**No gap to close at requirement granularity.** Across 72 archived runs (ShipLoop state versions 8–11, 2026-10-16 to
2026-10-31; Sonnet, DeepSeek flash, Codex Terra, Grok subjects; greenfield, brownfield and Salesforce cases), the
specs added or changed 331 requirements:

| End state | Requirements | of them primary |
|---|---:|---:|
| `inner`: a test-spec case naming it in its `requirement` field, seen passing in ShipLoop's own test records | 231 | 192 |
| `inner-criterion`: a passing case names another ID, but the case's step-plan criterion names this one | 29 | 22 |
| `system`: a system command tied to it in the system-test catalog, system-test accepted | 9 | 6 |
| `unverified`: product-acceptance lists it with a reason | 2 | 0 |
| `none`: nothing above | 60 | 37 |

The 60 `none` rows, each read in full (classification.json, model-judged):

| Category | Rows | What it is |
|---|---:|---|
| tests-themselves | 27 | the requirement *is* the suite ("`test_hello.py` contains a unittest", "`node --test` runs the tests"); the passing suite satisfies it |
| delivery-structure | 20 | deploy target, metadata allow-list, project root, module placement, secrets, process obligations, exclusions |
| preserved | 6 | existing behaviour run as the existing regression suite; one is a one-word edit in a note |
| harness-probe | 3 | the E2E harness's checkpoint protocol, not product |
| unverified-old-shape | 3 | Salesforce board UI no host browser could open: recorded as an open assumption and an unverified row with an owner, on the row shape before 2026-10-24 that has no `requirement` field |
| tested-other-id | 1 | tested by a passing case filed under another requirement (its oracle asserts the seeds and fleet) |

**Product behaviour that ends with no test and no recorded reason: 0 of 331.**

So neither a dedicated phase nor a scheduled final "re-anchor" work item has anything measurable to catch at this
level, and a script coverage gate keyed on test-case IDs would cost more than it finds (§3).

## 2. Method

`ledger.py` reads each archived run with ShipLoop's own readers: `shiploop_store.read_record` for `state.md`,
`shiploop_planning_revision.current_actions` for the results in force, `shiploop_knowledge_home._entries` for the
spec's R-<n> entries, and the test records `tests/<action>-verify<N>.md` that `shiploop_primary.passed_cases` reads.

- **Changed requirements:** the R-<n> entries of `docs/shiploop/spec.md` added, or changed in text, between the
  run's baseline commit (`RUN/run-baseline.txt`) and the final checkout. Retired entries are excluded. The 46 runs
  without a baseline file (before the knowledge-home baseline, up to 2026-10-11) are listed but not scored.
- **Inner coverage:** a current test-spec case maps to the requirement IDs in its `requirement` field
  (`knowledge.requirement_ids`), and, as a second route, to the IDs its step-plan criterion's text names, with ranges
  such as "R-1 through R-4" expanded. It counts when an accepted inner action's passed record lists its ID.
- **System coverage:** system-command IDs that are not inner case IDs, tied to requirements by the catalog lines in
  system-test-author's summary that name both.
- **Unverified:** product-acceptance `unverified` rows by their `requirement` field.
- Reproduce: `python3 ledger.py --json ledger.json && python3 summarize.py` (summary.txt holds the output). The
  summarizer refuses when the `none` set and classification.json disagree, so a rerun cannot pass on a stale hand
  classification. The run set grows as other sessions finish runs: this snapshot has 118 archived runs, 72 scored. A
  run that finished during the pass added 4 requirements: 3 `inner` and 1 `inner-criterion`.

## 3. What a coverage gate keyed on test-case IDs would cost

- The `requirement` field is single-valued in practice: **6 of 549** test-spec cases name two or more IDs there,
  while one case often covers several requirements. A field-only ledger (what `passed_cases` reads) misses the 29
  `inner-criterion` rows, plus the 1 `tested-other-id` row.
- 53 `none` rows are requirements no single case should name (tests-themselves, delivery-structure, preserved).
- Together, **83 of 331 rows (25%)** would need a "covered another way" answer from the model at the end of every run,
  for no product gap found in 72 runs.

## 4. Side findings

1. **The existing primary gate shares the field-only reading.** 22 primary requirements in these runs are covered only
   through a case's criterion. For them `shiploop_primary.packet_lines` prints "none passed" in the product-acceptance
   packet, and `check_unverified` would refuse a `lower_layer_check` that names the covering case. It has not bound a
   run here: 24 product-acceptance unverified rows name a primary requirement, and `passed_cases` accepts all 24
   `lower_layer_check` values. Each of those runs named a case that carries the requirement in its own field.
2. **`knowledge.requirement_ids` does not expand ranges.** "R-1 through R-4" reads as R-1 and R-4. Criteria are
   written that way (e.g. hooks-before-user-listing C1, A-user-listing-s2 C1). `shiploop_loops.step_anchors` reads
   criteria with it too.
3. **The `not_covered` channel works, but no script can trace it.** Implement flagged 160 behaviours in 26 runs (all
   after the test duty's "Gaps" item of 2026-10-11). The test stages do act on them: the summaries of v2180-sonnet,
   live-sonnet, pa-ds battleship and gate-290 csv-report name the `(a)`/`(b)` sub-cases they added. One also lists
   leftovers "not_covered by design, documented in the spec". But ShipLoop's records keep the parent ID token
   (`TC-3`), so the ledger sees 0 sub-case IDs in those 26 runs. Which flagged behaviours got a test is known only
   from prose.

## 5. Prior and parallel work this agrees with

- **TS1's replay, 2026-10-26** (70d88d379fece7457b9136b39ab8d586fd43cdae;
  docs/experiments/judgement-stage-checks-20261026/ts1-in1-replay.jsonl). An end-of-run coverage check, replayed,
  "refused 5 of 8 runs for honest work". Requirements about the tests themselves had no case, and none could observe
  them. Grok chess-sf 12a23d passed only once its structural requirements (project root, metadata kinds, secrets) were
  marked with its deploy and secrets-check commands. Its one true positive, "Sonnet hello R-1 left a tested
  requirement unnamed by any case", is live-sonnet-hello-b01d1c R-1 here. The criterion route credits it
  (`inner-criterion`, case TC_1), so it was an attribution miss, not untested behaviour. This ledger reproduces that
  replay's categories on 72 runs and 331 requirements.
- **A parallel session on the same owner concern, 2026-10-31** (d9fefb1144dea7f9a8d85b5897ad1275dbe08a07,
  learning-only). It found from source and history that no evidence justifies another final stage, a stronger refusal
  gate or longer loops. It replayed gym-published-baseline-03 with `passed_cases`: R-1 and R-5 have no lower-layer
  case, which is "no missing-test verdict". Those two rows are delivery-structure here. Its predeclared next step
  matches §7's first open item: compare the current audit with explicit atomic-condition reconciliation on a frozen
  corpus that holds one genuinely missed request condition plus controls. It also records the owner's hold on the
  next live E2E cycle, which this offline ledger respects.

## 6. Limits and unknowns

- **Granularity:** this traces requirements, not acceptance lines. A requirement with five acceptance lines counts as
  covered when one passing case names it. Within-requirement coverage is unmeasured.
- **Attribution, not adequacy:** a case that names a requirement may test it weakly. The only adequacy evidence is
  E7's request measure: one case and implementation, 10 of 10 request-breaking variants killed in every arm
  (docs/experiments/test-stage-prompt-20261030/e7-request.md). It has not been repeated on a multi-item run.
- **Hand classification:** the six categories were assigned by one reader (Claude Opus 5.5). The rows and the reading
  notes are in classification.json for review.
- Hidden E2E checks were not joined to the ledger.

## 7. What this means for the design question

- A dedicated end phase already exists. On this evidence, neither a new phase nor a planned final work item is
  warranted. A test-only final item would also escape the step's two quality checks: its new tests pass on its base,
  and it changes no product lines for the mutation check to mutate.
- A ledger gate is not warranted either: 25% disposition overhead, 0 gaps found.
- Open, if the question returns:
  - (a) adequacy within a requirement: the frozen-corpus, atomic-condition comparison d9fefb11 predeclares, or the E7
    request-variant method on a multi-item run, run offline while the live hold stands;
  - (b) the small truthfulness fix for side findings 1 and 2: read the criterion route and expand ranges in
    `passed_cases` and `requirement_ids`.

  Both are owner decisions, and neither is built.
