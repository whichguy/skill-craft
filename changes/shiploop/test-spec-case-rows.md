---
bump: minor
---
The test-spec stage no longer prints an example ID anywhere a model might copy it, and its refusals and head now say which
requirements the living spec holds.
- A refusal about a test case printed a literal example row with `"requirement": "R-3"`. A model copied it ("Requirement is
  expected as R-3; I'll use it"), found the spec held no R-3, and wrote a spec entry to match, which ShipLoop committed.
  Every printed shape of a case now holds placeholders only (`"id": "<a focused command ID>"`, `"criterion": "<a step-plan
  criterion id>"`, `"requirement": "R-<n>"`), the same text the template prints, and a case that keeps one is refused as a
  template placeholder like the oracle, red and green fields already were.
- The refusal for a case with a missing, unusable or unknown `requirement` ends with the IDs `HOME/spec.md` holds (`lists R-1,
  R-2`; a retired one is marked), or, when it holds none, `lists no R-<n> entry: report revise naming the missing
  requirement`.
- The test-spec result template has one row per focused-command ID of the item's step plan (the first twelve; the packet names
  the rest). Each row carries the ID, the one criterion the plan's focused commands list for it, and the requirement when that
  criterion's text names exactly one R-<n> the spec holds; the model fills the oracle, RED and GREEN and may change any field.
  An item whose plan lists no focused ID prints `"test_cases": []`.
- The test-spec packet lists the spec's requirement IDs with the first 60 characters of each entry beside the template (the IDs
  alone for a spec so large the line would pass 2,400 characters), so a printed head that drops the quoted spec still shows
  them.
- `complete --check-only` on a test-spec result prints a counted notice (`ShipLoop coverage notice: Criterion C2 has no test
  case ...`) for each step-plan criterion that no case names, no recorded non-focused command lists and no open item of the
  result mentions. A notice never refuses.
