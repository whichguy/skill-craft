# Group C-step-entry: step-plan, test-spec, validate-existing (2026-10-31)

This review uses the regenerated stage-health table, which now counts refusals from the separate `shiploop check`
verb. It also covers two items the D reviewer handed over from implement's send-backs. The counting scripts are in
this session's scratchpad. Each one reads `trace.jsonl` and `results/` only.

### step-plan: verdict improve, plus one side test

**Signals:** 90 runs and 138 packets. There are 14 real refusals, all live, and 86 dry refusals across 50 runs; the
character caps among the dry refusals are retired. Median 1.5 min, 238 min in total.

**Findings:**

- **`shiploop check` says yes to drafts that `complete` then refuses.** All 14 real refusals are test-command shape
  rules: 13 are "a test command's criteria must be a nonempty list of distinct criterion IDs" and 1 is "…ids must be a
  nonempty list…". In every case, the check had already said yes to the same action.
  - Example: `~/e2e-runs-qr/20261031/A-user-listing-s1/events.jsonl` items 48–52. The model wrote the row
    `{"suite": "check", "command": "node --check src/server.js", "criteria": []}`. The check said yes at 15:11:12Z;
    the model ran only the Until Loop's done; `complete` refused at 15:11:17Z.
  - Cause: `_submitted_result` returns the draft "without a shape check". `_evaluate` is shared by check and
    complete, and it never calls `_canonical_result`. Only `apply`, which runs in complete alone, calls it.
  - This breaks the invariant 5086baf6 built ("a matching yes cannot be refused"). It also contradicts the glossary
    entry for `shiploop check`.
  - The same gap hit 2 Improve children's step plans and 1 system-test-author result.
  - All occurrences are on Codex Terra 6.1: 15 of the 61 runs since 2026-10-29.
  - Live: yes. The check branch at HEAD is unchanged.
- **The Result template teaches the empty list.**
  - The template's check row is `{"command": "<exit-code check command>", "suite": "check", "criteria": ["C2"]}`,
    and its C2 is `executed`. That row comes from 153160e1, when a check row meant "a README must document a flag".
  - Since d7388043, the check row is the item's lint, type or build command (duty item 5, done_when, glossary). Such a
    command confirms no criterion, so models write `[]` or attach a behaviour criterion.
  - In accepted step plans:
    - 37 of 106 check rows name an `executed` criterion;
    - 22 of 445 executed criteria are confirmed only by check rows;
    - at least 3 of those rest on a bare syntax check: `pa-ds-battleship-4ed4e3` C3 and C5 by `node --check`;
      `round-se-sigterm-2-b14d8c` C1, "paginate counts a trailing partial page", by `node --check src/paginate.js`.
  - Two of the 13 repairs made the mapping worse. In `A-ticket-assignment-s2`, `node --check src/app.js` now
    "confirms" C2, "endpoint validates arguments and state".
  - Live: yes.
- **Models read the expectation `from` field as provenance.** It drew 25 dry refusals in 22 runs:
  - 10 stray values: "baseline", "baseline, plan", or an assumption ID not due at this item;
  - 5 values that are not an ID, such as "W1 item commit 32cca35";
  - 10 cases where an assumption due at this item had no expectation.

  Duty item 6 lists `from` among every expectation's keys: `{"id", …, "check", "from"}`. The packet's open-item rows
  end "| from plan". Live: yes (`shiploop_expectations.py`; the duty wording comes from 153139f1).
- **Handed item 1: a Proof that names no test path.** ffea2956's proof-order rule reads paths, so it misses several
  forms of a Proof that cannot pass at implement:
  - `npm test` in `bf-codex-r1-user-listing` W1 S1. On the base this is the baseline suite, so it passes without the
    step: a vacuous Proof. The criteria's "Confirm by" texts also name the unwritten `test/user-listing.test.js`,
    which caused 2 implement send-backs.
  - `python3 -m unittest test_hello.GreetingTest.test_TC_1` in `shiploop-basic-repairs-44mijad9`: a module name
    rather than a path.
  - `sf apex run test --class-names …Test` in `gym-published-baseline-03` and the sf-fidelity `battleship-candidate`
    run: a class name on a remote target.

  `command_paths` returns `[]` for all four. Live: yes.
- **Handed item 2: broken Proof commands.** Five implement send-backs had a broken Proof, and no gate reads any of
  them:
  - unescaped shell quotes, so node threw a SyntaxError before any assertion (`A-ticket-assignment-s2`);
  - BSD `grep -P` (`trace-verify-4fd9f1`);
  - a sort-order assertion (`gate-2132` battleship);
  - `fs.rmSync` given `force:1` (`bf-codex-r2-ticket-escalation`);
  - a Proof that cannot be repeated, because it duplicates a permission assignment (salesforce-battleship).

  Run on the item base, the first two would fail visibly as a broken command. The next two fail only after the
  behaviour exists. The last only fails on a repeat, against a remote target.
- **Retired causes.** The criteria and proof character caps caused 10 dry refusals; 232689c5 removed both. Proofs
  that name an unwritten test path are now refused by ffea2956. The 13 "no result file" refusals are cheap and
  generic, so no change there.

**Proposal:**

1. **Mechanism.** In the navigator's `check` branch, run `_canonical_result(submitted, stage=cursor_stage, …)` before
   `_evaluate`. Record a "no" answer if it raises, as 5086baf6 did for F15 and P9. Add a fail-first test: a step-plan
   draft whose check row holds `"criteria": []` gets the same refusal from check as from complete.
2. **Template.** Use `{"command": "...", "suite": "focused", "ids": ["TC-1", "TC-2"], "criteria": ["C1", "C2"]}` and
   `{"command": "<exit-code check command>", "suite": "check"}`, with the regression row unchanged. This adds no duty
   text and shortens the head by about 6 characters.
3. **Duty item 6.** Drop `from` from the key list. Change the last bullet to: "Each open item listed for this item
   (`due: W<n>`) becomes an expectation with `"from": "<its A-<n>>"` whose check settles it; no other expectation has
   `from`." When `open_assumptions(state, item)` is non-empty, the template adds one such row, as F3 adds `target`
   only when a target keeps state.

**Gain / risk:**

- Change 1 removes the 14 real refusals and makes a yes from the check trustworthy at every stage. Risk: shape
  refusals print before gate refusals.
- Change 2 removes the cause of both the empty list and lint rows standing in for behaviour tests, so it is the
  quality gain. Risk: low. A `searched` criterion still gets its search command as a check row, which duty item 3
  covers.
- Change 3 should remove most of the 25 dry refusals. The gate is unchanged, so it still catches any that remain.

**Side test (for handed items 1 and 2): a Proof dry run on the item base.**

- Question: if ShipLoop runs each step's Proof on the item base at step-plan's check, does it reveal the vacuous,
  unloadable and broken Proofs before a whole implement loop is spent?
- Corpus: the saved plans that have a recoverable base, from ffea2956's replay set. The harness is
  `docs/experiments/question-record-20261031/sg1/replay_d6.py`, joined with `implement-sendbacks.jsonl`.
- Method: run each local Proof in a temporary copy of the base, with the test loop's timeout. Skip Proofs on a remote
  target or a target that keeps state, as the base run already does.
- Measure:
  - S1 exits 0 on the base;
  - the command cannot run (exit 126 or 127);
  - any other non-zero exit, with its last 20 lines saved. A person then classifies these as "behaviour missing" or
    "broken command".
- Predeclared rule:
  - If the dry run reveals at least 3 of the 6 handed faults that have a local base, and adds at most 10 s to the
    median check, print its results as a notice in the check answer. A notice tells the model and refuses nothing,
    because a behaviour-preserving step (a rename) passes on its base legitimately.
  - Only an exit of 126 or 127 may refuse.
  - Otherwise, drop the idea.
- Cost: about half a day extending `replay_d6.py`, no model calls, about 1 h of machine time.

**History respected:**

- 153160e1: criteria are confirmed only by commands ShipLoop runs;
- 5086baf6 and 8bf10c64: one evaluator for check and complete;
- 232689c5: the size caps are retired;
- 12151c49: the per-step Proof;
- ffea2956: the proof-order refusal. The side test measures what that rule cannot see, and does not reopen its
  rejected exemption for a step's own test path.

The test that pins the empty-list refusal (`test/shiploop-confirmation.test.py`) stays.

### test-spec: verdict side-test (low priority)

**Signals:** 87 runs and 136 packets. The 5 real refusals are all retired or fixed:

- the headline cap, removed by 232689c5;
- 3 disallowed outcomes, which the check has caught since 5086baf6;
- 1 Until Loop that completed with a send-back.

The 4 dry refusals include 2 from the TS1 gate, which fdec0f6e retired. 6 accepted send-backs. Median 0.7 min, 170 min
in total.

**Findings:**

- **Send-backs route correctly.** Of the 6:
  - 3 were Proofs needing unwritten tests; ffea2956 now catches these upstream;
  - 1 was one focused ID for three criteria (`B-ticket-assignment-s3`);
  - 1 was an ID-scheme problem;
  - 1 was a synthetic seed.
- **The `mock` sentence has no effect.** Item 6's mock sentence arrived in 3c904e64 (2026-10-29, F5). Since then, 63
  accepted results in 42 runs carried it, and none of their 205 rows has a `mock` field. Item 2 asks for a real
  boundary, and the HTTP and subprocess cases used one. Whether any case needed a double is unknown. Live: yes.
- **Criteria without a case.** 58 of 424 executed criteria (14%) finish with no case. They get a coverage notice,
  which is accepted by design (d9fefb11). The coverage ledger finds requirement coverage complete. No change.

**Proposal:** none until the side test runs.

**Side test:**

- Question: did any of the 205 rows need a dependency to be slow, to fail or to answer out of order?
- Corpus: those 63 results, selected as the packets that contain "the mock it runs against".
- Measure: a person classifies each row's oracle and red as needing a test double or not.
- Rule:
  - If at least 10% need a double and none names one, narrow item 6 to "a case whose oracle needs a dependency to be
    slow, fail or answer out of order names the mock that plays it". Then try it on a seeded slice of F5's
    stale-fetch battleship case.
  - If 2% or fewer need one, make no change.
- Cost: about an hour of reading, no model calls.

**History respected:** 3c904e64 (the owner's go on F5). E7's arm P stays parked, as the E7 journal decided. TS1 was
replaced by F3 (fdec0f6e).

### validate-existing: verdict no-change

**Signals:** 1 packet in 96 runs, because ShipLoop issues one only when an expectation does not match. 1 real refusal,
1 send-back, 1.3 min.

**Findings:**

- **Its only use routed correctly.** E1 claimed `works` for a selector that S2 builds. The model sent it back with
  route "steps" (`~/e2e-runs/20261030/p0-terra-ask-agent-55bfcd/.shiploop-runs/seed/run/results/nav-21f2b70ced1244cfbfa8fae757e984cd.md`).
- **The refusal was not about this duty.** "A complete validate-existing loop reports outcome done" is the shared
  Until Loop terminal rule (`shiploop_loops.check_terminal`): the model completed its loop and then sent the work
  back. It happened twice in 96 runs (the other was in test-spec). It belongs to the shared Until Loop block, not this
  duty.

**Proposal:** none.

**Gain / risk:** none.

**History respected:** ShipLoop runs the expectation checks itself and issues a packet only when one does not match.

## Group top picks

1. **step-plan: `check` runs `_canonical_result`, and the template's check row drops `criteria`.**
   - Gain: removes the 14 real refusals (15 of 61 runs since 2026-10-29) and makes a yes from the check reliable at
     every stage. It also ends lint rows "confirming" behaviour criteria.
   - Cost: about 20 lines, one fail-first test, a one-line template edit and the quick tier.
2. **step-plan: the `from` wording in duty item 6, plus a template row that appears only when an assumption is due.**
   - Gain: should remove most of the 25 dry refusals, which hit 22 of 96 runs.
   - Cost: one duty sentence, about 10 lines of template logic and one test.

The Proof dry-run side test comes next. It costs about half a day offline, and it decides the two items handed over
from D.
