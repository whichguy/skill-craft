# Run analysis reports (2026-10-18)

Two live ShipLoop runs in the owner's Salesforce org, analysed step by step for three owner questions: was implementation
step by step, was the Improve loop effective, did each prompt say how to carry out its stage.

- Battleship (integration branch, packet-review units): https://claude.ai/artifact/4dwjgqaNCzRCCj5tzUr5ey ; run folder
  `/Users/dadleet/e2e-runs/20261017/bs-sf-int-b7c77f`.
- Chess (ShipLoop 1.5.0 plus the first efficiency wave): https://claude.ai/artifact/PeHgXZ2M19JYSRsx4ebV1s ; run folder
  `/Users/dadleet/e2e-runs/20261017/salesforce-chess-int-802e29`.

`bs/` and `chess/`: the step index and the reviewers' analysis per group (`analysis-*.json`: purpose, directive 1-5 with
evidence, response, step-by-step, Improve, gaps). `tools/`: `run_steps.py` lays a run out step by step from `events.jsonl`
(each event belongs to the action whose packet header the model last received), `build_report.py` renders the page,
`report-BRIEF.md` is the reviewers' rubric, `meta-*.json` the verdicts and ranked fixes. One chess reviewer was stopped by
a safety filter while quoting the model's raw reasoning; its rerun used only what the model said and did (`*.actions.md`).
The Battleship preparation reviewer scored 0-2; its scores are mapped to 1-5 (0->1, 1->3, 2->5) and the original kept.
