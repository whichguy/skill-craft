# Question-driven planning: journal

Living journal for the owner's 2026-10-30 question: should ShipLoop's planning (intake through step-plan) be driven by
key questions about the request, and what else should change in its prompts, Until Loop use, stages, graph and state
files. The proposal and the stage-by-stage reference are in
[docs/shiploop-planning-pipeline-2026-10-30.md](shiploop-planning-pipeline-2026-10-30.md). Evidence lives in
[docs/experiments/key-questions-intake-20261030/](experiments/key-questions-intake-20261030/). The illustrated pages
are the planning map, https://claude.ai/artifact/BvpneLuojWv7Le1M7CEdnP, and the outcome summary,
https://claude.ai/artifact/QbP7gaR9x2gW2yUKkWMW1t (E4), and the verdicts of 2026-10-31,
https://claude.ai/artifact/S5r3siGPAJWkAEszTqDwwT (E5-E11); all are private to the owner. The verdicts and the
improvement plan: [docs/shiploop-question-record-verdicts-and-plan-2026-10-31.md](shiploop-question-record-verdicts-and-plan-2026-10-31.md).

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

### E5 — 2026-10-31: SG1's replay on the saved runs, and the proof-order refusal (D6) it supports

- Question: SG1 (`docs/shiploop-sdlc-gates-proposal-2026-10-30.md` §5) asks whether a static check at step-plan
  catches a step whose Proof cannot run when its implement completes. Its verdict "needs the owner's full saved runs
  (~/e2e-runs), which this container does not have"; this machine has them. X4 (§9.2) waits on it.
- Method: the SG1 tool unchanged (`docs/experiments/sdlc-gates-20261030/sg1_proof_order.py`, self-test 12 cases pass)
  on its corpus `~/e2e-runs/2026*/*`, read-only; then on a held-out corpus (the saved runs outside that glob); then a
  classification of every implement send-back in both corpora by its accepted summary; then the SHIPPED rule
  (`shiploop_item_scope.proof_order_refusal`) replayed on every accepted step plan at its base commit
  (`sg1/replay_d6.py`).
- Result:
  - Proposal corpus: 111 runs, 141 step plans, 42 steps judged, 60 unjudged, 2 flags. Bar item 1 met (DeepSeek
    battleship W1 of 2026-10-26 flagged, rule A, `test/game.test.js`, then a send-back). Bar item 3 missed on its
    letter: `20261029/pilot-terra-ask-agent-32f436` W1 S1 is flagged (rule A, `test/records.test.js`, git mode) although
    its implement was done. Its implement summary says "Proof passed all three cases": implement wrote the tests the
    Proof ran, against its own duty ("Write no tests"). Bar item 2 is not assessable (no chess plan in the corpus has
    a judged step with an S4).
  - A post-hoc refinement (exempt a test path the step itself declares) separated the two flags but fails the
    held-out corpus: it drops `bf-codex-r1-ticket-escalation` W1, whose send-back reads "C1 proof requires
    test/bulk-escalation.test.js, absent at item base, while implement explicitly forbids writing tests". Rejected.
  - Every implement send-back in the saved runs: 12. Nine are this fault (8 on Codex Terra 6.1 xhigh, all in the
    2026-10-29 brownfield rounds; 1 on DeepSeek flash); the other three are a chess oracle, an Apex exception type and
    a proof-command typo (`fs.rmSync` force:1). The prompt rule has been in the step-plan duty since 12151c49
    (2026-10-17: "It needs no later step, unwritten test or release artifact"), so the prompt alone does not stop it.
  - The shipped rule (rule A with an earlier-step exemption, rule B, paths outside the repository skipped) on 182
    plans in 142 runs (62 without a base to judge): 9 refused. Seven of those went on to exactly this send-back, one
    passed only by the contract breach above, and one had no implement after it. It refuses no plan whose implement
    passed by the rules. The first version refused a Proof that ran `../run/scratch/proofs/W1-S1.test.js` (a script in
    the run's scratch folder; `20261028/bf-ds-ticket-escalation-09c33b`); `command_paths` now skips paths that leave
    the repository. It misses two of the nine faults: `bf-codex-r1-user-listing` W1, whose Proofs (`npm test`, a scratch
    script) name no test path; the second send-back there was about criteria that demanded the test file.
  - Live, 2026-10-31: the baseline arm of the A/B (unchanged ShipLoop, Codex Terra 6.1 high, all tools) hit the fault
    on user-listing within four minutes: "S1 proof invokes test/user-listing.test.js before the test stage creates it;
    implement forbids writing tests" (`~/e2e-runs-qr/20261031/A-user-listing-s1`).
- Decision: build D6 as the owner approved it on 2026-10-30 ("If SG1 meets its bar, add the step-plan refusal"). The
  bar's item 3 is missed only by a plan whose Proof could pass solely by implement breaking its duty, which the
  refusal is right to stop; recorded here so the owner can veto.
- Status: firm (replay of every saved plan, two corpora, plus one live reproduction).
- Evidence: `docs/experiments/question-record-20261031/sg1/` (`replay-e2e-runs.jsonl`, `heldout-original.jsonl`,
  `heldout-refined.jsonl`, `implement-sendbacks.jsonl`, `replay-d6-shipped.jsonl`, `refined.py`, `replay_d6.py`).

### E6 — 2026-10-31: X1 on Codex Terra 6.1 high (X1-T), the subject the owner put in focus

- Question: does X1's verdict (no catalog; the shipped intake already surfaces most of what a vague request leaves
  open) hold on the subject the owner put in focus ("Focus using Terra 6.1 high for now")?
- Method: X1's prompts unchanged (`d47d69d4` duty), 4 cases x arms A, B, C x 4 samples = 48 `codex exec` calls
  (`gpt-6.1-terra`, `model_reasoning_effort=high`, throwaway CODEX_HOME linking only auth.json, read-only, no tools,
  from an empty directory outside any repository: X1's design, kept for comparability with its Sonnet results). Judge:
  Opus, X1's judge text, two calls per case; all 8 returned JSON, 0 unverified quotes. Pre-registered in ddd371ea.
- Result (n = 16 per arm): recall A 0.493, B 0.907, C 0.657; B vs A +0.414 (exact one-sided p < 0.0001), C vs A
  +0.164 (p 0.003), B vs C +0.250 (p < 0.0001). Committed defaults matching the full request: A 25 of 30 (0.83), B 93
  of 121 (0.77), C 55 of 82 (0.67). Output 1,932 / 7,692 / 3,859 characters; 9.7 / 20.5 / 12.8 s. Judged noise 2.9 /
  4.8 / 1.9 items. Terra high's shipped intake is terse: Sonnet's was 0.932 at 7,214 characters.
- Rules: D2 ("no catalog") does not hold on Terra (B beats C by 25 points); the intake wording reopens (C - A = +16).
- Status: firm for Terra high in the no-tool exercise; whether the gain reaches later stages is E9's question.

### E7 — 2026-10-31: X2, does a numbered record become requirements better than prose? (Terra high)

- Method: the shipped spec duty (main 3ae78af7) as a no-tool exercise in the packet's frame, discovery and research
  fixed per case; arms A (intake A's prose), D (the same plus one duty line: every open question and default becomes a
  marked acceptance line and a `## Open questions` entry) and C (intake C's ledger quoted by value plus the same line
  for Q-rows); 48 calls on Terra high, A and D paired on the same intakes. Judge: Opus, six outputs a call; 0
  unverified quotes. Pre-registered in ddd371ea.
- Result (n = 16 per arm): acceptance A 0.635, D 0.687, C 0.650; pinned 0.649 / 0.687 / 0.657; carried 0.789 / 0.808 /
  0.807; agreement 0.65 / 0.65 / 0.62; flagged as a default 0.79 / 0.92 / 0.89. C vs A acceptance +0.015 (p 0.44); D vs
  A +0.052 (p 0.28 unpaired, 0.008 paired). Spec carries about 0.8 of the decisions whatever intake hands it: A's
  terse intake (0.49) loses little by spec. What spec drops is mostly technology and structure (dependencies, port and
  entry, page identity, the rules module, test framework), which ShipLoop routes to test-strategy and plan (spec duty
  item 3: a technology choice is an AD-<n>). Conflicting defaults are interface contracts no stage can know from a
  vague request (output format, error codes, response shapes).
- Rules: phase 1 (the record) not adopted; the duty line alone not adopted (+5, below the pre-registered 10); prose
  does not carry 0.95 (A 0.79), but the record carries no more (C 0.81).
- Status: firm for Terra high in the no-tool exercise (n = 16 per arm). D1, D3, D4 and D6 of the proposal lose their
  basis on this subject; Sonnet and DeepSeek flash are not run.

### E8 — 2026-10-31: X4, the Proof-input question, has no isolated test that can measure it on Terra

- Method 1 (pre-registered): archived step-plan packets of the Terra runs that hit the fault, today's duty (A) or plus
  the Proof-input sentence (Q), no tools. Terra answered `blocked` in 64 of 64 calls ("cannot be verified in the
  exercise's no-tools environment"); with the loop and callback lines removed it still blocked: the packet lists the
  knowledge files by outline and does not quote them, so a step plan cannot be written from it alone.
- Method 2 (the owner: "we would use codex harness with terra high", "It should have all tools available"): step
  slices on the Codex harness (`slice.py --case tickets-assign --seed-at step-plan --stop-after step-plan --host codex
  --effort high`, Q by overlay). Both smoke slices (A 94 s; Q one refusal) planned clean proofs, and both copied the
  `node -e` proof the case's own seed records carry, so the slice cannot show the fault either.
- Decision: X4 closed without a prompt change. The step-plan duty already states the rule (since 12151c49); the
  measured fix is D6's refusal (E5), and its refusals per run in the live A/B are the measure a prompt sentence would
  have to lower.
- Status: firm that neither isolated design measures it; exploratory otherwise.

### E9 — 2026-10-31: effort is not the lever at intake; the catalog's gain reaches the spec (X1-T at xhigh, X2b)

- Question 1 (the owner, after X1-T: "If Terra high is too ineffective, bump it up in thinking levels if needed", then
  "My preference is to improve shiploop to handle this, but if it doesn't change then increase the thinking level"):
  does raising Terra's effort do what the catalog does?
- Method 1: X1-T's 48 calls again at `model_reasoning_effort=xhigh`, the harness's Codex default; judged the same way
  (8 Opus calls, 0 unverified quotes). Added after X1-T was scored, as a control; the same rules.
- Result 1 (n = 16 per arm): recall A 0.513, B 0.981, C 0.681 (high: 0.493, 0.907, 0.657). xhigh reasons about four
  times as much (A 268 reasoning tokens against 59) and writes the same terse intake (2,019 characters against 1,932).
  B vs A +0.467, C vs A +0.167 (both p < 0.002). Effort moves the shipped intake by 2 points; the prompt moves it by 41.
- Question 2 (X2b, pre-registered in the README before any X2b call): does intake B's ledger reach the spec, where X2
  showed C's did not?
- Method 2: the shipped spec duty fed intake B's result (B→spec) against X2's A→spec outputs, re-judged in the same
  calls (Opus, four outputs a call, 8 calls, 0 unverified quotes); 16 Terra-high calls.
- Result 2 (n = 16 per arm): carried A 0.776, B 0.897 (+0.120, exact one-sided p 0.013, paired sign-flip p 0.001);
  pinned 0.650 against 0.717 (+0.067, p 0.23, paired 0.02); acceptance 0.643 against 0.665 (ns); agreement 0.65 both;
  spec length and time unchanged (12,826 against 12,722 characters; 32.6 against 33.3 s). A's re-judged carriage
  (0.776) is within 1.3 points of its X2 judging (0.789). The gain sits where spec dropped decisions: battleship
  acceptance 0.25 to 0.39, with dependencies, the rules module and the test framework now carried.
- Rule: met (carried +12 points, p < 0.05, agreement held). The intake catalog is adopted for this subject, reversing
  D2 of 2026-10-30, which rested on Sonnet (X1: catalog +7 points at the ceiling, more conflicting guesses).
- Decision: build intake duty 9 and its template exactly as tested (X1's arm B text, byte for byte), with the ledger
  optional and checked only for its shape, as measured; all 32 Terra arm-B outputs pass that shape check.
- Status: firm for Terra 6.1 (high and xhigh) in the no-tool exercise; the live A/B is its tools-on check.

### E10 — 2026-10-31: the build, live: A/B on the Codex harness (Terra 6.1 high, all tools)

- Question: on the owner's runner with all tools, does the changed ShipLoop (ffea2956 and e7e0bc3c) plan without the
  proof-order send-back, keep its hidden checks, and write the intake ledger?
- Method: `run.py --case <case> --host codex --model gpt-6.1-terra --effort high --source checkout`, hooks on, output
  `~/e2e-runs-qr/20261031/`; arm A from a detached worktree at 3ae78af7, arm B from this checkout; ticket-assignment and
  user-listing (the brownfield cases where Terra xhigh hit the fault on 2026-10-29), one lane per port, arms
  interleaved, 3 runs per arm per case. Reader `docs/experiments/question-record-20261031/e2e_ab.py`
  (`scores-e2e-ab.json`).
- Result: arm A passed 5 of 6 (ticket-assignment A3 paused at document with 2 of 3 checks failing) and 4 of its 6
  runs lost a stage loop to the proof-order fault (3 at implement, 1 caught by the model at test-spec). Arm B passed 6
  of 6, no run had that send-back (exact one-sided p 0.030), and the refusal fired 3 times, each followed by an accepted
  plan. Time: no effect claimed (user-listing B faster in every run, median 9.4 against 11.1 minutes, p 0.05;
  ticket-assignment B slower, 13.9 against 8.1, p 0.70, its longest runs spent on other gates). Every B intake wrote the
  ledger (11 categories, 2-6 questions). The shipped rule, replayed on arm A's 12 step plans, refuses exactly the 4 that
  went on to the send-back and accepts the other 8.
- Found on the way: the first build accepted the ledger and dropped it from the stored result (`_canonical_result`
  copied neither field). I first read the stored result and blamed the model; Terra's inbox block held 11 categories and
  3 questions. A requirement added on that wrong reading refused every synthetic intake of the hermetic suites and was
  reverted before commit; e7e0bc3c keeps the fields. Runs B1 of each case ran builds without the fix (ledger written,
  not stored); every B run carries the refusal.
- Status: firm that the refusal moves the fault from a send-back to a step-plan refusal on Terra high; interim on time;
  the ledger's downstream product effect is not measurable on these fully specified prompts.
- Evidence: `test/shiploop_e2e/LEARNINGS.md` (the entry of this date); `~/e2e-runs-qr/20261031/`;
  `docs/experiments/question-record-20261031/scores-e2e-ab.json`, `sg1/replay-d6-live-arm-a.jsonl`; 12 rows in
  `test/shiploop_e2e/baselines.jsonl`.

### E11 — 2026-10-31: does the catalog hurt a thorough subject's spec? (X2b-S, Sonnet 5.5 xhigh)

- Question: the catalog ships for every subject; on Sonnet, X1 had it commit more guesses that conflict with the full
  request (agreement 0.64 against 0.77). Does that reach Sonnet's spec?
- Method: X2b's design on Sonnet (`ask sonnet`, xhigh), fed X1's own Sonnet intakes A and B (samples 1 and 2: n = 8
  per arm), 16 spec calls (about 10 minutes each), 4 Opus judge calls, 0 unverified quotes. Rule pre-registered in the
  evidence README before any call: a fall of more than 10 points in agreement or carried share flags the catalog as
  subject-dependent.
- Result: carried 1.000 in both arms (Sonnet's spec carries every decision whatever intake gives it); pinned 0.935
  against 0.960; agreement 0.59 against 0.63; spec length 49,184 against 54,128 characters; scope additions 1.0 against
  2.0 per run.
- Rule: no fall; the catalog stays for every subject. On a thorough subject it changes little downstream; on Terra it
  lifts what spec carries by 12 points (E9).
- Status: interim (n = 8 per arm, one judge).

### E12 — 2026-10-31: do runs miss runtime facts or break existing behaviour? (the saved corpus, no model run)

- Question: the owner asked whether planning should plan and run experiments, or add extended tests on the existing code,
  to clarify conditions, state and behaviour, and whether as a prompt or a script-enforced step. Before building either:
  do the saved runs miss the runtime facts such a step would establish?
- Method (docs/experiments/experiment-route-20261031/corpus/): run node-tickets' 36 documented claims against the base, and
  probe every saved completed product of its cases outside the run (filters that combine, the assignee across a SIGTERM
  restart, escalation at most once across SIGTERM and SIGKILL restarts, the 36 claims diffed against the base); read the
  harness's held-out acceptance (result.json `quality.acceptance`) of every saved brownfield run.
- Result: the base has one drift (filters OR where docs/api.md says they combine). Filters combine in 17 of 18 completed
  products, the assignee survives a restart in 17 of 17, escalation stays at most once in 5 of 5, and 0 of 17 products
  break a documented claim or change any of 7 undocumented behaviours. Held-out acceptance: 26 of 26 completed brownfield
  runs pass every check (ticket-assignment 10 x 18, ticket-escalation 5 x 14, user-listing 11 x 11), latent facts
  included, DeepSeek flash and Codex Terra.
- Reading: on the cases we have, runs already find runtime facts and keep behaviour; a required experiment step or
  characterization tests would bind nothing there. Characterization tests stay on hold, now with evidence.
- Status: firm for these cases (two Node bases); not a claim about larger or less documented systems.

### E13 — 2026-10-31: XR, does one sentence move runtime questions to the `experiment` route? (Terra high, no tools)

- Method (pre-registered in 593b4b44, README "XR"): X1's intake exercise with the shipped duty (A) or one added sentence on
  the `experiment` route (B); four brownfield requests, 4 samples each, 32 calls; Opus classed every question RUNTIME or
  NOT_RUNTIME, blind to arm and route.
- Result: RUNTIME questions routed `experiment` per output 0.25 (10%) -> 1.06 (33%), p = 0.0035; NOT_RUNTIME so routed
  0.25 -> 0; no invalid ledger. The rule asked for +1.0: missed (+0.81), so the shipped route text stays.
- Reading: the sentence shifts what intake proposes and over-routes nothing, but two-thirds of RUNTIME questions still take
  `inspect`; on ticket-import the shipped intake already names the deciding facts and routes the timing question to
  `experiment` in all four samples.
- Status: firm (no-tool exercise, one judge).

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
| F13 | 9 of the 12 implement send-backs in the saved runs are a Proof that needs a test the test stage writes later (8 on Codex Terra xhigh); the prompt rule (since 2026-10-17) does not stop it; the shipped refusal catches 7 of the 9 and refuses no plan that passed by the rules | firm | E5 |
| F14 | On Codex Terra 6.1 the shipped intake surfaces about half of what a vague request leaves open (0.49 high, 0.51 xhigh); effort barely moves it, the catalog ledger does (0.91, 0.98) | firm (no-tool exercise) | E6, E9 |
| F15 | A numbered record quoted into spec carries no more than prose (C 0.81, A 0.79 on Terra high): F2's harm is not the format at the intake→spec hand-off | firm (no-tool exercise) | E7 |
| F16 | The catalog ledger's gain reaches the spec: carried 0.78 → 0.90 (p 0.013), agreement unchanged | firm (no-tool exercise) | E9 |
| F17 | Neither isolated design measures a step-plan prompt sentence on Terra: no-tool packets block (64/64), and the step case's seed carries a clean proof | firm | E8 |
| F18 | Live on Terra high the refusal moves the proof-order fault from a send-back to one step-plan refusal (0 of 6 runs with the send-back against 4 of 6, p 0.03), with every hidden check kept; the ledger is written without a gate | firm (proof order), interim (time) | E10 |
| F19 | On the brownfield cases we have, runs already find runtime facts and keep existing behaviour: 26 of 26 completed runs pass every held-out check, 0 of 17 products break a probed behaviour; a plan-time experiment step has nothing to bind there | firm (two Node bases) | E12 |
| F20 | One sentence on the `experiment` route moves runtime questions there (10% -> 33%, p 0.0035) without over-routing, below the +1.0 bar; a prompt shifts what intake proposes, not what the run probes | firm (no-tool) | E13 |
