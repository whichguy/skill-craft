---
bump: minor
---
Each implementation step is proven by its own command, and the step's packet, its printed head and its Improve hand-off
carry one Step block.
- step-plan records `check` on every step: the one command, from the repository root, that proves the step's criteria
  with only that step and accepted earlier steps. A step without it is refused, naming the step. A step's `paths` are
  optional (the parallel chain reads them); when steps name none, the expectations cover the item's own paths. The
  step-plan Improve review flags a check that needs a later step's work or passes by skipping a missing artifact.
- On the inline route ShipLoop runs the step's Proof when the step reports done and refuses a failure, quoting the exit
  and the output's tail; the refusal gives the loop's start command and both routes (fix and report done, or stop
  blocked and report revise). Each run is recorded at `tests/<action>-step-proof<N>.md`, bound to the action, the step,
  the command and the candidate's working trees; `--check-only` runs it without counting, and `complete` takes a passed
  run whose tree is unchanged. Before importing the step's Improve review ShipLoop runs the Proof again when the review
  changed the candidate, and reuses the record when it did not.
- The item's check commands leave implement and its step review: they stay with the test stage and verify. The step's
  duty, exit conditions and repeat rule, its Improve focus and `stage_commands` name the step's Proof; the ask-agent
  route's whole-plan Work, repeat rule and gates are unchanged.
- The Step block (task, the criteria it serves by value with their test cases, what it depends on, its Proof, its
  skills, the accepted steps and the later ones by their first sentence) sits right under Done when, the same lines on
  every surface, with no path fence; the inline step's packet and head end with its Until Loop, whose Work names the
  step's criteria, the R-<n> they serve and the item's AD-<n> ("until each requirement assigned to this step is
  satisfied and none of the others is broken"), and whose first exit condition lists the step's criteria.
- The step's Improve hand-off names its review base: a `git diff` of the tree recorded when the step began and the tree
  when the review was bound, untracked files included.
- State version 7: a run saved at version 6 is refused with its reason (its step plans name no check); start it again in
  a fresh run directory.
