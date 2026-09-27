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
- First admission crashed: the stub run cannot finish (item 28); rerun with
  the bounded stub run pending.
