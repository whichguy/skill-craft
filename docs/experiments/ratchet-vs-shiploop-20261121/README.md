# Ratchet against ShipLoop (2026-11-21)

A harness that runs ShipLoop and the Ratchet loop on the same cases, each in a new Git repository of its own, on the
same host, model and effort, and measures what each delivered. Design, registered readings and results:
`docs/ratchet-vs-shiploop-journal.md`. This is an experiment apparatus, not a released skill; nothing under `skills/`
changes.

| File | What it is |
|---|---|
| `launch.py` | One detached checkout for both arms (`checkout`, adding to the E2E harness's cases.json the cases it lacks, with the Ratchet pilot's exact requests and starting files), and one run of an arm on a case (`run`; ShipLoop through `test/shiploop_e2e/run.py --source checkout`, Ratchet through the pilot's `ratchet.py --enrich reworded`); `resume` for a stopped ShipLoop run. |
| `measure.py` | Every script measure of one finished run, per point (ShipLoop's delivered head; Ratchet's first build and final): time, tokens (Codex rollouts), held-out checks (the pilot's `grade.py tree`), seeded faults (`mutate.py`), ticket assignment's calibrated defects (`baseline.py`), `static.py`, `coverage.py`. |
| `coverage.py` | Line, function and branch coverage from V8 coverage of every Node process the tests start, servers included (a preload writes a process's coverage when a signal stops it). |
| `static.py` | Code measures by script (functions, complexity, longest function, repeated windows, syntax) and documentation coverage (public surfaces new in the product, named in its user documents; comments above functions). |
| `code_judge.py` | Blind packets for one judge (both final products of a case, labelled X and Y by a seeded coin, two orders, names and ids masked) and the score of its answers. |
| `report.py` | The registered readings R1 to R7, the overall rule and the predictions, as `report.json` and `report.md`. |
| `page.py` | The results page drawn from `report.json`. |
| `export.py` | Copies the compact evidence from the runs root into `evidence/`. |
| `evidence/` | Each run's measure record, the launch records, the judge's key, answers and score, and the report. |

## Run

Python 3.13 or newer. The runs root is a folder outside the repository; label runs neutrally (a session sees its path).

```sh
python3 launch.py checkout "$ROOT"                       # once: the checkout both arms run from
python3 launch.py run "$ROOT" shiploop shared-expenses expenses-1
python3 launch.py run "$ROOT" ratchet shared-expenses expenses-2
python3 measure.py "$ROOT" expenses-1                     # after the run has ended
python3 code_judge.py packet "$ROOT" "$ROOT/judge"         # then one judge per packet writes answer-N.json
python3 code_judge.py score "$ROOT/judge"
python3 report.py "$ROOT" "$ROOT/report" --judge "$ROOT/judge/score.json"
python3 page.py "$ROOT/report" page.html --judge "$ROOT/judge/score.json"
python3 export.py "$ROOT"
```

Heavy parts (`mutate.py` and `baseline.py` on the ticket service, whose `npm test` starts a process per test file)
are best run after the live sessions end.
