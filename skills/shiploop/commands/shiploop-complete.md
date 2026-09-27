# /shiploop complete

Run exactly the callback the current packet printed on the line after its
header. There are three kinds:

~~~sh
# Producer step result
python3 "$SKILL_ROOT/scripts/shiploop" complete \
  --run-dir "$RUN_DIR" --action "$ACTION_ID" --result "$RUN_DIR/inbox/$ACTION_ID.md"
# Bind the selected Improve card when the packet asks for it
python3 "$SKILL_ROOT/scripts/shiploop" improve-bind \
  --run-dir "$RUN_DIR" --action "$ACTION_ID" --skill-card /absolute/selected/improve/SKILL.md
# Import a finished Improve child, no record to write
python3 "$SKILL_ROOT/scripts/shiploop" improve-complete \
  --run-dir "$RUN_DIR" --action "$ACTION_ID"
~~~

The producer result file is the packet's template, filled in: one `outcome`
(`done`, `repeat` or `blocked`; outer steps may also `replan`), a nonempty
`summary`, and `evidence_refs` naming the files this step wrote or the check
output it recorded. The template placeholder is refused. The script refuses an
omitted, stale or conflicting action ID and never infers an advance from the
chat or worktree. `improve-complete` takes no result file: it imports the
child's own `review-<n>.md` and `checks.md` from its reviews directory and
writes the summary itself; pass `--notes` for lessons, `--final-result` only
when the review changed a decision, and `--no-commit` for a user's or
repository's instruction not to commit. Every result at a planning stage
(including `blocked` and `repeat`),
and a `done` at the last `carry-forward` that leaves no work item pending, parks
the action for its Improve child instead of advancing: bind it with the printed
`improve-bind` command; only `improve-complete` releases it.
An identical replay is safe; a changed result for a consumed action is refused.
Protocol 4 adds `improve-reconcile`, printed only when its Plan Improve child
returns a reconciliation need.
