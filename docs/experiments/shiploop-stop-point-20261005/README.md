# Script-owned stop point: feasibility study and design, 2026-10-05

The owner asked: should the script hold state that makes ShipLoop itself stop at a named stage or iteration, so testing is
deterministic ("having the script control the flow")? A read-only eight-agent study (four investigators, a design, two attacks,
a revision) with scratch prototypes and tiny real host calls answered **feasible in part**.

| Question | Answer |
|---|---|
| Stop after or before a stage | yes: an optional `stop_at` record in state.md; the transition that accepts the stage and moves past it is saved already paused, through the existing pause; nothing is killed, so metrics.json, result.json and the Run Review export are written; `resume` continues in place |
| Stop at pass N of an Improve or Backchain loop | no: the Until Loop runtime is hash-pinned and S-10 forbids a cap; the nearest feasible stop is the import after the child (an improve-complete) |
| How a model-started run receives it | the harness arms it with a new verb (`shiploop stop-at --set after:<stage>`) as soon as state.md appears (the model's first accept comes 7-16 s later on Claude hello runs, 81-304 s on Grok and Luna battleship runs); an environment variable also reaches Claude, Grok and Codex (observed) but is ambient and cannot arm a continuation, so it is not recommended |
| What it cannot do | test a changed ShipLoop on a stored real plan (a continuation runs the planning-time install); say how reliably models end their turn on the held packet in long runs (unmeasured) |

Files: `design-final.json` (the final design: stop kinds, option, arming, resume, harness changes with owners, increments, spec text, owner
decisions, unknowns), the four investigation reports as text, and the two attacks. The prototypes and experiments were
session-local scratch and are not kept; every figure in the design names its source.

Ownership: the engine changes (state key, firing hook, verb, held packet, docs) belong to the ShipLoop engine session; `test/shiploop_e2e/run.py` (the `--stop-at`
flag, arming, grading, termination record, regrade and export of a stopped run) and the SPEC amendment belong to the E2E and Run Review session.
Status: designed, not built. Nothing here changes a skill, script or prompt.
