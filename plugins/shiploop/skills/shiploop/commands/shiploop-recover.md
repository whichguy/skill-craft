# ShipLoop pause, repair, and migration

~~~sh
python3 "$SKILL_ROOT/scripts/shiploop" pause --run-dir "$RUN_DIR" --reason='specific blocker'
python3 "$SKILL_ROOT/scripts/shiploop" resume --run-dir "$RUN_DIR"
python3 "$SKILL_ROOT/scripts/shiploop" repair \
  --run-dir "$RUN_DIR" --action "$ACTION_ID" --reason='specific discovered defect'
python3 "$SKILL_ROOT/scripts/shiploop" halt --run-dir "$RUN_DIR" --reason='terminal reason'
python3 "$SKILL_ROOT/scripts/shiploop" migrate --run-dir "$RUN_DIR"
~~~

Pause preserves the current action and is never success. Resume only reprints
the preserved action. Repair records a real late defect, resets convergence,
and returns to Improve review without deleting work. Halt writes an unfinished
terminal handoff. Migrate is only for a legacy JSON run; it archives old JSON,
keeps code/branches/worktrees, and re-establishes Markdown authority and new
evidence gates.
