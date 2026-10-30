# ShipLoop document stage: review journal

Living journal of the 2026-10-30 review of the inner loop's `document` stage: whether its prompt produces precise,
enterprise-grade documentation (code contracts, argument constraints, tombstones, file and class docs, README and
operator docs) and keeps the knowledge home (spec, architecture, environment) current with durable learnings only. The
proposal it supports is [shiploop-document-stage-proposal-2026-10-30.md](shiploop-document-stage-proposal-2026-10-30.md).
Evidence lives in [experiments/document-stage-20261030/](experiments/document-stage-20261030/).

Owner request (2026-10-30, paraphrased): review the document stage's prompt deeply, research how others build such
prompts, check whether referencing spec, architecture and environment beats dumping prompt text, cover tombstones,
argument validity and checking, file, class and global docs, README and deployment docs, and let the stage update the
knowledge files when a learning is persistent. Side experiments allowed.

## 1. What the stage is today (code read on origin/main 7fce12e4)

| Piece | Where | What it says or does |
|---|---|---|
| Stage row | `shiploop_stage_spec._ROWS`, row `document` | Goal "Update the docs this step's change affects ... from observed behaviour"; three done-when lines (public behaviour documented "where users and maintainers look", reread, knowledge record); `edits={"docs"}` (validated, never enforced); `improve="item"`; complete runs loop-terminal, lint-gate, test-rerun |
| Duty | `shiploop_prompts.DUTIES["document"]` | 7 items: List; Observe and write (README, API, user, operator, error, design docs); Reflect (spec line with step mark, AD-n, environment command; route other work); Baseline; Reread; Commit nothing; send-back/blocked. 2,531 characters before the commit rule |
| Guides linked | `shiploop_prompts` stage guide table, `document` | Documentation guidance (`testing-and-documentation.md#documentation`), Current-system baseline guide. Not House-style guidance, not Code craft |
| Loop contract | `shiploop_loops._build` default `scope`; `WORK["document"]`; `REPEAT["document"]` | Scope: "only the paths its accepted step plan declares, plus docs/shiploop/". Repeat while a public behaviour is undocumented or a reread found a wrong statement |
| Code craft | `shiploop_prompts.CODE_CRAFT` | Rules 2-4 define argument checks, contract docstrings, purpose lines and removed-approach comments. Carried by the implement packet and both Improve review focuses, not by the document packet (`BLOCKS` "code-craft: implement only"). The comment above `CODE_CRAFT` still says implement, test and document carry it, and the comment "What a producer packet prints instead of CODE_CRAFT" has no code under it |
| Commit | `shiploop_stage_spec.ITEM_COMMITS`, `item_scope.commit_scope` | Commits declared paths, the docs path class (`path-classes.json`: `*.md`, `docs/**`, LICENSE, CHANGELOG) and docs/shiploop/ |
| Step plan | `DUTIES["step-plan"]` item 3 | A new public entry point gets a criterion that it carries a contract docstring, confirmed `searched` (a presence search) |
| Review after | `IMPLEMENT_STEP_REVIEW_FOCUS` | The per-step Improve review checks "a public function with no contract docstring, a comment restating code", argument checks, and "a doc that disagrees with the code" |
| Deployment | `DUTIES["release-verify"]` item 11, `DUTIES["operations"]` items 2 and 5 | Update KNOWLEDGE/environment.md only; operations records "support documentation" in `summary`. No outer stage compares the product's operator docs with the observed release; product-acceptance routes doc fixes as add-work |
| House style | `house-style.md#extract-the-house-style` | Records "comment and docstring density", not docstring form or doc tooling; the document packet does not read it |

Design intent, as the reference states it (`testing-and-documentation.md#implementation-constitution` rule 4):
implement writes the contracts, the per-step Improve review checks them after document. The document stage itself
never checks code contracts against observed behaviour.

## 2. Live-run evidence

Run audit by a Sonnet subagent, then spot-checked by hand
([research/document-stage-runs.md](experiments/document-stage-20261030/research/document-stage-runs.md)).

| ID | Finding | Status | Evidence |
|---|---|---|---|
| L1 | In 10 older runs (Claude host, Sonnet 5.5) the document stage changed README.md only; every docstring traces to the implement commit | firm (10 runs) | report table rows 1-10; `git log --follow` on product files |
| L2 | One older slice spent 2 tool calls and 8 s at document | firm (n=1) | `docs/experiments/shiploop-eff-evidence-20261017/artrev/09-document.md` |
| L3 | **Scope defect.** In the 2026-10-29 per-step pilot (Codex gpt-6.1-terra xhigh, ask-agent route) the document stage left README.md unchanged in both steps and wrote the product's API reference into `docs/shiploop/records.md`, inside ShipLoop's knowledge home. Its notes give the reason: "README remains unchanged because this loop's scope is limited to step-plan paths and docs/shiploop/". The loop contract's `scope` (`shiploop_loops._build` default) says exactly that, while the packet's duty says to update the README and `ITEM_COMMITS` commits documentation files | firm (mechanism read in code; 2 of 2 steps on that arm) | `~/e2e-runs/20261029/pilot-terra-ask-agent-32f436/.shiploop-runs/seed/run/loops/nav-0fcdd8adcbe14d8b9dc0b1c86762eb32-contract.json` `context.scope`; its `notes/` file line 2; worktree commits 8b503a1, d70c709 |
| L4 | The inline arm of the same pilot updated README.md (+7, +4) under the same scope text, so the defect bites when a model follows the contract literally | firm (n=1 arm) | `~/e2e-runs/20261029/pilot-terra-inline-32f436` worktree commits 56f7b76, cac33f0 |
| L5 | Terra's code docs in the pilot were compact and accurate: a purpose line and one-line contract docstrings naming each error | firm (n=1) | pilot-terra-inline worktree `src/records.js` |
| L6 | Per-step document reviews: fresh context changed files 2 of 2, inline 0 of 3; release-verify once added work for "a README claim the code did not keep" (1 of 22) | firm, quoted | `docs/shiploop-sdlc-gates-proposal-2026-10-30.md` §2 rows "Document-stage reviews" and "Late catches" |
| L7 | *Superseded 2026-10-30:* "the per-step design defers README by design". Checked by hand: the inline arm did update README; the ask-agent deferral is L3's scope defect, not a design choice | superseded | L3, L4 |

## 3. External research

A Sonnet subagent surveyed about 45 sources
([research/doc-prompt-research.md](experiments/document-stage-20261030/research/doc-prompt-research.md)). The findings
that bear on the proposal, ranked by evidence:

- Text that restates what the repository says costs steps and money; agent-written context files changed resolution
  by about -0.5% to -2% and added about 20% cost, minimal human-written ones gained about 4% (arXiv 2602.11988).
  Add a duty line only for an observed miss.
- Self-review without an external signal does not reliably fix errors (arXiv 2310.01798); executed "document
  testing" tracked comment accuracy where nine consistency detectors did not (arXiv 2406.14836). Mechanical checks
  belong in scripts.
- DocAgent (arXiv 2504.08725): dependency-first context drove quality; its Verifier asks three questions (adds
  information? exposes implementation instead of contract? misses a critical usage fact?).
- Examples carry style in fewer tokens than rules (Anthropic prompting guidance).
- Knowledge admission: an entry belongs in a durable doc only if not derivable from code, it changes later behaviour,
  it is costly to rediscover and it outlives the next refactor; ADR triggers are structure, non-functional
  requirements, dependencies, interfaces and construction techniques (Nygard; arc42 §9).
- "Tombstone comment" is not a standard term; define it once where it is used.
- No study sizes the effect of a documentation prompt's length; only a local A/B can.

## 4. Experiments

Rounds, conditions and results follow. Subject and judge models follow the owner's experiment note: Sonnet 5.5 is
allowed for exploratory rounds; one Opus 5.5 judge per round.

### E1: document duty A (today) against B (proposed), 2026-10-30

- **Question.** Does the proposed duty (contracts at the code, reader placement, drift hint, knowledge admission
  test) produce better documentation than today's, without more volume?
- **Cases.** Three post-implement states built from `test/shiploop_e2e/fixtures/node-base` by
  `harness/build.py`, each with planted defects listed in its `planted` block: S1 Basket (new class, vacuous
  docstrings, comments restating code, removed-approach note, public array bypassing the limit, a spec departing from
  the RangeError convention); S2 rename getUser to findUser (stale mentions in README.md and docs/api.md); S3 GET
  /health (no start, port or route docs; HEAD answers 404).
- **Arms.** A: `DUTIES["document"]`, the row's done-when and `REPEAT["document"]`, imported from origin/main 7fce12e4
  at render time. B: `harness/variant_b.json` plus the drift hint line. Same packet layout as the rendered live
  `07-document` packet (`test/shiploop_e2e/packets.py --offline node-add-function`), except that the Until Loop and
  the callback are replaced by exit and repeat lines and a result file. Packets: `packets/s1-basket-{A,B}.md`.
- **Models and conditions.** Subject Sonnet 5.5 (Agent subagents, default effort, one per arm, confined to the arm
  folder, no commits). Judge Opus 5.5 at medium effort, one judge, blind X/Y order from a seeded shuffle
  (`judge-key-r1.json`), with the planted list as a reference checklist and an instruction not to reward length.
  One repetition per cell.
- **Deterministic results** (`harness/grade.py`, `grades-r1.json`):

| Scenario | Checks A | Checks B | Knowledge lines A / B | Product .md lines A / B | Other |
|---|--:|--:|--:|--:|---|
| S1 Basket | 16/17 | 16/17 | 8 / 4 | 15 / 13 | comment lines 27 / 16 for 18 code lines; ADs 2 / 1 |
| S2 rename | 10/10 | 10/10 | 6 / 0 | 2 / 2 | both fixed both stale mentions |
| S3 health | 12/12 | 12/12 | 4 / 4 | 21 / 15 | A's environment.md holds test counts and a host `pkill` refusal |

  The one failed check in both S1 arms is the grader's file-purpose rule, which a class docstring opening a
  one-class file does not meet; read it as a grader choice, not a miss.
- **Judge results** (`judge/verdicts-r1.json`): B preferred in 3 of 3; totals A 51, B 68 of 75; concision 7 / 13,
  knowledge 6 / 14, contract 12 / 14, reader docs 15 / 14, drift 11 / 13; false or unsupported statements 7 / 3.
  A's included `Platform seen in W1/S1: Node v26.12.1` and an AD-3 for a choice local to one class; B's included the
  run mark `(W1/S1)` in a product source comment and a HEAD answer described with a body.
- **Finding E1-1 (exploratory).** On Sonnet the current duty already produces accurate contracts, a tombstone, the
  drift fixes and the caveats when the packet is clean; its measured misses are volume, one fact in several homes,
  and transient or derivable facts in the knowledge home. The proposed text kept the checks and roughly halved the
  knowledge-home writing.
- **Finding E1-2 (exploratory).** Both S1 arms wrote multi-line JSDoc under a recorded one-line convention without
  saying so; S3-B kept one line "per the architecture convention".
- **Limits.** n = 1 per cell; one subject model; the judge family may favour shorter text (research F3.8), which the
  tied deterministic checks partly answer; the packets omit the Until Loop, so E1 cannot show L3.

### E2: drift hint precision, 2026-10-30

- **Rule** (`harness/stale_mentions.py`): identifier-shaped names (an underscore or a camel hump, 4+ characters) on
  removed lines of non-doc files in the item's diff, absent from every added line and from every tracked non-doc
  file now, searched whole-word in living docs (dated paths, CHANGELOG, journals, LEARNINGS, experiments and archive
  folders excluded).
- **Results.** S2: `getUser` at README.md:7 and docs/api.md:6, the two planted mentions; S1 and S3: none.
  `harness/stale_history.py` over skill-craft's last 30 non-merge commits: first version (any 4+ character token, no
  history filter) 87 hits; with the history filter 30; with identifier-shaped tokens 10, in 3 large refactors, 27
  commits printing none. Spot-check of the 10: a CLI placeholder in README usage text, a host error name, release
  output and a historical audit; no real stale mention in a living doc.
- **Finding E2-1 (measured).** High recall on renames, low noise on ordinary commits, judgement needed after large
  refactors: advisory packet text, never a gate.

## 5. Changes made

### C1: P0, the document loop's scope names the documentation files, 2026-10-30

- **What changed.** `shiploop_loops._build` gives the document stage its own `scope`: the step plan's paths, the
  documentation files this step's change affects (`shiploop_loops.DOC_FILES`, the `docs` path class's globs), and
  docs/shiploop/ for the knowledge record, with "Product documentation (README, API, user and operator docs) stays
  with the product, never in docs/shiploop/". The other stages that used the default scope (test-spec,
  validate-existing, test, carry-forward) are unchanged. Change note:
  `changes/shiploop/document-loop-scope-names-docs.md` (patch).
- **Design choice.** The first version read the globs from `references/path-classes.json` at contract time. The
  quick tier refused it: `test/shiploop-guidance.test.py` (`_knowledge_reads_only`) lets a packet render read only
  the knowledge home and the run baseline, and 9 of its tests failed with "render read evidence: .../path-classes.json".
  The globs are now a constant, and the test pins them equal to the catalog's `docs` class, so the two cannot drift.
- **Why.** L3: the old scope allowed only the step plan's paths and docs/shiploop/, while `ITEM_COMMITS` and
  `commit_scope` commit changed documentation files outside the declared paths. Codex Terra on the ask-agent route
  followed the scope.
- **Test.** `test/shiploop-loops.test.py`,
  `test_document_scope_admits_every_file_the_item_commit_takes_and_no_undeclared_code`: runs the real
  `commit_scope` over declared code, README.md, docs/api.md, an .rst guide, CHANGELOG.md, LICENSE, a nested README,
  docs/shiploop/spec.md and one undeclared code file, then checks that the scope admits each committed path and that
  its globs do not admit the undeclared code file. It also checks that the scope's glob list equals `DOC_FILES` and
  the catalog's `docs` class. Quick tier (`test/run-all.sh --group quick --changed-from 7fce12e4`): 30 of 30 suites
  pass, among them shiploop-loops, shiploop-guidance and shiploop-navigator-contract. It fails on the old scope (no documentation globs listed) and
  passes on the new one.
- **Known gap (not fixed).** The `test` path class comes before `docs`, so an undeclared Markdown file under a test
  folder matches the scope's `**/*.md` but `commit_scope` leaves it uncommitted. No run has written one; the test checks
  the direction that bit (everything committed is in scope).
- **Not yet verified live.** No E2E round has run on the new scope. The proposal's §5 round on Codex Terra (ask-agent
  and inline) would show whether the README is now updated; status of L3's fix: interim until that round.
