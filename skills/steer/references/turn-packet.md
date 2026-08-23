# Turn packet headings (script interpolates; do not paraphrase)

Every `steer next` and `steer-next` prints these H2s in order:

```text
## You are here
## Reminder
## Look here
## Next prompt
## When done invoke
## Missing
```

- **You are here** — session phases plus, in implement, each backchain id as `done` / `ready` / `running` / `blocked` / `todo`. After `--to plan`, spec is `frozen`.
- **Reminder** — prompt one-liner and frozen `done_sentence`. No spec/plan body dump. No “rewrite the spec.”
- **Look here** — absolute pointers with a one-line why (`required` / `if-needed`). Spec marked frozen after `--to plan`.
- **Next prompt** — interpolated `references/activities/<phase>.md`. In implement, then one `/goal` line per **running** id (in-flight label if already claimed).
- **When done invoke** — computed from running + drain, not a hardcoded `--to residual`. `complete-step` / `clear-step` / `update` then **steer-next**.
- **Missing** — same validator as `update`.
