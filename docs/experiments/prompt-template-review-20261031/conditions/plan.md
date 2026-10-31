# Per-run condition test: plan (predeclared 2026-10-31, before any variant ran)

**Question.** Take the archived runs. A changed spec requirement states several independently observable conditions.
For what share of them does the run's own final test suite fail when the product is changed to violate exactly that
one condition?

**Why.**
- The ledger (6c626574) found no untested requirement at the level of requirement IDs.
- The condition-review pilot (488ffbd9) planted omissions on selected conditions. It left the natural gap rate
  unknown ("true gap frequency").
- This test measures that rate on real runs, with conditions taken from the spec text, not from the tests.

**Corpus.** Five runs with locally runnable suites, frozen in `conditions/*.requirements.json` (hashes in
`requirements.sha256`), 39 changed requirements in total. The five are chosen to cover four model subjects,
greenfield and brownfield work, and multi-item plans.

| key | run | subject | items | changed R |
|---|---|---|---|---|
| v2170-ds-battleship | ~/e2e-runs/20261027/v2170-ds-battleship-759a03 | DeepSeek flash | 3 | 10 |
| bf-ds-ticket-assignment | ~/e2e-runs-brownfield/20261028/bf-ds-ticket-assignment-09c33b | DeepSeek flash, brownfield | 3 | 12 |
| grok-web-battleship | ~/e2e-runs/20261025/gate-2132-f7ba78-grok-web/battleship | Grok | 2 | 6 |
| claude-csv-report | ~/e2e-runs/20261024/gate-290-b60ed7-claude-csv-report | Claude | 1 | 7 |
| codex-r2-user-listing | ~/e2e-runs-brownfield/20261029/bf-codex-r2-user-listing | Codex Terra, brownfield | 1 | 4 |

**Procedure.** One worker per run. Never edit an original; hash each original before and after.

1. **Conditions from the spec text only.** Before opening the checkout, split each requirement into atomic
   conditions. Each condition records:
   - id (R-n.k);
   - quote: the verbatim span it comes from;
   - observable: what a check from outside the code would see;
   - kind: behaviour, error, boundary, format, structural, tests-themselves, or preserved.

   Only behaviour, error, boundary and format conditions are variant candidates; the rest are listed with a reason.
   Write `conditions.json`, then record its sha256.
2. Copy the final worktree to a scratch directory. Find the run's own full-suite command from its records (the
   test-strategy, `tests/*-verify*.md`, the system-test commands) and run it on the copy. It must pass. If it does
   not, exclude the run with the reason.
3. For each candidate condition:
   - write a minimal change to the **product** code (never the tests) that violates exactly that condition;
   - write an independent witness, a small outside check of the condition. It must pass on the copy and fail on the
     variant. Without such a witness the condition is `unwitnessed` and is left out of the rate;
   - run the full suite on the variant: `killed` if the suite fails, `survived` if it passes;
   - restore the copy.
4. Record per condition: the patch, the witness command and both its exit codes, the suite's exit code, and the
   failing test names.

**Measures.**
- Primary: kill rate = killed ÷ witnessed conditions, pooled and per run.
- Secondary:
  - requirements with at least one survivor;
  - each survivor's kind;
  - whether a recorded test case claims to cover the survivor (a weak assertion) or none does (absent);
  - the stage that owned it: the step whose criteria name it, or system-test.

**Decision rule (fixed now).**
- **No change, base rate recorded:** pooled survival ≤ 10% and no survivor is a primary requirement's core outcome
  (the main thing the request asks for).
- **Separate predeclared A/B first:** survival > 10%, or any core-outcome survivor. The A/B tests a test-spec or test
  prompt candidate before anything is adopted.
- This test alone never adopts a change.

**Checks by the parent.**
- Re-run every survivor's witness and suite.
- Re-run a sample of three killed conditions.
- Confirm the original hashes are unchanged.

**Limits.**
- One model reader enumerates conditions per run, and models write the variants.
- Suites run locally; no hidden E2E checks are joined.
- Five runs make a base-rate estimate, not a population claim.
