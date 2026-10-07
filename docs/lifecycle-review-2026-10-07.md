# ShipLoop lifecycle review: stages, packets and ledger (2026-10-07)

Status: **interim**. Five read-only reviewers (early planning; per-item plan, tests-first and build; per-item check and integrate;
whole-product test and release; the ledger and packets as a system) judged the 34 stages and the records against the real packets and
results of one finished run: Grok 4.7 medium, planning review off, Node Battleship, 52 accepted stages
(`/Users/dadleet/e2e-runs/20261006/v1220-battleship-grok-medium-none`, record in `docs/experiments/grok-none-battleship-20261006/`), with
the Sonnet 5.5 run (checks on) and the Google Apps Script run as comparisons. Every saving below is a single-run figure, measured or
derived from stage times, or estimated; none has been tested. The reviewers' own reports are model output; this document is the
combination. Related: `docs/planning-time-analysis-2026-10-06.md`, `docs/test-suite-review-2026-10-06.md`.

## 1. Correctness findings (more important than speed)

1. **The test counter misreads two common cases** (`shiploop_test_counts.py`): `node --test` output is not parsed (`counts: null`, so
   `min_tests` is never enforced), and a passing test whose title contains `pending`, `skip`, `todo` or `deselected` counts as missing.
2. **The delivered repo's plain `node --test` needs macOS Chrome.** The browser script claimed to sit outside the test folder; the final
   regression run printed its two browser cases inside bare `node --test`, and the file hard-codes the Chrome path with no skip. Three
   review passes, system-test, acceptance, operations and handoff all passed it. Fix: refuse or warn when a regression run prints an id
   that belongs to a focused-only system command.
3. **release-verify runs the consumer checks in the work area, not in the returned source checkout,** so the script proof does not observe
   the product the user receives.
4. **Facts the planning stages did not settle** were repaired downstream: the plan said ESM in a repo with no `package.json`; the browser
   tool was not probed at test-strategy (Luna's two escapes, 165.9 and 123.4 minutes, were this kind).
5. SKILL.md says an iteration 4 that still fails stops a loop; the loop contract says there is no iteration limit.
6. The retry loop's state lives in a temporary file the ledger does not point to, so a fresh agent cannot find it (S-6 gap).

## 2. Which stages are necessary

Real work or standing-risk gates, keep: discovery, research, spec, test-strategy, plan (trim its reads), step-plan, test-author, implement,
test-refine, document, static-checks (material repair in 5 of 5 item-runs), verify, carry-forward, system-test-author, system-test, release,
handoff.

Redundant or script-decidable, in the order the reviewers found evidence:

| Stage | Observation | Proposal | Saving |
|---|---|---|---|
| select-work | read by no stage; restated the queue in 21 of 21 runs | script-only step | 0.4 min per item |
| baseline | repeats discovery's zero-test result for item 1 | script runs the recorded commands at item entry | 1.2 min |
| test-red | same command as the author probe, same 5 failures 20 s later | fold into test-author with a per-id red check (also closes 6 vacuous passes seen in the GAS run) | 0.6 min |
| test-green | loop ended in one trivial iteration in all 6 cases seen | script run at implement's complete; open the loop only on failure | 2.8 min |
| regression | 0 catches in 5 item-runs; verify reruns the same command | script gate first, loop only on failure | 2 to 3 min (E) |
| skill-assess, skill-validate | N/A in 5 of 5, script-checkable | merge; script writes N/A when no skill surface | 1.6 min |
| integrate, integration-verify | no catches; same worktree, not a clean checkout | merge when no chain is bound | 1.1 to 1.5 per item (E) |
| release-check | re-proved a command already run twice | merge into release for a source-return-only build | about 3 min (E) |
| operations | found nothing for a local process | fold into handoff when nothing is deployed | 0.8 min |
| product-acceptance | maps request sentences to ids system-test already passed | tail of system-test | 0.4 min |
| intake | defaults became spec decisions; "ask the user" unused in 19 of 19 | merge into discovery (weakest case) | 0.5 min (E) |
| prepare | model re-runs `node --test` | script runs the smoke command; move the knowledge close to plan | 0.7 min |

Merging these takes a small local build from 34 visited stages to about 24 and saves roughly 15 to 20 of 93.6 minutes (estimated, single
run). A deployed product keeps operations, release-check and the chain-bound integrate pair.

## 3. The ledger and packets

- One stage summary is stored about 8 times (inbox, results, `accepted`, `history`, context index, report, later packets); `history` equals
  `accepted` for 52 of 52. `state.md` is 157 KB. Notes were written 9 times and read 0 times; lint files 88 written, 0 model reads.
- After every compaction (5 of 5) the model's first call was to re-read the current packet; it never read notes, state or status. The
  packet is the real recovery path.
- Packets average 40 KB with about 6 KB printed; 185 rule lines repeat in at least 40 of 53 packets (56% of a packet); a median packet
  names 11 reference files totalling 323 KB; 27 of 35 ranged skill-markdown reads returned whole files (687 KB for about 174 KB asked).
- Proposals: one stored summary per stage (the stage record keeps the results file's hash); relative paths and pointers only in the
  context index; one run-level rules file; per-stage reference cards of 8 KB or less; script-generated knowledge index (removes about 20
  of 58 model writes); record the loop's temporary state path in the run directory.

## 4. Owner rules at risk

S-10 (loops iterate until a check confirms) for the script-first regression and test-green, which would have no loop receipt on the
passing path; S-6 and S-11 for any packet or ledger consolidation (packets must still stand alone and knowledge must still be retained);
"rigour is standard even for small requests" for merging release-check and operations; script-run proof is kept or strengthened by every
proposal above.

## 5. Order

1. The correctness findings (section 1): fail-first tests, one note, no owner-rule risk.
2. Script-first and low-risk merges: select-work, baseline, skill pair, test-red into test-author, operations into handoff.
3. Ledger: one stored summary per stage with the hash check; trim the context index; script-generated knowledge index.
4. Packets: the run-level rules file and reference cards (needs a compaction probe).
5. Owner decisions: script-first loops (S-10), integrate pair, release-check, intake merge, the Backchain pass itself.
