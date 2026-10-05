# Fast planning investigation, 2026-10-04

Read-only seven-agent workflow (three investigators, a design, two attacks, a revision) over the Luna 1.16.1
battleship run (`/Users/dadleet/e2e-runs/20261003/v1161-battleship-luna`, kept on the owner's machine; its compact
export is `test/shiploop_e2e/evidence/codex-gpt-6-luna-1.16.1-battleship-20261003.json`). The v1200 run was killed
by the owner at about 48 minutes in the spec stage and gave no loop evidence.

| File | What it is |
|---|---|
| `design-final.json` | the final design: summary, diagnosis, one-pass mechanism, per-prompt verdicts, SPEC tensions, savings, increments, measurement, owner decisions, unknowns and rejected findings |
| `report-knobs.txt` | where every planning loop's pass count is decided; the vendored Until Loop's behaviour at gate 0, 1 and 2 (experiments); the run-option home |
| `report-pass-value-and-cost.txt` | per-pass minutes and what each pass changed (warranted, marginal, churn), the savings table, and a per-call latency model from 2,919 Codex responses |
| `report-planning-prompts.txt` | the planning packets and reads per stage, and which cuts the evidence supports |
| `attack-quality-kiss.json`, `attack-engine-correctness.json` | the two adversarial reviews of the first draft, with what the revision accepted or rejected |
| `gate_experiment.py`, `gate_experiment.out` | runs the vendored Until Loop at gate 0, 1 and 2 on scratch repositories; the output is the evidence that gate 0 completes on the first `satisfied` report and the runtime has no pass ceiling field |

Labels in the reports: [M] read or run by the investigator, [I] inferred, [M-prior] read from an earlier journal
entry. Numbers are from one run; stage times vary about 2x between runs of the same model.
