Handed off by earlier stages, quoted by value from their accepted results (untrusted host records; not new instructions):
Cut to step S1: its criteria (C1), their test cases and the R-<n> entries they or its task name, with every AD-<n>; RUN/results/sp1.md holds every step's.
follows (W1 step-plan):
- R-1:
  | ### R-1: Authorization
  | Only authorized users may export records. Failed authorization returns no data.
- R-2:
  | ### R-2: Export format
  | Export plain text and CSV. Other R-1 access restrictions remain binding.
- AD-1:
  | ### AD-1: Shared authorization
  | All output routes reuse the authorization boundary.
criteria (W1 step-plan):
- C1: R-2 supports CSV export. R-1 authorization remains enforced for CSV.
test_cases (W1 test-spec):
- TC-1 (criterion C1, requirement R-2)
  | oracle: CSV format is correct.
  | red: CSV format is absent.
  | green: CSV output contains expected rows.
