# Consumer reads (step 0 of the consumer contract plan)

Question: which ShipLoop artifacts does the model actually open, at which stage, and is the reader a later stage (a consumer) or the stage that wrote the file (checking its own work)?

Method: `consumer_reads.py` over the saved Claude runs' `events.jsonl`.
- Reads are Read tool calls, plus Bash commands that run a content-showing command (cat, sed, head, grep, python, ...) on the path.
- Writes are Write and Edit calls, plus Bash `>`, `>>`, `tee` and `sed -i`.
- Each call is attributed to the stage of the most recent packet header the model saw.
- Not measured:
  - whether a read was used;
  - subagent reads;
  - per-file reads under a recursive grep (counted once as "home dir").

Evidence: `eight-stage-runs.json` covers seven runs on the 8-stage build: hello on `13d278dd`, Checkers on `88d412e9` and `1ac83089`, and four hellos on `1ac83089`. `released-1270-runs.json` covers seven runs on the released 1.27.0 tree.

## Reads by stage on the 8-stage build (7 runs)

| Artifact | Written at | Read by the stage that wrote it | Read by a later stage (consumer) |
|---|---|---|---|
| feature `spec.md` | spec | spec 11 | carry-forward 1 |
| feature `plan.md` | plan, step-plan | plan 9, step-plan 10 (step-plan also writes it) | test-spec 2, carry-forward 1. Step-plan reads the plan stage's file: a real consumer |
| feature `test-spec.md` | test-spec | test-spec 19 | verify 1, carry-forward 1. **The test stage never opened it (0 reads)** |
| feature `system-tests.md` | system-test-author | system-test-author 8 | system-test 3, product-acceptance 1, release-plan 1 |
| feature `release-plan.md` | release-plan | release-plan 7 | release 1, release-check 1, operations 2 |
| feature `outcome.md` | release-verify | none | handoff 2 |
| `spec.md` | spec, test-strategy, carry-forward | spec 23, test-strategy 9, carry-forward 2 | plan 9, document 3, implement 1 |
| `environment.md` | prepare, release-plan, release-verify, carry-forward | as written | step-plan 4, document 2, test-spec 2, plan 1 |
| `architecture.md` | plan, carry-forward | plan 7, carry-forward 4 | **implement 1 (one of seven runs); step-plan, test-spec, test and verify 0** |
| `test-strategy.md` | test-strategy, carry-forward, step-plan | test-strategy 16 | plan 6, step-plan 5. **test-spec, test and system-test-author 0** |
| knowledge `README.md` | spec, plan, release-verify, prepare | as written | used as a file the model maintains, not as an index |
| `features/README.md` | (model-written in one run) | spec 1 | none |
| `run/results/*.md` | engine | — | step-plan 2, plan 1, product-acceptance 1 (the prose hand-off path is almost never followed) |
| `run/notes/` | implement, carry-forward, document, verify | — | implement 1 |
| `SHIPLOOP.md`, `state.md`, `reference.md`, `report.html` | — | — | never opened |

## Findings (status: interim; seven first runs on one host)

1. **The build and test stages barely consume the files meant for them.**
   - The build phase hardly opens the architecture file: implement 1 read in 7 runs; step-plan, test and verify none.
   - No test stage opened the test strategy: test-spec, test and system-test-author 0 reads.
   - The test stage never opened `test-spec.md`.

   This supports the owner's direction: quote the named sections of `environment.md` and `architecture.md` into those packets (READS) instead of relying on a path the model may not open.
2. **Some feature files do have model consumers, so their content must be quoted forward, not dropped:**
   - step-plan reads `plan.md`;
   - system-test and product-acceptance read `system-tests.md`;
   - release, release-check and operations read `release-plan.md`.

   The contract keeps each one's content in a state field and quotes it into exactly those stages' packets (plan section 3.2).
3. **The prose hand-off by path is close to unused:** `results/*.md` was opened 4 times in 7 runs. Content that matters must be quoted, which is the plan's premise for the hand-off fields.
4. **Most reads are self-reads.** A stage re-reads the file it is writing. They are not evidence of a consumer.
5. **The feature spec and the indexes have no later reader:**
   - the feature spec is read once by carry-forward;
   - `features/README.md` has no reader;
   - `SHIPLOOP.md` was never opened.

   This is consistent with removing them.

Reproduce:

    python3 docs/experiments/consumer-reads-20261011/consumer_reads.py <run> [<run> ...] --json out.json
