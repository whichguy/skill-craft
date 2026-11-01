# Replication R3: do the K12 line's stage send-backs repeat on a representative Node service case? (2026-11-01)

Consumer: the owner, who answered "Yes" on 2026-11-01 to "Run about 10 more hello runs a side to settle the send-back question?" and then
suggested "a more complicated test which does a standalone node server with app functionality ... a more representative test case to
repeat on"; and the session that reads the Results below to decide whether anything follows. Follows the live A/B of the
terms-and-references line ([../terms-line-live-ab-20261101/README.md](../terms-line-live-ab-20261101/README.md)) and its replication R2.

This file is written and committed **before** any scored run. The rules are never edited; results are appended under "Results".

## Question

On today's `main`, does the K12 terms-and-references line (shipped in skill-craft 2.28.0 / ShipLoop 1.27.0) make ShipLoop send stages back
more often, on a case that plans several steps?

## What is known, and how much it is worth

- **Round 1** of the live A/B (hello, user-listing, ticket-assignment; two runs per arm per case): runs with a stage send-back, arm A (no
  K12) **0 of 6**, arm B (K12) **4 of 5**; exact one-sided p of that split 0.0152. The registered rules L1 to L5 did not look at send-backs;
  the excess was noticed after the runs, so that p is not a test (results commit `74cfdc91ea4a15287508d9a5913336a3b8584b90`).
- **R2**, registered before its runs (`9c2bf16a0264edc7d8b682ded7dc9a8292e8a838`): hello, four more runs per arm, rule R2-1 (B has at least two more runs with a send-back
  than A): A 0 of 4, B 1 of 4; R2-1 did not fire. Pooled over all 19 runs, descriptive and biased toward an effect (round 1 was chosen for being
  odd): A 0 of 10, B 5 of 9; by stage in B, test-spec 3 and implement 2. No mechanism is known by which intake's ledger changes what
  step-plan writes five stages later.
- **The product has changed since.** Round 1 and R2 ran on release 2.27.2 (`e13af240100c066489e83c028d97339845402b55`). Three ShipLoop commits that bear on exactly those
  send-backs came after it and are in `main` now (checked with `git merge-base --is-ancestor`): `b8d320335c81151a99e7d168b684d79fd0e81352` (step-plan refuses a criterion a
  focused command names without a test ID of its own, the test-spec send-back's cause), `9870c6f68bfbd9375340c0e91ffdf4abfd76bd85` (rule C: the proof-order refusal also
  refuses a plain suite Proof for a criterion only an unwritten test confirms, the implement send-back's cause) and `4515368495e2b2e50ea07f7599146875188449f9` (the
  focused-ID wording fix). So this round cannot say whether the 2.27.2 excess was chance; it says whether today's product has one.

## Design

- **Subject.** Codex `gpt-6.1-terra` at `high`, all tools, hooks on, `--source checkout`, `--timeout 4800`: the setting of round 1, R2 and the
  last three ShipLoop rounds, the same in both arms.
- **Case.** `shared-expenses` (commit `47ed1804d379e1ad58ac5ad081e027dab043f906`): a dependency-free Node.js service with a JSON data file, groups, equal and exact expense
  splits, balances, a stated settlement rule, restart persistence and a concurrency requirement; six product checks calibrated against a
  reference service and nine defects before any live run. It leases no port and needs no browser, so the lanes cannot refuse each other and
  another session's rounds on 3000 or 4180 cannot starve them (the 29 minutes and 78 refusals of the A/B's twelfth run). It was added because
  hello is a one-step case (mean 10.2 minutes at high over 16 rows, almost all pipeline overhead) and the owner asked for a more
  representative one. The unscored smoke run before this registration: one run on `main` at `d71eaa7198772501b189dff76308d4ee7ac533cb` (release 2.29.0, K12 present) plus the case files, before the case was rebased onto P (`~/e2e-runs-r3/20261101/smoke-b-s1`, its row in `test/shiploop_e2e/baselines.jsonl`): the harness verdict is pass and all six checks passed on the model's own delivery; 22.2 minutes at the machine's load, 37.1 million processed tokens, 227 turns, 2 implement stages, 3 refused callbacks; a 12-category ledger with K12 "yes"; and one stage send-back, at implement ("The step proof requires node --test to execute TC_1-TC_4, but implement forbids writing tests and the test stage occurs later"), the fault family round 1 saw, on a tree that has rule C. It is not one of the 20.
- **Arms, pinned.** P = `47ed1804d379e1ad58ac5ad081e027dab043f906` (`main` with the case, ShipLoop 1.29.0, skill-craft 2.30.0). **B = P**, run from its own detached worktree. **A = P with
  `git revert --no-commit 60dc376881d397d770874af16c8a6a8ed60956b2` committed on a scratch branch** (K12 and the look-it-up-first sentence removed; intake's ledger is K1 to K11
  again, its shape check too); A differs from B in the three skill files that commit changed (and in its test file, which no run reads), and the scratch commit is
  never merged. Each run starts `run.py` from its arm's checkout, so `--source checkout` builds that arm; the plugin tree digest of every run is recorded
  (`plugin_sha256`). `main` may move while the runs go; the arms do not.
- **Runs.** 10 per arm, 20 in all, over five lanes started 20 seconds apart, each lane running four runs in turn with the arms alternating so that both
  share the hours (`lanes.sh`): L1 A1 B1 A2 B2; L2 B3 A3 B4 A4; L3 A5 B5 A6 B6; L4 B7 A7 B8 A8; L5 A9 B9 A10 B10. Output
  `~/e2e-runs-r3/20261101/<arm>-shared-expenses-s<n>`, a runs root of its own (the orphan check scans only that root).
- **Measures** (`r3_reader.py`, which reads each run's `result.json`, `metrics.json`, `trace.jsonl` and `state.md` through the first A/B's reader):
  the harness verdict, minutes, processed tokens, refused callbacks, **send-backs with their stage and summary**, the stored intake ledger, the
  K12 row and questions, the number of implement stages, the failed product checks, `asked_user`, the final status, the plugin digest.

## Rules (decided now)

A **send-back** is a history entry of the run's state with outcome `send-back` (what `e2e_ab.read` reads; round 1 and R2 used the same);
a run counts once, whatever its stage.

1. **R3-1, the excess repeats.** Over the 10 runs of each arm, the runs with a send-back in B against A, exact one-sided Fisher test (B
   higher), **p at most 0.05.** With 10 a side that is: A 0, B at least 4; A 1, B at least 6; A 2, B at least 7; A 3, B at least 8; A 4, B at least 9.
2. **R3-2, leaning.** B has more runs with a send-back than A and p is above 0.05 and at most 0.20: no finding. A further round on new runs
   is registered before it starts, with its own rule.
3. **R3-3, no excess seen.** Neither of the above.
4. **S1, the arms differ as designed** (a check on the experiment): the runs of each arm carry one plugin digest and the two differ; every
   stored B ledger names 12 categories and every A ledger 11. A run that fails S1 is scored and listed, and the analysis is repeated without it.
5. **C1 to C3, the delivery and its cost** (L2 to L5 of the first A/B, over 10 runs a side): C1 B passes the harness verdict in at least 8 of 10 runs and
   in at least as many as A minus one; C2 B's mean processed tokens at most 1.25 times A's, and B's mean refused callbacks at most A's plus
   1.5; C3 no B run ends blocked, and B asks a person no more often than A.

**Decision.** R3-1 holds: the shipped line has a measured cost on today's product. Nothing under `skills/` changes in this session and
the release stands; the finding goes to the owner with every send-back by stage and arm and their summaries, because keeping, fixing or
dropping a ShipLoop behaviour is the owner's call. R3-2: a further round is registered. R3-3: the line stays; the round-1 imbalance
is recorded as unexplained and not repeated on today's product. C1 to C3 failing goes to the owner the same way. Under every outcome the
report names all send-backs by stage and arm, the pass, refusal, token and time figures, and what the data cannot tell.

**Runs that do not finish.** A launch the harness refuses (no model started, no output folder) is retried by the lane every 90 seconds
for up to 40 minutes, each refusal recorded. A host or account failure (credit limit, network, a killed process) is run once more and both
attempts are recorded. A run that started and ended blocked or failed is scored as its state stands; it has a send-back only if its state
shows one. The reader prints the p-value also with every missing run counted for the null (a send-back in A, none in B) and for the excess
(the reverse).

## What this can detect (my arithmetic, exact binomial sums over the 121 outcomes)

At 10 a side R3-1 fires with probability 0.001 if both arms have a 5% rate, 0.005 at 10%, 0.017 at 25%. If B truly has 40% and A 5%
it fires 43% of the time; 50% against 5%, 63%; 40% against 10%, 29%; 60% against 20%, 43%. So a result that does not fire says "no excess
seen at this size", not "none"; a miss against a 40%-versus-5% excess is the likelier outcome than a hit. Ten a side is what the owner
approved; if the result is R3-2 a second block is the next step, and 20 a side in all would reach 81% for 40% against 5% and 94% for
50% against 5%.

## What this cannot settle

- **The benefit of K12.** The prompt is fully specified, so K12 will mostly find nothing to settle. The benefit evidence is the
  confirmation's, at exercise level; a loosely worded live request is not tested here.
- **Why.** Reading the summaries of any send-backs is a description, not a test of a mechanism.
- One case, one subject and effort; a new case whose first scored runs these are (one unscored smoke run before them); run time varies
  by tens of percent between runs on a loaded machine, so no time effect is claimed; the served model's identity and the dollar cost are
  not observed.

## Reproduce

```
bash lanes.sh L1 ~/e2e-runs-r3/20261101 <checkout of arm A> <checkout of arm B> A:1 B:1 A:2 B:2     # and L2 to L5 as above
python3 r3_reader.py      # reads the runs, applies R3-1 to R3-3, S1 and C1 to C3, writes scores.json and results-tables.md
```
