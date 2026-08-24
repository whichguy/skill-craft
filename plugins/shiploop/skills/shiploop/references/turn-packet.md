# Turn packet headings (script interpolates; do not paraphrase)

Every `shiploop next`, `shiploop complete`, and `/shiploop next` prints these H2s in order
(after the harness banner):

```text
## You are here
## Reminder
## Look here
## Next prompt
## When done invoke
## Missing
```

- **You are here** — session phases plus, in implement, each backchain id as `done` / `ready` / `running` / `blocked` / `todo`. After `--to plan`, spec is `frozen`. Then a `Diagnosis` block: frozen `done_sentence`, stand vs spec/steps, **completed**, **now** (running/ready, with worktree/branch), **pending** (waiting on suppliers or later session phases).
- **Reminder** — prompt one-liner and frozen `done_sentence`. No spec/plan body dump. No “rewrite the spec.”
- **Look here** — absolute pointers with a one-line why (`required` / `if-needed`). Spec marked frozen after `--to plan`.
- **Next prompt** — interpolated `references/activities/<phase>.md`. Drained implement uses `implement-drained.md` (no `/goal`). Otherwise one `/goal` line per **running** id (in-flight label if already claimed; cwd is that step's worktree).
- **When done invoke** — `invoke /shiploop complete` (not `complete-step --id` / `update --to`). That command commits/merges if needed, closes the increment, and prints the next packet. Failure: `/shiploop complete --clear` or `--blocked --reason`. Empty or unmerged complete is refused.
- **Missing** — same validator as `update`.
