You are reviewing a design before it is built. Be adversarial and concrete. Read the files; do not take my summary on trust.

## What this folder is

- `DESIGN.md`: the design under review. A change to ShipLoop, a script-driven software delivery skill: scripts own
  navigation and print one stage's instructions ("packet") at a time; a model does that one stage and submits a
  result (a JSON block) that the script checks ("gate") before moving on. Context is cleared between stages.
- `shiploop/scripts/`: the current code the design changes or copies from. The ones that matter most:
  `shiploop_prompts.py` (`DUTIES["spec"]`, `STAGE_RULES`), `shiploop_navigator.py` (`_result_template`,
  `_canonical_result`, `_evaluate`, `_stage_input_blocks`, `_render_lines`, `_render_report`, `_stage_gates`,
  `_validate_current_state`), `shiploop_primary.py` (the spec stage's existing required list, the closest model),
  `shiploop_follow_on.py` (the newest list of this kind, the pattern the design copies), `shiploop_owner_notes.py`
  (how a sentence from the owner reaches a running run), `shiploop_planning_revision.py`.
- `shiploop/references/`, `shiploop/README.md`, `shiploop/SKILL.md`: the skill's documents.
- `tests/`: the follow-on list's test suite and the loophole table, as examples of what a new gate must come with.
- `evidence/baseline-11.txt`: what eleven archived real deliveries recorded about the point at issue.
  `evidence/archive-sol-medium-checks.txt`: their held-out check results. `evidence/replies.json`: the stand-in
  requester's answer.
- `journal/pilot-journal-section-26.md`: the experiment program this design comes out of (findings F48 to F60; the
  closing entry lists six suggested changes; this design is the first).
  `journal/spec-elaboration-sections-22-28.md`: another study's results on wording that takes or leaves a default.

## The owner's standing rules that bind the design

- ShipLoop runs unattended by default. It records defaults and asks a person only when nothing can proceed. No
  separate attended mode, no pause for confirmation, no limit on its loops.
- A requirement is only what the code needs. No shims, fallbacks or migrations: one supported version.
- Change only for a material difference: show the measured outcome a change moves.
- Every output names its consumer; no consumer, no artifact.
- No size or count caps on model text (raise a bound, spill to a file).
- A new gate adds its known dodge to the loophole table in the same commit.

## What I want from you

1. **Is this the right structure?** A required list on the spec stage's done result, checked by the script, shown in
   three places. Argue for the strongest alternative you can find in the code (for example: extending intake's
   question ledger; a new disposition in the `assumptions` list; a list at the plan stage; marking the requirement
   in `spec.md` with a script-read marker and deriving the list from the file; using the handoff's `follow_on` class
   `decision`). Say which you would build and why, using the evidence in the journals.
2. **The entry and the bar.** Are the five fields the right ones? Is anything missing that the requester needs to act,
   or present that only adds a way to fail a submission? Attack the wording of section 2.2 sentence by sentence:
   where will a model at medium effort misread it, list trivia, list nothing, or invent behaviour to have something
   to list? The other study found that "a limit the request leaves to choice" made the stage invent limits. Give
   replacement wording where you would change it. Keep it short: the spec packet has a 20,000-character head limit.
3. **Consistency of the stage's own text.** Spec duty 4 keeps "Mark each unresolved prerequisite or user decision as
   an open gap", `STAGE_RULES` keeps "record it as an assumption ... else in its summary", and duty 9's clause is
   repointed. Does the stage's text now pull three ways? What is the smallest edit that makes it one rule, and what
   does that edit risk on a driver that already records defaults (Sonnet)?
4. **The surfaces.** (a) Is a required block in the `test-strategy` packet telling the host to tell the user, with
   the `note` command, compatible with "unattended, no pause"? What goes wrong on a headless run, on a run with
   planning reviews on, on a spec that is revised later? (b) When the owner's sentence arrives as a note at
   `test-strategy` or later, does the run have a working route to change the requirement and everything built on
   it? Trace it in the code and say where it breaks. (c) Is "directly after Original request" the right place in
   the report, and are the done-packet lines the right amount?
5. **The gate.** Anything refused that should not be, or accepted that should be refused? Does the loose stored
   shape with a strict CLI gate hold against `_validate_current_state` and the stage review's import route? Which
   existing tests and fingerprints will this change move that the design does not name?
6. **The test plan (section 3).** Will three runs with those rules tell me what I think they will? What would you
   measure instead or as well? What result would make you stop? Is the stand-in requester's rule fair?
7. **What did I miss?** Any way this makes ShipLoop worse: a wrong default now looks endorsed; the list becomes a
   place to launder scope; later stages ignore it; it costs a refusal loop on every run; it contradicts something in
   the journals.

End with a verdict: build as designed, build with the changes you list (numbered, most important first), or do not
build, and the one experiment that would change your mind.
