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
