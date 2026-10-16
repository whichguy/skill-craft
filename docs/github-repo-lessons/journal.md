# High-star GitHub repos: how they achieve their results (2026-10-11)

Question: which popular repos hold real insight on prompt design and on driving models through an SDLC, and
by what mechanism (not what the README says).

Method: 15 repos, 5 subagents x 3 repos. Each read prompt, template, hook and script files and recorded
mechanisms with file paths. Stars from `gh api` on 2026-10-11. Evidence: `evidence/lessons-A..E.md`.
Status of every finding: **interim**. Findings are the subagents' reading of the files. The lead spot-checked none
of them against the repos yet; the items under "Check before relying" are the ones most worth verifying.
ShipLoop comparison has NOT been done; the "fit" column is a hypothesis from the lessons only.

## Repos studied

| Group | Repo | Stars |
|---|---|---|
| A | x1xhlol/system-prompts-and-models-of-ai-tools | 143,952 |
| A | asgeirtj/system_prompts_leaks | 69,387 |
| A | repowise-dev/claude-code-prompts (reconstruction, not leaks) | 1,210 |
| B | github/spec-kit | 140,793 |
| B | Fission-AI/OpenSpec | 71,614 |
| B | bmad-code-org/BMAD-METHOD | 54,027 |
| C | obra/superpowers | 297,427 |
| C | affaan-m/ECC (was everything-claude-code) | 276,869 |
| C | gsd-build/get-shit-done | 64,325 |
| D | anthropics/skills | 180,434 |
| D | anthropics/claude-code (plugins) | 150,157 |
| D | snarktank/ralph (Ralph loop) | 21,939 |
| E | openai/codex | 128,624 |
| E | Aider-AI/aider | 49,467 |
| E | SWE-agent/SWE-agent + mini-swe-agent | 20,522 + 8,391 |

## Ranked lessons (mechanism first)

1. **Make "confirm" into "show evidence".** ECC GateGuard (`scripts/hooks/gateguard-fact-force.js`) denies the first
   edit of a file until the agent states concrete facts (importers, public API, quoted instruction); the retry passes.
   Its header says yes/no questions always get "yes". Same idea in repowise's verifier: each check is a command plus
   verbatim output, the report ends in a literal `VERDICT:` line, and the caller re-runs commands and rejects the whole
   report on a mismatch. Why it works: evidence fields can be checked by a script; a confirmation cannot.
2. **Reviewers are told not to trust the author.** Superpowers `task-reviewer-prompt.md` ("Do Not Trust the Report",
   reads a diff file); GSD verifier starts from "goal not achieved" and treats SUMMARY.md as non-evidence; BMAD
   `claims-check.md` treats the plan as "testimony, not evidence" and reads claims only after tracing code.
   The ordering (trace first, read claims last) stops anchoring.
3. **Fresh context per unit, state in files.** Ralph restarts the process each pass (state: `prd.json`, append-only
   `progress.txt`, `AGENTS.md`, git); GSD runs wave-ordered fresh executors; Superpowers builds each subagent's context
   instead of inheriting it. Ralph's only enforced parts are the loop counter and a grep for a completion string.
4. **Size work by context cost.** GSD plans fit ~50% of a window, 2-3 tasks each (TDD gets its own plan);
   Ralph stories must fit one window and have checkable criteria ("Typecheck passes"); BMAD proposes 900-1600 tokens.
5. **Output format beats stronger prompting.** Aider: GPT-4 Turbo 20% with SEARCH/REPLACE vs 61% with unified diffs on a
   laziness benchmark (`aider/website/docs/unified-diffs.md`). Codex `apply_patch` is a Lark-grammar freeform tool with
   no line numbers and a lenient parser (`seek_sequence.rs`, `parser.rs`). The benchmark was built before the change.
6. **Reject-and-explain inside the tool, with a retry cap.** SWE-agent lint-gated `edit` shows would-be and original code and
   says the edit was not applied; Aider returns "did you mean" lines and which blocks already applied, reflections capped
   at 3; mini-swe-agent classifies truncation vs missing tool call, cap 3 format errors.
7. **Stage graph owned by code, completion by artifact.** OpenSpec `schema.yaml` declares artifacts with `requires`;
   a stage is done when its file exists (`artifact-graph/state.ts`); instructions are served per step by the CLI.
   BMAD plan frontmatter `status` routes each step; intent sits in `<frozen-after-approval>`.
8. **Delta spec merged by code that refuses conflicts.** OpenSpec ADDED/MODIFIED/REMOVED/RENAMED deltas; `specs-apply.ts`
   throws on duplicates and cross-section conflicts; MODIFIED must carry the full block. Closest to a
   feature-spec-into-persistent-spec lifecycle.
9. **Cap ambiguity mechanically, give every question a default.** spec-kit: `[NEEDS CLARIFICATION]` capped at 3
   (greppable), clarify stage max 5 questions each with a recommended answer. Caveat: caps are prompt-enforced, not code.
10. **Lint shape before each handoff; name the silent failures in the prompt.** spec-kit task line
    `T012 [P] [US1] path`; OpenSpec warns that "exactly 4 hashtags" else the parser fails silently;
    BMAD `lint_spine.py` runs before reviewers (placeholders, duplicate AD ids, missing Binds/Prevents/Rule).
11. **Exit by a tool call the harness can validate.** Plan mode ends only via ExitPlanMode or AskUserQuestion;
    Devin `suggest_plan`; Kiro approval question. Mandatory `think` points fire on state transitions
    (before edit, before "done"). A script that knows the transition can require the answers.
12. **Skill descriptions state the trigger, never the workflow.** Superpowers records a failure where a summarising
    description led to one review instead of two. anthropics/skills says descriptions should be "pushy" and tunes them
    on a 60/40 train/held-out split (`scripts/run_loop.py`).
13. **Pressure-test rules against a no-skill baseline.** Superpowers `testing-skills-with-subagents.md` (RED/GREEN/REFACTOR for
    prose); anthropics/skills runs with-skill vs without-skill graded by `agents/grader.md`. Rationalisation tables list the
    exact excuses seen in failed runs.
14. **Independent validator per finding.** claude-code `code-review.md`: cheap haiku gate, 4 parallel reviewers, a separate
    validator per finding, unvalidated findings dropped; a "Do NOT flag" list. Codex review rubric: flag only
    discrete, actionable issues introduced by this change.
15. **Hooks are the only hard enforcement.** claude-code phase gates are prose; the real controls are hookify and the
    ralph-wiggum Stop hook. ECC `block-no-verify.js` and `config-protection.js` stop agents editing linter config;
    GSD context hook tells the model its remaining context at 35% and 25%.
16. **Read-only by tool list, then repeat the bypasses.** Explore agent removes Edit/Write and the prompt names redirects,
    heredocs and /tmp files. Role = (prompt, tool list, model).

## Surprises worth keeping

- Ralph, the most-copied loop, enforces only an iteration cap and a grep for `<promise>COMPLETE</promise>`.
- ECC has 311 skills; its best idea is one hook.
- The flagship code-review plugin moved from a numeric confidence threshold to a validator per finding.
- Anthropic's skill guide says to explain why instead of using MUSTs; the production pdf/docx skills use scripts and MUSTs.
- mini-swe-agent: bash only, linear history, claims >74% on SWE-bench Verified (README claim, unchecked).
- BMAD abandoned chat personas for script-resolved config and a status state machine.
- No repo studied has a script that owns the whole loop and validates every step's exit; that is the gap a
  script-driven harness fills.

## Check before relying

- repowise is an independent reconstruction; treat as ideas, not vendor behaviour.
- The claude-code code-review plugin having no numeric score today (group D) contradicts common descriptions.
- OpenSpec `archive.ts` merge logic and BMAD step-04 review internals were skimmed only via grep.
- Codex `codex-full.md`, `codex-auto-review.md` and Claude Code `compact.md` were not fully read; per-model dumps were not diffed.
- Aider and mini-swe-agent benchmark figures are the repos' own claims.
- Other Ralph variants (frankbria 9,678 stars) not read.

## Next

Compare each lesson with what ShipLoop already does and list gaps. Not started.

## Round 2: deep dives (2026-10-11)

Question: for nine techniques, how exactly is each achieved, with real prompts and outputs, limited to what matters
for Claude 5-era models. Method: six subagents read full files in shallow clones; output is `evidence/deep/*.json`
(overview, steps, examples, pitfalls, model-era note, what would change). Loaded into the Technique Atlas cards.
Status of all findings: **interim** (agent readings; items the agents could not run are marked unverified in each file).

Key findings:
- **Context sizing is not measured anywhere up front.** GSD's ~50% per plan and 10-30% per task are prompt heuristics; the
  plan checker is an LLM counting tasks and files. Ralph and BMAD are advisory. GSD measures remaining context only after
  the fact (`hooks/gsd-context-monitor.js`, 35%/25%). Token estimates are only estimates, and Claude 4.7+ tokenizers yield
  ~30% more tokens, so chars-per-token rules are stale. (`evidence/deep/size-by-context.json`)
- **Ambiguity caps are prompt-only in all three repos.** spec-kit's cap of 3 markers is not counted by any code. BMAD's headless
  mode (assumptions[], open_questions[], status blocked) is the closest to unattended use. Risk: a default accepted with "yes"
  looks the same as a real answer. (`cap-ambiguity.json`)
- **Stage graph.** OpenSpec completion is file existence only (an empty file counts). BMAD routes by LLM-written frontmatter
  status; code only renders steps and classifies tickets. Neither makes downstream stages stale when upstream changes.
  (`code-owned-stage-graph.json`)
- **Delta merge** order is RENAMED, REMOVED, MODIFIED, ADDED. No base fingerprint, so two open changes to one requirement
  can overwrite each other; REMOVED Reason/Migration are demanded but never checked. The default archive skills have the agent
  merge; only the CLI uses the code merge. (`delta-spec-merge.json`)
- **Handoffs.** Four techniques: model summary at compaction, model-written files after each unit, script-written ledger
  after a passing check (Superpowers `task-done`), and hook re-injection. Codex frames the summary with a fixed prefix.
  (`handoff-for-a-successor.json`)
- **Loop control.** Code-enforced: Ralph counter plus sentinel grep, mini-swe-agent limits before each model call, SWE-agent
  typed exits. No repo detects the same failure repeating; a fingerprint-based design is proposed (not from any repo).
  (`stop-is-script-owned.json`)
- **Trigger-only descriptions.** Documented failure in Superpowers `writing-skills`: a description saying "code review between
  tasks" caused one review instead of two. Anthropic's guidance (describe what and when, be "pushy") conflicts with it.
  `run_loop.py` measures whether a skill is consulted, not whether its body is followed. (`trigger-only-descriptions.json`)
- **Baseline tests.** Superpowers' own spec records Opus producing 0 placeholders in 60 plans with or without its rule: run the
  no-guidance control first. No raw baseline transcript or real grading.json exists in either repo. (`baseline-pressure-test.json`)
- **mini-swe-agent** bash-only scores (one attempt): Claude 4.5 Opus 76.8%, 4.6 Opus 75.6%; no Claude 5 row found.
  (`bash-only-baseline.json`)

Model-era tags added to cards: `format-over-prompt`, `repo-map`, `reject-and-explain`, `size-by-context`,
`handoff-for-a-successor`, `bash-only-baseline` are "mixed" (rationale partly GPT-4-era).

Check before relying: BMAD and OpenSpec issue statuses (#2033, #1387, #1697, #1246, #1112) came from WebFetch summaries;
reconstructed status/instructions JSON and the worked merge example were built from code and docs, not run.

## Round 3: linking and grounding (2026-10-11, 07:10 PDT)

Owner rule: href and ground as much as possible (memory `always-href-and-ground`).
- Every file reference on every Atlas card was resolved against the live GitHub file tree of its repo
  (`tools/build_refs.py`, trees fetched with `gh api repos/<r>/git/trees/HEAD?recursive=1`).
  Result: 312 references, 235 verified file links, 6 unresolved (search-link fallback, listed in
  `tools/unresolved-2026-10-11.txt`), 16 web links all returning HTTP 200 (`tools/urlcheck-2026-10-11.json`).
- 64 curated claims, each linked to the file that shows it (`tools/claims.py`; every path verified before use).
- Page auto-links repo names, known paths and URLs inside card text; a bare file name links only when unambiguous in that card.
- Verified by reading source: SWE-bench experiments `evaluation/verified/20260217_mini-v2.0.0_claude-4-5-opus-high/metadata.yaml`
  (76.8%, $0.75/instance, reasoning effort high) and `..._claude-4-6-opus/metadata.yaml` (75.6%, $0.55).
- Status: interim. Links prove a file exists at HEAD, not that the claim text matches it; file paths may move over time.

## Round 4: counter-evidence and verdicts (2026-10-11, ~07:25 PDT)

Question: for each technique, who disagrees, and is there well-substantiated evidence of failure? Method: six subagents
searched adversarially (neutral queries such as "X fails", "problems with X"), opened each source, rated evidence quality
(strong / moderate / anecdotal) and flagged model era. Output `evidence/counter/*.json` (27 cards: the 22 techniques plus 5
cross-cutting questions); all 109 cited URLs returned HTTP 200 (`evidence/counter/urlcheck-2026-10-11.json`). Loaded into
the Atlas as `counter` on each card and a written overall conclusion (`tools/build_counter.py`).
Status of all findings: **interim** (many PDFs, issue bodies and secondary summaries were read as abstracts or snippets;
each is marked in the card data).

Verdicts, 22 techniques: 14 hold with conditions, 7 contested, 1 refuted (read-only by tool list, as a security boundary).
Cross-cutting: 3 contested, 1 holds (agents tamper with tests and guards), 1 insufficient evidence (AI review reducing defects).

Spot checks by the lead:
- OpenSpec issue #2033 verified: opened 2026-10-02 by a maintainer, still open, asks whether to stop merging specs deterministically.
- Claude Code issue #31292 verified: `disallowedTools [Write, Edit]` bypassed via Bash; it is now closed (reason not checked).
- **A correction to a correction.** The adversarial agent reported it could not find "0 placeholders in 60 plans". The lead read
  `docs/superpowers/specs/2026-06-10-positive-instruction-redesign-design.md` in obra/superpowers: 0 placeholders in 20 plans, then
  40 of 40 clean on a 10-task spec, with and without the banned-patterns list. The original claim was right; the agent had searched
  the PRs, not the spec file. The baseline card was fixed and now links the spec.

Largest findings: relevance matters more than fill for context (Opus 5 flat with unrelated padding to 500k, about 15% loss with
task-related context at 250k); script-checked evidence beats model-written evidence; SWE-bench Verified was dropped by OpenAI
(at least 59.4% of audited failing problems had tests rejecting correct solutions; seen via a secondary source); delta-spec merge
is contested by OpenSpec's own maintainers (46 fix commits since June).

Open experiments that would settle verdicts (none run): sequential fresh stages vs one long session on Claude 5; authored
handoff vs raw transcript; prompted cap vs script cap; each prompt rule vs a no-guidance control.

## Round 5: ShipLoop versus the Atlas (2026-10-11, ~08:20 PDT)

Question: compare ShipLoop with each atlas technique and say what, if anything, passes YAGNI and KISS.
Target: published origin/main at commit 4b1759ac16a13953570f8f12f06f32b4da6ec866 (committed 2026-10-11 07:48 PDT),
exported read-only with `git archive`. The local checkout was 445 commits behind origin/main with uncommitted ShipLoop edits,
so it was not used. Five subagents compared 27 cards (`evidence/shiploop-compare/*.json`); all 189 evidence paths were checked
to exist in the export. Artifact: https://claude.ai/artifact/CHiMb8KsER5RBCepJ7Ytqu (db collections `comparisons`, `meta/summary`;
builder `tools/build_compare.py`). Status of findings: **interim**.

Tests used: YAGNI pass = recorded evidence in this repo of a failure or cost in a normal run (or a pure deletion). KISS pass =
smallest version touches at most one script and one prompt paragraph, no new state file/mode/flag, no net added complexity.

Result: 27 comparisons: 15 already covered, 6 skip, 4 watch, 2 consider, 0 adopt.
- ShipLoop already holds what survived the counter-evidence: script-side verification (runs recorded commands, reads counts from
  runner output, new tests must fail on base, mutation checks) and refusals that name the reason and exact correction.
- Where it differs from the repos (in-place spec edit with R-ID retention instead of delta merge; inline by default; no validator
  agents, repo map, tool-list restrictions or per-model forks) the counter-evidence backs ShipLoop.
- Worth doing anyway (none are skill changes): (1) replay saved runs for self-attested `exit_assessment` receipts, already listed as
  the top open gap in docs/shiploop-artifact-flow-2026-10-11.md; (2) grep waiver, `red_na`, `retired_tests` reasons; (3) count
  `awaiting.no_default` refusals at early stages, then decide on the `requirements-definition.md` "obtain the missing decision"
  sentence that reads against S-14; (4) one bare-model control run (about 3 runs, $10-20) before trimming planning scaffolding;
  (5) delete the stale Hermes row in references/host-matrix.md (found along the way; local copy has uncommitted edits).

Lead spot-checks: MAX_REFUSED_RUNS = 11, STUCK_CONTINUATIONS = 22, GENUINE_FIX_ATTEMPTS = 7, MAX_REVISES = 2 exist as stated;
baselines.jsonl rows for claude-sonnet-5-5: 25 of 25 pass; hello avg $3.77 (15 runs, 179 turns), checkers $4.50 (6), battleship
$6.32 (4); the Hermes row is on line 21 of host-matrix.md; requirements-definition.md line 53 has the "obtain the missing decision"
wording. Caveat: in most cells ShipLoop's own evidence is n=1 run, so several YAGNI failures mean "no failure recorded", not
"idea is wrong".
