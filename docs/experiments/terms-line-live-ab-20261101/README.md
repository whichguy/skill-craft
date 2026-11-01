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
