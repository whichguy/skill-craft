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
| Test exits sent back | 2 of 5 (40.0%) | 12 of 327 (3.7%), corrected: see Corrections | same |
| Visits that ended in a send-back | five, 156.6 min (38% of the run) | | `evidence/visits-table.txt` |
| Repeated passing checks (a passing `check` followed by another `check`, the owner's `dupcheck.py`) | 7 pairs, 372 s (1.5% of the run) | 84 s across the retained corpus | `evidence/dupcheck.txt` |
| Refusals | 19 (16 `check`, 3 `complete`), none advanced the run | | `evidence/trial-trace.txt` |
| Observed tool time | 187.1 min (45%); the other 225.7 min (55%) is model time between calls (`Inferred:`: generation and reasoning; the host's 21 stream failures were each retried at once, see Corrections) | | `evidence/tool-ledger.txt` |
| Builder polling a directory for another party's file | about 46 calls over about 56 min (13%), a heuristic | | `evidence/tool-ledger.txt` |
| Model calls, context | 838 calls; peak 452,921 of 475,000; 3 compactions, each re-grounded within three calls (two through `shiploop next`, one from the packet) | | `review-export/facts.md` |
| Tokens | 175.9 M input (99.2% cached), 553,834 output (272,130 reasoning) | | the `end` event in `events.jsonl` |
| Packets | 65 prints: 61 first prints and 4 second prints, 3 of them the post-compaction re-grounding prints (different content) and 1 an identical reprint (203 KB, 11% of printed text) | | `evidence/trial-trace.txt` |

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
- The exporter's two readers of the verify records disagree (33 against 35 commands, listed under `unmeasured` in
  `review-export.json`). Resolved on 2026-11-14: a parser bug in the text reader, see Corrections.
- **The builder polled for the operator's evidence** (46 calls, about 56 min) and the operator's trace window became
  ready 1.3 s after a journey ended, so six calls could not qualify. A readiness marker and one wait would replace the
  polling; this costs model calls, not wall time, because the review takes as long as it takes.
- **An independent review passed code it had flagged and flagged again** (10:25, 11:05, 11:57). One instance, and the
  intended repeat caught it. A continuity record is an experiment, not a change (exploratory).

### 5. What held and must stay (firm)

No refusal became an advance; 19 refusals each named a real gap. Send-back recovered all five stops. Each compaction
re-grounded within three calls (two through `shiploop next`, one from the packet); the 855 s figure in `facts.md` runs
to the next accepted action, so it includes continued work. Per-item-plan `validate-existing` cost 26.3 s in all
(0.11% of the final 24,766 s of engine dwell; 0.12% was the interim snapshot's share), so the owner's suspected repeated-validation cost is not supported. ShipLoop ended BLOCKED
honestly, with evidence preserved, instead of passing on missing proof.

## Decisions

| # | Decision | Status |
| --- | --- | --- |
| 1 | Add the generic TAP count reader, with the real `security-tests8.tap` and malformed controls, and a replay over the retained check records that shows no earlier count changes | recommended; awaits the owner's tick. **2026-11-15: approved and built** ("Decision 1 built" below) |
| 2 | Record the four rare defects as known limits; ride the timeout-tail fix along with the next change in that file | recommended |
| 3 | The durable-wait capability | owner's decision; not recommended now |
| 4 | Hold cleanup after a non-pass outcome (reusing `keep_decision`'s machinery); record API headroom; add the plan's separate pre-journey readiness record | harness options, owner's tick |
| 5 | Repair the verify-record text reader (P9a): a `]` inside captured output ends the `runs` array early | recommended (harness, effort S); reproduced. **2026-11-15: approved and built** ("Decision 5 built" below) |
| 6 | The Codex plan's P4 (feasible implementation proofs) | declined as proposed: the class was studied on 2026-11-01 and left; only the unrun whole-delivery A/B of A2b remains registered |

## Corrections after the Codex Astra plan (2026-11-14, 17:20 PST)

These supersede statements above and in the first commit's message. Nothing above was deleted.

- **Test send-back rate.** The table said 17 of 327 earlier test exits (5.2%) were sent back. Five of the 17 were
  `test -> implement` moves, the next step of a multi-step item (headlines such as "Revalidated controller tests"), not
  send-backs. The count is 12 of 327 (3.7%); the implement figure (28 of 335, 8.4%) is unchanged. This trial's 40.0% is
  therefore 10.9 times the corpus rate, not 7.7. Fixed in `analysis/sendback_base.py`; `evidence/sendback-base.txt`
  regenerated. The first commit's message carries the old figure.
- **33 against 35 verify rows** (it said "not investigated"). `_RUN_ROWS` in
  [metrics.py](../../../test/shiploop_e2e/metrics.py) counts `[` and `]` without knowing about JSON strings, so a `]`
  inside a command's captured output ends the `runs` array early. On the six verify records it reads 33 rows against the
  JSON reader's 35, short in exactly two (9 against 10 and 5 against 6). All six records carry reuse provenance, so the 35
  are recorded results, not executions. Found by the Codex plan (P9a, its card E22); reproduced by
  `analysis/verify_readers.py` (`evidence/verify-readers.txt`). The reader's own comment expects an unreadable record to
  over-count; this one under-counts. **Superseded 2026-11-15:** this describes `_RUN_ROWS` before the fix in "Decision 5
  built" below, which scans JSON strings as strings; the trial now reads 35 through both readers.
- **Validation share.** 0.12% was against the interim snapshot (22,157 s); against the final 24,766 s it is 0.106%.
- **Stream retries.** The host's `stderr.txt` shows each stream disconnect retried at once ("1/5 in" about 200 ms), and
  several fall about 16 minutes past the hour (a connection lifetime, Inferred). They are not a large part of the 225.7 min.
- **Packet reprints.** Of the 4 second prints, 3 are the post-compaction re-grounding prints, with different content (the
  resumed-loop text), and 1 is identical: the harness's "reprints: 1".
- **Option g14-sb-classify is done:** 21 of the 28 implement send-backs are one class the owner studied on 2026-11-01.
  See P4 below.

## The Codex Astra improvement plan, considered (2026-11-14, 17:17 PST)

Source: "ShipLoop Improvement Plan from the Salesforce Grokbot Run" (ChatGPT page
`page_b4451bdbea8481919454c550052299f9`; local copy `operator/improvement-plan/improvement-plan.md`, which differs from the
download by 4 bytes) and the newer journal that links it (its entries 22 to 27 postdate the snapshot read above). Ten work
packages, 25 evidence cards, a validation program, and a statement that it is a plan, not an authorization. Its independent
review ran `gpt-6-astra` at **high** (`advisor-disposition.md`); the owner's rule of 2026-10-25 is max for plan and design
feedback.

Checked against the run and the code, and right: the harness files it cites are unchanged since the pin (only a new probe
file was added); `keep_decision` in [run.py](../../../test/shiploop_e2e/run.py) keeps an unfinished run only when the case
declares keep checks that passed, so it cannot hold under this quota block; the verify-reader parser bug (above); the three
plan refusals (trace lines 42, 87 and 103) and the stopped-loop causes; the two process listings (below).

| Package | Plan | Disposition here | Evidence |
| --- | --- | --- | --- |
| P1 hold and truthful terminal status | adopt the owner requirement, first | adopt for this run's hold; the lifecycle default is the owner's call, as the plan says. Reuse `keep_decision`'s machinery and consult the hold in every cleanup path (finally, regrade, recovery); report unsupported-phase checks as unexamined (`mismatch.md` lists them as failed) | `g14-hold-cleanup` |
| P2a readiness record | pilot | adopt the plan's design: a separate pre-journey readiness record. My "marker next to each request" would be circular, because the acceptance request needs the finished passing UI receipt | `g14-ready-marker` |
| P2b capacity wait | pilot, policy first | the owner's decision, not now; the plan agrees. Its neutral timeout wording also needs the route open (`remedy_open` reads counted records only) | `g14-timeout-tail` |
| P3 carry findings across reviews | pilot, observer first | hold. Over the 24 reviews: 21 actionable findings had a next review; 13 carried, 5 dropped after the code changed, 3 dropped after a new or edited test or script file resolved them. One finding went silent for 11 reviews on identical code and returned at review 14. That is one thread in 24 reviews, and the final exact-source review passed all five dimensions | `evidence/review-continuity.txt` |
| P4 feasible implementation proofs | pilot handoffs | decline as proposed. 21 of the 28 retained implement send-backs (19 runs, 6.3% of implement exits) are the class where the Proof is the test runner and the tests are not written yet. The owner studied it on 2026-11-01: a loop costs 2.0 min, every one recovered, no gate was precise enough, "leave it"; the proof-bullet rewording (A2b) was registered, run and reverted. The plan cites none of it. This trial's first stop is the same class | `evidence/sendback-reasons.txt`, `27c453fac4b518fdd99b09a773631f717a4d517c`, `68985caf4ee4eab732e0df725e88aca40817f2d4` |
| P5 countable native results | adopt | adopt, first among the ShipLoop changes. Nine of the 12 retained test send-backs are also "the recorded command cannot be read or classified" (four are an `rg` search recorded as a test), so the registration-time idea has more support than my TAP-only reading; start with the TAP reader, which has the pre-registered trigger | `g14-tap-reader` |
| P6 setup order | pilot | hold: 1 hit in 286 runs | `evidence/fold-census.txt` |
| P7 test and review calibration | pilot | hold: no measured outcome. An Apex `==` case note in the platform card is cheap and in the right place, but unmeasured | |
| P8a loop wording | adopt | hold: wording only, same outcome (owner, 2026-11-14); fold into the next change in that file | `g14-loop-wording` |
| P8b interruption fixtures | later | drop until a corrupted state is observed; the plan itself says it is not observed (owner, 2026-09-27) | |
| P9a verify parser | adopt | adopt (harness, effort S): reproduced | `evidence/verify-readers.txt` |
| P9b measurement and output | pilot | hold. Two `ps -axo` listings were 578,541 and 207,871 bytes, 14.0% of all tool-output bytes, and no ShipLoop packet or case prompt asked for them. Each ran 2 to 4 minutes after a compaction, so they look like re-orientation, not a cause (Inferred). None of the 2,489 retained runs ran a whole-machine listing, and among the 1,259 whose events I can read the largest ps, lsof or pgrep output was 86.5 KB | `evidence/big-outputs.txt`, `evidence/process-census.txt`, `evidence/process-output-sizes.txt` |
| P10 proof reuse | defer | agree | |

Where the plan is better than my review: the P2a design, the P1 hold design, and the root cause of the 33-against-35
disagreement. Where I would differ in shape: it puts evaluator work first, while the owner ranks generic ShipLoop first
(2026-09-26 and 2026-10-19); and its validation program (six paired trials in three families, Sol at medium, Astra at high)
is heavier than the measured gain of what is left after the holds.

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
- Read for the plan's P4: `27c453fac4b518fdd99b09a773631f717a4d517c` (the implement send-back class: a test-runner Proof
  on an empty base predicts it 5 of 5 against 0 of 15; a loop costs 2.0 min; the shipped gate refuses 0 of 28 plans; no
  candidate rule is clean; recommendation "leave it"), `c767968528e3db301da38bd4e821f923ac440563` (A2b, the reworded proof
  bullet) and `68985caf4ee4eab732e0df725e88aca40817f2d4` (its revert: the registered replay found the fault in 1 of 12 plans,
  too rare to judge; the follow-up named is a whole-delivery A/B, 6 a side, not run), `12151c49783a262595c83ff0ec92e0222379dfd3`
  (each step proven by its own command), and `docs/experiments/step-plan-round2-20261101/README.md`. Preserved: this review
  proposes no step-plan wording change for that class.

## Decision 1 built: the TAP count reader (2026-11-15)

The owner approved the implementation plan, which Astra (`gpt-6-astra`, max effort, read-only) reviewed first. Its
verdict was "ship with the listed fixes; Phase 2 is not ready", and each of its factual claims was checked against the
code, the TAP 14 specification and the retained runs before it was folded in. The hold, headroom and readiness items
(decision 4) stay gated on the owner's tick, with the corrected hold design listed in the plan.

**What the reader reads** (`_tap` in `skills/shiploop/scripts/shiploop_test_counts.py`):

- one flat TAP stream with exactly one `1..N` plan, placed before every test point or after them all;
- exactly N top-level points, numbered 1..N in order;
- a point whose TAP 14 directive is SKIP or TODO did not run, and its `not ok` is no failure. The directive starts at the
  first unescaped `#` after whitespace, takes any suffix (`# skipped`) and any case, and `\#` belongs to the title;
- YAML diagnostic blocks, comments, blank lines, `TAP version` and CRLF are skipped;
- `1..0` reads as zero tests;
- numberless or out-of-order points, an indented point or plan (nested subtests, and since the wrap-up of the review
  campaign below any other indent), a second plan or a mid-stream one, a point count the plan does not declare, and a
  column-0 `Bail out!` are not read (`None`, as before).

**Order and identity.** TAP is tried only when no runner's own summary matched, pytest's included, and before
pytest's exit-status-5 guess. `named` and `outcomes` judge a TAP point line by the same directive rule, so a count and
the IDs it shows agree. Every other runner's lines keep their skip marks.

| Evidence | Result | File |
| --- | --- | --- |
| The trial's real outputs, neutralized | `1..9` reads 9/0, `1..36` 36/0, `1..19` 19/3, all by `tap`; the wrapper's output reads 38/2 by `node` alone | `test/fixtures/shiploop-tap/` |
| New tests | 19 counter tests and 9 route tests through `test_loop.verify` and `step_proof` (floor, kept tail, check reuse, base floor, the pinned upgrade case). 25 of the 28 fail on the base reader; the 3 that pass on both are controls for behaviour that must not move | `evidence/tap-fail-first.txt` |
| Replay of every retained run | 429 run directories (1,608 copies excluded), 5,371 records, 8,925 rows, 4,434 unique count inputs; 877 records hold no runs and 653 rows have cut output. The positive control flips (the trial's Security row, `None` to 9). (a) no earlier count changed, and the registered exit-5 exception never occurs. (b) 75 inputs newly counted, all native TAP, in 5 run directories (this trial, one battleship control, three chess runs). (c) no verdict tightened: check `uncounted` to `passed` 1 (this trial's refusal); check-only and verify `passed-uncounted` to `passed` 4 each; 96 rows keep their verdict and now carry a count. (e) 32 newly counted command series, none with a later count below an earlier one, so no floor binds that did not before | `evidence/replay-counts.txt`, manifest `evidence/replay-manifest.txt` |

The planning prototype, run before the reader was written, gave the same (a), (b) and (e). Its (c) counted a judged row once across record forms, so it read 4 `passed-uncounted` to `passed` and 68 rows now counted, where the committed replay keeps each form (a check-only record and the verify record that copied it) and includes base rows: 4 + 4 and 96. The rows are the same, and nothing tightened in either count.

**Behaviour that moves.**

- A TAP command's accepted count becomes the count floor for later runs of it.
- A focused row with ids and `min_tests` is now held to that minimum (the trial's controller row ran 36 against 8).
- A `not ok` point at exit 0 fails the run for every row kind read as TAP (the masked-failure rule): a regression row
  without `min_tests`, a failing point that no listed ID names, and a `check` such as a linter that marks warnings
  `not ok` while it exits 0. No retained run hits any of these.
- `1..0` is refused as `no-tests` for every row kind (it was `uncounted` with `min_tests`, and passed without).
- A base run of a focused row with no ids reads `red` on TAP failures at exit 0.
- Harness evidence may be a TAP stream.

**Known limits, pinned by tests.**

- A point whose title starts with a duration still reads as a Go package line.
- A stream on stderr is read like any runner's summary there.
- A YAML diagnostic that names an ID shows it.
- A check passed under the earlier reader and completed on an unchanged tree is reused as recorded for that one
  completion.

**Not done, with the reason.**

- The registration-time readability check: measure the 9 retained send-backs' minutes first.
- The timeout-tail ride-along: `shiploop_test_loop.py` is unchanged.

`c700eb29aae866050bb6d83ab858de33f921e460`'s exit item ("one real `--result-format tap` output read by `outcomes`") is
now met by `apex-pass-36.tap`. The counting gap was a separate one, and this change closes it.

Status: firm for the retained inputs. How the native runner prints errors or a partial run that no retained record
shows is unknown; anything outside the contract stays unread. A live rerun is offered to the owner, not run: it deploys
to their org and needs API quota.

## Decision 5 built: the verify-record scan (2026-11-15)

`_RUN_ROWS` in `test/shiploop_e2e/metrics.py` now finds the `"runs": [` field and scans brackets only outside JSON
strings. An escaped character is consumed before a quote is read, so `\"` does not end a string and `\\` is one
backslash. It stays a text reader with no JSON fallback (`9b4bc8ae7cf171ddcbdd451a3e1f84dfb029a0e0`: it serves
baselines that must not depend on a schema). An array that never closes still counts its occurrences to the end of the
text.

The old scan erred both ways. A `]` in captured output ended the array early, which is this trial's 33 against 35. A
`[` in a string could carry the scan past the array: Astra's record `{"runs":[{"command":"["}],"commands":[...]}` read
2, and reads 1 now.

The `verifications` docstring now says `commands` counts recorded results. A record with `reused` provenance holds a
check's copied results, executed once by that check, whose record this reader does not read.

The plan's `copied_runs` field was dropped. The Run Review projection would discard it, and subtracting it would not
recover executions, so it had no consumer.

| Evidence | Result | File |
| --- | --- | --- |
| The trial, read with no write | both readers 35, no disagreement (was 33 against 35) | `evidence/replay-rows.txt` |
| Every retained verify record | 1,869 distinct records; 8 counted differently, all upward: this trial's two (9 to 10, 5 to 6) and six of the 2026-10-03 `v1161-battleship-luna` run (7 to 11 each). The JSON reader reads 1,828 of the records, and the new count agrees with it on all 1,828 | `evidence/replay-rows.txt` |
| Tests | one new test (a `]` in stdout, a `[` before the request, escaped quotes and backslash runs, a string value `"runs"`, an unterminated array). It fails on the base function (1 != 2); the existing exact-dict pins and the eleven-run agreement test are unchanged | `test/shiploop-e2e-analysis.test.py` |

The trial was neither regraded nor resumed. Its cleanup record is `ran: true, ok: false`, a regrade re-arms cleanup
against the owner's org, and the owner's hold is in force. Stored `metrics.json` files and evidence keep the values they
were written with; a regrade recomputes them.

## Review campaign on decisions 1 and 5 (2026-11-15)

The approved plan's Review Coverage block ran a review-converge campaign on the change. The ledger is
`review-converge-ledger.md` in this folder. The rounds:

| Round | Reviewer | Material | Minor | Test command |
| --- | --- | --- | --- | --- |
| 1 | a fresh read-only Claude subagent (652 s; resumed once after a session restart) | 0 | 7, parked | not required on a first clean round; the reviewer ran all 11 named suites green |
| 2 | Sol (`gpt-6.1-sol`, medium effort, read-only) | 0 | 0 new | PASS (terminal clean): 9 suites, 1,121 tests, exit 0 in 814 s, no artifacts left in the target paths |

Two clean rounds in a row completed the campaign. The completion report is a private artifact,
`https://claude.ai/artifact/VMtXvmfsG5eZxRYqvKwHTo`. Sol re-derived the replay from the frozen manifest with the
same figures, and its 242 JSON string and bracket controls of its own all passed against the verify scan.

The seven minor findings went into one wrap-up commit:

- **The change note** now names every new refusal, so readers of the changelog can see what may now be refused:
  - a `not ok` point at exit 0 fails any row read as TAP, a regression row without `min_tests` and a linter `check`
    that marks warnings `not ok` included;
  - `1..0` is `no-tests` for every row kind;
  - a check that straddles the release keeps its recorded result.
  The "Behaviour that moves" list above says the same.
- **An indented point or plan of any width makes a stream unread** (`_TAP_INDENTED`, was `_TAP_NESTED` with 4-space
  multiples only). A 2-space or tab-indented point used to be dropped silently, which undercounts: it could set a floor
  too low or refuse a focused row with leaf IDs. Controls: points indented two spaces, and a tab-indented point.
- **Deviation from the plan, kept and pinned.** `_skip_line` reads an indented TAP point (a node subtest) by the
  TAP 14 directive rule too, where the plan named only column-0 points. Node's own totals honour its subtests'
  directives, and no retained output reads differently (2,789 retained (output, ids) rows; review round 1). Test:
  `test_an_indented_tap_point_is_judged_by_the_same_directive_rule`.
- **Test gaps closed:**
  - inside a YAML block, a column-0 plan, a `Bail out!` and a point are skipped up to the block's `...`;
  - "the first `#` after whitespace decides" is now asserted through `named` too (`ok 1 TC-6 handles # of items #
    SKIP` shows TC-6; the old `_SKIP_LINE` hid it).
- **Two route tests substitute, as noted by the review:**
  - The base-floor test writes a synthetic base record rather than driving a base run. The base run calls the same
    `count`.
  - The reuse test exercises `_reused`, which takes the check's runs, rather than `take_check`, which copies records
    verbatim. Neither path has logic of its own for TAP.
- **The replay method is tighter.** `analysis/replay_counts.py` was rerun against 5b48232f0dd3295b545efc509f0760d8cd26a2ba,
  the commit before the change on this branch (the reader file is byte-identical to the one at 17cd64b4). The rerun's
  evidence is in `evidence/replay-counts.txt`:
  - it verifies the frozen manifest instead of overwriting it: all 429 run directories match;
  - each floor series now holds every counted row of its command, rows the old reader counted included, since a floor
    is the most any accepted run ran: still 0 falls in 32 series;
  - the header names each reader by the sha256 of its source;
  - the 24 rows whose stored output is cut and holds a TAP plan line are listed. On their stored tails, 20 read the
    same by `node` before and after, and 4 are unread by both; a live run's judge read the whole output;
  - every other figure is unchanged: (a) 0, (b) 75 by tap, (c) no verdict tightened, and the positive control flips.

  Fail-first now covers 29 new tests: 26 fail on the base reader, and the 3 that pass on both are controls
  (`evidence/tap-fail-first.txt`). `analysis/replay_rows.py` against the same base is unchanged: 8 records upward and
  1,828 of 1,828 agree (`evidence/replay-rows.txt`).
- **Stale text fixed:** the runner-table comment (mocha's tap reporter prints no `# cancelled`, so `_tap` reads it),
  the `_SKIP_LINE` comment (a TAP point is read by its own directive), the `analysis/verify_readers.py` docstring (a copy
  of the reader before the fix), and the Corrections bullet above, marked superseded.
- **Correction to the reader commit's message.** It frames the reuse limit as "a check passed under 1.34.3". Release
  1.35.0 has since shipped without this reader, so the limit covers a check passed under any release before the one
  that carries it. The change note says so. The commit is not rewritten, because the ledger and the round commits cite
  it by hash.

## Publication (2026-11-15)

Decisions 1 and 5 shipped as **shiploop 1.36.0 / skill-craft 2.40.0**:

- **Release commit:** `5057c18ab901927ce0026f58a741ff8239de6c5e` on main.
- **Push:** `scripts/release-push.py` with its four checks (`sync-plugin-views.sh --check`,
  `check-marketplace-packages.py`, `check-release-boundary.py --base`, `test/test-groups.test.py`), onto base `292f1dade64464b38f7cb846eb62c80c99f35fd3`.
- **Before the release:**
  - the quick tier on the merged tree (`--changed-from` pinned to main's 065dfadd) passed 89 of 90 suites in 1,248 s;
  - the 90th, `shiploop-e2e-brownfield-tickets`, failed once, when the base's `node --test` did not end within its limit
    at a machine load average of 61 to 76, with other sessions testing;
  - run alone it passed: 35 tests in 514 s.
- **Main moved three times during the release**, from other sessions' documentation, experiment and test-fixture commits.
  - The guarded push refused once, as designed, and one more move came during a re-cut.
  - Each time the unpublished release commit was dropped and re-cut on top of a fresh merge of main. The merges were
    `cce96ea358b3267f51f4ed6bb3b95527d5523931`, `025bb093453ffe68edc802ad5a978553668d79ef`, `96181a9b997d4ab9e1e7c2ad0578791d1ccffb2d` and `9d0baab4939e7e36e19d433e871c38a538ad12a6`.
  - The branch merged main instead of rebasing, because its commits are cited by hash in the review ledger and the round
    commits.
- **Hosts, read back rather than taken from exit codes:**
  - Claude Code 2.39.0 → 2.40.0 (restart to apply);
  - Codex 2.40.0 (its own auto-upgrade installed it first, and `codex plugin list` reads 2.40.0);
  - Grok 2.39.0 → 2.40.0;
  - Cursor not refreshed: its `whichguy` registration is pinned, so the move is a remove, an add and an Add click in its
    app, which falls to the owner.
- **CI:** the push run of the release commit was in progress when this was written; it is read afterwards.

## Unknowns

- The page after 15:38 PST. Dollars: the host reports none. The model time between calls is inferred, not measured.
- The polling figure is a heuristic. Tool time is a floor on busy time.
- Run12 is a warm start, so 108 against 413 minutes says nothing about 2.36.1 against 2.37.4.
- Whether a fold that dropped a row elsewhere was harmless is not visible to the census, only that the non-adjacent
  `check` shape never occurred.
- The class of an implement send-back is read from the model's own summary, by a recogniser that matches my reading of all
  28; the 2.0 min cost per loop is the R3 study's (one case, six loops), and this trial's own first stop cost 16.2 min,
  most of it the app build the stage did anyway. After 2026-11-05 only 18 implement exits are retained, so whether the
  class has changed since cannot be judged.
- The process-listing census reads the 1,259 runs whose host events carry tool outputs; the other 1,230 are counted as
  unread, not zero. The strict pattern, a command that starts `ps -axo`, `ps aux`, `ps -ef` or `ps -e`, is zero in all
  2,489 files, and an earlier run of the census with a failing `xargs` gave truncated counts that are not used.
- Why the builder ran the two listings is not recorded.

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
python3 -I analysis/sendback_reasons.py /tmp/trace-files.txt
python3 -I analysis/sendback_class_by_date.py /tmp/trace-files.txt
python3 -I analysis/verify_readers.py $RUN/.shiploop-runs/work-20261114-161603-238276/run
python3 -I analysis/big_outputs.py $RUN
python3 -I analysis/review_continuity.py $RUN/platform/grok-chat-quality
python3 -I analysis/process_output_sizes.py
bash analysis/process_census.sh $RUN
# Decision 1 (2026-11-15), from a checkout of the change; BASE is the commit before it:
python3 -I analysis/replay_counts.py --repo <checkout> --base 5b48232f0dd3295b545efc509f0760d8cd26a2ba \
  --manifest evidence/replay-manifest.txt ~/e2e-runs ~/e2e-runs-sp /Users/Shared/Codex/shiploop-e2e
python3 -I analysis/tap_fail_first.py --repo <checkout> --base 5b48232f0dd3295b545efc509f0760d8cd26a2ba
python3 -I analysis/replay_rows.py --repo <checkout> --base 5b48232f0dd3295b545efc509f0760d8cd26a2ba \
  ~/e2e-runs ~/e2e-runs-sp /Users/Shared/Codex/shiploop-e2e
```
