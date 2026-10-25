# DeepSeek Flash review of ShipLoop 1.9.0 (2026-10-24)

**Question.** Asked to review ShipLoop's scripts and prompts, what would an outside model change? The owner
wanted specific plans in ranked order.

**Setup.** `deepseek-v4.1-flash:1017-cloud` (Ollama cloud, thinking `high` by default) ran as the model inside
headless Claude Code 2.1.310:

- connection: through Ollama 0.40.11's native Anthropic endpoint (`ANTHROPIC_BASE_URL=http://127.0.0.1:11434`);
- permissions: `--permission-mode bypassPermissions`, with every built-in tool, as the owner asked for no restrictions;
- MCP: `--strict-mcp-config`, so no connectors, because those include a brokerage account and email;
- workspace: a detached worktree of `origin/main` 31933a73 (skill-craft 2.9.0, ShipLoop 1.9.0).

The brief is [brief.md](brief.md): ShipLoop's purpose, its eight tenets, where to read, and the
report format. The run took 16.6 min, 164 turns and 161 tool calls ([run-summary.txt](run-summary.txt)). It
changed no repository file. Its report is [REVIEW-deepseek.md](REVIEW-deepseek.md), and its two probes are in
[probes/](probes/).

**How I checked it.** I re-opened every cited `path:symbol` at 31933a73 and re-ran both probes on the same
worktree. I also searched the docs for prior proposals. Status: **firm** for what was re-run or re-read; the
savings are **interim**, inferred and unmeasured in a live run.

The verdict column below is the first pass, which checked citations only. The live-run check in the next
section **supersedes** it (2026-10-24): it measured value, not just correctness.

| # | Recommendation | Check | Prior art | Verdict (first pass, superseded) |
|---|---|---|---|---|
| 1 | Reuse a passed base run and mutation check, as the candidate run already is | Re-run of `probe_base_mutation_reuse.py`: red-check 2, `complete --check-only` 8, `complete` 6 command runs, 8 of 16 repeats. `_base_run` and `shiploop_mutation._check` have no reuse; only `_reused`/`verify` do | Mutation half = **C4** in `docs/experiments/run-insights-2026-10-18/fix-catalogue.json`, status `open`, never built. Base-run half is new | Adopt steps 1, 2, 4 and 5. **Drop step 3** (no mutation check in check-only): packets promise that `--check-only` prints the refusal `complete` would give. With reuse, `complete` takes the last check-only mutation record, so step 3 saves little |
| 2 | A materiality bar for planning documents in Improve | Quotes confirmed (`skills/improve/references/shiploop-route.md` trivial classification; `review-policy.md` stop rule; LEARNINGS run 4 and Battleship) | **F4** in `docs/experiments/battleship-grok-2026-10-18/inefficiency-analysis.md` (est. 10–12 min), never shipped | Adopt. Run 4 already had the 2026-10-20 one-trivial-pass stop rule (5e377ff7 is in 2.8.0), yet planning Improve still took 46.6 of 78.8 min, so the stop rule alone did not fix it. Choose one home: the route card or the `shiploop_prompts.py` focus that F4 names |
| 3 | Dependency directories from the platform cards, not `DEPENDENCY_DIRS` | `shiploop_test_loop.py:DEPENDENCY_DIRS = ("node_modules", ".venv", "venv")` confirmed. The card parser exists (`shiploop_mutation.remote_test_commands`) | none found | Adopt as a genericity fix (tenet 3). The stuck-run harm is inferred: no live run shows it |
| 4 | A `not-run` base refusal states the exit code when no test line was printed | Re-run of `probe_base_start_failure.py`: `exit(3)` gives `not-run` with test-writing advice and no exit code | none found | Adopt. Cheap |
| 5 | Drop `pytest -v; python -m unittest -v; jest --verbose` from the `unread` refusal | Text confirmed in `_explain_base` | commit 6051924c did the same for the file guard | Adopt **with a correction**: no card names those reporters (only `node-express.md` and `salesforce.md` cover reporters). Move them into `python.md` and a JS card first, or the advice is lost |

**Also found (rejected by its ranking rule, but real):** `graph-dry-run` prints "The loop contract is
missing; report outcome blocked naming this path." in all 42 packets (`shiploop_loops.py:invoke_lines`).
`dry_run` renders the packets without the emit step that writes the contract. This misleads anyone reading
dry-run packets, not a live run.

**Harness finding.** The Ollama-in-Claude-Code route worked: it read files, ran the module's 161 tests and
wrote its own probes. Three conditions mattered:

- the user's `defaultMode: auto` let a write through until a permission mode was passed explicitly;
- under `--bare` the model had no Glob or Grep;
- stderr carries a harmless `unrecognized_model` line.

Building this into `ask-ollama` is a separate session in grok-build-additions.

## Second look: are they worth doing? (2026-10-24, live-run evidence) — status: firm for the counts, interim for the verdicts

**Question.** The citations hold. Does each fix pay off on real runs? The ranking rule is quality first, then
tokens, then time. The data comes from three saved live runs under `/Users/dadleet/e2e-runs/`:

- chess run 4: `20261020/chess-sf-full-9e52e8`, 2.8.0, which already had the one-trivial-pass stop rule;
- chess run 3: `20261019/chess-sf-full-05fe25b`;
- Battleship: `2026-10-18/battleship-1`.

I read every `run/tests/*.md` record (each run's `seconds` and the mutation record's `seconds`), every
`run/improve/*/passes.md`, and the work repo's planning-stage commits.

| # | Evidence | Verdict |
|---|---|---|
| 1 Reuse base run and mutation check | Total command time per 4-hour run. Run 4: base 0.2 min, red-check 0.8 min, mutation 0.0 min (skipped: remote commands). Run 3: mutation-check-only 3.4 min, mutation 3.9 min, base ~0. Battleship: about 0.6 min. The reuse could save at most ~3.4 min of a 240-min run (≈1.5%). The review's "tens of minutes per item" assumes a slow local suite that no run has had | **Defer.** The cache key would be a new way to wrongly accept stale work (a quality risk) for a time gain that no run has shown. Revisit when a run's test-stage command time is a large share of its wall time; C4 stays in the backlog |
| 2 Materiality bar for planning documents | Run 4 planning Improve: spec 3 passes, test-strategy 4, plan 2; 6 passes changed the document. All 6 commits were substantive oracle and check fixes: `dda7d6f` replayable FEN oracles, `bac983e` remaining castling/pin/en-passant oracles, `490f449` checks reject a weaker stand-in, `2916ee4` require the tab, not a mention, `d9465b5` compare whole FENs, `8569b0e` correct the tab check. The review's wording still calls each of these material, so it would have saved 0 passes. F4's wording ("more exact oracles … are polish") would save them, but by giving up test quality | **Don't do it.** As worded it changes nothing measurable; the version that saves time costs quality. The waste the 10-16 study found (polish labelled non-trivial, non-trivial labels without edits: run 3 step-plan had 6) had mostly gone by run 4 under the 10-20 stop rule (2 such passes) |
| 3 Dependency directories from cards | No live run hit it (Salesforce and Node projects). It is a tenet-3 leak of the same kind as the reverted Apex globs and the removed `existsSync` | **Yes, but not urgent.** Do it with the next path-catalog rework, alongside the Salesforce patterns the owner asked to leave noted (2026-10-24) |
| 4 Exit code in the `not-run` refusal | One `not-run` base record across the runs (run 3 `…f27b4e99…-red-check.md`). It was a file-existence guard that hit an `assert` before printing (`exit 1`, traceback on stderr): it ran, but asserted a path, not behaviour. The proposed "it never reached the tests" would have misdiagnosed it; the existing advice already covers it | **Reduced version only.** Add the exit code and the stderr tail to the refusal; do not claim the command never started |
| 5 No ecosystem names in the `unread` refusal | No `unread` refusal in any live run (the grep hits in the E2/E3/E6 experiment folders are a model reading the source). The text names pytest, unittest and jest, and no card carries them | **Yes, cheap.** Move the reporter examples into `python.md` and a JavaScript card, then shorten the refusal. Bundle with 3 |

**Net.** Two cheap genericity fixes are worth doing (5, then 3), plus the reduced 4. The two
time-saving ideas DeepSeek ranked highest don't hold up against the run data: 1 saves too little, and 2 saves
nothing unless it gives up test quality. Lesson for outside reviews: the reviewer measured the mechanism
(command counts) but not its live cost, and it scaled a fixture count with the journal's per-item call count.
Rank by measured live minutes before adopting.

## Built (2026-10-24, owner go: "build fix 5, fix 3 and the reduced fix 4") — status: firm for the tests listed

Branch `fix/shiploop-generic-test-advice-320e96`, off `origin/main` 5f71657f, one commit per fix so each can be dropped.

- **Fix 3: dependency directories from the cards.** `shiploop_mutation.dependency_directories` reads
  `## Dependency directories` through `_card_bullets`, the same reader `remote_test_commands` now uses.
  `shiploop_test_loop._BaseTree._make` links what it returns, and `DEPENDENCY_DIRS` is gone. The Node and Python cards
  list the same three names, so the result is unchanged on today's stacks. Tests: the real cards give
  `["node_modules", ".venv", "venv"]`; a focused test importing from an ignored `vendor/` reads not-run on the base until
  a card lists `vendor`, then RED.
- **Fix 4, reduced: the exit code.** The refusal already printed the output's last 15 lines (`_base_run`), so the
  stderr part of the review's plan existed. Only the exit code and an empty-output note were missing. The `not-run`
  explanation now starts `exited <n>[ and printed nothing]: it did not run …`, with no diagnosis, and the existing
  wording and its test pins are unchanged. The review's probe (`sys.exit(3)`) is now a test.
- **Fix 5: the unread refusal points at the card.** The refusal drops "pytest -v; python -m unittest -v; jest
  --verbose". `python.md` names `pytest -v` and `python -m unittest -v`, and `node-express.md` names Jest's `--verbose`.
  **Correction to my earlier ranking:** I called these names a breach of the genericity rule. In fact D-13
  (`docs/shiploop-efficiency-plan-2026-10-16.md`, section 11, and the `test/domain-words.json` comment) kept generic runner
  examples on purpose. This commit departs from D-13 for this one refusal only, at the owner's 2026-10-24 go. The
  step-plan duty in `shiploop_prompts.py` ("Jest `--verbose`, pytest `-v`, others: GUIDES/platforms/") and the runner
  readers in `shiploop_test_counts.py` still name runners under D-13, so the step-plan duty and this refusal now differ
  in style. Drop this commit to keep D-13 everywhere.
