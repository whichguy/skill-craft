# CI over-design audit, 2026-10-05

The owner asked whether CI is over-designed after a local quick-tier run for the evalskills merge took 569 s. A read-only
ten-agent audit (five measurers, synthesis, two attacks, revision) answered "partly, and not where suspected": the tier
structure is sound (quick on push, full on release, a cheap release-boundary job) and no layers duplicate each other's
assertions; the slowness is one selection rule and a few implementation defects; the real design tax is pins (22 of 36 red
runs since 09-22 broke on legitimate change, not on regressions).

| File | What it is |
|---|---|
| `ci-audit-final.json` | the final verdict: timings, why it is slow, value evidence, options O1-O13 with savings, risks and the evidence each needs, recommendation, do-not-touch list, unknowns |
| `name-collision-trace.json` | the selection of every tracked path before and after the O3 change, with every dropped (path, suite) pair |
| `dump_selection.py` | the script that produced the selection dumps (run it before and after a change to test/suite_catalog.py) |

Done (each its own commit, each verified): O1 `ebc2d25d` (launch() wakes when the session ends: shiploop-e2e 321 s to 64.5 s locally, CI green in 3m16s), O2 `c993f680` (the suite's recorded duration 0.7 s to 61 s, an estimate until per-suite seconds are printed), O3 `c479d85a` (plan, review and spec are generic stems; 28 suites to 17 on the evalskills merge replay; 9 collision suites dropped on the 1411d5f1 range, nothing else; quick tier 119 s for that commit).
Open: O4 per-suite seconds (the runner buffers output, so one timestamp covers every suite on GitHub), O11 and O10 (a hub suite for the 09-24 miss; derive the suite-count pin), O5 and O6 (apparatus memo 467 s to 103 s; mutants per scenario: release tier about 18.7 to 10.5-11 min), O7 to O9, O12, O13 only if a measured wait still hurts.
