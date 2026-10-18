# Template review brief (read-only, 2026-10-18)

ShipLoop is an SDLC harness. Scripts navigate a stage graph and print one prompt ("packet") per stage. A model, often in a
fresh context, does that one stage and calls `complete`, and ShipLoop's gates accept or refuse its result. The run-insights
plan (`/Users/dadleet/src/skill-craft/docs/shiploop-run-insights-plan-2026-10-18.md`, theme N1 and sections 6 to 8) moves
every packet into one template file per stage. The fixed text lives in the template, the script fills declared slots, and
the result form at the end is the schema the gate parses. Two stage templates and eight shared partials are drafted:

- `T = /Users/dadleet/src/skill-craft/docs/experiments/run-insights-2026-10-18/templates/`
  - `step-plan.template.md`, `implement.template.md`: front matter (consumer, flags, slots, pools, row formats, result
    table with gate ids), then the body
  - `step-plan.filled.md`, `implement.filled.md`: each template rendered with the Battleship run's real data. This is
    what a model would read.
  - `partials/`: frame, loop-invoke, loop-result, rules, result-rules, appendix, code-craft-titles, code-craft
- The design and its measurements: `/Users/dadleet/src/skill-craft/docs/experiments/run-insights-2026-10-18/packets-audit.json`
  (`template_option`, `duty_review`, `headline_findings`).

**Sources of truth:** `R = /Users/dadleet/src/skill-craft` (main, current).
- Gates and packet code:
  - `R/skills/shiploop/scripts/shiploop_navigator.py`: `_stage_gates`, `_check_text`, `_checked_line`,
    `_result_contract_lines`, `_result_template`, `HANDOFF_PLACEHOLDERS`, `_step_proof_gate`, `_lint_gate`, `step_block`,
    `_implement_scope`, the `complete` / `--check-only` path, and the Improve start
  - `shiploop_expectations.py`: `check_step_plan`
  - `shiploop_loops.py`: contract building, `check_terminal`, `WORK`/`REPEAT` and the invoke lines
  - `shiploop_test_loop.py`: `step_proof`
  - `shiploop_prompts.py`: today's `DUTIES`, `STAGE_RULES`, `CODE_CRAFT`
  - `shiploop_stage_spec.py`: done_when, outcomes, `GENUINE_FIX_ATTEMPTS`, `MAX_REVISES`
- The vendored Until Loop runtime: `R/skills/until-loop/scripts/` (receipt statuses, done report fields, next_argv).
- Hook parsers that read packet lines: `R/skills/shiploop/scripts/shiploop_status_hook.py`, the keepalive hook,
  `R/test/shiploop-head-order.test.py`.

**Live evidence:** the Battleship run printed today's packets for the same stages. The files are under
`SP = /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/report-bs/in/`.
- `11-step-plan.*`: packet, result, and actions (what the model said and did: SAY, CALL, OUT)
- `16-implement.*`, `18-implement.*`, ...: implement steps
- `*-improve-*`: Improve files
- Analyses: `R/docs/experiments/run-analysis-2026-10-18/` and `R/docs/experiments/packet-review-2026-10-17/`
- **Never open a `*.transcript.md` file and never quote the model's raw reasoning.** Use `.actions.md`. A safety filter
  stops agents that do.

**Owner rules to judge against:**
- Context is cleared between stages, so each packet must work alone.
- Packets are concise and printed whole (Grok cuts a print over 20,000 characters, losing its middle).
- Reference long unchanged text; do not reprint it.
- One wording per rule.
- Scripts own state; the model does one step and reports.
- Clear allowed outcomes. Plan N5 replaces revise with send-back and replan with add-work, and drops repeat.
- One step at a time.
- Test the route, not the wording: a named exit must be accepted by the real gate.
- Generic, not tailored to one app.
- KISS.
- Every output names its consumer.

**You are READ-ONLY.** Edit nothing in R. Run no ShipLoop command that writes state. You may run read-only Python
(`python3 -c` importing the modules) and `git grep`/`git log`. Cite every claim with a file and a symbol or quoted text
(never a bare line number), a run file, or a command you ran.

**What to decide, for every block and every line of your file(s):**

1. **Sufficient:** can a model in a fresh context do the stage correctly from this print alone? Check that:
   - every rule a gate on this stage can refuse is stated in the packet, as the frame claims ("this packet states every
     rule its gates apply"). Enumerate the gate's refusals from the code and map each to template text, or mark it
     missing;
   - every input the work needs is quoted or reachable;
   - every allowed outcome has its exact shape and is accepted by the real gate;
   - every command it must run is present and correct, including the callback, `--check-only`, the loop start or
     resume, lint and the Proof.

   Flag any slot whose source does not exist in today's state (a planned feature) and say what renders if it is absent.
2. **Necessary:** for each block and line, name who consumes it and what failure it prevents. Flag text no consumer
   needs, text that repeats another block or a partial (a rule stated twice), and text that does not apply to this
   stage.
3. **Confusing:** flag contradictions within the template or with a partial, ambiguous or undefined terms, mixed
   vocabulary, and instructions whose order fights the work. Examples of mixed vocabulary: loop stop status vs result
   outcome, blocked vs revise vs send-back, "done" in three senses.
4. **Would cause problems:** flag anything that would make a run fail, loop, stall or be refused. Examples:
   - an instruction the gate or runtime refuses (for instance, `--check-only` while the loop receipt is still active);
   - an Until Loop argument that differs from the contract ShipLoop builds and compares (`check_terminal`);
   - a print over budget, or the host cut at 20,000;
   - a placeholder rule the example itself breaks;
   - a hook line moved;
   - outcome names the gate does not accept.

**Output:** write `SP/../tmpl-review/<your-name>.json`, that is
`/private/tmp/claude-501/-Users-dadleet-src-skill-craft/8acf399b-0cf4-40cc-bba3-bf238461db58/scratchpad/tmpl-review/<your-name>.json`,
with:

- **`blocks`:** for each block in print order:
  - `name`
  - `chars` (approximate)
  - `consumer`
  - `necessary`: yes, partly or no, with the reason
  - `sufficient`: yes, partly or no, with the reason
- **`gate_map`:** each refusal the gate code can raise for this stage:
  - its symbol or message
  - where the template states it, or "missing"
- **`findings`:** each with:
  - `id`
  - `category`: insufficient, unnecessary, confusing or problem
  - `severity`:
    - P0: breaks or stalls a run, or a gate refuses a route the packet offers
    - P1: likely wrong work or a wasted iteration
    - P2: friction or a cost
    - P3: polish
  - `where`: block plus a short quoted line
  - `evidence`: code symbol, run file or command output
  - `fix`: exact replacement text, or "delete"
  - `confidence`: high, medium or low
- **`verdict`:** sufficient (yes, partly or no), necessary (yes, partly or no), a one-paragraph summary, and the three
  changes that matter most.

**Owner question (2026-10-18), for every reviewer:** should the folder symbols (RUN, WORKTREE, HOME, GUIDES) look like
variables rather than bare words, for example `<HOME/>`? Note each place your file's symbols could be misread. Examples:
- HOME read as the shell's `$HOME` or the user's home directory;
- RUN read as the verb;
- a symbol copied literally into a shell command, so `mkdir RUN/scratch` makes a directory named RUN;
- a symbol confused with a `<...>` placeholder the model must fill, or with a `{{slot}}` the script fills.

The partials reviewer owns the full answer: put it in `symbols` in its JSON. It covers:
- **Today's conventions:** the frame's Symbols line, prose paths, and absolute paths in commands.
- **Live evidence:** grep the Battleship and chess `.actions.md` files for commands or writes that used a literal `RUN/`,
  `HOME/`, `WORKTREE/` or `GUIDES/` path, and say what happened. The chess files are under `SP/../report-chess/in/`. Check
  the run folders `/Users/dadleet/e2e-runs/20261017/bs-sf-int-b7c77f` and `/Users/dadleet/e2e-runs/20261017/salesforce-chess-int-802e29`
  for stray directories named RUN, HOME, WORKTREE or GUIDES.
- **Options:**
  - bare word;
  - `<HOME/>`;
  - `$HOME_DIR`-style;
  - a distinct sigil;
  - absolute paths everywhere.
- **Criteria for each option:**
  - collision with the result form's `<...>` placeholder rule (`HANDOFF_PLACEHOLDERS`, the placeholder gate) and with the
    template's `{{slot}}` and `<action>`-style fill-ins;
  - what a shell does with it if copied literally;
  - character cost: `measure.path_overhead` in packets-audit.json;
  - how hooks and the Until Loop runtime read paths.
- **A recommendation**, with the exact Symbols line it implies.

Return a 12-line summary. Prefer verifying a suspected P0 in the code over guessing. Say "not verified" when you could not.
