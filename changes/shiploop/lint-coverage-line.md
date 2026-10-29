---
bump: minor
---
Every lint result says how each changed file was covered, so a syntax check is never read as a lint (design T
section 8.2a, F6).
- A lint pass prints a `Lint coverage:` line right after its `Result:` line. It counts the files a linter covered
  and names the linters, then lists each other file with its coverage: syntax only (a parse, or a linter that was
  unavailable or timed out), not linted, or linted in part (another linter the repository configures did not run).
  Deleted files are left out.
- The packet's lint digest keeps this line, though it still leaves the per-file Coverage section to the stored record.
  Both lint gate refusals (after an auto-fix, and on an unwaived finding) print it, and so does a pass that could not
  run ("Lint coverage: none").
- With lint off, the implement, test and document packets say so: no linter and no lint gate run, so the step
  chooses and runs its own static checks.
