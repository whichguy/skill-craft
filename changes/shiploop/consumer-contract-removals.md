---
bump: major
---
ShipLoop's knowledge home has three living files, and every artifact it keeps has a named reader (consumer contract,
slices 4b to 4d).

- **Three living files.** `docs/shiploop/spec.md`, `environment.md` and `architecture.md`. `environment.md` gains the
  sections `## Harnesses and suites` (each suite with its files and command, and the system-test catalog) and
  `## ID convention` (the scheme and the one command that lists the IDs already taken); `architecture.md` gains
  `## Real-boundary checks` (each check a local test cannot prove, with its owner). test-strategy writes those two files;
  system-test-author keeps the catalog, and release-check corrects the standing release procedure, in `environment.md`.
  test-spec is no longer a knowledge close (its cases are in the result), and intake keeps no file.
- **`test-strategy.md` and `docs/shiploop/README.md` are retired.** No close requires them and nothing writes or names
  them; an older repository keeps its copies, which the credential screen still reads.
- **Rollback at release and operations.** In an isolated run the release, release-plan, release-check and operations
  packets print the return's rollback commands.
- **The feature folder, the retire and outcome.md are removed.** A run no longer writes or requires
  `docs/shiploop/features/<run>/` (spec, plan, test spec, system tests, release plan, outcome) or the feature list
  `features/README.md`: their content is in the stage results the consumers quote, in the living files, or in the
  release-verify lessons commit. The handoff no longer removes the run's feature spec, and an older version's feature
  folders are left untouched. release-verify's close needs `environment.md` only: the lessons are the result's field.
- **`SHIPLOOP.md` is the host's file.** ShipLoop no longer commits, screens or returns it as knowledge: a return plan
  reviews it like any product file and may exclude it, and validate-existing treats a change to it as a stray path.
  Packets still name it as the host-authored index to read if present.
- **Progress view.** It lists the living spec and the run's accepted results; the feature drafts, the test strategy and
  the retired-spec row are gone.
