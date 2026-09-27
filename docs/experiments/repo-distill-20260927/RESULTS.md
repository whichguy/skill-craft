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
| Codex gpt-5.6-luna, xhigh | 1,199 pass (68.2%), 560 fail | 2,110 s, 89 commands | 17.0M input (16.7M cached), 102k output tokens |

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
