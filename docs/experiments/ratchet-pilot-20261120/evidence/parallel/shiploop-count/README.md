# The count behind journal section 11

- `../shiploop-test-changes.md` (one folder up): every row, with the delivery, the note file and the run's own reason.
- `deliv.tsv`, `rows.json`: the deliveries taken and the rows as data.
- Left out for size: the helper's dumps of each delivery's history and notes, and the per-row diffs the table numbers (`diffs/NN.txt`). Each row names its delivery, commit and file, so a diff can be shown again with `git -C <delivery>/work show <commit> -- <file>`.
- The deliveries are other sessions' records under `/Users/dadleet/e2e-runs/` and `/Users/dadleet/e2e-runs-sdlc*/`; they were read and not changed.
