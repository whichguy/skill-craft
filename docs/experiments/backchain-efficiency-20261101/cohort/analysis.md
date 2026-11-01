# Backchain efficiency cohort: analysis

Attempts present: 60 of 60. Grading passes: 3. Grader noise bound: 1.05 points (mean pairwise difference between passes divided by sqrt(3)).

## Decision

- Winner: none
- Decided by: none
- quality -1.19, 95% [-8.85, +6.26], Wilcoxon p=0.7532, 30 cells in 10 cases (points): inconclusive (not near-identical, and the tests do not agree on a difference)

## Paired comparisons (candidate minus control)

candidate minus control per case x repetition cell; 95% percentile bootstrap (4000 resamples, seed 3) clustered by case; Wilcoxon signed-rank over per-case mean differences. Decision measures: score, then input_plus_output_tokens, then wall_seconds; qualified and key_rate block a candidate win; the rest are descriptive.

| Measure | Cells | Cases | Mean | 95% interval | Wilcoxon p | Candidate higher / lower |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| score | 30 | 10 | -1.19 | [-8.85, +6.26] | 0.7532 | 5 / 13 |
| qualified | 30 | 10 | +0.40 | [+0.13, +0.70] | None | 13 / 1 |
| key_rate | 12 | 4 | +0.01 | [+0.00, +0.03] | None | 2 / 1 |
| input_tokens | 30 | 10 | -624949.97 | [-870978.77, -418111.47] | 0.0051 | 0 / 30 |
| cached_input_tokens | 30 | 10 | -599739.73 | [-837260.80, -399795.20] | 0.0051 | 0 / 30 |
| uncached_input_tokens | 30 | 10 | -25210.23 | [-33143.17, -17335.17] | 0.0051 | 1 / 29 |
| output_tokens | 30 | 10 | -5130.67 | [-6056.17, -4314.50] | 0.0051 | 0 / 30 |
| input_plus_output_tokens | 30 | 10 | -630080.63 | [-877055.60, -422650.70] | 0.0051 | 0 / 30 |
| wall_seconds | 30 | 10 | -123.75 | [-150.65, -99.55] | 0.0051 | 0 / 30 |
| commands | 30 | 10 | -5.13 | [-7.23, -2.83] | 0.0093 | 3 / 25 |
| code_blocks | 30 | 10 | -3.67 | [-5.20, -2.33] | 0.0076 | 2 / 27 |

## Arms

| Arm | Present | Outcome ok | Qualified | Mean score | Keys passed | Median input+output tokens | Median wall s | Median commands | Median code blocks | Routes |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| control | 30/30 | 7 | 7 | 92.3 | 84/102 | 1192680.0 | 234.4 | 18.0 | 6.5 | hand-built 30 |
| candidate | 30/30 | 22 | 19 | 91.1 | 85/102 | 653619.0 | 115.2 | 14.0 | 3.0 | toolkit 30 |

## Outcome check failures

- control: loop_terminal 10, plan_completion 23, plan_structure 23
- candidate: loop_terminal 7, plan_completion 2

## Per case (finding F7)

| Case | Held-out | Qualified control / candidate | Score control / candidate | Keys control / candidate | Median tokens control / candidate |
| --- | --- | --- | --- | --- | --- |
| independent-inspection-scopes | no | 0/3 / 3/3 | 81.6 / 98.3 | - | 1149499 / 669999 |
| stale-build-receipt-identity | no | 1/3 / 2/3 | 100.0 / 100.0 | - | 1191091 / 600998 |
| legacy-draft-discovers-mapping | no | 3/3 / 3/3 | 100.0 / 100.0 | - | 1019507 / 649294 |
| bounded-source-edge-repair (F7) | no | 0/3 / 0/3 | 96.4 / 69.8 | - | 776843 / 616931 |
| known-external-approval-blocker (F7) | no | 0/3 / 3/3 | 100.0 / 100.0 | - | 2410240 / 671189 |
| missing-normative-redaction-source (F7) | no | 3/3 / 3/3 | 100.0 / 97.9 | - | 1140196 / 666894 |
| billing-late-fee | yes | 0/3 / 3/3 | 82.2 / 100.0 | 11/21 / 11/21 | 2008302 / 710713 |
| library-reminders | yes | 0/3 / 2/3 | 98.8 / 98.8 | 28/30 / 29/30 | 1280103 / 701937 |
| revenue-export-lineage | yes | 0/3 / 0/3 | 89.3 / 80.2 | 21/21 / 21/21 | 871486 / 591220 |
| orders-cancel-rpc | yes | 0/3 / 0/3 | 74.8 / 66.3 | 24/30 / 24/30 | 1417278 / 755835 |

## Previously losing cases, pooled (finding F7)

Cases: bounded-source-edge-repair, known-external-approval-blocker, missing-normative-redaction-source. Qualified: control 3/9, candidate 6/9. Mean score: control 98.8, candidate 89.2. Mechanical keys: none (no held-out case in this block). Blocks a candidate win: no.

## Confirming-review yield, control arm (finding F6; not in the decision)

2026-10-16 prior: 0 of 11 confirming reviews changed anything (PROTOCOL.md, finding F6). Rule: every report the runtime accepted after the attempt's first trivial report, read from the packets the done calls printed (last_report.classification).

This cohort: 7 confirming reviews in 30 control attempts (10 with a trivial report); 0 non-trivial, 0 unresolved; 0 incomplete sequences; 0 attempts without an event log.

| Attempt | Gate | Report classifications | Confirming | Non-trivial at | Complete |
| --- | --- | --- | ---: | --- | --- |
| independent-inspection-scopes-control-r1 | default | unresolved | 0 | - | yes |
| independent-inspection-scopes-control-r2 | default | trivial, trivial | 1 | - | yes |
| independent-inspection-scopes-control-r3 | default | trivial, trivial | 1 | - | yes |
| stale-build-receipt-identity-control-r1 | one | non-trivial | 0 | - | yes |
| stale-build-receipt-identity-control-r2 | one | trivial | 0 | - | yes |
| stale-build-receipt-identity-control-r3 | one | non-trivial | 0 | - | yes |
| legacy-draft-discovers-mapping-control-r1 | one | trivial | 0 | - | yes |
| legacy-draft-discovers-mapping-control-r2 | one | non-trivial | 0 | - | yes |
| legacy-draft-discovers-mapping-control-r3 | one | trivial | 0 | - | yes |
| bounded-source-edge-repair-control-r1 | one | non-trivial | 0 | - | yes |
| bounded-source-edge-repair-control-r2 | one | non-trivial | 0 | - | yes |
| bounded-source-edge-repair-control-r3 | one | non-trivial | 0 | - | yes |
| known-external-approval-blocker-control-r1 | default | non-trivial, trivial, trivial | 1 | - | yes |
| known-external-approval-blocker-control-r2 | default | non-trivial, trivial, trivial | 1 | - | yes |
| known-external-approval-blocker-control-r3 | default | trivial, trivial | 1 | - | yes |
| missing-normative-redaction-source-control-r1 | one | unresolved | 0 | - | yes |
| missing-normative-redaction-source-control-r2 | one | unresolved | 0 | - | yes |
| missing-normative-redaction-source-control-r3 | one | unresolved | 0 | - | yes |
| billing-late-fee-control-r1 | default | trivial, trivial | 1 | - | yes |
| billing-late-fee-control-r2 | default | trivial, trivial | 1 | - | yes |
| billing-late-fee-control-r3 | default | unresolved | 0 | - | yes |
| library-reminders-control-r1 | one | unresolved | 0 | - | yes |
| library-reminders-control-r2 | one | non-trivial | 0 | - | yes |
| library-reminders-control-r3 | one | unresolved | 0 | - | yes |
| revenue-export-lineage-control-r1 | one | unresolved | 0 | - | yes |
| revenue-export-lineage-control-r2 | one | unresolved | 0 | - | yes |
| revenue-export-lineage-control-r3 | one | unresolved | 0 | - | yes |
| orders-cancel-rpc-control-r1 | default | unresolved | 0 | - | yes |
| orders-cancel-rpc-control-r2 | default | unresolved | 0 | - | yes |
| orders-cancel-rpc-control-r3 | default | unresolved | 0 | - | yes |

Each non-trivial confirming review is examined by hand against the request: did it repair a real material defect? A real defect only a confirming review found is reported to the owner as evidence on D1.
