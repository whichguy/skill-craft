# Judge a spec against its repository

**Intent.** Someone will rely on this spec instead of reading the
repository. The spec is the contract (what users and callers rely on) and
must survive a rebuild on a different stack; the architecture record is the
stack, structure and decisions and must survive a change of the spec. Neither
is meant to reconstruct the exact code, so judge gaps at contract level. Find where it says more than the repository supports
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
hold · `unverifiable` the repository does not decide it. Separately set
`"leaks": true` when the requirement names implementation or stack (a
language, library, module, function or algorithm) that a rebuild on another
stack would not share.

**tests** (under-spec). Find the requirement(s) that state the behaviour the
test checks. `covered` (list IDs) · `partly` (a requirement exists but misses
the tested case) · `missing` · `internal` (plumbing no user or caller can
observe; say why). A skipped or disabled test (`it.skip`, `xit`, ...) states
no current behaviour: mark it `internal` and say it is skipped.

**sources** (under-spec). Name the user- or caller-visible responsibility
the file carries (behaviour, option, output, error, contract) and whether the
spec states it at contract level (for behaviour) or the architecture states
it (for its place in the structure). Internal mechanisms no caller can
observe need not be in either; do not count them as missing. `covered` (IDs or section) · `partly`
(name what is missing) · `missing` (name what should have been specified) ·
`internal` (pure plumbing; say why).

**readme** (under-spec). The README states purpose, features, options,
examples and promises. For the section at `at`, is each requirement it states
in the spec? `covered` (IDs) · `partly` (name what is missing) · `missing` ·
`not-a-requirement` (badges, credits, contribution process, links).

**architecture**. Is the item answered in the architecture file, the spec,
or another knowledge file next to them (commands belong in an environment or
test-strategy file), and true of the code? `answered-true` · `answered-false` · `vague` (too
general to act on) · `absent`. Also set `"restates_behaviour": true` when the
architecture file mostly restates what the spec says instead of how it is
built.

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
