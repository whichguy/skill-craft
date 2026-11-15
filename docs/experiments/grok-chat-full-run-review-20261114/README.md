# Review of the 2026-11-14 independent Salesforce Grok chat trial (ShipLoop 1.34.3 on Codex)

**Consumer.** The owner, deciding what to change in ShipLoop from this run; a later session checking whether a
candidate was already measured; the Run Review page (the review file is
[codex-gpt-6.1-sol-2.37.4-grok-chat-salesforce-full-20261114.review.json](../../../test/shiploop_e2e/evidence/codex-gpt-6.1-sol-2.37.4-grok-chat-salesforce-full-20261114.review.json)).

**Status of this document.** Written 2026-11-14 16:00 PST. Nothing was changed in ShipLoop, the harness, the paused
operator or the preserved org state. Findings carry a status: *firm* (verified in source, trace and records),
*interim* (an inference, marked `Inferred:`), *exploratory* (a hypothesis only).

## Question

Does this run show anything to repair, fix or improve in ShipLoop, as opposed to the case or the test apparatus?

## What was read, and what was not

- The page the owner pointed at is a ChatGPT Space page, "ShipLoop Salesforce Grokbot Observation Journal"
  (`page_99a1e5c0580481919e9fb67e50d0bc4d`). It needs a ChatGPT login and the built-in browser was not signed in, so I
  read the operator's saved snapshot of it
  (`/Users/Shared/Codex/shiploop-e2e/salesforce-grokbot-independent-20261114T161019Z/operator/observation-journal/page-snapshot-20261114-review-hold.json`,
  taken 15:38 PST; the page's own `updated_at` is 15:33:50 PST, sequence 12). Edits after 15:38 are unseen.
- The run's own records under `/Users/Shared/Codex/shiploop-e2e/salesforce-grokbot-independent-20261114T161019Z/run/`
  (`trace.jsonl`, `events.jsonl`, `timeline.jsonl`, `review-export/`, `inbox/`, `results/`, `tests/`, `notes/`,
  `platform/sf-calls.jsonl`), the operator's three read-only reviews, and 742 retained traces from earlier runs in
  `~/e2e-runs` and `~/e2e-runs-sp` (376 of them hold ShipLoop commands since `check` shipped on 2026-10-29).
- The trial ran harness commit `3f8ebf5a30ea8c70a6e8118d66b97d1d7951f399`. No commit since touches `skills/shiploop`,
  `skills/improve` or `changes/shiploop`; two touch `test/shiploop_e2e` (a probe registration,
  `57dfccdb250e4342565587f13f802a57eb62eaa5`, and an unregistered Grok chat scenario packet,
  `71fa298e44db73f6afa46217377ba0ea850de916`), so this checkout's ShipLoop is the code the trial ran and every symbol
  cited below reads as the trial saw it. Neither commit touches the apparatus findings below.
- Not done: I did not re-audit each of the 52 `done` callbacks (the operator's Astra/high Until review did, and found no
  silent advance); I read all 19 refusals and the 5 stopped loops.

## The run in numbers

| What | This trial | Compared with | Source |
| --- | --- | --- | --- |
| Outcome | BLOCKED at system-test-author after 412.8 min (6.9 h); 51 accepted actions. Headline: "Application checks passed; current operator live-acceptance receipt remains missing"; the operator's evidence collection hit `TotalRequests Limit exceeded` from 14:48 PST | Run12 of the same case, 2026-11-12: done in 108.3 min, but a warm start, so not comparable | `evidence/visits-table.txt`; [Run12 review](../../../test/shiploop_e2e/evidence/codex-gpt-6.1-sol-2.36.1-grok-chat-salesforce-full-20261112.review.json) |
| ShipLoop `check` time | 99.6 min (24% of the run); 15 of 50 checks took 100 s or more | median 0.1 min per run, p95 1.1, max 8.0 over 331 runs; 2 of 2,057 checks took 100 s or more | `evidence/check-baseline.txt`, `evidence/trial-trace.txt` |
| Implement exits sent back | 3 of 8 (37.5%) | 28 of 335 (8.4%) over 260 runs | `evidence/sendback-base.txt` |
| Test exits sent back | 2 of 5 (40.0%) | 17 of 327 (5.2%) | same |
| Visits that ended in a send-back | five, 156.6 min (38% of the run) | | `evidence/visits-table.txt` |
| Repeated passing checks (a passing `check` followed by another `check`, the owner's `dupcheck.py`) | 7 pairs, 372 s (1.5% of the run) | 84 s across the retained corpus | `evidence/dupcheck.txt` |
| Refusals | 19 (16 `check`, 3 `complete`), none advanced the run | | `evidence/trial-trace.txt` |
| Observed tool time | 187.1 min (45%); the other 225.7 min (55%) is model time between calls, which includes the host's stream retries (`Inferred:`) | | `evidence/tool-ledger.txt` |
| Builder polling a directory for another party's file | about 46 calls over about 56 min (13%), a heuristic | | `evidence/tool-ledger.txt` |
| Model calls, context | 838 calls; peak 452,921 of 475,000; 3 compactions, each re-grounded within three calls (two through `shiploop next`, one from the packet) | | `review-export/facts.md` |
| Tokens | 175.9 M input (99.2% cached), 553,834 output (272,130 reasoning) | | the `end` event in `events.jsonl` |
| Packets | 65 prints, 4 of them reprints (203 KB, 11% of printed text) | | `evidence/trial-trace.txt` |

Terms. A *check* is the ShipLoop command that runs a stage's recorded commands without finishing the stage. A
*send-back* is a stage reporting that its plan cannot be satisfied and returning to planning. A *fold* is ShipLoop
merging recorded command rows that are the same command into one. *TAP* is a plain test-result format: a `1..9` plan
line and one `ok N name` or `not ok N name` line per test. A *mutant* is a small deliberate break of product code used
to see whether the tests catch it.

## Findings

### 1. The test counter cannot read plain TAP, and ShipLoop's own platform card steers the model to it (firm; cost interim)

- At 19:14:03Z a `check` took 178 s to say the regression command "exited 0, but ShipLoop could not read how many tests
  it ran" (trace line 100). The command was `sf apex run test --class-names SLGrokChatSecurityTest ... --result-format
  tap`, which the card tells the model to use. Its real output (`notes/security-tests8.tap`) is a `1..9` plan line and
  nine `ok N Class.method` lines.
- The reader table in [shiploop_test_counts.py](../../../skills/shiploop/scripts/shiploop_test_counts.py) (`READERS`)
  covers jest, vitest, unittest, mocha, cargo, go, dotnet, node and pytest. It has no TAP reader, so only a node-style
  `# tests N` summary counts. The card
  ([salesforce.md](../../../skills/shiploop/references/platforms/salesforce.md), the reporter paragraph) covers the
  per-test mark a focused command needs, not the count a regression row or `min_tests` floor needs.
- The builder's recovery was a send-back at the test stage (34.3 min visit), a replan, then an 89-line wrapper,
  `scripts/run_apex_tests.py`, whose only job is to re-print the native counts as `# tests N`, `# pass N`, `# fail N`.
  The passing check record shows the Apex rows counted by the `node` reader (`counts.runners: ["node"]`).
- The builder kept the count floor. A regression row with no ids or `min_tests` passes uncounted
  (`c38f6887abfcc4a51fab616fddc7c3714d3f41e1`), so it could have dropped `min_tests`; it wrote the wrapper instead
  (its receipt says "no countfloor waiver", S-9).
- Refusal to wrapper in place: 19:14Z to 19:46Z, about 32 min (8% of the run). `Inferred:` most of it was avoidable.
- This was left open on purpose. Commit `c700eb29aae866050bb6d83ab858de33f921e460` says the real-org check of the card
  was not run and "if it fails, D-25's adapter code opens as its own plan"; the plan
  ([aggregate-plan-final.md](../shiploop-eff-evidence-20261017/plan/aggregate-plan-final.md), D-25) says adapter code
  "only if the final run still hits 'unread' with the card in place". This run followed the card and hit the count form
  of it.
- Prevalence: 10 earlier runs list `sf apex run test`; one used `--result-format tap` on any row and none on a
  regression row (`evidence/apex-census.txt`), so the route was untried until now.
- **Recommendation: fix, generically.** Add a TAP reader that only runs when no other reader matched: a top-level
  `1..N` plan line and exactly N top-level result lines, the existing skip marks honoured, anything else unreadable as
  today. Node's TAP carries `# tests N`, so it never double counts, and the Go reader must not read `ok N name` lines
  (`c38f6887abfcc4a51fab616fddc7c3714d3f41e1` found TAP double-counted through it and says an unreadable summary is
  refused, not guessed; a declared plan checked against its rows is neither). The card stays; no stack word enters the
  engine.

### 2. Four ShipLoop shortcomings that no earlier run hit (firm): record, do not build

| Shortcoming | Where | In this trial | In earlier runs | Decision |
| --- | --- | --- | --- | --- |
| A repeated command row is merged silently, whatever sits between the two rows | `normalise_commands` and `_fold` in [shiploop_test_loop.py](../../../skills/shiploop/scripts/shiploop_test_loop.py); commit `a3b2f975487ebb7ede6987628c4a931941f9b057` made the fold deliberate after the chess run ran one org suite three or four times per stage (about 104 s of org time per complete), and does not weigh a repeat with other rows between | system-test-author submitted 10 rows; rows 1 and 8 were the same `check` deploy with six other rows between; the accepted packet listed 9 and said nothing. The builder noticed, sent back (1.1 min) and redid the stage (13.8 min), joining deploy and the UI check with `&&`. About 15 min. | 0 of 285 other runs (661 submissions). 148 rows were folded in 83 runs, none a repeated `check` row with other rows between (`evidence/fold-census.txt`) | known limit |
| A timed-out `check` gets no route out: it is told "Fix the code" under its own "no verdict about the product" line, and ShipLoop's own record does not open the remedy | `verify` in the same file: for a non-counting `check` it sets `attempts` and never calls `_unavailable_sentence`, the neutral text that says "report blocked only for ... an outside dependency". `Inferred:` from the code, `remedy_open` reads counted records only, and a non-counting check writes `counted: false` with no attempt number, so the route opens only after a counted `done` that also times out. Commit `6a59012cde0f7e752ee1163ee7290486c0bc4d1a` fixed that dead end for counted attempts and says to test the route, not the words. | trace lines 124 and 149; the builder kept the incomplete attempt, no harm seen | 0 timeouts in 376 runs (`evidence/refusal-census.txt`) | known limit; if the file is open for another change, fix the words and the route together |
| Mixed-item survivors need dispositions by design, but the refusal does not name the commands left out, and test classes count as product | [shiploop_mutation.py](../../../skills/shiploop/scripts/shiploop_mutation.py): the record carries an advisory ("the remote commands this check left out may be the only tests that reach the mutated code") that the refusal does not show. The requirement is designed: `3f8a0a7b1f9e0d022cf20946664ae4b4b009d19b` made survivors of an item whose remote tests were left out need `not-exercisable` dispositions, and `7a194ae4fffbe34ee605e9e12075354a30f46420` fixed the same 0-of-8 symptom for items whose focused commands are all remote | trace line 120: 8 of 8 survived, only the node view command ran, 2 of the 8 sat in `*Test.cls` files; the builder wrote 8 dispositions (6 `not-exercisable`, the 2 test classes `out-of-scope`), so the existing route handled them | the check fires often (145 refusals in 120 of 376 runs); mutants in test-looking files: 6 of 352, in one run. Telling a test class apart needs stack naming the catalog deliberately lacks. | known limit |
| "a second start resets the loop" | `INVOKE_LINE` and `RESUME_LINE` in [shiploop_loops.py](../../../skills/shiploop/scripts/shiploop_loops.py); `_check_start_receipt` in the Until runtime refuses and changes nothing | both texts send the model to `next_argv` | not measured | no change: same outcome |

Why not build: the owner's rules are to fix only what breaks or misleads a normal run (owner, 2026-09-27, KISS and
YAGNI) and to change nothing without a measured difference in outcome (owner, 2026-11-14). The census is the "did a
real run hit it" test. Re-run `analysis/fold_census.py` and `analysis/refusal_census.py` after
the next batch of runs; a second hit changes the decision.

### 3. This run sits outside ShipLoop's usual regime (firm)

- `check` took 99.6 min, more than any of the 331 earlier runs and 12 times the earlier maximum of 8.0 min. The recorded commands ran 2 to
  12 minutes each (deploy, a browser journey against a live provider, a wait for the operator's independent review),
  chained with `&&`, and every failed check re-ran every command (`reused=None` in the check record). The earlier
  close-out study found repeated checks cost 0.1% of inner-stage time
  ([README](../closeout-one-command-20261114/README.md)); that holds for typical runs and not for this one. Only this
  case type produces such checks. Yet even here repeated passing checks, the owner's own measure
  (`dupcheck.py`), cost 372 s in 7 pairs (1.5% of the run) against 84 s over the whole retained corpus
  (`evidence/dupcheck.txt`), so re-running after a pass is not the cost; first runs and failed or timed-out runs are.
  The close-out entry (`a41cb125800f731e0eca2f4a51de4f3d03810dbd`) said the test stage, where a repeated check costs
  most, had no live scenario; this run is that measurement, and it does not support changing whole-record reuse.
- Five visits ended in a send-back (156.6 min, 38%): three at implement (16.2 min: the plan's proof called a quality
  check that needs tests the implement stage may not write; 47.8 and 5.7 min: the proof's live provider journey came
  back incomplete after a prompt and budget repair and then timed out), two at test (52.6 min: required concurrency coverage had no
  execution route in the plan; 34.3 min: finding 1). The send-back route worked every time and the visits include the
  real build, so this is not waste. It is the plan accepting proofs the stage could not satisfy.
- **Needs the owner:** (a) whether ShipLoop should support a check that waits on an outside party longer than the
  600-second command guard, by a durable wait the script owns. That is a new capability, it touches a limit, and the
  quota exhaustion that blocked this run would not be cured by a short wait. The owner asked (2026-10-28) to be
  consulted before any limit is added, lowered or swapped, so this one is theirs to decide. (b) Whether to classify the 45 send-backs in the retained corpus by reason before any plan-time check of an
  implementation proof is proposed.

### 4. Test apparatus, not ShipLoop (interim)

- **Cleanup needs the API it ran out of, and ran before the owner's review point.** The harness's default cleanup after
  the blocked exit failed its identity query with `TotalRequests Limit exceeded`, leaving the deployed app and trace
  resources; the owner then paused the operator (`owner-review-hold.json`). Hold cleanup after any non-pass outcome
  until the owner confirms; keep an API reserve for cleanup.
- **Quota use is not accounted.** The builder's guarded ledger shows 203 `sf` calls from 08:14 to 14:46 PST (59 deploys,
  56 Apex test runs); the error began at 14:48:09 PST. The operator, the UI helper and any other client are not
  counted, so the cause is unmeasured. Record `DailyApiRequests` remaining at the start, at checkpoints and at the end.
- **Teardown stopped the owner's live viewer.** The harness stops every listener whose working directory or command line
  lies under the case folder ([listeners.py](../../../test/shiploop_e2e/listeners.py), `reap`); the operator's viewer,
  started at 16:17:08Z with the run directory in its command line, was ended by SIGTERM and restored afterwards. Start an
  observer's listener from outside the folder, or let the operator name listeners to keep.
- Also seen: the exporter's two readers of the verify records disagree (33 against 35 commands, listed under
  `unmeasured` in `review-export.json`), so command counts in `facts.md` are a floor. Not investigated.
- **The builder polled for the operator's evidence** (46 calls, about 56 min) and the operator's trace window became
  ready 1.3 s after a journey ended, so six calls could not qualify. A readiness marker and one wait would replace the
  polling; this costs model calls, not wall time, because the review takes as long as it takes.
- **An independent review passed code it had flagged and flagged again** (10:25, 11:05, 11:57). One instance, and the
  intended repeat caught it. A continuity record is an experiment, not a change (exploratory).

### 5. What held and must stay (firm)

No refusal became an advance; 19 refusals each named a real gap. Send-back recovered all five stops. Each compaction
re-grounded within three calls (two through `shiploop next`, one from the packet); the 855 s figure in `facts.md` runs
to the next accepted action, so it includes continued work. Per-item-plan `validate-existing` cost 26.3 s in all
(0.12% of the run), so the owner's suspected repeated-validation cost is not supported. ShipLoop ended BLOCKED
honestly, with evidence preserved, instead of passing on missing proof.

## Decisions

| # | Decision | Status |
| --- | --- | --- |
| 1 | Add the generic TAP count reader, with the real `security-tests8.tap` and malformed controls, and a replay over the retained check records that shows no earlier count changes | recommended; awaits the owner's tick |
| 2 | Record the four rare defects as known limits; ride the timeout-tail fix along with the next change in that file | recommended |
| 3 | The durable-wait capability | owner's decision; not recommended now |
| 4 | Hold cleanup after a non-pass outcome; record API headroom; add a readiness marker | harness options, owner's tick |

## Prior decisions read and preserved

Each full message was read before this review was written down.

- `a3b2f975487ebb7ede6987628c4a931941f9b057` (the fold, decision D5): repeats merge so a suite runs once; only a
  passing check-only record is reused at `complete`. Preserved: this review does not propose per-command reuse, and its
  fold option only names a refusal for the one shape that never recurred.
- `6a59012cde0f7e752ee1163ee7290486c0bc4d1a` (the could-not-run route): test the route, not the words. Applied to the
  timeout option, whose test submits the named route through the navigator.
- `3f8a0a7b1f9e0d022cf20946664ae4b4b009d19b` and `7a194ae4fffbe34ee605e9e12075354a30f46420` (mutation dispositions,
  remote skip): the 0-of-8 survivors and the `not-exercisable` route are designed, so the mutation item is recorded, not
  changed.
- `c38f6887abfcc4a51fab616fddc7c3714d3f41e1` (the node reader): TAP double counted through the Go reader; an unreadable
  summary is refused, not guessed. Both are controls in the TAP option's test.
- `c700eb29aae866050bb6d83ab858de33f921e460` (the Salesforce card): left the real-org reporter check open and
  pre-registered D-25. This run is that check.
- `a41cb125800f731e0eca2f4a51de4f3d03810dbd` and `98fe611efc6ae30f0cd22c254d8fef79ef8f2bbf` (the close-out rounds):
  an entry goes after the ShipLoop commit it vouches for, because the release preflight reads commit order, and the
  test stage had no live scenario for repeated checks. So this commit does not touch `test/shiploop_e2e/LEARNINGS.md`,
  and its `dupcheck.py` numbers are the missing measurement.
- `a270e5bf0a3c12641ef27cfcfdb70d647837957a` (Run12): a warm start with inherited application and tests, so its 108
  minutes are not a baseline for a cold build, and a failed trial is preserved beside any recovery.
- `71fa298e44db73f6afa46217377ba0ea850de916` (the Grok chat scenario packet, landed while this was written): a separate,
  unregistered product-outcome prompt; it overlaps none of the findings here.

## Unknowns

- The page after 15:38 PST. Dollars: the host reports none. The model time between calls is inferred, not measured.
- The polling figure is a heuristic. Tool time is a floor on busy time.
- Run12 is a warm start, so 108 against 413 minutes says nothing about 2.36.1 against 2.37.4.
- Whether a fold that dropped a row elsewhere was harmless is not visible to the census, only that the non-adjacent
  `check` shape never occurred.

## Reproduce

```sh
find ~/e2e-runs ~/e2e-runs-sp -name trace.jsonl > /tmp/trace-files.txt
RUN=/Users/Shared/Codex/shiploop-e2e/salesforce-grokbot-independent-20261114T161019Z/run
TRACE=$RUN/.shiploop-runs/work-20261114-161603-238276/run/trace.jsonl
python3 -I analysis/visits_table.py $RUN/review-export/review-export.json
python3 -I analysis/trial_trace.py $TRACE
python3 -I analysis/tool_ledger.py $RUN
python3 -I analysis/refusal_census.py /tmp/trace-files.txt
python3 -I analysis/fold_census.py /tmp/trace-files.txt
python3 -I analysis/apex_census.py /tmp/trace-files.txt
python3 -I analysis/check_baseline.py /tmp/trace-files.txt
python3 -I analysis/sendback_base.py /tmp/trace-files.txt
```
