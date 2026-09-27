# Initialize ShipLoop's knowledge home from this repository

**Intent.** This repository has never run ShipLoop. Its first ShipLoop run
should start from what the repository already is: its behaviour, its
architecture and the decisions behind it, how to build and test it. Write that
knowledge where ShipLoop reads it, so the run plans a change instead of
rediscovering the product, and respects the design instead of reinventing it.

**Your input.** The repository in the current directory: source, tests, docs,
configuration, history (`git log`). Run its build and tests to confirm what
works. Do not use the web.

**Your output.** Only files under `docs/shiploop/`. Change nothing else.

| File | Holds |
|---|---|
| `README.md` | Index: what each file answers; links to the repository's README and any formal requirements, API or design documents |
| `spec.md` | The living spec: requirements with stable IDs `R-1`, `R-2`, ... and an empty `## Retired` section |
| `architecture.md` | Structure and decisions (below) |
| `environment.md` | Runtime targets, the working install, build, test and run commands (each one you actually ran, with its result), platform facts |
| `test-strategy.md` | Existing test harnesses and suites, the command that runs each, how tests are named and organised, what they cover and what they do not |

## Rules

- **The README is a primary source.** The repository's README (and its
  other user docs) states the product's purpose, features, options, examples
  and promises. Distill every one of them into `spec.md` requirements with
  `evidence: docs` and a `README.md:line` citation; do not merely link it.
  Where the README and the code disagree, record what the code does, cite
  both, and list the disagreement under unknowns.
- **One authoritative home.** Only a separate, maintained formal
  requirements, API or design document (not the README) may be linked from
  `spec.md` instead of copied; then `spec.md` holds what it does not.
- **Observed, not accepted.** You can only observe. Mark every requirement
  `Status: observed` with its evidence (`path:line`, a test name, or a doc
  section). Say `evidence: test` when a test enforces it, `evidence: docs`
  when documentation promises it, `evidence: code` when only the code shows
  it. The owner accepts intent later; never present an observation as a
  decision someone made.
- **Requirements are behaviour.** Each `R-n` is one observable outcome with
  its preconditions, failure and negative cases. Group closely related
  behaviour under one ID; keep IDs stable and never reuse one.
- **Architecture is where design lives.** In `architecture.md`: entry points;
  modules and their responsibilities; the data flow for the main use cases;
  key dependencies and what each is used for; configuration and its sources;
  error handling; extension points and public contracts other code relies
  on; conventions a change must follow (style, layering, naming). For each
  non-obvious choice, record the decision and its rationale when the
  repository states it (docs, comments, commit messages), and mark it
  `rationale: inferred` when you infer it.
- **Unknowns stay unknown.** List what you could not determine and the
  default reading you would take, in the file it concerns.
- No credentials, tokens or secrets in any file, even if the repository
  contains them.

## Before you finish: grade your own result

Fix the files until all hold:

- every behaviour the repository's tests check is covered by a requirement
  whose evidence names that test;
- every purpose, feature, option and promise in the README is a requirement
  citing its `README.md` line;
- every command in `environment.md` was run by you, and its result is stated;
- `architecture.md` answers, for a new contributor: where does a request or
  input enter, which module owns each responsibility, and what must a change
  not break;
- nothing outside `docs/shiploop/` changed (`git status`).

End with one line:
`INITIALIZED: <requirement count> requirements, <architecture decision count> decisions, <unknown count> unknowns`.
