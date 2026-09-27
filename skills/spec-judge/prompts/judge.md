# Judge a spec against its repository

**Intent.** Someone will rely on this spec instead of reading the
repository. Find where it says more than the repository supports
(**over-spec**) and where the repository does or promises more than it says
(**under-spec**). Judge only what is written, from the source; do not improve
the spec.

**Inputs.** `sample.json` (written by `spec_judge.py sample`) names the
repository (`repo`), the spec (`spec`), an optional architecture file, and the
items to judge, drawn at random by the script: `requirements`, `tests`,
`sources`, `readme` and `architecture`. Its `anchors` block is the mechanical
anchor check; it is context, not something to redo.

## Verdicts

**requirements** (over-spec). Read the requirement, follow its anchors and
check the code, tests or docs that decide it.
`correct` every statement holds · `partial` the main statement holds but a
detail is wrong or missing (name it) · `wrong` the main statement does not
hold · `unverifiable` the repository does not decide it.

**tests** (under-spec). Find the requirement(s) that state the behaviour the
test checks. `covered` (list IDs) · `partly` (a requirement exists but misses
the tested case) · `missing` · `internal` (plumbing no user or caller can
observe; say why).

**sources** (under-spec). Name the user- or caller-visible responsibility
the file carries (behaviour, option, output, error, contract) and whether the
spec or architecture file states it. `covered` (IDs or section) · `partly`
(name what is missing) · `missing` (name what should have been specified) ·
`internal` (pure plumbing; say why).

**readme** (under-spec). The README states purpose, features, options,
examples and promises. For the section at `at`, is each requirement it states
in the spec? `covered` (IDs) · `partly` (name what is missing) · `missing` ·
`not-a-requirement` (badges, credits, contribution process, links).

**architecture**. Is the item answered in the architecture file (or the spec)
and true of the code? `answered-true` · `answered-false` · `vague` (too
general to act on) · `absent`.

## Output

Write `verdicts.json` next to `sample.json`:

```json
{"requirements": [{"id": "R-3", "verdict": "correct", "evidence": "path:line", "note": ""}],
 "tests": [{"test": "...", "file": "...", "verdict": "covered", "ids": ["R-3"], "note": ""}],
 "sources": [{"file": "...", "verdict": "missing", "ids": [], "note": "what should be specified"}],
 "readme": [{"section": "...", "verdict": "partly", "ids": ["R-7"], "note": ""}],
 "architecture": [{"item": "...", "verdict": "answered-true", "evidence": "path:line", "note": ""}]}
```

Every sampled item appears exactly once, keyed exactly as in `sample.json`,
with evidence citing the repository. Then run `spec_judge.py score` and
report its grade.
