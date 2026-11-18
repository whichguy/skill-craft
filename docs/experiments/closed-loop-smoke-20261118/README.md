# The first real compute through the ShipLoop adapter: an attended one-step smoke on `hello` (2026-11-18)

Campaign `14b4a9cbf1` (scope S0, `hello` alone), evaluator clone at release 3.0.1 (`b23e0166b8c4dd70bffc08822e246d3cc122cc0f`), boundary
`cb2b6747c77e17d71caa383600674052392093bf76b13a5b2813fe7dcda17acb` ratified with the owner's approval, budget `seconds=14400,runs=8`, quiet
window 1, subject profile Codex `gpt-6.1-terra` at `high`. Journal: `docs/closed-loop-journal.md` R14 (the terms) and R15 (the results).

| file | what it holds |
| --- | --- |
| `readiness.json` | the orchestrator's readiness answer: `cases.runs:hello` runs (one real session, 1234 s), `grading.scores` scores, `improver.bounded` bounded, `grading.calibrated` unmeasured; `start_ok` true |
| `step-record.json` | the facade's record of step `14b4a9cbf1-S0-1`: published, its iteration facts (hello did not run; review and judge valid; cleanup verified) |
| `steps.jsonl` | every answer of `closed_loop.py step` while the step ran (start, four polls, done) |
| `certificate.json` | the certificate after iteration 1: incomplete (C1 three caseless records, C2 not quiet, C3 and C4 no run on the build) |
| `next.json` | the orchestrator's next action: stop, "owner decisions are needed before any further investigation" |
| `python-in-login-shells.json` | what `python3` each real session saw: Apple's 3.9.6 in both; the readiness session used `python3.15`, the step's session reported a missing prerequisite |
| `harness-python-pin-checks.txt` | the checks of the fix in the harness (journal R16): the quick tier's one failure, a test that read the new startup files as a platform's, and the reruns after narrowing it |
| `python-auto-select.txt` | the real case after ShipLoop's own fix (journal R17; portability journal Round 13): with Apple's 3.9.6 first on PATH the CLI starts on Homebrew's 3.15.1, a hook event stays silent, the refusal when no Python qualifies, and what the run again costs a hook event |
| `published-install-3.1.0.txt` | the published-install smoke of release 3.1.0 and the host refresh: a clean install matches main, and a real Python 3.7.3 with no newer Python is still refused |
| `python-floor-3.9.6.txt` | what ShipLoop's code needs (journal R18; portability journal Round 14): it compiles and its floor suites pass on Apple's 3.9.6, so its minimum is 3.9 |
