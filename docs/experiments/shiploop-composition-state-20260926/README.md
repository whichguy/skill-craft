# Composition and state-lifecycle experiment harness — 2026-09-26

Results and decisions: [../../shiploop-composition-state-experiments-2026-09-26.md](../../shiploop-composition-state-experiments-2026-09-26.md).
Every judge verdict behind those tables is in [verdicts.json](verdicts.json).

These scripts launch real model calls (`claude -p --model sonnet`). They are not
part of the test suite. Run them from a scratch working directory; builders read
ShipLoop's current prompt text from this checkout, so rerunning after a prompt
change gives a before/after comparison.

| Experiment | Build | Run | Score |
| --- | --- | --- | --- |
| E0 code composition | `composability/build_code.py` | `claude -p` per prompt | `composability/score_code.py` (AST) |
| E0 plan composition | `composability/build_plan.py` | `claude -p` per prompt | read by hand |
| E1 architecture | `battleship/build_architecture.py` | `battleship/run1.sh` | `battleship/judge1.sh` with `judge.txt` |
| E2 discovery | `battleship/sample-prompts/prompts2_*` over `fixtures/gas`, `fixtures/sf` | `battleship/run2.sh` | inline regex, see results doc |
| E3 intake | `battleship/sample-prompts/GAS_intake_*` | `claude -p` per prompt | `battleship/judge_intake.txt` |
| E4/E5 lifecycle v2 | `battleship/build_lifecycle_v2.py` (`life2.txt`) | `claude -p` per prompt | `battleship/judge4.sh` with `judge4.txt` |
| E6 research claims | `battleship/build_platform_claims.py` | `battleship/run6.sh` | `battleship/judge6.sh` with `judge6.txt` |
| E6b planning review | real E1 plans with errors plus the planning review focus | `claude -p` with web tools | `battleship/judge6b.txt` |
| Rerun after implementation | `after/build_after.py` (reads the E3, E6b and E7 prompts and `build.py`/`build4.py` from the original `EXP_DIR`; `SHIPLOOP_WT` = the checkout to test) | `after/run_after.sh` | `after/score_after.py` → `after/verdicts_after.json` |
| E7 layered conventions | `battleship/build7.py` (`layered.txt`, `layered_props.txt`, `trace_bullet.txt`) | `battleship/run7.sh` | `battleship/judge7_gas.txt`, `battleship/judge7_sf.txt` |

Environment variables: `EXP_DIR` (the scratch working directory, default the
current directory) and `SHIPLOOP_ROOT` (`skills/shiploop` in this checkout).

Fixtures: `battleship/fixtures/gas` and `battleship/fixtures/sf` are the
browser-only Battleship projects for E2; `battleship/fixtures/sf-layered` is the
Salesforce project with an in-house layer for E7. The E7 Apps Script fixture was
built from the private repository `whichguy/gas-tic-tac-toe` at `7d56d8e`:
its tracked files without `.shiploop/`, `SHIPLOOP.md` and `.mcp-gas/`, with the
script ID, deployment ID and domain replaced by examples, placed at
`$EXP_DIR/fx7/gas`. `candidate-apps-script-card.md` is the Apps Script platform
card with the tested mcp-gas-deploy section appended; the published card is
unchanged.
