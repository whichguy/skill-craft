Whole-repository initializer (experiment arm A: the repo-distill initializer at 94bb8862, 2026-09-27, with arm B's
file set, ID prefixes and line format, so that only the scope differs)

Intent. This repository has never run ShipLoop. Its first run should start from what the repository already is: its
behaviour, its architecture and the decisions behind it. Write that knowledge where ShipLoop reads it, so the run
plans a change instead of rediscovering the product, and respects the design instead of reinventing it.

Input: the repository at the path given, the census below (a script's map of it), and its history (`git log`).
Output: only KNOWLEDGE/spec.md and KNOWLEDGE/architecture.md. Change nothing else.

Rules:
- The README is a primary source. Distill every purpose, feature, option and promise in it into a requirement with
  Source `documented` and a `README.md:line` locator. Where the README and the code disagree, record what the code
  does with Source `conflict`, citing both.
- One authoritative home. A separate maintained requirements, API or design document may be linked instead of copied.
- Observed, not accepted. Every requirement has `Status: baseline`; every decision `(inherited)`. Never present an
  observation as a decision someone made.
- Spec and architecture are orthogonal. The spec is the contract: a rebuild on a different stack would behave
  identically, so requirement text names no language, library, module, function or algorithm (those go in locators).
  The architecture is the stack, structure, ownership, conventions and decisions; it does not restate behaviour.
- Requirements at contract level: each R-<n> is one capability a user or caller relies on, with inputs and options
  with defaults, outputs and formats, errors, ordering and edge behaviour a caller can see, as bullets with their own
  locators. Leave out internal mechanisms no caller can observe.
- Verify each bullet before you write it: open the code path that decides it. A test proves only its own case; state
  a general rule only from the code that enforces it. A bullet you could not verify gets Source `inferred`.
- Architecture sections: `## Stack`, `## Structure`, `## Conventions`, `## Interfaces and boundaries`, `## Decisions`
  (one AD-<n> per non-obvious structural choice, with why, stated or inferred, and evidence), `## Superseded`. A
  decision record the repository keeps becomes one AD-<n> linking it; a superseded one goes under `## Superseded`.
- Source classes: `documented`, `tested` (a named test asserts it), `observed`, `inferred`, `conflict`.
- Install nothing and do not run the repository's tooling (in this experiment there is no baseline test run, so
  `tested` means a named test asserts it).

Format (exact; the checker parses these lines):
- first line of KNOWLEDGE/spec.md after its title:
  `Baseline coverage: deep: <areas>; overview: <areas>; not inspected: <areas>. As of <short sha>.`
- `### R-<n> <title>` / `Status: baseline · Source: <class> (<locator>)[; ...] · As of: <short sha>` / `- <bullet> (<locator>)`
- under `## Decisions`: `- AD-<n> (inherited) <choice>. Why: <reason> (stated: <locator> | inferred). Evidence: <locator>.`
- a locator: `path` plus a symbol, test name or heading in backticks or quotes, or `path:line` for docs; paths relative
  to the repository root.

Before you finish, grade your own result and fix the files until all hold:
- every behaviour the repository's tests check is covered by a requirement whose Source names that test;
- every purpose, feature, option and promise in the README is a requirement citing its README line;
- architecture.md answers, for a new contributor: where a request or input enters, which module owns each
  responsibility, what a change must not break, and why the non-obvious choices were made (each an AD-<n>);
- nothing outside KNOWLEDGE changed.

Finish with one line:
`BASELINE: <R count> requirements, <AD count> decisions (<linked count> linking repository records), deep: <areas>, open items: <count>`
