---
Status: firm for these corpora (2026-10-31). The stage-prompt review and the per-run condition test are complete; nothing is adopted.
Consumer: the owner, deciding which ShipLoop prompt or script changes to land and which side tests to run first.
Journal: this file (§6) and docs/shiploop-test-stage-prompt-design-2026-10-30.md §10.
---

# Stage-prompt review and per-run condition test (2026-10-31)

Owner, 2026-10-31: "Examine each prompt template and help identify if improvements or side tests should be
executed", which followed "Run to completion, illustrate findings" on the test-coverage question
(docs/experiments/coverage-ledger-20261031/).

Nothing in ShipLoop changed in this work. Every finding below was read from archived runs and current code (main
`11414642`, shiploop 2.26.0), with no model call except the reviewers' own reading.

## 1. Method

- **Stage health.** `stage_health.py` reads `RUN/trace.jsonl` from the 96 traced archived runs (2026-10-25 to
  2026-10-31). Per stage it counts:
  - runs and packets;
  - real refused `complete` callbacks;
  - dry refusals (`complete --check-only`, plus the `check` verb that replaced it in 8bf10c64);
  - other outcomes (send-back, add-work);
  - wall minutes from one packet to the next;
  - the commonest refusal messages.

  Output: `stage-health.txt`, `stage-health.json`. The first version missed the `check` verb; the D reviewer caught
  this, and it was fixed before synthesis. With the fix, step-plan has 86 dry refusals rather than 33, and test 85
  rather than 33.
- **Six read-only reviewers** (Opus, one per stage group) took the same brief (`review-brief.md`). For each stage
  they:
  - rendered its prompt (`shiploop_prompts.PROMPTS`);
  - traced every refusal to its code, and checked whether that code is still live;
  - read the commits that shaped its duty, including rejected approaches;
  - returned `improve`, `side-test` or `no-change`, with evidence.

  Reports: `reviews/A-front.md` … `reviews/F-release.md`.
- **Parent checks.** The parent re-checked each top finding in current code before ranking it (§3).
- **Per-run condition test.** Five Sonnet workers each took one runnable archived run, following the plan
  predeclared in `conditions/plan.md`:
  1. split each changed requirement into conditions from the spec text alone;
  2. broke each condition in the product code;
  3. proved the break with an independent witness;
  4. ran the run's own suite.

  Results: `conditions/<run>/results.json`.

## 2. Verdict per stage

| Stage | Verdict | One-line reason |
|---|---|---|
| intake | improve | Long requests: 3 of 3 refused for self-numbered sentences, and 2 of 3 then copied the whole request |
| discovery | no-change | 57 of 64 cite a baseline test output; numbered questions were already rejected (X2) |
| research | no-change | 63 of 64 write research.md; the cue A/B tied 4 of 4 (b992183d). Exploration allowance flagged for the owner |
| spec | no-change | 0 of 39 send-backs trace to spec |
| test-strategy | improve | 5 of 8 recent Terra runs record a test-ID convention (`test_TC_1_output`) the matcher cannot see |
| plan | no-change | Concern-row repairs take seconds in about 10% of runs; the head is at its bound |
| prepare | no-change | 2 refusals, both from the readable-evidence gate working as designed |
| step-plan | improve, plus a side test | `check` approves drafts `complete` refuses (14 real refusals); the template teaches lint rows to confirm behaviour criteria |
| test-spec | side-test (low) | The mock sentence (3c904e64) appears in 63 results; no row uses it |
| validate-existing | no-change | One packet in 96 runs, routed correctly |
| implement | no-change | 17 of 23 send-backs were the proof-order fault, which ffea2956 now refuses upstream |
| test | improve | An empty `red_na` list is refused (17 in 16 runs); the packet misstates the mutation gate |
| document | improve | The spec-mark check refuses a correct line ending in a period (3 times, plus 1 at implement) |
| carry-forward | no-change | 86 of 86 decided `skill: none`; the owner's revisit trigger has not occurred |
| system-test-author | side-test | 3 of 3 Salesforce runs on Terra marked the default suite `host_dependent`, then were sent back |
| system-test | no-change | Its refusals come from the system-test-author defect above |
| product-acceptance | improve | The duty contradicts itself on release-phase items, behind 4 of 6 refusals; it prints a Backchain paragraph that 0 of 60 results used |
| release-plan | improve | 51 of 62 returned environment.md files keep a rollback command with a literal `<kept paths>` |
| release-check | improve (one clause) | Compare the filled rollback with environment.md |
| release | no-change | No refusals of its own |
| release-verify | improve | The instruction to restate `unverified` is never printed: 8 of 63 first submissions were refused |
| operations | no-change | 0 refusals |
| handoff | improve | Same restatement placement as release-verify (4 of 52) |

Totals: 10 improve, 2 side-test, 11 no-change.

## 3. Ranked recommendations

Ranked by gain on any project, quality first ([[eval-decision-priority]]). In the "Checked" column, *parent* means
the parent re-ran the check in current code (main `11414642`).

**Land now** (each fix's evidence comes from the runs; each is a script or wording fix that changes no gate's intent)

| # | Change | Evidence | Checked | Cost |
|---|---|---|---|---|
| 1 | step-plan: `shiploop check` runs the result shape check (`_canonical_result`) before `_evaluate`, as complete does | 14 real refusals after a "yes"; 15 of 61 Terra runs since 2026-10-29; breaks 5086baf6's "a matching yes cannot be refused" | parent: the check branch calls `_evaluate` on the raw `_submitted_result` | ~20 lines, fail-first test |
| 2 | step-plan template: the check row drops `criteria`; the focused row carries the criteria | 22 of 445 executed criteria confirmed only by a lint/syntax row (e.g. `node --check` "confirms" pagination) | reviewer count | one template line |
| 3 | test: an empty `red_na`/`retired_tests` list counts as absent | 17 refusals in 16 runs (DeepSeek, Terra; latest 2026-10-31) | parent: `_RECORD_FIELDS` requires a non-empty list | one line, route test |
| 4 | document/implement: accept `.` or `;` after the spec mark `(W1/S1)` | 3 refusals of correct lines plus 1 at implement | parent: `endswith("(" + marker + ")")` | one line, route test |
| 5 | test packet: the mutation Checked-by line says the gate refuses each survivor with no disposition | the text says "refuses when the focused tests catch none"; 51 of 51 refusals are the per-survivor form | parent: `_CHECK_TEXT["test-loop"]` | one string, contract pairing |
| 6 | release-verify, release and handoff: print the restate-`unverified` sentence in the head (P1 block), rows stay in the file | 8 of 63 first submissions refused; the sentence is FILE_ONLY | reviewer scan of heads | block order and head pins |
| 7 | release-plan/release-check: print a runnable rollback recipe (`<kept paths>` filled from the return plan) | 51 of 62 returned environment.md keep the placeholder; 9 of 9 qr runs on 2026-10-31 | parent: `rollback_lines` prints `<kept paths>` | ~30 lines, offline `git apply -R --check` replay |
| 8 | test-strategy item 10: declare IDs as the runner prints them; a name such as `test_TC_1_output` does not show `TC_1` | 5 of 8 recent Terra hello runs; they passed only by a docstring | parent: `(?<![\w-])TC_1(?![\w])` misses `test_TC_1_output` and `….test_TC_1` | one sentence |
| 9 | intake: cite sentences as RUN/request.md numbers them, ranges allowed, no copying; the excerpt note points at RUN/request.md | 3 of 3 long-request intakes refused; 2 of 3 then pasted 8–11K characters | parent: duty says "cited S<n> (S1 is the first)" | four text edits |
| 10 | product-acceptance: ShipLoop's own worktree return is release's, named in `summary`, not `unverified`; print the one-line optional audit instead of the Backchain paragraph | 4 of 6 refusals and ~19 summary-only rows; 0 of 60 results used the paragraph | parent: items 3 and 6 disagree | two edits |
| 11 | step-plan item 6: `from` appears only on an expectation that settles a due open item | 25 dry refusals in 22 runs | reviewer count | one sentence, template row |

**Side tests before deciding**

| Side test | Question | Corpus and cost | Predeclared rule |
|---|---|---|---|
| **S7 test-spec condition A/B** (§5a) | Does a clause asking for a case that separates each stated rule from its nearest wrong rule kill more of the 74 verified survivor variants? | These five runs' fixed products; ~40 slices on the E2E subject; needs the owner's go under the live hold | Adopt if +15 points on survivors (permutation p < 0.05), no loss on the 374 killed variants or hidden checks, tokens ≤ +25% |
| S1 Proof dry run on the item base | Does running each step's Proof on its base catch vacuous, unloadable and broken Proofs before implement spends a loop? | ffea2956's replay set and `implement-sendbacks.jsonl`; ~half a day offline, no model calls | Notice only if it reveals ≥3 of the 6 handed faults and adds ≤10 s to the median check; only exit 126/127 may refuse |
| S2 `host_dependent` definition | Does item 6's reworded definition stop marking the default suite without un-marking optional browsers? | 3 archived first packets + one neutral hosted-runtime fixture with a browser countercase; 40 Terra calls. The offline replay already shows 4 hits, 0 false | Adopt if mis-marking goes from ≥3/5 to 0/5 and the countercase stays 5/5 |
| S3 Mock sentence | Did any of 205 test-spec rows need a test double? | 63 results; ~1 h of reading | Narrow item 6 if ≥10% need one; no change if ≤2% |
| S4 Intake replay (optional) | Does the range wording pass first time and stop copying? | 6 long-request packets; 48 Terra calls | Adopt if first-pass ≥ arm A and copying falls |
| S5 Test-ID slices (optional) | Does item 10's new sentence produce a convention `named()` reads? | 8 hello slices on Terra; ~30 min | Adopt if ≥3 of 4 |
| S6 F1 bundle count | Does a bundle review at prepare find what per-stage reviews find? | Analysis in F1's planned three-arm batch (45a4d2ff) | Part of F1's decision |

**Owner decisions flagged, nothing proposed**

- research: the written exploration allowance (15 minutes, 64 actions, 3 experiments) is a limit, so it is the
  owner's to change ([[shiploop-loops-unbounded]]).
- carry-forward: the skill procedure is 3,321 of 6,104 duty characters, and every run decided `none`. The owner kept
  the decision per item (7b2d57b7); its revisit trigger has not fired.
- spec: the goal-6 live measure (docs/shiploop-question-record-verdicts-and-plan-2026-10-31.md §4) has no signal in
  39 of 39 outcomes and could be closed.

## 4. Cross-cutting learnings

- **Most refusals in the history are retired caps.** Examples: test-strategy 23 of 28, plan 10 of 19, implement 7 of
  17. The caps went in 16a3279f and 232689c5. Of what is still live, most is repaired in seconds. The live defects
  that cost loops or quality are few and specific (§3, rows 1, 2, 6, 7).
- **Three findings are script truthfulness, not prompt text.**
  - The check verb skips a shape rule (row 1).
  - A gate refuses a correct value (rows 3 and 4).
  - A printed recipe cannot run (row 7).

  None needs more prompt words.
- **Two findings are placement.** The text exists, but in a part of the packet that is not printed (rows 6 and 9).
  Moving it to the head costs about 250 characters.
- **Packets are near their bounds.** The step-plan head is at 19,888 of 20,000 characters, test at 18,820, and plan
  at its 19,500 bound. Additions must be paid for by cuts, so rows 2 and 10 shorten the head.

## 5. Per-run condition test: the natural gap rate within requirements

**Question** (predeclared in `conditions/plan.md` before any variant ran). A changed spec requirement states several
conditions that can each be observed. For what share of them does the run's own final suite fail when exactly that
one condition is broken in the product?

**Result.** 74 of 448 witnessed conditions survived: 16.5%, or 16.1% without the two conditions a worker inferred
rather than read. Every survivor's witness passes on the unchanged product and fails on the variant, while the run's
own suite still passes.

| Run | Subject | Witnessed | Killed | Survived | Survival | Requirements with a survivor |
|---|---|---|---|---|---|---|
| codex-r2-user-listing | Codex Terra, brownfield | 46 | 42 | 4 | 8.7% | 1 of 3 |
| claude-csv-report | Claude, greenfield | 91 | 74 | 17 | 18.7% | 6 of 6 |
| bf-ds-ticket-assignment | DeepSeek flash, brownfield | 97 | 82 | 15 | 15.5% | 8 of 10 |
| grok-web-battleship | Grok, greenfield | 89 | 68 | 21 | 23.6% | 3 of 5 |
| v2170-ds-battleship | DeepSeek flash, greenfield | 125 | 108 | 17 | 13.6% | 6 of 9 |
| **pooled** | | **448** | **374** | **74** | **16.5%** | 24 of 33 |

By kind, the survivors are 27 behaviour, 22 boundary, 17 error and 8 format. By the workers' own labels, 36 have no
case at all, and 38 have a case whose input or assertion does not catch the break.

**What the survivors look like** (every one is in `conditions/summary.json`, with its quote and reason):

- **A planned case never written.** grok-web-battleship TC-3, firing from the page in a real browser (R-3.8 to
  R-3.13), was specified at test-spec. test-strategy and prepare then decided there was "no control-activation
  runner", and every later stage carried it as an `unverified` row owned by the local player. The same run used
  Chrome to read the page title, and the worker drove clicks with local headless Chrome. The run predates the UI
  criteria in 2.24.0 (Wave A), so this may already be addressed.
- **An example that cannot tell the rule from its nearest wrong rule.**
  - claude-csv-report R-3.8: the spec's own boundary example, 2.675 → 2.68, gives the same answer under half-even
    rounding.
  - R-3.15/R-3.16: the only multi-region example lists regions already in sorted order.
  - R-3.6: Decimal summing is tested on one row only.
  - v2170 R-5.1: a symmetric walk passes with row and column swapped.
  - bf-ds R-8.10: the dedupe is tested only while the first notice is still pending.
- **An enumerated class tested by one member.**
  - bf-ds R-4.7 to R-4.9: of tab, line breaks, other C0 controls and DEL, only tab is tried.
  - grok R-5.22 to R-5.29: only row 10 is sent out of range, never row −1 or column −1/10.
  - v2170 R-1.3 to R-1.5: port edges 1, 65535 and 65536 are never tried.
  - v2170 R-7.7/R-7.8: there is no column mirror of the row error cases.
- **A stated rule with no case.**
  - codex R-3.20 to R-3.22: the first value of a duplicate query parameter.
  - claude-csv R-1.3: a repeated FILE, which the spec itself marked `n/a`.
  - bf-ds R-9.6: all three filters together.
  - bf-ds R-5.3: unassigning an in_progress ticket.

**Seven survivors break a core outcome** (the parent's reading, before tallying): firing from the page (grok
R-3.8, R-3.9, R-3.10, R-3.13), the revenue total's rounding and summing (claude-csv R-3.6, R-3.8), and random fleet
placement (v2170 R-3.13).

**Decision by the predeclared rule.** Survival is above 10%, and core-outcome survivors exist. So this test adopts
nothing. A test-spec or test candidate gets its own predeclared A/B first (§5a).

**Checks by the parent** (`conditions/verify.py`, on fresh copies without `.git`):
- all 74 survivors reproduced: witness 0 on the unchanged copy, nonzero on the variant, suite 0 on the variant;
- 15 of 15 sampled killed conditions failed the suite;
- the originals' hashes are unchanged (in each `results.json`).

The first Grok check showed a failing baseline and one disagreement. Both came from port contention with the
battleship worker, which was still running. Rerun once the ports were free, both are clean, and R-3.11 survived 3 of 3
times.

**How this relates to earlier work.**
- The ledger (6c626574) counted requirement IDs and found none untested. This test finds that within a requirement,
  one in six stated conditions is not checked. The two results agree: IDs are covered, and conditions under them are
  not all covered.
- E7-F's request measure was saturated: every arm killed 10 of 10 variants (56a1f7b6, 143dba28). d9fefb11 asked for
  an unsaturated measure. These 74 verified variants are one, on five apps and four subjects.
- 488ffbd9's planted omissions were all found by both product-acceptance arms. That tested a reviewer reading
  evidence. This tested the suites the runs shipped.

### 5a. Recommended next side test (S7): a test-spec A/B on these variants

- **Arms.** A is current main. B adds one clause to test-spec item 3: "For each condition a criterion states, give a
  case whose input makes the stated rule and its nearest wrong rule disagree, such as an input out of the required
  order, a half-way value, both sides of a range edge, each member of an enumerated class, or each axis of a
  symmetric rule." The clause is generic and names no stack. Its wording is to be fixed before any run.
- **Corpus.** These five runs' final products, held fixed. test-spec and test are re-run for every work item.
- **Measure** (script, no judge):
  - kill share of the 74 survivor variants;
  - the 374 killed variants, which must not fall more than 2 points;
  - tokens.
- **Rule** (to be fixed before running):
  - adopt B if it kills at least 15 points more of the survivors, with a permutation p < 0.05 across runs;
  - also required: no loss on the killed set or the hidden checks, and at most 25% more tokens.
- **Cost.** About 40 slices on the E2E subject (5 runs × 2 arms × 4).
  - It needs a slice that re-runs test-spec and test for every item, where E7-F's slice re-ran one item.
  - It is live model work, so it waits for the owner's go under the live-run hold (d9fefb11).

## 6. Journal

| Date | Entry | Status | Evidence |
|---|---|---|---|
| 2026-10-31 | Stage-health table over 96 traced runs. First version missed the `check` verb (113 refusals); corrected before synthesis | firm | stage_health.py, stage-health.txt |
| 2026-10-31 | The six product-acceptance "lower_layer_check names no test" refusals were read. 2 were wrong IDs, corrected by the model. 4 were release-phase rows pushed out of `unverified` (E-close). None comes from `passed_cases` missing a criterion-route case, so the coverage ledger's side finding still has not bound a run | firm | trace rows; ledger.json rows |
| 2026-10-31 | Six reviewers returned 10 improve, 2 side-test and 11 no-change. The parent re-checked rows 1, 3, 4, 5, 7, 8, 9 and 10 in code | firm | reviews/*.md |
| 2026-10-31 | Condition test, all five runs: 74 of 448 witnessed conditions survived (16.5%; 16.1% without 2 inferred). Per run 8.7% to 23.6%. Seven break a core outcome. By the predeclared rule nothing is adopted, and the next step is an A/B (S7) | firm for these runs | conditions/summary.json, conditions/*/results.json |
| 2026-10-31 | Parent check: 74 of 74 survivors and 15 of 15 sampled kills reproduced on fresh copies. A first Grok pass was disturbed by port contention with a concurrent worker; the rerun was clean | firm | conditions/verify.py output in this commit's message |
| 2026-10-31 | Finding: grok-web-battleship's browser case TC-3 was planned, never written, and carried as unverified, although local headless Chrome could drive it. The run predates 2.24.0's UI criteria | firm (one run); whether 2.24.0 closes it is unknown | grok-web-battleship/results.json; run results nav-33c30e48 (prepare), nav-820b080d (product-acceptance) |
