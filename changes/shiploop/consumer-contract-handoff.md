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
