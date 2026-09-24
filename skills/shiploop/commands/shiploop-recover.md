# ShipLoop pause, resume, halt and delegation

~~~sh
python3 "$SKILL_ROOT/scripts/shiploop" pause --run-dir "$RUN_DIR" --reason='specific blocker'
python3 "$SKILL_ROOT/scripts/shiploop" resume --run-dir "$RUN_DIR"
python3 "$SKILL_ROOT/scripts/shiploop" halt --run-dir "$RUN_DIR" --reason='terminal reason'
python3 "$SKILL_ROOT/scripts/shiploop" delegation --run-dir "$RUN_DIR" --set inline   # or ask-agent
~~~

Pause keeps the current action, and any bound Improve child, and is never
success. Resume returns a paused or blocked run to the same action; run it once
after the stated condition is resolved. Halt ends the run unfinished and writes
its terminal report. `delegation` applies from the next issued action.

After an interruption, run `next` first, inspect saved history and the actual
repository effects, then follow the reprinted packet. There is no repair,
migrate or merge-recover command: a stopped Improve child restarts through the
route its packet prints, and a saved run from an older protocol (v1/v2, managed
or legacy) is refused with an error naming it. Start a fresh `--run-dir` (or
`workspace start --workspace-root`) for that request.
