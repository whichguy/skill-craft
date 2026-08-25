# Turn packet headings (script interpolates; do not paraphrase)

Every `shiploop next`, `shiploop complete`, and `/shiploop next` prints these H2s in order
(after the harness banner):

```text
## You are here
## Progress
## Reminder
## Look here
## Next prompt
## When done invoke
## Missing
```

- **You are here** — glanceable rails, then the same machine-stable status lines (not a new H2). Session rail: `intake → validate-spec → plan → implement → residual → done` with `●` done / `▶` current / `○` left / `✗` blocked. Then each session phase as `phase: current|done|todo|blocked`. In implement, a walk rail lists every backchain id with its **statement**, `done` / `ready` / `running` / `todo` (still as `S1: running` on that line), and if waiting, `waiting on <supplier id> <statement>`. No phantom `blocked` step status — blocked is a session phase, not a step state. After `--to plan`, spec is `frozen`. Then a `Diagnosis` block: frozen `done_sentence`, stand vs spec/steps, **completed**, **now** (running/ready, with worktree/branch), **pending** (waiting on suppliers or later session phases).
- **Progress** — verbose begin/finish for the current phase or running step: what this increment does, worktree folder + branch (implement), session checkout (do not edit during `/goal`), and what `/shiploop complete` does next. Not a new SM phase. Always prints this host flag first (same wording again in the implement Next envelope; stored `prompt`s stay verbatim):

```text
HOST FLAG — extra folder (do not re-root):
ShipLoop creates another folder: a per-step worktree under <repo>/.worktrees/shiploop/<run_id>/<id> on branch shiploop/<run_id>/<id>.
Implementation work happens IN that worktree, not in the session checkout.
Do not move_agent_to_root / re-root the host chat into that folder or the product repo unless the user asked.
The session checkout stays the merge dest; do not edit it during implement.
After /shiploop complete, the host merges the kept branch into session HEAD; the next packet names the next worktree.
```
- **Reminder** — prompt one-liner and frozen `done_sentence`. No spec/plan body dump. No “rewrite the spec.”
- **Look here** — first line `Reference only — not the next action.`, then absolute pointers with a one-line why (`required` / `if-needed`), phase-scoped (validate-spec adds `environment.md` + the survey guide; implement adds `environment.md` as **required** frozen survey plus each running step's worktree labeled with the step statement, e.g. `S1 worktree — cwd here — write the file`; residual points at `recap.html` as written on dest done; done/halted add the generated recap). Spec/environment marked frozen after `--to plan`.
- **Next prompt** — first line `Use this prompt as much as possible.` Implement (not drained): envelope (worktree folder, branch, checkout guard, HOST FLAG, Frozen session environment) then each running id's **stored** `prompt` printed verbatim (the script does not compose or rewrite it from statement/produces/suppliers/worktree). Paste the Frozen session environment block together with the stored prompt into `/goal`; do not paste worktree, branch, or HOST FLAG. Other phases (including drained implement, which uses `implement-drained.md`, and residual with a bound-plan waiver, which uses `residual-waived.md`): the interpolated activity body, printed as-is.
- **When done invoke** — `invoke /shiploop complete` (not `complete-step --id` / `update --to`). Implement labels the closer as `Finish S1: write the file —` (still matches `Finish S1:`). That command commits/merges if needed, closes the increment, and prints the next packet. Failure: `/shiploop complete --clear` or `--blocked --reason`. Empty or unmerged complete is refused. Worktree/branch stay in Look here / Diagnosis, not spliced into the prompt. Plan-before-DAG is the success closer (`complete` → implement), not `--blocked`; `--blocked` is only when a written DAG is illegal. Residual Diagnosis / Progress name a bound-plan waiver when one exists (not “run Phase B”).
- **Missing** — same validator as `update`.
