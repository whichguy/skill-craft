# ShipLoop evidence commands

Use only the current packet action ID:

~~~sh
python3 "$SKILL_ROOT/scripts/shiploop" verify \
  --run-dir "$RUN_DIR" --action "$ACTION_ID" --manifest /absolute/checks.md \
  [--reason "why the manifest changed"]

python3 "$SKILL_ROOT/scripts/shiploop" history \
  --run-dir "$RUN_DIR" --action "$ACTION_ID" --limit 1 --skip 0 --full

python3 "$SKILL_ROOT/scripts/shiploop" context \
  --run-dir "$RUN_DIR" --section prompt --offset 0 --limit 4000
~~~

Verify records argv-based lint and test evidence. Every iteration needs a
lint check and required tests; changing an already-recorded manifest needs a
specific reason. History defaults to compact rows; use a one-row full request
to inspect a commit body without overflowing a small context. Context returns
a bounded character slice of one durable section. After a cold resume read
prompt first, then request step or iteration. When paging context, pass
its printed digest on the next request so an intervening state change is
rejected rather than silently mixing snapshots.
