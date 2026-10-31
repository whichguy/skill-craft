---
Execute: ask
Status: E7 decided 2026-10-30 (owner: "Yes, build E7", D1): no arm adopted, nothing in ShipLoop changed (§7b).
  E7-F, the rerun with the implementation held fixed (owner: "Yes, build it", D4), decided the same day: no arm
  adopted; implement was most of E7's noise (§7c, §7d). D6 is running as arm T of E7-F (owner: "Yes, run the D6
  arm"; §7e). D5 awaits the owner (§9).
Opened: 2026-10-30
Consumer: the owner, who decides §9; then whoever builds experiment E7 (§7) and, on its verdict, the test-stage
  prompt change. Later: anyone who proposes more test-stage prose and needs the bar it must clear.
Journal: §10 below (this file is the topic journal); evidence in docs/experiments/test-stage-prompt-20261030/
---

# The test-stage prompt: what the evidence says, and a smaller prompt to test — design, 2026-10-30

Owner, 2026-10-30: "I really want a deep dive on the ship loop prompt that we have for implementing tests in the inner
loop stage, and to identify how to make sure that that's really well designed. [...] I'm not convinced that just simply
more profuse text in the prompt will actually make it better quality. I want to research kinds of things that other
folks have found that are really great prompts for effectively looking at code and writing a set of tests to validate
and anchor that code. Keep in mind that we can use the reference material from anything else that's built during
interloop, or from architecture.md, environment.md, or the spec that gets written."

Scope: the inner loop's `test` stage (writes the step's tests and makes the recorded commands pass) and, where it
decides the tests' shape, `test-spec` (writes the cases before code). Both are rows in `STAGE_SPEC`
(skills/shiploop/scripts/shiploop_stage_spec.py) with duty text in `DUTIES` (skills/shiploop/scripts/shiploop_prompts.py).

## 1. The answer

**The owner's doubt is right: the test stage's quality is limited by what it is shown and how it is checked, not by
how much it is told.** The evidence points at four changes. Two are script changes; the duty text that carries the
other two gets shorter, not longer:

1. **Fix the expected values before the code is visible, then show the code.** Tests written while the model sees the
   code copy its behaviour, bugs included, and putting the spec beside the code barely helps. Spec-only input found the
   most bugs (L9: 11 current models). ShipLoop's split already does the first half: `test-spec` writes the cases before
   implement runs.
   - But each case's oracle is one sentence, so the test stage still invents most concrete values while reading the
     code (§3d).
   - And the test packet does not show the step's diff, so the model must go and find the code for choosing inputs.
     There, the code under test is the most valuable context (L4).
2. **Choose inputs from the code.** The mutants that survive the delivered tests are almost all limits and guard
   clauses the *code* introduced, which no spec sentence names (§3a). 75% of the defects LLM tests miss are missed
   for lack of the triggering input (L24).
3. **One behaviour per test.** One case per criterion, and "each case becomes a test", makes each test check a whole
   criterion. In one brownfield run, TC_1 is a single 40-line test with about 27 assertions. The gate already accepts
   several tests per case ID (§3d), so only the wording forces this.
4. **Make the in-loop mutation check show the misses that matter.** It negates comparisons (`<`→`>=`), which nearly any
   test kills. It has no boundary shift (`<`→`<=`) and no `||`↔`&&` flip. Those two classes are 70% of the product
   mutants that survive the delivered tests: 40 of 57 over three greenfield runs and twelve Codex Terra brownfield runs
   (§3a, §3b, §3c).

The proposed duty text (§6a) is **474 words against today's 680**. It drops the rules a gate already states elsewhere
in the packet (the Checked-by line, the floors and the base-run paragraph carry them, and so does each refusal) and
spends the words on the points above. Whether it is better is a question for
experiment E7 (§7): the harness can measure it, and this repository's own E6 found prose moved its metric less than a
check did (§3e).

## 2. What the test stage receives today

The packet of the `test` stage, W1 S3 of the Codex Terra brownfield run `hooks-after-ticket-escalation` (2026-10-29),
is 31.7 KB, about 3,900 words (≈8k tokens with paths). By section
(docs/experiments/test-stage-prompt-20261030/packet-anatomy.txt):

| Section | Words | Share |
|---|---:|---:|
| Header: delegation, recovery, callback, owner rule, goal, Checked-by | 474 | 12% |
| Until Loop block, its argument, floors, red-check; keepalive and where | 645 | 16% |
| **Duty items 1 and 3 (writing tests: the craft)** | **281** | **7%** |
| Duty items 2 and 4–8 (decisions, run and fix, end states, fields, limits, send-back) | 399 | 10% |
| RULES | 91 | 2% |
| Work item, layers, targets, Pass, Floor, Base run, lint, template, outcomes | 625 | 16% |
| References, results list, progress, pause | 263 | 7% |
| Knowledge-file listing | 116 | 3% |
| **Hand-offs: the R-n spec text, AD-2, the three test cases, `not_covered`** | **694** | **18%** |
| Tail: pass log, halt, state, recovery, request, decision source, last summary | 335 | 9% |

Three things follow:
- **The craft is 7% of the packet, and 75% is neither craft nor the data the tests check against.** The craft sits
  after 1,100 words of header and loop text and before 2,500 words of rules, gate text, references and records.
- **Rules a gate enforces are restated.** "base" appears 14 times, "floor" 9, the case-ID naming rule 5, "send-back"
  6. Each says the same thing as the gate's own refusal, which the model reads anyway when it calls `check`.
- **The data it tests against is partly missing.** The spec text and the cases are quoted by value. The code under
  test (the step's diff, its public entry points) and an example test in the repository's style are not. The document
  packet prints "Changed since the item base"; the test packet does not. The test-cases guide already says "After code,
  inspect the actual diff [...] then author or refine the executable tests from that evidence"
  (skills/shiploop/references/testing-and-documentation.md#test-cases), but the duty never asks for it and the
  packet never shows it.

## 3. What its tests miss (ShipLoop's own runs)

### 3a. Greenfield: the surviving mutants are code-introduced limits and guard clauses

The E2E harness's quality phase mutates each delivered product with operator catalog `js-1` (test/shiploop_e2e/quality.py)
and runs its tests. Ratios on saved runs range from 0.47 (DeepSeek flash, 2026-10-28) to 0.87 (Sonnet), mostly
0.75–0.86. The product survivors of three recent runs, with their source lines
(docs/experiments/test-stage-prompt-20261030/greenfield-survivors.json):

| Operator | Survivors | Examples |
|---|---:|---|
| `rel-bound` (`<`↔`<=`, `>`↔`>=`) | 12 | `size > MAX_BODY_BYTES`, `port <= 65535`, `cap < 1`, `attempts >= MAX_PLACEMENT_ATTEMPTS` |
| `logic-flip` (`||`↔`&&`) | 11 | `body === null \|\| typeof body !== 'object' \|\| Array.isArray(body)` |
| `bound-literal` (n→n+1 after `<`/`>`) | 5 | `value <= 9`, `length < 1` |
| `arith-flip` | 5 | ship placement span `SIZE - length + 1` under a random draw |
| `eq-flip` | 3 | the type name in an error message |

Two patterns explain most of it:
- **The tests never sit on the limit.** They try a value far inside and far outside a limit, never the limit itself
  and one past it.
- **They break a compound guard with one input.** One invalid input fails several clauses at once, so `||`→`&&` still
  rejects it.

Neither limit is in the spec. `MAX_BODY_BYTES`, the 65,535 port bound and the placement retry cap are the
implementer's choices. A test written to "the spec's oracle, never the code" before the code exists cannot name them.
The rest are random placement, where the tests had no seed to pin.

The 0.47 run's low ratio is mostly an artefact: 122 of its 139 survivors are in `test-support/` helpers the harness
mutated as product. A reader of this measure must exclude them.

### 3b. Brownfield: changed-line mutation on the Codex Terra runs of 2026-10-29

Brownfield runs record no harness mutation block, but their worktrees are kept.
docs/experiments/test-stage-prompt-20261030/changed_line_mutation.py does the following for each run:
- takes the product lines the run added since its baseline commit (`src/` only);
- applies each `js-1` site on those lines alone, in a `git archive` copy (the run folders are never touched);
- runs the product's own `npm test`, the whole delivered suite.

Twelve Codex Terra xhigh runs of 2026-10-29: hooks after, hooks before, and the r1 and r2 rows, each over ticket
assignment, ticket escalation and user listing (brownfield-mutation.json).

| | Killed | Survived | Survival rate |
|---|---:|---:|---:|
| All operators | 196 of 217 (0.903) | 21 | 10% |
| `eq-flip` | 80 | 0 | 0% |
| `logic-flip` | 70 | 10 | 12.5% |
| `rel-bound` | 18 | 7 | 28% |
| `bool-flip` | 2 | 4 | 4 of 6 |
| `bound-literal`, `arith-flip` | 26 | 0 | 0% |

Per run the ratio is 0.82–1.00, with no visible difference between hooks on and off.

**The strongest model shows the same two misses.**
- **No test sits on the limit.** `name.length > 64` → `>=` survives in six of the twelve runs (`src/config.js`,
  `src/persistence.js`): the tests try 65 characters and never exactly 64. The seventh `rel-bound` survivor is
  `pageValue > Number.MAX_SAFE_INTEGER`.
- **No test fails one guard clause alone.** `typeof assignee !== 'string' || assignee.trim() === ''` survives `||`→`&&`
  in four runs.
- **A side effect goes unchecked.** The four `bool-flip` survivors are the store's `save` flag (three `save = true`
  defaults, one call passing `false`): no test observes when the store writes.

Seventeen of the 21 survivors (81%) are `logic-flip` or `rel-bound`. With §3a, that is **40 of 57 product survivors
(70%) across both settings**.

This also sets E7's ceiling. On Terra brownfield there are 1–3 survivors per run, so the overall ratio has little
room to move (§7).

### 3c. The in-loop mutation check grades on an easier catalog than the outcome measure

The test stage's own check (`shiploop_mutation.py`, owner decision 2026-10-11) mutates up to `MUTANT_SAMPLE` = 8
changed product lines per check, and each survivor must be killed or given a disposition. It is the most-fired
test-stage gate in the 16 brownfield runs: `mutation_not_done` fired 15 times (metrics.json `gate_counts`). So the loop
works: the model's first draft leaves survivors, and the refusal makes it strengthen the tests.

But its `OPERATORS` negate comparisons (`<` becomes `>=`) instead of shifting them (`<` becomes `<=`), and have no
`&&`/`||` flip. In the 28 stage mutation records of those runs, all 79 comparison mutants were killed (77 failed a
test, 2 timed out, which the check counts as a kill), as were 68 of 70 integer and 4 of 4 arithmetic mutants. By its
own catalog the tests look near-perfect. The harness's `js-1` catalog finds the gap in the very classes the stage catalog leaves out.

This is a feedback problem, not a prompt problem. Meta's mutation-guided generation and MuTAP (§4) improve tests by
showing the model surviving mutants of the kinds that matter.

### 3d. Eager tests come from case granularity, not from the gate

The step plan lists one focused ID per criterion. The test-spec writes one row per ID, and its oracle becomes one
sentence carrying every assertion. In the brownfield run, TC_1's oracle names validation of eight bad inputs, ordering,
state, audit, notification, delivery and idempotency. The test duty then says "Each quoted test case becomes a test
titled with its ID". The result is `test('TC_1 bulk reassignment validates and moves only active tickets with
notifications')`: 40 lines, about 27 assertions, the first failure hiding the rest.

The assertions themselves are good. They hold the exact 60-minute threshold and the next millisecond, and check state
is unchanged on rejection, because that spec sentence names them. Only the shape is wrong.

The gate does not need one test per ID. `shiploop_test_counts.named` and `outcomes` match an ID on any non-skip output
line and let a failure win. So a `describe('TC_1 …')` group of several tests, or several tests titled `TC_1 …`, already
satisfies the base run, the candidate run and the floors. The case guide even asks for "one compact case record per
distinct behavior" (testing-and-documentation.md#test-cases); the ID scheme collapsed that to one per criterion.

### 3e. What earlier test-prompt experiments here found

- **E1** (stand-ins at the test stage, 2026-10-24): **ceiling**. Every arm killed every crude stand-in, so the case
  could not separate prompt variants.
- **E1b** (four subtle stand-ins modelled on a run-4 miss) is built and verified but was never decided
  (docs/shiploop-template-experiments-journal.md). Its `limit-never-trips` and `cross-field` stand-ins are the §3a
  patterns in miniature.
- **E6-K1**: a step-size bound stated as prose moved the metric 0.25→0.75 (inside the A/A spread, inconclusive). The
  same bound as a refusal moved it 0.25→1.00 (supports). This is ShipLoop's own measurement that a check moves
  behaviour more than prose does.
- The SDLC gates proposal (docs/shiploop-sdlc-gates-proposal-2026-10-30.md §3 #13) deferred property-based cases
  because "the mutation check is the instrument that would show weak tests". §3c shows that instrument cannot yet see
  the commonest weakness.

## 4. Outside evidence

A literature pass (2026-10-30) read 24 groups of sources; each is listed with its numbers, URL and a verification tag in
docs/experiments/test-stage-prompt-20261030/literature.md, cited here as L1–L24. Grouped by the design question each
answers:

| Question | What the evidence says | Strength |
|---|---|---|
| What context helps the model write tests? | The code body and its doc comment matter most; removing either hurt most (L4). An existing test file from the same module doubles fail-to-pass and passing rates (L7). Generic retrieved tests and few-shot examples hurt smaller models (L7). Coverage-gap lists add little coverage (≤2%, L5). | Firm on older models; untested on frontier agents |
| Where must expected values come from? | Code-visible oracles copy the bug: 3.84% of tests asserted it with buggy code vs 0.46% with fixed code. Spec plus code ≈ code (3.80%); spec only found the most bugs (L9, 11 models including Claude 4 Sonnet). A retry loop rewrote an expected value from the assertion error (L4). Discarding tests that fail on the current code throws away bug-revealing ones (L10). | Firm; contested only for targeting, where code helps (L11, L13) |
| What feedback improves tests? | Surviving mutants fed back: +28% buggy programs detected (L6 MuTAP). Meta built a production system on it (L2); Google shows surviving mutants in review (L3). Continuing after errors is the largest single lever (L5). Running tests before submitting raises fail-to-pass (L12). | Firm |
| What stops weakening and special-casing? | Checks and an allowed abort: GPT-5 54% → 9% (L19). A short anti-hack prompt with an escape hatch works on Claude 4 (47% → 5%) but not on Claude 3.7 or o3 (L18, L20). Read-only tests stop edits, not special-casing (L19). | Firm; prompt effect depends on the model |
| How long, and in what order? | Padding a task to about 3k tokens cut accuracy 0.92 → 0.68 (L22). Later instructions are dropped more, mostly by omission (L21). Long data first and the task last scores up to 30% better (L23). Explain the why; capitalised "MUST" over-triggers newer models (L23). | Firm in general; no study ablates test-writing prose in an agent prompt |
| What shape should the tests take? | One behaviour per test, named for it, through the public API, checking state (L24). LLM suites show Assertion Roulette in 38–49% of class-level suites, and exception-path tests are rare (7–23%, L17). | Firm |
| Property-based tests? | One property test finds about 50× the mutants of an average unit test (L14). But LLM-written properties are often unsound: 41.7% valid at best (L15). Tests of properties the code explicitly claims are the productive kind (L16). | Moderate |

Two corrections to common intuition, for ShipLoop specifically:
- **Showing the code is not the risk; showing it before the expected values are fixed is.** ShipLoop's
  test-spec-before-implement order already matches the strongest oracle result (L9). §6b makes it bind the values,
  not just the topic.
- **ShipLoop already has the levers the evidence ranks highest.** It continues after errors (the Until Loop), runs the
  tests before submitting (the check callback), feeds back surviving mutants (§3c), keeps a fail-to-pass rule (the base
  run) and an allowed abort (`send-back`). The gaps are what those levers are shown (§3c) and the context the model
  starts from (§2), not missing instructions.

## 5. Design principles

Each principle names the evidence behind it. A principle tagged *[prompt]* is a sentence in the duty, *[context]* is
data the packet supplies, and *[check]* is enforced by a script.

1. **The oracle is fixed before the code is seen** *[prompt, test-spec]*. Each case lists concrete expected values from
   the spec, written before implement (L9, L8). The test stage takes values from there, never from a run or a failure
   message (L4, L10).
2. **The code chooses the inputs** *[context + prompt]*. Show the step's diff. Ask for each limit and one past it, and
   for each guard clause failing alone (§3a, L24 Yang, L4).
3. **A value the spec leaves open is a spec gap, not a guess** *[prompt]*. Test it as the code documents it and name it
   in the summary. The document stage, whose duty already writes "a vague clause this step made precise" into the R-n
   entry, then records it, so the next reader sees it was the code's choice.
4. **Feedback shows the misses that matter** *[check]*. The in-loop mutation catalog includes the classes that survive
   the outcome measure (§3a, §3c, L2, L3, L6).
5. **One behaviour per test, grouped under the case ID** *[prompt]* (L24, L17, §3d).
6. **The repository's own test is the example** *[context]*, never a generic one (L7).
7. **Each gate is stated once, as what it checks** *[prompt]*. The refusal carries the detail (L21, L22, L23, E6).
8. **The escape hatch stays, with its why** *[prompt]*. `send-back` is a correct outcome; one sentence says why a
   weakened test proves nothing. Nothing is capitalised (L18, L19, L23).
9. **Properties only for stated invariants and random behaviour** *[prompt]* (L14–L16). Not gated (§6e).
10. **Data before the task** *[layout]*: test on one stage before any cross-stage packet reorder (L22, L23).

## 6. Proposed changes

### 6a. The test-stage duty (prompt-only; arm P of E7)

Today's duty items 1–8 are 680 words. The draft below is 474. It keeps every obligation a gate or a later stage reads
(the case ID in the name, mocks built first, harness decisions in KNOWLEDGE/environment.md, the result fields,
send-back and blocked). It drops what the packet already says elsewhere (end states, proof limits, floor and base-run
rules, which the Checked-by line and the refusals carry) and the one vague instruction ("Test the new code in detail:
unit and mock tests first, then any MCP server or skill this host offers where it observes more").

Its second line names two inputs the packet supplies only with §6c. In arm P, the prompt-only arm, the model finds them
itself: the diff with `git diff` against the item base, the example among the step plan's house-style exemplars.
Arm C then measures what printing them adds.

```text
Your tests are this step's evidence: each should fail if the behaviour its case names broke, and say what broke.
Read first: the step's product diff, the spec text each case follows, the cases, and the repository's example test.

1. **One behaviour per test.** Each quoted case becomes a group titled with its ID as its own word (`describe('TC_1
   …')`, or the runner's equivalent), holding one test per behaviour its oracle names, so a failing name says what
   broke. Put it in the suite and command the case names. Write no case due at a later stage.
2. **Inputs from the code, expected values from the case.** Read the diff for the inputs worth trying: each comparison
   at its limit and one past it, each condition of a compound guard failing on its own, each error or refusal branch
   (assert its type, the field it names and that state is unchanged), each new setting at its default and overridden.
   Take every expected value from the case's oracle, written before the code existed, or from the spec text; never from
   running the code: a test that copies the code's output passes on the bug. Where the code fixes something the spec
   leaves open (a limit, a default, a message), test it as the code documents it and name it in the summary as a spec
   gap, so the document stage records it.
3. **Deterministic.** Build the mock each case names in `mock` before its test, playing what it says (slow, failing,
   out of order), with a header saying what it stands in for. Inject the clock and randomness; for random behaviour
   assert what must hold for every seed (bounds, counts, no overlap) over several seeds.
4. **Match the repository.** Follow the example test's layout, helpers, fixtures and assertion style; reuse a helper
   before writing one. A facility you must build: validate it first and record it in KNOWLEDGE/environment.md
   ## Harnesses and suites.
5. **When a run fails**, the case's oracle decides which side is wrong: find out with one small observation, then fix
   the product. Never copy a value from a failure message into an assertion. Change a test only when the test itself
   is wrong, with the reason in RUN/notes/<action>.md; a run made green by weakening a test proves nothing.
6. **When a case cannot be tested as written**, the spec contradicts itself, or a recorded command is wrong or cannot
   run here, report send-back naming it: that is a correct outcome. Report blocked only when a person or an outside
   service must act.

Result fields: `red_na` `[{"id", "reason"}]` for a new test that passes on the base; `retired_tests` `[{"id", "reason":
"<the R-<n> or AD-<n> that retires it>"}]`; `lint_waivers` `[{"id", "reason"}]`. The summary names each test by ID and
what it asserts, and which harness and suite decisions you kept or changed and why.
```

### 6b. The test-spec oracle (prompt-only; part of arm P)

Change the `oracle` placeholder in `CASE_PLACEHOLDERS` (skills/shiploop/scripts/shiploop_expectations.py) from "<what
observes the behaviour, and where>" to one behaviour per clause: "<each behaviour the case checks, as `input or action
→ expected value`, the value taken from the spec>". The IDs stay one per criterion, so the step plan, focused commands
and floors are untouched. The test stage gets a list to turn into one test each, instead of a sentence to cram into one.

The bigger reason is principle 1. Test-spec is the one stage that writes expected values before any product code
exists, which is the condition L9 found best. Today the oracle names the topic ("check wording", "reject [...] with
400") and leaves the values to the test stage, which then picks them while reading the code. Asking test-spec for
`input → value` pairs moves the choice of values to the moment the evidence favours.

### 6c. Context supply (script; arm C)

Add two lines to the test packet, as data, beside the hand-offs it already quotes:
- **The step's product diff**: the changed product files (the document packet's "Changed since the item base" already
  computes them) and a path to the diff written under RUN/, never cut (the owner's no-small-caps rule: spill to a
  file).
- **One example test**: the repository's test file nearest to the changed paths, which the house-style match contract
  at step-plan already names among its exemplars (house-style.md#write-the-match-contract).

### 6d. Mutation operators the loop is missing (script; arm M; a gate change)

Add `rel-bound` (`<`↔`<=`, `>`↔`>=`) and `logic-flip` (`&&`↔`||`) to `shiploop_mutation.OPERATORS`, as `js-1` has them.
The rule stays as built: no kill-rate threshold, and every survivor is killed or given a disposition (`equivalent`,
`out-of-scope`, `not-exercisable`).

Expected cost: more `mutation_not_done` refusals until the tests sit on limits. It also changes what a stage mutation
record's kill count means, so stage kill counts across versions stop being comparable. The harness's `js-1` outcome
ratio is unaffected.

### 6e. What not to do

- **Do not add anti-tampering prose.** The floors, the base run, the mutation check and an allowed `send-back` are what
  the outside evidence credits (§4). Restating them a sixth time costs attention and buys nothing measurable.
- **Do not grow the duty with a test-smell checklist.** Item 1's shape rule and the example test carry it.
- **Do not reorder the whole packet yet.** Putting data before instructions (§4) is a cross-stage change to every
  packet; measure it on one stage first, after E7.
- **Do not gate property-based tests.** §6a item 3 asks for invariants over seeds where behaviour is random, which is
  where §3a's arithmetic survivors live. A gate waits for a live run that shows it.

## 7. Experiment E7: does the smaller, data-first prompt write better tests?

Use the template-field harness (test/shiploop_e2e/experiment.py), which already runs step slices with a prompt overlay
per arm and decides against the A/A spread.

| | |
|---|---|
| Claim | Arm P (§6a + §6b) kills more mutants of the changed product lines than arm A (today's main), at no loss in hidden checks; arm C (P + §6c) more than P; arm M (A + §6d) more than A. |
| Cases | `stand-in-rules` (E1b's, built and verified; seed at `test-spec`, stop after `test`), plus one brownfield case such as `ticket-escalation`, seeded at `test-spec` from a saved Codex Terra run, which needs a step case built from it. |
| Arms | A = main; P = A + overlay (prompt-only, both texts above); C = a branch with P plus §6c; M = a branch with §6d only. |
| Evaluators | E1b's stand-in kill fraction (exists); new: the changed-line `js-1` mutation ratio, the method of docs/experiments/test-stage-prompt-20261030/changed_line_mutation.py, excluding test-support files. Also recorded, not scored: tests per case ID, assertions per test, test-stage seconds, refusals by gate. |
| Samples | 4 per arm (the harness's rule for an A/A spread). |
| Hosts | Codex Terra (the owner's E2E runner) first; DeepSeek flash when its monthly limit resets, since a weaker model is where prompt wording shows most. |
| Decision | Adopt P if it supports over A on either evaluator and contradicts on neither; C and M each only if they support over the arm they extend. |

Cost: four arms × two cases × four samples = 32 slices, each a test-spec plus test stage, about 2–5 min on Terra.

**Ceiling risk (E1's lesson).** On Terra brownfield the delivered suites already kill about 0.90 of changed-line
mutants (§3b), leaving 1–3 survivors per run. An A/A spread at that level can swallow a real gain. So:
- score the brownfield case by survivors in the two classes §3a and §3b name (`rel-bound`, `logic-flip`), not by the
  overall ratio;
- run DeepSeek flash as soon as its limit resets: its one measured greenfield run left 17 product survivors, against
  9–10 for Sonnet on the same case (greenfield-survivors.json), so it has more headroom;
- if A and P both sit at the ceiling there, build a step case whose code must introduce a limit and a compound guard
  that the request leaves open (a body-size cap, a name-length bound). That is where §3a's survivors come from.

### 7a. As built, 2026-10-30

The owner chose D1 ("Yes, build E7"). Three things changed from the plan above; each has its evidence.

- **The score is the limit-and-guard kill fraction on both cases, not E1b's stand-in fraction.** The 12 saved E1b
  samples (Grok 4.7, 2026-10-24) all killed 4 of 4 stand-ins, a ceiling. Scored by the new evaluator, the same trees
  killed 0.57–1.00 of their `rel-bound` and `logic-flip` mutants; arm A's two sample pairs averaged 0.69 and 0.75.
  So `value` is that fraction on the product lines the slice wrote (evaluators/e7_tests.py), and the stand-in fraction
  is recorded beside it. Evidence: e1b-trees-e7.json.
- **The brownfield case is ticket assignment, not escalation.** In the four 2026-10-29 Terra assignment runs all 10
  changed-line survivors are `rel-bound` or `logic-flip`, against 5 of 9 in the escalation runs (four are `bool-flip`
  on a `save` flag). The new step case `tickets-assign` (step_cases.json) is ticket-assignment without the listing
  filter and the command line, as one step on the pinned `node-tickets` fixture. Its hidden check fails on the base and
  passes on two Terra deliveries.
- **Arm M replaces the four relational negations with boundary shifts** instead of adding beside them. A stage mutant
  is named `file:line:column` (`mutant_id`), so two operators on one token would share a name. The negations were also
  killed 77 of 79 times (§3c). `logic-flip` is added.

Smaller points:
- Arm P also adds one clause to test-spec's duty item 3 (`input or action → expected value`). The placeholder alone
  shows only in the result template.
- Arm C's two lines were checked in the first live test packets of both cases. The diff file held the five changed
  product files on `tickets-assign`, and the example tests named were the existing tests of those files.
- On Terra a slice took about 3 min (the test stage 35–80 s), within the plan's 2–5. The Grok 4.7 E1b slices took
  20–30 min.

| | |
|---|---|
| Arms | A = 7fce12e4 (origin/main, ShipLoop 1.23.1); P, C, M = A + overlays/e7-p.json, e7-c.json, e7-m.json; D (round 2, E7-K2 only) = A + e7-d.json, arm C's packet lines on today's duty |
| Experiments | E7-K1 (`stand-in-rules`), E7-K2 (`tickets-assign`); 4 samples per arm; seed at test-spec, stop after test |
| Host | Codex, gpt-6.1-terra at xhigh (hosts.RUN_DEFAULT_HOST) |
| Run | round 1: `experiment.py queue E7-K2 E7-K1 --arms C,M,A,P --jobs 5 --out ~/e2e-runs/e7-20261030` (32 slices); round 2: `queue E7-K2 --arms D,C,A,M --samples 8 --jobs 6` (20 slices: D 1–8, A, C and M 5–8). All 52 exited 0 and passed their slice verdicts |
| Verified | the overlays apply to A (`experiment.py verify E7-K1`); the evaluator scores weak tests 0.625 and boundary tests 0.875 on the reference (test/shiploop-e2e-experiments.test.py) |
| Decide | `decide E7-Kn A P`, `decide E7-Kn P C`, `decide E7-Kn A M` |

### 7b. Results, 2026-10-30: no arm adopted, and the noise is as large as the effects

Value = the killed fraction of `rel-bound` and `logic-flip` mutants on the product lines the slice wrote. "Harness" is
`experiment.py decide` against A, with the A/A spread from A's samples 1–2 against 3–4. "A-condition" pools A with the 7
arm-M runs whose test stage saw exactly A's packet and feedback (below). p is a one-sided permutation test.

| Case | Arm | n | Mean | sd | Survivors per run | Harness vs A | Over the A-condition, p |
|---|---|---:|---:|---:|---:|---|---|
| stand-in-rules | A | 4 | 0.836 | 0.097 | 2.75 | | |
| | P | 4 | 0.811 | 0.148 | 2.00 | contradicts | −0.04, 0.73 |
| | C | 4 | 0.831 | 0.065 | 2.00 | contradicts | −0.02, 0.68 |
| | M | 4 | 0.862 | 0.044 | 2.00 | inconclusive | +0.01, 0.47 |
| tickets-assign | A | 8 | 0.454 | 0.270 | 3.25 | | |
| | P | 4 | 0.582 | 0.161 | 2.50 | inconclusive | +0.05, 0.37 |
| | C | 8 | 0.688 | 0.125 | 1.62 | supports | +0.15, 0.06 |
| | D | 8 | 0.633 | 0.215 | 2.12 | supports | +0.10, 0.17 |
| | M | 8 | 0.646 | 0.194 | 2.12 | supports | +0.11, 0.14 |

1. **On `stand-in-rules`, nothing separates.** Every arm kills 0.81–0.86 and leaves 2–3 limit or guard mutants per
   run, whatever the prompt.
2. **On `tickets-assign`, the harness's three "supports" are within noise.** Arm M's stage check found a survivor in
   1 of 8 runs, and its packet never names the operators. So the other 7 runs saw exactly A's packet and feedback, and
   they still scored 0.17 above A (p 0.08). That gap is an A/A difference. The harness's spread (0.13) understated A's
   sd of 0.27. Against all 15 A-condition runs, C is +0.15 (p 0.06) and D +0.10 (p 0.17).
3. **The rewritten duty (P) changed neither the score nor the tests' shape.** One test per behaviour was followed in 1
   of 20 P and C runs (C's first `stand-in-rules` run, 13 tests). Every other run wrote one test per case ID; on
   `tickets-assign` each held 10–14 assertions. A sentence asking for a different shape did not move the shape, which is
   the owner's doubt about prose, measured.
4. **The packet lines (C, D) are the only change with a visible mechanism, and they are not established.**
   - C has the lowest spread: it never scored below 0.5, and 1.6 limit or guard mutants survived per run against A's 3.25.
   - In C's first run the tests write a 65-character assignee into the data file and expect the load to refuse it.
     That guard is one the code introduced and only the diff shows. A's tests tried 65 characters only over HTTP.
   - But the load-path 64-character bound still survived in 4 of 8 C runs (A: 5 of 8), and D and C overlap
     (C − D = +0.05, p 0.31).
5. **Arm M as built cannot act.** The stage check samples 8 mutants spread across the changed files.
   - On `stand-in-rules` it drew 2–6 limit or guard mutants per run, all already killed.
   - On `tickets-assign` it drew 0–2, all killed. They were often on the same load-path guard line as the evaluator's
     survivors, but on other clauses of it.
   - The gate's one survivor in 12 runs was an `integer` mutant (64 → 65 in validate.js), which A's catalog also has.
   So the new operators never produced feedback, and M's scores are A's scores.
6. **Most of the variance comes from implement, not the test stage.** Each run's implement writes different code: 5–7
   limit or guard sites, with or without a validator on load. That changes both how many mutants there are and how hard
   they are to kill. A sample that varies the code cannot isolate a change to the test prompt. (§7c and §7d measure
   it: the guard's shape followed the arm unevenly, and with one implementation held fixed A's sd fell from 0.27 to
   0.09.)

By §7's rule nothing is adopted. P contradicts on `stand-in-rules`. C does not support over P on either case at n=8
(P n=4). M's gain cannot come from its gate. Nothing ships (D3).

What would decide it (D4–D6):
- **Hold the implementation fixed.** Seed at the test stage with a recorded implement result and one Terra delivery's
  product files laid over the worktree after the item base, so only the test stage varies. `release_slice.copy_home`
  already lays files over a run's worktree after its base is recorded, for a delivered item. Rerun A, D and C there.
  P's oracle change needs test-spec in the loop and has shown nothing, so it can wait.
- **Fix the decision rule's noise estimate.** A 2-against-2 spread called three A/A-sized gaps "supports". A
  permutation test over all control samples, or the spread over all of them, would not. Earlier E-decisions would
  read differently, so the change is the owner's call.
- **Targeted sampling for M.** Only if the stage check prefers limit and guard mutants on changed lines would §6d act.
  That changes a gate's cost.

Evidence: e7-results.json (52 scored samples and 10 decision records); e7_analysis.py prints the table's p values
from it; decision records under ~/e2e-runs/e7-20261030/E7-K*/decision-*.json; journal lines in
docs/shiploop-template-experiments-journal.md.

### 7c. E7-F: the implementation held fixed (D4), as built

**What the 36 E7-K2 runs show about the implementations.** Each run's implement tree was recovered from its step proof
(`RUN/tests/<implement>-step-proof<n>.md`, `trees`):
- Every limit and guard site on the changed lines is in one place: the compound guard added to `readTicket` in
  src/persistence.js, which refuses a stored assignee that is not null, not a string, blank, over 64 characters or (in
  most runs) holds a control character. Validation over HTTP reuses the existing `text(body, field, 64)`, so it adds
  no new site.
- So E7-K2's value counts how many kinds of bad stored assignee the tests load from the data file. Each `|| → &&`
  mutant survives unless one test loads a record that is bad in exactly that one way.
- Implement wrote the guard with 5 sites in 16 runs (mean value 0.75), with 6 in 13 (0.44) and with 7 in 1. In the
  other 6 runs implement never persisted the assignee. The test stage's restart test caught that, and the test stage
  added the persistence and the guard itself (A2, C4, C5, M1, M3, M8; mean 0.60).
- The arms drew different shapes, and the shape moves the score as much as the arm does:

  | Arm | 5-site runs: n, mean | 6-site runs: n, mean | Guard written by the test stage: n, mean |
  |---|---|---|---|
  | A | 3, 0.73 | 4, 0.25 | 1, 0.43 |
  | C | 5, 0.68 | 1, 0.50 | 2, 0.80 |
  | D | 3, 0.80 | 5, 0.53 | 0 |
  | M | 3, 0.87 | 2, 0.50 | 3, 0.52 |
  | P (one 7-site run, 0.43) | 2, 0.70 | 1, 0.50 | 0 |

  C's lead over A in §7b is mostly the five easier implementations it drew. Among 5-site runs C is below A. Among
  6-site runs A is lowest, three of its four at 0.17. This is a stratified reading of small cells, not a test. It is
  why the rerun below holds the implementation fixed.

**The seed.** `slice.py --seed-at test --seed-from <earlier slice>` (`recorded_delivery`, `run.seed_run`'s
`implementation`):
- It records test-spec and implement with the earlier run's own accepted results, less the keys that locate that
  run's files and commits (`evidence_refs`, `learned_from`).
- It lays implement's change, the tree of its last passed step proof against the item's base snapshot, in the new
  worktree, uncommitted, after the item's base is recorded.
- The opening prompt says the step's implementation is in the worktree.
- Checked on the source chosen below: the seeded test packet equals that run's own test packet line for line, but for
  three locators to implement's evidence the seed does not carry (its lint gate record, loop receipt and notes).
  Both case checks pass on the seeded worktree. Hermetic test:
  `test_a_seed_at_test_lays_an_earlier_slices_implementation_uncommitted_after_the_item_base`.

**The source: E7-K2 arm A sample 6.** It was chosen before any E7-F run, by four rules:
- an A run, so the packet before the test stage is today's;
- the modal 6-site guard;
- an implement that wrote no test file, and a test stage that changed no product code;
- a mid-range score (0.5), leaving room both ways.
A3 and A7 met the first three rules but scored 0.17.

**Arms and decision rule (fixed before the runs).** Arms A, D and C on 7fce12e4 with E7's overlays, 8 samples each, Codex
Terra at xhigh. P waits, because its oracle change acts in test-spec, which is now recorded. M waits on D6. The
reading:
- An arm is adopted only if it beats A by a one-sided exact permutation test at p < 0.05 over all 8 + 8 samples.
- Its gain must also exceed A's own split-half gap (samples 1–4 against 5–8).
- `experiment.py decide` runs as well and is reported beside it, not used.
- C over D at the same bar would credit the shorter duty.

**Run.** `experiment.py queue E7-F --arms D,C,A --samples 8 --jobs 6 --out ~/e2e-runs/e7-20261030`, after the smoke
sample A/1. All 24 slices exited 0 and passed their verdicts, at 2.0–2.5 min each (the test stage 68–111 s).
- In every sample the test stage left the five laid files byte for byte and changed no other src/ file
  (`product_as_recorded`, 24 of 24). So every sample was scored on the same 6 sites.
- D/1's first scoring failed its own baseline run: the existing restart test in test/service.test.js hung up a socket
  (ECONNRESET). The same suite then passed 5 times of 5 in that worktree, and D/1 was rescored alone (its score.json
  says so).

### 7d. E7-F results, 2026-10-30: no arm adopted; with implement fixed the noise falls to a third

| Arm | n | Mean | sd | Survivors per run (of 6) | Tests per case ID | Assertions per test | Test stage s | Permutation vs A | `decide` vs A |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| A | 8 | 0.604 | 0.086 | 2.38 | 1.04 | 11.9 | 91 | | |
| D | 8 | 0.625 | 0.118 | 2.25 | 1.17 | 10.6 | 98 | +0.02, p 0.50 | supports (spread 0.00) |
| C | 8 | 0.583 | 0.089 | 2.50 | 1.42 | 9.9 | 81 | −0.02, p 0.84 | contradicts |

A's split-half gap is 0.04. C against D: −0.04, p 0.84 (`decide`: contradicts).

1. **Nothing meets the rule, so nothing is adopted.** Neither packet change moved the kill rate on a fixed
   implementation. The source run's own test stage scored 0.5 on it; its eight A reruns scored 0.5 three times and
   0.67 five times.
2. **Implement was most of E7-K2's noise.** A's sd fell from 0.27 (E7-K2, implement free) to 0.09 here. Every run of
   every arm killed 3 or 4 of the same 6 mutants (one D run killed 5).
3. **The survivors are the same in every arm.**
   - The two `|| → &&` mutants on the guard's first line survived together in 21 of 24 runs, and at least one of them
     in all 24. Both turn on the clause `ticket.assignee.trim() !== ticket.assignee`. A test kills them by loading a
     stored name with surrounding spaces; the first one also dies to a non-string stored assignee whose exact error the
     test checks. The trimmed-name rule is an invariant the code introduced, not one the request states. The HTTP
     validator trims every name (`text` in src/tickets/validate.js), so only a hand-edited data file can hold one. C
     and D printed the diff that shows the clause, and no run loaded a padded name.
   - `length > 64 → >= 64` on the load path survived in 4 of 8 runs of each arm. Test-spec's own TC-1 asks for a
     64-character name and a restart. Half the runs in every arm combined the two.
4. **The shorter duty moved the tests' shape a little, not what they kill.** C wrote more than one test per case ID in 5
   of 8 runs (A 1, D 3), averaging 1.42 tests per ID against A's 1.04 (one-sided permutation p 0.03). It put fewer assertions in
   each (9.9 against 11.9) and finished 9 s faster (p 0.04). §7b item 3 saw no such change with test-spec free. Still
   no run wrote one test per behaviour, and the kill rate did not change.
5. **`decide`'s rule failed again, more plainly.** A's samples 1–2 and 3–4 both average 0.583 on this discrete metric
   (each run kills 3 or 4 of 6). So the spread is 0.00, and D's +0.02 (p 0.50) reads "supports". That is the second time
   in one day the 2-against-2 spread passed noise off as a gain (D5).

What this settles, and what it does not:
- **Settled for this case and model:** the diff and example-test lines (D), and the shorter duty with them (C), did not
  raise the kill rate of the step's limit and guard mutants. With an sd near 0.1 and 8 samples per arm, a real gain of
  0.15 would very likely have shown; one under 0.1 could hide. E7-K2's apparent gains are best explained by which
  implementation each arm drew (§7c), though that reading rests on small strata.
- **Not settled:** whether surviving limit and guard mutants fed back by the stage's own check would close the two
  gaps above. That is the lever the literature measured (L2, L6), and the one arm M could not exercise (§7b item 5).
  The fixed seed makes it a cheap test: the stage check sampling these 6 sites first (D6, as an overlay arm) on E7-F,
  against A's 8 samples above.
- **Not settled either:** other cases, models and hosts. E7-F is one implementation of one brownfield step, on Codex
  Terra.

Evidence: e7-results.json (E7-F rows: `product_as_recorded`; E7-K2 rows: `implement_sites`; 13 decision records);
e7_analysis.py prints §7c's shape table and this section's p values; ~/e2e-runs/e7-20261030/E7-F/decision-*.json;
journal lines in docs/shiploop-template-experiments-journal.md.

### 7e. E7-F arm T: the stage's own mutation check feeds back the guard's sites (D6), as built

**What the stage check drew in A's runs.** In all 8 A runs it sampled the same 8 mutants of the recorded implementation
(RUN/tests/*-mutation1.md), none of them limit or guard mutants:
- `!==`/`===` swaps and `64 → 65` on the guard's two lines, the other files' integers and comparisons;
- it killed all 8 in 7 runs. In A/7 one survived, `64 → 65` on the existing requester limit (validate.js:12), and the
  test stage recorded it `out-of-scope` with evidence. In none of the 8 runs did a refusal name one of the 6 sites the
  evaluator scores.

**Why arm M could not change that (§7b item 5).** A dry run of the check's own `candidates` and `sample` on A/1's
worktree (lines changed against the seed commit) shows:
- today's catalog: 13 candidates, none limit or guard;
- M's: 17 candidates, 5 of them limit or guard, but the even spread picks the same 8 as today;
- M's `(?=\s)` cannot match the `||` that ends line 144 (persistence.js:144:118), one of the two trimmed-name
  flips that survived in all 24 E7-F runs (§7d item 3).

**Arm T** (overlays/e7-t.json, on 7fce12e4):
- M's catalog, with logic-flip also matching an operator that ends its line;
- `sample` takes the limit and guard mutants (rel-bound, logic-flip) first, spread as before, and the other operators
  fill what is left of the 8.

On A/1's worktree T's sample is exactly the evaluator's 6 sites: persistence.js 144:32, 144:72, 144:118, 145:24,
145:50 and 145:55. The other two picks are the integer on app.js:38 and the comparison at persistence.js:144:59.

Everything else in the check is unchanged: 8 mutants, a refusal naming each survivor that has no disposition, and the
three dispositions. The packet is A's. Hermetic test:
`test_e7_arm_t_samples_the_limit_and_guard_mutants_first_and_flips_a_line_ending_or`.

**What T's score can and cannot show.** T's check samples the very sites the evaluator scores. So a gain shows that the
feedback is acted on: a survivor the refusal names becomes a test that kills it, not a disposition. It does not show
how targeted sampling does on code it was not shaped on, nor its cost there. That needs another case.

**Decision rule (fixed before the runs).** 8 T samples (`--no-early-stop`), Codex Terra at xhigh, against A's 8 E7-F
samples in §7d:
- The primary reading is §7c's: one-sided exact permutation p < 0.05 over 8 + 8, and a gain larger than A's split-half
  gap (0.042).
- Reported beside it, per run:
  - each of the 6 sites killed by a test or given a disposition;
  - each disposition checked against the code (a stored ticket record reaches every site through the load path, so a
    disposition has to show that no stored record tells the mutant apart);
  - the number of mutation refusals, and the test-stage seconds against A's.
- `decide` runs as well, reported, not used.
- If T meets the primary bar, D6 goes to the owner as a recommendation, with its measured cost; adopting it changes a
  gate's cost and is the owner's call. If T does not, the per-run rows say why: survivors disposed instead of killed,
  or tests that kill only at a cost.

## 8. Out of scope here: the UI verification route (Salesforce run, 2026-10-30)

The owner relayed feedback on the Codex Salesforce Battleship run (`~/e2e-runs/2026-10-30/shiploop-salesforce-battleship-zbcb4i5d`):
- **R-4 (rendered UI) was handed to the user**, because the runner had no authenticated browser.
- **The automatic document skip left an incomplete result**, which Improve rejected.

The first does bear on testing, but not on this prompt. Test-strategy's duty already makes each case that needs a host
tool probe it and record a failed probe as an access gap, and that is what happened. The fix is an authenticated UI
route the runner can use, verified at preflight, with the required UI checks named in the case. That is environment and
harness work, and a Salesforce rerun deploys to the owner's org, which needs the owner's go.

The second is a script defect, confirmed on main: `_document_entry` in shiploop_navigator.py builds the skipped
document result with no `assumptions` and no `knowledge`. It is proposed as its own session.

## 9. Decisions for the owner

- **D1.** Build and run E7 as in §7: arms A, P, C, M on `stand-in-rules` plus one brownfield case, on Codex Terra.
  (Recommended. Launching verification runs is routine; the brownfield step case is new harness work.)
- **D2.** §6d changes a gate's operator catalog, so it changes what stage mutation records count. Run it only as an
  experiment arm until E7 decides, or adopt it now on §3a/§3c's evidence? (Recommended: experiment arm first.)
- **D3.** On E7's verdict, ship the winning arm in one release, with a change note and a journal entry citing E7's
  decision files.
- *Outcome, 2026-10-30:* D1 was run, with M as an experiment arm only (D2). No arm won, so nothing ships under D3
  (§7b).
- **D4.** Rerun E7's test-stage arms (A, D, C) with the implementation held fixed: a new slice seed at the test stage
  that lays one delivery's product files over the worktree after the item base. (Recommended: harness work only, and
  the one design that can separate a test-prompt change from implement's variance.)
- *Outcome, 2026-10-30:* D4 was built and run as E7-F (§7c, §7d). No arm is adopted. Nothing in ShipLoop changes, so
  there is nothing to ship under D3.
- **D5.** Replace `decide`'s 2-against-2 A/A spread with a permutation test over all control samples. Earlier
  experiment verdicts would read differently. E7-F adds a second case: a spread of exactly 0.00 on a discrete metric
  turned +0.02 (p 0.50) into "supports".
- **D6.** Give the stage mutation check targeted sampling (limit and guard mutants on changed lines first), so §6d can
  act. This is a gate-cost change. E7-F makes it cheap to try first as an overlay arm: on the fixed implementation, its
  six sites are the whole target, and A's 8 samples are the control (§7d). (Recommended next, as an experiment only.)
- *Run, 2026-10-30:* the owner said "Yes, run the D6 arm". It runs as arm T of E7-F, with its decision rule fixed
  before the runs (§7e).

## 10. Journal

| Date | Entry | Status | Evidence |
|---|---|---|---|
| 2026-10-30 | Packet anatomy of the test stage: craft 7%, gate text restated 5–14 times, no diff or example test in the packet | firm (one packet; the template is fixed, so others differ only in hand-off sizes) | packet-anatomy.txt |
| 2026-10-30 | Greenfield survivors: 23 of 36 product survivors are `rel-bound` or `logic-flip` on limits and guard clauses the code introduced | firm for these three runs | greenfield-survivors.json |
| 2026-10-30 | The stage mutation catalog has neither class; its mutants end killed (151 of 153, two of them by timeout; the 2 survivors are integer mutants; 28 records) | firm | §3c tally, run/tests/*-mutation*.md under ~/e2e-runs-brownfield/2026102*/ |
| 2026-10-30 | Eager tests follow from one case per criterion and "becomes a test"; the gate allows a group per ID | firm (code read: `shiploop_test_counts.named`, `outcomes`) | §3d |
| 2026-10-30 | Brownfield changed-line `js-1` on 12 Codex Terra runs: 196 of 217 killed (0.903); 17 of 21 survivors are `logic-flip` or `rel-bound` (`length > 64` in 6 runs); 40 of 57 product survivors across both settings | firm for these runs (one model, one product family) | brownfield-mutation.json, changed_line_mutation.py |
| 2026-10-30 | Literature: oracles fixed before the code is seen find the most bugs (L9); feedback with surviving mutants and an allowed abort are the measured levers (L2, L6, L19); length and distractors cost accuracy (L22). No study ablates test-writing prose in an agent prompt | firm for the cited results; the prose question stays open, hence E7 | literature.md |
| 2026-10-30 | Proposal: §6a duty (474 words against 680), §6b oracle as `input → value`, §6c diff and example test, §6d two operators; E7 to decide | interim, awaiting the owner's decisions | §6, §7, §9 |
| 2026-10-30 | E7 built: evaluator e7_tests.py (limit-and-guard kill fraction), case `tickets-assign`, overlays e7-p/c/m on 7fce12e4; queue launched on Codex Terra | interim, running | §7a; e1b-trees-e7.json |
| 2026-10-30 | E1b's stand-in score is at its ceiling (12 of 12 samples killed every stand-in), while the same trees kill 0.57–1.00 of their limit and guard mutants | firm for those 12 Grok 4.7 samples | e1b-trees-e7.json |
| 2026-10-30 | E7 decided: no arm adopted. `stand-in-rules`: all arms 0.81–0.86, none separates. `tickets-assign` (n=8): the harness says C, D and M support over A, but 7 arm-M runs that behaved as A scored +0.17 over A (p 0.08); over the 15 A-condition runs C +0.15 (p 0.06), D +0.10 (p 0.17) | firm for these runs (one model, two cases); supersedes the round-1 reading "C supports over P" (n=4) | §7b; e7-results.json; e7_analysis.py |
| 2026-10-30 | Prose did not change test shape: one test per behaviour in 1 of 20 P and C runs | firm for these runs (test-spec free); revised 2026-10-30: with test-spec fixed, C moved shape a little (§7d item 4) | e7-results.json (mean_titles_per_id) |
| 2026-10-30 | The 8-mutant stage sample never drew a surviving limit or guard mutant (0–6 drawn per run, all killed, in 12 of 12 runs); the gate's one survivor was an `integer` mutant | firm for these runs | RUN/tests/*-mutation-check.md of ~/e2e-runs/e7-20261030/E7-K*/M/* |
| 2026-10-30 | `experiment.py decide`'s 2-against-2 A/A spread understated A's sd (0.13 against 0.27) and labelled A/A-sized gaps "supports" | firm (E7-K2) | §7b item 2 |
| 2026-10-30 | E7-K2's limit and guard sites all sit in one load-path guard. Implement wrote it with 5 sites in 16 of 36 runs (mean 0.75), 6 in 13 (0.44), 7 in 1, and not at all in 6 (the test stage added it). C drew five 5-site runs, A three. Among 5-site runs C is below A | firm counts (step-proof trees); the arm reading is a stratified look at small cells | §7c; e7-results.json (`implement_sites`) |
| 2026-10-30 | E7-F built: `slice.py --seed-at test --seed-from` holds test-spec, implement and implement's files fixed. The seeded test packet equals the source's own but for three evidence locators. Source E7-K2 A/6, and the decision rule, fixed before any run | firm (dry seed, smoke slice, hermetic test) | §7c; ff6a4e72 |
| 2026-10-30 | E7-F decided: no arm adopted. A 0.604 (sd 0.086), D 0.625 (+0.02, p 0.50), C 0.583 (−0.02, p 0.84); A's split-half gap 0.04. The test stage left the implementation as recorded in 24 of 24 runs | firm for this implementation (one model, one case) | §7d; e7-results.json; e7_analysis.py |
| 2026-10-30 | With implement fixed, A's sd fell from 0.27 to 0.09: implement, not the test prompt, was most of E7-K2's variance | firm (E7-K2 against E7-F) | §7d item 2 |
| 2026-10-30 | Survivors are the same in every arm: a trimmed-name invariant the code introduced (both `||` mutants together in 21 of 24 runs, at least one in all 24, though C and D printed the diff), and the 64-character load bound (4 of 8 runs per arm) | firm for these runs | §7d item 3; e7-results.json (`target_survivors`) |
| 2026-10-30 | The shorter duty moved test shape a little with test-spec fixed (1.42 tests per case ID against 1.04, p 0.03), not kill rate. This revises the shape half of the E7-K2 row "prose did not change test shape" | interim (one implementation) | §7d item 4 |
| 2026-10-30 | `decide` read +0.02 (p 0.50) as "supports" on a 2-against-2 spread of 0.00 | firm | §7d item 5; ~/e2e-runs/e7-20261030/E7-F/decision-A-D.json |
| 2026-10-30 | E7-F arm T built (D6): M's catalog with a line-ending logic-flip, and limit and guard mutants sampled first. A dry run on the fixed implementation: today's and M's samples are the same 8 mutants, none limit or guard; M's `(?=\s)` misses persistence.js:144:118; T's sample is the evaluator's 6 sites. In A's 8 runs no refusal named any of the 6 | firm (the dry run and A's mutation records); T's result pending | §7e; overlays/e7-t.json; ~/e2e-runs/e7-20261030/E7-F/A/*/slice/.shiploop-runs/seed/run/tests/*-mutation1.md |
