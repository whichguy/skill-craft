# Readings and run lists of the platform-knowledge study, copied from its apparatus branch

Copied on 2026-11-22 from branch `pk-candidate-0d73cf` at commit df43f399da76b2e522d9029c16da4762e54e0984, so that every reading
`docs/platform-knowledge-journal.md` cites can be opened from the journal's own branch. They are the scripts'
printed outputs and the run allocation lists, unchanged.

- `harbor/`: the invented-platform bench: its specification (`SPEC.md`), the readings of rungs 1 to 3 and their
  allocation lists.
- `familiar/readings/`: the readings of rungs 4 to 13 on the two platforms the models know (plan-stage slices and
  whole deliveries): the fact readings, the product checks, the scope readings and the packet reading of journal
  section 47.
- `familiar/runs/`: the allocation list of each rung (sample id, host, model, effort, case or starting repository,
  build, request).
- `familiar/packets/`: two spec packets as rendered: with the entries printed by value
  (`pk-nodeplain-spec-live.md`) and with the one look-up line (`pk-nodeplain-named-spec-lookup.md`).

The journal cites these files by their path on the apparatus branch (`familiar/readings/<name>`); the same name is
here under `evidence/study-branch/familiar/readings/`.

Not copied, and only on that branch: the benches' scripts and fixtures, the experiment switches in
`skills/shiploop/scripts/shiploop_navigator.py`, and the platform cards with their experiment-only sections. That
branch holds two planted facts (N-GATEWAY, S-ACCESS-GROUP) and an invented platform card, and must not go to `main`
as it is.

The files hold absolute paths of the machine the runs were made on.
