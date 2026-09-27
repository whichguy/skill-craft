# Repo distill: results

Case typicode/json-server @89a34a4. Execution Grok 4.7 medium; judge Opus 5.5
medium. Products and transcripts are disposable (session scratchpad), never
committed.

## E1 distill, round 1 (rev-1 prompt), 2026-09-27

- Exit normal: 33 turns, $0.82, 1,920 s wall.
- Spec: 676 lines; 80 claims (D-1..D-80), 5 unknowns each with a default,
  sections for launch, database file, HTTP interface (headers, errors,
  routes, homepage, static files, filters, sort, pagination, embed, writes),
  relationships and left-free.
- `spec_check.py`: pass after a checker fix: 141 citations resolve (10 cite
  dependency source without the `node_modules/@` prefix), 0 claims without
  evidence, original name absent.
- The distiller probed the running original to confirm behaviour.

## E0 oracle port, round 1 (rev-1 prompt), 2026-09-27

- Exit normal: 55 turns, $1.15, 1,531 s wall.
- 6 test files plus a shared harness; every original test mapped, including
  the broken-import adapter file (its two behaviours ported as black-box
  checks). Readiness is a seeded token served at `/oracleReady`, so a check
  knows it reached the program it started.
- First admission crashed: the stub run cannot finish (item 28).
- Admission rerun (bounded stub): **admitted**. 123 checks pass on the
  original in both runs (no flakes, ~8 s per run, well inside the harness's
  180 s check timeout); none pass on the stub (it timed out after 180 s
  with 7 file-level failures reported and every other check unreported).

## E3 baseline rebuild on json-server: not completed

Killed at ~30 min when the watcher that launched it expired (plan item 35);
not rerun because the owner switched the pilot to marked. The partial build
had a `package.json`, `src/` and a `schema.json`.

# Case markedjs/marked @ef0704c (the pilot from here on)

## E0 oracle port, round 1 (rev-3 prompts), 2026-09-27

- Exit normal: 53 turns, $1.37, 1,143 s wall.
- 1,759 black-box checks across specs, lexer, parser, hooks, instance,
  module and CLI; reached through `APP_CMD` (CLI) and `APP_MODULE` (the
  package's import entry). MAPPING.md: every original test mapped; 4 not
  observable (type checks, benchmark, regex dump, static ReDoS scan), 1
  excluded (the fixture updater).
- Admission: **admitted** first time. 1,759/1,759 pass on the original in
  both runs, no flakes; 0 pass on the CLI and library stubs. One oracle run
  takes ~1 s, far inside the harness's 180 s check timeout.

## E1 distill, round 1 (rev-3 prompts), 2026-09-27

- Exit normal: 43 turns, $1.88, 1,832 s wall.
- Spec: 4,262 lines, 1,200 claims, 1,799 resolving citations; CLI, module
  API, class, pipeline, errors, extensions and hooks, then the Markdown
  grammar and rendering rules.
- `repo_value.py --spec`: 1% of evidence cites dependency code (material).
- `spec_check.py` findings:
  - leaks: the original name appears in **evidence file paths**
    (`src/marked.ts`, `bin/marked.js`, ...). Structural, not a distill
    fault: citations are for verification. Fix: the builder receives the
    evidence-stripped view (`builder_view`), and leaks are checked there.
  - one real prose leak in that view: "`--tokens` calls
    `marked.lexer(...)`" (distill fault; the branded-value rule was in the
    prompt). Recorded, not hand-patched.
  - one citation to a nonexistent `hash.js` (distill fault).
  - checker fixes: whole-file fixture citations count as evidence; a range
    may end one line past a file's last line (trailing newline).
- The first E3 launch received the evidence-bearing spec (the chain started
  it before the builder view existed); it was stopped after ~3 min and
  voided (`rebuilds/m1-void-evidence-leak`). E3 restarted on the 3,042-line
  builder view.

## T1 baseline rebuild on marked, two builders, 2026-09-27

Same evidence-stripped spec (3,042 lines), empty directory, web off, host
isolation (Claude: project settings only; Codex: CODEX_HOME with only the
sign-in). Both clean-room checks clean; neither transcript names the original.

| Builder | Oracle (1,759) | Wall | Spend |
|---|---|---|---|
| Claude Sonnet 5 | **1,452 pass (82.5%)**, 307 fail | 2,241 s, 103 turns | $8.88 |
| Codex **gpt-5.6-luna** (wrong model; owner wants GPT-6 Luna), xhigh | 1,199 pass (68.2%), 560 fail | 2,110 s, 89 commands | 17.0M input (16.7M cached), 102k output tokens |

Failures concentrate in the CommonMark/GFM spec examples (Sonnet: 96/652
CommonMark, 99/680 GFM; Luna about twice that). Sonnet is the T3 builder.

Scoring finding (plan item 40): raw scores were 35 and 31 because the oracle,
admitted against the original, imports the original's export names (`Marked`,
`marked`), while the spec renamed the product and both rebuilds correctly
export `Mdkit`/`mdkit`. Scoring now loads the rebuild through an alias module
(`--rename marked=mdkit --rename Marked=Mdkit`; the case check uses
`ALIASES=`) that falls back to the new name only where the original name is
missing. Attribution's first attempt read nothing: its inputs were symlinks
outside the sandboxed judge's directory; they are now copied in.

## T2 attribution of the Sonnet T1 rebuild, 2026-09-27

One Opus 5.5 judge (medium), copied inputs: 621 s, $24.74 (above the $15
cap passed to the CLI: the cap is checked after the fact, plan item 42).
Every one of the 307 failing checks attributed exactly once, 26 root causes:

- **distill:error — 2 checks, 1 cause.** D-658 says a duplicate link
  definition overwrites the earlier one; the original keeps the first
  (`src/Lexer.ts:218`). The rebuild followed the claim. Verified by hand.
- **build:implementation — 305 checks, 25 causes.** Largest: emphasis
  without the delimiter stack (70), link masking left as a no-op stub (34,
  verified: `maskReflinks` returns its input), block grammar (32), HTML
  blocks (27), block quotes (24), a list/tab crash hidden by silent mode (17),
  fenced code (17), lists (14), pedantic mode (13), ReDoS timing (7).
- **distill:omission / ambiguity, oracle, unattributed: 0.**

Reading: the spec carried the product (0.7% of failures trace to it). The
builder's losses share one generic shape: it did not turn the spec's named
conformance suites and stated claims into tests before finishing, and it
shipped a stub. That is exactly what ShipLoop's test-first and Until-Loop
stages are meant to prevent, which T3 measures on the same spec and model.
Two judge fixes also carry a distiller lesson: verify a code-derived claim
at the guard that decides it, and state a rule for every form it applies to.

Correction (owner): "Luna" means **GPT-6 Luna** (`gpt-6-luna`) at xhigh. The
Luna T1 above ran `gpt-5.6-luna` (a stale local model reference), so it does
not measure GPT-6 Luna; T1 is rerun on `gpt-6-luna` (rebuilds/l2).

## T3 ShipLoop on marked, Claude Sonnet 5 (partial), 2026-09-27

Released ShipLoop 0.44.1 (checkout build), seeded evidence-stripped spec, same
oracle. Session 1 ended on an account rate limit (240 turns, $10.29); resumed
in place with `--resume-run`; the resumed session stopped at its $30 cap.
Total 701 turns, $36.47, ~88 min, 0 model glue. ShipLoop paused cleanly after
**work item 1 of 4** (core CommonMark engine) and starting item 2.

- Oracle on the product at that point: **1,171 / 1,759 (66.6%)**, vs the
  plain Sonnet session's 82.5% for $8.88 in 37 min. Items 2-4 (GFM variants
  and extensions, pedantic, CLI/extension surfaces) were not built.
- Costliest stages: implement 65 turns/16.0 min, step-plan 59/8.7,
  static-checks 54/5.0, implement 49/8.7, spec 37/4.6.
- Not resumed: the owner moved builders to GPT-6 Luna, and finishing three
  more items on Sonnet would cost real spend; the GPT-6 Luna max pair
  carries the ShipLoop comparison.

Waste review (owner, 15:20): the Luna xhigh ShipLoop run was stopped in
preparation (superseded by the max pair); the Luna xhigh T1 finishes as the
xhigh-vs-max datapoint.

# Phase 2A: initializer distill audit, round 1 (GPT-6 Luna max), 2026-09-27

Four repositories from the star-ordered walk, each distilled by
`skills/repo-distill/prompts/initialize.md` (README primary; architecture
with A-n; pre-orthogonality wording) in a temporary clone, then graded by
the spec-judge skill under one Opus 5.5 judge (sample n=40; about $1.60 per
judge run).

| Repo (shape) | Reqs | Unanchored | Wrong/partial | Tests missing | Sources missing | README missing | Arch true |
|---|---|---|---|---|---|---|---|
| marked (library + CLI) | 37 | 5.4% | 2.7% | 12.8% | 31% | 0% | 90% |
| Figma-Context-MCP (MCP server) | 34 | 0% | 2.9% | 15% | 40% | 0% | 90% |
| webpack-bundle-analyzer (CLI + UI), v1 / v2 grader | 27 | 7.4% | 3.7% / 14.8% | 10% / 0% | 53% / 60% | 0% / 6% | 80% / 90% |
| mocha (test runner), v1 grader | 34 | 50% | 17.6% | 45% | 95% | 0% | 80% |

marked also got the leakage measures: spec names implementation 2.7% (one
requirement names TypeScript declarations and `test:types`), architecture
restates behaviour 0%.

Readings:
- Accuracy is good where anchors are present; mocha's misses are inferred
  behaviour stated as fact (a CI-driven `--forbid-only` default that no code
  implements).
- The README rule holds everywhere (0-6% missing).
- Under-spec concentrates in source files: partly the v1 grader counting
  internal mechanisms (fixed: only contract-level gaps count), partly real
  coarseness (topic-level requirements from "group related behaviour").
- The judge varies: re-grading the same webpack-bundle-analyzer spec moved
  wrong/partial from 1 to 4 of 27. Round 2 grades each spec twice on the
  same sample.

Grader defects fixed during round 1: the judge saw only spec and
architecture (build/test commands live in environment.md); skipped tests
counted as missing; duplicate test names across and within files broke the
score step.

Round 2 (running): the same commits, the contract-level orthogonal
initializer (spec survives a stack change, architecture survives a spec
change; anchor or omit), each spec judged twice.

## T1 on marked, GPT-6 Luna at max, 2026-09-27

`gpt-6-luna`, `model_reasoning_effort=max`, isolated CODEX_HOME, same
evidence-stripped spec and aliased oracle: **1,385 / 1,759 (78.7%)**, 3,133 s,
73 commands, 19.0M input tokens (18.6M cached), 154k output (98k reasoning).
Clean room clean, no recognition. Plain-session ranking on marked so far:
Sonnet 5 82.5% (37 min) > GPT-6 Luna max 78.7% (52 min) > GPT-5.6 Luna xhigh
68.2% (35 min); GPT-6 Luna xhigh still running.

## T1 on marked, GPT-6 Luna at xhigh, 2026-09-27

**1,334 / 1,759 (75.8%)**; 6486.9 s, 158 commands, 38880036 input (38206464 cached), 280790 output. Clean room clean. So on marked,
**max beat xhigh by 2.9 points (78.7% vs 75.8%) and finished far sooner**
(52 min vs about 1 h 50 min): the extra reasoning per step cut the
run-and-fix cycling (73 commands vs over 300). Plain-session ranking:
Sonnet 5 82.5% > GPT-6 Luna max 78.7% > GPT-6 Luna xhigh 75.8% > GPT-5.6
Luna xhigh 68.2%. One run each; not repeated.
