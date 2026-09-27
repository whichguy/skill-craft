---
name: spec-judge
description: >
  Grade a spec against the repository it describes, in both gap directions:
  over-spec (requirements the code does not support: missing or broken
  path:line anchors, wrong or partial claims) and under-spec (tests, source
  files and README promises the spec never states), plus architecture
  coverage. Works on any spec with R-n requirement IDs: a distilled or
  initialized ShipLoop spec, or a hand-written one. Invoke as /spec-judge
  <repo> <spec>, "judge this spec", "is this spec complete and accurate",
  or "grade the distilled spec".
version: 0.1.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  skill_craft:
    kind: script-backed
---

# /spec-judge

A spec is only useful if what it says is true of the repository and it says
what the repository does. This skill measures both, from the source, with
samples a script draws so the judge cannot pick easy items.

## Invocation

```
/spec-judge <repo> <spec> [--architecture <file>] [--n 40]
```

`<spec>` holds requirements with IDs `R-1`, `R-2`, ... that cite
`path:line` anchors (for example `docs/shiploop/spec.md` written by
`/repo-distill` in initializer mode). Scripts live in `scripts/` next to
this file.

## Steps

1. **Sample** (script):
   `python3 scripts/spec_judge.py sample --repo <repo> --spec <spec> [--architecture <file>] --out <dir>`.
   It checks every requirement's anchors mechanically and writes
   `<dir>/sample.json`: random requirements, tests from the repository's
   own test files, source files, README sections, and the architecture
   checklist.
2. **Judge** (you): follow `prompts/judge.md` and write
   `<dir>/verdicts.json`, one verdict per sampled item, each with evidence
   from the repository.
3. **Score** (script): `python3 scripts/spec_judge.py score --out <dir>`.
   It refuses an incomplete or duplicated verdict set and writes
   `<dir>/grade.json`.

## Reading the grade

| Measure | Direction | Meaning |
|---|---|---|
| `over_spec.unanchored` | over | requirements with no `path:line` anchor |
| `over_spec.broken_anchors` | over | anchors that do not resolve |
| `over_spec.unsupported` | over | sampled requirements judged wrong or partial |
| `under_spec.tests_missing` | under | tested behaviour the spec does not state |
| `under_spec.sources_missing` | under | a file's visible responsibility the spec does not state |
| `under_spec.readme_missing` | under | README promises the spec does not state |
| `architecture_true` | coverage | checklist items answered and true |

Lower is better for every over- and under-spec share; report each with the
sample size behind it. Quote the notes of `wrong`, `missing` and `partly`
verdicts: they are the concrete fixes for the spec or for whatever wrote it.

## Honesty

A verdict without repository evidence is not a verdict. Judge the spec as
written; a gap is a finding even when you know the answer. The sample is the
script's: never replace an item with an easier one.
