---
bump: major
---
ShipLoop records the data each stage's consumer reads, so a stage cleared of its context can work from its packet alone
(consumer contract, slice 4a).

- **Whole-file knowledge quotes.** `knowledge_home.READS` names, for every stage, the living files its packet quotes
  whole (`spec.md`, `environment.md`, `architecture.md`); `reads_quotes(state, stage)` returns each file's absolute path
  and its whole text, or None when it is absent or blank. A heading spelled any way is quoted the same.
- **Entries.** `knowledge_home.entry_text(repo, "R-3")` returns one requirement (from `spec.md`) or decision (`AD-<n>`,
  from `architecture.md`) as the file holds it, uncut, and `entries()` flags one under Retired or Superseded.
- **Run baseline.** `init` records the execution checkout's HEAD in the run folder (`run-baseline.txt`);
  `spec_diff(root, state)` is the uncut `git diff` of `docs/shiploop/spec.md` and `docs/shiploop/architecture.md` since
  then.
- **Lessons commit.** release-verify's knowledge commit is always made: its body is the result's `lessons` (Learned, Key
  considerations, Open for the next run) plus the open items still left, and it is an empty commit when the home did not
  change. The next run's intake and discovery quote it whole, found by its subject however many commits follow, beside
  the last three commit messages they already quote.
- **Hand-off result fields.** step-plan records `follows` (the R-<n> and AD-<n> the item follows; each must have an
  entry in the living spec or architecture), test-spec records `test_cases` (one `{id, criterion, requirement, oracle,
  red, green}` per ID this item's focused commands list, both ways, with the step plan's criteria and real
  requirements; this replaces the check of the feature `test-spec.md` headings), implement may record `not_covered`,
  and release-verify records `lessons`. A template placeholder left in any of them is refused.
- **Open items.** test-spec, verify, carry-forward, system-test-author, system-test, release-plan and release-verify
  list the open items they leave in `assumptions` (`[]` when none); an open item's consumer is a later outer stage, or
  the same item's carry-forward from test-spec or verify, and may name an `owner`. A row stays open until its consumer
  stage's later done result settles it.
- **Refusals.** Every hand-off refusal's first line is the fix, the result file's absolute path and the next command;
  on improve-complete without `--final-result` it says to write a final result to the printed path and pass it. The
  Improve packet lists `revise` among the final outcomes at test-spec to verify.
- **What each packet consumes.** `navigator.CONSUMES` names, for every stage, the hand-off values its packet quotes, and
  `handoff_sources(root, state, stage)` returns them; system-test-author now reads test-spec and release-plan reads
  system-test-author in the stage table.
- **State version 6.** A run saved by an earlier version is refused with the fresh-run hint.
