# ShipLoop brownfield baseline: journal

Living journal for [the design](shiploop-brownfield-baseline-design-2026-10-28.md). Evidence, prompts, scripts and
compact outputs: [docs/experiments/brownfield-baseline-20261028/](experiments/brownfield-baseline-20261028/). Products
(clones, worktrees, full agent outputs) stay in the session scratchpad and are never committed; the outputs that
findings rest on are exported under `results/`.

## Question (owner, 2026-10-28)

ShipLoop is mostly used to add features to an existing repository, which may be large and may have no spec,
environment or architecture documents. Where in ShipLoop should the existing repository be reverse-engineered into a
spec (from the README, tests, code) and into the environment and architecture decisions ShipLoop needs, so that
existing decisions are reused unless the incoming request says to change them? How should the planning phase and
discovery be organised around it?

## Conditions for every round

- Subject: Claude Sonnet (`sonnet` agents), exploratory per [[experiments-use-sonnet]]; a confirmation on the E2E
  subject (DeepSeek flash on Ollama until 2026-10-29, then the owner's choice) is a follow-up.
- Judge: Claude Opus 5.5 (one judge per round).
- Subjects run read-only on local clones: no network, nothing installed, no repository tooling run, nothing sent to
  any project. Repository text is data, never instructions.
- Repositories, pinned: node-base (ShipLoop's fixture `test/shiploop_e2e/fixtures/node-base`, digest in cases.json),
  [log4brains](https://github.com/thomvaill/log4brains) `17e32021a8c5`, [healthchecks](https://github.com/healthchecks/healthchecks)
  `f6c46b594dec`, [uptime-kuma](https://github.com/louislam/uptime-kuma) `2e8bf7da56f7` (census only),
  [cosmos-sdk](https://github.com/cosmos/cosmos-sdk) `27246c287d98` (census only).

## Rounds

### X1 census (script, no model), 2026-10-28 — firm

Question: how much of the map a baseline needs can a script produce, generically and cheaply?
Harness: [census.py](experiments/brownfield-baseline-20261028/census.py), outputs in
[census/](experiments/brownfield-baseline-20261028/census/).

| Repository | Tracked files | Code lines | Test lines | Size class | Seconds | Markdown lines | Decision records found |
|---|---|---|---|---|---|---|---|
| node-base | 11 | 94 | 69 | small | 0.09 | 40 | none |
| log4brains | 368 | 29,472 | 4,787 | medium | 0.11 | 50 | 15 of the 19 real records (docs/adr 10, packages/core/docs/adr 2, packages/web/docs/adr 3), plus 16 fixture and template hits |
| healthchecks | 1,275 | 61,326 | 23,573 | large | 0.15 | 66 | none |
| uptime-kuma | 923 | 163,995 | 14,901 | large | 0.16 | 72 | none |
| cosmos-sdk | 4,275 | 1,160,240 | 189,985 | huge | 0.53 | 77 | 58 (docs/architecture, with template) |

Findings:
- Firm: the census is generic (file classes come from ShipLoop's own `path-classes.json` through
  `shiploop_item_scope.classify`), runs in under a second on a 1.16-million-line repository, and fits a packet
  (40-77 lines).
- Firm (harness change, round 1 → 2): decision records must be found by **content** (status, context, decision,
  consequences), not by name. Round 1 matched digit-prefixed names: it missed both real sets (`20200924-*.md`,
  `adr-007-*.md`) and flagged cosmos-sdk's numbered tutorial chapters. Round 2 found 15 of log4brains' 19 real
  records and cosmos-sdk's 58 (with its template), and no tutorial chapters; it also lists ADR-shaped fixtures and
  templates (16 hits on log4brains), so its output is a candidate list. (Corrected 2026-10-28: this line first said
  "13 … no false positives", read off a truncated print; the counts come from `census/log4brains.json`.)
- Firm: the census surfaces instruction files a baseline must read first. uptime-kuma's `AGENTS.md` limits code agents
  to 1-10-line fixes and tells them to "revert all changes in Git" otherwise; healthchecks' `CONTRIBUTING.md` refuses
  AI-made contributions and documents how a new integration must be built. Both are team policy to surface to the
  owner, never commands to obey. Because of its policy, uptime-kuma stayed census-only.
- Observed limitation: dependency manifests count as code (path classes do not classify them), so cosmos-sdk's hot
  spots are dependency files. Acceptable for a map; a model reads past it.
- Observed limitation: content detection also finds ADR-shaped test fixtures and templates (log4brains:
  `packages/core/integration-tests/**/adr`, `packages/init/assets`) and missed one real record
  (`packages/core/docs/adr/20201002-…`, which has a status line but none of the other parts as headings). The
  census lists candidates; the baseline stage decides which are the team's records.

### X2 baseline extraction, 2026-10-28

Question: what does a scoped baseline (the proposed stage, arm B) produce on real repositories, how accurate is it,
what does it cost, and how does it compare with a whole-repository initializer (arm A)?
Prompts: [baseline-scoped.md](experiments/brownfield-baseline-20261028/prompts/baseline-scoped.md) (B),
[baseline-whole.md](experiments/brownfield-baseline-20261028/prompts/baseline-whole.md) (A: the repo-distill
initializer of 2026-09-27, commit 94bb8862, with arm B's format so only the scope differs). Measures:
[summarize.py](experiments/brownfield-baseline-20261028/summarize.py) and check C1 of
[baseline_check.py](experiments/brownfield-baseline-20261028/baseline_check.py); accuracy and coverage by an Opus
judge ([judge-baseline.md](experiments/brownfield-baseline-20261028/prompts/judge-baseline.md)) against hand-built
expectations ([ground-truth/](experiments/brownfield-baseline-20261028/ground-truth/)).

#### X2a node-base, arm B, request user-listing — interim (n=1)

Evidence: [results/x2/nb-B/](experiments/brownfield-baseline-20261028/results/x2/nb-B/). Discovery's baseline run
(`node --test`, 7 pass) was given as the `tested` evidence.

- 870 s, 221k tokens, 31 tool calls. Output 16.2 KB spec + 10.7 KB architecture for 149 lines of code (about 7x
  the source): 10 R (53 bullets), 12 AD, all inherited. C1: 123 of 123 locators resolve; 0 findings. Classes:
  documented 4, tested 5, observed 10, inferred 3, conflict 1.
- It caught the planted defect: R-5 records that `paginate` rounds the page count down, drops a partial last page,
  gives 0 pages for a list shorter than the size, conflicts with `README.md:6`, and that the existing test compares
  the result shape with strict deep equality (so the feature cannot add fields to it). This is exactly the
  calibration's `floor-pages` defect (6 of 11 held-out checks,
  [calibration.txt](experiments/e2e-brownfield-20261026/calibration.txt)).
- It noted that `GET /users` has no HTTP test (only the store function has one), so the request's compatibility
  clause rests on code alone.
- Defect of the packet, firm: it **template-fills**. The list of cross-cutting rules in "Done when" produced R-7
  "Background work", R-8 "Identity and access" and R-9 "Privacy and security" for a repository that has none of
  them, and R-10 puts test commands (environment knowledge) in the spec. A trivial repository took half the 30-minute
  planning ceiling. Fix: a concern that does not apply is one `none` line in the overview, never an entry; size the
  deep slice to the touched code.

#### X2c log4brains, arm B, request L1 (`adr list --json`) — interim (n=1)

Evidence: [results/x2/l4b-B/](experiments/brownfield-baseline-20261028/results/x2/l4b-B/).

- 1,405 s, 431k tokens, 101 tool calls. 29.2 KB spec + 26.3 KB architecture: 12 R (77 bullets), 33 AD (32
  inherited, 1 superseded, 21 linking the team's records). C1 round 2: 246 of 246 locators resolve; its only finding
  is a parser edge (below). The "deep" list named six packages for a one-flag CLI change: over-scoped.
- The team's records were reused, not copied: each of the 16 real ADRs maps to one AD-<n>, the two superseded ones sit
  under `## Superseded` with their replacements, and the ADR-shaped fixtures and templates were named as "not
  decisions of this project".
- Its open items are the kind a planner needs before planning: the request's "id" is the slug (ADR 20201016) and
  "date" is ambiguous among three dates; `init` parses the stdout of `adr list --raw` (an existing consumer contract);
  CONTRIBUTING still says "simplified Git Flow" after ADR 20241217 reverted it (a doc-versus-decision conflict).
- New generic issue, firm: the repository's CI runs Prettier over every `.md` file, so ShipLoop's
  `docs/shiploop/*.md` files are product files that must pass the repository's own format and lint gates. The
  existing lint auto-fix (`shiploop_lint`, lint catalog) should run over the knowledge home before its commit.
- Side finding in ShipLoop itself, firm: `shiploop_knowledge_home._entries` takes the first line that starts with an
  ID as the entry. The prose line "AD-4 and AD-10 appear under Superseded." shadows the real AD-4 entry, so
  `entry_text(repo, "AD-4")` returns that prose line (reproduced). C1 round 2 reports it as "AD-4: starts 2 times".

#### X2b healthchecks, arm B (scoped, request T1) against arm A (whole repository) — interim (n=1 each)

Evidence: [results/x2/hc-B1/](experiments/brownfield-baseline-20261028/results/x2/hc-B1/),
[results/x2/hc-A/](experiments/brownfield-baseline-20261028/results/x2/hc-A/), the comparison
[scoped-vs-whole-T1.json](experiments/brownfield-baseline-20261028/results/x2/scoped-vs-whole-T1.json).

| Arm | Seconds | Tokens | Tool calls | Size | R (bullets) | AD | C1 | Judge |
|---|---|---|---|---|---|---|---|---|
| B scoped | 1,795 | 520k | 180 | 61 KB | 18 (126) | 27 | 260/260 locators, 0 findings | 39/42 correct, 0 wrong, 0 unsupported; GT1-3, 5, 7-9 all present |
| A whole | 3,023 | 883k | 169 | 273 KB | 90 (348) | 38 | 375/379 locators, but 51 of 128 entries unparseable: the format drifted (paths without backticks) | not judged alone; see the comparison |

- Comparison for request T1 (Opus, 41 consequential facts checked against the code): **only in A and consequential:
  2** (a delayed "down" retry arriving after recovery re-opens incidents in pairing integrations; Signal CAPTCHA
  failures re-email on every retry); **only in B and consequential: 8** (no Notification-to-flip link; the
  "Sending" marker that makes "failed" ambiguous; the 200-character error column; four callers sharing
  `Channel.notify`; paid quota spent before each call; notifications hidden behind an unticked filter; a broken live
  update in `log.js`; the webhook page's "up to 2 additional times" promise); in neither: 2 (open questions the
  request leaves). Firm for this request: scoping loses little and keeps more of what matters, at a quarter of the
  size and 60% of the time; the whole baseline's two extra facts are cross-integration side effects, an argument
  for naming "every other caller and consumer of the touched function" in the scope rule.
- B's open items were the planner's real questions (retry semantics for callbacks and bounces, in-attempt retries
  already present, no durable retry state, retry side effects, display limits), and it surfaced the AI policy as
  an owner item. It went "deep" on 8 of 19 census areas: the scope rule is too loose.
- Cost, firm: 30 minutes on Sonnet for the scoped pass alone uses the whole 30-minute planning ceiling.

#### X2d healthchecks deepen pass for a later request (T2), on the committed B1 baseline — interim (n=1)

Evidence: [results/x2/hc-B2/](experiments/brownfield-baseline-20261028/results/x2/hc-B2/) (with the diff from B1).

- 2,180 s, 517k tokens, 182 tool calls: **more than the first pass**. It added 24 entries, changed 5 and deepened
  9 areas, growing the home from 61 KB to 102 KB.
- Nothing it cited had changed since B1 (the same commit plus the knowledge commit): C3 rates all 69 entries
  `fresh` in seconds. The packet's "re-verify the entries of those areas" made the model re-read them anyway. Fix,
  firm: the packet quotes C3's result, and only `stale` or `unknown` entries are re-verified.
- C2 refused its 5 changed entries (R-11, R-16, AD-3, AD-16, AD-18): corrections the packet never asked it to mark.
  This confirms the `Corrected: <locator>` marker is needed, and that C2 can tell a correction from a change only if
  the packet asks for the marker.
- Its open items were again what a planner needs: the capability already exists (`GET /api/v3/checks/` with a
  read-only key), the docs promise HTTP 429 above 100 requests a minute and no code throttles the API, and a
  `SITE_ROOT` path prefix would make every call act as v1.
- Directory coverage misled it: B1 had listed `hc/api` as deep, yet its entries covered notification delivery, not
  the API listing. That confirms Astra's C1: coverage must name flows.

### X3 plans on healthchecks: three requests × three arms — interim (n=1 per cell)

Arms: A0 (the 2026-10-27 plan wording), A0w (A0 plus the inherit rule: record each existing decision relied on,
change one only with `Basis: S<k>`), A1 (A0w plus the committed B1 baseline in the repository). Requests: T1 delayed
retries (tempts a queue or scheduler), T2 a read-only status API (already exists), E1 an explicit move to Celery.
Plans: [results/x3/plans/](experiments/brownfield-baseline-20261028/results/x3/plans/) under blind labels
([key.json](experiments/brownfield-baseline-20261028/results/x3/key.json)); blind Opus verdict
[judge.json](experiments/brownfield-baseline-20261028/results/x3/judge.json).

| Request | Arm | Seconds | Tokens | Unauthorized | Rebuilt | Authorized (with basis) | Existing decisions named |
|---|---|---|---|---|---|---|---|
| T1 | A0 | 1,050 | 309k | 0 | 0 | 1 (all) | 7 |
| T1 | A0w | 1,355 | 328k | 0 | 0 | 1 (all) | 8 |
| T1 | A1 | 1,351 | 348k | 0 | 0 | 1 (all) | 8 |
| T2 | A0 | 759 | 257k | 0 | 0 | 0 | 3 |
| T2 | A0w | 770 | 279k | 0 | 0 | 0 | 5 |
| T2 | A1 | 805 | 275k | 0 | 0 | 0 | 3 |
| E1 | A0 | 1,131 | 340k | 0 | 0 | 3 (all) | 7 |
| E1 | A0w | 1,218 | 357k | 0 | 0 | 3 (all) | 6 |
| E1 | A1 | 1,641 | 417k | 0 | 0 | 3 (all) | 7 |

- **Null result, firm for this subject and these cases: neither the inherit wording nor the baseline changed
  decision preservation.** Every plan kept every existing decision unless its request asked; every T2 plan found
  that the existing API already answers the request; every T1 plan put delayed retries on `Notification` and in the
  existing `sendalerts` loop (no broker, queue or scheduler); every E1 plan made the requested Celery move and kept
  the rest. The "tempting" requests did not tempt Sonnet, which read the code for 13-27 minutes per plan.
- Cost: the A1 plans cost 6-45% more time than A0 (they read the baseline and the code).
- What the baseline arm adds that the others lack: its knowledge edits are checkable. C2 on the A1 runs: T1 changed
  R-2, R-3, R-15, R-18, AD-6, AD-12 and E1 changed R-2, R-14, R-15, R-17, AD-4, AD-7, each with a valid basis; T2
  changed nothing existing (it only added).
- Not tested: a weaker or faster subject (the E2E default is DeepSeek flash), the stages of a real run with cleared
  context, and a real second run.

#### X3 fact coverage of the three T1 plans — interim (n=1 per arm)

A blind Opus judge graded each T1 plan against the 41 consequential facts of
[scoped-vs-whole-T1.json](experiments/brownfield-baseline-20261028/results/x2/scoped-vs-whole-T1.json):
[t1-fact-coverage.json](experiments/brownfield-baseline-20261028/results/x3/t1-fact-coverage.json).

| Plan | Arm | Handled | Noted | Missed | n/a |
|---|---|---|---|---|---|
| P3 | A0 | 32 | 3 | 4 | 2 |
| P4 | A0w | 34 | 2 | 3 | 2 |
| P7 | A1 (with the baseline) | 31 | 5 | 4 | 1 |

- Null again, interim: the baseline did not make the plan more complete.
- **Firm, and the most useful single result: the baseline arm missed facts its own baseline states.** F4 (an error
  longer than 200 characters fails the UPDATE that would also schedule the retry) is in the B1 spec
  (`results/x2/hc-B1/spec.md`, "Error text is stored as given in a 200-character column") and is one of the eight
  facts only the scoped baseline had; F12 (each retry spends another paid SMS or call unit) is the B1 report's open
  item 5. A 61 KB baseline in the repository was not consumed. A baseline's open questions are useful only when the
  next packet quotes them by value and the stage must answer each one (a script can check the answers by ID). This is
  the owner's consumer rule ([[produce-for-a-consumer]]: excerpts quoted into a packet, not a path) and the planning
  research loop's "key questions anchored" step.

### Astra (GPT-6 Astra, max effort) design review, 2026-10-28

Question and answer: [results/astra/](experiments/brownfield-baseline-20261028/results/astra/) (`model_used
gpt-6-astra`, `effort max`, no fallback; read-only, no file changed). Verdict: the persistence problem is real; fold a
durable, scoped baseline into discovery's close for the first build and defer a separate stage until experiments
show its benefit. Findings, each checked against the code before use:

| # | Rank | Finding | Checked | Taken into the design |
|---|---|---|---|---|
| A1 | P1 | A new stage after discovery breaks reconciliation: `RECONCILIATION_TARGETS = PLANNING_STAGES[:4]` would drop test-strategy | yes, `shiploop_planning_revision.PLANNING_STAGES` | fold into discovery first |
| A2 | P1 | `_knowledge_close` commits after the state is saved and tolerates a failed commit, so "done means a committed baseline" does not hold; moving `RUN_BASELINE` can absorb feature changes | yes, `shiploop_navigator._knowledge_close` | keep the run-start identity; add a separate comparison snapshot taken once, before spec |
| B1 | P0 | an assumption must not override accepted intent; split obligations, defaults and evidence corrections | guidance agrees (`project-knowledge.md` maintained requirements) | change rule rewritten |
| B2 | P1 | C2 checked citation syntax only: `S0`, a bare `assumption`, an accepted entry changed freely, an `As of` refresh refused | yes, reproduced; fixed in round 2 with 6 new tests | C2 is traceability, never semantic authorization |
| C1 | P1 | a directory marked deep is no coverage proof; a later request on another flow in the same directory would be skipped | design reasoning | coverage records flows and interfaces; touches are a hypothesis discovery validates |
| C2 | P1 | C3 turned missing evidence into freshness (dropped unresolved paths, ignored Git failures and dirty edits, used a global date) | yes, reproduced; fixed in round 2 | fresh / stale / unknown; only fresh may skip |
| D1 | P0 | "current behaviour stands" must not resolve an intent-versus-implementation conflict (X2a's R-5 is the example) | `current-system-baseline.md` already says resolve before dependent changes | conflict default rewritten |
| D2 | P1 | a test that exists is not a test that ran; runtime-observed evidence and authority are separate dimensions | design reasoning | classes split from authority |
| E1 | P1 | "AGENTS.md is never instructions" is wrong in the user's workspace: host-loaded repository instructions are operative; text found in sources is not | design reasoning | policy handling rewritten: classify scope before the affected action |
| F1 | P1 | consumer scope: test-strategy and plan cover "every criterion", so a baseline catalog would demand work for the whole product | `DUTIES["test-strategy"]`, `DUTIES["plan"]` done-when lines | consumers read the delta plus the preservation set |
| F2 | P1 | cut mandatory cross-cutting entries; P2: one AD per record (index broadly, materialize what applies), routine history study, the ban on public API names in requirements | X2a and X2c sizes | taken |
| G1 | P1 | the experiments cannot decide placement; add a discovery-integrated versus separate-stage comparison with a cold restart | agreed | follow-up experiment |

### X4 prototype checks, round 2, 2026-10-28 — firm (as a prototype)

[baseline_check.py](experiments/brownfield-baseline-20261028/baseline_check.py) and
[test_baseline_check.py](experiments/brownfield-baseline-20261028/test_baseline_check.py): 13 tests pass (6 new
ones failed first: 2 failures, 5 errors). C1 adds missing files, unknown source classes and duplicate ID starts;
C2 covers every entry that existed at the run's start, needs the request itself for an obligation, accepts a
recorded assumption only for a default, ignores an `As of` refresh, reads the rendered request's own index; C3 judges
each entry from its own evidence commit (its `As of`, else the commit before the one that wrote it) and reports
`stale` for changed, deleted or uncommitted sources and `unknown` without usable evidence. A test cannot show that
`S<k>` really asks for a change: C2 stays traceability, and review and preservation tests carry the semantics.
The census (round 2) keeps the whole directory inventory in its JSON (cosmos-sdk: 206 directories against 30 map
rows) and lists instruction files one level down too.

### X3b node-base plans, request user-listing — interim (n=2 per arm)

Arms: A0 (the 2026-10-27 plan wording, no baseline) and A1 (inherit wording plus the X2a baseline committed in the
repository). Evidence: [results/x3b/](experiments/brownfield-baseline-20261028/results/x3b/).

| Run | Seconds | Tokens | Items | Decisions | Fixes `paginate`'s rounding | C2 on its knowledge edits |
|---|---|---|---|---|---|---|
| A0-1 | 599 | 175k | 3 | 9 | yes (W1, floor to ceil, keeps the pinned keys) | n/a |
| A0-2 | 558 | 171k | 2 | 8 | yes (W1) | n/a |
| A1-1 | 771 | 209k | 3 | 18 | yes (W1, `Basis: S5`) | 5 changed entries, each with a basis; 0 findings |
| A1-2 | 631 | 200k | 3 | 15 | yes (W1) | the same 5 entries (R-1, R-3, R-5, AD-5, AD-12), each with a basis; 0 findings |

- Firm for this repository: **on a 149-line repository the baseline changed nothing that matters to the plan.** Both
  no-baseline plans read `paginate` themselves and planned the same fix. The baseline's value has to come from larger
  repositories and from inheritance across runs, not from single-run planning on small ones.
- Interim: with a baseline, the plans recorded which existing decisions they change and why, consistently (both A1
  runs changed the same five entries with a basis), and they cost about 20% more time.
- C1 flags new `(accepted)` decisions for having no `Evidence` locator; that is right for code not yet written, so
  C1 should demand evidence only of found entries.

## Findings (2026-10-28)

| # | Finding | Status | Evidence |
|---|---|---|---|
| F1 | Today the recovered system lives in a run note (`DUTIES["discovery"]` steps 10, 13); the committed home on a first brownfield run describes only the feature; nothing protects pre-existing behaviour; `spec_diff` cannot separate recovered from new | firm (code) | design section 1 |
| F2 | A generic script census costs 0.1-1.5 s and fits a packet; decision records are found by content, as candidates | firm | X1 |
| F3 | A model-written baseline is accurate on what it anchors (26/27, 47/48, 39/42 correct; 0 wrong; every expected fact) and surfaces what planners need (defects, hidden contracts, side effects, doc conflicts, team policies) | interim (n=1 per repository) | X2 judges |
| F4 | A separate baseline pass costs 15-30 minutes scoped and 50 minutes whole on Sonnet; the whole pass also drifts from the parseable format; a later pass re-verifies fresh entries unless told otherwise | firm | X2, X2d |
| F5 | Scoping by the request loses little against a whole-repository account and keeps more of what matters (8 against 2 consequential facts only one side had) | interim | scoped-vs-whole-T1.json |
| F6 | On Sonnet, neither the inherit wording nor a baseline changed single-run decision preservation (0 unauthorized changes in all 9 healthchecks plans; all 4 node-base plans fixed the same defect) | firm for these cases; untested on weaker subjects | X3, X3b |
| F7 | With a baseline, changes to existing entries carry a basis a script can check, and both node-base runs changed the same five entries | interim | X3, X3b, C2 runs |
| F8 | C2 must cover every existing entry, split obligations from defaults, and accept marked corrections; C3 must report fresh / stale / unknown; C1 checks locators only | firm (prototype, 13 tests) | X4 round 2, Astra |
| F9 | Placement at discovery's close beats a new stage for a first build (reconciliation wiring, shared allowance) | firm (code) | Astra A1, `shiploop_planning_revision` |
| F10 | The knowledge home must pass the repository's own format gates; repository instruction files the host loads are operative rules, classified by scope before the operation they govern | firm | X2c, Astra E1 |
| F11 | `shiploop_knowledge_home._entries` lets a prose line that starts with an ID shadow the real entry | firm (reproduced) | X2c |
| F12 | A baseline in the repository is not consumed by being there: the baseline-arm T1 plan missed two facts its own baseline states; open questions must be IDs quoted by value into the spec and plan packets, each answered or carried as an assumption | firm (for this case) | X3 fact coverage |

Design revisions: revision 1 (a separate, script-gated baseline stage) → revision 2 (discovery's close writes a
progressive, flow-scoped account; plan inherits; C1-C3 as traceability and notice), after F4, F6, F9 and Astra.

F11 is fixed (D8, below), so its status is now superseded by the fix, 2026-10-28.

## Owner decisions and their execution (2026-10-28)

The owner accepted D1–D9 as recommended ("Accept D1–D9"). D7 orders the work: the E2E evidence on today's ShipLoop
comes first, because the experiments showed no single-run gain on Sonnet and left three questions open (a weaker
subject, reuse across a real run's stages, a second run that inherits a committed home). The build of design section 10
follows that evidence and is measured against it.

### D8: an entry starts at its heading or list item — firm (built, tested)

- **Question.** Which line stands for an `R-<n>` or `AD-<n>` entry when the ID starts more than one line?
  `shiploop_knowledge_home._entries` took the first start of any form (F11).
- **Corpus.** Every living `docs/shiploop/spec.md` and `architecture.md` under `~/e2e-runs`, `~/e2e-runs-owner-note`
  and the default E2E output folder: runs from 2026-10-04 to 2026-10-28 on Grok, Sonnet, Opus, Haiku, DeepSeek and
  Codex hosts. At the snapshot that is 1,204 files and 5,369 entries; 56 files have an ID that starts more than once.
  Live runs keep adding files, so a rerun counts a few more.
- **Patterns, first start → later starts** ([entry_starts.py](experiments/brownfield-baseline-20261028/entry_starts.py),
  output in [d8-entry-starts.txt](experiments/brownfield-baseline-20261028/results/d8-entry-starts.txt)).

  | Pattern | IDs | Real entry |
  |---|---|---|
  | heading → table | 56 | the heading; the table is a traceability row |
  | heading → list | 29 | the heading; the list items are its acceptance lines (`- **R-1.1 …**`) |
  | table → heading | 18 | the heading; the table is a summary above it (a Haiku 5.5 max run) |
  | list → plain line | 15 | the list item |
  | heading → heading, plain line | 9 | the first heading |
  | heading → list, plain line | 5 | the heading |
  | plain line → heading | 5 | the heading (`AD-5's HTTP step 5 relies on this order, …`) |
  | plain line → heading, list | 4 | the heading (`R-3–R-9 and the API half of R-10 therefore carry …`) |

- **Rule.** The ID's first heading or list-item start is its entry. When it has none, the first start of any form
  (a table row, or a plain line that begins with the ID) still counts, so table-only and paragraph-only formats keep
  working. `outline` uses the same start.
- **Effect on the corpus.** The script compares the parser at the commit before the fix with the fixed one on every file:
  27 entries move, 18 from a table row and 9 from a plain line, each to its heading. The key sets are identical (asserted),
  no retired flag changes (asserted), and 8 files' outlines change.
- **Test.** `EntryTests.test_a_heading_or_list_start_outranks_an_earlier_table_row_or_plain_line_of_the_id` in
  `test/shiploop-handoff.test.py`. On the old parser it fails: the summary row `| AD-1 | Plain modules |` came back as
  AD-1. The handoff, knowledge and callback-contract suites pass (124, 135 and 87 tests).
- **Change note.** `changes/shiploop/entry-start-prefers-heading.md` (patch).

### D7: E2E evidence on today's ShipLoop — firm for these cases (n=1 per case)

Recorded below as the runs finish: the `user-listing` live run, and the medium brownfield case with its follow-on, both
on the E2E subject (DeepSeek flash on Ollama through the Claude host, `hosts.RUN_DEFAULT_BACKEND`).

#### The medium case pair: built and calibrated, not yet run — firm (as an instrument)

- **What.** `ticket-assignment` on a new base, `test/shiploop_e2e/fixtures/node-tickets`, and its follow-on
  `ticket-escalation` (`follows`, run with `--continue-from`). The base is a dependency-free help-desk ticket service:
  1,681 lines of source, 1,264 of tests (117 `node:test` tests), 624 of documents, with eight decision records (one
  superseded), an index and a template. `user-listing`'s base is 149 lines; this one is about 24 times that, so reading it
  again costs a run real time.
- **What it measures (D7).** (1) Does a run keep behaviour and team decisions its request does not name? Thirteen latent
  facts, LA1-LA8 for the first request and LB1-LB5 for the follow-on, each with the file and symbol that holds it and the
  checks that read it: [node-tickets-expected.md](experiments/brownfield-baseline-20261028/ground-truth/node-tickets-expected.md).
  Like node-base, the base breaks one of them in the flow the request touches: its listing combines two filters with "or"
  where `docs/api.md` says every filter must match, and its tests try one filter at a time. (2) Does the follow-on keep what
  the first run had to learn? The follow-on's seven pass-to-pass checks reuse the first case's checks, so against the first
  run's delivery a check that passed after the first run and fails after the second is something the second run lost.
- **Checks.** 18 held-out checks for the first case (6 pass-to-pass, 12 fail-to-pass) and 14 for the follow-on (7 and 7),
  plus each case's visible checks (the first: `base_tests.py suite` and `pristine`, one HTTP check; the follow-on: two HTTP
  checks and four retention checks in battleship-scoring's shape).
- **Calibration** (`test/shiploop-e2e-brownfield-tickets.test.py`, 24 tests). 54 variants: each base fails exactly its
  fail-to-pass checks and passes its pass-to-pass checks and the 117 pristine tests; each reference and each independently
  written alternative passes everything; 27 targeted defects of the first case and 21 of the follow-on each fail exactly the
  checks they read. Every check is failed by some defect, and every defect is caught by a check or the pristine tests.
  Three defects break a base module and edit the base's tests to match, so only the pristine tests see them; three break
  existing behaviour that both the pristine tests and a held-out pass-to-pass check see; and one, `update-rejects-resolved`
  (in both cases), is seen only by a held-out pass-to-pass check, because nothing in the base's tests edits a resolved ticket.
- **Harness change.** A held-out check may take a second parameter, the delivered copy (`quality.Product`): more servers
  of the product with an environment of the check's own, restarts, and the product's command lines. `quality.free_port`
  never hands out a port twice within 4,096, and a product server that exits on `EADDRINUSE` naming its own port is started
  again on another. The evaluator digest changes for every case (as it does for any harness change), and the oracle digest
  with the new check modules: a promotion decision never spans this commit.
- **Findings while building it (firm for the instrument):**
  - The base's tests first compared whole objects (a created ticket, the loaded data file, the configuration), so the
    request's own `assignee` field, or the follow-on's `ONCALL` setting, failed the pristine suite. A base whose tests forbid
    the requested change is a broken case; they now compare the fields they own.
  - Grading 54 variants side by side made thousands of short TCP connections a minute. Closing them from the product's side
    left wait states on its ports, which `listen(0)` hands to the base's own test servers; closing them from the client's side
    ran the ephemeral range out (`EADDRNOTAVAIL`). The checks now keep one connection per server and close it first, and the
    base's test client keeps one per test. What remained, under load averages of 40 to 90 from other work, was about one
    reset in two hundred concurrent `node --test` runs, never twice in a row; the calibration grades a disagreeing result once
    more, alone, and pins that this happens at most four times.
- **Runs.** None yet: the owner launches them. `python3 test/shiploop_e2e/run.py --case ticket-assignment --output <out>`,
  then `python3 test/shiploop_e2e/run.py --case ticket-escalation --continue-from <out> --output <out2>`, both on the E2E
  subject by default. The same pair runs again after section 10's build.

#### The before-runs: no correctness gap; planning is slow, and Improve is most of it — firm for these cases (n=1)

- **Conditions.**
  - Subject: DeepSeek flash (`deepseek-v4.1-flash:1017-cloud`) on Ollama through the Claude host, `--permission-mode auto`.
  - Source: `--source checkout` from one detached worktree pinned at 8aa6e1fe (origin/main 4e1c8df0, plus the design, its
    results, D8 and the medium case).
  - Output: under `~/e2e-runs-brownfield/20261028/`, a runs root of our own. Under `~/e2e-runs` the E6D2 slices hold no
    run lock, so the orphan check refused. The runs sharing Ollama at each launch are in
    [results/d7/](experiments/brownfield-baseline-20261028/results/d7/).
  - Tokens and cost are not measured on this host, so cost compares in minutes and turns only.
  - Laptop sleep: the machine slept 13:00-13:47 before any of these runs started, so none of them include it.
- **Evidence.** [before-runs.json](experiments/brownfield-baseline-20261028/results/d7/before-runs.json), built by
  [d7_summary.py](experiments/brownfield-baseline-20261028/d7_summary.py) from each run's `result.json` and `metrics.json`.

  | Run | Held-out checks | Visible checks | Planning window (Improve) | Run | Refusals |
  |---|---|---|---|---|---|
  | `user-listing` (149 lines) | 11/11 (2 pass-to-pass, 9 fail-to-pass) | 3/3 | 17.4 min (10.0) | 68.1 min | 25 |
  | `ticket-assignment` (3,631 lines) | 18/18 (6, 12) | 3/3 | 30.1 min (17.2) | 110.5 min | 27 |
  | `ticket-escalation` (follow-on) | 14/14 (7 kept from run 1, 7 new) | 9/9, with 4 retention | 48.7 min (25.7) | 138.6 min | 18 |

- **Correctness: no gap.**
  - Every latent fact was kept: LA1-LA8, and LB1-LB5 on the follow-on.
  - Both planted defects were fixed: `paginate`'s partial last page, and the OR filter.
  - The follow-on broke none of run 1's behaviour.
  - This repeats X3 and X3b (Sonnet) on the E2E subject. On these cases, neither a single run nor a second run needed a
    recorded baseline to stay correct.
  - Limit of the instrument: 3,631 lines fit in the host's context (peak 157-160K), so "too big to read" is untested.
- **Discovery is not where the reading happens.** Discovery took 0.6, 1.6 and 2.4 minutes. The model read the code in
  spec, step-plan and implement.
- **Planning: Improve is 53-58% of the window** (10.0 of 17.4, 17.2 of 30.1, 25.7 of 48.7 min).
  - The spec stage's own authoring took 0.6, 0.5 and 1.4 min; its Improve review took 2.2, 6.2 and 7.5 min.
  - The 2026-10-05 ledger found the same share on Luna xhigh (54%).
- **The follow-on's planning grows where it works on larger living files.**
  - Authoring: test-strategy 6.6 against 2.3 min, step-plan 5.5 against 2.8 min.
  - Improve: test-strategy 9.5 against 5.2 min, step-plan 6.5 against 2.5 min.
  - Carry-forward: 14.7 against 9.5 min in total.
  - `environment.md` was 72 KB after run 1 and 87 KB after run 2. The spec went from R-1..R-12 to R-1..R-20.
  - Run 2's harness plan names only its own requirements (R-13 to R-18, R-20), so test-strategy did not re-plan run 1's.
    The growth is in reading and reviewing bigger files, not in re-testing old requirements. Status: interim; one
    follow-on.
- **Refusals.**
  - Size limits: 3-5 per run.
  - Improve protocol: `--check-only` at Improve, and a skipped skill call at a new Improve.
  - Lint at Improve: 6 of 6 lint refusals named the Improve action while lint wanted the reviewed step's. Fixed in
    18844f21 (first made as d0916465 on `claude/priceless-hertz-be6123`, which is not merged). The harness stored those
    refusals without their text; fixed there too, 8764d1b1 (first e740819b).
  - Quality gates: mutation, expectations, evidence, and the primary-coverage gate.
  - Every refusal was recovered.
- **What it means for the design.**
  - Section 10's as-is account has no correctness gap to close on these cases.
  - The measured costs are Improve at planning and growing living files.
  - D6's "30-minute planning window" was a misreading of the owner's alarm threshold.
  - The owner's answer, 2026-10-28: "I don't want to have a 30-minute planning session at all." The plan that follows
    is [docs/shiploop-planning-speed-and-caps-plan-2026-10-28.md](shiploop-planning-speed-and-caps-plan-2026-10-28.md).

