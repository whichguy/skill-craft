# Question-driven planning: journal

Living journal for the owner's 2026-10-30 question: should ShipLoop's planning (intake through step-plan) be driven by
key questions about the request, and what else should change in its prompts, Until Loop use, stages, graph and state
files. The proposal and the stage-by-stage reference are in
[docs/shiploop-planning-pipeline-2026-10-30.md](shiploop-planning-pipeline-2026-10-30.md). Evidence lives in
[docs/experiments/key-questions-intake-20261030/](experiments/key-questions-intake-20261030/). The illustrated pages
are the planning map, https://claude.ai/artifact/BvpneLuojWv7Le1M7CEdnP, and the outcome summary,
https://claude.ai/artifact/QbP7gaR9x2gW2yUKkWMW1t (E4); both are private to the owner.

This work designs the owner's open TODO of 2026-10-11 ("plan → key questions → research/experiment Until Loops →
revised plan + test spec → build → test Until Loop"), which needs the owner's go before anything is built.

Statuses: **firm** (measured, replicated or by construction), **interim** (measured once, small n), **exploratory**
(a pilot or a reading), **superseded** (kept, with the date and reason).

## Entries

### E1 — 2026-10-30: the planning path as shipped (reading, no model run)

- Question: what does each planning stage get as its prompt, what does it write, and what checks it?
- Method: read the stage table (`shiploop_stage_spec._ROWS`), the duties (`shiploop_prompts.DUTIES`), the knowledge
  tables (`shiploop_knowledge_home.STAGE_FILES`, `READS`, `CLOSES`), the inner-stage loop texts
  (`shiploop_loops.WORK`, `REPEAT`) and the gate list (`shiploop_navigator._stage_gates`); rendered every packet with
  `shiploop graph-dry-run --scenario delivery --format markdown` on main `d47d69d4` (synthetic results, no model).
- Result: §2–§4 of the proposal document. Prelude stages are single-pass with self-confirmed done-when and
  structural gates; only inner stages run as script-written Until Loops; the first structured, gated record of a
  question is plan's `assumptions`.
- Findings: F1, F2, F6 below.

### E2 — 2026-10-30: pilot X1, key questions at intake (exploratory)

- Question: on an underspecified request, does asking intake for key questions surface more of the decisions the real
  request pins, at what cost, and does a fixed category catalog add to a free-form ask?
- Test cases: battleship, csv-report, seat-reservations and user-listing from `test/shiploop_e2e/cases.json`, each cut
  to a one- or two-sentence request (`cases.json` in the evidence folder); ground truth = the 38 decisions the full
  prompts pin and the short ones leave open.
- Arms: A, the shipped intake duty (`shiploop_prompts.duty("intake")` on `d47d69d4`); B, A plus a key-question item
  with a K1-K11 category catalog and a `questions` ledger; C, the same item and ledger with no catalog. Frames
  byte-identical otherwise.
- Model and effort: Claude Sonnet 5.5 (`claude-sonnet-5-5`, served model verified), xhigh, through the `ask` runner
  (subscription Claude Code CLI, fresh headless session per call, empty working directory). Two samples per case and
  arm: 24 calls (52-215 s each), plus one excluded smoke call. Judge: Claude Opus (`ask opus`, xhigh), one blind call per
  case with outputs shuffled and relabelled; a decision counts only if the judge's quote is found in the output.
- Result: recall A 0.932, B 1.000, C 0.986; committed defaults matching the real request A 0.77, B 0.64, C 0.74;
  judged noise A 27%, B 21%, C 23%; output 7,214 / 16,662 / 12,427 characters; 70 / 139 / 106 s. B vs A +0.068
  (exact permutation p 0.077, optimistic); C vs A +0.054 (p 0.23); B vs C +0.014 (p 1.0). All 24 judge quote sets
  verified. On the brownfield case both ledger arms routed most questions to `inspect` before any default.
- Reading: surfacing is near ceiling on this subject; the catalog adds cost and commits more intent guesses that
  contradict the real request, not coverage. Not tested: a weaker subject (DeepSeek flash was at its monthly limit),
  downstream use of the record, real repositories.
- Status: exploratory (n = 2 per cell, one subject, one judge).
- Evidence: `docs/experiments/key-questions-intake-20261030/` (`README.md`, `cases.json`, `build.py`, `prompts/`,
  `outputs/`, `judge/`, `score.py`, `scores.json`).

### E3 — 2026-10-30: outside frameworks and literature (reading)

- Question: how do other planning frameworks turn a request into steps and ask questions, and what does published
  evidence say about asking or answering key questions before planning?
- Method: three Sonnet research agents read each framework's own source files at named versions (BMAD v6.12.4 and v7
  alpha, Spec Kit v1.2.5, Kiro docs, cc-sdd v3.1.0, OpenSpec v1.16.0, GSD Core v1.19.0, Superpowers v7.0.1, Agent OS
  v3.0.0, Taskmaster 0.43.1, PRP, SPARC) and the papers (graded A to E); a fourth digested this repository's own
  planning measurements and decisions. No framework was run.
- Result: no framework measures whether its questions help; one vendor benchmark (Uvik, ±10 points) shows specs help
  only on features touching 3+ files; with an answer oracle, asking closes most of the underspecification gap, without
  one gains are smaller (corrected 2026-10-31 in E4: "single-digit" held for SpecFix only); models commit to early assumptions; implicit requirements in interfaces, conventions and
  invariants are the largest failure component of autonomous agents.
- Evidence: `frameworks-a.md`, `frameworks-b.md`, `question-evidence.md`, `planning-history.md` in the evidence
  folder.
- Status: firm as a reading of sources; the numbers are the sources' own.

### E4 — 2026-10-31: an outcome page drawn by Sonnet, and three corrections found while checking it

- Question: can a second model illustrate what this study achieved and found, faithfully, from the committed files
  alone? (The owner asked: "Ask sonnet to provide illustration of what was achieved and discovered".)
- Method: one Claude Sonnet 5.5 subagent (default effort; 81 tool calls, about 343k tokens, 15.3 min) got the owner's
  verbatim request, the source list and the artifact page contract, and built a static page with no script. Its X1
  figures and tables are computed from `scores.json` and `cases.json`; its counts are read from git. It validated the
  X1 palette in light and dark (`validate_palette.js --pairs all`: all checks pass, with one light-mode contrast
  warning, 2.82:1 for `#1baf7a`, relieved by the A, B and C labels; the main session re-ran it with the same
  verdicts) and looked at headless Chrome captures at 1280 px (light, dark) and 390 px. The main session (Claude Opus
  5.5) then checked the page's numbers and claims against the files, corrected the page's wording, looked once at all
  three widths, and published it: https://claude.ai/artifact/QbP7gaR9x2gW2yUKkWMW1t.
- Result: every number on the page matched its source: the study commit (86 files, 4,486 lines, all under docs/), the
  file line counts, X1 per-case recall, the arm table, the Uvik size buckets and the Ask-or-Assume bars. Its errors
  were wording of two kinds. Some claims went past the source: "checks every exit" beside F1; "the only route that
  needs a default"; "its build waits on X5", where §7.6 says the loop is adopted only if X5 pays. Other labels collide
  across documents: F3's RE1, X1 and X2, and X5's "D5 permutation rule", name items of other proposals, not this
  study's X1, X2 or D5. A page drawn from these files should name the source of a borrowed label.
- Corrections to this study's committed files, found while checking the page:
  1. F2 quoted "a file in the repository is not consumed; a quoted, numbered question is", which is a paraphrase made
     in `planning-history.md`, not the source's words. The brownfield journal's F12 says "A baseline in the
     repository is not consumed by being there". Fixed in the pipeline doc §6.1 and in `planning-history.md`.
  2. F5 (and E3 above) said that without an answerer, gains are "single-digit (SpecFix +4.3%) at up to 26x the
     tokens". The 26x belongs to REA-Coder, whose gains are +7.9% to +30% relative (`question-evidence.md` §0 item 2
     and §2.4). F5 now reads "smaller (SpecFix +4.3% Pass@1; REA-Coder +7.9% to +30% relative at about 26x the
     tokens)". The conclusion stands: without an answerer, gains are smaller and cost more.
  3. §2.1's Checked-by row pointed at "finding F6"; the finding is F11.
- Status: firm (each correction is a direct reading of the cited source).

## Findings

Each finding is stated in full, with its evidence, in §6.1 of the proposal document.

| # | Finding (short) | Status | Since |
|---|---|---|---|
| F1 | Prelude stages end on the model's word; planning iteration comes from Improve (53-58% of DeepSeek planning windows) | firm | E1 |
| F2 | A question has no record until plan; prose loses it (Checkers stale decision; brownfield X3 unconsumed baseline) | firm mechanism, interim harm | E1 |
| F3 | The owner's accepted brownfield D9 (`Q-<n>` quoted by value, answered by ID) is the same mechanism; RE1, X1, X2 add it piecewise | firm | E1 |
| F4 | On Sonnet 5.5 the shipped intake already surfaces 93% of omitted decisions; a catalog adds cost and wrong guesses | exploratory | E2 |
| F5 | Without an intent oracle, gains from questions are small and early assumptions persist | firm (literature) | E3 |
| F6 | Implicit requirements in interfaces, conventions and invariants dominate autonomous failures and are repository-checkable | firm (literature, grade C) | E3 |
| F7 | Plan-time experiments are unused live; research's prose allowance conflicts with the no-caps rule | firm | E1, E3 |
| F8 | 42% of acted planning findings were missing content, the class questions could move earlier (unmeasured) | interim | E1 |
| F9 | Step planning's measured failure is Proof order (SG1/D6 in flight) | firm (two live cases) | E1 |
| F10 | Plan and step-plan packet heads are at their print bound; a quoted record belongs in the packet file | firm | E1 |
| F11 | Intake's Checked-by line omits IN1 | firm (small) | E1 |
| F12 | `Basis: S<k>` (brownfield D2) would be unresolvable in a later run: no durable request text | firm (design) | E1 |
