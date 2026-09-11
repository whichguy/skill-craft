# /shiploop next

Reprint the current action without advancing it:

~~~sh
python3 "$SKILL_ROOT/scripts/shiploop" next --run-dir "$RUN_DIR"
~~~

Use it after a context loss or after reviewing durable evidence. It may finish
durable step scheduling/recovery, but it does not complete implementation,
review, verification, or merge by inference. Use context for a bounded section
rather than asking next to dump every receipt or the full DAG.
