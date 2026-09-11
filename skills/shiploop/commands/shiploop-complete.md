# /shiploop complete

Complete exactly the action that the current packet printed:

~~~sh
python3 "$SKILL_ROOT/scripts/shiploop" complete \
  --run-dir "$RUN_DIR" --action "$ACTION_ID" --result /absolute/result.md
~~~

The result is Markdown with exactly one shiploop-state JSON object fence. It
always needs a nonempty summary and must provide the current stage's additional
fields from the action protocol. The script refuses an omitted, stale, or
conflicting action ID; it does not infer an advance, an Improve outcome, or a
merge from the current chat or worktree.

Before completing a stage with a check gate, run the packet's verify command.
Before completing review, retrieve the required Git history. Before completing
commit, make the iteration's verbose primary commit at the worktree's actual
HEAD. Before merge, complete the final verification and broader-plan review.

An identical replay of an already completed action/result is safe; changing a
consumed action's result is refused. If a true defect appears after an
iteration, use repair rather than altering receipts or claiming completion.
