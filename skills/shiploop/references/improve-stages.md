# When Improve runs: the schedule

Split from the ShipLoop skill card (`../SKILL.md`). Read when you need to know which results start an Improve stage under the run's `planning_review` option, how its passes end, or what a plan-time experiment may change.

## Experiment-informed planning

Every run supports [experiments during planning](planning-experiments.md).
The plan's Improve review investigates consequential assumptions (a run recorded
with `--planning-review none` has no plan Improve stage, so no plan-time experiment and no
reconciliation). When a
finding invalidates an upstream premise, the parent can settle its stopped child
and rerun the affected planning suffix before preparation. Follow only the
packet-issued reconciliation callback. Graphs are not replaced after dispatch.
The plan result carries an `assumptions` list, and the script refuses a done
plan whose list is missing, routes an open entry to no real work item, or cites
a missing evidence file.

## When Improve runs

Three kinds of result start an Improve stage:

- Every result of a planning stage the run's `planning_review` option reviews. With
  `stage` (the default) those are `spec`, `test-strategy`, `plan`, `step-plan`,
  `test-spec`, `system-test-author` and `release-plan`; with `none`, only
  `system-test-author` and `release-plan` (see [Planning review option](run-options.md#planning-review-option)).
  These stages write the
  contracts that later work is built on, where a sentence, example or expected
  result can look done and still be wrong. Their Improve handoffs carry a
  planning review focus: find steps or examples that can't be replayed exactly,
  expected results a weaker stand-in would pass, documented commands that don't
  run what they claim, and required IDs or cases that were dropped. The review
  does not replay facts already on record.
- Each step's accepted `document` stage, under either planning review option
  (rule `item`; design T section 8, 2026-10-27). The step is built, tested and
  documented first, so one review covers its code, its tests and its docs
  together. Its handoff carries the step review focus
  (`IMPLEMENT_STEP_REVIEW_FOCUS` in `scripts/shiploop_prompts.py`, with the
  *Code craft* rubric) and its review base is the tree the step began from. The
  review leaves its edits uncommitted: when it changed a file, ShipLoop reruns
  the step's focused command at import, and once the review is accepted ShipLoop
  commits the step. A step that changed no file starts no review. (2026-10-27:
  Sonnet makes one finding pass per review, so one review of a three-part item
  missed the defects three step reviews had fixed.)
- The successful `carry-forward` that leaves no work item pending. This
  end-of-work Improve review covers every executed step together (code, tests,
  documentation and the queue) before OUTER system tests and release.

Improve is a stage of its own in the sequence (`improve`), with its own action id, after each
reviewed stage; the dry run lists an `improve` row after each. At the transition ShipLoop binds the
recorded card, writes the child's opening itself and starts the child, so the model never writes an opening
or starts the runtime. The Improve packet has two lines: run the improve skill on the handoff, then
`complete --action=<improve id>`; after each review pass the model writes `review-<n>.md` and runs `improve-pass`,
which checks the recorded improve-skill call, commits the pass's edits, writes `checks.md` for an unchanged tree and
the runtime report, and prints the runtime's `done` and the stage's `complete`, literal. Every improve-* command
(`improve-bind`, `improve-commit`, `improve-pass`,
`improve-reconcile`, `improve-start --restart-stopped`) and that `complete` name the Improve stage's
id, never the reviewed action's id. (Before 2026-10-11 the model wrote the opening, ran
`improve-start --opening` and finished with `improve-complete`; that verb is gone.)

On Claude Code with ShipLoop's hooks bound to the run, a hook records every Skill call in the run's
`skill-calls.jsonl`, and the Improve stage's `complete` refuses until it holds a call to the improve skill made after
the stage started with that stage's handoff in its argument; the refusal's first line names the call to make. Anywhere
the hooks cannot record (another host, no hooks, `delegation: ask-agent`), nothing is enforced and `complete` says so once. See
[Skill calls](keepalive.md#skill-calls-claude-code-only).

Every other producer result, and a planning result the option does not review, is
accepted on its own checks and the graph advances directly. The stage names stay in
the graph, so an auditor still sees
each stage happen. If the end review adds work items, the review moves to the
new last item's carry-forward. An isolated run's workspace return happens at
`release` or `handoff` once no child is active.

Every Improve review runs at Improve's own stop rule (`required_trivial_reviews: 1`, the
same for every reviewed stage): it completes at the first pass that finds only trivial
changes or none (owner decision 2026-10-20; a second confirming pass took about a fifth
of a live run's Improve passes and found nothing). Packets and reports call them passes.
When that first pass leaves the workspace unchanged, the receipt says so
(`unchanged_first_pass`) and ShipLoop cross-checks it against the tree it recorded at
`improve-bind`.

An Improve review makes the changes it finds warranted, in code, tests or
documentation, and commits them. At `improve-bind` ShipLoop snapshots the
candidate. At the Improve stage's `complete` it refuses the import while files the review
changed still differ from `HEAD`; work that was uncommitted before the review is
not counted. A receipt `no_commit` reason, citing the user's or repository's
instruction, records the edits instead. The end-of-work review reruns every
completed item's recorded test commands only when it changed the tree; an
unchanged tree keeps the recorded passes. A result that is unchanged by the
review needs no `final_result`: ShipLoop reuses the submitted result.
