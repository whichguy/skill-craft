---
bump: patch
---
`shiploop check` now runs the same result-shape check `complete` runs, so a check's yes is no longer followed by a
refusal at complete (for example a step-plan check row with an empty `criteria` list). An empty `red_na` or
`retired_tests` list is accepted as the field left out, and a step's spec line may end in `.` or `;` after its
`(W<n>/S<n>)` mark.
