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
| `architecture.md` | Stack, ownership, contracts, configuration, error model, conventions and numbered decisions `A-n` (below) |
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
- **Spec and architecture are orthogonal, big-ticket documents.** The spec
  is the contract: complete enough that a rebuild on a **different stack**
  would behave identically, so it names no language, library, module,
  function or algorithm. The architecture is the stack, structure,
  ownership and decisions: complete enough that a **changed spec** would be
  built on the **same stack**, so it does not restate behaviour. Neither is
  a guide to reconstructing this exact code.
- **Requirements are the contract, at contract level.** Each `R-n` is one
  capability a user or caller relies on, stated with the observable detail
  that decides it: inputs and options with their defaults, outputs and
  formats, errors and failure cases, ordering and edge behaviour a caller
  can see. Put that detail as short bullets under the requirement, each with
  its own anchor. Leave out internal mechanisms no caller can observe.
- **Anchor or omit.** Every requirement and every bullet cites `path:line`
  (or a test name or README line). If you cannot anchor it, it is an unknown,
  not a requirement. Never state an inferred default or behaviour as fact.
- **Architecture is where design lives, kept short.** `architecture.md`
  holds what an agent cannot cheaply read for itself: short, non-obvious,
  actionable facts, not a tour of the code. Sections:
  - **Stack:** runtime, frameworks and key libraries, each with what it is
    used for and why (commands belong in `environment.md`);
  - **Ownership:** entry points, the module that owns each responsibility,
    and the main data flow in a few lines;
  - **Contracts and boundaries:** public APIs, file formats, layering and
    anything a change must not break;
  - **Configuration:** where options come from (defaults, files, arguments,
    environment) and which source wins;
  - **Error model:** how failures are represented inside and how they reach
    a caller (thrown, returned, logged, exit status), and what is swallowed;
  - **Conventions:** naming, layering and placement rules, and the lint,
    format and type-check gates a change must pass;
  - **Decisions:** numbered `A-1`, `A-2`, ... (stable, never reused), each
    with the decision, its rationale, `rationale: stated` (docs, comments,
    commit messages; cite them) or `rationale: inferred`, and `path:line`
    evidence of where the code embodies it.
  If the repository already keeps an architecture document or decision
  records, link their sections instead of copying them and record only what
  they lack.
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
  input enter, which module owns each responsibility, what must a change not
  break, and why the non-obvious choices were made (each an `A-n` decision
  with evidence);
- nothing outside `docs/shiploop/` changed (`git status`).

End with one line:
`INITIALIZED: <requirement count> requirements, <architecture decision count> decisions, <unknown count> unknowns`.
