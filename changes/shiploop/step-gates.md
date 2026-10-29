---
bump: minor
---
Each step's document stage and its review are gated on their own edits (design T section 9.1, 2b-4b).
- Document's done lints the lines document changed since it began, and reruns what those edits could affect: nothing
  after no edit, the step's check commands after a documentation edit, and every command the step's test stage ran
  after a code or test edit. A document result may carry `lint_waivers`.
- The step review's import lints the lines the review changed before ShipLoop reruns the step's commands. A new,
  unwaived finding refuses the import.
- Before, only verify linted and reran, once per item and against the last step's base, so an earlier step's review
  edits were never linted by a gate.
