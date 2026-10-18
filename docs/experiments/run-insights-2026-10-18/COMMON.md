# Common brief for the plan-revision audits (2026-10-18, read-only)

ShipLoop is an SDLC harness: scripts navigate a stage graph and print a prompt ("packet") per stage; a model does one
stage and calls `complete`. The owner is revising the run-insights plan
(`/Users/dadleet/src/skill-craft/.claude/worktrees/shiploop-eff-int-c5f79b/docs/shiploop-run-insights-plan-2026-10-18.md`,
read it first) after two live runs in a Salesforce org. You are READ-ONLY: edit nothing anywhere; run no `sf`, no tests,
no ShipLoop command; read files and `git grep`/`git log` only.

Sources:
- Source code (integration branch, current): `R = /Users/dadleet/src/skill-craft/.claude/worktrees/shiploop-eff-int-c5f79b`
  — `skills/shiploop/scripts/` (shiploop_navigator.py, shiploop_prompts.py, shiploop_stage_spec.py, shiploop_loops.py,
  shiploop_test_loop.py, shiploop_workspace.py, shiploop_mutation.py, shiploop_expectations.py ...), `skills/shiploop/references/`,
  `skills/improve/`, `test/shiploop_e2e/`.
- Runs (the chess run used an older build; Battleship used the current integration branch):
  chess `/Users/dadleet/e2e-runs/20261017/salesforce-chess-int-802e29`, Battleship `/Users/dadleet/e2e-runs/20261017/bs-sf-int-b7c77f`
  (each: `.shiploop-runs/work-*/run` = run records, `.shiploop-runs/work-*/worktree` = the product checkout, `work/` = the user
  checkout, plus harness files).
- Step layouts: `SP = /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad`;
  `SP/report-chess/in/` and `SP/report-bs/in/` hold per step `<NN>-<stage>.packet.md` (the prompt), `.result.md`,
  `.actions.md` (what the model said and did: SAY, CALL, OUT), Improve files; `index.json` beside them. **Do not open any
  `*.transcript.md` and do not quote the model's raw reasoning** (a safety filter stops agents that do); use `.actions.md`.
- Analyses already done: `R/docs/experiments/run-analysis-2026-10-18/` (per-group analysis JSON, sdlc-audit.json),
  `R/docs/experiments/packet-review-2026-10-17/` (A-F packet reviews), reports' fix lists in
  `R/docs/experiments/run-analysis-2026-10-18/tools/meta-*.json`.
- Owner rules to respect (name a conflict if a proposal breaks one): the main tenet (context is cleared between stages; each
  packet must work alone); compact packets printed whole; reference, do not reprint unchanged long text; one supported
  version (no compatibility shims); test the route, not the wording; KISS; produce for a consumer (every output names its
  consumer, when it reads it, in what form); scripts own graph position and state, the model does one step and reports done;
  generic fixes only (platform detail only in `references/platforms/`).

Cite every claim with a file and symbol (never a bare line number), a run file, or a command you ran. Measure where you
can (counts, bytes, minutes). Write your output file as named in your task and return a 12-line summary.
