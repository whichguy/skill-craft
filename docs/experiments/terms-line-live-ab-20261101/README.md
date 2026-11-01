# Live A/B of the terms-and-references line on the Codex harness (2026-11-01)

Consumer: the owner, who answered "Yes test all this then Commit and merge everything to main and publish" on 2026-11-01 to the
question "Run the live A/B and make the terms-line change?"; and the session that cuts the release, which reads the Rules and the
Results below to see whether the change cleared them. Follows the confirmation
([../terms-line-confirmation-20261031/README.md](../terms-line-confirmation-20261031/README.md)) and the question-bank study
([../../shiploop-intake-question-bank-journal.md](../../shiploop-intake-question-bank-journal.md), §8 decision D2).

This file was written and committed **before** any scored run. The rules are never edited; results are appended under "Results".

## What is under test

Commit `60dc376881d397d770874af16c8a6a8ed60956b2` (`feat(shiploop): intake settles the request's terms and references by looking ...`), one commit above
origin/main `e13af240100c066489e83c028d97339845402b55`: intake duty 9 gains the catalog line K12 (terms and references) and the
look-it-up-first sentence, and the ledger's shape check names K1-K12 (so a ledger that stops at K11 is refused and corrected in the
same callback). The wording is QB5's with two changes, because a real packet lists no skills: "the installed skills listed above"
became "the skills and commands your host lists", and "the installed skills" in the K12 line became "the skills your host lists".
This round is the first time the shipped wording runs, and it runs in the real packet with the host's own skill list.

Checks that came first, on this tree: `test/shiploop-callback-contract.test.py` 96 tests OK; the quick and prompt tiers
(`bash test/run-all.sh --group quick --group prompt --changed-from e13af240100c066489e83c028d97339845402b55 --jobs 8`) 38 suites OK
in 402 s, none failed.

Evidence behind the change (all exercise-level, intake only, Codex Terra 6.1 xhigh, Opus judge): on three requests and three
repositories the first study had not seen, items answered right rose from 0.52 to 0.67 (exact one-sided p 0.0083, ahead in every
request: +0.186, +0.186, +0.092) for 8% more output tokens; installed skills 0.20 to 0.80. One of QB5's four registered rules failed:
silent assertions fell from 0.67 to 0.20 per output but at p 0.115 (bar 0.05). The owner's "Yes" of 2026-11-01 is the explicit go over
that miss.

## Question

Does a real ShipLoop run on the Codex harness with the change behave as well as one on current main: the K12 ledger accepted by the
gate with no extra refusals, the same deliveries, comparable cost, and no stop for a person?

## Design

- **Subject.** Codex `gpt-6.1-terra` at `high`, all tools, hooks on (the harness default), `--source checkout`. High, not xhigh, because
  the last three ShipLoop rounds on this harness (`45f9752eee7d4fe3450b9ac88843cc1da0fbb980`, the stage-prompt round, the 2026-11-01
  ticket baseline) ran at high and this keeps their baselines comparable; the intake studies ran at xhigh and say so. Both arms use the
  same setting, so nothing here changes a default.
- **Arms.** A = ShipLoop at origin/main `e13af240100c066489e83c028d97339845402b55` (release skill-craft 2.27.2 / ShipLoop 1.26.2), run
  from its own detached worktree. B = `60dc376881d397d770874af16c8a6a8ed60956b2`, run from its own detached worktree; B differs from A
  in five files (the three skill files, the ledger test, the change note). Each run starts `run.py` from its arm's checkout, so
  `--source checkout` builds that arm. `origin/main` moved twice while this was prepared (a docs commit, then the Python 3.9 floor
  release, whose 46 files include the hook scripts that run in these tests); the arms were first set on the older base, never ran there,
  and were re-taken on the release before any scored run. The harness's `--preflight-only` prints a marketplace line that refuses a
  checkout with unpublished commits; that gate belongs to `--source marketplace` runs (`run.py`, `version_gate`), and the first launch
  will show whether a checkout run is affected.
- **Cases.** `hello` (greenfield smoke), `user-listing` (brownfield, fixture node-base) and `ticket-assignment` (brownfield, fixture
  node-tickets). 2 runs per arm per case: 12 runs. Three lanes in parallel, one per case (their declared ports differ: none, 3000, 4180),
  each lane running A1, B1, A2, B2 in turn so that the arms share the hours (`lane.sh`). Output `~/e2e-runs-tl/20261101/<arm>-<case>-s<n>`.
- **Measures** (`e2e_ab.py`, from each run's `result.json`, `metrics.json`, `trace.jsonl` and `state.md`): the harness verdict
  (`pass`), minutes, processed tokens, refused callbacks (all stages; at intake, those whose text names `question_categories`), the intake
  ledger as stored and as submitted, the K12 row and the questions filed under K12, routes, the intake stage's seconds and tool calls,
  `asked_user`, and the run's final status.

## Rules (decided now, over the six runs of each arm)

1. **L1, it works live:** at least 5 of the 6 B runs store an intake ledger that names each of K1-K12 once, and at most 1 of the 6 B runs
   has an intake refusal whose text names `question_categories`.
2. **L2, no harm to the delivery:** B passes the harness verdict in at least 5 of 6 runs and in at least as many runs as A minus one.
3. **L3, no refusal cost:** B's mean refused callbacks per run (all stages) is at most A's plus 1.5.
4. **L4, cost:** B's mean processed tokens per run is at most 1.25 times A's.
5. **L5, no stop for a person:** no B run ends blocked, and B's runs ask a person (`asked_user`) no more often than A's.

If L1 to L5 all hold, the change ships: it merges to main and the next release carries it. If any rule fails, the change stays on its
branch (unaccepted candidate code stays out of `main`), the failure is reported with its run, and only the owner decides what follows. A
run that fails for a host or account reason (credit limit, network, a killed process) is run once more and both attempts are recorded;
no other run is repeated or replaced. A result is not edited after the fact.

**Descriptive, no rule:** minutes, the intake stage's seconds and tool calls, intake questions per run, how often K12 applies and what the
K12 questions say, the route mix, send-backs.

## What this cannot settle

- **The benefit.** All three requests are fully specified, so K12 will mostly find nothing to settle. The benefit is the confirmation's
  (exercise level, three requests); this round checks that the shipped wording runs live without harm. A loosely worded live request is
  not tested here.
- One subject and effort, 6 runs per arm, three cases; run-to-run time varies by tens of percent in earlier rounds, so no time effect is
  claimed. Actual served model identity and dollar cost are not observed.
- The `research` route (a web search) is not exercised unless a run chooses it; these requests name no outside term.

## Reproduce

```
bash lane.sh CASE <checkout of arm A> <checkout of arm B> ~/e2e-runs-tl/20261101      # once per case
python3 e2e_ab.py                                                                       # reads the runs, applies L1-L5, writes scores.json
```

## Round 1 as read, and why a replication (R2) is registered (written after the 11 round-1 runs that finished were read, before any R2 run)

Round 1 is the 12-run design above. Eleven runs finished; the twelfth (B, ticket-assignment, run 2) was refused by the harness at
launch before any model started, because a listener an earlier case of another session left was still bound, and a retry is now
queued behind another session's runs that hold the machine-wide lease on port 4180 (the registered one-rerun contingency; both attempts
are recorded). Reading the eleven with the reader, the five rules L1 to L5 all hold even if the missing run counts as a total failure
(L1 and L2 need 5 of 6 and B has 5 of 5; L3 and L4 would need that run to refuse 9 callbacks or use 149 million tokens to fail).

One thing the rules did not look at stands out. **Send-backs** (a stage returning the item to step-plan) were registered as descriptive:
A had **0 of 6** runs with one, B had **4 of 5** (hello s1 and s2 at test-spec: a step plan whose focused test command listed no test
ID; ticket-assignment s1 and user-listing s2 at implement: a criterion that needs tests the test stage writes later). Exact one-sided
p of that split, if both arms had one rate: 0.015. Earlier rounds on the same subject and effort, with the proof-order refusal in the
product, had 2 runs with a send-back in 18 (the stage-prompt round's hello r1 and the ledger round's B ticket-assignment s3), about 11%.
There is no mechanism I can name by which intake's ledger changes what step-plan writes five stages later, and the four are three
different faults across three cases, so chance is the likelier reading; but this was found after the rules were set, the rules cannot
see it, and a prompt change that adds planning loops is a cost this round must not wave through.

**R2, the replication.** New runs only (the round-1 runs are not reused for the decision): case `hello`, which needs no port lease,
4 more runs per arm (samples s3 to s6; A and B each in two lanes of two, all four lanes started together, so both arms share the
hours), the same command, subject, effort, arms and reader as round 1 (`lane-r2.sh`).

- **R2-1:** the excess **replicates** if, among the 8 new runs, B has at least 2 more runs with a send-back than A (counting a run once,
  whatever its stage). Under one rate of 15% in both arms that happens about 6% of the time; against a rate of 80% in B and 10% in A it
  happens about 90% of the time (my arithmetic, 4 runs a side).
- **Decision.** R2-1 replicates: the change does not ship; the finding goes to the owner with the runs, and nothing under `skills/` is
  published. R2-1 does not replicate: the change ships under L1 to L5, and the round-1 imbalance is recorded as unexplained and
  compatible with chance, with its numbers.
- **Report either way:** all send-backs by stage and arm, pooled over round 1 and R2 (descriptive only: round 1 was chosen for being
  odd, so a pooled test would be biased toward finding an effect and is not used), and the pass, refusal and token figures of R2.

R2 cannot say whether the brownfield implement send-backs (two of the four) repeat, because the ticket case is behind another session's
lease and user-listing would take an hour on its own port; it cannot tell a small effect from none (4 runs a side); and it is a second
look at an outcome chosen after the first look.

## Results (19 runs of Codex gpt-6.1-terra at high; every run passed; `scores.json`, `results-tables.md`)

The reader (`e2e_ab.py`) gained, after the registration commits, the `plugin_sha256` field, the send-back columns, the markdown tables
and `replication()`, which applies R2-1 as registered in `9c2bf16a0264edc7d8b682ded7dc9a8292e8a838`; no rule changed. Runs:
`~/e2e-runs-tl/20261101/` (outside git, like the earlier rounds); the harness rows are in `test/shiploop_e2e/baselines.jsonl`.
**Identity.** All 10 arm A runs loaded the plugin tree `b665a3fac1d7`, built from origin/main
`e13af240100c066489e83c028d97339845402b55`; all 9 arm B runs loaded `b054e60d0e03`, built from `60dc376881d397d770874af16c8a6a8ed60956b2`. The
B build contains "K12 Terms and references" and the A build does not.

### Every run

| Run | pass | minutes | tokens (M) | refused callbacks | send-backs | ledger categories | K12 | intake questions | intake s / tool calls |
|---|---|---|---|---|---|---|---|---|---|
| A-hello-s1 | True | 9.2 | 18.2 | 0 | - | 11 | n/a | 0 | 22.9 / 5 |
| A-hello-s2 | True | 14.6 | 24.0 | 1 | - | 11 | n/a | 3 | 21.0 / 5 |
| A-hello-s3 | True | 9.5 | 16.8 | 0 | - | 11 | n/a | 2 | 24.8 / 6 |
| A-hello-s4 | True | 9.9 | 16.8 | 0 | - | 11 | n/a | 1 | 26.8 / 6 |
| A-hello-s5 | True | 8.5 | 17.2 | 0 | - | 11 | n/a | 2 | 19.3 / 5 |
| A-hello-s6 | True | 9.9 | 17.6 | 1 | - | 11 | n/a | 6 | 21.8 / 6 |
| A-ticket-assignment-s1 | True | 22.0 | 60.9 | 2 | - | 11 | n/a | 11 | 28.2 / 6 |
| A-ticket-assignment-s2 | True | 29.0 | 66.7 | 2 | - | 11 | n/a | 10 | 24.6 / 6 |
| A-user-listing-s1 | True | 10.8 | 15.5 | 1 | - | 11 | n/a | 2 | 31.3 / 4 |
| A-user-listing-s2 | True | 13.3 | 21.1 | 0 | - | 11 | n/a | 6 | 32.4 / 7 |
| B-hello-s1 | True | 11.1 | 19.2 | 0 | test-spec | 12 | yes | 3 | 24.1 / 5 |
| B-hello-s2 | True | 13.1 | 19.8 | 2 | test-spec | 12 | no | 0 | 18.6 / 3 |
| B-hello-s3 | True | 12.4 | 25.4 | 0 | - | 12 | no | 1 | 30.9 / 6 |
| B-hello-s4 | True | 10.8 | 17.1 | 0 | - | 12 | no | 3 | 28.0 / 6 |
| B-hello-s5 | True | 10.4 | 20.3 | 2 | test-spec | 12 | yes | 1 | 22.4 / 5 |
| B-hello-s6 | True | 9.6 | 15.4 | 0 | - | 12 | no | 4 | 25.7 / 5 |
| B-ticket-assignment-s1 | True | 17.1 | 26.1 | 2 | implement | 12 | yes | 12 | 28.7 / 5 |
| B-user-listing-s1 | True | 11.1 | 17.9 | 1 | - | 12 | yes | 2 | 27.5 / 7 |
| B-user-listing-s2 | True | 16.2 | 25.9 | 2 | implement | 12 | yes | 5 | 27.1 / 6 |

### Arms

Round 1, the registered 12-run design (samples 1 and 2; 11 finished):

| Arm | runs | passed | minutes | tokens (M) | refused callbacks | runs with a send-back | intake questions | intake seconds | intake tool calls | K12 applies yes |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 6 | 6 | 16.5 | 34.4 | 1.00 | 0 | 5.3 | 26.7 | 5.5 | 0 |
| B | 5 | 5 | 13.7 | 21.8 | 1.40 | 4 | 4.4 | 25.2 | 5.2 | 4 |

All runs, round 1 and R2 (samples 1 to 6):

| Arm | runs | passed | minutes | tokens (M) | refused callbacks | runs with a send-back | intake questions | intake seconds | intake tool calls | K12 applies yes |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 10 | 10 | 13.7 | 27.5 | 0.70 | 0 | 4.3 | 25.3 | 5.6 | 0 |
| B | 9 | 9 | 12.4 | 20.8 | 1.00 | 5 | 3.4 | 25.9 | 5.3 | 5 |

### Round 1, the registered rules (samples 1 and 2)

Eleven of the 12 registered runs finished. The twelfth, B ticket-assignment run 2, was refused by the harness at launch with no model
started (`b-ticket-s2-refusals/attempt-1-refused-at-launch.txt`: a listener of another session's ended case was still bound). The
registered rerun was then queued for 29 minutes, 78 attempts, and every attempt was refused because another session's Round 4 holds the
machine-wide lease on port 4180 (`b-ticket-s2-refusals/retry-attempts.txt`); I stopped it when the decision no longer depended on it.
That run was not made.

| Rule | Registered | Result | |
|---|---|---|---|
| L1 works live | at least 5 of 6 B ledgers name K1-K12; at most 1 B run with an intake refusal that names `question_categories` | 5 of 5 B ledgers hold 12 categories, as submitted and as stored; 0 intake refusals in any B run | holds |
| L2 no harm | B passes at least 5 of 6 and at least A minus 1 | A 6 of 6, B 5 of 5 | holds |
| L3 refusals | B's refused callbacks per run at most A's plus 1.5 | A 1.00, B 1.40 | holds |
| L4 cost | B's mean processed tokens at most 1.25 times A's | 21.8M against 34.4M, ratio 0.63 | holds, with the caution below |
| L5 no stop | no blocked B run; B asks a person no more than A | 0 blocked; both arms asked a person 0 times | holds |

With the missing run counted as a total failure, L1 and L2 still hold at their thresholds (5 of 6); L3 would fail only if it refused 9
callbacks, and L4 only if it used more than 149 million processed tokens, against a maximum of 67 million in any run.

**Caution on L4.** The arms are unbalanced by case: B has one ticket-assignment run, A has two, and the two A runs are the two most
expensive of the eleven, so the arm means flatter B. By case, round 1 only (B against A): hello 19.5M against 21.1M, ratio 0.92;
user-listing 21.9M against 18.3M, ratio 1.19; ticket-assignment 26.1M (one run) against 63.8M (two runs), ratio 0.41; the mean of the three
ratios is 0.84. The rule holds either way, but these runs show no saving: tokens per run ranged from 15M to 67M, and ticket-assignment alone from 26M to 67M.

### R2, the replication (new runs only: hello, samples 3 to 6)

| Arm | runs | passed | runs with a send-back |
|---|---|---|---|
| A | 4 | 4 | 0 |
| B | 4 | 4 | 1 (B-hello-s5, at test-spec) |

R2-1 needs B to have at least 2 more runs with a send-back than A. B minus A is 1, so **the excess did not replicate by the registered
rule.** Descriptively, pooled over every run: A 0 of 10 runs with a send-back; B 5 of 9 (test-spec 3, implement 2); hello alone A 0 of 6,
B 3 of 6. R2 alone, B 1 of 4 against A 0 of 4, is nowhere near the round-1 split but points the same way.

### Decision

Under the registration: L1 to L5 hold and R2-1 did not replicate, so **the change ships.** The round-1 send-back imbalance is recorded
as unexplained and compatible with chance, not as disproved.

### What these runs show, and do not

- **Shown (for these three cases, one subject and effort):** the shipped wording runs in the real packet with the host's own skill
  list; every B intake wrote all 12 categories, nobody had to be corrected, nobody stopped for a person, and all 19 runs passed. K12 is
  used: 5 of 9 B ledgers mark it "yes", the other 4 mark it "no" with a reason ("Python unittest has standard meaning", "Terms and named
  skill are clear"), and one filed a question under it (B ticket-assignment run 1, Q12, route inspect: "How does the repository define
  notification and ticket status?"). Intake cost did not rise: seconds 25.9 against 25.3 and tool calls 5.3 against 5.6 per intake.
  No `research` route and no `person` route was used in either arm.
- **Not shown:** the benefit. These requests are fully specified, so K12 had little to settle; the benefit is QB5's, at exercise level.
- **Pass rate:** 19 of 19 rules out only true pass rates below about 85% (one-sided 95%); B's 9 of 9 alone, below about 72%.
- **Send-backs remain the open point.** Pooled B 5 of 9 against A 0 of 10 (exact one-sided p 0.011, but round 1 was picked because it was
  odd, so that figure is biased toward an effect and is not used for the decision). A moderate real effect (say 40% against 5%) would give
  R2-1 a 46% chance of firing at 4 runs a side, so R2 cannot rule one out. The cost seen is small: on hello, minutes 11.2 against 10.3 and
  tokens 19.5M against 18.4M for B against A, within the spread of one arm. A comparison of about 10 hello runs a side (about 40 minutes)
  would settle whether the K12 packet raises test-spec send-backs on hello; it was not run because the registered decision did not need it.
- **Not tested:** the ticket-assignment second run; user-listing and ticket-assignment replications; any other subject or effort; the
  `research` route with a real search tool; a loosely worded live request.
