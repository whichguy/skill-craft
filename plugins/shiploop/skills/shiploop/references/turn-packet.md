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

- **You are here** — session phases plus, in implement, each backchain id as `done` / `ready` / `running` / `todo` (no phantom `blocked` step status — blocked is a session phase, not a step state). After `--to plan`, spec is `frozen`. Then a `Diagnosis` block: frozen `done_sentence`, stand vs spec/steps, **completed**, **now** (running/ready, with worktree/branch), **pending** (waiting on suppliers or later session phases).
- **Reminder** — prompt one-liner and frozen `done_sentence`. No spec/plan body dump. No “rewrite the spec.”
- **Look here** — first line `Reference only — not the next action.`, then absolute pointers with a one-line why (`required` / `if-needed`), phase-scoped (validate-spec adds `environment.md` + the survey guide; implement adds each running step's worktree; residual/done add `recap.html`). Spec/environment marked frozen after `--to plan`.
- **Next prompt** — first line `Use this prompt as much as possible.` Implement (not drained): each running id's **stored** `prompt` printed verbatim (the script does not compose or rewrite it from statement/produces/suppliers/worktree). Other phases (including drained implement, which uses `implement-drained.md`): the interpolated `references/activities/<phase>.md` body, printed as-is.
- **When done invoke** — `invoke /shiploop complete` (not `complete-step --id` / `update --to`). That command commits/merges if needed, closes the increment, and prints the next packet. Failure: `/shiploop complete --clear` or `--blocked --reason`. Empty or unmerged complete is refused. Worktree/branch stay in Look here / Diagnosis, not spliced into the prompt.
- **Missing** — same validator as `update`.
