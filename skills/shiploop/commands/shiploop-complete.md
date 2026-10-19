# /shiploop complete

Run exactly the callback the current packet printed on its line labelled
`Callback for this stage` (an Improve child's packet labels it `Next command (` or
`2. When the improve skill has completed, run:`). There are three kinds:

~~~sh
# Producer step result (reads $RUN_DIR/inbox/$ACTION_ID.md, the path the callback's label names; --result takes only that path)
python3 "$SKILL_ROOT/scripts/shiploop" complete \
  --run-dir "$RUN_DIR" --action "$ACTION_ID"
# Bind the selected Improve card when the Improve packet asks for it (the Improve stage's id)
python3 "$SKILL_ROOT/scripts/shiploop" improve-bind \
  --run-dir "$RUN_DIR" --action "$IMPROVE_ID" --skill-card /absolute/selected/improve/SKILL.md
# Import a finished Improve child, no record to write
python3 "$SKILL_ROOT/scripts/shiploop" complete \
  --run-dir "$RUN_DIR" --action "$IMPROVE_ID"
~~~

The producer result file is the packet's template, filled in: one `outcome`
(`done`, `repeat` or `blocked`; outer steps may also `replan`), a nonempty
`summary`, and `evidence_refs` naming the files this step wrote or the check
output it recorded (an absolute path, or one led by `RUN/`, `KNOWLEDGE/`, `WORKTREE/` or `GUIDES/`,
which ShipLoop expands; an inner stage's Until Loop receipt is listed by ShipLoop when the
result leaves it out). The template placeholder is refused. The script refuses an
omitted, stale or conflicting action ID and never infers an advance from the
chat or worktree. The Improve stage's `complete` takes no `--result`: it imports the
child's own `review-<n>.md` and `checks.md` from its reviews directory and
writes the summary itself; pass `--notes` for lessons, `--final-result` only
when the review changed a decision, and `--no-commit` for a user's or
repository's instruction not to commit. Every result at a planning stage the run's
`planning_review` option reviews (all seven under `stage`, the default; only `system-test-author`
and `release-plan` under `none`), including `blocked` and `repeat`,
and a `done` at the last `carry-forward` that leaves no work item pending, parks
the action for its Improve stage instead of advancing. The Improve stage has its own action id
(`$IMPROVE_ID`, printed in its packet); ShipLoop binds the recorded card, writes the opening and
starts the child at the transition, and the model runs the improve skill, then `complete` with
that id, which alone releases it. Only if the recorded card no longer resolves does the packet print
`improve-bind`. Every improve-* command takes the Improve stage's id; one given the reviewed
action's id is refused. The packet's Improve line says
which: under `none`, a result at `spec`, `test-strategy`, `plan`, `step-plan` or `test-spec`
advances on ShipLoop's checks at `complete`, with no child to bind.
An identical replay is safe; a changed result for a consumed action is refused.
Protocol 4 adds `improve-reconcile`, printed only when its Plan Improve child
returns a reconciliation need (a `none` run has no Plan Improve child).
