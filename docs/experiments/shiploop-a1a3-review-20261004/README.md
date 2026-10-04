# A1 to A3 adversarial review, 2026-10-04

**Reviewed.** A1 `0d8d32f9` (ShipLoop test-run classification), A2 and A3 `3c604304` (harness stage
attribution, baseline identity, termination record) and the design document `e469f2a4`, merged onto
the 1.19.x release line as `9db0be37` (branch `a1a3-integ-7f216e`).

**How.** Four scopes (A1, A2, A3, integration with the release line) by three lenses (rules,
adversarial, runtime); every finding verified by two skeptics; 186 agents. 78 findings confirmed
(30 major, 48 minor; 68 by both skeptics, 10 by one). 9 further candidates were rejected by both
skeptics; the export does not carry them and that count comes from the review run's report. The 16
groups below are the review's own grouping. Reproduction scripts stayed in the review session's
scratchpad; only this compact export is kept.

**`findings.json`.** One object per line: index, cluster, severity, scope, lens, title, file, symbol,
scenario, evidence (cut to 400 characters), suggested_fix (cut to 200) and the two skeptic votes.
Details: [design document section 10](../../shiploop-graph-engineering-comparison-2026-10-04.md).

**Dispositions.** "see follow-up" means fixed or decided on one of the two review follow-up
branches (skills, harness), not merged when this was written. "fixed here" and "documented here"
mean this commit (design document, harness README, journal). The integrator updates the column
after merging.

| Cluster | What | Indices | Disposition |
| --- | --- | --- | --- |
| A | revise route refused after could-not-run (test-green, regression, static-checks) | 0, 2, 3, 22 | see follow-up (skills) |
| B | budget-skipped command is a deterministic could-not-run | 1 | see follow-up (skills) |
| C | hosts without per-turn usage: measured zeros, no incomplete row, no difference reported | 4, 6, 7, 9, 20, 21, 24, 28 | see follow-up (harness) |
| C2 | Claude per-call counters zero by construction | 10, 25 | see follow-up (harness) |
| D | stage_diff_lines: incomplete marker, unmeasured side, coverage | 5, 8, 40, 56, 66 | see follow-up (harness) |
| E1 | Claude API error recorded as stop success | 11, 14, 64, 74 | see follow-up (harness) |
| E2 | session_stops not one entry per session | 12, 19, 62 | see follow-up (harness) |
| E3 | regrade and resume budget record a host exit nobody observed | 13, 15, 18, 27, 29, 68 | see follow-up (harness) |
| M23 | marketplace-branch regrade overwrites a finished result.json | 23 | see follow-up (harness) |
| F | tests missing (A3 stops and wiring, A2 behaviours, A1 budget skip and legacy records) | 16, 34, 48 | see follow-up (skills, harness) |
| G | change-admission records missing for A2 and A3 | 17, 26, 51 | fixed here (design doc sections 8.1 to 8.3, 9) |
| H | keepalive stuck-stop premise broken by could-not-run | 31, 33, 38 | see follow-up (skills); recorded here in section 8.1 |
| I | A2 edge cases (stamps, recreated timeline, seeded runs, incomplete-row edges) | 41, 42, 43, 45, 46, 47, 53, 54, 55, 58, 59, 61, 65, 67, 69, 72, 73, 75, 76 | 45, 53, 69, 73, 76: documented here (section 10.4); rest: see follow-up (harness) |
| J | A1 minor (partial output, 126/127, wording, doc count) | 30, 32, 35, 36, 37, 39 | 30, 35: documented here (10.4); 37: fixed here; 32, 36: see follow-up (skills); 39: text see follow-up, route open (owner decision, 10.4) |
| K | no comparable baseline; skipped comparison prints nothing | 60 | see follow-up (harness); README describes the rule |
| L | stale docs (README, citations, journal, exporter duplicate, wall-clock) | 44, 49, 50, 52, 57, 63, 70, 71, 77 | 50, 52, 57, 63, 70, 71, 77: fixed here (52 as a stated limit); 44: see follow-up; 49: doc part fixed here, code part see follow-up |
