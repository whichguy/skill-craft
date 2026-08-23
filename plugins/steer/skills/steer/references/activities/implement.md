Walk ready steps via `/goal`. The spec is **frozen** — do not refine, expand, or rewrite it.

`steer next` already claimed newly ready ids `running` and printed one `/goal` line per running id (inner-loop: write tests, run them, fix until they pass; or prep / deploy / cleanup when that step names it).

Do **not** invoke `/devloop`. Do not nest a second `/goal` inside the first. If a `/goal` for an id is already open, do not open a second one.

After a `/goal` succeeds: `steer complete-step --run-dir {{RUN_DIR}} --id <id>` then invoke **steer-next**.
After a `/goal` fails and the session can continue: `steer clear-step --run-dir {{RUN_DIR}} --id <id>` then invoke **steer-next**.
Hard stop: `steer update --to blocked --resume-to implement --reason …` then invoke **steer-next**.
