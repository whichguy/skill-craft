---
bump: minor
---
Run trace: every run appends `RUN/trace.jsonl`, one line per command that names the run (verb, exit code, revision,
stage and action before and after, results accepted, refusal text), per printed packet (kept as sent in
`packets/sent/<sha>.md`, since `next` rewrites `packets/<action>.md`) and per keepalive stop decision (with the text the
hook put into the turn). `shiploop trace --run-dir RUN` reads it: every stage done, current, reopened or pending, the steps
run, recent events; `--action ID` shows one action's packets as sent, commands and refusals; `--json` gives the whole
model; `--html` writes the self-contained `RUN/trace.html`, which the progress observer keeps current. Runs saved before
the trace still read from `state.md` and `timeline.json`.
