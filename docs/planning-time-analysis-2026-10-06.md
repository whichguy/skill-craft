# Planning time: where it went, what is waste, and whether to one-shot and fix later (2026-10-06)

Status: **interim**. Output of a read-only workflow (three analysts on the stage anatomy of the Grok medium `none` run, the cross-run comparison and
what planning bought; a design pass over six one-shot options; a synthesis; two adversarial reviews, 17 findings applied and 3 rejected). Numbers
are labelled [M] measured, [D] derived, [E] estimated. Evidence (the analysts' structured results, the design options and the reviewers'
findings): `docs/experiments/planning-time-analysis-20261006/evidence.json`. The run analysed is
`/Users/dadleet/e2e-runs/20261006/v1220-battleship-grok-medium-none`, recorded in `docs/experiments/grok-none-battleship-20261006/`. n=1 and a
`--source checkout` run, so exploratory.

**Labels:** [M] measured, [D] derived, [E] estimated.

**Bottom line.** On Grok medium, `planning_review none` planning took 22.05 min on the harness clock and 20.5 on the engine clock [M: accept stamps in state.md joined to timeline.json]. It finished 52 of 52 actions with no revise. Stage windows of 72.7 (1.21.0 Node) and 63.8 (1.22.0 GAS, invalid trial) put it well outside their own spread [M]. **Time is measured. Quality is not.** The none documents are 2 to 4x smaller than the stage baseline (spec 8,409 B vs 19,151; test-strategy 5,714 vs 20,880; W1 test-spec 2,498 vs 11,162 [D: git blobs vs baseline in docs/pending-work-plan-2026-10-06.md]). Authoring minutes fell too (14.2 vs 19.9 on 1.21.0 [D]). Whether the removed content was churn or rigour is unknown. This is n=1 and a `--source checkout` run, so it is exploratory. SPEC forbids recording a checkout run as release evidence, so it is not PT-2 probe 1. On Luna no one-shot option reaches 30 min.

## 1. Where planning time went (none run, ShipLoop 0.54.0)

| Stage | Min [M] | Note |
|---|---|---|
| intake | 2.56 | 1.55 is before the engine exists |
| discovery | 1.37 | |
| research | 2.82 | 0.62 dead-end node-binary search |
| spec | 1.72 | |
| test-strategy | 1.08 | |
| **plan** | **8.38** | 38% of the window, 41% of output tokens |
| prepare + select-work | 1.07 | |
| step-plan | 2.25 | one 94 s request, 70% reasoning |
| test-spec | 0.80 | |
| **Total** | **22.05** | |

Generation was 18.05 min (82%), tools 2.5 (11%) and one compaction 1.47 (6.7%) [D]. Output was 86,986 tokens, 43% reasoning [M]. Time tracks tokens at about 80 tokens/s.

Plan-stage reads: the host ignored the requested `limit` on 17 of 24 ranged plugin-reference reads [M: I recounted FileContent line numbers in events.jsonl]. It returned text from line 1, up to about 49 KB, and returned the whole file on only 4 of 24. About 284k of 497k chars read before the first compaction lay beyond the requested range (about 64k tokens, 32% of the 203k context [E: 4.4 chars/token]). That is the largest removable block, not the whole fill. After the compaction, 9 of the plan's 11 repeat reads re-fetched about 149 KB [M: reviewer recount, not independently reproduced]. The cause is unknown.

## 2. Waste versus necessary

| Item | Min | Verdict |
|---|---|---|
| Reads, compaction, re-reads | up to 2.2 [D] | recoverable only if the host read behaviour is fixed and compaction does not recur (whole-run compactions recur every 14 to 20 min [M]) |
| Model-written Until Loop glue | up to 1.1 [D] | S-5 conformance (open item a02) |
| Node-binary hunt, wrong-cwd probe | 0.8 [D] | one-off detour, not recoverable by any option |
| Backchain loop | 2.7 [D] (3.7 incl. a 1.05 min first draft every mode needs) | value unknown; `backchain-check` is record-only and never gates (shiploop_protocol help text) |
| Pass logs never read | ~0.5 [E] | unknown |
| Slow bootstrap request | ~0.8 [D] | unknown |
| Orientation; spec, strategy, step-plan, test-spec | ~1.5; ~12 [D] | necessary |

The 1.1 and 2.2 items sit inside other totals, so do not add them. Recoverable is at most 3.3 min (15%) if both fixes work [D]. It is not needed to meet 30.

## 3. Cross-run

| Run | Window min | Output tokens | Improve share |
|---|---|---|---|
| Sonnet, stage | 7.3 | ~36k [E] | 55% |
| Grok, none | 22 | 87k | 0 |
| Grok, GAS, stage (invalid trial, window only) | 64 | 230k | 48% |
| Grok, Node, stage, 1.21.0 | 73 | 275k | 64% |
| Luna xhigh, stage | 376 | 1.15M | 54% |

Improve share is bind-to-accept. Repo docs use the children clock (Node 42.4 min, 58%). The pending plan flags this clash. Sonnet tokens are 99,115 measured session tokens split by tool-input character share, with sensitivity of about ±30% [E]. The 80% floor comes from Sonnet pairs.

Volume explains 80 to 96% of pairwise gaps [D]. That describes where time goes, not what to cut. Compaction is 3 to 9% in the four observable runs (6.7, 8.0, 9.1, 3.1 [M]). For Sonnet it is unmeasured (its events carry no signal; its 1M window against about 250k on Grok and Luna suggests none [E]), so compaction may separate Sonnet from the rest.

## 4. What planning bought

- **Load-bearing:** ids, commands and probes. 50 script receipts, 48 passed [M].
- **Retained reviews paid:** TC-15's weak oracle (system-test-author Improve child) and Sonnet's malformed-request-target crash (end-of-work review) both came from reviews `none` keeps [M: commits e3efb49, d6910c8].
- **Planning-review catches `none` gives up:** Sonnet b1e196d (importable server seam), E6b (10 of 15 platform errors caught vs 0 of 15) and Luna's five warranted fixes [M: docs/shiploop-planning-review-plan-2026-10-05.md, ledger F10].
- **Script-run checks:** only the loadable-module class. Criteria completeness, mapping, oracle independence and platform claims have none in any mode (SPEC S-10 carve-out 2026-10-05).
- **Late repairs on Grok and Sonnet:** about 1 to 3 min each, inside the stage that made them. Later stages cost more (system-test-author 15.6 min, release-check 4.6 [M]). Their planning-origin share is unknown, and the escape rate and Grok escape cost are unmeasured.
- **Luna escapes:** a 165.9 min test-red revise (missing module; 1.21.0, xhigh) and a 123.4 min implement revise (1.16.1, Luna max) [M]. PROBE_RULE moves only the first class earlier. LEARNINGS lists the second as not covered. Whether it prevents the first on Luna is unknown.
- **Late stages:** verify, integrate, integration-verify and product-acceptance found nothing. Undetected defects are unmeasured, not zero.

## 5. One-shot then fix later

| Option | Saves | Catching gate | Risk |
|---|---|---|---|
| **5. planning_review none** (shipped) | Grok: 50.7 min against the 1.21.0 stage run (cross-release, n=1, outside the earlier 29 to 46 range) [D]; Luna at most 172.5 of the window (203.4 gross, net lower) [M] | probe, test-red, implement and retained Improve; no script-run gate for review-only classes | escape rate unmeasured |
| **2. backchain-passes none** | Grok at most 2.7 [D]; Luna 22 to 57 [E] | none: no script check on plan ownership or order in any mode; later gate is test-red | stacked with 5, no model look at the plan graph; highest-risk pair |
| **2b. glue and read fixes** | up to 1.1 conformance; up to 2.2 only if the host cause is found [D] | none needed | engine work |
| **7. one review after first RED** (unbuilt) | unknown (earlier 32 to 38 had no derivation) | itself | unshown |
| 1. merge docs | 0.5 to 0.7 [E] | none lost | new carve-out; reject |
| 3. skip step-plan, test-spec | ≤3 per item [D] | none | removes gate fields; reject |
| 4. rolling wave | 0.3 to 0.6 [E] | carry-forward | reject |
| 6. all | Luna 115 to 131 [D: ledger floor; the 149.7 figure is retracted] | | reject |

**Ranking.**
1. Keep option 5 opt-in. Do not flip the default before PT-2. If it flips, a compensating review (option 7 or ledger L1) must precede the flip.
2. Do 2b as S-5 conformance (a02), not for time. Read the Backchain cost free from existing events (14,162 of the plan stage's 35,670 output tokens [D]). A paired n=1 probe cannot resolve 2.7 min against about 2x variance.
3. Build option 7 as that pre-flip compensator, or after PT-3 or a real escape.

**Cheapest next measurement.** One more plain none Grok medium probe, run per PT-2 (`--source marketplace`, `--timeout 5400`, `--max-resumes 2`, external watcher). The stop route (RC1 to RC3) is unbuilt. Unstopped, this run took 93.6 min and $12.50 [M, host-reported, billing unverified]. Stopped at W1 test-red it would be 26 to 27 min [M] and about $2.6 to $3.1 by turn-share [D]. PT-2 documents a worst case of about $45 per probe [E]: Grok has no spend cap, and a killed session reports no cost. It gives the first same-arm variance. It needs your go.